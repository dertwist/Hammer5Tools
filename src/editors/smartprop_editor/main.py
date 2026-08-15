import sys
import os.path
from functools import partial
from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QApplication,
    QMessageBox,
    QMenu,
    QDialog,
    QDockWidget
)
from PySide6.QtGui import QUndoStack, QIcon, QKeySequence, QAction
from PySide6.QtCore import Qt
from src.editors.smartprop_editor.ui_main import Ui_MainWindow
from src.settings.main import (
    get_addon_name,
    settings,
    get_settings_value,
    set_settings_value,
)
from src.widgets.explorer.main import Explorer
from src.editors.smartprop_editor.document import SmartPropDocument
from src.editors.smartprop_editor.choices import AddChoice
from src.editors.smartprop_editor.commands import GroupElementsCommand
from src.other.assettypes import check_vsmart_configuration
from src.widgets import ErrorInfo, exception_handler
from src.common import (
    enable_dark_title_bar,
    get_cs2_path,
    set_qdock_tab_style
)

cs2_path = get_cs2_path()

class SmartPropEditorMainWindow(QMainWindow):
    def __init__(self, parent=None, update_title=None):
        super().__init__()
        self.parent = parent
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
        self.opened_file = None
        self.update_title = update_title
        enable_dark_title_bar(self)

        # Make the tab widget closable and connect to our close_document method
        self.ui.DocumentTabWidget.setTabsClosable(True)
        self.ui.DocumentTabWidget.tabCloseRequested.connect(self.close_document)
        self.ui.DocumentTabWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.DocumentTabWidget.customContextMenuRequested.connect(self.show_tab_context_menu)
        self.ui.DocumentTabWidget.currentChanged.connect(self.update_menu_states)

        # Initialize file explorer
        self.init_explorer()
        # Hide the Explorer dock title bar (no label, no float/close buttons)
        from PySide6.QtWidgets import QWidget as _QWidget
        self.ui.ExplorerDock.setTitleBarWidget(_QWidget())

        # Initialize categorized menu bar
        self.init_menu_bar()

        set_qdock_tab_style(self.findChildren)

        self.undo_stack = QUndoStack(self)

        # Set initial UI state based on document availability
        self.update_placeholder_visibility()

        # Persist document layout on quit
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._persist_current_document_layout)

    def get_current_document(self) -> SmartPropDocument | None:
        idx = self.ui.DocumentTabWidget.currentIndex()
        if idx >= 0:
            doc = self.ui.DocumentTabWidget.widget(idx)
            if isinstance(doc, SmartPropDocument):
                return doc
        return None

    def init_menu_bar(self):
        menubar = self.menuBar()
        menubar.clear()
        menubar.setStyleSheet("QMenuBar { padding-top: 4px; padding-bottom: 4px; }")

        file_menu = menubar.addMenu("&File")
        file_menu.setStyleSheet("QMenu { padding-bottom: 6px; }")

        self.action_new = file_menu.addAction("New File")
        self.action_new.setShortcut(QKeySequence.New)
        self.action_new.setIcon(QIcon(":/icons/add_24dp.svg"))
        self.action_new.triggered.connect(self.create_new_file)

        self.action_open = file_menu.addAction("Open...")
        self.action_open.setShortcut(QKeySequence.Open)
        self.action_open.setIcon(QIcon(":/icons/edit_document_16dp.svg"))
        self.action_open.triggered.connect(lambda: self.open_file(external=True))

        self.action_open_selected = file_menu.addAction("Open Selected from Explorer")
        self.action_open_selected.setIcon(QIcon(":/icons/file_open_16dp.svg"))
        self.action_open_selected.triggered.connect(lambda: self.open_file(external=False))

        file_menu.addSeparator()

        self.action_save = file_menu.addAction("Save")
        self.action_save.setShortcut(QKeySequence.Save)
        self.action_save.setIcon(QIcon(":/icons/save_16dp.svg"))
        self.action_save.triggered.connect(lambda: self.save_file(external=False))

        self.action_save_as = file_menu.addAction("Save As...")
        self.action_save_as.setShortcut(QKeySequence.SaveAs)
        self.action_save_as.setIcon(QIcon(":/icons/save_as_16dp.svg"))
        self.action_save_as.triggered.connect(lambda: self.save_file(external=True))

        self.action_save_all = file_menu.addAction("Save All")
        self.action_save_all.triggered.connect(self.save_all_files)

        file_menu.addSeparator()

        self.action_close = file_menu.addAction("Close File")
        self.action_close.setShortcut(QKeySequence("Ctrl+W"))
        self.action_close.triggered.connect(lambda: self.close_document())

        file_menu.addSeparator()

        self.action_convert_vmap = file_menu.addAction("Load Vmap...")
        self.action_convert_vmap.triggered.connect(self.active_document_load_vmap)

        file_menu.addSeparator()

        self.action_export_scene_debug = file_menu.addAction("Export scene (debug)")
        self.action_export_scene_debug.triggered.connect(self.export_scene_debug)

        file_menu.addSeparator()

        self.action_exit = file_menu.addAction("Exit")
        self.action_exit.triggered.connect(self.close)

        edit_menu = menubar.addMenu("&Edit")

        self.action_undo = edit_menu.addAction("Undo")
        self.action_undo.setShortcut(QKeySequence.Undo)
        self.action_undo.triggered.connect(self.active_document_undo)

        self.action_redo = edit_menu.addAction("Redo")
        self.action_redo.setShortcuts([QKeySequence.Redo, QKeySequence("Ctrl+Shift+Z")])
        self.action_redo.triggered.connect(self.active_document_redo)

        edit_menu.addSeparator()

        self.action_cut = edit_menu.addAction("Cut")
        self.action_cut.setShortcut(QKeySequence.Cut)
        self.action_cut.triggered.connect(self.active_document_cut)

        self.action_copy = edit_menu.addAction("Copy")
        self.action_copy.setShortcut(QKeySequence.Copy)
        self.action_copy.triggered.connect(self.active_document_copy)

        self.action_paste = edit_menu.addAction("Paste")
        self.action_paste.setShortcut(QKeySequence.Paste)
        self.action_paste.triggered.connect(self.active_document_paste)

        self.action_paste_replace = edit_menu.addAction("Paste with Replacement")
        self.action_paste_replace.setShortcut(QKeySequence("Ctrl+Shift+V"))
        self.action_paste_replace.triggered.connect(self.active_document_paste_replace)

        self.action_duplicate = edit_menu.addAction("Duplicate")
        self.action_duplicate.setShortcut(QKeySequence("Ctrl+D"))
        self.action_duplicate.triggered.connect(self.active_document_duplicate)

        self.action_delete = edit_menu.addAction("Delete")
        self.action_delete.setShortcut(QKeySequence("Delete"))
        self.action_delete.triggered.connect(self.active_document_delete)

        edit_menu.addSeparator()

        self.action_group = edit_menu.addAction("Group Selected")
        self.action_group.setShortcut(QKeySequence("Ctrl+G"))
        self.action_group.triggered.connect(self.active_document_group)

        element_menu = menubar.addMenu("&Element")

        self.action_add_element = element_menu.addAction("New Element...")
        self.action_add_element.setShortcut(QKeySequence("Ctrl+F"))
        self.action_add_element.triggered.connect(self.active_document_add_element)

        self.action_add_preset = element_menu.addAction("New from Preset...")
        self.action_add_preset.triggered.connect(self.active_document_add_preset)

        element_menu.addSeparator()

        self.action_add_operator = element_menu.addAction("Add Operator / Modifier...")
        self.action_add_operator.triggered.connect(self.active_document_add_operator)

        self.action_add_criteria = element_menu.addAction("Add Selection Criteria...")
        self.action_add_criteria.triggered.connect(self.active_document_add_criteria)

        element_menu.addSeparator()

        self.action_add_choice = element_menu.addAction("Add Choice...")
        self.action_add_choice.triggered.connect(self.active_document_add_choice)

        self.action_add_variable = element_menu.addAction("Add Variable...")
        self.action_add_variable.triggered.connect(self.active_document_add_variable)

        element_menu.addSeparator()

        self.action_bulk_import = element_menu.addAction("Bulk Model Importer...")
        self.action_bulk_import.triggered.connect(self.active_document_bulk_import)

        self.action_load_vmap = element_menu.addAction("Load VMAP into Hierarchy...")
        self.action_load_vmap.triggered.connect(self.active_document_load_vmap)

        view_menu = menubar.addMenu("&View")

        self.action_isolate = view_menu.addAction("Isolate in 3D Viewport")
        self.action_isolate.setShortcut(QKeySequence("Ctrl+H"))
        self.action_isolate.triggered.connect(self.active_document_toggle_isolation)

        view_menu.addSeparator()

        self.docks_menu = view_menu.addMenu("Docks & Panels")
        self.update_docks_menu()

        self.action_save_layout = view_menu.addAction("Save Current Layout as Default")
        self.action_save_layout.triggered.connect(self.save_layout_action)

        self.action_reset_layout = view_menu.addAction("Reset Layout")
        self.action_reset_layout.triggered.connect(self.reset_layout_action)

        self.update_menu_states()

    def update_menu_states(self):
        """Enables or disables document-dependent menu actions based on active document presence."""
        doc = self.get_current_document()
        has_doc = doc is not None

        # Document-dependent File actions
        if hasattr(self, 'action_save'): self.action_save.setEnabled(has_doc)
        if hasattr(self, 'action_save_as'): self.action_save_as.setEnabled(has_doc)
        if hasattr(self, 'action_save_all'): self.action_save_all.setEnabled(has_doc)
        if hasattr(self, 'action_close'): self.action_close.setEnabled(has_doc)
        if hasattr(self, 'action_export_scene_debug'): self.action_export_scene_debug.setEnabled(has_doc)

        # Edit menu actions
        if hasattr(self, 'action_undo'): self.action_undo.setEnabled(has_doc)
        if hasattr(self, 'action_redo'): self.action_redo.setEnabled(has_doc)
        if hasattr(self, 'action_cut'): self.action_cut.setEnabled(has_doc)
        if hasattr(self, 'action_copy'): self.action_copy.setEnabled(has_doc)
        if hasattr(self, 'action_paste'): self.action_paste.setEnabled(has_doc)
        if hasattr(self, 'action_paste_replace'): self.action_paste_replace.setEnabled(has_doc)
        if hasattr(self, 'action_duplicate'): self.action_duplicate.setEnabled(has_doc)
        if hasattr(self, 'action_delete'): self.action_delete.setEnabled(has_doc)
        if hasattr(self, 'action_group'): self.action_group.setEnabled(has_doc)

        if hasattr(self, 'action_add_element'): self.action_add_element.setEnabled(has_doc)
        if hasattr(self, 'action_add_preset'): self.action_add_preset.setEnabled(has_doc)
        if hasattr(self, 'action_add_operator'): self.action_add_operator.setEnabled(has_doc)
        if hasattr(self, 'action_add_criteria'): self.action_add_criteria.setEnabled(has_doc)
        if hasattr(self, 'action_add_choice'): self.action_add_choice.setEnabled(has_doc)
        if hasattr(self, 'action_add_variable'): self.action_add_variable.setEnabled(has_doc)
        if hasattr(self, 'action_bulk_import'): self.action_bulk_import.setEnabled(has_doc)
        if hasattr(self, 'action_convert_vmap'): self.action_convert_vmap.setEnabled(has_doc)
        if hasattr(self, 'action_load_vmap'): self.action_load_vmap.setEnabled(has_doc)

        # View menu actions
        if hasattr(self, 'action_isolate'): self.action_isolate.setEnabled(has_doc)
        if hasattr(self, 'action_save_layout'): self.action_save_layout.setEnabled(has_doc)
        if hasattr(self, 'action_reset_layout'): self.action_reset_layout.setEnabled(has_doc)

        self.update_docks_menu()

    def save_all_files(self):
        """Saves all open modified documents."""
        for i in range(self.ui.DocumentTabWidget.count()):
            doc = self.ui.DocumentTabWidget.widget(i)
            if hasattr(doc, 'save_file'):
                doc.save_file(external=False)
                base_name = "Untitled"
                if doc.opened_file:
                    base_name = os.path.splitext(os.path.basename(doc.opened_file))[0]
                self.update_document_tab_title(doc, base_name)

    def export_scene_debug(self):
        """Dump the active document's 3D viewport scene to a .glb, textures included."""
        document = self.get_current_document()
        if document is None:
            QMessageBox.warning(self, "Export Scene", "No document is open.")
            return

        if getattr(document, "_viewport_3d", None) is None:
            document._ensure_viewport_3d()
        viewport = getattr(document, "_viewport_3d", None)
        render_area = getattr(viewport, "render_area", None) if viewport else None
        if render_area is None:
            QMessageBox.warning(self, "Export Scene", "The 3D viewport isn't available.")
            return

        default_name = "scene.glb"
        if document.opened_file:
            default_name = os.path.splitext(os.path.basename(document.opened_file))[0] + ".glb"
        path, _ = QFileDialog.getSaveFileName(self, "Export Scene (debug)", default_name, "glTF Binary (*.glb)")
        if not path:
            return
        if not path.lower().endswith(".glb"):
            path += ".glb"

        from src.editors.smartprop_editor.viewport_3d.scene_export import export_scene_to_glb
        try:
            ok, message = export_scene_to_glb(render_area, path)
        except Exception as exc:
            QMessageBox.critical(self, "Export Scene", f"Export failed: {exc}")
            return

        (QMessageBox.information if ok else QMessageBox.warning)(self, "Export Scene", message)

    def active_document_undo(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'undo_stack'):
            doc.undo_stack.undo()

    def active_document_redo(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'undo_stack'):
            doc.undo_stack.redo()

    def _dispatch_focused_action(self, action_name: str) -> bool:
        doc = self.get_current_document()
        if not doc:
            return False
        focused = QApplication.focusWidget()
        cl = None
        if hasattr(doc, 'smartprop_property_panel') and doc.smartprop_property_panel:
            cl = getattr(doc.smartprop_property_panel, 'components_list', None)
        if cl and focused and (focused == cl or cl.isAncestorOf(focused)):
            if action_name == 'cut':
                cl._cut_focused()
            elif action_name == 'copy':
                cl._copy_focused()
            elif action_name == 'paste':
                cl._paste_focused()
            elif action_name == 'duplicate':
                cl._duplicate_focused()
            elif action_name == 'delete':
                cl._delete_focused()
            return True
        return False

    def active_document_cut(self):
        if self._dispatch_focused_action('cut'):
            return
        doc = self.get_current_document()
        if doc and hasattr(doc, 'cut_item'):
            doc.cut_item(doc.ui.tree_hierarchy_widget)

    def active_document_copy(self):
        if self._dispatch_focused_action('copy'):
            return
        doc = self.get_current_document()
        if doc and hasattr(doc, 'copy_item'):
            doc.copy_item(doc.ui.tree_hierarchy_widget)

    def active_document_paste(self):
        if self._dispatch_focused_action('paste'):
            return
        doc = self.get_current_document()
        if doc and hasattr(doc, 'paste_item'):
            doc.paste_item(doc.ui.tree_hierarchy_widget)

    def active_document_paste_replace(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'new_item_with_replacement'):
            doc.new_item_with_replacement(QApplication.clipboard().text())

    def active_document_duplicate(self):
        if self._dispatch_focused_action('duplicate'):
            return
        doc = self.get_current_document()
        if doc and hasattr(doc, 'ui'):
            doc.ui.tree_hierarchy_widget.DuplicateSelectedItems(doc.element_id_generator)

    def active_document_delete(self):
        if self._dispatch_focused_action('delete'):
            return
        doc = self.get_current_document()
        if doc and hasattr(doc, 'ui'):
            doc.ui.tree_hierarchy_widget.DeleteSelectedItems()

    def active_document_group(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'ui'):
            doc.undo_stack.push(GroupElementsCommand(doc.ui.tree_hierarchy_widget))

    def active_document_add_element(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'add_an_element'):
            doc.add_an_element()

    def active_document_add_preset(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'add_preset'):
            doc.add_preset()

    def active_document_add_operator(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'add_an_operator'):
            doc.add_an_operator()

    def active_document_add_criteria(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'add_a_selection_criteria'):
            doc.add_a_selection_criteria()

    def active_document_add_choice(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'ui'):
            AddChoice(tree=doc.ui.choices_tree_widget, variables_scrollArea=doc.variable_viewport.ui.variables_scrollArea)

    def active_document_add_variable(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'variable_viewport'):
            doc.variable_viewport.add_new_variable()

    def active_document_bulk_import(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'open_bulk_model_importer'):
            doc.open_bulk_model_importer()

    def active_document_load_vmap(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'load_vmap_into_hierarchy'):
            doc.load_vmap_into_hierarchy()
        else:
            QMessageBox.warning(self, "No Document Open", "Please open or create a SmartProp document before loading a VMAP file.")

    def active_document_toggle_isolation(self):
        doc = self.get_current_document()
        if doc and hasattr(doc, 'toggle_isolation'):
            doc.toggle_isolation()

    def update_docks_menu(self):
        if not hasattr(self, 'docks_menu'):
            return
        self.docks_menu.clear()
        explorer_action = self.ui.ExplorerDock.toggleViewAction()
        explorer_action.setText("Explorer")
        self.docks_menu.addAction(explorer_action)
        doc = self.get_current_document()
        if doc:
            self.docks_menu.addSeparator()
            if hasattr(doc, 'ui') and hasattr(doc.ui, 'HierarchyDock'):
                self.docks_menu.addAction(doc.ui.HierarchyDock.toggleViewAction())
            if hasattr(doc, '_property_dock'):
                self.docks_menu.addAction(doc._property_dock.toggleViewAction())
            if hasattr(doc, 'ui') and hasattr(doc.ui, 'VariablesDock'):
                self.docks_menu.addAction(doc.ui.VariablesDock.toggleViewAction())
            if hasattr(doc, 'ui') and hasattr(doc.ui, 'ChoicesDock'):
                self.docks_menu.addAction(doc.ui.ChoicesDock.toggleViewAction())
            if hasattr(doc, '_viewport_dock'):
                self.docks_menu.addAction(doc._viewport_dock.toggleViewAction())
            if hasattr(doc, '_manual_dock'):
                self.docks_menu.addAction(doc._manual_dock.toggleViewAction())
            if hasattr(doc, '_history_dock'):
                self.docks_menu.addAction(doc._history_dock.toggleViewAction())

    def save_layout_action(self):
        idx = self.ui.DocumentTabWidget.currentIndex()
        if idx >= 0:
            self.save_current_layout_as_default(idx)

    def reset_layout_action(self):
        idx = self.ui.DocumentTabWidget.currentIndex()
        if idx >= 0:
            self.reset_document_layout(idx)

    def update_placeholder_visibility(self):
        """
        Updates the UI: hides DocumentTabWidget and shows placeholder_label if no documents are open.
        Otherwise, shows DocumentTabWidget and hides placeholder_label.
        """
        if self.ui.DocumentTabWidget.count() == 0:
            self.ui.DocumentTabWidget.hide()
            self.ui.placeholder_label.show()
        else:
            self.ui.DocumentTabWidget.show()
            self.ui.placeholder_label.hide()
        self.update_menu_states()

    def init_explorer(self, dir: str = None, editor_name: str = None):
        if dir is None:
            self.tree_directory = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name())
        else:
            self.tree_directory = dir
        if editor_name is None:
            editor_name = "SmartPropEditor"

        self.mini_explorer = Explorer(
            tree_directory=self.tree_directory,
            addon=get_addon_name(),
            editor_name=editor_name,
            parent=self.parent
        )
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)

    def create_new_file(self):
        """
        Creates a new blank document in a new tab.
        """
        new_doc = SmartPropDocument(self)
        self._setup_document_signals(new_doc, tab_title="Untitled")
        self.ui.DocumentTabWidget.addTab(new_doc, "Untitled")
        self.update_placeholder_visibility()

    def save_file(self, external=False):
        """
        Saves only the currently active tab (document).
        The 'external' flag indicates whether to perform a 'Save As' operation.
        After saving, updates the tab's text (shows '*' if modified).
        """
        current_index = self.ui.DocumentTabWidget.currentIndex()
        if current_index < 0:
            return

        doc = self.ui.DocumentTabWidget.widget(current_index)
        if hasattr(doc, 'save_file'):

            # Check if the tools files are prepared for vsmart compilation
            check_vsmart_configuration()

            doc.save_file(external=external)
            base_name = "Untitled"
            if doc.opened_file:
                base_name = os.path.splitext(os.path.basename(doc.opened_file))[0]
            self.update_document_tab_title(doc, base_name)
            if self.update_title and doc.opened_file:
                self.update_title('saved', doc.opened_file)

    def open_file(self, external=False, filename=None):
        """
        Opens a .vsmart or .vdata file and creates a new document tab.
        If 'external' is True, uses a file dialog; otherwise uses the path from the explorer.
        Ensures only one instance of an opened file name is open at a time.
        """
        if filename is None:
            if external:
                filename, _ = QFileDialog.getOpenFileName(
                    self,
                    "Open File",
                    os.path.join(cs2_path, "content", "csgo_addons", get_addon_name()),
                    "VSmart Files (*.vsmart *.vdata);;All Files (*)"
                )
            else:
                # Get the currently selected file path from the explorer
                if hasattr(self.mini_explorer, "get_current_path"):
                    filename = self.mini_explorer.get_current_path(absolute=True)

        if filename:
            norm_filename = os.path.abspath(filename)
            extension = os.path.splitext(norm_filename)[1].lower()
            if extension not in (".vsmart", ".vdata"):
                warning_dialog = ErrorInfo(
                    text="Invalid File Format",
                    details="Please select a .vsmart or .vdata file."
                )
                warning_dialog.exec_()
                return

            # Check if file is already open
            tab_count = self.ui.DocumentTabWidget.count()
            for i in range(tab_count):
                doc = self.ui.DocumentTabWidget.widget(i)
                if hasattr(doc, 'opened_file') and doc.opened_file:
                    if os.path.abspath(doc.opened_file) == norm_filename:
                        # Switch to already-open file's tab
                        self.ui.DocumentTabWidget.setCurrentIndex(i)
                        return

            # Create a new document and load file
            document = SmartPropDocument(self)
            document.opened_file = norm_filename
            if hasattr(document, "open_file"):
                document.open_file(norm_filename)

            base_name = os.path.splitext(os.path.basename(norm_filename))[0]
            self._setup_document_signals(document, tab_title=base_name)

            self.ui.DocumentTabWidget.addTab(document, base_name)
            self.update_placeholder_visibility()
            # Track in recent files
            if hasattr(self, 'mini_explorer') and self.mini_explorer is not None:
                self.mini_explorer.add_recent_file(norm_filename)
            if self.update_title:
                self.update_title('opened', norm_filename)

        else:
            error_dialog = ErrorInfo(text="No file selected", details="Please select a file to open.")
            error_dialog.exec_()

    def _setup_document_signals(self, doc, tab_title=None):
        """
        Helper method to connect document change signals (if any) and set initial tab text.
        Ensures the tab name is updated when the document is edited.
        """
        # Connect the _edited signal from the document to update the tab title
        if hasattr(doc, "_edited"):
            doc._edited.connect(lambda d=doc: self.update_document_tab_title(d))
            
        self.update_document_tab_title(doc, tab_title)

    def update_document_tab_title(self, doc, base_name=None):
        """
        If doc is modified, prepend '*' to the tab name; otherwise use base_name.
        """
        idx = self.ui.DocumentTabWidget.indexOf(doc)
        if idx != -1 and hasattr(doc, 'is_modified'):
            if not base_name:
                if getattr(doc, 'opened_file', None):
                    base_name = os.path.splitext(os.path.basename(doc.opened_file))[0]
                else:
                    base_name = "Untitled"
            text = f"*{base_name}" if doc.is_modified() else base_name
            self.ui.DocumentTabWidget.setTabText(idx, text)

    def unsaved_files(self):
        """(label, save_callable) for every modified document tab."""
        files = []
        for i in range(self.ui.DocumentTabWidget.count()):
            doc = self.ui.DocumentTabWidget.widget(i)
            if hasattr(doc, 'is_modified') and doc.is_modified():
                files.append((doc.opened_file or "Untitled", partial(self._save_document, doc)))
        return files

    def _save_document(self, doc):
        """Save a specific document tab through the regular save path."""
        self.ui.DocumentTabWidget.setCurrentWidget(doc)
        self.save_file()

    def close_document(self, index=None):
        """
        Closes the document tab. If index is not provided, closes the currently active tab.
        If the document has unsaved changes, prompts the user before closing.
        """
        if index is None:
            index = self.ui.DocumentTabWidget.currentIndex()

        if index < 0 or index >= self.ui.DocumentTabWidget.count():
            return

        doc = self.ui.DocumentTabWidget.widget(index)
        if hasattr(doc, "is_modified") and doc.is_modified():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "This document has unsaved changes. Do you want to close it without saving?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        removed_widget = self.ui.DocumentTabWidget.widget(index)
        # Persist the dock/viewport layout before the document is destroyed.
        # Closing a tab uses removeTab()+deleteLater(), which never fires the
        # document's closeEvent, so the layout has to be saved explicitly here.
        if isinstance(removed_widget, SmartPropDocument):
            try:
                removed_widget._save_user_prefs()
            except Exception:
                pass
        self.ui.DocumentTabWidget.removeTab(index)
        if removed_widget is not None:
            removed_widget.deleteLater()
        self.update_placeholder_visibility()

    def show_tab_context_menu(self, position):
        index = self.ui.DocumentTabWidget.tabBar().tabAt(position)
        if index < 0:
            return

        menu = QMenu(self)
        save_layout_action = menu.addAction("Save Current Layout as Default")
        save_layout_action.triggered.connect(lambda: self.save_current_layout_as_default(index))
        reset_layout_action = menu.addAction("Reset Layout")
        reset_layout_action.triggered.connect(lambda: self.reset_document_layout(index))

        menu.exec(self.ui.DocumentTabWidget.mapToGlobal(position))

    def save_current_layout_as_default(self, index):
        doc = self.ui.DocumentTabWidget.widget(index)
        if isinstance(doc, SmartPropDocument):
            doc.save_layout_as_default()

    def reset_document_layout(self, index):
        doc = self.ui.DocumentTabWidget.widget(index)
        if isinstance(doc, SmartPropDocument):
            doc.reset_layout()

    def _persist_current_document_layout(self):
        """Save the active document's dock/viewport layout as the 'last' layout.

        Used as the app-quit / window-close persistence point, since the nested
        SmartPropDocument widgets do not receive closeEvent on those paths.
        """
        try:
            doc = self.ui.DocumentTabWidget.currentWidget()
        except RuntimeError:
            # Tab widget already torn down.
            return
        if isinstance(doc, SmartPropDocument):
            try:
                doc._save_user_prefs()
            except Exception:
                pass

    def closeEvent(self, event):
        """
        Overridden close event to persist layout and perform cleanup.
        """
        # Closed on addon switch: keep the current layout so the next addon's
        # documents open with the arrangement the user last used.
        self._persist_current_document_layout()
        event.accept()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartPropEditorMainWindow()
    window.show()
    sys.exit(app.exec())