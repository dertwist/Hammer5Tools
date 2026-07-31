import webbrowser
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QWidget
)
from PySide6.QtCore import Qt, QUrl, QSize, Signal
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
import src.resources_rc

class BrowserSidePanel(QFrame):
    """
    Embedded dark-themed web browser side panel with fixed-height controls matching Valve toolbar styling.
    """
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_url = ""
        self.init_ui()

    def init_ui(self):
        self.setObjectName("browserSidePanel")
        self.setStyleSheet("""
            QFrame#browserSidePanel {
                background-color: #151515;
                border-left: 1px solid #363639;
            }
            QLabel { color: #E3E3E3; font: 600 9pt 'Segoe UI'; }
            QLineEdit {
                background-color: #1D1D1F;
                color: #9D9D9D;
                border: 1px solid #363639;
                border-radius: 0px;
                padding: 0px 8px;
                height: 26px;
                min-height: 26px;
                max-height: 26px;
                font: 8.5pt 'Consolas', sans-serif;
            }
            QPushButton {
                background-color: #26262A;
                color: #E3E3E3;
                border: 1px solid #363639;
                border-radius: 0px;
                padding: 0px 8px;
                height: 26px;
                min-height: 26px;
                max-height: 26px;
                font: 600 9pt 'Segoe UI';
            }
            QPushButton:hover {
                background-color: #323236;
                border-color: #414956;
            }
            QPushButton:pressed {
                background-color: #414956;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Header Navigation Bar ---
        nav_bar = QFrame(self)
        nav_bar.setStyleSheet("background-color: #1C1C1C; border-bottom: 1px solid #363639; padding: 2px 4px;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(4, 3, 4, 3)
        nav_layout.setSpacing(4)

        CONTROL_HEIGHT = 26

        self.back_btn = QPushButton(nav_bar)
        self.back_btn.setIcon(QIcon(":/icons/chevron_left_24dp.svg"))
        self.back_btn.setIconSize(QSize(16, 16))
        self.back_btn.setToolTip("Back")
        self.back_btn.setFixedWidth(28)
        self.back_btn.setFixedHeight(CONTROL_HEIGHT)
        nav_layout.addWidget(self.back_btn)

        self.forward_btn = QPushButton(nav_bar)
        self.forward_btn.setIcon(QIcon(":/icons/chevron_right_24dp.svg"))
        self.forward_btn.setIconSize(QSize(16, 16))
        self.forward_btn.setToolTip("Forward")
        self.forward_btn.setFixedWidth(28)
        self.forward_btn.setFixedHeight(CONTROL_HEIGHT)
        nav_layout.addWidget(self.forward_btn)

        self.reload_btn = QPushButton(nav_bar)
        self.reload_btn.setIcon(QIcon(":/icons/sync_24dp.svg"))
        self.reload_btn.setIconSize(QSize(16, 16))
        self.reload_btn.setToolTip("Reload")
        self.reload_btn.setFixedWidth(28)
        self.reload_btn.setFixedHeight(CONTROL_HEIGHT)
        nav_layout.addWidget(self.reload_btn)

        self.url_label = QLineEdit(nav_bar)
        self.url_label.setReadOnly(True)
        self.url_label.setPlaceholderText("Select a plugin to inspect repository...")
        self.url_label.setFixedHeight(CONTROL_HEIGHT)
        nav_layout.addWidget(self.url_label, 1)

        self.ext_browser_btn = QPushButton(nav_bar)
        self.ext_browser_btn.setIcon(QIcon(":/icons/open_in_new_16dp.svg"))
        self.ext_browser_btn.setIconSize(QSize(16, 16))
        self.ext_browser_btn.setToolTip("Open in external browser")
        self.ext_browser_btn.setFixedWidth(30)
        self.ext_browser_btn.setFixedHeight(CONTROL_HEIGHT)
        self.ext_browser_btn.clicked.connect(self.open_external)
        nav_layout.addWidget(self.ext_browser_btn)

        self.close_btn = QPushButton(nav_bar)
        self.close_btn.setIcon(QIcon(":/icons/close_16dp.svg"))
        self.close_btn.setIconSize(QSize(16, 16))
        self.close_btn.setToolTip("Close side panel")
        self.close_btn.setFixedWidth(30)
        self.close_btn.setFixedHeight(CONTROL_HEIGHT)
        self.close_btn.clicked.connect(self.on_close_clicked)
        nav_layout.addWidget(self.close_btn)

        layout.addWidget(nav_bar)

        # --- WebEngine View Body ---
        self.web_view = QWebEngineView(self)
        self.web_view.page().setBackgroundColor(QColor("#151515"))
        
        # Force dark mode natively on QtWebEngine pages
        settings = self.web_view.page().settings()
        if hasattr(QWebEngineSettings, 'ForceDarkMode'):
            settings.setAttribute(QWebEngineSettings.ForceDarkMode, True)

        self.web_view.urlChanged.connect(self.on_url_changed)
        self.web_view.titleChanged.connect(self.on_title_changed)

        self.back_btn.clicked.connect(self.web_view.back)
        self.forward_btn.clicked.connect(self.web_view.forward)
        self.reload_btn.clicked.connect(self.web_view.reload)

        layout.addWidget(self.web_view, 1)

    def load_url(self, url: str):
        if not url:
            return
        self.current_url = url
        self.url_label.setText(url)
        self.web_view.setUrl(QUrl(url))

    def on_url_changed(self, qurl: QUrl):
        self.current_url = qurl.toString()
        self.url_label.setText(self.current_url)

    def on_title_changed(self, title: str):
        if title:
            self.url_label.setToolTip(title)

    def open_external(self):
        if self.current_url:
            webbrowser.open(self.current_url)

    def on_close_clicked(self):
        self.hide()
        self.closed.emit()
