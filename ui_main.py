from PyQt5 import QtWidgets, QtCore
from ui_biomass import BiomassWindow
from ui_history import HistoryWindow
from database import get_last_record
from theme import *

class MainMenu(QtWidgets.QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.logout_requested = False
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setStyleSheet(f"background-color:{BG_COLOR}; color:{TEXT_COLOR}; font-family:{FONT_FAMILY};")

        # --- Title ---
        self.lblTitle = QtWidgets.QLabel("Shrimp Biomass Calculation System")
        self.lblTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.lblTitle.setStyleSheet("font-size:38px; font-weight:bold; margin-top:10px; margin-bottom:20px;")

        # --- Last Process (center area) ---
        self.lastFrame = QtWidgets.QFrame()
        self.lastFrame.setStyleSheet("""
            QFrame {
                background-color: #f7fbff;
                border: 2px solid #0077cc;
                border-radius: 16px;
                padding: 40px;
            }
        """)

        lastLayout = QtWidgets.QVBoxLayout(self.lastFrame)
        lastLayout.setSpacing(20)
        lastLayout.setAlignment(QtCore.Qt.AlignCenter)

        self.lblRecentTitle = QtWidgets.QLabel("Last Process Summary")
        self.lblRecentTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.lblRecentTitle.setStyleSheet("font-size:32px; font-weight:bold; color:#005fa3;")

        self.lblRecent = QtWidgets.QLabel("No recorded process yet.")
        self.lblRecent.setAlignment(QtCore.Qt.AlignCenter)
        self.lblRecent.setWordWrap(True)
        self.lblRecent.setStyleSheet("""
            font-size:28px;
            font-weight:600;
            color:#333;
            line-height: 1.6;
        """)

        lastLayout.addWidget(self.lblRecentTitle)
        lastLayout.addWidget(self.lblRecent)

        # --- Buttons (bottom row) ---
        self.btnStart = self.make_button("Start Biomass Calculation", BTN_SYNC)
        self.btnHistory = self.make_button("View History", BTN_COLOR)
        self.btnLogout = self.make_button("Logout", BTN_DANGER)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setSpacing(40)
        buttonLayout.setContentsMargins(60, 20, 60, 40)
        buttonLayout.addWidget(self.btnStart, stretch=1)
        buttonLayout.addWidget(self.btnHistory, stretch=1)
        buttonLayout.addWidget(self.btnLogout, stretch=1)

        # --- Main Layout ---
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.setContentsMargins(80, 40, 80, 40)
        mainLayout.setSpacing(20)
        mainLayout.addWidget(self.lblTitle)
        mainLayout.addStretch(1)
        mainLayout.addWidget(self.lastFrame, stretch=3, alignment=QtCore.Qt.AlignCenter)
        mainLayout.addStretch(1)
        mainLayout.addLayout(buttonLayout)

        # --- Connections ---
        self.btnStart.clicked.connect(self.open_biomass)
        self.btnHistory.clicked.connect(self.open_history)
        self.btnLogout.clicked.connect(self.logout)

        # --- Load last process ---
        self.update_recent()

    def make_button(self, text, color):
        b = QtWidgets.QPushButton(text)
        b.setFixedHeight(160)
        b.setStyleSheet(f"""
            QPushButton {{
                background-color:{color};
                color:white;
                border-radius:30px;
                font-size:34px;
                font-weight:bold;
                letter-spacing: 0.5px;
                padding: 15px;
            }}
            QPushButton:pressed {{
                background-color:#005fa3;
            }}
        """)
        return b

    def update_recent(self):
        rec = get_last_record(self.user_id)
        if rec:
            shrimpCount, biomass, feed, date = rec[3], rec[4], rec[5], rec[6]
            self.lblRecent.setText(
                f"<div style='text-align:center;'>"
                f"<b>Shrimp Count:</b> {shrimpCount}<br>"
                f"<b>Biomass:</b> {biomass:.3f} g<br>"
                f"<b>Feed:</b> {feed:.3f} g<br>"
                f"<span style='font-size:24px; color:#666;'><b>Date:</b> {date[:19]}</span>"
                f"</div>"
            )
        else:
            self.lblRecent.setText("No recorded process yet.")

    def open_biomass(self):
        self.hide()
        self.bw = BiomassWindow(self.user_id, self)
        self.bw.showFullScreen()

    def open_history(self):
        self.hide()
        self.hw = HistoryWindow(self, self.user_id)
        self.hw.showFullScreen()

    def logout(self):
        self.logout_requested = True
        self.close()
