"""
exam.py  (updated) — ExamScreen with server callback hooks.

New vs previous version:
  - Accepts on_save_answer(q_id, answer, question_number, time_taken) callback
    → called immediately on Save & Next so ExamController can POST /v1/exam/answer
  - Accepts on_run_code callback forwarded into CodingSection
  - _save_current_answer(push_to_server=True/False) controls when to fire the callback
  - show_coding_view() feeds real coding questions from exam_data into CodingSection
  - All other UI logic (palette, timer, violation badge, warning bar) unchanged
"""

from __future__ import annotations
import json
import time as _time
import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSplitter, QGridLayout, QStackedWidget, QScrollArea,
    QMessageBox, QLineEdit, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QIntValidator
from typing import Callable, Any

try:
    from core.logger import logger as _AUDIT_LOGGER
except Exception:
    _AUDIT_LOGGER = None

from ui.components.coding_section import CodingSection
from ui.components.mcq_section import MCQSection
from ui.components.msq_section import MSQSection
from ui.components.fillups_section import FillupsSection
from ui.components.short_answer_section import ShortAnswerSection
from ui.components.long_answer_section import LongAnswerSection
from ui.components.numerical_section import NumericalSection


# ─────────────────────────────────────────────────────────────────────────────
# ProctorAlertsWorker - Background thread for polling proctoring alerts
# ─────────────────────────────────────────────────────────────────────────────
class ProctorAlertsWorker(QThread):
    """Background worker to poll proctoring alerts without blocking UI."""
    alerts_received = pyqtSignal(list)           # list of alert messages
    violation_count_updated = pyqtSignal(int)    # violation count
    
    def __init__(self, proctoring_service):
        super().__init__()
        self.proctoring_service = proctoring_service
        self.daemon = True
        self._stop_requested = False

    def stop(self):
        """Request graceful stop of background polling."""
        self._stop_requested = True
    
    def run(self):
        """Run on background thread, emit results via signals."""
        if self.proctoring_service is None or self._stop_requested:
            return
        
        try:
            # Collect alerts and violation count on background thread (non-blocking)
            alerts = (
                self.proctoring_service.collect_alerts() 
                if hasattr(self.proctoring_service, "collect_alerts") 
                else []
            )
            count = (
                int(self.proctoring_service.get_violation_count())
                if hasattr(self.proctoring_service, "get_violation_count")
                else 0
            )
            
            # Emit results - automatically marshalled to main thread by Qt
            if not self._stop_requested:
                self.alerts_received.emit(alerts or [])
                self.violation_count_updated.emit(count)
        except Exception as e:
            print(f"[ProctorAlertsWorker] Error: {e}")
            if not self._stop_requested:
                self.alerts_received.emit([f"Alert poll failed: {e}"])


class ExamScreen(QWidget):
    exam_submitted = pyqtSignal(dict)
    exam_runtime_alert = pyqtSignal(str)
    transition_requested = pyqtSignal(str)
    server_answer_processed = pyqtSignal(dict)

    def __init__(
        self,
        exam_data: dict = None,
        on_save_answer: Callable | None = None,
        on_run_code: Callable | None = None,
    ):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #F8FAFC;")

        self._on_save_answer = on_save_answer
        self._on_run_code    = on_run_code

        self._exam_data              = exam_data or {}
        self._duration               = self._exam_data.get("duration_seconds", 5400)
        self._remaining              = self._duration
        self._violation_count        = 0
        self._violation_threshold    = self._exam_data.get("violation_threshold", 30)
        self._current_section_index  = 0
        self._current_question_index = 0
        self._answers:    dict[tuple, object] = {}
        self._answers_lock = threading.Lock()
        self._review_set: set[tuple]          = set()
        self._review_set_lock = threading.Lock()
        self._q_start_epoch: float            = _time.time()

        self._api_client = None
        self._server_url = None
        self._user_email = None
        self._login_token = None
        self._exam_id = None
        self._attempt_id = None
        self._proctoring_service = None
        self._started_at: float | None = None
        self._critical_violation_threshold = 30
        self._last_alert_message_at: dict[str, float] = {}
        self._last_alert_message_at_lock = threading.Lock()
        self._submission_emitted = False
        self._submit_lock = threading.Lock()
        self._finish_btn: QPushButton | None = None
        self._is_jit_exam = False
        self._is_server_driven_exam = False
        self._jit_confidence: dict[tuple, int] = {}
        self._jit_exam_complete = False
        self._question_activity_seq = 0
        self._question_activity_log: list[dict[str, Any]] = []

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._alert_worker = None
        self._alert_worker_lock = threading.Lock()
        self._alert_timer = QTimer(self)
        self._alert_timer.timeout.connect(self._poll_proctor_alerts_bg)
        self._alert_timer.setInterval(5000)  # Increased from 3s to 5s (still frequent)
        self._warning_hide_timer = QTimer(self)
        self._warning_hide_timer.setSingleShot(True)
        self._warning_hide_timer.timeout.connect(self._hide_warning_bar)
        self.server_answer_processed.connect(self._apply_server_next_question)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._build_header()
        self._build_warning_bar()

        self.content_stack = QStackedWidget()
        self.main_layout.addWidget(self.content_stack, 1)

        self.content_stack.addWidget(self._build_normal_view())

        self.coding_section = CodingSection(on_run_code=on_run_code)
        self.coding_section.back_requested.connect(self.show_normal_view)
        self.coding_section.answer_submitted.connect(self._on_coding_answer_submitted)
        self.content_stack.addWidget(self.coding_section)

        self.content_stack.setCurrentIndex(0)
        self._refresh_question_ui()

    def set_api_client(self, api_client):
        self._api_client = api_client
        if hasattr(self, 'coding_section') and self.coding_section:
            self.coding_section.set_api_client(api_client)

    def set_server_context(self, server_url: str, email: str, login_token: str):
        self._server_url = server_url
        self._user_email = email
        self._login_token = login_token

    def set_exam_session(self, exam_id: int, attempt_id: int):
        self._exam_id = exam_id
        self._attempt_id = attempt_id
        if hasattr(self, 'coding_section') and self.coding_section:
            self.coding_section.set_session_context(attempt_id)

    def set_proctoring_service(self, service):
        self._proctoring_service = service
        if service is not None and hasattr(service, "set_violation_threshold_callback"):
            service.set_violation_threshold_callback(self._on_violation_threshold_reached)

    def start_exam(self, exam_data: dict = None):
        """Called by the main app controller to officially start the exam with valid data."""
        if not exam_data:
            return
        self._exam_data = exam_data
        self._duration = self._exam_data.get("duration_seconds", 5400)
        self._duration = int(self._exam_data.get("duration", self._duration))
        self._remaining = self._duration
        self._violation_threshold = self._exam_data.get("violation_threshold", 30)
        self._current_section_index = 0
        self._current_question_index = 0
        self._answers.clear()
        self._review_set.clear()
        self._jit_confidence.clear()
        self._jit_exam_complete = False
        self._question_activity_log.clear()
        self._question_activity_seq = 0
        self._started_at = _time.time()
        with self._submit_lock:
            self._submission_emitted = False
        if self._finish_btn is not None:
            self._finish_btn.setEnabled(True)
        generation_mode = str(self._exam_data.get("generation_mode") or "").strip().lower()
        exam_mode = str(self._exam_data.get("exam_mode") or "").strip().lower()
        self._is_jit_exam = bool(
            self._exam_data.get("is_jit")
            or self._exam_data.get("jit_enabled")
            or self._exam_data.get("is_jit_exam")
            or ("jit" in generation_mode)
            or ("jit" in exam_mode)
        )
        self._is_server_driven_exam = self._is_jit_exam or ("morph" in generation_mode) or ("morph" in exam_mode)

        if self._is_server_driven_exam and not self._is_jit_exam:
            first_sec_idx = None
            first_question = None
            for i, sec in enumerate(self._exam_data.get("sections", []) or []):
                questions = list(sec.get("questions") or [])
                if questions:
                    first_sec_idx = i
                    first_question = dict(questions[0])
                    break
            for sec in (self._exam_data.get("sections", []) or []):
                sec["questions"] = []
            if first_sec_idx is not None and first_question is not None:
                self._exam_data["sections"][first_sec_idx]["questions"] = [first_question]
                self._current_section_index = first_sec_idx
                self._current_question_index = 0
        
        self._timer_lbl.setText(self._fmt_time(self._remaining))
        self._alert_count_lbl.setText(f"0/{self._violation_threshold}")

        # Replace the dummy normal view constructed in __init__ with the real data view
        old_view = self.content_stack.widget(0)
        self.content_stack.removeWidget(old_view)
        old_view.deleteLater()
        
        new_view = self._build_normal_view()
        self.content_stack.insertWidget(0, new_view)
        self.content_stack.setCurrentIndex(0)
        self._refresh_question_ui()
        self._maybe_switch_to_coding_view()

        # Engage security / proctoring now that the data is loaded (async - non-blocking)
        if self._proctoring_service:
            try:
                from exam_controller import ExamMonitoringStarter  # Late import to avoid circular dependency
                starter = ExamMonitoringStarter(self._proctoring_service)
                starter.monitoring_ready.connect(
                    lambda: print("[ExamScreen] Monitoring started successfully")
                )
                starter.monitoring_failed.connect(
                    lambda err: print(f"[ExamScreen] Monitoring failed: {err}")
                )
                starter.start_async()  # Non-blocking
            except Exception as e:
                print(f"[ExamScreen] Error starting proctoring service: {e}")

        if not self._timer.isActive():
            self._timer.start(1000)
        if not self._alert_timer.isActive():
            self._alert_timer.start()

    def stop_exam_monitoring(self):
        if self._timer.isActive():
            self._timer.stop()
        if self._alert_timer.isActive():
            self._alert_timer.stop()
        self._cleanup_alert_worker()
        if self._proctoring_service:
            try:
                self._proctoring_service.stop_exam_monitoring()
            except Exception as e:
                print(f"[ExamScreen] Error stopping proctoring service: {e}")

    def _on_alert_worker_finished(self, worker: QThread):
        with self._alert_worker_lock:
            if self._alert_worker is worker:
                self._alert_worker = None
        try:
            worker.deleteLater()
        except RuntimeError:
            pass

    def _cleanup_alert_worker(self, wait_ms: int = 1000):
        with self._alert_worker_lock:
            worker = self._alert_worker
            self._alert_worker = None
        if worker is None:
            return
        try:
            if worker.isRunning():
                worker.stop()
                worker.requestInterruption()
                worker.quit()
                worker.wait(wait_ms)
        except RuntimeError:
            return
        try:
            worker.deleteLater()
        except RuntimeError:
            pass

    def _poll_proctor_alerts_bg(self):
        """Start background worker to poll alerts (non-blocking)."""
        if self._proctoring_service is None:
            return
        
        with self._alert_worker_lock:
            existing = self._alert_worker

        if existing is not None:
            try:
                if existing.isRunning():
                    return  # Already polling, skip this cycle
            except RuntimeError:
                with self._alert_worker_lock:
                    if self._alert_worker is existing:
                        self._alert_worker = None
        
        # Create and start new worker
        worker = ProctorAlertsWorker(self._proctoring_service)
        worker.alerts_received.connect(self._on_alerts_received)
        worker.violation_count_updated.connect(self.update_violation_count)
        worker.finished.connect(lambda w=worker: self._on_alert_worker_finished(w))
        with self._alert_worker_lock:
            self._alert_worker = worker
        worker.start()

    def _on_alerts_received(self, alerts: list):
        """Handler called when alerts received (runs on main thread via signal)."""
        now = _time.time()
        for message in alerts or []:
            key = str(message).strip().lower()
            with self._last_alert_message_at_lock:
                last = self._last_alert_message_at.get(key, 0.0)
                if now - last < 5.0:
                    continue
                self._last_alert_message_at[key] = now
            self.show_warning(str(message))
            self.exam_runtime_alert.emit(str(message))
        
        # Check threshold
        if self._proctoring_service is None:
            return
        count = (
            int(self._proctoring_service.get_violation_count())
            if hasattr(self._proctoring_service, "get_violation_count")
            else 0
        )
        if count >= self._critical_violation_threshold:
            self._on_violation_threshold_reached()

    def _poll_proctor_alerts(self):
        if self._proctoring_service is None:
            return
        try:
            alerts = self._proctoring_service.collect_alerts() if hasattr(self._proctoring_service, "collect_alerts") else []
            count = int(self._proctoring_service.get_violation_count()) if hasattr(self._proctoring_service, "get_violation_count") else 0
            self.update_violation_count(count)

            now = _time.time()
            for message in alerts or []:
                key = str(message).strip().lower()
                with self._last_alert_message_at_lock:
                    last = self._last_alert_message_at.get(key, 0.0)
                    if now - last < 5.0:
                        continue
                    self._last_alert_message_at[key] = now
                self.show_warning(str(message))
                self.exam_runtime_alert.emit(str(message))

            if count >= self._critical_violation_threshold:
                self._on_violation_threshold_reached()
        except Exception as e:
            self.exam_runtime_alert.emit(f"Proctor alert poll failed: {e}")

    def _on_violation_threshold_reached(self):
        self.exam_runtime_alert.emit("Critical violation threshold reached. Exam session will be submitted.")
        self._emit_submit_payload()

    # ─── header ───────────────────────────────────────────────────────────────
    def _build_header(self):
        header = QFrame()
        header.setFixedHeight(72)
        header.setStyleSheet("background-color: #FFFFFF; border-bottom: 1px solid #E2E8F0;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(30, 0, 30, 0)
        h_layout.setSpacing(20)

        try:
            from PyQt6.QtSvgWidgets import QSvgWidget
            import os
            p = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "logo.svg"))
            if os.path.exists(p):
                logo = QSvgWidget(p)
                logo.setFixedSize(140, 38)
                logo.setStyleSheet("border: none; background: transparent;")
                h_layout.addWidget(logo)
            else:
                raise FileNotFoundError
        except Exception:
            logo = QLabel("◆ OBSERVE")
            logo.setStyleSheet("color:#0F172A;font-weight:900;font-size:20px;font-family:'Inter','Segoe UI',sans-serif;border:none;")
            h_layout.addWidget(logo)

        h_layout.addStretch()

        # AI Monitor pill
        ai_pill = QFrame()
        ai_pill.setFixedHeight(40)
        ai_pill.setStyleSheet("QFrame{background:transparent;border:1.5px solid #10B981;border-radius:20px;}")
        ai_lyt = QHBoxLayout(ai_pill)
        ai_lyt.setContentsMargins(14, 0, 14, 0)
        ai_lyt.setSpacing(8)
        ai_dot = QLabel("●")
        ai_dot.setStyleSheet("color:#10B981;font-size:10px;border:none;background:transparent;")
        ai_lyt.addWidget(ai_dot)
        ai_lbl = QLabel("AI Monitor Active")
        ai_lbl.setStyleSheet("color:#10B981;font-size:13px;font-weight:600;font-family:'Inter','Segoe UI',sans-serif;border:none;background:transparent;")
        ai_lyt.addWidget(ai_lbl)
        h_layout.addWidget(ai_pill)
        h_layout.addSpacing(8)

        # Alerts badge
        self._alert_box = QFrame()
        self._alert_box.setFixedHeight(40)
        self._alert_box.setStyleSheet("QFrame{background-color:#D1FAE5;border:1.5px solid #10B981;border-radius:10px;}")
        ab_lyt = QHBoxLayout(self._alert_box)
        ab_lyt.setContentsMargins(16, 0, 16, 0)
        ab_lyt.setSpacing(8)
        ab_icon = QLabel("Alerts")
        ab_icon.setStyleSheet("color:#065F46;font-size:13px;font-weight:800;font-family:'Inter','Segoe UI',sans-serif;background:transparent;border:none;")
        self._alert_count_lbl = QLabel(f"0/{self._violation_threshold}")
        self._alert_count_lbl.setStyleSheet("color:#065F46;font-size:13px;font-weight:800;font-family:'Inter','Segoe UI',sans-serif;border:none;background:transparent;")
        ab_lyt.addWidget(ab_icon)
        ab_lyt.addWidget(self._alert_count_lbl)
        h_layout.addWidget(self._alert_box)
        h_layout.addSpacing(8)

        # Timer badge
        time_box = QFrame()
        time_box.setFixedHeight(40)
        time_box.setStyleSheet("QFrame{background-color:#F8FAFC;border:1.5px solid #E2E8F0;border-radius:10px;}")
        tb_lyt = QHBoxLayout(time_box)
        tb_lyt.setContentsMargins(18, 0, 18, 0)
        self._timer_lbl = QLabel(self._fmt_time(self._remaining))
        self._timer_lbl.setStyleSheet("color:#0F172A;font-weight:900;font-size:17px;font-family:'JetBrains Mono',Consolas,monospace;letter-spacing:1.5px;background:transparent;border:none;")
        tb_lyt.addWidget(self._timer_lbl)
        h_layout.addWidget(time_box)
        h_layout.addSpacing(12)

        self._finish_btn = QPushButton("Finish Exam")
        self._finish_btn.setFixedHeight(40)
        self._finish_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._finish_btn.setStyleSheet("QPushButton{background-color:#0F172A;color:white;font-weight:700;border-radius:10px;padding:0px 24px;font-size:14px;font-family:'Inter','Segoe UI',sans-serif;border:none;}QPushButton:hover{background-color:#1E293B;}")
        self._finish_btn.clicked.connect(self._on_finish_exam)
        h_layout.addWidget(self._finish_btn)
        self.main_layout.addWidget(header)

    def _build_warning_bar(self):
        self._warning_bar = QFrame()
        self._warning_bar.setFixedHeight(40)
        self._warning_bar.setStyleSheet("QFrame{background-color:#FEF3C7;border:1px solid #FCD34D;border-radius:6px;margin:5px 10px;}")
        wb_lyt = QHBoxLayout(self._warning_bar)
        wb_lyt.setContentsMargins(15, 0, 15, 0)
        self._warning_lbl = QLabel("")
        self._warning_lbl.setStyleSheet("color:#B45309;font-weight:bold;font-size:13px;border:none;background:transparent;")
        wb_lyt.addWidget(self._warning_lbl)
        wb_lyt.addStretch()
        self._warning_bar.setVisible(False)
        self.main_layout.addWidget(self._warning_bar)

    # ─── normal view (3-panel) ────────────────────────────────────────────────
    def _build_normal_view(self):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background-color:#E2E8F0;width:1px;}")

        # Left – sections
        sec_panel = QFrame()
        sec_panel.setStyleSheet("background-color:#FFFFFF;")
        sp_lyt = QVBoxLayout(sec_panel)
        sp_lyt.setContentsMargins(20, 25, 20, 25)
        sp_lyt.setSpacing(0)
        sec_title = QLabel("SECTIONS")
        sec_title.setStyleSheet("font-size:12px;font-family:'Inter','Segoe UI',sans-serif;font-weight:700;color:#64748B;letter-spacing:1.2px;margin-bottom:15px;")
        sp_lyt.addWidget(sec_title)
        sp_lyt.addSpacing(10)

        self._section_buttons: list[QPushButton] = []
        sections = self._exam_data.get("sections", [])
        for idx, sec in enumerate(sections):
            title = sec.get("title") or sec.get("name") or f"Section {idx+1}"
            btn = QPushButton(title)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("section_idx", idx)
            
            is_coding = sec.get("is_coding", False)
            if "is_coding" not in sec:
                if sec.get("question_type") == "coding":
                    is_coding = True
                else:
                    is_coding = any(self._resolve_question_type(q) == "coding" for q in sec.get("questions", []))
                    
            btn.setProperty("is_coding", is_coding)
            
            if is_coding and not self._is_server_driven_exam:
                btn.clicked.connect(lambda _, i=idx: self.show_coding_view(i))
            else:
                btn.clicked.connect(lambda _, i=idx: self._select_section(i))
            self._section_buttons.append(btn)
            sp_lyt.addWidget(btn)
            sp_lyt.addSpacing(8)
        self._update_sections_ui(0)
        sp_lyt.addStretch()
        splitter.addWidget(sec_panel)

        # Center – questions
        center_panel = QFrame()
        center_panel.setStyleSheet("background-color:#FFFFFF;")
        cp_lyt = QVBoxLayout(center_panel)
        cp_lyt.setContentsMargins(40, 30, 40, 20)
        cp_lyt.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        self.questions_stack = QStackedWidget()
        self._question_widgets: list[QWidget] = []
        
        scroll.setWidget(self.questions_stack)
        cp_lyt.addWidget(scroll, 1)

        nav_lyt = QHBoxLayout()
        nav_lyt.setContentsMargins(0, 16, 0, 0)
        self._prev_btn = QPushButton("← Previous")
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.setStyleSheet("QPushButton{background-color:#FFFFFF;border:1.5px solid #E2E8F0;color:#475569;font-family:'Inter','Segoe UI',sans-serif;font-weight:700;font-size:14px;padding:12px 24px;border-radius:10px;}QPushButton:hover{background-color:#F8FAFC;color:#0F172A;border-color:#CBD5E1;}QPushButton:disabled{background-color:#F1F5F9;color:#CBD5E1;border-color:#E2E8F0;}")
        self._prev_btn.clicked.connect(self._prev_question)

        self._review_btn = QPushButton("🚩 Mark for Review")
        self._review_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._review_btn.setStyleSheet("QPushButton{background-color:#FEF3C7;color:#D97706;font-family:'Inter','Segoe UI',sans-serif;font-weight:700;font-size:14px;padding:12px 24px;border-radius:10px;border:none;}QPushButton:hover{background-color:#FDE68A;color:#B45309;}QPushButton:checked{background-color:#FDE68A;color:#92400E;border:2px solid #F59E0B;}")
        self._review_btn.setCheckable(True)
        self._review_btn.clicked.connect(self._toggle_review)

        self._confidence_label = QLabel("Confidence (1-5)")
        self._confidence_label.setStyleSheet("color:#475569;font-weight:700;font-family:'Inter','Segoe UI',sans-serif;")
        self._confidence_input = QLineEdit()
        self._confidence_input.setFixedWidth(90)
        self._confidence_input.setMaxLength(1)
        self._confidence_input.setValidator(QIntValidator(1, 5, self))
        self._confidence_input.setPlaceholderText("1-5")
        self._confidence_input.setStyleSheet(
            "QLineEdit{background:#FFFFFF;color:#0F172A;border:1.5px solid #CBD5E1;border-radius:8px;padding:8px 10px;font-weight:700;}"
            "QLineEdit:focus{border:1.5px solid #2563EB;}"
        )
        self._confidence_wrap = QFrame()
        conf_lyt = QHBoxLayout(self._confidence_wrap)
        conf_lyt.setContentsMargins(0, 0, 0, 0)
        conf_lyt.setSpacing(8)
        conf_lyt.addWidget(self._confidence_label)
        conf_lyt.addWidget(self._confidence_input)
        self._confidence_wrap.setVisible(False)

        self._next_btn = QPushButton("Save && Next →")
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.setStyleSheet("QPushButton{background-color:#0F172A;color:#FFFFFF;font-family:'Inter','Segoe UI',sans-serif;font-weight:700;font-size:14px;padding:12px 32px;border-radius:10px;border:none;}QPushButton:hover{background-color:#1E293B;}QPushButton:disabled{background-color:#CBD5E1;}")
        self._next_btn.clicked.connect(self._save_and_next)

        nav_lyt.addWidget(self._prev_btn)
        nav_lyt.addStretch()
        nav_lyt.addWidget(self._confidence_wrap)
        nav_lyt.addSpacing(8)
        nav_lyt.addWidget(self._review_btn)
        nav_lyt.addSpacing(15)
        nav_lyt.addWidget(self._next_btn)
        cp_lyt.addLayout(nav_lyt)
        splitter.addWidget(center_panel)

        # Right – overview palette
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color:#F8FAFC;")
        rp_lyt = QVBoxLayout(right_panel)
        rp_lyt.setContentsMargins(20, 20, 20, 20)
        rp_lyt.setSpacing(0)
        rp_title = QLabel("OVERVIEW")
        rp_title.setStyleSheet("font-size:12px;font-family:'Inter','Segoe UI',sans-serif;font-weight:700;color:#64748B;letter-spacing:1.2px;")
        rp_lyt.addWidget(rp_title)
        rp_lyt.addSpacing(16)
        grid_w = QWidget()
        self._palette_grid = QGridLayout(grid_w)
        self._palette_grid.setSpacing(10)
        self._palette_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        rp_lyt.addWidget(grid_w)
        rp_lyt.addStretch()

        leg_w = QWidget()
        leg_lyt = QGridLayout(leg_w)
        leg_lyt.setContentsMargins(0, 0, 0, 0)
        leg_lyt.setSpacing(10)
        for col, (color, text, border) in enumerate([
            ("#22C55E","Answered",None),("#FFFFFF","Unanswered","#CBD5E1"),
            ("#F59E0B","Review",None),("#0F172A","Current",None),
        ]):
            row_lyt = QHBoxLayout()
            box = QFrame()
            box.setFixedSize(13, 13)
            bs = f"border:1px solid {border};" if border else "border:none;"
            box.setStyleSheet(f"background-color:{color};border-radius:3px;{bs}")
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size:12px;font-family:'Inter','Segoe UI',sans-serif;font-weight:600;color:#64748B;")
            row_lyt.addWidget(box)
            row_lyt.addWidget(lbl)
            row_lyt.addStretch()
            leg_lyt.addLayout(row_lyt, col//2, col%2)
        rp_lyt.addWidget(leg_w)
        splitter.addWidget(right_panel)
        splitter.setSizes([210, 720, 240])
        layout.addWidget(splitter)
        
        self._build_question_widgets()
        
        return w

    @staticmethod
    def _to_display_text(value, fallback: str = "") -> str:
        if value is None:
            return fallback
        if isinstance(value, str):
            text = value.strip()
            return text if text else fallback
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict):
                    if item.get("input") is not None or item.get("output") is not None:
                        parts.append(
                            f"Input: {item.get('input', '')}\nExpected: {item.get('output', item.get('expected_output', ''))}"
                        )
                    else:
                        parts.append(" ".join(str(v) for v in item.values()))
                else:
                    parts.append(str(item))
            return "\n".join(p for p in parts if p).strip() or fallback
        if isinstance(value, dict):
            return "\n".join(f"{k}: {v}" for k, v in value.items())
        return str(value)

    def _section_questions(self, sec_idx: int) -> list[dict]:
        try:
            section = self._exam_data.get("sections", [])[sec_idx]
        except Exception:
            return []
        return list(section.get("questions") or [])

    def _is_coding_section(self, sec_idx: int) -> bool:
        try:
            section = self._exam_data.get("sections", [])[sec_idx]
        except Exception:
            return False
        if section.get("is_coding"):
            return True
        if section.get("question_type") == "coding":
            return True
        return any(self._resolve_question_type(q) == "coding" for q in (section.get("questions") or []))

    @staticmethod
    def _resolve_question_type(question: dict) -> str:
        raw = (
            question.get("type")
            or question.get("question_type")
            or question.get("qtype")
            or "short"
        )
        value = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "fib": "fillups",
            "fill": "fillups",
            "fillup": "fillups",
            "mcq": "mcq",
            "msq": "msq",
            "coding": "coding",
        }
        return aliases.get(value, value)

    def _next_section_index_for_auto_move(self) -> int | None:
        if self._is_jit_exam:
            return None
        sections = self._exam_data.get("sections", []) or []
        nxt = self._current_section_index + 1
        if nxt >= len(sections):
            return None
        return nxt

    def _current_confidence_value(self) -> int | None:
        raw = (self._confidence_input.text() or "").strip()
        if raw.isdigit():
            value = int(raw)
            if 1 <= value <= 5:
                return value
        return None

    # ─── question widgets ─────────────────────────────────────────────────────
    def _build_question_widgets(self):
        while self.questions_stack.count():
            w = self.questions_stack.widget(0)
            self.questions_stack.removeWidget(w)
            w.deleteLater()
        self._question_widgets.clear()

        sections = self._exam_data.get("sections", [])
        sec_idx  = self._current_section_index
        if sec_idx < len(sections) and sections[sec_idx].get("is_coding") and not self._is_server_driven_exam:
            self._rebuild_palette()
            return

        questions = (sections[sec_idx]["questions"]
                     if sec_idx < len(sections) and "questions" in sections[sec_idx]
                     else [])
        if not questions:
            lbl = QLabel("No questions available in this section.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #64748B; font-size: 16px; font-weight: bold;")
            self.questions_stack.addWidget(lbl)
            self._question_widgets.append(lbl)
        else:
            def _option_text(opt) -> str:
                if isinstance(opt, dict):
                    return self._to_display_text(
                        opt.get("text")
                        or opt.get("option")
                        or opt.get("label")
                        or opt.get("value")
                        or ""
                    )
                return self._to_display_text(opt)

            _type_map = {
                "mcq":       lambda q: MCQSection(self._to_display_text(q.get("text", q.get("question", ""))), [_option_text(o) for o in (q.get("options") or [])]),
                "msq":       lambda q: MSQSection(self._to_display_text(q.get("text", q.get("question", ""))), [_option_text(o) for o in (q.get("options") or [])]),
                "fillups":   lambda q: FillupsSection(self._to_display_text(q.get("text", q.get("question", ""))),),
                "short":     lambda q: ShortAnswerSection(self._to_display_text(q.get("text", q.get("question", ""))),),
                "long":      lambda q: LongAnswerSection(self._to_display_text(q.get("text", q.get("question", ""))),),
                "numerical": lambda q: NumericalSection(self._to_display_text(q.get("text", q.get("question", ""))),),
                "fill":      lambda q: FillupsSection(self._to_display_text(q.get("text", q.get("question", ""))),),
                "fillup":    lambda q: FillupsSection(self._to_display_text(q.get("text", q.get("question", ""))),),
                "fill_blank": lambda q: FillupsSection(self._to_display_text(q.get("text", q.get("question", ""))),),
                "fill_in_blank": lambda q: FillupsSection(self._to_display_text(q.get("text", q.get("question", ""))),),
                "short_answer": lambda q: ShortAnswerSection(self._to_display_text(q.get("text", q.get("question", ""))),),
                "long_answer": lambda q: LongAnswerSection(self._to_display_text(q.get("text", q.get("question", ""))),),
                "numeric":   lambda q: NumericalSection(self._to_display_text(q.get("text", q.get("question", ""))),),
                "fib":       lambda q: FillupsSection(self._to_display_text(q.get("text", q.get("question", ""))),),
            }
            for q_idx, q in enumerate(questions):
                q_type = self._resolve_question_type(q)
                if q_type == "coding":
                    continue
                if q_type == "msq" and q.get("multi_select") is False:
                    q_type = "mcq"
                factory = _type_map.get(
                    q_type,
                    lambda qq: ShortAnswerSection(self._to_display_text(qq.get("text", qq.get("question", "")))),
                )
                widget  = factory(q)
                self.questions_stack.addWidget(widget)
                self._question_widgets.append(widget)
                # Process events every 5 widgets to prevent UI freeze
                if (q_idx + 1) % 5 == 0:
                    QApplication.processEvents()
        self._rebuild_palette()

    def _rebuild_palette(self):
        while self._palette_grid.count():
            item = self._palette_grid.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        
        n = self.questions_stack.count()
        for i in range(n):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(40, 40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._jump_to_question(idx))
            self._palette_grid.addWidget(btn, i//4, i%4)
            # Process events every 10 buttons to prevent UI freeze
            if (i + 1) % 10 == 0:
                QApplication.processEvents()
        
        self._update_palette_ui()

    # ─── navigation ───────────────────────────────────────────────────────────
    def _prev_question(self):
        if self._current_question_index > 0:
            self._jump_to_question(self._current_question_index - 1)

    def _save_and_next(self):
        saved = self._save_current_answer(push_to_server=True, action="save_and_next")
        if saved is False:
            return

        if self._is_server_driven_exam:
            if self._jit_exam_complete:
                self.show_warning("All questions are completed. Click Finish Exam to submit.")
            return

        cnt = self.questions_stack.count()
        if self._current_question_index < cnt - 1:
            self._jump_to_question(self._current_question_index + 1)
            return

        next_section = self._next_section_index_for_auto_move()
        if next_section is not None:
            self._select_section(next_section)
            return

    def _jump_to_question(self, index: int):
        saved = self._save_current_answer(push_to_server=False, action="question_navigate")
        if saved is False:
            return
        self._current_question_index = index
        self.questions_stack.setCurrentIndex(index)
        self._q_start_epoch = _time.time()
        # Defer UI refresh to prevent blocking on button click
        QTimer.singleShot(0, self._refresh_question_ui)

    def _select_section(self, index: int):
        if self._is_jit_exam:
            self.show_warning("Section switching is disabled for JIT exams.")
            return
        if index == self._current_section_index:
            return
        saved = self._save_current_answer(push_to_server=False, action="section_navigate")
        if saved is False:
            return
        self._current_section_index  = index
        self._current_question_index = 0
        self._update_sections_ui(index)
        if self._is_coding_section(index):
            self.show_coding_view(section_index=index)
            return
        # Defer widget building to prevent blocking on section switch click
        QTimer.singleShot(0, lambda: self._build_and_refresh_questions())

    def _toggle_review(self, checked: bool):
        key = (self._current_section_index, self._current_question_index)
        with self._review_set_lock:
            if checked:
                self._review_set.add(key)
            else:
                self._review_set.discard(key)
        # Defer palette update to prevent blocking
        QTimer.singleShot(0, self._update_palette_ui)

    def _build_and_refresh_questions(self):
        """Build question widgets and refresh UI (called via QTimer.singleShot for responsiveness)"""
        self._build_question_widgets()
        self._refresh_question_ui()

    # ─── answer persistence ───────────────────────────────────────────────────
    def _save_current_answer(self, *, push_to_server: bool = False, enforce_jit_confidence: bool = True, action: str = "save"):
        idx = self.questions_stack.currentIndex()
        if idx < 0 or idx >= len(self._question_widgets):
            return True
        widget = self._question_widgets[idx]
        if not hasattr(widget, "get_answer"):
            return True
        ans = widget.get_answer()
        key = (self._current_section_index, idx)

        confidence = None
        if self._is_jit_exam:
            confidence = self._current_confidence_value()
            if enforce_jit_confidence and ans not in (None, "", []) and confidence is None:
                self.show_warning("JIT exam requires confidence level (1-5) before Save & Next.")
                self.exam_runtime_alert.emit("Missing confidence level for JIT answer")
                return False

        # Store answer if provided
        if ans not in (None, "", []):
            with self._answers_lock:
                self._answers[key] = ans
            if confidence is not None:
                self._jit_confidence[key] = confidence
            else:
                self._jit_confidence.pop(key, None)
        else:
            with self._answers_lock:
                self._answers.pop(key, None)
            self._jit_confidence.pop(key, None)

        q_id = self._get_question_id(self._current_section_index, idx)
        elapsed_seconds = max(0, int(_time.time() - self._q_start_epoch))
        answer_kind = type(ans).__name__ if ans is not None else "NoneType"
        answer_size = len(str(ans)) if ans not in (None, "") else 0
        self._log_question_activity(
            action=action,
            sec_idx=self._current_section_index,
            q_idx=idx,
            question_id=q_id,
            time_on_question_sec=elapsed_seconds,
            answered=(ans not in (None, "", [])),
            pushed_to_server=bool(push_to_server),
            answer_kind=answer_kind,
            answer_size=answer_size,
            confidence=confidence,
        )

        # For morphing exams: allow pushing empty/null answers to server
        # For JIT exams: only push if answer is provided
        should_push_to_server = push_to_server
        if push_to_server:
            # If answer is empty and this is a morphing exam, still push null answer to server
            # This allows users to skip questions and move to the next one
            if ans in (None, "", []) and not self._is_jit_exam and self._is_server_driven_exam:
                # For morphing morphing exams, allow empty/null answers to be pushed
                should_push_to_server = True
            elif ans not in (None, "", []):
                # For any exam with an answer, push to server
                should_push_to_server = True
            else:
                # For JIT exams with empty answers, don't push
                should_push_to_server = False

        if should_push_to_server:
            if q_id is not None:
                time_taken = int(_time.time() - self._q_start_epoch)
                self._persist_answer_async(
                    q_id,
                    ans,  # Can be None/empty for morphing exams
                    time_taken=time_taken,
                    question_number=idx+1,
                    confidence=confidence,
                )
                # Response processing happens in background thread now (non-blocking)
                if self._on_save_answer and ans not in (None, "", []):
                    self._on_save_answer(q_id, ans, question_number=idx+1, time_taken=time_taken)
        
        return True

    def _persist_answer_async(self, question_id, answer, time_taken: int = 0, question_number: int = 0, confidence: int | None = None):
        if not self._api_client or not self._exam_id or not self._attempt_id:
            return None

        def _send():
            try:
                response = self._api_client.save_answer(
                    attempt_id=self._attempt_id,
                    exam_id=self._exam_id,
                    question_id=question_id,
                    answer=answer,
                    confidence=confidence,
                    time_taken_seconds=time_taken,
                    question_number=question_number,
                    timeout=8.0
                )
                # For server-driven exams, process the response on background thread
                if self._is_server_driven_exam:
                    try:
                        if isinstance(response, dict):
                            self.server_answer_processed.emit(dict(response))
                    except Exception as e:
                        print(f"[ExamScreen] Failed to apply server response: {e}")
            except Exception as e:
                print(f"[ExamScreen] Background answer sync failed: {e}")
                
        import threading
        threading.Thread(target=_send, daemon=True).start()
        return None

    def _ensure_section_index(self, section_id, section_title: str) -> int:
        sections = self._exam_data.setdefault("sections", [])
        if section_id is not None:
            for idx, sec in enumerate(sections):
                try:
                    if int(sec.get("id") or -1) == int(section_id):
                        return idx
                except Exception:
                    pass
        if section_title:
            for idx, sec in enumerate(sections):
                if str(sec.get("title") or "").strip().lower() == str(section_title).strip().lower():
                    return idx

        sections.append({
            "id": section_id,
            "title": section_title or f"Section {len(sections) + 1}",
            "questions": [],
            "is_coding": False,
        })
        return len(sections) - 1

    def _apply_server_next_question(self, response_payload):
        if not isinstance(response_payload, dict):
            return

        self._jit_exam_complete = bool(response_payload.get("exam_complete"))

        # Show evaluation feedback in warning bar after each JIT answer
        evaluation = response_payload.get("evaluation") or {}
        if evaluation:
            status = str(evaluation.get("status") or "").upper()
            score_pct = int(float(evaluation.get("score") or 0) * 100)
            feedback = str(evaluation.get("feedback") or "")
            status_icons = {"CORRECT": "✓", "PARTIAL": "~", "WRONG": "✗", "SKIPPED": "-"}
            icon = status_icons.get(status, "?")
            msg = f"{icon} {status} ({score_pct}%)"
            if feedback:
                msg += f" — {feedback[:120]}"
            # self.show_warning(msg)

        # Show final report when section/exam completes
        if self._jit_exam_complete:
            final_report = response_payload.get("final_report") or {}
            if final_report:
                accuracy = final_report.get("accuracy", 0)
                skill    = final_report.get("skill_label", "")
                correct  = final_report.get("correct", 0)
                total    = final_report.get("total_questions", 0)
                # self.show_warning(
                #     f"Section complete — Score: {accuracy}% | {correct}/{total} correct | Skill: {skill}"
                # )

        next_question = response_payload.get("next_question")
        if not isinstance(next_question, dict) or not next_question.get("id"):
            return

        section_id = response_payload.get("section_id")
        section_title = str(response_payload.get("section_title") or next_question.get("_section_title") or "Section")
        sec_idx = self._ensure_section_index(section_id, section_title)

        sections = self._exam_data.get("sections", [])
        if sec_idx >= len(sections):
            return
        section = sections[sec_idx]
        questions = section.setdefault("questions", [])
        if self._resolve_question_type(next_question) == "coding":
            section["is_coding"] = True

        next_qid = str(next_question.get("id"))
        q_index = None
        for i, existing in enumerate(questions):
            if str(existing.get("id")) == next_qid:
                questions[i] = dict(next_question)
                q_index = i
                break
        if q_index is None:
            questions.append(dict(next_question))
            q_index = len(questions) - 1

        self._current_section_index = sec_idx
        self._current_question_index = q_index
        self._build_question_widgets()
        self.questions_stack.setCurrentIndex(self._current_question_index)
        self._q_start_epoch = _time.time()
        self._refresh_question_ui()
        self._maybe_switch_to_coding_view()

    def _get_question_id(self, sec_idx: int, q_idx: int):
        try:
            return self._exam_data["sections"][sec_idx]["questions"][q_idx].get("id")
        except (IndexError, KeyError):
            return None

    def _restore_answer(self, q_idx: int):
        if q_idx < 0 or q_idx >= len(self._question_widgets):
            return
        widget = self._question_widgets[q_idx]
        if hasattr(widget, "set_answer"):
            with self._answers_lock:
                ans = self._answers.get((self._current_section_index, q_idx))
            widget.set_answer(ans)
        if self._is_jit_exam:
            saved_conf = self._jit_confidence.get((self._current_section_index, q_idx))
            self._confidence_input.setText(str(saved_conf) if saved_conf is not None else "")
        else:
            self._confidence_input.clear()

    def _on_coding_answer_submitted(self, code: str):
        coding_index = 0
        submitted_question_id = None
        confidence = None
        parsed_code = code
        try:
            parsed = json.loads(code) if isinstance(code, str) else None
            if isinstance(parsed, dict):
                parsed_code = str(parsed.get("source_code") or parsed.get("code") or "")
                coding_index = int(parsed.get("question_index") or 0)
                submitted_question_id = parsed.get("question_id")
                conf_raw = parsed.get("confidence")
                if conf_raw is not None:
                    conf_value = int(conf_raw)
                    if 1 <= conf_value <= 5:
                        confidence = conf_value
        except Exception:
            parsed_code = code

        sec_idx = self._current_section_index
        coding_q_idx = coding_index
        if submitted_question_id is not None:
            sections = self._exam_data.get("sections", []) or []
            if 0 <= sec_idx < len(sections):
                section_questions = list(sections[sec_idx].get("questions") or [])
                matched_index = next((i for i, q in enumerate(section_questions) if str(q.get("id")) == str(submitted_question_id)), None)
                if matched_index is not None:
                    coding_q_idx = matched_index
        if coding_q_idx < 0:
            coding_q_idx = 0

        key = (sec_idx, coding_q_idx)
        with self._answers_lock:
            self._answers[key] = parsed_code

        if self._is_jit_exam:
            if confidence is None and hasattr(self.coding_section, "get_confidence_value"):
                confidence = self.coding_section.get_confidence_value()
            if confidence is not None:
                self._jit_confidence[key] = confidence
            else:
                self._jit_confidence.pop(key, None)

        if self._is_server_driven_exam:
            qid = self._get_question_id(sec_idx, coding_q_idx)
            if qid is not None:
                time_taken = int(_time.time() - self._q_start_epoch)
                self._log_question_activity(
                    action="coding_submit",
                    sec_idx=sec_idx,
                    q_idx=coding_q_idx,
                    question_id=qid,
                    time_on_question_sec=time_taken,
                    answered=bool(parsed_code.strip()),
                    pushed_to_server=True,
                    answer_kind="str",
                    answer_size=len(parsed_code or ""),
                    confidence=confidence,
                )
                self._persist_answer_async(
                    qid,
                    parsed_code,
                    time_taken=time_taken,
                    question_number=coding_q_idx + 1,
                    confidence=confidence,
                )
                # Response processing happens in background thread now (non-blocking)

    # ─── UI refresh ───────────────────────────────────────────────────────────
    def _refresh_question_ui(self):
        n   = self.questions_stack.count()
        idx = self._current_question_index
        self._prev_btn.setEnabled((not self._is_jit_exam) and idx > 0)
        self._next_btn.setEnabled(n > 0)
        key = (self._current_section_index, idx)
        with self._review_set_lock:
            is_review = key in self._review_set
        self._review_btn.setChecked(is_review)
        self._confidence_wrap.setVisible(self._is_jit_exam)
        self._restore_answer(idx)
        self._update_palette_ui()
        self._update_sections_ui(self._current_section_index)

    def _update_sections_ui(self, active: int):
        for i, btn in enumerate(self._section_buttons):
            is_coding = btn.property("is_coding")
            btn.setEnabled((not self._is_jit_exam) or (i == active))
            if i == active and not is_coding:
                btn.setStyleSheet("QPushButton{text-align:left;padding:14px 20px;border-radius:10px;font-size:15px;font-family:'Inter','Segoe UI',sans-serif;font-weight:700;background-color:#0F172A;color:#FFFFFF;border:2px solid #0F172A;margin-bottom:8px;}")
            elif is_coding:
                btn.setStyleSheet("QPushButton{text-align:left;padding:14px 20px;border-radius:10px;font-size:15px;font-family:'Inter','Segoe UI',sans-serif;font-weight:500;background-color:#F8FAFC;color:#475569;border:1.5px solid #E2E8F0;margin-bottom:8px;}QPushButton:hover{background-color:#F1F5F9;color:#0F172A;border-color:#CBD5E1;}")
            else:
                btn.setStyleSheet("QPushButton{text-align:left;padding:14px 20px;border-radius:10px;font-size:15px;font-family:'Inter','Segoe UI',sans-serif;font-weight:500;background-color:#F8FAFC;color:#475569;border:2px solid #E2E8F0;margin-bottom:8px;}QPushButton:hover{background-color:#F1F5F9;color:#0F172A;border-color:#CBD5E1;}")

    def _update_palette_ui(self):
        for i in range(self._palette_grid.count()):
            item = self._palette_grid.itemAt(i)
            if not item:
                continue
            btn = item.widget()
            if not btn:
                continue
            key        = (self._current_section_index, i)
            is_current  = i == self._current_question_index
            with self._review_set_lock:
                is_review = key in self._review_set
            with self._answers_lock:
                is_answered = key in self._answers
            if is_current:
                s = "background-color:#0F172A;color:white;border-radius:8px;font-family:'Inter','Segoe UI',sans-serif;font-weight:800;font-size:14px;border:2px solid #0F172A;"
            elif is_review:
                s = "background-color:#F59E0B;color:white;border-radius:8px;font-family:'Inter','Segoe UI',sans-serif;font-weight:800;font-size:14px;border:none;"
            elif is_answered:
                s = "background-color:#22C55E;color:white;border-radius:8px;font-family:'Inter','Segoe UI',sans-serif;font-weight:800;font-size:14px;border:none;"
            else:
                s = "background-color:#FFFFFF;color:#64748B;border:1.5px solid #CBD5E1;border-radius:8px;font-family:'Inter','Segoe UI',sans-serif;font-weight:700;font-size:14px;"
            btn.setStyleSheet(s)
            # Process events every 10 buttons to prevent UI freeze
            if (i + 1) % 10 == 0:
                QApplication.processEvents()

    # ─── coding view ──────────────────────────────────────────────────────────
    def show_coding_view(self, section_index: int | None = None):
        sec_idx = self._current_section_index if section_index is None else section_index
        sections = self._exam_data.get("sections", []) or []
        if sec_idx < 0 or sec_idx >= len(sections):
            return

        sec = sections[sec_idx]
        raw_questions = list(sec.get("questions") or [])
        coding_questions = [q for q in raw_questions if self._resolve_question_type(q) == "coding"]
        if not coding_questions and raw_questions:
            coding_questions = raw_questions

        if coding_questions:
            active_exam_question = raw_questions[self._current_question_index] if (0 <= self._current_question_index < len(raw_questions)) else None
            active_question_id = str(active_exam_question.get("id")) if isinstance(active_exam_question, dict) else ""
            coding_active_index = 0
            if active_question_id:
                for idx, cq in enumerate(coding_questions):
                    if str(cq.get("id")) == active_question_id:
                        coding_active_index = idx
                        break

            self.coding_section.set_questions(coding_questions, active_index=coding_active_index)
            if hasattr(self.coding_section, "set_confidence_visible"):
                self.coding_section.set_confidence_visible(self._is_jit_exam)
            if self._is_jit_exam and hasattr(self.coding_section, "set_confidence_value"):
                key = (sec_idx, self._current_question_index)
                self.coding_section.set_confidence_value(self._jit_confidence.get(key))

        self._current_section_index = sec_idx
        self.content_stack.setCurrentIndex(1)

    def show_normal_view(self):
        self.content_stack.setCurrentIndex(0)
        self._update_sections_ui(self._current_section_index)

    def _maybe_switch_to_coding_view(self):
        sections = self._exam_data.get("sections", []) or []
        if self._current_section_index < 0 or self._current_section_index >= len(sections):
            self.show_normal_view()
            return

        questions = list(sections[self._current_section_index].get("questions") or [])
        if self._current_question_index < 0 or self._current_question_index >= len(questions):
            self.show_normal_view()
            return

        q = questions[self._current_question_index]
        if self._resolve_question_type(q) == "coding":
            self.show_coding_view(self._current_section_index)
        else:
            self.show_normal_view()

    # ─── timer ────────────────────────────────────────────────────────────────
    def _tick(self):
        if self._remaining > 0:
            self._remaining -= 1
            self._timer_lbl.setText(self._fmt_time(self._remaining))
            if self._remaining == 0:
                self._on_time_up()

    @staticmethod
    def _fmt_time(secs: int) -> str:
        secs = max(0, secs)
        h, rem = divmod(secs, 3600)
        m, s   = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _on_time_up(self):
        self._timer.stop()
        self._save_current_answer(push_to_server=True)
        from ui.components.premium_popup import PremiumPopup
        from PyQt6.QtWidgets import QMessageBox as _QMB
        PremiumPopup.show_message(
            parent=self,
            title="Time's Up",
            message="Examination time has ended. Your answers have been saved.",
            icon=_QMB.Icon.Information,
            buttons=_QMB.StandardButton.Ok
        )
        self._emit_submit_payload()

    def _serialize_submit_answer(self, answer) -> str:
        if isinstance(answer, str):
            return answer
        if isinstance(answer, list):
            return json.dumps(answer, ensure_ascii=True)
        if isinstance(answer, dict):
            return json.dumps(answer, ensure_ascii=True, sort_keys=True, default=str)
        return str(answer)

    def _get_coding_question_id(self, coding_index: int = 0):
        seen = -1
        for sec in self._exam_data.get("sections", []):
            questions = sec.get("questions", []) or []
            for q in questions:
                if str(q.get("type", "")).lower() == "coding":
                    seen += 1
                    if seen == coding_index:
                        return q.get("id")
        return None

    def _resolve_question_id_for_key(self, key):
        if not isinstance(key, tuple) or len(key) != 2:
            return None

        sec_idx, q_idx = key
        if sec_idx == "coding":
            try:
                coding_pos = int(q_idx)
            except Exception:
                coding_pos = 0
            return self._get_coding_question_id(coding_pos)

        try:
            return self._get_question_id(int(sec_idx), int(q_idx))
        except Exception:
            return None

    def _build_answers_payload(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        with self._answers_lock:
            for key, answer in list(self._answers.items()):
                if answer in (None, "", []):
                    continue
                qid = self._resolve_question_id_for_key(key)
                if qid is None:
                    continue
                payload[str(qid)] = self._serialize_submit_answer(answer)
        return payload

    def _capture_coding_draft_for_submission(self) -> None:
        """Capture latest coding editor draft so Finish Exam includes the newest code."""
        if not hasattr(self, "coding_section") or self.coding_section is None:
            return
        if not hasattr(self.coding_section, "get_submission_data"):
            return
        try:
            data = self.coding_section.get_submission_data() or {}
            source_code = str(data.get("source_code") or "")
            if not source_code.strip():
                return
            coding_index = 0
            if hasattr(self.coding_section, "get_current_question_index"):
                coding_index = int(self.coding_section.get_current_question_index())
            key = (self._current_section_index, max(0, coding_index))
            with self._answers_lock:
                self._answers[key] = source_code
        except Exception:
            # Keep finish flow resilient even if coding view is unavailable.
            return

    def closeEvent(self, event):
        """Cleanup all timers and background workers when widget closed."""
        try:
            self.stop_exam_monitoring()
        except Exception:
            pass
        super().closeEvent(event)

    def _emit_submit_payload(self):
        with self._submit_lock:
            if self._submission_emitted:
                return
            self._submission_emitted = True
            if self._finish_btn is not None:
                self._finish_btn.setEnabled(False)
        self.stop_exam_monitoring()
        submission = self.get_all_answers()
        self.exam_submitted.emit(submission)
        self.transition_requested.emit("submit")

    # ─── violations ───────────────────────────────────────────────────────────
    def update_violation_count(self, count: int):
        self._violation_count = count
        self._alert_count_lbl.setText(f"{count}/{self._violation_threshold}")
        t = self._violation_threshold
        if count >= t:
            bg, border, text = "#FEE2E2", "#DC2626", "#7F1D1D"
        elif count >= t * 0.7:
            bg, border, text = "#FED7AA", "#EA580C", "#7C2D12"
        elif count >= t * 0.4:
            bg, border, text = "#FEF3C7", "#F59E0B", "#92400E"
        else:
            bg, border, text = "#D1FAE5", "#10B981", "#065F46"
        self._alert_box.setStyleSheet(f"QFrame{{background-color:{bg};border:1.5px solid {border};border-radius:10px;}}")
        self._alert_count_lbl.setStyleSheet(f"color:{text};font-size:13px;font-weight:800;font-family:'Inter','Segoe UI',sans-serif;border:none;background:transparent;")

    def show_warning(self, message: str):
        text = str(message or "").strip()
        if not text:
            self._warning_hide_timer.stop()
            self._warning_lbl.setText("")
            self._warning_bar.setVisible(False)
            return

        self._warning_lbl.setText(text)
        self._warning_bar.setVisible(True)
        # Each incoming alert gets a fresh 2-second visibility window.
        self._warning_hide_timer.start(2000)

    def _hide_warning_bar(self):
        self._warning_lbl.setText("")
        self._warning_bar.setVisible(False)

    # ─── finish exam ──────────────────────────────────────────────────────────
    def _on_finish_exam(self):
        with self._submit_lock:
            if self._submission_emitted:
                return

        if (
            hasattr(self, "coding_section")
            and self.coding_section is not None
            and hasattr(self.coding_section, "has_pending_operation")
            and self.coding_section.has_pending_operation()
        ):
            self.show_warning("Please wait for Run/Submit to finish before ending the exam.")
            return

        self._capture_coding_draft_for_submission()
        saved = self._save_current_answer(push_to_server=True, enforce_jit_confidence=False, action="finish_exam")
        if saved is False:
            return
        answered = len(self._answers)
        total    = self.questions_stack.count()
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Finish Exam")
        dialog.setText(f"You have answered {answered} of {total} question(s).")
        dialog.setInformativeText("Are you sure you want to submit?")
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        dialog.setStyleSheet(
            "QMessageBox{background:#FFFFFF;}"
            "QMessageBox QLabel{color:#0F172A;font-size:13px;}"
            "QPushButton{background:#1D4ED8;color:#FFFFFF;border:none;border-radius:6px;padding:8px 16px;font-weight:700;min-width:90px;}"
            "QPushButton:hover{background:#1E40AF;}"
        )
        reply = dialog.exec()
        if reply == QMessageBox.StandardButton.Yes:
            self._emit_submit_payload()

    def get_all_answers(self) -> dict:
        self._capture_coding_draft_for_submission()
        self._save_current_answer(push_to_server=False, action="collect_submit")
        duration = int(_time.time() - self._started_at) if self._started_at else 0
        answers = self._build_answers_payload()
        total_questions = 0
        for sec in self._exam_data.get("sections", []):
            total_questions += len(sec.get("questions", []) or [])
        return {
            "answers": answers,
            "duration": duration,
            "sections": len(self._exam_data.get("sections", [])),
            "total_questions": total_questions,
            "exam_id": self._exam_id,
            "attempt_id": self._attempt_id,
            "question_activity_count": len(self._question_activity_log),
            "question_activity": list(self._question_activity_log[-200:]),
        }

    def _question_meta(self, sec_idx: int, q_idx: int) -> dict[str, Any]:
        section_title = ""
        question_type = "unknown"
        question_number = int(q_idx) + 1
        try:
            sections = self._exam_data.get("sections", []) or []
            if 0 <= sec_idx < len(sections):
                sec = sections[sec_idx] or {}
                section_title = str(sec.get("title") or sec.get("name") or "")
                questions = sec.get("questions", []) or []
                if 0 <= q_idx < len(questions):
                    q = questions[q_idx] or {}
                    question_type = self._resolve_question_type(q)
        except Exception:
            pass
        return {
            "section_title": section_title,
            "question_type": question_type,
            "question_number": question_number,
        }

    def _log_question_activity(
        self,
        *,
        action: str,
        sec_idx: int,
        q_idx: int,
        question_id: Any,
        time_on_question_sec: int,
        answered: bool,
        pushed_to_server: bool,
        answer_kind: str,
        answer_size: int,
        confidence: int | None,
    ) -> None:
        self._question_activity_seq += 1
        meta = self._question_meta(sec_idx, q_idx)
        payload = {
            "event_seq": self._question_activity_seq,
            "event_ts": int(_time.time()),
            "exam_id": self._exam_id,
            "attempt_id": self._attempt_id,
            "action": str(action),
            "section_index": int(sec_idx),
            "section_title": meta.get("section_title", ""),
            "question_index": int(q_idx),
            "question_number": int(meta.get("question_number") or (q_idx + 1)),
            "question_id": question_id,
            "question_type": meta.get("question_type", "unknown"),
            "time_on_question_sec": int(max(0, time_on_question_sec)),
            "answered": bool(answered),
            "pushed_to_server": bool(pushed_to_server),
            "answer_kind": str(answer_kind),
            "answer_size": int(max(0, answer_size)),
            "confidence": confidence,
            "is_jit_exam": bool(self._is_jit_exam),
        }
        self._question_activity_log.append(payload)
        if len(self._question_activity_log) > 2000:
            self._question_activity_log = self._question_activity_log[-2000:]

        line = f"QUESTION_ACTIVITY {json.dumps(payload, ensure_ascii=True, sort_keys=True)}"
        # Log asynchronously on background thread to avoid UI blocking
        threading.Thread(target=self._log_activity_async, args=(line, payload), daemon=True).start()

    def _log_activity_async(self, line: str, payload: dict) -> None:
        """Log activity to audit logger on background thread (non-blocking)."""
        if _AUDIT_LOGGER is not None:
            try:
                _AUDIT_LOGGER.info(line, telemetry=payload, module="exam_screen")
                return
            except Exception:
                pass
        print(f"[Exam] {line}")