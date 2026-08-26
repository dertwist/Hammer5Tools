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
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton
)
from PySide6.QtGui import QUndoStack, QIcon, QKeySequence, QAction, QPixmap
from PySide6.QtCore import Qt
from gui.editors.smartprop_editor.ui_main import Ui_MainWindow
from gui.settings.main import (
    get_addon_name,
    settings,
    get_settings_value,
    set_settings_value,
)
from gui.widgets.explorer.main import Explorer
from gui.editors.smartprop_editor.document import SmartPropDocument
from gui.other.assettypes import check_vsmart_configuration
from gui.widgets import ErrorInfo, exception_handler
from gui.common import (
    enable_dark_title_bar,
    get_cs2_path,
    set_qdock_tab_style
)

from gui.widgets.document_tab import DocumentTabBar
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

        # Setup DocumentTabBar on DocumentTabWidget (supports middle-click close and adjacent Valve new-tab button)
        self.doc_tab_bar = DocumentTabBar(self.ui.DocumentTabWidget)
        self.doc_tab_bar.set_new_tab_tooltip("Create New SmartProp (Ctrl+N)")
        self.doc_tab_bar.new_tab_requested.connect(self.create_new_file)
        self.ui.DocumentTabWidget.setTabBar(self.doc_tab_bar)
        self.ui.DocumentTabWidget.setTabsClosable(True)
        self.ui.DocumentTabWidget.setMovable(True)
        self.ui.DocumentTabWidget.setDocumentMode(True)
        self.ui.DocumentTabWidget.tabCloseRequested.connect(self.close_document)
        self.ui.DocumentTabWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.DocumentTabWidget.customContextMenuRequested.connect(self.show_tab_context_menu)

        self.new_tab_btn = self.doc_tab_bar.new_tab_btn

        # Global shortcuts for when no document tab is focused/open
        self.action_new_global = QAction(self)
        self.action_new_global.setShortcut(QKeySequence.New)
        self.action_new_global.triggered.connect(self.create_new_file)
        self.addAction(self.action_new_global)

        self.action_open_global = QAction(self)
        self.action_open_global.setShortcut(QKeySequence.Open)
        self.action_open_global.triggered.connect(lambda: self.open_file(external=True))
        self.addAction(self.action_open_global)

        # Initialize file explorer
        self.init_explorer()
        # Hide the Explorer dock title bar (no label, no float/close buttons)
        from PySide6.QtWidgets import QWidget as _QWidget
        self.ui.ExplorerDock.setTitleBarWidget(_QWidget())

        set_qdock_tab_style(self.findChildren)

        self.undo_stack = QUndoStack(self)

        # Build placeholder empty state view
        self._build_empty_state()

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

    def _build_empty_state(self):
        """
        Builds the empty state placeholder widget when no documents are open,
        matching the design in AssetGroup Maker.
        """
        self.empty_state_widget = QWidget(self.ui.centralwidget)
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(QPixmap(":/icons/tools/assettypes/vsmart_sm.png").scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_lbl.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon_lbl)

        title_lbl = QLabel("Create or open a SmartProp")
        title_lbl.setProperty("h5Component", "emptyStateTitle")
        title_lbl.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(title_lbl)

        desc_lbl = QLabel("Select a .vsmart or .vdata file in the Explorer on the left, open an existing file, or create a new SmartProp.")
        desc_lbl.setProperty("h5Component", "emptyStateDescription")
        desc_lbl.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(desc_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setAlignment(Qt.AlignCenter)

        btn_open = QPushButton("Open File...")
        btn_open.setIcon(QIcon(":/valve_common/icons/tools/common/open.png"))
        btn_open.setProperty("h5Component", "legacyButton")
        btn_open.setFixedHeight(26)
        btn_open.clicked.connect(lambda: self.open_file(external=True))
        btn_row.addWidget(btn_open)

        btn_new = QPushButton("Create New...")
        btn_new.setIcon(QIcon(":/valve_common/icons/tools/common/new.png"))
        btn_new.setProperty("h5Component", "legacyButton")
        btn_new.setFixedHeight(26)
        btn_new.clicked.connect(self.create_new_file)
        btn_row.addWidget(btn_new)

        empty_layout.addLayout(btn_row)
        self.ui.verticalLayout.addWidget(self.empty_state_widget)

    def update_placeholder_visibility(self):
        """
        Updates the UI: hides DocumentTabWidget and shows empty_state_widget if no documents are open.
        Otherwise, shows DocumentTabWidget and hides empty_state_widget.
        """
        if self.ui.DocumentTabWidget.count() == 0:
            self.ui.DocumentTabWidget.hide()
            if hasattr(self, 'empty_state_widget') and self.empty_state_widget is not None:
                self.empty_state_widget.show()
        else:
            self.ui.DocumentTabWidget.show()
            if hasattr(self, 'empty_state_widget') and self.empty_state_widget is not None:
                self.empty_state_widget.hide()

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

            saved = doc.save_file(external=external)
            if saved is False:
                return
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
                if not filename:
                    return
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
