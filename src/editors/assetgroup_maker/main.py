import os
import json
from typing import Optional, Dict, List, Tuple
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QDockWidget, QFileDialog, QMessageBox,
    QTabBar, QToolButton, QMenu, QApplication, QStackedWidget, QFrame,
    QCheckBox
)
from PySide6.QtCore import Qt, Signal, QByteArray
from PySide6.QtGui import QIcon, QAction, QKeySequence, QCloseEvent, QPixmap

from src.settings.main import get_addon_name, get_cs2_path, get_addon_dir, get_settings_value, set_settings_value, debug
from src.widgets.explorer.main import Explorer
from src.editors.assetgroup_maker.monitor import MonitoringFileWatcher
from src.editors.assetgroup_maker.editor_tab import EditorTabWidget
from src.editors.assetgroup_maker.objects import get_default_file
from src.styles.common import qt_stylesheet_button, qt_stylesheet_checkbox, qt_stylesheet_lineedit


class BatchCreatorMainWindow(QMainWindow):
    """
    Redesigned AssetGroup Maker Main Window:
    - Left Dock: Addon Explorer with "New config for selected folder" button at bottom
    - Center Area: Multi-Document Tab System + Empty State Placeholder ("Create config for asset folder or open a config")
      with Save & Watch the changes inside each individual document footer
    - Right Dock: Config Explorer (Monitored .hbat files) with search filter and "+ New Config..." button
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

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._save_layout_state)

    def _build_ui(self):
        self.setWindowTitle("AssetGroup Maker")
        self.setObjectName("BatchCreator_MainWindow")

        # Set dock widget options to allow animated docking, nesting, tabbed docks
        self.setDockOptions(
            QMainWindow.AnimatedDocks |
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks |
            QMainWindow.GroupedDragging
        )
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        # 1. Central Container with Stack (Empty State / Tabs)
        self.central_container = QWidget()
        self.central_container.setMinimumWidth(260)
        central_layout = QVBoxLayout(self.central_container)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Central Stack: Page 0 = Empty State, Page 1 = Document Tabs
        self.central_stack = QStackedWidget()

        # Page 0: Empty State View
        self.empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(QPixmap(":/valve_common/icons/tools/model_editor/hierarchy_sequence_group_referenced.png").scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_lbl.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon_lbl)

        title_lbl = QLabel("Create config for asset folder or open a config")
        title_lbl.setStyleSheet("font: 700 13pt 'Segoe UI'; color: #E5E5E5;")
        title_lbl.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(title_lbl)

        desc_lbl = QLabel("Select an asset folder in the Explorer on the left, open an existing .hbat file, or create a new profile.")
        desc_lbl.setStyleSheet("font: 500 9.5pt 'Segoe UI'; color: #9D9D9D;")
        desc_lbl.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(desc_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setAlignment(Qt.AlignCenter)

        btn_create_folder = QPushButton("New Config for Selected Folder")
        btn_create_folder.setIcon(QIcon(":/valve_common/icons/tools/common/folder.png"))
        btn_create_folder.setStyleSheet(qt_stylesheet_button)
        btn_create_folder.setFixedHeight(28)
        btn_create_folder.clicked.connect(self.create_new_config_for_selected_folder)
        btn_row.addWidget(btn_create_folder)

        btn_open = QPushButton("Open Config...")
        btn_open.setIcon(QIcon(":/valve_common/icons/tools/common/open.png"))
        btn_open.setStyleSheet(qt_stylesheet_button)
        btn_open.setFixedHeight(28)
        btn_open.clicked.connect(self._open_file_dialog)
        btn_row.addWidget(btn_open)

        btn_new = QPushButton("Create New Config...")
        btn_new.setIcon(QIcon(":/valve_common/icons/tools/common/new.png"))
        btn_new.setStyleSheet(qt_stylesheet_button)
        btn_new.setFixedHeight(28)
        btn_new.clicked.connect(lambda: self.create_new_config_dialog(force_file_dialog=True))
        btn_row.addWidget(btn_new)

        empty_layout.addLayout(btn_row)
        self.central_stack.addWidget(self.empty_state_widget)

        # Page 1: Multi-Document Tab Widget
        from src.widgets.document_tab import DocumentTabWidget
        self.tab_widget = DocumentTabWidget()
        self.tab_widget.set_new_tab_tooltip("Create New Batch Profile (Ctrl+N)")
        self.tab_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self._show_tab_context_menu)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.new_tab_requested.connect(lambda: self.create_new_config_dialog(force_file_dialog=True))
        self.new_tab_btn = self.tab_widget.new_tab_btn

        self.central_stack.addWidget(self.tab_widget)
        central_layout.addWidget(self.central_stack, 1)

        self.setCentralWidget(self.central_container)

        # 2. Left Dock Widget: Addon Explorer
        self.explorer_dock = QDockWidget("Explorer", self)
        self.explorer_dock.setObjectName("AssetGroup_ExplorerDock")
        self.explorer_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.explorer_dock.setMinimumWidth(180)

        explorer_dock_content = QWidget()
        explorer_dock_layout = QVBoxLayout(explorer_dock_content)
        explorer_dock_layout.setContentsMargins(2, 2, 2, 2)
        explorer_dock_layout.setSpacing(4)

        self.explorer = Explorer(
            parent=self.parent,
            tree_directory=self.explorer_directory,
            addon=self.addon_name,
            editor_name='BatchCreator'
        )
        explorer_dock_layout.addWidget(self.explorer.frame, 1)

        self.new_cfg_for_folder_btn = QPushButton("New config for selected folder")
        self.new_cfg_for_folder_btn.setIcon(QIcon(":/valve_common/icons/tools/common/folder.png"))
        self.new_cfg_for_folder_btn.setToolTip("Create a new batch configuration for the selected directory in Explorer")
        self.new_cfg_for_folder_btn.setStyleSheet(qt_stylesheet_button)
        self.new_cfg_for_folder_btn.setFixedHeight(28)
        self.new_cfg_for_folder_btn.clicked.connect(self.create_new_config_for_selected_folder)
        explorer_dock_layout.addWidget(self.new_cfg_for_folder_btn)

        self.explorer_dock.setWidget(explorer_dock_content)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.explorer_dock)

        # 3. Right Dock Widget: Config Explorer (.hbat files)
        self.config_dock = QDockWidget("Config Explorer", self)
        self.config_dock.setObjectName("AssetGroup_ConfigDock")
        self.config_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.config_dock.setMinimumWidth(180)

        config_dock_content = QWidget()
        config_dock_layout = QVBoxLayout(config_dock_content)
        config_dock_layout.setContentsMargins(4, 4, 4, 4)
        config_dock_layout.setSpacing(4)

        # Search / filter input at top of Config Explorer
        self.cfg_search = QLineEdit()
        self.cfg_search.setPlaceholderText("Filter configs...")
        self.cfg_search.setStyleSheet(qt_stylesheet_lineedit)
        self.cfg_search.setClearButtonEnabled(True)
        self.cfg_search.textChanged.connect(self._filter_configs)
        config_dock_layout.addWidget(self.cfg_search)

        # List of monitored .hbat files
        self.monitoring_list = MonitoringFileWatcher(self.explorer_directory)
        self.monitoring_list.open_file.connect(self.open_filepath)
        self.monitoring_list.watch_status_changed.connect(self._on_monitor_watch_status_changed)
        config_dock_layout.addWidget(self.monitoring_list, 1)

        # Bottom section: + New Config... button
        cfg_bottom_layout = QVBoxLayout()
        cfg_bottom_layout.setContentsMargins(0, 2, 0, 0)
        cfg_bottom_layout.setSpacing(4)

        self.new_cfg_btn = QPushButton("New Config...")
        self.new_cfg_btn.setIcon(QIcon(":/valve_common/icons/tools/common/new.png"))
        self.new_cfg_btn.setToolTip("Open file dialog to create a new .hbat batch config file (Ctrl+N)")
        self.new_cfg_btn.setStyleSheet(qt_stylesheet_button)
        self.new_cfg_btn.setFixedHeight(28)
        self.new_cfg_btn.clicked.connect(self._open_new_config_file_dialog)
        cfg_bottom_layout.addWidget(self.new_cfg_btn)

        config_dock_layout.addLayout(cfg_bottom_layout)

        self.config_dock.setWidget(config_dock_content)
        self.addDockWidget(Qt.RightDockWidgetArea, self.config_dock)

        # Restore saved dock layout or apply defaults
        self._restore_layout_state()

        # Initialize view stack state
        self._update_view_stack()

    def _setup_shortcuts(self):
        new_act = QAction("New Batch Profile", self)
        new_act.setShortcut(QKeySequence.New)
        new_act.triggered.connect(lambda: self.create_new_config_dialog(force_file_dialog=True))
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

    def _update_view_stack(self):
        if self.tab_widget.count() > 0:
            self.central_stack.setCurrentWidget(self.tab_widget)
        else:
            self.central_stack.setCurrentWidget(self.empty_state_widget)

    def _on_monitor_watch_status_changed(self, file_path: str, enabled: bool):
        norm = os.path.normpath(file_path)
        for idx in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, EditorTabWidget) and widget.file_path:
                if os.path.normpath(widget.file_path).lower() == norm.lower():
                    widget.watch_changes_cb.blockSignals(True)
                    widget.watch_changes_cb.setChecked(enabled)
                    widget.watch_changes_cb.blockSignals(False)
                    widget.process_data['watch_changes'] = enabled

    def _filter_configs(self, text: str):
        search_term = text.lower().strip()
        for idx in range(self.monitoring_list.count()):
            item = self.monitoring_list.item(idx)
            widget = self.monitoring_list.itemWidget(item)
            if widget and hasattr(widget, 'file_path'):
                full_path = widget.file_path.lower()
                item.setHidden(search_term not in full_path)

    def _get_selected_folder_from_explorer(self) -> Optional[str]:
        if hasattr(self, 'explorer') and self.explorer and hasattr(self.explorer, 'tree'):
            curr_idx = self.explorer.tree.currentIndex()
            if curr_idx.isValid():
                src_idx = self.explorer.filter_proxy_model.mapToSource(curr_idx)
                path = self.explorer.model.filePath(src_idx)
                if path:
                    abs_path = os.path.abspath(path)
                    if os.path.isdir(abs_path):
                        return abs_path
                    return os.path.dirname(abs_path)
        return None

    def create_new_config_for_selected_folder(self):
        folder = self._get_selected_folder_from_explorer()
        if not folder:
            addon_dir = get_addon_dir() or self.explorer_directory
            folder = addon_dir

        if not folder or not os.path.exists(folder):
            QMessageBox.warning(self, "Warning", "No valid folder selected in Explorer.")
            return

        if os.path.isfile(folder):
            folder = os.path.dirname(folder)

        folder_name = os.path.basename(os.path.normpath(folder))
        if not folder_name:
            folder_name = "new_batch"

        candidate = os.path.join(folder, f"{folder_name}.hbat")
        if os.path.exists(candidate):
            idx = 1
            while os.path.exists(os.path.join(folder, f"{folder_name}_{idx}.hbat")):
                idx += 1
            candidate = os.path.join(folder, f"{folder_name}_{idx}.hbat")

        file_path = candidate
        default_data = get_default_file()
        try:
            from src.editors.assetgroup_maker.objects import save_hbat_file
            save_hbat_file(file_path, default_data)

            MonitoringFileWatcher.notify_new_file(file_path)
            self.open_filepath(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create .hbat file:\n{e}")

    def _open_new_config_file_dialog(self):
        self.create_new_config_dialog(force_file_dialog=True)

    def create_new_config_dialog(self, target_folder: Optional[str] = None, force_file_dialog: bool = True):
        """
        Prompts to create a new .hbat config file in the specified/active folder or opens a new tab.
        """
        current_folder = target_folder
        if not current_folder:
            current_folder = self._get_selected_folder_from_explorer()
        if not current_folder:
            current_folder = get_addon_dir() or self.explorer_directory

        default_name = os.path.basename(current_folder) if current_folder else "new_batch"
        default_target = os.path.join(current_folder, f"{default_name}.hbat") if current_folder else "new_batch.hbat"

        if force_file_dialog:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Create New Batch Profile (.hbat)",
                default_target,
                "Hammer Batch (*.hbat)"
            )
            if file_path:
                if not file_path.lower().endswith(".hbat"):
                    file_path += ".hbat"

                default_data = get_default_file()
                try:
                    from src.editors.assetgroup_maker.objects import save_hbat_file
                    save_hbat_file(file_path, default_data)
                    
                    MonitoringFileWatcher.notify_new_file(file_path)
                    self.open_filepath(file_path)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create .hbat file:\n{e}")
        else:
            self.create_new_batch_tab()

    def create_new_batch_tab(self, reference_path: Optional[str] = None) -> EditorTabWidget:
        tab = EditorTabWidget(file_path=None, parent=self)
        if reference_path:
            tab.template_manager.set_data({
                'version': 3,
                'settings': get_default_file()['settings'],
                'templates': [{'id': 'template_0', 'extension': 'vmdl', 'reference': reference_path, 'replacements': []}]
            })

        tab_idx = self.tab_widget.addTab(tab, QIcon(":/valve_common/icons/tools/assettypes/vcompmat_sm.png"), "Untitled.hbat")
        self.tab_widget.setCurrentIndex(tab_idx)

        tab.title_changed.connect(lambda title, t=tab: self._update_tab_title(t, title))
        tab.dirty_changed.connect(lambda dirty, t=tab: self._on_tab_dirty(t, dirty))
        tab.status_updated.connect(self._on_status_updated)

        self._update_view_stack()
        return tab

    def open_filepath(self, file_path: str):
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "File Not Found", f"File does not exist:\n{file_path}")
            return

        norm_path = os.path.normpath(file_path)

        # Check if already open
        for idx in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, EditorTabWidget) and widget.file_path:
                if os.path.normpath(widget.file_path).lower() == norm_path.lower():
                    self.tab_widget.setCurrentIndex(idx)
                    self._update_view_stack()
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

        self._update_view_stack()

    def _open_file_dialog(self):
        addon_dir = get_addon_dir() or self.explorer_directory
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Batch Profile", addon_dir, "Hammer Batch (*.hbat);;All Files (*.*)"
        )
        if file_path:
            self.open_filepath(file_path)

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
        if idx < 0 or idx >= self.tab_widget.count():
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
            self._update_view_stack()

    def _show_tab_context_menu(self, position):
        tab_idx = self.tab_widget.tabBar().tabAt(position)
        if tab_idx < 0:
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
        for i in reversed(range(self.tab_widget.count())):
            if i != keep_idx:
                self.close_tab(i)

    def has_unsaved_changes(self) -> bool:
        for idx in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, EditorTabWidget) and widget.has_unsaved_changes():
                return True
        return False

    def unsaved_files(self) -> List[Tuple[str, callable]]:
        results = []
        for idx in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(idx)
            if isinstance(widget, EditorTabWidget) and widget.has_unsaved_changes():
                name = widget.file_path or "Untitled.hbat"
                results.append((name, widget.save_file))
        return results

    def _save_layout_state(self):
        try:
            geo_hex = self.saveGeometry().toHex().data().decode('utf-8')
            state_hex = self.saveState().toHex().data().decode('utf-8')
            set_settings_value('AssetGroupMaker', 'geometry', geo_hex)
            set_settings_value('AssetGroupMaker', 'window_state', state_hex)
        except Exception as e:
            debug(f"Error saving AssetGroupMaker layout state: {e}")

    def _restore_layout_state(self):
        try:
            geo_hex = get_settings_value('AssetGroupMaker', 'geometry')
            if geo_hex:
                self.restoreGeometry(QByteArray.fromHex(geo_hex.encode('utf-8')))
            state_hex = get_settings_value('AssetGroupMaker', 'window_state')
            if state_hex:
                restored = self.restoreState(QByteArray.fromHex(state_hex.encode('utf-8')))
                if not restored:
                    self.resizeDocks([self.explorer_dock, self.config_dock], [260, 260], Qt.Horizontal)
            else:
                self.resizeDocks([self.explorer_dock, self.config_dock], [260, 260], Qt.Horizontal)
        except Exception as e:
            debug(f"Error restoring AssetGroupMaker layout state: {e}")
            self.resizeDocks([self.explorer_dock, self.config_dock], [260, 260], Qt.Horizontal)

    def closeEvent(self, event: QCloseEvent):
        self._save_layout_state()
        if self.has_unsaved_changes():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved batch profiles. Save them before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                for idx in range(self.tab_widget.count()):
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