import os
import json
from typing import Optional, Dict, List, Tuple
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QSplitter, QDockWidget, QFileDialog,
    QMessageBox, QTabBar, QToolButton, QMenu, QApplication, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QAction, QKeySequence, QCloseEvent

from src.settings.main import get_addon_name, get_cs2_path, get_addon_dir, debug
from src.widgets.explorer.main import Explorer
from src.editors.assetgroup_maker.monitor import MonitoringFileWatcher
from src.widgets.model_browser.main import ModelBrowserWidget
from src.editors.assetgroup_maker.editor_tab import EditorTabWidget
from src.editors.assetgroup_maker.objects import get_default_file
from src.styles.common import qt_stylesheet_button


class BatchCreatorMainWindow(QMainWindow):
    """
    Redesigned AssetGroup Maker Main Window:
    - Left Dock: Addon Explorer (top) + Config Explorer / Monitored .hbat files (bottom)
    - Center Area: Multi-Document Tab System (.hbat tabs) + Model Asset Browser tab
    """

    def __init__(self, parent: Optional[QMainWindow] = None, update_title: Optional[callable] = None):
        super().__init__(parent)
        self.parent = parent
        self.update_title_cb = update_title

        self.addon_name = get_addon_name()
        self.cs2_path = get_cs2_path()
        if self.cs2_path and self.addon_name:
            self.explorer_directory = os.path.join(self.cs2_path, "content", "csgo_addons", self.addon_name)
        else:
            self.explorer_directory = ""

        self._build_ui()
        self._setup_shortcuts()
        self.setAcceptDrops(True)

    def _build_ui(self):
        self.setWindowTitle("AssetGroup Maker")

        # 1. Central Widget with Tabs
        self.central_container = QWidget()
        central_layout = QVBoxLayout(self.central_container)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self._show_tab_context_menu)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # New Tab (+) Corner Button
        self.new_tab_btn = QToolButton()
        self.new_tab_btn.setText("+")
        self.new_tab_btn.setToolTip("Create New Batch Profile (Ctrl+N)")
        self.new_tab_btn.setStyleSheet("""
            QToolButton {
                font: 700 12pt "Segoe UI";
                color: #C7C7BB;
                background: transparent;
                border: none;
                padding: 2px 8px;
            }
            QToolButton:hover {
                color: #FFFFFF;
                background-color: #363639;
                border-radius: 2px;
            }
        """)
        self.new_tab_btn.clicked.connect(self.create_new_config_dialog)
        self.tab_widget.setCornerWidget(self.new_tab_btn, Qt.TopRightCorner)

        # 2. Add Persistent "Asset Browser" Tab (Lazy scanned)
        self.asset_browser = ModelBrowserWidget(self, addon=self.addon_name, show_accept=False, auto_scan=False)
        self.asset_browser.use_as_template.connect(self._on_model_use_as_template)
        self.tab_widget.addTab(self.asset_browser, QIcon(":/valve_common/icons/tools/common/browse.png"), "Asset Browser")
        tab_bar = self.tab_widget.tabBar()
        tab_bar.setTabButton(0, QTabBar.RightSide, None)

        central_layout.addWidget(self.tab_widget)
        self.setCentralWidget(self.central_container)

        # 3. Left Dock Widget
        self.left_dock = QDockWidget("Asset & Config Explorer", self)
        self.left_dock.setObjectName("AssetGroup_LeftDock")
        self.left_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        left_dock_content = QWidget()
        left_dock_layout = QVBoxLayout(left_dock_content)
        left_dock_layout.setContentsMargins(0, 0, 0, 0)
        left_dock_layout.setSpacing(0)

        # Splitter: Upper = Addon Explorer, Lower = Config Explorer
        self.left_splitter = QSplitter(Qt.Vertical)

        # Addon Explorer Host
        explorer_host = QWidget()
        explorer_layout = QVBoxLayout(explorer_host)
        explorer_layout.setContentsMargins(0, 0, 0, 0)
        explorer_layout.setSpacing(2)

        exp_header = QLabel("  ADDON EXPLORER")
        exp_header.setStyleSheet("background-color: #1C1C1C; color: #9D9D9D; font: 700 8.5pt 'Segoe UI'; padding: 3px;")
        explorer_layout.addWidget(exp_header)

        self.explorer = Explorer(
            parent=self.parent,
            tree_directory=self.explorer_directory,
            addon=self.addon_name,
            editor_name='BatchCreator'
        )
        explorer_layout.addWidget(self.explorer.frame)
        self.left_splitter.addWidget(explorer_host)

        # Config Explorer Host (Monitored .hbat files)
        config_host = QWidget()
        config_layout = QVBoxLayout(config_host)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(2)

        cfg_header_row = QHBoxLayout()
        cfg_header_row.setContentsMargins(4, 3, 4, 3)
        cfg_header_row.setSpacing(4)

        cfg_header = QLabel("CONFIG EXPLORER (.hbat)")
        cfg_header.setStyleSheet("color: #9D9D9D; font: 700 8.5pt 'Segoe UI';")
        cfg_header_row.addWidget(cfg_header)

        cfg_header_row.addStretch(1)

        # Explicit + New Config Button in Config Explorer Header
        self.new_cfg_btn = QPushButton("+ New")
        self.new_cfg_btn.setToolTip("Create a new .hbat batch config file (Ctrl+N)")
        self.new_cfg_btn.setStyleSheet("""
            QPushButton {
                background-color: #26262B;
                color: #E3E3E3;
                border: 1px solid #363639;
                border-radius: 3px;
                padding: 1px 6px;
                font: 600 8.5pt 'Segoe UI';
                min-height: 18px;
            }
            QPushButton:hover {
                background-color: #3A78C4;
                color: #FFFFFF;
                border-color: #4C8BE2;
            }
            QPushButton:pressed {
                background-color: #2D62A3;
            }
        """)
        self.new_cfg_btn.clicked.connect(self.create_new_config_dialog)
        cfg_header_row.addWidget(self.new_cfg_btn)

        self.cfg_search = QLineEdit()
        self.cfg_search.setPlaceholderText("Filter configs...")
        self.cfg_search.setMaximumWidth(110)
        self.cfg_search.textChanged.connect(self._filter_configs)
        cfg_header_row.addWidget(self.cfg_search)

        config_layout.addLayout(cfg_header_row)

        self.monitoring_list = MonitoringFileWatcher(self.explorer_directory)
        self.monitoring_list.open_file.connect(self.open_filepath)
        config_layout.addWidget(self.monitoring_list)

        self.left_splitter.addWidget(config_host)
        self.left_splitter.setSizes([350, 250])

        left_dock_layout.addWidget(self.left_splitter)
        self.left_dock.setWidget(left_dock_content)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)

    def _setup_shortcuts(self):
        new_act = QAction("New Batch Profile", self)
        new_act.setShortcut(QKeySequence.New)
        new_act.triggered.connect(self.create_new_config_dialog)
        self.addAction(new_act)

        open_act = QAction("Open Batch Profile", self)
        open_act.setShortcut(QKeySequence.Open)
        open_act.triggered.connect(self._open_file_dialog)
        self.addAction(open_act)

        save_act = QAction("Save Batch Profile", self)
        save_act.setShortcut(QKeySequence.Save)
        save_act.triggered.connect(self.save_active_tab)
        self.addAction(save_act)

        close_act = QAction("Close Tab", self)
        close_act.setShortcut(QKeySequence.Close)
        close_act.triggered.connect(lambda: self.close_tab(self.tab_widget.currentIndex()))
        self.addAction(close_act)

    def _filter_configs(self, text: str):
        search_term = text.lower().strip()
        for idx in range(self.monitoring_list.count()):
            item = self.monitoring_list.item(idx)
            widget = self.monitoring_list.itemWidget(item)
            if widget and hasattr(widget, 'file_path'):
                full_path = widget.file_path.lower()
                item.setHidden(search_term not in full_path)

    def create_new_config_dialog(self):
        """
        Prompts to create a new .hbat config file in the active folder or opens a new tab.
        """
        # Determine current folder from explorer if available
        current_folder = ""
        if hasattr(self, 'explorer') and self.explorer:
            selected_path = self.explorer.get_current_path()
            if selected_path:
                addon_dir = get_addon_dir() or self.explorer_directory
                full_selected = os.path.join(addon_dir, selected_path) if not os.path.isabs(selected_path) else selected_path
                if os.path.isdir(full_selected):
                    current_folder = full_selected
                else:
                    current_folder = os.path.dirname(full_selected)

        if not current_folder:
            current_folder = get_addon_dir() or self.explorer_directory

        default_name = os.path.basename(current_folder) if current_folder else "new_batch"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New Batch Profile (.hbat)",
            os.path.join(current_folder, f"{default_name}.hbat"),
            "Hammer Batch (*.hbat)"
        )

        if file_path:
            if not file_path.lower().endswith(".hbat"):
                file_path += ".hbat"

            # Write default template
            default_data = get_default_file()
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, indent=4)
                
                # Notify file watcher
                MonitoringFileWatcher.notify_new_file(file_path)
                
                # Open in a new tab
                self.open_filepath(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create .hbat file:\n{e}")
        else:
            # If user cancelled file picker, create an in-memory untitled tab
            self.create_new_batch_tab()

    def create_new_batch_tab(self, reference_path: Optional[str] = None) -> EditorTabWidget:
        tab = EditorTabWidget(file_path=None, parent=self)
        if reference_path:
            tab.reference_card.set_reference_path(reference_path)

        tab_idx = self.tab_widget.addTab(tab, QIcon(":/valve_common/icons/tools/assettypes/vcompmat_sm.png"), "Untitled.hbat")
        self.tab_widget.setCurrentIndex(tab_idx)

        tab.title_changed.connect(lambda title, t=tab: self._update_tab_title(t, title))
        tab.dirty_changed.connect(lambda dirty, t=tab: self._on_tab_dirty(t, dirty))
        tab.status_updated.connect(self._on_status_updated)

        return tab

    def open_filepath(self, file_path: str):
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "File Not Found", f"File does not exist:\n{file_path}")
            return

        norm_path = os.path.normpath(file_path)

        # Check if already open
        for idx in range(1, self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, EditorTabWidget) and widget.file_path:
                if os.path.normpath(widget.file_path).lower() == norm_path.lower():
                    self.tab_widget.setCurrentIndex(idx)
                    return

        # Open in new tab
        tab = EditorTabWidget(file_path=norm_path, parent=self)
        title = os.path.basename(norm_path)
        tab_idx = self.tab_widget.addTab(tab, QIcon(":/valve_common/icons/tools/assettypes/vcompmat_sm.png"), title)
        self.tab_widget.setCurrentIndex(tab_idx)

        tab.title_changed.connect(lambda t_title, t=tab: self._update_tab_title(t, t_title))
        tab.dirty_changed.connect(lambda dirty, t=tab: self._on_tab_dirty(t, dirty))
        tab.status_updated.connect(self._on_status_updated)

        if hasattr(self, 'explorer') and self.explorer:
            self.explorer.add_recent_file(norm_path)

        if self.update_title_cb and callable(self.update_title_cb):
            self.update_title_cb('opened', norm_path)

    def _open_file_dialog(self):
        addon_dir = get_addon_dir() or self.explorer_directory
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Batch Profile", addon_dir, "Hammer Batch (*.hbat);;All Files (*.*)"
        )
        if file_path:
            self.open_filepath(file_path)

    def _on_model_use_as_template(self, model_path: str):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, EditorTabWidget):
            current_widget.reference_card.set_reference_path(model_path)
        else:
            self.create_new_batch_tab(reference_path=model_path)

    def _update_tab_title(self, tab: EditorTabWidget, title: str):
        idx = self.tab_widget.indexOf(tab)
        if idx != -1:
            dirty_suffix = " *" if tab.has_unsaved_changes() else ""
            self.tab_widget.setTabText(idx, f"{title}{dirty_suffix}")

    def _on_tab_dirty(self, tab: EditorTabWidget, dirty: bool):
        idx = self.tab_widget.indexOf(tab)
        if idx != -1:
            base_title = os.path.basename(tab.file_path) if tab.file_path else "Untitled.hbat"
            dirty_suffix = " *" if dirty else ""
            self.tab_widget.setTabText(idx, f"{base_title}{dirty_suffix}")

    def _on_tab_changed(self, idx: int):
        if idx == 0:
            if not getattr(self.asset_browser, '_has_scanned', False):
                self.asset_browser._start_scan()
        else:
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, EditorTabWidget) and widget.file_path:
                if self.update_title_cb and callable(self.update_title_cb):
                    self.update_title_cb('opened', widget.file_path)

    def _on_status_updated(self, msg: str):
        if self.update_title_cb and callable(self.update_title_cb):
            self.update_title_cb(text=msg)

    def save_active_tab(self) -> bool:
        widget = self.tab_widget.currentWidget()
        if isinstance(widget, EditorTabWidget):
            saved = widget.save_file()
            if saved and self.update_title_cb and callable(self.update_title_cb):
                self.update_title_cb('saved', widget.file_path)
            return saved
        return False

    def close_tab(self, idx: int):
        if idx <= 0:
            return

        widget = self.tab_widget.widget(idx)
        if isinstance(widget, EditorTabWidget):
            if widget.has_unsaved_changes():
                tab_name = self.tab_widget.tabText(idx).rstrip(" *")
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    f"Save changes to '{tab_name}' before closing?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                if reply == QMessageBox.Save:
                    if not widget.save_file():
                        return
                elif reply == QMessageBox.Cancel:
                    return

            self.tab_widget.removeTab(idx)
            widget.deleteLater()

    def _show_tab_context_menu(self, position):
        tab_idx = self.tab_widget.tabBar().tabAt(position)
        if tab_idx <= 0:
            return

        menu = QMenu(self)

        save_action = QAction("Save", self)
        save_action.triggered.connect(lambda: self._save_tab_at(tab_idx))
        menu.addAction(save_action)

        close_action = QAction("Close Tab", self)
        close_action.triggered.connect(lambda: self.close_tab(tab_idx))
        menu.addAction(close_action)

        close_others_action = QAction("Close Other Tabs", self)
        close_others_action.triggered.connect(lambda: self._close_other_tabs(tab_idx))
        menu.addAction(close_others_action)

        menu.exec_(self.tab_widget.mapToGlobal(position))

    def _save_tab_at(self, idx: int):
        widget = self.tab_widget.widget(idx)
        if isinstance(widget, EditorTabWidget):
            widget.save_file()

    def _close_other_tabs(self, keep_idx: int):
        for i in reversed(range(1, self.tab_widget.count())):
            if i != keep_idx:
                self.close_tab(i)

    def has_unsaved_changes(self) -> bool:
        for idx in range(1, self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, EditorTabWidget) and widget.has_unsaved_changes():
                return True
        return False

    def unsaved_files(self) -> List[Tuple[str, callable]]:
        results = []
        for idx in range(1, self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, EditorTabWidget) and widget.has_unsaved_changes():
                name = widget.file_path or "Untitled.hbat"
                results.append((name, widget.save_file))
        return results

    def closeEvent(self, event: QCloseEvent):
        if self.has_unsaved_changes():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved batch profiles. Save them before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                for idx in range(1, self.tab_widget.count()):
                    widget = self.tab_widget.widget(idx)
                    if isinstance(widget, EditorTabWidget) and widget.has_unsaved_changes():
                        widget.save_file()
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
                return
        super().closeEvent(event)