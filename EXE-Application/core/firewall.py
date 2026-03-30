"""Windows Firewall-based outbound isolation for exam runtime.

Primary workflow:
1) Switch default outbound policy to block.
2) Add allow rules for the app process (and optional approved endpoints).
3) Restore normal policy and remove rules during cleanup.
"""

import os
import sys
import subprocess
import ctypes
import platform
import socket
import threading
from urllib.parse import urlparse
from typing import List, Dict, Optional


class NetworkIsolator:
    """Manage temporary firewall lockdown around an exam session."""
    
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self._dev_program_paths: List[str] = []
        if getattr(sys, "frozen", False):
            self.app_path = sys.executable
        else:
            # In source mode the active process is python.exe, so rules must target
            # the interpreter executable rather than script file paths.
            self.app_path = sys.executable
            # Include common launcher binaries used in local/dev run paths.
            exe_dir = os.path.dirname(sys.executable)
            for p in [
                sys.executable,
                os.path.join(exe_dir, "python.exe"),
                os.path.join(exe_dir, "pythonw.exe"),
                os.path.join(os.environ.get("WINDIR", r"C:\\Windows"), "py.exe"),
            ]:
                pp = os.path.abspath(p)
                if os.path.isfile(pp) and pp.lower() not in [x.lower() for x in self._dev_program_paths]:
                    self._dev_program_paths.append(pp)
            print(
                "[Network] WARNING: Running in dev mode — firewall rule targets python.exe. "
                "This allows Python-based tooling to access network while isolated. Build the EXE for production-hard isolation."
            )
        self.rule_name_allow = "Proctoring_App_Allow"
        self.rule_name_block = "Proctoring_App_Block_All"
        self._is_isolated = False
        self._allowed_endpoints: List[str] = []
        self._allowed_domains: List[str] = []
        self._dynamic_rule_names: List[str] = []
        self._last_error: str = ""
        self._state_lock = threading.RLock()

    def _is_admin(self) -> bool:
        """Return True when the current process has administrator privileges."""
        if not self.is_windows:
            return False
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() == 1
        except:
            return False

    def _run_netsh(self, args: List[str]) -> bool:
        """Execute a netsh firewall command and capture failures in _last_error."""
        try:
            cmd = ["netsh", "advfirewall", "firewall"] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode != 0:
                self._last_error = (result.stderr or result.stdout or "netsh firewall command failed").strip()
            return result.returncode == 0
        except Exception as e:
            self._last_error = str(e)
            return False

    def _set_global_outbound(self, action: str) -> bool:
        """
        Set default outbound policy to allow or block.

        Windows accepts different token styles across versions/locales, so we
        try multiple compatible command forms before failing.
        """
        token_candidates = [
            f"blockin,{action}out",
            f"blockinbound,{action}outbound",
        ]
        profile_candidates = ["allprofiles", "currentprofile"]

        for profile in profile_candidates:
            for token in token_candidates:
                cmd = [
                    "netsh",
                    "advfirewall",
                    "set",
                    profile,
                    "firewallpolicy",
                    token,
                ]
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    if result.returncode == 0:
                        self._last_error = ""
                        return True
                    self._last_error = (result.stderr or result.stdout or "netsh firewallpolicy failed").strip()
                except Exception as e:
                    self._last_error = str(e)
                    continue

        return False

    def _local_firewall_rules_available(self) -> bool:
        """
        Return True when local firewall rules can be applied.

        Some managed endpoints enforce "GPO-store only" where local rules are
        ignored. In that mode, setting outbound policy to BLOCK would cut all
        traffic because our per-program allow rules cannot take effect.
        """
        try:
            cmd = ["netsh", "advfirewall", "show", "allprofiles"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            text = (result.stdout or "").lower()
            if "localfirewallrules" in text and "gpo-store only" in text:
                return False
            return True
        except Exception:
            # If we cannot determine policy mode, keep existing behavior.
            return True

    def add_backend_whitelist(self, backend_url: str) -> bool:
        """
        Parse a backend URL and register its hostname in the allowlist.

        Intended to be called before engage_isolation so backend traffic can
        remain reachable through explicit remote-IP allow rules.
        
        Args:
            backend_url: Full backend URL (e.g., https://host.cloudspaces.litng.ai)
            
        Returns:
            True if domain was successfully registered, False on parse error.
        """
        try:
            if not backend_url:
                return False
            parsed = urlparse(backend_url or "")
            hostname = parsed.hostname or parsed.netloc or ""
            if hostname:
                with self._state_lock:
                    if hostname not in self._allowed_domains:
                        self._allowed_domains.append(hostname)
                        added = True
                    else:
                        added = False
            else:
                added = False

            if hostname and added:
                print(f"[Network] ✓ Backend domain whitelisted: {hostname}")
                return True
            elif hostname:
                print(f"[Network] ℹ Backend domain already whitelisted: {hostname}")
                return True
            else:
                print(f"[Network] ✗ Failed to parse backend URL: {backend_url[:50]}")
                return False
        except Exception as e:
            print(f"[Network] ✗ Whitelist error: {e}")
            return False

    def add_allowed_endpoint(self, host: str, port: Optional[int] = None):
        """
        Add a specific endpoint to the explicit allowlist.

        When port is omitted, all remote ports for the host are allowed.
        """
        endpoint = f"{host}:{port}" if port else host
        with self._state_lock:
            if endpoint not in self._allowed_endpoints:
                self._allowed_endpoints.append(endpoint)

    def _resolve_host_ips(self, host: str) -> List[str]:
        """Resolve host to a deduplicated IP list (IPv4/IPv6)."""
        try:
            infos = socket.getaddrinfo(host, None)
            ips: List[str] = []
            for info in infos:
                sockaddr = info[4]
                if not sockaddr:
                    continue
                ip = sockaddr[0]
                if ip and ip not in ips:
                    ips.append(ip)
            return ips
        except Exception:
            return []

    def _add_remote_allow_rule(self, name: str, remote_ip: str, remote_port: Optional[str] = None) -> bool:
        """Create one outbound allow rule for a remote IP (and optional port)."""
        args = [
            "add", "rule",
            f"name={name}",
            "dir=out",
            "action=allow",
            f"program={self.app_path}",
            "enable=yes",
            "profile=any",
            f"remoteip={remote_ip}",
        ]
        if remote_port:
            args.append(f"remoteport={remote_port}")
        return self._run_netsh(args)

    def _engage_domain_endpoint_whitelist(self, flags: List[str]) -> None:
        """
        Create explicit remote-IP allow rules for configured domains/endpoints.

        This is a best-effort step. Failures are reported in flags but do not
        abort the primary isolation flow.
        """
        with self._state_lock:
            self._dynamic_rule_names.clear()
            allowed_domains = list(self._allowed_domains)
            allowed_endpoints = list(self._allowed_endpoints)
        idx = 0

        for domain in allowed_domains:
            ips = self._resolve_host_ips(domain)
            if not ips:
                flags.append(f"Could not resolve whitelisted domain: {domain}")
                continue
            for ip in ips:
                idx += 1
                rule_name = f"{self.rule_name_allow}_Remote_{idx}"
                if self._add_remote_allow_rule(rule_name, ip):
                    with self._state_lock:
                        self._dynamic_rule_names.append(rule_name)
                else:
                    err = f" Details: {self._last_error}" if self._last_error else ""
                    flags.append(f"Failed to add remote allow rule for {domain} ({ip}).{err}")

        for endpoint in allowed_endpoints:
            host = endpoint
            port: Optional[str] = None
            if ":" in endpoint and endpoint.count(":") == 1:
                host, port = endpoint.split(":", 1)
            if not host:
                continue

            ips = self._resolve_host_ips(host)
            if not ips:
                flags.append(f"Could not resolve whitelisted endpoint host: {host}")
                continue
            for ip in ips:
                idx += 1
                rule_name = f"{self.rule_name_allow}_Endpoint_{idx}"
                if self._add_remote_allow_rule(rule_name, ip, port):
                    with self._state_lock:
                        self._dynamic_rule_names.append(rule_name)
                else:
                    err = f" Details: {self._last_error}" if self._last_error else ""
                    flags.append(f"Failed to add endpoint allow rule for {endpoint} ({ip}).{err}")

    def engage_isolation(self) -> Dict:
        """
        Engage outbound lockdown for the current process.

        Sequence:
        1) Remove stale rules from previous runs.
        2) Set default outbound policy to BLOCK.
        3) Add process-specific allow rules.
        4) Add optional remote endpoint/domain allow rules.
        
        Returns dict with isolation status and any warning flags.
        """
        flags = []
        
        if not self.is_windows:
            flags.append("Network isolation is only supported on Windows.")
            return {"isolated": False, "flags": flags}

        if not self._is_admin():
            flags.append("CRITICAL: Network isolation requires RUN AS ADMINISTRATOR.")
            return {"isolated": False, "flags": flags}

        # If local rules are disabled by policy, skip lockdown to avoid blocking
        # all traffic without any working allow exceptions.
        if not self._local_firewall_rules_available():
            flags.append(
                "CRITICAL: Local firewall rules are disabled by Group Policy "
                "(GPO-store only). Skipping isolation to avoid blocking all network traffic."
            )
            return {"isolated": False, "flags": flags}

        with self._state_lock:
            if self._is_isolated:
                return {"isolated": True, "flags": ["Isolation already engaged."]}

        # Clean up stale rules before applying a new isolation session.
        self.release_isolation(silence_errors=True)

        # Apply global outbound block policy.
        if not self._set_global_outbound("block"):
            err = f" Details: {self._last_error}" if self._last_error else ""
            flags.append(f"Failed to set global outbound policy to BLOCK.{err}")
            return {"isolated": False, "flags": flags}

        # Add primary program-level allow rule.
        allow_args = [
            "add", "rule",
            f"name={self.rule_name_allow}",
            "dir=out",
            "action=allow",
            f"program={self.app_path}",
            "enable=yes",
            "profile=any",
        ]
        
        if not self._run_netsh(allow_args):
            err = f" Details: {self._last_error}" if self._last_error else ""
            flags.append(f"Failed to add app whitelist to Windows Firewall.{err}")
            # Roll back outbound policy if allow rule creation fails.
            self._set_global_outbound("allow")
            return {"isolated": False, "flags": flags}

        # In source mode, also allow common interpreter launcher binaries.
        if not getattr(sys, "frozen", False):
            for idx, dev_path in enumerate(self._dev_program_paths, start=1):
                if os.path.normcase(dev_path) == os.path.normcase(self.app_path):
                    continue
                rule_name = f"{self.rule_name_allow}_DevProg_{idx}"
                dev_allow_args = [
                    "add", "rule",
                    f"name={rule_name}",
                    "dir=out",
                    "action=allow",
                    f"program={dev_path}",
                    "enable=yes",
                    "profile=any",
                ]
                if self._run_netsh(dev_allow_args):
                    with self._state_lock:
                        self._dynamic_rule_names.append(rule_name)
                else:
                    err = f" Details: {self._last_error}" if self._last_error else ""
                    flags.append(f"Failed to add dev allow rule for {dev_path}.{err}")

        # Add explicit remote allow rules for preconfigured domains/endpoints.
        self._engage_domain_endpoint_whitelist(flags)

        with self._state_lock:
            self._is_isolated = True
        print(f"[Network] Isolation engaged. Only {self.app_path} can access network.")
        return {"isolated": True, "flags": flags}

    def release_isolation(self, silence_errors: bool = False, max_retries: int = 3):
        """
        Release isolation and restore normal outbound firewall policy.

        Cleanup sequence:
        1) Restore outbound policy to ALLOW.
        2) Remove static and dynamic rules created by this component.
        
        Retries are used to tolerate transient command failures.
        """
        if not self.is_windows:
            return {"success": True, "message": "Not Windows, isolation not applicable"}

        with self._state_lock:
            if not self._is_isolated:
                return {"success": True, "message": "Not isolated, no cleanup needed"}

        print("[Network] Starting firewall cleanup...")
        
        for attempt in range(1, max_retries + 1):
            try:
                success_policy = False
                success_del = False
                
                # Step 1: restore global outbound policy.
                print(f"[Network] Attempt {attempt}/{max_retries}: Restoring outbound policy...")
                success_policy = self._set_global_outbound("allow")
                
                if success_policy:
                    print("[Network] ✓ Outbound policy restored to ALLOW")
                else:
                    print(f"[Network] ✗ Failed to restore policy: {self._last_error}")
                
                # Step 2: remove custom rules created during isolation.
                print(f"[Network] Attempt {attempt}/{max_retries}: Deleting firewall rules...")
                del_args = ["delete", "rule", f"name={self.rule_name_allow}"]
                success_del = self._run_netsh(del_args)

                # Also remove dynamically created endpoint/domain rules.
                with self._state_lock:
                    dynamic_rules = list(self._dynamic_rule_names)
                for rule_name in dynamic_rules:
                    self._run_netsh(["delete", "rule", f"name={rule_name}"])
                with self._state_lock:
                    self._dynamic_rule_names.clear()
                
                if success_del:
                    print("[Network] ✓ Firewall rules deleted")
                else:
                    # Missing rule is acceptable during cleanup.
                    if "not found" in self._last_error.lower():
                        print("[Network] ✓ No custom rules to delete (already clean)")
                        success_del = True
                    else:
                        print(f"[Network] ✗ Failed to delete rules: {self._last_error}")
                
                # Exit successfully when policy and rule cleanup both succeed.
                if success_policy and success_del:
                    with self._state_lock:
                        self._is_isolated = False
                    print("[Network] ✅ Isolation successfully released. Network restored to normal.")
                    return {"success": True, "message": "Firewall cleanup completed successfully"}
                
                # Final attempt failed; force-safe policy restoration.
                if attempt == max_retries:
                    print(f"[Network] ⚠️  Final cleanup attempt - using emergency mode...")
                    self._emergency_force_firewall_restore()
                    with self._state_lock:
                        self._is_isolated = False
                    return {
                        "success": True,
                        "message": "Firewall restored via emergency mode",
                        "warning": "Some rules may require manual verification"
                    }
                    
            except Exception as e:
                print(f"[Network] Exception during cleanup (attempt {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    return {"success": False, "message": f"Firewall cleanup failed after {max_retries} attempts: {str(e)}"}
                continue
        
        with self._state_lock:
            self._is_isolated = False
        if not silence_errors:
            print("[Network] Warning: Failed to cleanly restore firewall rules.")
        return {"success": False, "message": "Firewall cleanup incomplete"}
    
    def _emergency_force_firewall_restore(self):
        """
        Emergency fallback to force outbound policy back to allow.

        Used only after normal cleanup retries are exhausted.
        """
        print("[Network] Executing emergency firewall restore...")
        
        try:
            # Force-restore policy using allprofiles token form.
            cmd = ["netsh", "advfirewall", "set", "allprofiles", "firewallpolicy", "blockinbound,allowoutbound"]
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                print("[Network] ✓ Emergency restore successful")
                return True
        except Exception as e:
            print(f"[Network] Emergency restore failed: {e}")
        
        return False

    def verify_isolation_status(self) -> Dict:
        """
        Query firewall profiles and infer current outbound policy state.
        """
        if not self.is_windows:
            return {"verified": True, "status": "N/A (not Windows)"}
        
        try:
            # Query current firewall policy text from netsh.
            cmd = ["netsh", "advfirewall", "show", "allprofiles"]
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            stdout_lower = result.stdout.lower()
            # Match explicit outbound tokens to avoid false positives.
            if "blockoutbound" in stdout_lower:
                return {"verified": True, "status": "ISOLATED (outbound blocked)", "isolated": True}
            elif "allowoutbound" in stdout_lower:
                return {"verified": True, "status": "NORMAL (outbound allowed)", "isolated": False}
            else:
                return {"verified": True, "status": "UNKNOWN", "raw": result.stdout}
        except Exception as e:
            return {"verified": False, "status": f"Error querying firewall: {e}"}
    
    def get_detailed_status_report(self) -> Dict:
        """
        Build a diagnostic report of runtime firewall/isolation state.
        """
        with self._state_lock:
            isolated_flag = self._is_isolated
            last_error = self._last_error
        report = {
            "timestamp": __import__('time').time(),
            "is_isolated_flag": isolated_flag,
            "is_windows": self.is_windows,
            "is_admin": self._is_admin(),
            "isolation_status": self.verify_isolation_status(),
            "firewall_rules": {},
            "error_log": last_error,
        }
        
        if not self.is_windows:
            return report
        
        try:
            # Query presence/details for the primary allow rule.
            cmd = ["netsh", "advfirewall", "firewall", "show", "rule", f"name={self.rule_name_allow}"]
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                report["firewall_rules"]["allow_rule_exists"] = True
                report["firewall_rules"]["allow_rule_details"] = result.stdout
            else:
                report["firewall_rules"]["allow_rule_exists"] = False
                report["firewall_rules"]["allow_rule_error"] = result.stderr or "Not found"
        except Exception as e:
            report["firewall_rules"]["query_error"] = str(e)
        
        return report
            
    def is_isolated(self) -> bool:
        """Returns True if network isolation is currently engaged."""
        with self._state_lock:
            return self._is_isolated
            
    def __del__(self):
        """Attempt best-effort cleanup during object finalization."""
        with self._state_lock:
            isolated = self._is_isolated
        if isolated:
            self.release_isolation(silence_errors=True)
