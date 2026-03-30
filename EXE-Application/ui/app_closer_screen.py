"""UI screen for detecting and terminating forbidden background applications."""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QListWidget, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QTimer
from PyQt6.QtGui import QFont

def show_error_popup(parent, title, text):
    from ui.components.premium_popup import PremiumPopup
    PremiumPopup.show_message(
        parent=parent,
        title=title,
        message=text,
        icon=QMessageBox.Icon.Warning,
        buttons=QMessageBox.StandardButton.Ok
    )

try:
    from PyQt6.QtSvgWidgets import QSvgWidget
    _SVG_AVAILABLE = True
except ImportError:
    _SVG_AVAILABLE = False


# Background worker threads.

class ProcessScanWorker(QThread):
    """Background thread for scanning malicious processes."""
    processes_found = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, proctoring_service):
        super().__init__()
        self.proctoring_service = proctoring_service
    
    def run(self):
        try:
            processes = self.proctoring_service.list_malicious_processes()
            self.processes_found.emit(processes)
        except Exception as e:
            self.error.emit(f"Failed to scan processes: {str(e)}")


class ProcessKillWorker(QThread):
    """Background thread for killing a single process."""
    kill_complete = pyqtSignal(bool, str)
    error = pyqtSignal(str)
    
    def __init__(self, proctoring_service, pid):
        super().__init__()
        self.proctoring_service = proctoring_service
        self.pid = pid
    
    def run(self):
        try:
            ok, msg = self.proctoring_service.kill_process(
                self.pid,
                kill_all_matching=True,
                force_immediate=True,
            )
            self.kill_complete.emit(ok, msg)
        except Exception as e:
            self.error.emit(f"Failed to terminate process: {str(e)}")


class ProcessKillAllWorker(QThread):
    """Background thread for killing all suspicious processes."""
    kill_all_complete = pyqtSignal(int, int, str)
    error = pyqtSignal(str)

    def __init__(self, proctoring_service, pids):
        super().__init__()
        self.proctoring_service = proctoring_service
        normalized = []
        for p in pids:
            try:
                v = int(p)
                if v > 0:
                    normalized.append(v)
            except Exception:
                continue
        self.pids = list(dict.fromkeys(normalized))

    def run(self):
        try:
            killed = 0
            failed = 0
            for pid in self.pids:
                ok, msg = self.proctoring_service.kill_process(
                    pid,
                    kill_all_matching=True,
                    force_immediate=True,
                )
                if ok or "no longer running" in (msg or "").lower():
                    killed += 1
                else:
                    failed += 1

            summary = f"Kill-all complete. Killed/cleared {killed}, failed {failed}."
            self.kill_all_complete.emit(killed, failed, summary)
        except Exception as e:
            self.error.emit(f"Failed to terminate all processes: {str(e)}")


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

        icon = QLabel("💻")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 56px; background: transparent; border: none;")
        fc_layout.addWidget(icon)

        fc_layout.addSpacing(15)

        fc_title = QLabel("System Sandbox")
        fc_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fc_title.setStyleSheet("font-size: 22px; font-weight: 900; color: #FFFFFF; background: transparent; border: none; letter-spacing: 1px;")
        fc_layout.addWidget(fc_title)

        fc_desc = QLabel("Running final compliance checks to ensure your environment is sterile.")
        fc_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fc_desc.setWordWrap(True)
        fc_desc.setStyleSheet("font-size: 13px; font-weight: 500; color: #94A3B8; background: transparent; border: none; margin-top: 10px;")
        fc_layout.addWidget(fc_desc)


class AppCloserScreen(QWidget):
    proceed = pyqtSignal()
    cancelled = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    _WHITE_LOGO = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "assets", "whitelogo.svg")
    )

    def __init__(self):
        super().__init__()
        self._proctoring_service = None
        self._scan_worker = None
        self._kill_worker = None
        self._kill_all_worker = None
        self._malicious_processes = []
        
        self._proceed_btn = None
        self._btn_retry = None
        self._btn_force_close = None
        
        self._scan_in_progress = False
        self._kill_in_progress = False
        
        self.current_check = 0
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Observe - System Sandbox")
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
        
        # Top-left logo.
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
        
        # Bottom-left watermark.
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
        
        # Title and subtitle.
        title = QLabel("System Sandbox")
        title.setStyleSheet("font-size: 34px; font-weight: 900; color: #0F172A; margin-top: 40px; margin-left:-10px;")
        right_layout.addWidget(title)
        
        desc = QLabel("We are verifying that no forbidden background applications are running before launching your exam environment.")
        desc.setStyleSheet("font-size: 14px; color: #64748B; margin-top: 5px;")
        desc.setWordWrap(True)
        right_layout.addWidget(desc)
        
        right_layout.addSpacing(25)
        
        # Checks and process-list layout.
        two_col_layout = QHBoxLayout()
        two_col_layout.setSpacing(50)
        
        # Left side: checklist and progress.
        checklist_col = QVBoxLayout()
        
        # Progress bar section.
        progress_lbl = QLabel("Sandbox Integrity Check Progress")
        progress_lbl.setStyleSheet("font-size: 13px; font-weight: 800; color: #1E293B;")
        checklist_col.addWidget(progress_lbl)
        
        checklist_col.addSpacing(8)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #E2E8F0; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #6366F1; border-radius: 3px; }
        """)
        checklist_col.addWidget(self.progress_bar)
        
        checklist_col.addSpacing(30)
        
        self.checks = [
            {"label": "Background apps closed", "widget": None},
            {"label": "Network traffic blocked", "widget": None},
            {"label": "Antivirus hooks verified", "widget": None}
        ]
        
        # Checklist items.
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
            
        checklist_col.addLayout(self.checklist_layout)
        checklist_col.addStretch()
        
        # Right side: process list.
        procs_col = QVBoxLayout()
        
        proc_title = QLabel("DETECTED FORBIDDEN PROCESSES")
        proc_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #EF4444;")
        procs_col.addWidget(proc_title)
        
        procs_col.addSpacing(8)
        self.proc_list = QListWidget()
        self.proc_list.setStyleSheet("""
            QListWidget {
                background-color: #FEF2F2;
                border: 1px solid #FCA5A5;
                border-radius: 4px;
                padding: 10px;
                font-size: 13px;
                font-weight: 600;
                color: #B91C1C;
                outline: none;
            }
            QListWidget::item {
                margin-bottom: 5px;
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #EFF6FF;
                border: 1px solid #93C5FD;
                border-radius: 2px;
                color: #B91C1C;
            }
            QListWidget::item:hover {
                background-color: #F8FAFC;
            }
        """)
        procs_col.addWidget(self.proc_list)
        
        self._process_status = QLabel("No process scan has run yet.")
        self._process_status.setFont(QFont("Inter", 12))
        self._process_status.setStyleSheet("color: #9A3412;")
        procs_col.addWidget(self._process_status)
        
        procs_col.addSpacing(15)
        proc_actions = QHBoxLayout()
        proc_actions.setSpacing(15)
        
        self._btn_retry = QPushButton("Retry")
        self._btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_retry.setFixedHeight(38)
        self._btn_retry.setStyleSheet("""
            QPushButton {
                background: #FFFFFF; color: #475569; border: 1px solid #CBD5E1; font-weight: bold; border-radius: 4px; padding: 0 15px;
            }
            QPushButton:hover { background: #F8FAFC; color: #0F172A; }
        """)
        
        self._btn_force_close = QPushButton("Force Close All")
        self._btn_force_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_force_close.setFixedHeight(38)
        self._btn_force_close.setStyleSheet("""
            QPushButton {
                background-color: #EF4444; color: #FFFFFF; font-weight: bold; padding: 0 15px; border-radius: 4px; border: none;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        
        proc_actions.addWidget(self._btn_retry, 1)
        proc_actions.addWidget(self._btn_force_close, 1)
        procs_col.addLayout(proc_actions)
        
        # Add checklist and process columns.
        two_col_layout.addLayout(checklist_col, 5)
        two_col_layout.addLayout(procs_col, 5)
        
        right_layout.addLayout(two_col_layout)
        
        right_layout.addStretch()
        
        # Footer actions.
        btn_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel Exam")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 14px; font-weight: bold; color: #64748B; }
            QPushButton:hover { color: #0F172A; }
        """)
        
        btn_row.addWidget(self.btn_cancel)
        btn_row.addStretch()
        
        self._proceed_btn = QPushButton("Proceed to Examination  →")
        self._proceed_btn.setCursor(Qt.CursorShape.ForbiddenCursor)
        self._proceed_btn.setFixedHeight(48)
        self._proceed_btn.setEnabled(False)
        self._proceed_btn.setStyleSheet("""
            QPushButton {
                background-color: #0F172A; color: #FFFFFF; border-radius: 8px; font-weight: bold; font-size: 15px; padding: 0 40px;
            }
            QPushButton:hover:!disabled { background-color: #1E293B; }
            QPushButton:disabled { background-color: #CBD5E1; color: #F1F5F9; }
        """)
        btn_row.addWidget(self._proceed_btn)
        
        right_layout.addLayout(btn_row)
        
        main_layout.addWidget(right_panel, 1)
        
        # Connect UI signals.
        self.btn_cancel.clicked.connect(lambda: self.cancelled.emit("User cancelled during system sandbox step."))
        self._proceed_btn.clicked.connect(self._on_proceed_clicked)
        self._btn_retry.clicked.connect(self._refresh_processes)
        self._btn_force_close.clicked.connect(self._kill_all_processes)

    def set_proctoring_service(self, service):
        self._proctoring_service = service

    def _set_actions_enabled(self, enabled: bool):
        if self._btn_retry:
            self._btn_retry.setEnabled(enabled)
        if self._btn_force_close:
            has_targets = len(self._malicious_processes) > 0
            self._btn_force_close.setEnabled(enabled and has_targets)

    def _bind_worker_cleanup(self, worker: QThread, attr_name: str):
        def _cleanup_finished():
            current = getattr(self, attr_name, None)
            if current is worker:
                setattr(self, attr_name, None)
            try:
                worker.deleteLater()
            except RuntimeError:
                pass

        worker.finished.connect(_cleanup_finished)

    def _stop_worker(self, worker: QThread | None, timeout_ms: int = 1000):
        if worker is None:
            return
        try:
            if worker.isRunning():
                worker.requestInterruption()
                worker.quit()
                worker.wait(timeout_ms)
        except RuntimeError:
            return
        try:
            worker.deleteLater()
        except RuntimeError:
            pass

    def _refresh_processes(self):
        if self._proctoring_service is None:
            self.error_occurred.emit("Proctoring service unavailable for sandbox scan.")
            return

        if self._scan_in_progress or self._kill_in_progress:
            return

        self._scan_in_progress = True
        self._set_actions_enabled(False)
        self._process_status.setText("Scanning processes...")
        self._process_status.setStyleSheet("color: #F59E0B;")
        
        self._scan_worker = ProcessScanWorker(self._proctoring_service)
        self._scan_worker.processes_found.connect(self._on_scan_complete)
        self._scan_worker.error.connect(self._on_scan_error)
        self._bind_worker_cleanup(self._scan_worker, "_scan_worker")
        self._scan_worker.start()
    
    @pyqtSlot(list)
    def _on_scan_complete(self, processes):
        self._scan_in_progress = False
        self._malicious_processes = processes
        
        self.proc_list.clear()
        
        if not processes:
            self._process_status.setText("No suspicious processes detected right now.")
            self._process_status.setStyleSheet("color: #047857;")
            
            # Update left side checklist and progress
            self._fill_checklist(100)
            
            self._set_actions_enabled(True)
            self._update_proceed_button_state()
            return

        # Show process names only (exclude PID/reason details from UI list).
        name_counts: dict[str, int] = {}
        for proc in processes:
            proc_name = str(proc.get("name") or "").strip()
            if not proc_name:
                exe_path = str(proc.get("exe") or "").strip()
                proc_name = os.path.basename(exe_path) if exe_path else "Unknown"
            if proc_name:
                name_counts[proc_name] = name_counts.get(proc_name, 0) + 1

        for proc_name in sorted(name_counts.keys(), key=lambda x: x.lower()):
            count = name_counts[proc_name]
            display_name = proc_name if count == 1 else f"{proc_name} ({count})"
            self.proc_list.addItem(display_name)
            
        self._process_status.setText(f"Detected {len(processes)} suspicious process(es).")
        self._process_status.setStyleSheet("color: #9A3412; font-weight: 700;")
        
        # Reset checklist when suspicious processes remain.
        self._fill_checklist(0)
        
        self._set_actions_enabled(True)
        self._update_proceed_button_state()
    
    @pyqtSlot(str)
    def _on_scan_error(self, error_msg):
        self._scan_in_progress = False
        self._kill_in_progress = False
        self._set_actions_enabled(True)
        self.error_occurred.emit(error_msg)

    def _kill_all_processes(self):
        if self._proctoring_service is None:
            self.error_occurred.emit("Proctoring service unavailable for bulk process termination.")
            return

        if self._scan_in_progress or self._kill_in_progress:
            return

        pids = []
        for proc in self._malicious_processes:
            try:
                pid = int(proc.get("pid") or 0)
                if pid > 0:
                    pids.append(pid)
            except Exception:
                continue

        if not pids:
            self._process_status.setText("No suspicious processes available to kill.")
            self._process_status.setStyleSheet("color: #047857;")
            return

        self._kill_in_progress = True
        self._set_actions_enabled(False)
        self._process_status.setText(f"Killing processes... ({len(pids)} queued)")
        self._process_status.setStyleSheet("color: #F59E0B; font-weight: 700;")

        self._kill_all_worker = ProcessKillAllWorker(self._proctoring_service, pids)
        self._kill_all_worker.kill_all_complete.connect(self._on_kill_all_complete)
        self._kill_all_worker.error.connect(self._on_scan_error)
        self._bind_worker_cleanup(self._kill_all_worker, "_kill_all_worker")
        self._kill_all_worker.start()

    @pyqtSlot(int, int, str)
    def _on_kill_all_complete(self, killed_count, failed_count, summary):
        self._kill_in_progress = False
        self._set_actions_enabled(True)

        if failed_count == 0:
            self._process_status.setText(summary)
            self._process_status.setStyleSheet("color: #047857; font-weight: 700;")
        else:
            self._process_status.setText(summary)
            self._process_status.setStyleSheet("color: #9A3412; font-weight: 700;")

        # Rescan shortly to verify process termination.
        QTimer.singleShot(500, self._refresh_processes)

    def _update_proceed_button_state(self):
        if self._proceed_btn is None:
            return
            
        has_malicious = len(self._malicious_processes) > 0
        self._proceed_btn.setEnabled(not has_malicious)
        
        if not has_malicious:
            self._proceed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self._proceed_btn.setCursor(Qt.CursorShape.ForbiddenCursor)
            
    def _fill_checklist(self, percentage):
        """Update checklist visuals based on current completion percentage."""
        self.progress_bar.setValue(percentage)
        for item in self.checks:
            icon, lbl = item["widget"]
            if percentage == 100:
                icon.setText("✓")
                icon.setStyleSheet("color: #04E762; font-weight: 900; font-size: 16px;")
                lbl.setStyleSheet("font-size: 14px; color: #0F172A; font-weight: bold;")
            else:
                icon.setText("⏳")
                icon.setStyleSheet("font-size: 14px;")
                lbl.setStyleSheet("font-size: 14px; color: #475569; font-weight: 600;")

    def _on_proceed_clicked(self):
        if len(self._malicious_processes) > 0:
            show_error_popup(
                self,
                "Cannot Proceed",
                f"Please terminate all suspicious processes before continuing.\n\n"
                f"Detected {len(self._malicious_processes)} suspicious process(es).\n"
                f"Use the 'Force Close All' button to verify they are closed."
            )
            return
        
        self.proceed.emit()
    
    def refresh(self):
        """Refresh detected-process list; invoked by the parent workflow."""
        print("[AppCloser] Refreshing application list...")
        self._refresh_processes()

    def closeEvent(self, event):
        self._scan_in_progress = False
        self._kill_in_progress = False

        scan_worker = self._scan_worker
        kill_worker = self._kill_worker
        kill_all_worker = self._kill_all_worker
        self._scan_worker = None
        self._kill_worker = None
        self._kill_all_worker = None

        self._stop_worker(scan_worker)
        self._stop_worker(kill_worker)
        self._stop_worker(kill_all_worker)
        super().closeEvent(event)
