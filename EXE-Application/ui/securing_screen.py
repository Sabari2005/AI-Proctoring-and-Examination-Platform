"""Environment-securing progress screen shown before exam launch.

Displays real-time status while network, monitoring, and evidence subsystems
are prepared for the upcoming exam session.
"""

import os
import time
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QProgressBar, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont

try:
    from PyQt6.QtSvgWidgets import QSvgWidget
    _SVG_AVAILABLE = True
except ImportError:
    _SVG_AVAILABLE = False


# Theme constants.
BG_WHITE = "#FFFFFF"
TEXT_BLACK = "#0F172A"
TEXT_GREY = "#64748B"
BORDER_LIGHT = "#E2E8F0"
ACCENT_BLUE_VIOLET = "#6366F1"


# Security initialization worker.

class SecurityInitializationWorker(QThread):
    """Background thread that initializes security features with progress reporting."""
    
    progress_update = pyqtSignal(int, str)
    initialization_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, proctoring_service, exam_data=None):
        super().__init__()
        self.proctoring_service = proctoring_service
        self.exam_data = exam_data or {}
        self._stop_event = threading.Event()

    def _sleep_interruptible(self, seconds: float) -> bool:
        """Sleep for up to `seconds`, returning False when stop/interruption is requested."""
        end_ts = time.monotonic() + max(0.0, float(seconds))
        while time.monotonic() < end_ts:
            if self._stop_event.is_set() or self.isInterruptionRequested():
                return False
            remaining = end_ts - time.monotonic()
            time.sleep(min(0.1, max(0.0, remaining)))
        return True

    def stop(self):
        self._stop_event.set()
        self.requestInterruption()
    
    def run(self):
        """Execute security initialization sequence with progress updates."""
        try:
            # Step 1: Network isolation preflight (activation occurs at exam start).
            self.progress_update.emit(10, "Starting network isolation...")
            if not self._sleep_interruptible(0.5):
                return
            
            if self.proctoring_service and self.proctoring_service.firewall:
                try:
                    if self.proctoring_service.firewall._is_admin():
                        self.progress_update.emit(25, "Network isolation ready ✓")
                    else:
                        self.progress_update.emit(25, "Network isolation: admin privileges unavailable")
                except Exception as e:
                    self.progress_update.emit(25, f"Network isolation warning: {str(e)}")
            else:
                self.progress_update.emit(25, "Network isolation: unavailable")
            
            if not self._sleep_interruptible(0.5):
                return
            
            # Step 2: Vision gaze detection calibration.
            self.progress_update.emit(40, "Initializing gaze calibration...")
            if not self._sleep_interruptible(0.5):
                return
            
            if self.proctoring_service and self.proctoring_service.vision:
                try:
                    # Vision proctor is lazy-initialized; ensure readiness here.
                    self.proctoring_service._ensure_vision_initialized()
                    self.progress_update.emit(60, "Gaze calibration ready ✓")
                except Exception as e:
                    self.progress_update.emit(60, f"Gaze calibration: {str(e)}")
            else:
                self.progress_update.emit(60, "Gaze calibration: unavailable")
            
            if not self._sleep_interruptible(0.5):
                return
            
            # Step 3: Keyboard and input control.
            self.progress_update.emit(70, "Securing keyboard & input...")
            if not self._sleep_interruptible(0.3):
                return
            
            if self.proctoring_service and self.proctoring_service.lockdown:
                # Keyboard lockdown is deferred to start_exam_monitoring.
                self.progress_update.emit(75, "Keyboard security: ready")
            else:
                self.progress_update.emit(75, "Keyboard security: unavailable")
            
            if not self._sleep_interruptible(0.3):
                return
            
            # Step 4: Evidence collection system.
            self.progress_update.emit(80, "Initializing evidence capture...")
            if not self._sleep_interruptible(0.3):
                return
            
            self.progress_update.emit(90, "Finalizing secure environment...")
            if not self._sleep_interruptible(0.5):
                return
            
            # Completion.
            self.progress_update.emit(100, "Secure environment ready ✓")
            if not self._sleep_interruptible(0.5):
                return
            
            # Emit completion signal.
            self.initialization_complete.emit({
                "success": True,
                "message": "Environment secured. Starting exam..."
            })
            
        except Exception as e:
            self.error_occurred.emit(f"Security initialization failed: {str(e)}")


# Securing screen UI.

class SecuringScreen(QWidget):
    """Loading screen showing progress of security feature initialization."""
    
    securing_complete = pyqtSignal()  # Emitted when security init completes
    error_occurred = pyqtSignal(str)  # Emitted on error

    _BLACK_LOGO = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "assets", "Blacklogo.svg")
    )
    
    def __init__(self):
        super().__init__()
        self._proctoring_service = None
        self._exam_data = None
        self._worker = None
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI layout."""
        self.setWindowTitle("Observe - Securing Environment")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {BG_WHITE};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 80)
        layout.addStretch(1)
        
        middle_layout = QVBoxLayout()
        middle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle_layout.setSpacing(15)
        
        if _SVG_AVAILABLE and os.path.exists(self._BLACK_LOGO):
            self.logo = QSvgWidget(self._BLACK_LOGO)
            self.logo.setFixedSize(440, 200)
            middle_layout.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            self.logo = QLabel("OBSERVE")
            self.logo.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
            self.logo.setStyleSheet(f"color: {ACCENT_BLUE_VIOLET};")
            middle_layout.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)

        self.tagline = QLabel("finalizing secure environment")
        self.tagline.setFont(QFont("Segoe UI", 14))
        self.tagline.setStyleSheet(f"""
            color: {TEXT_GREY};
            letter-spacing: 2px;
            text-transform: uppercase;
        """)
        middle_layout.addWidget(self.tagline, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addLayout(middle_layout)
        layout.addStretch(1)
        
        loader_layout = QVBoxLayout()
        loader_layout.setSpacing(16)
        loader_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._status_label = QLabel("Waiting to initialize...")
        self._status_label.setFont(QFont("Segoe UI", 13))
        self._status_label.setStyleSheet(f"color: {TEXT_BLACK}; letter-spacing: 1px;")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loader_layout.addWidget(self._status_label)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(2)
        self._progress_bar.setMinimumWidth(600)
        self._progress_bar.setMaximumWidth(800)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {BORDER_LIGHT};
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {TEXT_BLACK};
            }}
        """)
        loader_layout.addWidget(self._progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addLayout(loader_layout)
        
        # Configure fade-in effect.
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(1200)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

    def set_proctoring_service(self, service):
        """Attach the proctoring service."""
        self._proctoring_service = service
    
    def set_exam_context(self, exam_data):
        """Set exam data if needed."""
        self._exam_data = exam_data or {}
    
    def start_securing(self):
        """Start the security initialization process."""
        if self._proctoring_service is None:
            self.error_occurred.emit("Proctoring service unavailable")
            return

        existing = self._worker
        if existing is not None and existing.isRunning():
            existing.stop()
            existing.wait(1000)
        
        # Reset visual state.
        self._progress_bar.setValue(0)
        self._status_label.setText("Starting security checks...")
        self._status_label.setStyleSheet(f"color: {TEXT_BLACK}; letter-spacing: 1px;")
        
        # Trigger fade-in animation.
        self.fade_anim.start()
        
        # Start background worker.
        self._worker = SecurityInitializationWorker(
            self._proctoring_service,
            self._exam_data
        )
        self._worker.progress_update.connect(self._on_progress_update)
        self._worker.initialization_complete.connect(self._on_init_complete)
        self._worker.error_occurred.connect(self._on_init_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_finished(self):
        worker = self._worker
        self._worker = None
        if worker is None:
            return
        try:
            worker.deleteLater()
        except RuntimeError:
            pass
    
    @pyqtSlot(int, str)
    def _on_progress_update(self, percent: int, status: str):
        """Slot called when progress updates."""
        self._progress_bar.setValue(percent)
        self._status_label.setText(status)
    
    @pyqtSlot(dict)
    def _on_init_complete(self, result: dict):
        """Slot called when initialization completes."""
        if result.get("success"):
            self._progress_bar.setValue(100)
            self._status_label.setText("Environment secured ✓")
            
            # Delay completion signal briefly for visual feedback.
            QTimer.singleShot(500, self.securing_complete.emit)
        else:
            self.error_occurred.emit(result.get("message", "Initialization failed"))
    
    @pyqtSlot(str)
    def _on_init_error(self, error_msg: str):
        """Slot called when initialization fails."""
        self._status_label.setText("⚠ Initialization Error")
        self._status_label.setStyleSheet(f"color: #EF4444; font-weight: bold;")
        self.error_occurred.emit(error_msg)

    def closeEvent(self, event):
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.stop()
            worker.wait(1000)
            try:
                worker.deleteLater()
            except RuntimeError:
                pass
        super().closeEvent(event)
