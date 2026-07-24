from src.forms.about.ui_main import Ui_documentation_dialog
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from src.common import *
from src.settings.common import get_settings_bool, set_settings_bool

class AboutDialog(QDialog):
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.ui = Ui_documentation_dialog()
        self.ui.setupUi(self)
        self.ui.version.setText(f"Version: {version}")
        enable_dark_title_bar(self)

        # Connect buttons
        self.ui.request_a_new_feature_button.clicked.connect(self.open_request_a_new_feature)
        self.ui.open_documentation_button.clicked.connect(self.open_documentation)
        self.ui.open_radio_sound_guide_button.clicked.connect(self.open_radio_sound_guide)
        self.ui.watch_video_button.clicked.connect(self.open_video_tutorial)
        self.ui.close_button.clicked.connect(self.accept)

        # Connect Don't show on startup button
        self.ui.dont_show_button.clicked.connect(self.disable_show_on_startup_and_close)

    def open_request_a_new_feature(self):
        QDesktopServices.openUrl(QUrl(discord_feedback_channel))

    def open_documentation(self):
        QDesktopServices.openUrl(QUrl("https://hammer5tools.github.io/docs.html"))

    def open_radio_sound_guide(self):
        QDesktopServices.openUrl(QUrl("https://hammer5tools.github.io/docs.html#radio-sound"))

    def open_video_tutorial(self):
        QDesktopServices.openUrl(QUrl("https://www.youtube.com/watch?v=-xIHW65kNYA"))

    def disable_show_on_startup_and_close(self):
        set_settings_bool('APP', 'show_about_on_startup', False)
        self.accept()
