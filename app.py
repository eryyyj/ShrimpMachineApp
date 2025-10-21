import os
import sys
import subprocess
from PyQt5 import QtWidgets, QtCore
from database import init_db, verify_user
from ui_main import MainMenu

# --- Environment setup ---
os.environ.setdefault("QT_QPA_PLATFORM", "wayland")
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_FONT_DPI"] = "96"


class Login(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shrimp Biomass System - Login")
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(250, 180, 250, 180)

        # --- Username Field ---
        self.user = QtWidgets.QLineEdit()
        self.user.setPlaceholderText("Username")
        self.user.setFixedHeight(70)
        self.user.setStyleSheet("font-size:28px; padding:10px; border-radius:10px;")
        self.user.focusInEvent = lambda event: self.open_keyboard()

        # --- Password Field ---
        self.pw = QtWidgets.QLineEdit()
        self.pw.setPlaceholderText("Password")
        self.pw.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pw.setFixedHeight(70)
        self.pw.setStyleSheet("font-size:28px; padding:10px; border-radius:10px;")
        self.pw.focusInEvent = lambda event: self.open_keyboard()

        # --- Info Label ---
        self.info = QtWidgets.QLabel("")
        self.info.setStyleSheet("font-size:22px; color:red;")

        # --- Login Button ---
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

        # --- Layout Assembly ---
        layout.addWidget(self.user)
        layout.addWidget(self.pw)
        layout.addWidget(btn)
        layout.addWidget(self.info)

        self.user_id = None
        self.keyboard_process = None

    def showEvent(self, event):
        """Show fullscreen and make sure app allows other windows (keyboard) on top."""
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self.showFullScreen)
        # allow keyboard windows to overlap
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnBottomHint)
        self.show()

    def open_keyboard(self):
        """Show matchbox keyboard anchored at the bottom, above the app."""
        try:
            subprocess.Popen(["pkill", "-f", "matchbox-keyboard"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        try:
            # Launch keyboard detached
            subprocess.Popen(
                ["matchbox-keyboard"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            # Wait briefly for it to appear, then raise it on top
            def raise_keyboard():
                try:
                    subprocess.Popen(
                        ["xdotool", "search", "--classname", "Matchbox-keyboard", "windowraise"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass

            QtCore.QTimer.singleShot(800, raise_keyboard)

        except Exception as e:
            print("Keyboard launch failed:", e)


    def close_keyboard(self):
        """Close the matchbox keyboard."""
        try:
            subprocess.Popen(["pkill", "-f", "matchbox-keyboard"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def try_login(self):
        """Handle login logic and close keyboard after success."""
        username = self.user.text().strip()
        password = self.pw.text().strip()
        if not username or not password:
            self.info.setText("Please enter username and password.")
            return

        uid = verify_user(username, password)
        if uid:
            self.user_id = uid
            self.close_keyboard()
            self.accept()
        else:
            self.info.setText("Invalid credentials")


def main():
    init_db()
    app = QtWidgets.QApplication(sys.argv)

    while True:
        login = Login()
        if not login.exec_():
            break

        main_window = MainMenu(login.user_id)
        main_window.showFullScreen()

        app.exec_()

        if not getattr(main_window, "logout_requested", False):
            break

    sys.exit()


if __name__ == "__main__":
    main()
