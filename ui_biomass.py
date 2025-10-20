import sys, cv2, datetime, os
from PyQt5 import QtWidgets, QtGui, QtCore
from compute import compute_feed
from detector import ShrimpDetector
from camera import Camera
from database import save_biomass_record
from theme import *

# --- Catch all unhandled exceptions in Qt ---
def qt_exception_hook(exctype, value, traceback):
    print("Unhandled Exception:", value)
sys.excepthook = qt_exception_hook


class VideoLabel(QtWidgets.QLabel):
    """Displays video frames from the camera or test image."""
    def __init__(self):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet("border: 3px solid #0077cc; border-radius: 10px; background-color: black;")
        self.setFixedSize(880, 460)

    def set_frame(self, frame):
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QtGui.QImage(rgb.data, w, h, ch * w, QtGui.QImage.Format_RGB888)
            pix = QtGui.QPixmap.fromImage(qimg)
            pix = pix.scaled(self.width(), self.height(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.setPixmap(pix)
        except Exception as e:
            print("Error displaying frame:", e)


class BiomassWindow(QtWidgets.QWidget):
    def __init__(self, user_id, parent=None):
        super().__init__()
        self.parent = parent
        self.user_id = user_id
        self.detector = ShrimpDetector()
        self.camera = Camera()
        self.running = False
        self.count = 0
        self.mode = "Camera"  # default

        # --- Window setup ---
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setStyleSheet(f"background-color:{BG_COLOR}; color:{TEXT_COLOR}; font-family:{FONT_FAMILY};")
        self.setMinimumSize(1024, 600)

        # --- Title ---
        self.lblTitle = QtWidgets.QLabel("Biomass Calculation")
        self.lblTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.lblTitle.setStyleSheet("font-size:38px; font-weight:bold; margin-bottom:10px;")

        # --- Source selector ---
        self.selector = QtWidgets.QComboBox()
        self.selector.addItems(["Camera", "Test Image"])
        self.selector.setFixedWidth(300)
        self.selector.setStyleSheet("""
            QComboBox {
                font-size:24px;
                padding:8px;
                border:2px solid #0077cc;
                border-radius:10px;
                background-color:white;
                color:black;
            }
        """)
        self.selector.currentTextChanged.connect(self.change_source)

        # --- Status indicator ---
        self.lblStatus = QtWidgets.QLabel("Idle")
        self.lblStatus.setAlignment(QtCore.Qt.AlignCenter)
        self.lblStatus.setStyleSheet("font-size:26px; margin-bottom:15px; color:#555;")

        # --- Video Display ---
        self.video = VideoLabel()

        # --- Stats area ---
        self.lblCount = QtWidgets.QLabel("Count: 0")
        self.lblFeed = QtWidgets.QLabel("Biomass: 0.00g | Feed: 0.00g | Protein: 0.00g | Filler: 0.00g")
        for lbl in [self.lblCount, self.lblFeed]:
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setStyleSheet("font-size:26px; margin:10px;")

        # --- Buttons ---
        self.btnStart = self.make_button("Start", BTN_SYNC)
        self.btnStop = self.make_button("Stop", "#ffbb33")
        self.btnSave = self.make_button("Save Process", BTN_COLOR)
        self.btnReset = self.make_button("Cancel / Reset", "#999999")
        self.btnBack = self.make_button("Back", BTN_DANGER)

        # --- Layout ---
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(20)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addWidget(self.lblTitle, alignment=QtCore.Qt.AlignCenter)
        top_layout.addWidget(self.selector, alignment=QtCore.Qt.AlignRight)

        layout.addLayout(top_layout)
        layout.addWidget(self.lblStatus)
        layout.addWidget(self.video, alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(self.lblCount)
        layout.addWidget(self.lblFeed)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(20)
        btn_layout.setAlignment(QtCore.Qt.AlignCenter)
        for b in [self.btnStart, self.btnStop, self.btnSave, self.btnReset, self.btnBack]:
            btn_layout.addWidget(b)
        layout.addLayout(btn_layout)

        # --- Timer ---
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)

        # --- Button connections ---
        self.btnStart.clicked.connect(self.start)
        self.btnStop.clicked.connect(self.stop)
        self.btnSave.clicked.connect(self.save)
        self.btnReset.clicked.connect(self.reset)
        self.btnBack.clicked.connect(self.go_back)

    def make_button(self, text, color):
        b = QtWidgets.QPushButton(text)
        b.setFixedHeight(90)
        b.setFixedWidth(220)
        b.setStyleSheet(f"""
            QPushButton {{
                background-color:{color};
                color:white;
                border-radius:20px;
                font-size:28px;
                font-weight:bold;
            }}
            QPushButton:pressed {{
                background-color:#005fa3;
            }}
        """)
        return b

    # ---------------- Logic ----------------
    def change_source(self, mode):
        """Switch between camera and test image mode."""
        self.mode = mode
        if mode == "Camera":
            self.camera = Camera()
            print("Switched to Camera mode.")
        else:
            self.camera.release()
            print("Switched to Test Image mode.")

    def start(self):
        if not self.running:
            self.running = True
            self.timer.start(100)
            self.lblStatus.setText("Running...")

    def stop(self):
        if self.running:
            self.running = False
            self.timer.stop()
            self.lblStatus.setText("Stopped")

    def reset(self):
        self.running = False
        self.timer.stop()
        self.count = 0
        self.lblCount.setText("Count: 0")
        self.lblFeed.setText("Biomass: 0.00g | Feed: 0.00g | Protein: 0.00g | Filler: 0.00g")
        self.lblStatus.setText("Idle")
        QtWidgets.QMessageBox.information(self, "Reset", "Process has been reset successfully.")

    def save(self):
        b, f, p, fl = compute_feed(self.count)
        save_biomass_record(self.user_id, self.count, b, f)
        QtWidgets.QMessageBox.information(self, "Saved", "Process saved locally.")
        self.lblStatus.setText("Saved")

    def go_back(self):
        self.timer.stop()
        self.camera.release()
        if self.parent:
            self.parent.update_recent()
            self.parent.showFullScreen()
        self.close()

    def update_frame(self):
        if self.mode == "Camera":
            frame = self.camera.get_frame()
        else:
            frame = cv2.imread("test.jpeg")

        if frame is None:
            return

        count, frame_rgb = self.detector.detect(frame)
        self.count = count
        b, f, p, fl = compute_feed(count)
        self.lblCount.setText(f"Count: {count}")
        self.lblFeed.setText(f"Biomass: {b:.2f}g | Feed: {f:.2f}g | Protein: {p:.2f}g | Filler: {fl:.2f}g")
        self.video.set_frame(cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))
