from gui import resources_rc
from gui.forms.about.ui_main import Ui_documentation_dialog
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QUrl, QEvent, Qt
from PySide6.QtGui import QDesktopServices, QImage, QColor, QPixmap
from gui.common import apply_title_bar_theme, discord_feedback_channel
from gui.settings.common import get_settings_bool, set_settings_bool
from gui.styles import theme


def _get_themed_header_pixmap(text_color_hex: str) -> QPixmap:
    img = QImage(":/images/help/header.png")
    if not img.isNull():
        color = QColor(text_color_hex)
        for y in range(img.height()):
            for x in range(330, img.width()):
                c = img.pixelColor(x, y)
                if c.alpha() > 0:
                    img.setPixelColor(x, y, QColor(color.red(), color.green(), color.blue(), c.alpha()))
        pm = QPixmap.fromImage(img)
    else:
        pm = QPixmap(":/images/help/header.png")
    return pm.scaled(520, 130, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


class AboutDialog(QDialog):
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.ui = Ui_documentation_dialog()
        self.ui.setupUi(self)
        self.setFixedSize(680, 710)
        self.ui.version.setText(f"Version: {version}")
        self._refresh_theme_elements()
        apply_title_bar_theme(self)

        self.ui.request_a_new_feature_button.clicked.connect(self.open_request_a_new_feature)
        self.ui.open_documentation_button.clicked.connect(self.open_documentation)
        self.ui.open_radio_sound_guide_button.clicked.connect(self.open_radio_sound_guide)
        self.ui.open_smart_props_guide_button.clicked.connect(self.open_smart_props_guide)
        self.ui.watch_video_button.clicked.connect(self.open_video_tutorial)
        self.ui.support_button.clicked.connect(self.open_support_page)
        self.ui.close_button.clicked.connect(self.accept)
        self.ui.dont_show_button.clicked.connect(self.disable_show_on_startup_and_close)

    def _refresh_theme_elements(self):
        active_theme = theme.get_theme()
        self.ui.label.setPixmap(_get_themed_header_pixmap(active_theme.text))
        self.ui.special_thanks_label.setText(
            f'Special thanks: <a href="https://github.com/LaplaceTor" style="color: {active_theme.accent}; text-decoration: none;">LaplaceTor</a>, '
            f'<a href="https://github.com/Andrew900460" style="color: {active_theme.accent}; text-decoration: none;">Andrew900460</a>'
        )

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange):
            self._refresh_theme_elements()
            apply_title_bar_theme(self)

    def open_support_page(self):
        QDesktopServices.openUrl(QUrl("https://dertwist.gumroad.com/l/mallet"))

    def open_request_a_new_feature(self):
        QDesktopServices.openUrl(QUrl(discord_feedback_channel))

    def open_documentation(self):
        QDesktopServices.openUrl(QUrl("https://hammer5tools.github.io/docs.html"))

    def open_radio_sound_guide(self):
        QDesktopServices.openUrl(QUrl("https://hammer5tools.github.io/docs.html#radio-sound"))

    def open_smart_props_guide(self):
        QDesktopServices.openUrl(QUrl("https://hammer5tools.github.io/docs.html#smartprop-guide"))

    def open_video_tutorial(self):
        QDesktopServices.openUrl(QUrl("https://www.youtube.com/watch?v=-xIHW65kNYA"))

    def disable_show_on_startup_and_close(self):
        set_settings_bool('APP', 'show_about_on_startup', False)
        self.accept()
