"""Controller that bridges backend exam APIs with the exam UI.

Coordinates bootstrap, answer persistence, coding actions, telemetry dispatch,
and final submission flow between ProctorClient and ExamScreen.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Callable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QWidget

from api_client import ProctorClient, ProctorAPIError
from ui.exam import ExamScreen


# Vision model loader.
class VisionModelLoader(QObject):
    """Load vision model asynchronously without blocking UI."""
    model_loaded = pyqtSignal()
    model_load_failed = pyqtSignal(str)
    
    def __init__(self, vision_proctor):
        super().__init__()
        self.vision_proctor = vision_proctor
        self._state_lock = threading.Lock()
        self._in_flight_event = threading.Event()
        self._thread: threading.Thread | None = None
    
    def load_async(self):
        """Load model in background thread."""
        with self._state_lock:
            if self._in_flight_event.is_set():
                return
            self._in_flight_event.set()
            self._thread = threading.Thread(target=self._load_in_thread, daemon=True)
            thread = self._thread
        thread.start()
    
    def _load_in_thread(self):
        """Run on background thread."""
        try:
            self.vision_proctor._ensure_model_exists()
            self.model_loaded.emit()
        except Exception as e:
            self.model_load_failed.emit(str(e))
        finally:
            with self._state_lock:
                self._in_flight_event.clear()
                self._thread = None


# Exam monitoring starter.
class ExamMonitoringStarter(QObject):
    """Start exam monitoring on background thread without blocking UI."""
    monitoring_ready = pyqtSignal()
    monitoring_failed = pyqtSignal(str)
    
    def __init__(self, proctoring_service):
        super().__init__()
        self.proctoring_service = proctoring_service
        self._state_lock = threading.Lock()
        self._in_flight_event = threading.Event()
        self._thread: threading.Thread | None = None
    
    def start_async(self):
        """Start monitoring on background thread."""
        with self._state_lock:
            if self._in_flight_event.is_set():
                return
            self._in_flight_event.set()
            self._thread = threading.Thread(target=self._start_monitoring, daemon=True)
            thread = self._thread
        thread.start()
    
    def _start_monitoring(self):
        """Run monitoring initialization on a background thread."""
        try:
            # Initialize exam monitoring services away from the UI thread.
            self.proctoring_service.start_exam_monitoring(engage_security=True)
            self.monitoring_ready.emit()
        except Exception as e:
            self.monitoring_failed.emit(f"Exam monitoring startup failed: {e}")
        finally:
            with self._state_lock:
                self._in_flight_event.clear()
                self._thread = None


# Telemetry payload builder.
def _build_clean_telemetry() -> dict:
    """Return a safe default telemetry payload (all checks passed)."""
    return {
        "vm_detected":       {"detected": False, "flags": [], "mac_hints": []},
        "sandbox_detected":  {"detected": False, "flags": []},
        "rdp_detected":      {"detected": False, "flags": []},
        "anti_debug":        {"detected": False, "flags": []},
        "clock_integrity":   {"tampered": False, "message": ""},
        "os_enforcement":    {"passed": True,    "message": ""},
        "hw_checks": {
            "media_devices": {"passed": True, "flags": []},
            "monitors":      {"count": 1,    "flags": []},
        },
        "process_violations": {"flagged_processes": []},
        "audio_proctoring":   {"detected": False, "severity": "none", "flags": []},
        "client_raw_is_safe": True,
    }


# Exam controller.
class ExamController(QObject):
    """
    Bridges the ProctorClient (server) and ExamScreen (UI).

    Signals
    -------
    exam_ready(exam_data)   – emitted once bootstrap returns status="ready"
    exam_blocked(reason)    – emitted when server decision == "block"
    exam_submitted()        – emitted after successful final submission
    error_occurred(message) – any recoverable or display-worthy error
    """

    exam_ready    = pyqtSignal(dict)       # exam_data dict
    exam_blocked  = pyqtSignal(str)        # block reason string
    exam_submitted = pyqtSignal()
    error_occurred = pyqtSignal(str)
    ui_warning_requested = pyqtSignal(str)

    # Telemetry interval in seconds.
    TELEMETRY_INTERVAL = 60

    def __init__(
        self,
        client: ProctorClient,
        hw_fingerprint: str,
        exam_launch_code: str,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._client      = client
        self._hw_fp       = hw_fingerprint
        self._launch_code = exam_launch_code

        self._screen:          ExamScreen | None = None
        self._exam_data:       dict               = {}
        self._start_epoch:     float              = 0.0
        self._violation_count: int                = 0
        self._last_run_result: dict               = {}
        self._state_lock = threading.RLock()
        self._finalize_started = False
        self._telemetry_in_flight = False
        self._queued_telemetry_payload: dict | None = None
        self._thread_lock = threading.Lock()
        self._bg_threads: set[threading.Thread] = set()
        self._finalize_thread: threading.Thread | None = None

        # Background telemetry timer (Qt timer on main thread).
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.setInterval(self.TELEMETRY_INTERVAL * 1000)
        self._telemetry_timer.timeout.connect(self._send_telemetry_bg)

        # Pending answer queue (question_id -> answer_value).
        self._pending_answers: dict[str | int, str] = {}
        self._answer_lock = threading.Lock()
        self.ui_warning_requested.connect(self.show_warning)

    def _spawn_bg_task(
        self,
        *,
        name: str,
        target: Callable[[], None],
        timeout_warn_sec: float = 30.0,
    ) -> threading.Thread:
        """Start a daemon task with tracking and timeout warning."""
        def _runner() -> None:
            warned = False

            def _warn_if_still_running() -> None:
                nonlocal warned
                with self._thread_lock:
                    if thread in self._bg_threads:
                        warned = True
                        print(f"[CTRL] Background task '{name}' exceeded {int(timeout_warn_sec)}s")

            timer = threading.Timer(timeout_warn_sec, _warn_if_still_running)
            timer.daemon = True
            timer.start()
            try:
                target()
            finally:
                timer.cancel()
                with self._thread_lock:
                    self._bg_threads.discard(thread)
                if warned:
                    print(f"[CTRL] Background task '{name}' completed after timeout warning")

        thread = threading.Thread(target=_runner, daemon=True, name=name)
        with self._thread_lock:
            self._bg_threads.add(thread)
        thread.start()
        return thread

    def _on_screen_destroyed(self, _obj=None) -> None:
        """Stop periodic callbacks when screen is destroyed."""
        self._telemetry_timer.stop()
        self._screen = None

    # Public exam flow

    def start(self, parent_widget: QWidget | None = None) -> ExamScreen | None:
        """
        1. Acquire session nonce.
        2. Bootstrap exam.
        3. Build ExamScreen with real data.
        4. Wire all signals.
        5. Return the ExamScreen widget (caller is responsible for showing it).
        """
        # 1. Acquire session nonce.
        try:
            self._client.get_nonce(self._hw_fp)
        except ProctorAPIError as exc:
            self.error_occurred.emit(f"Session setup failed: {exc}")
            return None

        # 2. Bootstrap exam session.
        try:
            result = self._client.bootstrap_exam(self._launch_code)
        except ProctorAPIError as exc:
            self.error_occurred.emit(f"Exam bootstrap failed: {exc}")
            return None

        if result.get("status") == "waiting":
            secs = result.get("seconds_to_start", 0)
            mins = secs // 60
            self.error_occurred.emit(
                f"Exam starts in {mins} minute(s).  Please come back then."
            )
            return None

        if result.get("status") != "ready":
            self.error_occurred.emit(f"Unexpected bootstrap response: {result}")
            return None

        # 3. Build ExamScreen.
        self._exam_data  = self._transform_bootstrap(result)
        self._start_epoch = time.time()

        self._screen = ExamScreen(exam_data=self._exam_data)
        self._screen.destroyed.connect(self._on_screen_destroyed)

        # 4. Wire screen/controller signals.
        self._screen.transition_requested.connect(self._on_transition)

        # Hook coding submission callback.
        if hasattr(self._screen, "coding_section"):
            self._screen.coding_section.answer_submitted.connect(
                self._on_coding_submitted
            )

        # 5. Send initial telemetry and start periodic timer.
        with self._state_lock:
            self._finalize_started = False
            self._telemetry_in_flight = False
        self._send_telemetry_bg()
        self._telemetry_timer.start()

        self.exam_ready.emit(self._exam_data)
        return self._screen

    # Server to UI updates

    def update_violation_count(self, count: int):
        """
        Called by the proctoring engine when a new violation is detected.
        Updates both the in-memory counter and the ExamScreen header badge.
        """
        with self._state_lock:
            self._violation_count = count
        if self._screen:
            self._screen.update_violation_count(count)

    def show_warning(self, message: str):
        """Show a proctoring warning text in the exam screen warning bar."""
        if self._screen:
            self._screen.show_warning(message)

    # Answer saving

    def save_answer(
        self,
        question_id: int | str,
        answer: str | list,
        *,
        question_number: int = 1,
        time_taken: int = 0,
    ):
        """
        Immediately POST /v1/exam/answer to persist a single answer.
        Called by the UI after Save & Next.
        Runs in a background thread to keep the UI responsive.
        """
        def _do():
            try:
                self._client.save_answer(
                    question_id, answer,
                    question_number=question_number,
                    time_taken_seconds=time_taken,
                )
                with self._answer_lock:
                    self._pending_answers.pop(str(question_id), None)
            except ProctorAPIError as exc:
                print(f"[CTRL] Answer save failed (q={question_id}): {exc}")
                # Queue failed answer for retry during final submit.
                with self._answer_lock:
                    val = json.dumps(answer) if isinstance(answer, list) else str(answer)
                    self._pending_answers[str(question_id)] = val

                self._spawn_bg_task(name="SaveAnswer", target=_do)

    # Coding execution

    def run_code(
        self,
        question_id: int | str,
        language: str,
        source_code: str,
        stdin: str = "",
        callback: Callable[[dict], None] | None = None,
    ):
        """
        POST /v1/exam/coding/run in a background thread.
        callback(result_dict) is invoked on the result (may be on background thread -
        caller must marshal to main thread if updating Qt widgets).
        """
        def _do():
            try:
                result = self._client.run_code(question_id, language, source_code, stdin)
                with self._state_lock:
                    self._last_run_result = result
            except ProctorAPIError as exc:
                result = {
                    "error":    str(exc),
                    "stdout":   "",
                    "stderr":   str(exc),
                    "exit_code": 1,
                    "execution_time_ms": 0,
                    "public_test_results": [],
                }
            if callback:
                callback(result)

        self._spawn_bg_task(name="RunCode", target=_do)

    # Coding submission

    def _on_coding_submitted(self, code: str):
        """
        Called when CodingSection emits answer_submitted(code).
        Determines the current coding question_id from the session and POSTs.
        """
        # Read language and question context from CodingSection.
        cs = getattr(self._screen, "coding_section", None)
        if cs is None:
            return

        language = getattr(cs, "_current_lang", "Python 3")
        lang_normalized = language.lower().replace(" ", "").replace("python3", "python").split()[0]

        # Support both raw-code and JSON payload submissions.
        submitted_code = str(code or "")
        coding_index = 0
        submitted_question_id: int | str | None = None
        try:
            payload = json.loads(code) if isinstance(code, str) else None
            if isinstance(payload, dict):
                submitted_code = str(
                    payload.get("source_code")
                    or payload.get("code")
                    or submitted_code
                )
                lang_from_payload = str(payload.get("language") or "").strip().lower()
                if lang_from_payload:
                    lang_normalized = lang_from_payload
                coding_index = int(payload.get("question_index") or 0)
                submitted_question_id = payload.get("question_id")
        except Exception:
            pass

        if submitted_question_id not in (None, ""):
            q_id = submitted_question_id
        else:
            q_id = 0

        # Resolve question_id from indexed coding question in exam data.
        if not q_id:
            coding_seen = -1
            for sec in self._exam_data.get("sections", []):
                if sec.get("is_coding"):
                    qs = sec.get("questions", [])
                    for q in qs:
                        if str(q.get("type", "")).lower() == "coding":
                            coding_seen += 1
                            if coding_seen == coding_index:
                                q_id = q.get("id", 0)
                                break
                    if q_id:
                        break

        if not q_id:
            # Fallback for payloads that do not include coding_index.
            screen_exam_data = getattr(self._screen, "_exam_data", None) if self._screen else None
            exam_sections = (screen_exam_data or self._exam_data).get("sections", []) if isinstance((screen_exam_data or self._exam_data), dict) else []
            for sec in exam_sections:
                if sec.get("is_coding"):
                    qs = sec.get("questions", [])
                    if qs:
                        q_id = qs[0].get("id", 0)
                    break

        def _do():
            try:
                result = self._client.submit_code(
                    q_id, lang_normalized, submitted_code,
                    test_results=last_run_result.get("public_test_results"),
                    execution_time_ms=last_run_result.get("execution_time_ms"),
                    memory_used_kb=last_run_result.get("memory_used_kb"),
                    stdout=last_run_result.get("stdout", ""),
                    stderr=last_run_result.get("stderr", ""),
                )
                print(f"[CTRL] Code submitted: {result}")
            except ProctorAPIError as exc:
                print(f"[CTRL] Code submit failed: {exc}")

        with self._state_lock:
            last_run_result = dict(self._last_run_result)

        self._spawn_bg_task(name="SubmitCode", target=_do)

    # Telemetry

    def _send_telemetry_payload_bg(self, telemetry_payload: dict):
        """Serialize telemetry sends and queue latest payload while one is in flight."""
        if not self._client.has_nonce:
            return

        with self._state_lock:
            if self._telemetry_in_flight:
                self._queued_telemetry_payload = dict(telemetry_payload or {})
                return
            self._telemetry_in_flight = True
            self._queued_telemetry_payload = None

        def _do():
            try:
                resp = self._client.send_telemetry(telemetry_payload)
                decision = resp.get("server_decision", {})
                action   = decision.get("action", "allow")
                reasons  = decision.get("reasons", [])

                if action == "block":
                    self.exam_blocked.emit("; ".join(reasons) or "Blocked by server")
                elif action == "warn" and reasons:
                    self.ui_warning_requested.emit(reasons[0])

            except ProctorAPIError as exc:
                print(f"[CTRL] Telemetry failed: {exc}")
            finally:
                queued_payload = None
                with self._state_lock:
                    self._telemetry_in_flight = False
                    if self._queued_telemetry_payload is not None:
                        queued_payload = dict(self._queued_telemetry_payload)
                        self._queued_telemetry_payload = None

                if queued_payload is not None:
                    self._send_telemetry_payload_bg(queued_payload)

        self._spawn_bg_task(name="TelemetrySend", target=_do)

    def _send_telemetry_bg(self):
        """Send baseline telemetry in background without blocking UI."""
        self._send_telemetry_payload_bg(_build_clean_telemetry())

    def send_telemetry(self, results: dict):
        """
        Called by the proctoring engine with real detection results.
        Sends immediately (background thread).
        """
        self._send_telemetry_payload_bg(dict(results or {}))

    # Exam submission

    def _on_transition(self, signal: str):
        if signal in ("submit", "exit"):
            self._finalize_exam()

    def _finalize_exam(self):
        """Collect all answers, POST /v1/exam/submit, POST /v1/exam/logs."""
        with self._state_lock:
            if self._finalize_started:
                return
            self._finalize_started = True

        self._telemetry_timer.stop()

        # Gather answers from the UI.
        ui_answers: dict[str | int, object] = {}
        if self._screen:
            ui_answers = self._screen.get_all_answers()

        # Merge with pending answers queued for retry.
        serialized: dict[str, str] = {}
        for key, val in ui_answers.items():
            # key is (section_idx, q_idx); resolve to question_id.
            q_id = self._resolve_question_id(key)
            if q_id is not None:
                serialized[str(q_id)] = json.dumps(val) if isinstance(val, list) else str(val)

        with self._answer_lock:
            for q_id, val in self._pending_answers.items():
                serialized.setdefault(str(q_id), val)

        duration = int(time.time() - self._start_epoch)

        def _do():
            try:
                self._client.submit_exam(
                    answers=serialized,
                    total_questions=self._total_questions(),
                    session_duration_seconds=duration,
                )
                print("[CTRL] ✔ Exam submitted to server")
            except ProctorAPIError as exc:
                print(f"[CTRL] Submit failed: {exc}")

            # Always attempt log upload after submission.
            try:
                self._client.upload_logs(
                    log_text=f"Exam completed. duration={duration}s answers={len(serialized)}",
                    upload_reason="finalize",
                )
            except ProctorAPIError as exc:
                print(f"[CTRL] Log upload failed: {exc}")

            self.exam_submitted.emit()

        thread = self._spawn_bg_task(name="FinalizeExam", target=_do)
        with self._state_lock:
            self._finalize_thread = thread

    # Helpers

    def _transform_bootstrap(self, bootstrap: dict) -> dict:
        """
        Convert the server bootstrap payload into the format expected by ExamScreen.

        Server sections[].questions[].type values:
            "mcq" | "msq" | "text" | "coding"

        ExamScreen expects each section dict to have:
            { name, is_coding, questions: [{ id, type, text, options }] }
        """
        sections_raw = bootstrap.get("sections", [])
        sections_ui  = []

        for sec in sections_raw:
            questions_raw = sec.get("questions", [])
            is_coding = any(q.get("type") == "coding" for q in questions_raw)

            # Map server question type to the expected UI widget type.
            _type_map = {
                "mcq":     "mcq",
                "msq":     "msq",
                "text":    "short",      # generic text → short answer
                "fib":     "fillups",
                "short":   "short",
                "long":    "long",
                "numerical": "numerical",
                "coding":  "coding",
            }

            questions_ui = []
            for q in questions_raw:
                srv_type = (q.get("type") or "mcq").lower()
                ui_type  = _type_map.get(srv_type, "short")
                questions_ui.append({
                    "id":      q.get("id"),
                    "type":    ui_type,
                    "text":    q.get("text", ""),
                    "options": q.get("options", []),
                    # Coding metadata forwarded to CodingSection.
                    "title":              q.get("title", ""),
                    "description":        q.get("description", ""),
                    "difficulty":         q.get("difficulty", ""),
                    "supported_languages": q.get("supported_languages", ["python"]),
                    "starter_code":       q.get("starter_code", {}),
                    "constraints":        q.get("constraints", ""),
                    "examples":           q.get("examples", []),
                    "sample_test_cases":  q.get("sample_test_cases", []),
                })

            sections_ui.append({
                "name":       sec.get("title", f"Section {sec.get('order_index', '')}"),
                "is_coding":  is_coding,
                "questions":  questions_ui,
            })

        return {
            "title":              bootstrap.get("title", "Examination"),
            "duration_seconds":   bootstrap.get("duration", 5400),
            "violation_threshold": 30,
            "attempt_id":         bootstrap.get("attempt_id"),
            "exam_id":            bootstrap.get("exam_id"),
            "generation_mode":    bootstrap.get("generation_mode", "static"),
            "is_jit":             bootstrap.get("is_jit", False),
            "sections":           sections_ui,
        }

    def _resolve_question_id(self, key: tuple) -> int | str | None:
        """
        Map (section_idx, q_idx) from ExamScreen._answers to a server question_id.
        """
        try:
            sec_idx, q_idx = key
            sections = self._exam_data.get("sections", [])
            if sec_idx >= len(sections):
                return None
            qs = sections[sec_idx].get("questions", [])
            if q_idx >= len(qs):
                return None
            return qs[q_idx].get("id")
        except (TypeError, ValueError, IndexError):
            return None

    def _total_questions(self) -> int:
        return sum(
            len(sec.get("questions", []))
            for sec in self._exam_data.get("sections", [])
        )