import cv2, datetime
from PyQt5 import QtWidgets, QtGui, QtCore
from compute import compute_feed
from detector import ShrimpDetector
from camera import Camera
from database import save_biomass_record
from theme import *

class VideoLabel(QtWidgets.QLabel):
    """Displays video frames from the camera with fixed centered scaling."""
    def __init__(self):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet("border: 3px solid #0077cc; border-radius: 10px; background-color: black;")
        self.setFixedSize(800, 450)  

    def set_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QtGui.QImage(rgb.data, w, h, ch * w, QtGui.QImage.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(qimg)
        pix = pix.scaled(self.width(), self.height(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.setPixmap(pix)


class BiomassWindow(QtWidgets.QWidget):
    def __init__(self, user_id, parent=None):
        super().__init__()
        self.parent = parent
        self.user_id = user_id
        self.detector = ShrimpDetector()
        self.camera = Camera()
        self.running = False
        self.count = 0

        # --- Window setup ---
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setStyleSheet(f"background-color:{BG_COLOR}; color:{TEXT_COLOR}; font-family:{FONT_FAMILY};")

        # --- Title ---
        self.lblTitle = QtWidgets.QLabel("Biomass Calculation")
        self.lblTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.lblTitle.setStyleSheet("font-size:28px; font-weight:bold; margin-bottom:10px;")

        # --- Status indicator ---
        self.lblStatus = QtWidgets.QLabel(" Idle")
        self.lblStatus.setAlignment(QtCore.Qt.AlignCenter)
        self.lblStatus.setStyleSheet("font-size:22px; margin-bottom:15px; color:#888;")

        # --- Centered video frame ---
        self.video = VideoLabel()
        video_container = QtWidgets.QWidget()
        video_layout = QtWidgets.QHBoxLayout(video_container)
        video_layout.addStretch(1)
        video_layout.addWidget(self.video, alignment=QtCore.Qt.AlignCenter)
        video_layout.addStretch(1)

        # --- Stats area ---
        self.lblCount = QtWidgets.QLabel(" Count: 0")
        self.lblFeed = QtWidgets.QLabel(" Biomass: 0g | Feed: 0g | Protein: 0g | Filler: 0g")
        for lbl in [self.lblCount, self.lblFeed]:
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setStyleSheet("font-size:22px; margin:10px;")

        # --- Buttons ---
        self.btnStart = self.make_button(" Start", BTN_SYNC)
        self.btnStop = self.make_button(" Stop", "#ffbb33")
        self.btnSave = self.make_button(" Save Process", BTN_COLOR)
        self.btnReset = self.make_button(" Cancel / Reset", "#999999")  
        self.btnBack = self.make_button(" Back", BTN_DANGER)

        # --- Layout ---
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(40, 20, 40, 20)
        main_layout.setSpacing(10)
        main_layout.setAlignment(QtCore.Qt.AlignCenter)

        main_layout.addWidget(self.lblTitle)
        main_layout.addWidget(self.lblStatus)
        main_layout.addWidget(video_container, alignment=QtCore.Qt.AlignCenter)

        stats_layout = QtWidgets.QVBoxLayout()
        stats_layout.setAlignment(QtCore.Qt.AlignCenter)
        stats_layout.addWidget(self.lblCount)
        stats_layout.addWidget(self.lblFeed)
        main_layout.addLayout(stats_layout)

        # --- Buttons Row ---
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.setAlignment(QtCore.Qt.AlignCenter)
        for b in [self.btnStart, self.btnStop, self.btnSave, self.btnReset, self.btnBack]:
            btn_layout.addWidget(b)
        main_layout.addLayout(btn_layout)

        # --- Connect events ---
        self.btnStart.clicked.connect(self.start)
        self.btnStop.clicked.connect(self.stop)
        self.btnSave.clicked.connect(self.save)
        self.btnReset.clicked.connect(self.reset)
        self.btnBack.clicked.connect(self.go_back)

        # --- Timer for video update ---
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)

    def make_button(self, text, color):
        b = QtWidgets.QPushButton(text)
        b.setFixedHeight(80)
        b.setFixedWidth(220)
        b.setStyleSheet(f"""
            QPushButton {{
                background-color:{color};
                color:white;
                border-radius:15px;
                font-size:24px;
                font-weight:bold;
                padding:10px;
            }}
            QPushButton:pressed {{
                background-color:#005fa3;
            }}
        """)
        return b

    # ---------------- Logic ----------------
    def start(self):
        if not self.running:
            self.running = True
            self.timer.start(100)
            self.lblTitle.setText("Biomass Calculation - Running ")
            self.lblStatus.setText(" Running...")

    def stop(self):
        if self.running:
            self.running = False
            self.timer.stop()
            self.lblTitle.setText("Biomass Calculation - Stopped ")
            self.lblStatus.setText(" Paused")

    def reset(self):
        """Cancel and reset current process without saving."""
        self.running = False
        self.timer.stop()
        self.count = 0
        self.lblCount.setText(" Count: 0")
        self.lblFeed.setText(" Biomass: 0g | Feed: 0g | Protein: 0g | Filler: 0g")
        self.lblTitle.setText("Biomass Calculation - Reset")
        self.lblStatus.setText(" Idle")
        QtWidgets.QMessageBox.information(self, "Reset", "Process has been reset successfully.")

    def save(self):
        b, f, p, fl = compute_feed(self.count)
        save_biomass_record(self.user_id, self.count, b, f)
        QtWidgets.QMessageBox.information(self, "Saved", "Process saved locally ")
        self.lblTitle.setText("Process Saved ")
        self.lblStatus.setText(" Saved")

    def go_back(self):
        self.timer.stop()
        self.camera.release()
        self.parent.update_recent()
        self.parent.showFullScreen()
        self.close()

    def update_frame(self):
        frame = self.camera.get_frame()
        if frame is None:
            return
        count, _ = self.detector.detect(frame)
        self.count = count
        b, f, p, fl = compute_feed(count)
        self.lblCount.setText(f" Count: {count}")
        self.lblFeed.setText(f" Biomass: {b:.3f}g | Feed: {f:.3f}g | Protein: {p:.3f}g | Filler: {fl:.3f}g")
        self.video.set_frame(frame)
