import os
import webbrowser
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QTabWidget, QWidget, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from src.editors.source2plugin_loader.github_api import GitHubReadmeWorker
from src.editors.source2plugin_loader.installer import (
    is_plugin_installed, get_installed_plugin_path, uninstall_plugin, get_plugins_dir
)

class PluginDetailsDialog(QDialog):
    """
    Modal dialog displaying comprehensive details and README for a plugin repository.
    """
    install_requested = Signal(dict)
    uninstall_requested = Signal(str)

    def __init__(self, repo_data: dict, token="", parent=None):
        super().__init__(parent)
        self.repo_data = repo_data
        self.token = token
        self.full_name = repo_data.get("full_name", "")
        self.owner = repo_data.get("owner", {}).get("login", "")
        self.repo_name = repo_data.get("name", "")
        self.html_url = repo_data.get("html_url", "")
        self.description = repo_data.get("description") or "No description provided."
        self.stars = repo_data.get("stargazers_count", 0)
        self.forks = repo_data.get("forks_count", 0)
        self.open_issues = repo_data.get("open_issues_count", 0)
        self.license_name = repo_data.get("license", {}).get("name") if repo_data.get("license") else "No License specified"
        self.clone_url = repo_data.get("clone_url", "")

        self._readme_worker = None
        self.init_ui()
        self.fetch_readme()

    def init_ui(self):
        self.setWindowTitle(f"Plugin Details - {self.full_name}")
        self.resize(700, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #151515;
                color: #E3E3E3;
            }
            QLabel {
                color: #E3E3E3;
            }
            QTabWidget::pane {
                border: 1px solid #363639;
                background-color: #1C1C1C;
            }
            QTabBar::tab {
                background-color: #151515;
                color: #9D9D9D;
                padding: 6px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font: 600 9pt 'Segoe UI';
            }
            QTabBar::tab:selected {
                background-color: #1C1C1C;
                color: #FFFFFF;
                border-top: 2px solid #3A78C4;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Box
        header_box = QFrame(self)
        header_box.setStyleSheet("background-color: #1C1C1C; border: 1px solid #363639; border-radius: 6px; padding: 8px;")
        h_layout = QHBoxLayout(header_box)

        info_v = QVBoxLayout()
        title_label = QLabel(f"<b>{self.repo_name}</b>", header_box)
        title_label.setStyleSheet("font-size: 14pt; color: #FFFFFF;")
        info_v.addWidget(title_label)

        author_label = QLabel(f"Repository: {self.full_name}", header_box)
        author_label.setStyleSheet("color: #9D9D9D; font-size: 9pt;")
        info_v.addWidget(author_label)

        h_layout.addLayout(info_v, 1)

        # Stats column
        stats_v = QVBoxLayout()
        stats_v.setAlignment(Qt.AlignRight)
        stars_label = QLabel(f"⭐ {self.stars}  |  🍴 {self.forks}  |  🐞 {self.open_issues}", header_box)
        stars_label.setStyleSheet("font-weight: bold; font-size: 9.5pt;")
        stats_v.addWidget(stars_label)

        license_label = QLabel(f"License: {self.license_name}", header_box)
        license_label.setStyleSheet("color: #9D9D9D; font-size: 8.5pt;")
        stats_v.addWidget(license_label)

        h_layout.addLayout(stats_v)
        layout.addWidget(header_box)

        # Main Tab Widget
        self.tabs = QTabWidget(self)
        
        # Overview Tab
        overview_tab = QWidget()
        ov_layout = QVBoxLayout(overview_tab)
        ov_layout.setContentsMargins(12, 12, 12, 12)
        ov_layout.setSpacing(8)

        desc_title = QLabel("Description:", overview_tab)
        desc_title.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        ov_layout.addWidget(desc_title)

        desc_body = QLabel(self.description, overview_tab)
        desc_body.setWordWrap(True)
        desc_body.setStyleSheet("color: #D0D0D0; background-color: #151515; padding: 8px; border-radius: 4px; border: 1px solid #363639;")
        ov_layout.addWidget(desc_body)

        target_title = QLabel("Installation Destination:", overview_tab)
        target_title.setStyleSheet("font-weight: bold; color: #FFFFFF; margin-top: 8px;")
        ov_layout.addWidget(target_title)

        target_path = str(get_plugins_dir() / self.full_name.replace("/", "_"))
        path_label = QLabel(target_path, overview_tab)
        path_label.setStyleSheet("color: #3A78C4; font-family: Consolas; background-color: #151515; padding: 6px; border-radius: 4px; border: 1px solid #363639;")
        ov_layout.addWidget(path_label)

        clone_title = QLabel("Clone URL:", overview_tab)
        clone_title.setStyleSheet("font-weight: bold; color: #FFFFFF; margin-top: 8px;")
        ov_layout.addWidget(clone_title)

        clone_label = QLabel(self.clone_url or "N/A", overview_tab)
        clone_label.setStyleSheet("color: #9D9D9D; font-family: Consolas; background-color: #151515; padding: 6px; border-radius: 4px; border: 1px solid #363639;")
        ov_layout.addWidget(clone_label)

        ov_layout.addStretch()
        self.tabs.addTab(overview_tab, "Overview")

        # Readme Tab
        readme_tab = QWidget()
        rm_layout = QVBoxLayout(readme_tab)
        rm_layout.setContentsMargins(8, 8, 8, 8)

        self.readme_text = QTextEdit(readme_tab)
        self.readme_text.setReadOnly(True)
        self.readme_text.setPlaceholderText("Loading README...")
        self.readme_text.setStyleSheet("""
            QTextEdit {
                background-color: #151515;
                color: #E3E3E3;
                border: 1px solid #363639;
                font-family: 'Segoe UI', Consolas, sans-serif;
                font-size: 9.5pt;
            }
        """)
        rm_layout.addWidget(self.readme_text)
        self.tabs.addTab(readme_tab, "README")

        layout.addWidget(self.tabs, 1)

        # Footer Actions Bar
        footer_layout = QHBoxLayout()

        github_btn = QPushButton("View on GitHub 🌐", self)
        github_btn.setStyleSheet("""
            QPushButton {
                background-color: #26262A; color: #E3E3E3; border: 1px solid #363639;
                border-radius: 3px; padding: 6px 12px; font: 600 9pt 'Segoe UI';
            }
            QPushButton:hover { background-color: #323236; }
        """)
        github_btn.clicked.connect(lambda: webbrowser.open(self.html_url))
        footer_layout.addWidget(github_btn)

        footer_layout.addStretch()

        self.install_btn = QPushButton("Install Plugin", self)
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A78C4; color: #FFFFFF; border: none;
                border-radius: 3px; padding: 6px 16px; font: 700 9.5pt 'Segoe UI';
            }
            QPushButton:hover { background-color: #4A88D4; }
        """)
        self.install_btn.clicked.connect(self.on_install_btn_clicked)
        footer_layout.addWidget(self.install_btn)

        self.uninstall_btn = QPushButton("Uninstall", self)
        self.uninstall_btn.setStyleSheet("""
            QPushButton {
                background-color: #6B2323; color: #FFD1D1; border: 1px solid #8C3030;
                border-radius: 3px; padding: 6px 12px; font: 600 9pt 'Segoe UI';
            }
            QPushButton:hover { background-color: #822C2C; }
        """)
        self.uninstall_btn.clicked.connect(self.on_uninstall_clicked)
        footer_layout.addWidget(self.uninstall_btn)

        close_btn = QPushButton("Close", self)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #26262A; color: #E3E3E3; border: 1px solid #363639;
                border-radius: 3px; padding: 6px 12px; font: 600 9pt 'Segoe UI';
            }
            QPushButton:hover { background-color: #323236; }
        """)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)

        layout.addLayout(footer_layout)
        self.update_action_buttons()

    def fetch_readme(self):
        if self.owner and self.repo_name:
            self._readme_worker = GitHubReadmeWorker(self.owner, self.repo_name, self.token, self)
            self._readme_worker.readme_finished.connect(self.on_readme_loaded)
            self._readme_worker.readme_failed.connect(lambda msg: self.readme_text.setPlainText(msg))
            self._readme_worker.start()

    def on_readme_loaded(self, content):
        if content:
            # Render plain markdown text or set as plain text
            self.readme_text.setMarkdown(content)
        else:
            self.readme_text.setPlainText("No README content found.")

    def update_action_buttons(self):
        installed = is_plugin_installed(self.full_name)
        if installed:
            self.install_btn.setText("Open Installed Directory")
            self.install_btn.setStyleSheet("""
                QPushButton {
                    background-color: #254B30; color: #A3E2B6; border: 1px solid #356742;
                    border-radius: 3px; padding: 6px 16px; font: 700 9.5pt 'Segoe UI';
                }
                QPushButton:hover { background-color: #2D5B3A; }
            """)
            self.uninstall_btn.show()
        else:
            self.install_btn.setText("Install Plugin")
            self.install_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3A78C4; color: #FFFFFF; border: none;
                    border-radius: 3px; padding: 6px 16px; font: 700 9.5pt 'Segoe UI';
                }
                QPushButton:hover { background-color: #4A88D4; }
            """)
            self.uninstall_btn.hide()

    def on_install_btn_clicked(self):
        if is_plugin_installed(self.full_name):
            path = get_installed_plugin_path(self.full_name)
            if os.path.exists(path):
                os.startfile(path)
        else:
            self.install_requested.emit(self.repo_data)
            self.accept()

    def on_uninstall_clicked(self):
        if uninstall_plugin(self.full_name):
            self.uninstall_requested.emit(self.full_name)
            self.update_action_buttons()
