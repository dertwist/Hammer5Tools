import os
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QPushButton,
    QLabel, QScrollArea, QFrame, QGridLayout, QProgressBar, QMessageBox,
    QDialog, QDialogButtonBox, QCheckBox, QSplitter, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QCursor

from src.styles.qt_global_stylesheet import QT_Stylesheet_global
from src.settings.main import get_settings_value, set_settings_value
from src.editors.source2plugin_loader.github_api import GitHubSearchWorker, load_disk_cache
from src.editors.source2plugin_loader.plugin_card import PluginCardWidget
from src.editors.source2plugin_loader.browser_panel import BrowserSidePanel
from src.editors.source2plugin_loader.installer import (
    PluginDownloadWorker, get_plugins_dir, is_plugin_installed, get_installed_plugins_db, uninstall_plugin
)
import src.resources_rc

class GitHubTokenDialog(QDialog):
    """
    Dialog to configure optional GitHub Personal Access Token to bypass 60 req/hr rate limits.
    Uses sharp Valve UI styling with fixed control heights.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GitHub API Token Settings")
        self.setMinimumWidth(440)
        self.setStyleSheet("""
            QDialog { background-color: #151515; color: #E3E3E3; }
            QLabel { color: #E3E3E3; font-size: 9pt; }
            QLineEdit {
                background-color: #1D1D1F; color: #E3E3E3;
                border: 1px solid #363639; border-radius: 0px; padding: 4px 8px;
                height: 26px; min-height: 26px; max-height: 26px;
            }
            QPushButton {
                background-color: #26262A; color: #E3E3E3; border: 1px solid #363639;
                border-radius: 0px; padding: 0px 14px; font: 600 9pt 'Segoe UI';
                height: 26px; min-height: 26px; max-height: 26px;
            }
            QPushButton:hover { background-color: #323236; border-color: #414956; }
            QPushButton:pressed { background-color: #414956; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        info_label = QLabel(
            "<b>GitHub Rate Limit Configuration</b><br>"
            "Unauthenticated API searches are limited to 60 requests/hour.<br>"
            "Providing a Personal Access Token increases your limit to 5,000 requests/hour.",
            self
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        token_label = QLabel("Personal Access Token (PAT):", self)
        layout.addWidget(token_label)

        self.token_edit = QLineEdit(self)
        self.token_edit.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.token_edit.setText(get_settings_value("GITHUB", "token", ""))
        self.token_edit.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxx")
        self.token_edit.setFixedHeight(26)
        layout.addWidget(self.token_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save_and_accept(self):
        set_settings_value("GITHUB", "token", self.token_edit.text().strip())
        self.accept()


class Source2PluginLoaderWidget(QWidget):
    """
    Main Source2PluginLoader marketplace tab widget.
    Enforces a strict fixed height (26px) across all toolbar inputs, buttons, and combo boxes for pixel alignment.
    Connects author hyperlinks to embedded dark web browser.
    """
    def __init__(self, update_title=None, parent=None):
        super().__init__(parent)
        self.update_title = update_title
        self.current_page = 1
        self.total_count = 0
        self.cards = []
        self.raw_fetched_items = []
        self.active_search_worker = None
        self.active_download_workers = {}

        self.init_ui()
        # Startup: load cached results or fetch initial data
        QTimer.singleShot(150, lambda: self.do_search(force_refresh=False))

    def init_ui(self):
        self.setObjectName("Source2PluginLoaderWidget")
        self.setStyleSheet(QT_Stylesheet_global + """
            QWidget#Source2PluginLoaderWidget {
                background-color: #151515;
            }
            QLabel {
                color: #E3E3E3;
            }
            QLineEdit, QComboBox {
                background-color: #1D1D1F;
                color: #E3E3E3;
                border: 1px solid #363639;
                border-radius: 0px;
                padding: 0px 8px;
                height: 26px;
                min-height: 26px;
                max-height: 26px;
                font: 600 9.5pt "Segoe UI";
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #3A78C4;
            }
            QPushButton {
                background-color: #26262A;
                color: #E3E3E3;
                border: 1px solid #363639;
                border-radius: 0px;
                padding: 0px 10px;
                height: 26px;
                min-height: 26px;
                max-height: 26px;
                font: 600 9.5pt "Segoe UI";
            }
            QPushButton:hover {
                background-color: #323236;
                border-color: #414956;
            }
            QPushButton:pressed {
                background-color: #414956;
            }
            QCheckBox {
                height: 26px;
                min-height: 26px;
                max-height: 26px;
                color: #E3E3E3;
                font: 600 9pt 'Segoe UI';
            }
            QScrollArea {
                border: none;
                background-color: #151515;
            }
            QSplitter::handle {
                background-color: #363639;
                width: 2px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)

        CONTROL_HEIGHT = 26

        # =========================================================================
        # Main Splitter: Left (Entries List + Control Header + Footer), Right (Embedded Browser)
        # =========================================================================
        self.main_splitter = QSplitter(Qt.Horizontal, self)
        self.main_splitter.splitterMoved.connect(lambda pos, idx: self.relayout_cards())

        # --- Left Pane: Control Header Bar + Scrollable Card Grid + Footer Pagination ---
        self.left_pane = QWidget()
        left_layout = QVBoxLayout(self.left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        # Control Header Bar (positioned directly inside Left Pane)
        top_bar = QFrame(self.left_pane)
        top_bar.setStyleSheet("background-color: #1C1C1C; border: 1px solid #363639; border-radius: 0px;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(6, 4, 6, 4)
        top_layout.setSpacing(6)
        top_layout.setAlignment(Qt.AlignVCenter)

        # Search Input
        self.search_edit = QLineEdit(top_bar)
        self.search_edit.setPlaceholderText("Filter or search plugins...")
        self.search_edit.setMinimumWidth(180)
        self.search_edit.setFixedHeight(CONTROL_HEIGHT)
        self.search_edit.textChanged.connect(self.on_filter_text_changed)
        top_layout.addWidget(self.search_edit, 1)

        # Sort Combo
        sort_lbl = QLabel("Sort:", top_bar)
        sort_lbl.setFixedHeight(CONTROL_HEIGHT)
        top_layout.addWidget(sort_lbl)

        self.sort_combo = QComboBox(top_bar)
        self.sort_combo.addItem(QIcon(":/icons/star_16dp.svg"), "Most Stars", "stars")
        self.sort_combo.addItem(QIcon(":/icons/clock_loader_20_24dp.svg"), "Recently Updated", "updated")
        self.sort_combo.setFixedHeight(CONTROL_HEIGHT)
        self.sort_combo.currentIndexChanged.connect(lambda: self.do_search(force_refresh=False))
        top_layout.addWidget(self.sort_combo)

        # Refresh Marketplace Button
        self.refresh_btn = QPushButton("Refresh", top_bar)
        self.refresh_btn.setIcon(QIcon(":/icons/sync_24dp.svg"))
        self.refresh_btn.setIconSize(QSize(15, 15))
        self.refresh_btn.setToolTip("Fetch fresh repository data from GitHub API")
        self.refresh_btn.setFixedHeight(CONTROL_HEIGHT)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A78C4; color: #FFFFFF; border: 1px solid #4A88D4;
                border-radius: 0px; font: 700 9pt 'Segoe UI'; padding: 0px 12px;
                height: 26px; min-height: 26px; max-height: 26px;
            }
            QPushButton:hover { background-color: #4A88D4; }
            QPushButton:pressed { background-color: #2D60A0; }
        """)
        self.refresh_btn.clicked.connect(lambda: self.do_search(force_refresh=True))
        top_layout.addWidget(self.refresh_btn)

        # Installed Only Checkbox
        self.installed_only_cb = QCheckBox("Installed Only", top_bar)
        self.installed_only_cb.setFixedHeight(CONTROL_HEIGHT)
        self.installed_only_cb.toggled.connect(self.on_installed_only_toggled)
        top_layout.addWidget(self.installed_only_cb)

        # Plugins Folder Button
        self.open_folder_btn = QPushButton("Plugins Folder", top_bar)
        self.open_folder_btn.setIcon(QIcon(":/icons/folder_16dp.svg"))
        self.open_folder_btn.setIconSize(QSize(15, 15))
        self.open_folder_btn.setToolTip("Open userdata/source2pluginloader/plugins/")
        self.open_folder_btn.setFixedHeight(CONTROL_HEIGHT)
        self.open_folder_btn.clicked.connect(self.open_plugins_directory)
        top_layout.addWidget(self.open_folder_btn)

        # Token Dialog Button
        self.token_btn = QPushButton("API Token", top_bar)
        self.token_btn.setIcon(QIcon(":/icons/settings_16dp.svg"))
        self.token_btn.setIconSize(QSize(15, 15))
        self.token_btn.setToolTip("Configure GitHub API Token")
        self.token_btn.setFixedHeight(CONTROL_HEIGHT)
        self.token_btn.clicked.connect(self.open_token_dialog)
        top_layout.addWidget(self.token_btn)

        left_layout.addWidget(top_bar)

        # Progress bar
        self.progress_bar = QProgressBar(self.left_pane)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background-color: #151515; border: none; } QProgressBar::chunk { background-color: #3A78C4; }")
        self.progress_bar.hide()
        left_layout.addWidget(self.progress_bar)

        # Scroll Area for Plugin Cards
        self.scroll_area = QScrollArea(self.left_pane)
        self.scroll_area.setWidgetResizable(True)

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: #151515;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.grid_container)
        left_layout.addWidget(self.scroll_area, 1)

        # Status overlay label for empty/loading state
        self.status_overlay = QLabel("Loading plugin repositories...", self.grid_container)
        self.status_overlay.setAlignment(Qt.AlignCenter)
        self.status_overlay.setStyleSheet("font: 600 11pt 'Segoe UI'; color: #9D9D9D; padding: 40px;")
        self.grid_layout.addWidget(self.status_overlay, 0, 0, 1, 1)

        # Footer Pagination Bar (Positioned strictly inside Left Pane)
        footer_bar = QFrame(self.left_pane)
        footer_bar.setStyleSheet("background-color: #1C1C1C; border-top: 1px solid #363639; border-radius: 0px;")
        footer_layout = QHBoxLayout(footer_bar)
        footer_layout.setContentsMargins(6, 3, 6, 3)
        footer_layout.setSpacing(6)
        footer_layout.setAlignment(Qt.AlignVCenter)

        self.results_count_label = QLabel("0 repositories total", footer_bar)
        self.results_count_label.setStyleSheet("color: #9D9D9D; font: 600 9pt 'Segoe UI';")
        self.results_count_label.setFixedHeight(CONTROL_HEIGHT)
        footer_layout.addWidget(self.results_count_label)

        self.cache_status_label = QLabel("", footer_bar)
        self.cache_status_label.setStyleSheet("color: #707070; font: 600 8.5pt 'Segoe UI'; padding-left: 6px;")
        self.cache_status_label.setFixedHeight(CONTROL_HEIGHT)
        footer_layout.addWidget(self.cache_status_label)

        footer_layout.addStretch()

        self.prev_btn = QPushButton("Previous", footer_bar)
        self.prev_btn.setIcon(QIcon(":/icons/chevron_left_24dp.svg"))
        self.prev_btn.setIconSize(QSize(16, 16))
        self.prev_btn.setFixedHeight(CONTROL_HEIGHT)
        self.prev_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self.go_prev_page)
        footer_layout.addWidget(self.prev_btn)

        self.page_label = QLabel("Page 1", footer_bar)
        self.page_label.setStyleSheet("font: 700 9pt 'Segoe UI'; color: #E3E3E3; padding: 0 6px;")
        self.page_label.setFixedHeight(CONTROL_HEIGHT)
        footer_layout.addWidget(self.page_label)

        self.next_btn = QPushButton("Next", footer_bar)
        self.next_btn.setIcon(QIcon(":/icons/chevron_right_24dp.svg"))
        self.next_btn.setIconSize(QSize(16, 16))
        self.next_btn.setFixedHeight(CONTROL_HEIGHT)
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.go_next_page)
        footer_layout.addWidget(self.next_btn)

        left_layout.addWidget(footer_bar)

        self.main_splitter.addWidget(self.left_pane)

        # --- Right Pane: Embedded Browser Side Panel ---
        self.browser_panel = BrowserSidePanel(self.main_splitter)
        self.main_splitter.addWidget(self.browser_panel)

        # Set default splitter ratio (55% Marketplace Grid, 45% Embedded Browser)
        self.main_splitter.setSizes([550, 450])

        main_layout.addWidget(self.main_splitter, 1)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(30, self.relayout_cards)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(20, self.relayout_cards)

    def on_installed_only_toggled(self, checked):
        if checked:
            self.show_installed_plugins()
        else:
            self.do_search(force_refresh=False)

    def on_filter_text_changed(self, text):
        query = text.strip().lower()
        if not query:
            self.populate_cards(self.raw_fetched_items)
            return

        filtered = []
        for item in self.raw_fetched_items:
            name = item.get("name", "").lower()
            full_name = item.get("full_name", "").lower()
            desc = item.get("description", "") or ""
            desc = desc.lower()
            if query in name or query in full_name or query in desc:
                filtered.append(item)

        self.populate_cards(filtered)

    def do_search(self, force_refresh=False):
        query = ""
        sort_by = self.sort_combo.currentData() or "stars"
        token = get_settings_value("GITHUB", "token", "")

        self.clear_cards()
        self.status_overlay.setText("Loading plugins catalog...")
        self.status_overlay.show()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()

        if self.active_search_worker and self.active_search_worker.isRunning():
            self.active_search_worker.terminate()

        self.active_search_worker = GitHubSearchWorker(
            topic="blender-addon",
            query=query,
            sort_by=sort_by,
            page=self.current_page,
            token=token,
            force_refresh=force_refresh,
            parent=self
        )
        self.active_search_worker.search_finished.connect(self.on_search_success)
        self.active_search_worker.search_failed.connect(self.on_search_failure)
        self.active_search_worker.start()

    def on_search_success(self, data: dict):
        self.progress_bar.hide()
        items = data.get("items", [])
        self.raw_fetched_items = items
        self.total_count = data.get("total_count", len(items))

        is_cached = data.get("_is_from_cache", False)
        if is_cached:
            self.cache_status_label.setText("Loaded from local disk cache")
        else:
            self.cache_status_label.setText("Live data from GitHub API")

        rate_rem = data.get("_rate_limit_remaining", "N/A")
        if self.update_title:
            src_str = "Cache" if is_cached else "GitHub API"
            self.update_title(text=f"Marketplace: {len(items)} items ({src_str}, API quota: {rate_rem})")

        filter_text = self.search_edit.text().strip().lower()
        if filter_text:
            self.on_filter_text_changed(filter_text)
        else:
            self.populate_cards(items)

        self.update_pagination()

    def on_search_failure(self, error_msg: str):
        self.progress_bar.hide()
        self.clear_cards()
        self.status_overlay.setText(f"Error: {error_msg}")
        self.status_overlay.show()
        self.results_count_label.setText("Error loading repositories")
        self.cache_status_label.setText("")

    def populate_cards(self, items: list):
        self.clear_cards()
        if not items:
            self.status_overlay.setText("No plugins found matching your query.")
            self.status_overlay.show()
            return

        self.status_overlay.hide()

        for item in items:
            card = PluginCardWidget(item, self.grid_container)
            card.card_clicked.connect(self.on_card_clicked)
            card.author_clicked.connect(self.on_author_clicked)
            card.install_requested.connect(self.install_plugin_action)
            card.open_folder_requested.connect(self.open_folder)
            self.cards.append(card)

        self.relayout_cards()

    def relayout_cards(self):
        """
        Dynamically calculates available grid width and positions cards across multiple columns
        (e.g., 2, 3, or 4 columns) with uniform grid cell spacing.
        """
        if not self.cards:
            return

        viewport_w = self.scroll_area.viewport().width()
        pane_w = self.left_pane.width() - 24
        available_width = max(viewport_w, pane_w)

        # Compute column count based on target card width (~260px)
        card_target_width = 260
        cols = max(1, available_width // card_target_width)

        # Clear existing grid widgets and column stretches
        for card in self.cards:
            self.grid_layout.removeWidget(card)

        for c in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(c, 0)

        # Reflow cards into rows & columns
        for i, card in enumerate(self.cards):
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)

        # Set equal stretch across all active columns so cards distribute evenly
        for c in range(cols):
            self.grid_layout.setColumnStretch(c, 1)

        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

    def on_card_clicked(self, repo_data: dict):
        """
        Clicking any plugin card opens its GitHub repository page immediately in the
        embedded right-side dark web browser pane!
        """
        url = repo_data.get("html_url", "")
        if url:
            if not self.browser_panel.isVisible():
                self.browser_panel.show()
                w = self.width()
                self.main_splitter.setSizes([int(w * 0.55), int(w * 0.45)])
            self.browser_panel.load_url(url)

    def on_author_clicked(self, author_url: str):
        """
        Clicking the author hyperlink opens their GitHub profile in the embedded web browser.
        """
        if author_url:
            if not self.browser_panel.isVisible():
                self.browser_panel.show()
                w = self.width()
                self.main_splitter.setSizes([int(w * 0.55), int(w * 0.45)])
            self.browser_panel.load_url(author_url)

    def show_installed_plugins(self):
        self.clear_cards()
        db = get_installed_plugins_db()
        items = []
        for full_name, data in db.items():
            items.append({
                "full_name": full_name,
                "name": data.get("name", full_name.split("/")[-1]),
                "owner": {"login": data.get("owner", full_name.split("/")[0])},
                "stargazers_count": data.get("stargazers_count", 0),
                "description": data.get("description", ""),
                "html_url": data.get("html_url", ""),
                "topics": ["installed"]
            })

        self.total_count = len(items)
        self.raw_fetched_items = items
        self.results_count_label.setText(f"{self.total_count} installed plugins")
        self.cache_status_label.setText("Local Plugins Directory")
        self.page_label.setText("Installed")
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

        if not items:
            self.status_overlay.setText("No installed plugins found in userdata/source2pluginloader/plugins/")
            self.status_overlay.show()
        else:
            self.populate_cards(items)

    def clear_cards(self):
        for card in self.cards:
            self.grid_layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()

    def update_pagination(self):
        max_pages = math.ceil(self.total_count / 30) if self.total_count > 0 else 1
        self.results_count_label.setText(f"{self.total_count:,} repositories total")
        self.page_label.setText(f"Page {self.current_page} of {max_pages}")

        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < max_pages)

    def go_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.do_search(force_refresh=False)

    def go_next_page(self):
        self.current_page += 1
        self.do_search(force_refresh=False)

    def install_plugin_action(self, repo_data: dict):
        full_name = repo_data.get("full_name", "")
        if not full_name:
            return

        token = get_settings_value("GITHUB", "token", "")
        worker = PluginDownloadWorker(repo_data, token=token, parent=self)

        self.active_download_workers[full_name] = worker
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(10)
        self.progress_bar.show()

        worker.progress.connect(self.on_download_progress)
        worker.finished.connect(self.on_download_finished)
        worker.failed.connect(self.on_download_failed)
        worker.start()

    def on_download_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        if self.update_title:
            self.update_title(text=msg)

    def on_download_finished(self, full_name: str, target_dir: str):
        self.progress_bar.hide()
        if full_name in self.active_download_workers:
            del self.active_download_workers[full_name]

        if self.update_title:
            self.update_title(text=f"Installed {full_name} -> {target_dir}")

        QMessageBox.information(
            self,
            "Plugin Installed",
            f"Plugin '{full_name}' was successfully downloaded and extracted into:\n\n{target_dir}"
        )

        for card in self.cards:
            if card.full_name == full_name:
                card.refresh_installed_state()

    def on_download_failed(self, full_name: str, error_msg: str):
        self.progress_bar.hide()
        if full_name in self.active_download_workers:
            del self.active_download_workers[full_name]

        QMessageBox.critical(self, "Installation Failed", f"Failed to install {full_name}:\n\n{error_msg}")

    def open_folder(self, path: str):
        if os.path.exists(path):
            os.startfile(path)

    def open_plugins_directory(self):
        target = get_plugins_dir()
        os.startfile(target)

    def open_token_dialog(self):
        dialog = GitHubTokenDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.do_search(force_refresh=True)
