import sys
from PyQt5 import QtWidgets
from database import init_db, verify_user
from ui import MainWindow

class Login(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        layout = QtWidgets.QVBoxLayout(self)
        self.user = QtWidgets.QLineEdit(); self.user.setPlaceholderText("Username")
        self.pw = QtWidgets.QLineEdit(); self.pw.setPlaceholderText("Password"); self.pw.setEchoMode(QtWidgets.QLineEdit.Password)
        self.info = QtWidgets.QLabel()
        btn = QtWidgets.QPushButton("Login"); btn.clicked.connect(self.try_login)
        layout.addWidget(self.user); layout.addWidget(self.pw); layout.addWidget(btn); layout.addWidget(self.info)
        self.user_id = None
    def try_login(self):
        uid = verify_user(self.user.text(), self.pw.text())
        if uid: self.user_id = uid; self.accept()
        else: self.info.setText("Invalid credentials")

def main():
    init_db()
    app = QtWidgets.QApplication(sys.argv)
    login = Login()
    if not login.exec_(): return
    win = MainWindow(login.user_id)
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
