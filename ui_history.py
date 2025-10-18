from PyQt5 import QtWidgets, QtGui, QtCore
from database import get_all_records, delete_record, sync_biomass_records
from theme import *
import datetime

class HistoryWindow(QtWidgets.QWidget):
    def __init__(self, parent, user_id):
        super().__init__()
        self.parent = parent
        self.user_id = user_id
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setStyleSheet(f"background-color:{BG_COLOR}; color:{TEXT_COLOR}; font-family:{FONT_FAMILY};")
        self.setWindowTitle("Biomass History")

        # --- Title ---
        self.lblTitle = QtWidgets.QLabel("Biomass Process History")
        self.lblTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.lblTitle.setStyleSheet("font-size:28px; font-weight:bold; margin-bottom:10px;")

        # --- Scroll area for record cards ---
        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setStyleSheet("border: none;")

        self.recordsContainer = QtWidgets.QWidget()
        self.vboxRecords = QtWidgets.QVBoxLayout(self.recordsContainer)
        self.vboxRecords.setAlignment(QtCore.Qt.AlignTop)
        self.scrollArea.setWidget(self.recordsContainer)

        # --- Buttons ---
        self.btnSync = self.make_button("Sync to Cloud", BTN_SYNC)
        self.btnDelete = self.make_button("Delete Selected", BTN_DANGER)
        self.btnBack = self.make_button("Back", BTN_COLOR)

        btnLayout = QtWidgets.QHBoxLayout()
        btnLayout.setSpacing(20)
        btnLayout.addWidget(self.btnSync)
        btnLayout.addWidget(self.btnDelete)
        btnLayout.addWidget(self.btnBack)

        # --- Main Layout ---
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.setContentsMargins(40, 20, 40, 20)
        mainLayout.setSpacing(15)
        mainLayout.addWidget(self.lblTitle)
        mainLayout.addWidget(self.scrollArea)
        mainLayout.addLayout(btnLayout)

        # --- Connect buttons ---
        self.btnSync.clicked.connect(self.sync_data)
        self.btnDelete.clicked.connect(self.delete_selected)
        self.btnBack.clicked.connect(self.go_back)

        self.selectedRecordId = None
        self.selectedCard = None
        self.load_records()

    def make_button(self, text, color):
        b = QtWidgets.QPushButton(text)
        b.setFixedHeight(70)
        b.setStyleSheet(f"""
            QPushButton {{
                background-color:{color};
                color:white;
                border-radius:15px;
                font-size:22px;
                font-weight:bold;
                padding:8px;
            }}
            QPushButton:pressed {{
                background-color:#005fa3;
            }}
        """)
        return b

    def load_records(self):
        """Load all records into styled cards instead of a table."""
        for i in reversed(range(self.vboxRecords.count())):
            widget = self.vboxRecords.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        records = get_all_records(self.user_id)
        if not records:
            noData = QtWidgets.QLabel("No biomass records available.")
            noData.setAlignment(QtCore.Qt.AlignCenter)
            noData.setStyleSheet("font-size:22px; margin-top:200px; color:#888;")
            self.vboxRecords.addWidget(noData)
            return

        for rec in reversed(records):  # show newest first
            recordCard = self.create_record_card(rec)
            self.vboxRecords.addWidget(recordCard)

    def create_record_card(self, rec):
        """Create a single history record card."""
        card = QtWidgets.QFrame()
        card.setObjectName(str(rec[0]))  # store local ID
        card.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        synced = rec[7]
        shrimpCount, biomass, feed, date = rec[3], rec[4], rec[5], rec[6]
        date_str = datetime.datetime.fromisoformat(date).strftime("%B %d, %Y • %I:%M %p")

        # Base colors
        border_color = "#4CAF50" if synced else "#ff9800"
        bg_color = "#e8f5e9" if synced else "#fff5e6"

        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 12px;
                padding: 18px;
                transition: all 0.3s ease;
            }}
            QFrame:hover {{
                background-color: #f1faff;
            }}
        """)

        layout = QtWidgets.QVBoxLayout(card)
        layout.setSpacing(5)

        title = QtWidgets.QLabel(f"Process on {date_str}")
        title.setStyleSheet("font-size:22px; font-weight:bold; color:#0077cc;")

        lblCount = QtWidgets.QLabel(f"Shrimp Count: {shrimpCount}")
        lblBiomass = QtWidgets.QLabel(f"Biomass: {biomass:.3f} g")
        lblFeed = QtWidgets.QLabel(f"Feed Measurement: {feed:.3f} g")
        lblSync = QtWidgets.QLabel(f"Status: {'Synced' if synced else 'Not Synced'}")

        for lbl in [lblCount, lblBiomass, lblFeed, lblSync]:
            lbl.setStyleSheet("font-size:20px;")

        layout.addWidget(title)
        layout.addWidget(lblCount)
        layout.addWidget(lblBiomass)
        layout.addWidget(lblFeed)
        layout.addWidget(lblSync)

        # Card click event
        card.mousePressEvent = lambda event, rid=rec[0], c=card: self.select_record(rid, c)

        return card

    def select_record(self, record_id, card_widget):
        """Visually highlight selected card and remember ID for deletion."""
        # Reset previous selection
        if self.selectedCard:
            # Remove the blue glow from previously selected card
            self.selectedCard.setGraphicsEffect(None)

        # Apply a glowing blue shadow effect to the new selection
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QtGui.QColor("#0078D7"))
        shadow.setOffset(0, 0)
        card_widget.setGraphicsEffect(shadow)

        # Store selected record info
        self.selectedRecordId = record_id
        self.selectedCard = card_widget

    def sync_data(self):
        synced_count = sync_biomass_records(self.user_id)
        QtWidgets.QMessageBox.information(self, "Sync Complete", f"{synced_count} record(s) synced to MongoDB Atlas.")
        self.load_records()

    def delete_selected(self):
        if not self.selectedRecordId:
            QtWidgets.QMessageBox.warning(self, "Delete Record", "Please select a record to delete first.")
            return

        confirm = QtWidgets.QMessageBox.question(
            self, "Confirm Delete", "Are you sure you want to delete this record?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            delete_record(self.selectedRecordId, self.user_id)
            self.selectedRecordId = None
            self.selectedCard = None
            self.load_records()

    def go_back(self):
        self.parent.update_recent()
        self.parent.showFullScreen()
        self.close()
