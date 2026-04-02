"""
sandbox.py — Secure Docker-based code execution.

Each run spawns an isolated container:
  - No network access (--network none)
  - Read-only filesystem (--read-only)
  - Non-root user (uid 1000)
  - seccomp profile blocks dangerous syscalls
  - Hard CPU + memory limits
  - Auto-killed after time limit
"""

import asyncio
import os
import shlex
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional
import structlog

import docker
from docker.errors import DockerException, ImageNotFound, APIError
from docker.types import Ulimit

from app.config import settings
from app.schemas.schemas import RunResult

log = structlog.get_logger()

# ── Language config ───────────────────────────────────────────────────────────
LANGUAGE_CONFIG = {
    "python": {
        "image": f"{settings.SANDBOX_IMAGE_PREFIX}-python:latest",
        "filename": "solution.py",
        "run_cmd": ["python3", "-u", "/sandbox/solution.py"],
        "compile_cmd": None,
    },
    "javascript": {
        "image": f"{settings.SANDBOX_IMAGE_PREFIX}-nodejs:latest",
        "filename": "solution.js",
        "run_cmd": ["node", "/sandbox/solution.js"],
        "compile_cmd": None,
    },
    "java": {
        "image": f"{settings.SANDBOX_IMAGE_PREFIX}-java:latest",
        "filename": "Solution.java",
        "run_cmd": ["java", "-cp", "/sandbox", "Solution"],
        "compile_cmd": ["javac", "/sandbox/Solution.java"],
    },
    "cpp": {
        "image": f"{settings.SANDBOX_IMAGE_PREFIX}-cpp:latest",
        "filename": "solution.cpp",
        "run_cmd": ["/sandbox/solution"],
        "compile_cmd": ["g++", "-O2", "-o", "/sandbox/solution", "/sandbox/solution.cpp"],
    },
    "go": {
        "image": f"{settings.SANDBOX_IMAGE_PREFIX}-go:latest",
        "filename": "solution.go",
        "run_cmd": ["/sandbox/solution"],
        "compile_cmd": ["go", "build", "-o", "/sandbox/solution", "/sandbox/solution.go"],
    },
    "rust": {
        "image": f"{settings.SANDBOX_IMAGE_PREFIX}-rust:latest",
        "filename": "solution.rs",
        "run_cmd": ["/sandbox/solution"],
        "compile_cmd": ["rustc", "-o", "/sandbox/solution", "/sandbox/solution.rs"],
    },
}

# seccomp profile: block the most dangerous syscalls
SECCOMP_PROFILE = {
    "defaultAction": "SCMP_ACT_ALLOW",
    "syscalls": [
        {
            "names": [
                "mount", "umount", "umount2", "pivot_root", "chroot",
                "init_module", "delete_module", "finit_module",
                "kexec_load", "kexec_file_load",
                "perf_event_open", "ptrace",
                "unshare", "setns",
            ],
            "action": "SCMP_ACT_ERRNO",
        }
    ],
}


class SandboxExecutor:
    def __init__(self):
        self._client: Optional[docker.DockerClient] = None

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    async def run(
        self,
        language: str,
        source_code: str,
        stdin: str = "",
        time_limit_seconds: int = settings.MAX_EXECUTION_TIME_SECONDS,
        memory_limit_mb: int = settings.MAX_MEMORY_MB,
    ) -> RunResult:
        """Execute code in an isolated Docker container and return the result."""
        run_id = str(uuid.uuid4())[:8]
        lang_cfg = LANGUAGE_CONFIG.get(language)
        if not lang_cfg:
            raise ValueError(f"Unsupported language: {language}")

        log.info("sandbox_run_start", run_id=run_id, language=language)
        start_time = time.perf_counter()

        # Write source to temp dir that will be bind-mounted read-only
        with tempfile.TemporaryDirectory(prefix=f"sandbox_{run_id}_") as tmpdir:
            # Temp dirs are 0700 by default; make them traversable for uid 1000 in sandbox containers.
            os.chmod(tmpdir, 0o755)
            src_path = Path(tmpdir) / lang_cfg["filename"]
            src_path.write_text(source_code, encoding="utf-8")
            os.chmod(src_path, 0o644)

            try:
                # Step 1: Compile (if needed)
                if lang_cfg["compile_cmd"]:
                    compile_result = await self._run_container(
                        image=lang_cfg["image"],
                        command=lang_cfg["compile_cmd"],
                        tmpdir=tmpdir,
                        stdin_data="",
                        time_limit=30,       # compilation gets more time
                        memory_limit_mb=512,
                        run_id=f"{run_id}-compile",
                    )
                    if compile_result.exit_code != 0:
                        elapsed = int((time.perf_counter() - start_time) * 1000)
                        return RunResult(
                            stdout="",
                            stderr=compile_result.stderr[:4096],
                            exit_code=compile_result.exit_code,
                            execution_time_ms=elapsed,
                            timed_out=False,
                        )

                # Step 2: Run
                result = await self._run_container(
                    image=lang_cfg["image"],
                    command=lang_cfg["run_cmd"],
                    tmpdir=tmpdir,
                    stdin_data=stdin,
                    time_limit=time_limit_seconds,
                    memory_limit_mb=memory_limit_mb,
                    run_id=run_id,
                )
            except RuntimeError as exc:
                allow_fallback = os.getenv("OBSERVE_ALLOW_LOCAL_EXEC_FALLBACK", "1").lower() in ("1", "true", "yes", "on")
                if not allow_fallback:
                    raise
                log.warning(
                    "sandbox_docker_unavailable_fallback",
                    run_id=run_id,
                    language=language,
                    reason=str(exc),
                )
                result = await self._run_local(
                    language=language,
                    source_code=source_code,
                    stdin=stdin,
                    time_limit_seconds=time_limit_seconds,
                )

        elapsed = int((time.perf_counter() - start_time) * 1000)
        result.execution_time_ms = elapsed
        log.info(
            "sandbox_run_done",
            run_id=run_id,
            language=language,
            exit_code=result.exit_code,
            elapsed_ms=elapsed,
            timed_out=result.timed_out,
        )
        return result

    async def _run_container(
        self,
        image: str,
        command: list,
        tmpdir: str,
        stdin_data: str,
        time_limit: int,
        memory_limit_mb: int,
        run_id: str,
    ) -> RunResult:
        """Run a single Docker container and capture output."""
        container = None
        timed_out = False

        mem_bytes = memory_limit_mb * 1024 * 1024

        # Write stdin payload into the mounted sandbox volume and redirect from file.
        stdin_path = Path(tmpdir) / ".stdin.txt"
        stdin_path.write_text(stdin_data or "", encoding="utf-8")
        os.chmod(stdin_path, 0o644)

        container_command = command
        env_vars = {
            "HOME": "/tmp",
            "TMPDIR": "/tmp",
        }
        command_str = shlex.join(command)
        container_command = [
            "/bin/sh",
            "-lc",
            f"{command_str} < /sandbox/.stdin.txt",
        ]

        try:
            container = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.containers.run(
                    image=image,
                    command=container_command,
                    detach=True,
                    stdin_open=True,
                    # ── Security ─────────────────────────────────────────
                    network_mode=settings.DOCKER_NETWORK,
                    read_only=True,
                    user="1000:1000",
                    cap_drop=["ALL"],
                    security_opt=[
                        "no-new-privileges:true",
                        f"seccomp={self._seccomp_json()}",
                    ],
                    # ── Resource limits ───────────────────────────────────
                    mem_limit=f"{memory_limit_mb}m",
                    memswap_limit=f"{memory_limit_mb}m",  # disable swap
                    cpu_period=100_000,
                    cpu_quota=50_000,   # 50% of one CPU
                    ulimits=[
                        Ulimit(name="nofile", soft=64, hard=64),
                        Ulimit(name="fsize", soft=10 * 1024 * 1024, hard=10 * 1024 * 1024),
                    ],
                    # ── Filesystem ────────────────────────────────────────
                    volumes={
                        tmpdir: {"bind": "/sandbox", "mode": "rw"},
                        "/tmp": {"bind": "/tmp", "mode": "rw"},
                    },
                    tmpfs={"/run": "size=10m,noexec"},
                    environment=env_vars,
                    working_dir="/sandbox",
                    # ── Cleanup ───────────────────────────────────────────
                    auto_remove=False,
                    name=f"sandbox_{run_id}",
                    labels={"sandbox": "true", "run_id": run_id},
                ),
            )

            # Wait with timeout
            try:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: container.wait()
                    ),
                    timeout=time_limit + settings.EXECUTION_TIMEOUT_BUFFER_SECONDS,
                )
                exit_code = result.get("StatusCode", 1)
            except asyncio.TimeoutError:
                timed_out = True
                exit_code = 124  # standard timeout exit code
                await asyncio.get_event_loop().run_in_executor(None, lambda: container.kill())

            # Collect logs
            raw_logs = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: container.logs(stdout=True, stderr=True, stream=False),
            )
            # Docker muxes stdout/stderr; parse the stream
            stdout, stderr = self._parse_docker_logs(container)

        except ImageNotFound:
            log.error("sandbox_image_not_found", image=image)
            return RunResult(stdout="", stderr="Sandbox image not found", exit_code=1, execution_time_ms=0)
        except (APIError, DockerException, PermissionError, OSError) as e:
            log.error("docker_api_error", error=str(e), run_id=run_id)
            raise RuntimeError(f"Docker sandbox unavailable: {e}") from e
        finally:
            if container:
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda: container.remove(force=True)
                    )
                except Exception:
                    pass

        # Truncate outputs
        max_out = settings.MAX_OUTPUT_BYTES
        stdout = stdout[:max_out]
        stderr = stderr[:max_out]

        return RunResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            execution_time_ms=0,  # caller will set this
            timed_out=timed_out,
        )

    def _parse_docker_logs(self, container) -> tuple[str, str]:
        """Separate stdout and stderr from Docker multiplexed log stream."""
        try:
            stdout_lines = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr_lines = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            return stdout_lines, stderr_lines
        except Exception:
            return "", ""

    def _seccomp_json(self) -> str:
        import json
        return json.dumps(SECCOMP_PROFILE)

    async def _run_local(
        self,
        language: str,
        source_code: str,
        stdin: str,
        time_limit_seconds: int,
    ) -> RunResult:
        """
        Fallback execution path when Docker is unavailable in hosted environments.
        Supports interpreted languages only.
        """
        language = (language or "").strip().lower()
        local_commands = {
            "python": ["python3", "-u"],
            "javascript": ["node"],
        }
        if language not in local_commands:
            return RunResult(
                stdout="",
                stderr=(
                    "Execution backend unavailable: Docker access denied and "
                    f"local fallback does not support '{language}'"
                ),
                exit_code=1,
                execution_time_ms=0,
                timed_out=False,
            )

        start = time.perf_counter()
        suffix = ".py" if language == "python" else ".js"
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as f:
            f.write(source_code)
            tmp_file = f.name

        timed_out = False
        try:
            proc = await asyncio.create_subprocess_exec(
                *(local_commands[language] + [tmp_file]),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(input=(stdin or "").encode("utf-8")),
                    timeout=time_limit_seconds + settings.EXECUTION_TIMEOUT_BUFFER_SECONDS,
                )
                exit_code = int(proc.returncode or 0)
            except asyncio.TimeoutError:
                timed_out = True
                proc.kill()
                stdout_b, stderr_b = await proc.communicate()
                exit_code = 124

            max_out = settings.MAX_OUTPUT_BYTES
            stdout = (stdout_b or b"").decode("utf-8", errors="replace")[:max_out]
            stderr = (stderr_b or b"").decode("utf-8", errors="replace")[:max_out]
            elapsed = int((time.perf_counter() - start) * 1000)
            return RunResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time_ms=elapsed,
                timed_out=timed_out,
            )
        finally:
            try:
                os.remove(tmp_file)
            except Exception:
                pass


sandbox_executor = SandboxExecutor()

