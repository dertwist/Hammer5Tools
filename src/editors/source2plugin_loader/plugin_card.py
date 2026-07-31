import os
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QPixmap, QIcon, QCursor
from src.editors.source2plugin_loader.github_api import ImageLoaderWorker
from src.editors.source2plugin_loader.installer import is_plugin_installed, get_installed_plugin_path
import src.resources_rc

class PluginCardWidget(QFrame):
    """
    Compact card widget representing a single plugin repository.
    Uses sharp stylesheet borders and clean SVG icons matching Valve dark theme.
    """
    card_clicked = Signal(dict)
    install_requested = Signal(dict)
    open_folder_requested = Signal(str)

    def __init__(self, repo_data: dict, parent=None):
        super().__init__(parent)
        self.repo_data = repo_data
        self.full_name = repo_data.get("full_name", "Unknown/Plugin")
        self.owner = repo_data.get("owner", {}).get("login", "")
        self.repo_name = repo_data.get("name", "")
        self.description = repo_data.get("description") or "No description provided."
        self.stars = repo_data.get("stargazers_count", 0)
        self.html_url = repo_data.get("html_url", "")
        self.avatar_url = repo_data.get("owner", {}).get("avatar_url", "")
        self.topics = repo_data.get("topics", [])

        self._image_worker = None
        self.init_ui()
        self.refresh_installed_state()
        self.load_avatar()

    def init_ui(self):
        self.setObjectName("pluginCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumWidth(240)
        self.setMinimumHeight(150)
        self.setMaximumHeight(200)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        self.setStyleSheet("""
            QFrame#pluginCard {
                background-color: #1C1C1C;
                border: 1px solid #363639;
                border-radius: 0px;
            }
            QFrame#pluginCard:hover {
                border: 1px solid #3A78C4;
                background-color: #222226;
            }
            QLabel {
                background: transparent;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # --- Header: Avatar + Name/Author + Stars ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        self.avatar_label = QLabel(self)
        self.avatar_label.setFixedSize(36, 36)
        self.avatar_label.setStyleSheet("background-color: #28282B; border-radius: 0px; border: 1px solid #363639;")
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setText(self.owner[:1].upper() if self.owner else "P")
        top_layout.addWidget(self.avatar_label)

        title_v = QVBoxLayout()
        title_v.setSpacing(1)

        self.title_label = QLabel(self.repo_name, self)
        self.title_label.setStyleSheet("font: 700 10.5pt 'Segoe UI'; color: #FFFFFF;")
        title_v.addWidget(self.title_label)

        self.author_label = QLabel(f"by {self.owner}", self)
        self.author_label.setStyleSheet("font: 600 8.5pt 'Segoe UI'; color: #9D9D9D;")
        title_v.addWidget(self.author_label)

        top_layout.addLayout(title_v, 1)

        # Star badge
        star_container = QWidget(self)
        star_container.setStyleSheet("""
            background-color: #26262A;
            border: 1px solid #363639;
            border-radius: 0px;
        """)
        star_h = QHBoxLayout(star_container)
        star_h.setContentsMargins(5, 2, 6, 2)
        star_h.setSpacing(4)

        star_icon_lbl = QLabel(star_container)
        star_icon_lbl.setPixmap(QIcon(":/icons/star_16dp.svg").pixmap(QSize(13, 13)))
        star_h.addWidget(star_icon_lbl)

        star_txt_lbl = QLabel(self.format_stars(self.stars), star_container)
        star_txt_lbl.setStyleSheet("color: #E3E3E3; font: 700 8pt 'Segoe UI';")
        star_h.addWidget(star_txt_lbl)

        top_layout.addWidget(star_container, 0, Qt.AlignTop)

        layout.addLayout(top_layout)

        # --- Body: Description ---
        self.desc_label = QLabel(self.description, self)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("font: 400 8.5pt 'Segoe UI'; color: #B0B0B0;")
        self.desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.desc_label, 1)

        # --- Footer: Tags + Action Buttons ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(6)

        # Topics/Tags pills
        if self.topics:
            t_str = " ".join([f"#{t}" for t in self.topics[:2]])
            tag_label = QLabel(t_str, self)
            tag_label.setStyleSheet("color: #7A808A; font: 600 8pt 'Segoe UI';")
            bottom_layout.addWidget(tag_label)

        bottom_layout.addStretch()

        self.install_btn = QPushButton("Install", self)
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A78C4;
                color: #FFFFFF;
                border: 1px solid #4A88D4;
                border-radius: 0px;
                padding: 4px 12px;
                font: 700 8.5pt 'Segoe UI';
            }
            QPushButton:hover {
                background-color: #4A88D4;
            }
            QPushButton:pressed {
                background-color: #2D60A0;
            }
        """)
        self.install_btn.clicked.connect(self.on_install_clicked)
        bottom_layout.addWidget(self.install_btn)

        layout.addLayout(bottom_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.card_clicked.emit(self.repo_data)
        super().mousePressEvent(event)

    def load_avatar(self):
        if self.avatar_url:
            self._image_worker = ImageLoaderWorker(self.avatar_url, self)
            self._image_worker.image_loaded.connect(self.on_avatar_loaded)
            self._image_worker.start()

    def on_avatar_loaded(self, url, pixmap):
        if url == self.avatar_url and not pixmap.isNull():
            scaled = pixmap.scaled(36, 36, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(scaled)

    def refresh_installed_state(self):
        installed = is_plugin_installed(self.full_name)
        if installed:
            self.install_btn.setText("Installed")
            self.install_btn.setIcon(QIcon(":/icons/check_16dp.svg"))
            self.install_btn.setIconSize(QSize(14, 14))
            self.install_btn.setStyleSheet("""
                QPushButton {
                    background-color: #254B30;
                    color: #A3E2B6;
                    border: 1px solid #356742;
                    border-radius: 0px;
                    padding: 4px 10px;
                    font: 700 8.5pt 'Segoe UI';
                }
                QPushButton:hover {
                    background-color: #2D5B3A;
                }
            """)
        else:
            self.install_btn.setText("Install")
            self.install_btn.setIcon(QIcon())
            self.install_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3A78C4;
                    color: #FFFFFF;
                    border: 1px solid #4A88D4;
                    border-radius: 0px;
                    padding: 4px 12px;
                    font: 700 8.5pt 'Segoe UI';
                }
                QPushButton:hover {
                    background-color: #4A88D4;
                }
            """)

    def on_install_clicked(self):
        if is_plugin_installed(self.full_name):
            path = get_installed_plugin_path(self.full_name)
            if os.path.exists(path):
                self.open_folder_requested.emit(path)
            else:
                self.install_requested.emit(self.repo_data)
        else:
            self.install_requested.emit(self.repo_data)

    @staticmethod
    def format_stars(count: int) -> str:
        if count >= 1000:
            return f"{count / 1000:.1f}k"
        return str(count)
