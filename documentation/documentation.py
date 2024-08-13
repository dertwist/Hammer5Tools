from documentation.ui_documentation_dialog import Ui_documentation_dialog
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
class Documentation_Dialog(QDialog):
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.ui = Ui_documentation_dialog()
        self.ui.setupUi(self)
        self.ui.version.setText(f"Version: {version}")
        self.ui.report_a_bug_button.clicked.connect(self.open_report_bug_link)
        self.ui.github_page_button.clicked.connect(self.open_github_page_link)
        self.ui.online_help_batchcreator_button.clicked.connect(self.open_online_help_batchcreator_link)
        self.ui.online_help_soundevent_editor_button.clicked.connect(self.open_online_help_soundevent_editor_link)
        self.ui.online_help_loading_ediotor_button.clicked.connect(self.open_online_help_loading_ediotor)

    def open_report_bug_link(self):
        QDesktopServices.openUrl(QUrl("https://discord.gg/mMaub4jCBa"))

    def open_github_page_link(self):
        QDesktopServices.openUrl(QUrl("https://github.com/dertwist/Hammer5Tools"))

    def open_online_help_batchcreator_link(self):
        QDesktopServices.openUrl(
            QUrl("https://fish-banana-d65.notion.site/BatchCreator-df8191edbba3490c988e00d820c9419e?pvs=4"))

    def open_online_help_soundevent_editor_link(self):
        QDesktopServices.openUrl(
            QUrl("https://fish-banana-d65.notion.site/SoundEvent-Editor-32db6d9cb21e452abfaabf61988c9d54?pvs=4"))

    def open_online_help_loading_ediotor(self):
        QDesktopServices.openUrl(
            QUrl("https://fish-banana-d65.notion.site/Loading-Editor-1dab2db30c404510aaa895ca834b14f3?pvs=4"))