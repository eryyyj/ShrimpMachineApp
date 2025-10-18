import sys
from PyQt5 import QtWidgets, QtCore
from database import init_db, verify_user
from ui_main import MainMenu

class Login(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shrimp Biomass System - Login")
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)  
        self.showFullScreen()  
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(250, 180, 250, 180)

        self.user = QtWidgets.QLineEdit()
        self.user.setPlaceholderText("Username")
        self.user.setFixedHeight(70)
        self.user.setStyleSheet("font-size:28px; padding:10px; border-radius:10px;")

        self.pw = QtWidgets.QLineEdit()
        self.pw.setPlaceholderText("Password")
        self.pw.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pw.setFixedHeight(70)
        self.pw.setStyleSheet("font-size:28px; padding:10px; border-radius:10px;")

        self.info = QtWidgets.QLabel("")
        self.info.setStyleSheet("font-size:22px; color:red;")

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

    def try_login(self):
        username = self.user.text().strip()
        password = self.pw.text().strip()
        if not username or not password:
            self.info.setText("Please enter username and password.")
            return

        uid = verify_user(username, password)
        if uid:
            self.user_id = uid
            self.accept()  # proceed to main menu
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

        # Wait until user logs out or closes
        app.exec_()

        if not getattr(main_window, "logout_requested", False):
            break

    sys.exit()

if __name__ == "__main__":
    main()
