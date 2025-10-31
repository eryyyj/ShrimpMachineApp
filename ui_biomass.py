import sys, cv2, datetime, os
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_FONT_DPI"] = "96"
os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"
os.environ.setdefault("QT_QPA_PLATFORM", "wayland")  # use wayland or eglfs if on kiosk

from PyQt5 import QtWidgets, QtGui, QtCore
from compute import compute_feed
from detector import ShrimpDetector
from camera import Camera
from database import save_biomass_record
from theme import *

# ---------------- FIX ZOOMED-IN UI ----------------

# --- Catch all unhandled exceptions in Qt ---
def qt_exception_hook(exctype, value, traceback):
    print("Unhandled Exception:", value)
sys.excepthook = qt_exception_hook


class VideoLabel(QtWidgets.QLabel):
    """Displays video frames from the camera or test image."""
    def __init__(self):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet("border: 2px solid #0077cc; border-radius: 8px; background-color: black;")
        # allow the video area to expand to fullscreen instead of forcing a fixed size
        self.setMinimumSize(640, 320)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

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
        # switch to fullscreen mode (remove fixed size)
        # self.setFixedSize(1024, 600)
        self.setStyleSheet(f"background-color:{BG_COLOR}; color:{TEXT_COLOR}; font-family:{FONT_FAMILY};")

        # Force fullscreen state (call after initial setup)
        QtCore.QTimer.singleShot(0, lambda: self.showFullScreen())

        # --- Title ---
        self.lblTitle = QtWidgets.QLabel("Biomass Calculation")
        self.lblTitle.setAlignment(QtCore.Qt.AlignCenter)
        # smaller title to fit
        self.lblTitle.setStyleSheet("font-size:20px; font-weight:bold; margin-bottom:6px;")

        # --- Source selector ---
        self.selector = QtWidgets.QComboBox()
        self.selector.addItems(["Camera", "Test Image"])
        # narrower selector
        self.selector.setFixedWidth(160)
        self.selector.setStyleSheet("""
            QComboBox {
                font-size:14px;
                padding:4px;
                border:2px solid #0077cc;
                border-radius:8px;
                background-color:white;
                color:black;
            }
        """)
        self.selector.currentTextChanged.connect(self.change_source)

        # --- Status indicator ---
        self.lblStatus = QtWidgets.QLabel("Idle")
        self.lblStatus.setAlignment(QtCore.Qt.AlignCenter)
        self.lblStatus.setStyleSheet("font-size:14px; margin-bottom:6px; color:#555;")

        # --- Video Display ---
        self.video = VideoLabel()

        # --- Stats area ---
        self.lblCount = QtWidgets.QLabel("Count: 0")
        self.lblFeed = QtWidgets.QLabel("Biomass: 0.00g | Feed: 0.00g | Protein: 0.00g | Filler: 0.00g")
        for lbl in [self.lblCount, self.lblFeed]:
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setStyleSheet("font-size:16px; margin:4px;")

        # --- Buttons ---
        self.btnStart = self.make_button("Start", BTN_SYNC)
        self.btnStop = self.make_button("Stop", "#ffbb33")
        self.btnSave = self.make_button("Save", BTN_COLOR)
        self.btnReset = self.make_button("Reset", "#999999")
        self.btnBack = self.make_button("Back", BTN_DANGER)

        # --- Layout setup ---
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 12)
        layout.setSpacing(8)
        layout.setAlignment(QtCore.Qt.AlignTop)

        # --- Top row (title + selector) ---
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setAlignment(QtCore.Qt.AlignVCenter)
        top_layout.addWidget(self.lblTitle, stretch=3)
        top_layout.addWidget(self.selector, stretch=0, alignment=QtCore.Qt.AlignRight)

        layout.addLayout(top_layout)
        layout.addWidget(self.lblStatus)
        layout.addWidget(self.video, alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(self.lblCount)
        layout.addWidget(self.lblFeed)

        # --- Buttons layout ---
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(10)
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

    # --- Helper ---
    def make_button(self, text, color):
        b = QtWidgets.QPushButton(text)
        b.setFixedHeight(56)
        b.setFixedWidth(140)
        b.setStyleSheet(f"""
            QPushButton {{
                background-color:{color};
                color:white;
                border-radius:12px;
                font-size:16px;
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
            try:
                self.camera.release()
            except Exception:
                pass
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
        try:
            self.camera.release()
        except Exception:
            pass
        if self.parent:
            self.parent.update_recent()
            self.parent.show()
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


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Prevent auto scaling (critical for small LCDs)
    app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, False)
    app.setAttribute(QtCore.Qt.AA_DisableHighDpiScaling, True)
    app.setAttribute(QtCore.Qt.AA_Use96Dpi, True)

    win = BiomassWindow(user_id=1)
    win.show()
    sys.exit(app.exec_())
