import os
os.environ.setdefault("QT_QPA_PLATFORM", "wayland")  # fallback if systemd variable missing
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_FONT_DPI"] = "96"

import sys
import subprocess
from PyQt5 import QtWidgets, QtCore
from database import init_db, verify_user
from ui_main import MainMenu


class Login(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shrimp Biomass System - Login")
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(250, 180, 250, 180)

        # Username field
        self.user = QtWidgets.QLineEdit()
        self.user.setPlaceholderText("Username")
        self.user.setFixedHeight(70)
        self.user.setStyleSheet("font-size:28px; padding:10px; border-radius:10px;")

        # Password field
        self.pw = QtWidgets.QLineEdit()
        self.pw.setPlaceholderText("Password")
        self.pw.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pw.setFixedHeight(70)
        self.pw.setStyleSheet("font-size:28px; padding:10px; border-radius:10px;")

        # Info label
        self.info = QtWidgets.QLabel("")
        self.info.setStyleSheet("font-size:22px; color:red;")

        # Login button
        btn = QtWidgets.QPushButton("Login")
        btn.setFixedHeight(80)
        btn.setStyleSheet("""
            QPushButton {
                background-color:#0077cc;
                color:white;
                font-size:30px;
                border-radius:15px;
                font-weight:bold;
            }
            QPushButton:pressed { background-color:#005fa3; }
        """)
        btn.clicked.connect(self.try_login)

        layout.addWidget(self.user)
        layout.addWidget(self.pw)
        layout.addWidget(btn)
        layout.addWidget(self.info)

        self.user_id = None
        self.keyboard_visible = False
        self.keyboard_process = None

        # Connect focus signals more reliably
        self.user.focusInEvent = lambda event: self.open_keyboard()
        self.pw.focusInEvent = lambda event: self.open_keyboard()

    def showEvent(self, event):
        """Ensure fullscreen after dialog is shown."""
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self.showFullScreen)

    def open_keyboard(self):
        """Keep the Onboard keyboard open persistently."""
        if not self.keyboard_visible:
            try:
                # Kill any old keyboard instances first
                subprocess.Popen(["pkill", "-f", "onboard"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            except Exception:
                pass
            # Launch Onboard detached
            self.keyboard_process = subprocess.Popen(["onboard", "--xid"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.keyboard_visible = True

    def close_keyboard(self):
        """Close Onboard gracefully."""
        try:
            subprocess.Popen(["pkill", "-f", "onboard"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            self.keyboard_visible = False
        except Exception:
            pass

    def try_login(self):
        username = self.user.text().strip()
        password = self.pw.text().strip()

        if not username or not password:
            self.info.setText("Please enter username and password.")
            return

        uid = verify_user(username, password)
        if uid:
            self.user_id = uid
            self.close_keyboard()  # close keyboard when login succeeds
            self.accept()
        else:
            self.info.setText("Invalid credentials")


def main():
    init_db()
    app = QtWidgets.QApplication(sys.argv)

    while True:
        login = Login()
        if not login.exec_():  # user closed login
            break

        main_window = MainMenu(login.user_id)
        main_window.showFullScreen()
        app.exec_()

        if not getattr(main_window, "logout_requested", False):
            break

    sys.exit()


if __name__ == "__main__":
    main()
