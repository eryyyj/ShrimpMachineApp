import cv2, datetime
from PyQt5 import QtWidgets, QtGui, QtCore
from compute import compute_feed
from database import save_biomass_record, sync_biomass_records
from detector import ShrimpDetector
from camera import Camera

class VideoLabel(QtWidgets.QLabel):
    def set_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QtGui.QImage(rgb.data, w, h, ch*w, QtGui.QImage.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(qimg)
        pix = pix.scaled(self.width(), self.height(), QtCore.Qt.KeepAspectRatio)
        self.setPixmap(pix)

class MainWindow(QtWidgets.QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.detector = ShrimpDetector()
        self.camera = Camera()
        self.running = False
        self.start_time = None
        self.count = 0

        self.video = VideoLabel(); self.video.setMinimumSize(640,480)
        self.lblCount = QtWidgets.QLabel("Count: 0")
        self.lblFeed = QtWidgets.QLabel("Biomass: 0 | Feed: 0 | Protein: 0 | Filler: 0")

        self.btnStart = QtWidgets.QPushButton("Start")
        self.btnStop = QtWidgets.QPushButton("Stop")
        self.btnSync = QtWidgets.QPushButton("Sync")
        self.btnQuit = QtWidgets.QPushButton("Quit")

        self.btnStart.clicked.connect(self.start)
        self.btnStop.clicked.connect(self.stop)
        self.btnSync.clicked.connect(self.sync)
        self.btnQuit.clicked.connect(self.close)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.video)
        layout.addWidget(self.lblCount)
        layout.addWidget(self.lblFeed)
        row = QtWidgets.QHBoxLayout()
        for b in [self.btnStart, self.btnStop, self.btnSync, self.btnQuit]: row.addWidget(b)
        layout.addLayout(row)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)

    def start(self):
        self.start_time = datetime.datetime.now().isoformat()
        self.running = True
        self.timer.start(100)

    def stop(self):
        self.running = False
        self.timer.stop()
        end = datetime.datetime.now().isoformat()
        b, f, p, fl = compute_feed(self.count)
        save_biomass_record(self.user_id, self.count, b, f)
        QtWidgets.QMessageBox.information(self, "Saved", "Run saved locally.")
        self.start_time = None

    def sync(self):
        n = sync_biomass_records()
        QtWidgets.QMessageBox.information(self, "Sync", f"Synced {n} record(s)." if n else "Nothing to sync.")

    def update_frame(self):
        frame = self.camera.get_frame()
        if frame is None: return
        count, _ = self.detector.detect(frame)
        self.count = count
        b, f, p, fl = compute_feed(count)
        self.lblCount.setText(f"Count: {count}")
        self.lblFeed.setText(f"Biomass: {b:.4f} | Feed: {f:.4f} | Protein: {p:.4f} | Filler: {fl:.4f}")
        self.video.set_frame(frame)
