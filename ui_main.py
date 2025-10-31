import os
# --- FIX ZOOMED-IN GUI ON TOUCHSCREEN ---
# These environment variables prevent PyQt from scaling automatically
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_FONT_DPI"] = "96"
os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"
import sys
from PyQt5 import QtWidgets, QtCore
from ui_biomass import BiomassWindow
from ui_history import HistoryWindow
from database import get_last_record
from theme import *

# --- Optional: set the platform plugin explicitly (Wayland or EGLFS) ---
os.environ.setdefault("QT_QPA_PLATFORM", "wayland")

class MainMenu(QtWidgets.QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.logout_requested = False

        # Make it fixed to target screen size
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setFixedSize(1024, 600)

        # --- Normalize size policy (prevents zoom scaling) ---
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # --- Styling ---
        self.setStyleSheet(f"background-color:{BG_COLOR}; color:{TEXT_COLOR}; font-family:{FONT_FAMILY};")

        # --- Title ---
        self.lblTitle = QtWidgets.QLabel("Shrimp Biomass Calculation System")
        self.lblTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.lblTitle.setStyleSheet("font-size:18px; font-weight:bold; margin-top:6px; margin-bottom:8px;")

        # --- Last Process (center area) ---
        self.lastFrame = QtWidgets.QFrame()
        self.lastFrame.setStyleSheet("""
            QFrame {
                background-color: #f7fbff;
                border: 2px solid #0077cc;
                border-radius: 10px;
                padding: 14px;
            }
        """)

        lastLayout = QtWidgets.QVBoxLayout(self.lastFrame)
        lastLayout.setSpacing(6)
        lastLayout.setAlignment(QtCore.Qt.AlignCenter)

        self.lblRecentTitle = QtWidgets.QLabel("Last Process Summary")
        self.lblRecentTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.lblRecentTitle.setStyleSheet("font-size:18px; font-weight:bold; color:#005fa3;")

        self.lblRecent = QtWidgets.QLabel("No recorded process yet.")
        self.lblRecent.setAlignment(QtCore.Qt.AlignCenter)
        self.lblRecent.setWordWrap(True)
        self.lblRecent.setStyleSheet("""
            font-size:16px;
            font-weight:600;
            color:#333;
            line-height: 1.2;
        """)

        lastLayout.addWidget(self.lblRecentTitle)
        lastLayout.addWidget(self.lblRecent)

        # --- Buttons (bottom row) ---
        self.btnStart = self.make_button("Start Biomass Calculation", BTN_SYNC)
        self.btnHistory = self.make_button("View History", BTN_COLOR)
        self.btnLogout = self.make_button("Logout", BTN_DANGER)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setSpacing(12)
        buttonLayout.setContentsMargins(20, 8, 20, 12)
        buttonLayout.addWidget(self.btnStart)
        buttonLayout.addWidget(self.btnHistory)
        buttonLayout.addWidget(self.btnLogout)

        # --- Main Layout ---
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.setContentsMargins(16, 12, 16, 12)
        mainLayout.setSpacing(8)
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
        b.setFixedHeight(72)
        b.setFixedWidth(280)
        b.setStyleSheet(f"""
            QPushButton {{
                background-color:{color};
                color:white;
                border-radius:12px;
                font-size:18px;
                font-weight:bold;
                padding: 6px;
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
                f"<span style='font-size:14px; color:#666;'><b>Date:</b> {date[:19]}</span>"
                f"</div>"
            )
        else:
            self.lblRecent.setText("No recorded process yet.")

    def open_biomass(self):
        self.bw = BiomassWindow(self.user_id, self)
        self.bw.show()
        self.hide()

    def open_history(self):
        self.hw = HistoryWindow(self, self.user_id)
        self.hw.show()
        self.hide()

    def logout(self):
        self.logout_requested = True
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Force consistent scaling before showing
    app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, False)
    app.setAttribute(QtCore.Qt.AA_DisableHighDpiScaling, True)
    app.setAttribute(QtCore.Qt.AA_Use96Dpi, True)

    window = MainMenu(user_id=1)
    window.show()
    sys.exit(app.exec_())
