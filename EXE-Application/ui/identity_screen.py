"""Identity verification screen with live camera capture and face checks."""

import os
import cv2
import time
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QObject
from PyQt6.QtGui import QFont, QImage, QPixmap

try:
    from PyQt6.QtSvgWidgets import QSvgWidget
    _SVG_AVAILABLE = True
except ImportError:
    _SVG_AVAILABLE = False

# Camera capture worker thread.
class CameraWorker(QObject):
    """Captures camera frames and detects faces in background thread."""
    
    frame_ready = pyqtSignal(QImage)
    face_detected = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    
    def __init__(self, proctoring_service=None):
        super().__init__()
        self.proctoring_service = proctoring_service
        self.running = False
        self.cap = None
        self.face_count = 0
        self.consecutive_face_frames = 0
        self.face_detected_threshold = 5
        
    def run(self):
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.status_changed.emit("Failed to open camera")
                return
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.running = True
            self.status_changed.emit("Camera initialized")
            
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                
                frame = cv2.flip(frame, 1)
                display_frame = frame.copy()
                
                face_detected = self._detect_face_opencv(frame)
                
                if face_detected:
                    self.consecutive_face_frames += 1
                else:
                    self.consecutive_face_frames = 0
                
                if self.consecutive_face_frames >= self.face_detected_threshold:
                    self.face_detected.emit(self.face_count)
                    self.consecutive_face_frames = 0
                
                if face_detected:
                    h, w = display_frame.shape[:2]
                    cv2.rectangle(display_frame, (50, 50), (w - 50, h - 50), (0, 255, 0), 3)
                    cv2.putText(display_frame, f"Face Detected: {self.face_count}", 
                               (70, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
                
                rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
                self.frame_ready.emit(qt_image)
                
                time.sleep(0.03)
        
        except Exception as e:
            self.status_changed.emit(f"Camera error: {str(e)}")
        finally:
            if self.cap:
                self.cap.release()
            self.running = False
    
    def _detect_face_opencv(self, frame):
        if not hasattr(self, '_face_cascade'):
            self._face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._face_cascade.detectMultiScale(gray, 1.3, 5)
        self.face_count = len(faces)
        return len(faces) > 0
    
    def stop(self):
        self.running = False


# UI components.
class FloatingCardContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 320)

        self.wrapper = QWidget(self)
        self.wrapper.setGeometry(10, 30, 280, 260)

        self.card = QFrame(self.wrapper)
        self.card.setGeometry(0, 0, 280, 260)
        self.card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
            }
        """)

        fc_layout = QVBoxLayout(self.card)
        fc_layout.setContentsMargins(25, 40, 25, 40)
        fc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("📷")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 56px; background: transparent; border: none;")
        fc_layout.addWidget(icon)

        fc_layout.addSpacing(15)

        fc_title = QLabel("Identity Checkout")
        fc_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fc_title.setStyleSheet("font-size: 22px; font-weight: 900; color: #FFFFFF; background: transparent; border: none; letter-spacing: 1px;")
        fc_layout.addWidget(fc_title)

        fc_desc = QLabel("Running biometric analysis to confirm identity against organizational records securely.")
        fc_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fc_desc.setWordWrap(True)
        fc_desc.setStyleSheet("font-size: 13px; font-weight: 500; color: #94A3B8; background: transparent; border: none; margin-top: 10px;")
        fc_layout.addWidget(fc_desc)


class IdentityScreen(QWidget):
    identity_confirmed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    face_captured = pyqtSignal()

    _WHITE_LOGO = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "assets", "whitelogo.svg")
    )

    def __init__(self):
        super().__init__()
        self._proctoring_service = None
        
        self._camera_thread = None
        self._camera_worker = None
        self._camera_lock = threading.Lock()
        self._camera_frame_label = None
        
        self._face_detected = False
        self._camera_error = False
        self._transitioning_out = False
        
        self.checks = []
        
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Observe - Identity Verification")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #0B1120;")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left panel.
        left_panel = QFrame()
        left_panel.setFixedWidth(500)
        left_panel.setStyleSheet("background-color: #0B1120;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 50, 40, 40)
        
        logo_layout = QHBoxLayout()
        if _SVG_AVAILABLE and os.path.exists(self._WHITE_LOGO):
            self.logo = QSvgWidget(self._WHITE_LOGO)
            self.logo.setFixedSize(260, 120)
            logo_layout.addWidget(self.logo)
        else:
            self.logo = QLabel("OBSERVE")
            self.logo.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
            logo_layout.addWidget(self.logo)
            
        logo_layout.addStretch()
        left_layout.addLayout(logo_layout)
        left_layout.addStretch()
        
        self.floating_container = FloatingCardContainer()
        left_layout.addWidget(self.floating_container, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()
        
        watermark_lyt = QHBoxLayout()
        icon_wm = QLabel("✨")
        icon_wm.setStyleSheet("font-size: 15px; color: #64748B;")
        lbl_wm = QLabel("Powering next-gen proctoring")
        lbl_wm.setStyleSheet("font-size: 14px; color: #64748B; font-weight: 500;")
        watermark_lyt.addWidget(icon_wm)
        watermark_lyt.addWidget(lbl_wm)
        watermark_lyt.addStretch()
        left_layout.addLayout(watermark_lyt)
        
        main_layout.addWidget(left_panel)
        
        # Right panel.
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top-left-radius: 40px;
                border-bottom-left-radius: 40px;
            }
        """)
        
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(80, 50, 80, 40)
        
        title = QLabel("Identity Verification")
        title.setStyleSheet("font-size: 34px; font-weight: 900; color: #0F172A; margin-top: 40px; margin-left:-10px;")
        right_layout.addWidget(title)
        
        desc = QLabel("Please position your face clearly within the camera frame for biometric setup.")
        desc.setStyleSheet("font-size: 15px; color: #64748B; margin-top: 5px;")
        desc.setWordWrap(True)
        right_layout.addWidget(desc)
        
        right_layout.addSpacing(30)
        
        # Details layout (camera and status side by side).
        two_col_layout = QHBoxLayout()
        two_col_layout.setSpacing(50)
        
        # Camera column.
        cam_col = QVBoxLayout()
        cam_title = QLabel("LIVE FEED")
        cam_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #1E293B;")
        cam_col.addWidget(cam_title)
        cam_col.addSpacing(10)
        
        self._camera_frame_label = QLabel()
        self._camera_frame_label.setFixedSize(340, 250)
        self._camera_frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_frame_label.setStyleSheet("background-color: #1E293B; border-radius: 8px; border: 2px solid #CBD5E1;")
        cam_col.addWidget(self._camera_frame_label)
        
        self.face_status = QLabel("🔄 Initializing camera...")
        self.face_status.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        self.face_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.face_status.setStyleSheet("color: #F59E0B; background: transparent; margin-top: 5px;")
        cam_col.addWidget(self.face_status)
        
        cam_col.addStretch()
        two_col_layout.addLayout(cam_col, 5)
        
        # Status column.
        status_col = QVBoxLayout()
        stat_title = QLabel("SCAN STATUS")
        stat_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #1E293B;")
        status_col.addWidget(stat_title)
        status_col.addSpacing(10)
        
        self.checks = [
            {"label": "Lighting Optimal", "widget": None},
            {"label": "Face Detected", "widget": None},
            {"label": "Identity Confirmed", "widget": None}
        ]
        
        self.checklist_layout = QVBoxLayout()
        self.checklist_layout.setSpacing(20)
        for idx, item in enumerate(self.checks):
            row = QHBoxLayout()
            row.setSpacing(15)
            icon = QLabel("⏳")  
            icon.setStyleSheet("font-size: 14px;")
            lbl = QLabel(item["label"])
            lbl.setStyleSheet("font-size: 14px; color: #475569; font-weight: 600;")
            row.addWidget(icon)
            row.addWidget(lbl)
            row.addStretch()
            self.checks[idx]["widget"] = (icon, lbl)
            self.checklist_layout.addLayout(row)
            
        status_col.addLayout(self.checklist_layout)
        
        status_col.addSpacing(30)
        instr = QLabel("<b>Instructions:</b><br/>• Ensure good lighting<br/>• Look straight at camera<br/>• Remove glasses/masks")
        instr.setStyleSheet("font-size: 13px; color: #64748B; line-height: 1.5;")
        status_col.addWidget(instr)
        status_col.addStretch()
        
        two_col_layout.addLayout(status_col, 4)
        
        right_layout.addLayout(two_col_layout)
        right_layout.addStretch()
        
        # Footer actions.
        btn_row = QHBoxLayout()
        
        self.btn_retry = QPushButton("Retry Capture")
        self.btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retry.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 14px; font-weight: bold; color: #64748B; }
            QPushButton:hover { color: #0F172A; }
        """)
        btn_row.addWidget(self.btn_retry)
        btn_row.addStretch()
        
        self.btn_proceed = QPushButton("Confirm Identity  →")
        self.btn_proceed.setCursor(Qt.CursorShape.ForbiddenCursor)
        self.btn_proceed.setFixedHeight(48)
        self.btn_proceed.setEnabled(False)
        self.btn_proceed.setStyleSheet("""
            QPushButton {
                background-color: #0F172A; color: #FFFFFF; border-radius: 8px; font-weight: bold; font-size: 15px; padding: 0 40px;
            }
            QPushButton:hover:!disabled { background-color: #1E293B; }
            QPushButton:disabled { background-color: #CBD5E1; color: #F1F5F9; }
        """)
        btn_row.addWidget(self.btn_proceed)
        right_layout.addLayout(btn_row)
        
        main_layout.addWidget(right_panel, 1)
        
        # Connect button handlers.
        self.btn_retry.clicked.connect(self._on_retry)
        self.btn_proceed.clicked.connect(self._on_confirm)

    def set_proctoring_service(self, service):
        self._proctoring_service = service

    def _on_retry(self):
        self.face_status.setText("Retrying camera connection...")
        self.face_status.setStyleSheet("color: #F59E0B; background: transparent;")
        self.btn_retry.setEnabled(False)
        print("[Identity] Retry clicked - restarting camera feed")
        self.stop_camera_feed()
        QTimer.singleShot(300, self.start_camera_feed)

    def _on_confirm(self):
        if self._transitioning_out:
            return
        if not self._face_detected:
            self.face_status.setText("Please align your face before proceeding.")
            self.face_status.setStyleSheet("color: #F59E0B; background: transparent; font-weight: 700;")
            return
            
        self._transitioning_out = True
        self.btn_proceed.setText("Verifying map...")
        self.btn_proceed.setEnabled(False)
        self.btn_retry.setEnabled(False)
        print("[Identity] Confirmation clicked")
        self.stop_camera_feed()
        
        # Mark final verification check before transition.
        self._set_check_status(2, True)
        
        # Delay briefly so users can see the final check state.
        QTimer.singleShot(600, self.identity_confirmed.emit)

    def _set_check_status(self, index, is_done):
        if index < 0 or index >= len(self.checks):
            return
        icon, lbl = self.checks[index]["widget"]
        if is_done:
            icon.setText("✓")
            icon.setStyleSheet("color: #04E762; font-weight: 900; font-size: 16px;")
            lbl.setStyleSheet("font-size: 14px; color: #0F172A; font-weight: bold;")
        else:
            icon.setText("⏳")
            icon.setStyleSheet("font-size: 14px;")
            lbl.setStyleSheet("font-size: 14px; color: #475569; font-weight: 600;")
            
    def _reset_checks(self):
        for i in range(len(self.checks)):
            self._set_check_status(i, False)

    def start_camera_feed(self):
        with self._camera_lock:
            existing_thread = self._camera_thread
            if existing_thread is not None:
                try:
                    if existing_thread.isRunning():
                        return
                except RuntimeError:
                    pass
                self._camera_thread = None
                self._camera_worker = None
        
        try:
            self._transitioning_out = False
            self._face_detected = False
            self._camera_error = False
            self.btn_proceed.setEnabled(False)
            self.btn_proceed.setCursor(Qt.CursorShape.ForbiddenCursor)
            self.btn_proceed.setText("Confirm Identity  →")
            self.btn_retry.setEnabled(True)
            self._reset_checks()

            self._camera_worker = CameraWorker(self._proctoring_service)
            self._camera_thread = QThread(self)
            self._camera_worker.moveToThread(self._camera_thread)
            
            self._camera_worker.frame_ready.connect(self._on_frame_ready)
            self._camera_worker.face_detected.connect(self._on_face_detected)
            self._camera_worker.status_changed.connect(self._on_camera_status)
            self._camera_thread.started.connect(self._camera_worker.run)
            self._camera_thread.finished.connect(self._camera_worker.deleteLater)
            self._camera_thread.finished.connect(self._camera_thread.deleteLater)
            
            self._camera_thread.start()
            
            self.face_status.setText("🔄 Detecting face...")
            self.face_status.setStyleSheet("color: #F59E0B; background: transparent;")
            print("[Identity] Camera feed started")
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to start camera: {str(e)}")

    def stop_camera_feed(self):
        with self._camera_lock:
            worker = self._camera_worker
            thread = self._camera_thread
            self._camera_thread = None
            self._camera_worker = None

        if worker:
            try:
                worker.frame_ready.disconnect(self._on_frame_ready)
            except Exception:
                pass
            try:
                worker.face_detected.disconnect(self._on_face_detected)
            except Exception:
                pass
            try:
                worker.status_changed.disconnect(self._on_camera_status)
            except Exception:
                pass
            try:
                worker.stop()
            except Exception:
                pass

        if thread:
            try:
                thread.quit()
                thread.wait(1200)
            except Exception:
                pass
        
        if self._camera_frame_label is not None:
            self._camera_frame_label.clear()
            self._camera_frame_label.setText("")
            
        self.face_status.setText("🔄 Camera stopped")
        self.face_status.setStyleSheet("color: #9CA3AF; background: transparent;")
        print("[Identity] Camera feed stopped")

    def _on_frame_ready(self, qt_image):
        if self._transitioning_out or self._camera_frame_label is None:
            return
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(340, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._camera_frame_label.setPixmap(scaled_pixmap)

    def _on_face_detected(self, face_count):
        if self._face_detected:
            return
        
        self._face_detected = True
        self._camera_error = False
        
        # Mark face detection check as complete.
        self._set_check_status(1, True)
        
        self.face_status.setText(f"✅ Face captured ({face_count} face(s))")
        self.face_status.setStyleSheet("color: #10B981; background: transparent; font-weight: 700;")
        
        self.btn_proceed.setEnabled(True)
        self.btn_proceed.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retry.setEnabled(True)
        
        print("[Identity] Face captured - ready for next phase")
        self.face_captured.emit()

    def _on_camera_status(self, status_msg):
        if self._transitioning_out:
            return
        print(f"[Identity Camera] {status_msg}")
        status_lower = status_msg.lower()
        if "initialized" in status_lower:
            # Treat camera initialization as the lighting readiness signal.
            self._set_check_status(0, True)
            self.face_status.setText("🔄 Detecting face...")
            self.face_status.setStyleSheet("color: #F59E0B; background: transparent;")
            self.btn_retry.setEnabled(True)
            return

        if "error" in status_lower or "failed" in status_lower:
            self._camera_error = True
            self.face_status.setText("❌ Camera not detected. Click Retry Capture.")
            self.face_status.setStyleSheet("color: #EF4444; background: transparent; font-weight: 700;")
            self.btn_proceed.setEnabled(False)
            self.btn_proceed.setCursor(Qt.CursorShape.ForbiddenCursor)
            self.btn_retry.setEnabled(True)
            self.error_occurred.emit(f"Camera: {status_msg}")

    def closeEvent(self, event):
        self.stop_camera_feed()
        super().closeEvent(event)
    
    def cleanup(self):
        self.stop_camera_feed()
