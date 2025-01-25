from src.about.ui_main import Ui_documentation_dialog
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from src.common import *
class AboutDialog(QDialog):
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.ui = Ui_documentation_dialog()
        self.ui.setupUi(self)
        self.ui.version.setText(f"Version: {version}")
        enable_dark_title_bar(self)
        self.ui.request_a_new_feature_button.clicked.connect(self.open_request_a_new_feature)
        self.ui.open_documentation_button.clicked.connect(self.open_documentation)

    def open_request_a_new_feature(self):
        QDesktopServices.openUrl(QUrl(discord_feedback_channel))
    def open_documentation(self):
        QDesktopServices.openUrl(QUrl("https://twist-1.gitbook.io/hammer5tools"))
