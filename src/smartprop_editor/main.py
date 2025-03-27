import sys
import os.path
from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QApplication,
    QMessageBox
)
from PySide6.QtGui import QUndoStack
from PySide6.QtCore import QTimer
from src.settings.main import get_settings_value, get_settings_bool
from src.smartprop_editor.ui_main import Ui_MainWindow
from src.settings.main import get_addon_name, settings
from src.explorer.main import Explorer
from src.smartprop_editor.document import SmartPropDocument
from src.widgets import ErrorInfo
from src.common import (
    enable_dark_title_bar,
    get_cs2_path,
    SmartPropEditor_Preset_Path,
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
        self.realtime_save = False
        self.opened_file = None
        self.update_title = update_title
        enable_dark_title_bar(self)

        # Make the tab widget closable and connect to our close_document method
        self.ui.DocumentTabWidget.setTabsClosable(True)
        self.ui.DocumentTabWidget.tabCloseRequested.connect(self.close_document)

        # Initialize file explorer
        self.init_explorer()

        # Initialize button signals
        self.buttons()

        set_qdock_tab_style(self.findChildren)

        self.undo_stack = QUndoStack(self)

        # Initialize realtime save timer (interval from settings or default to 2000ms)
        delay = int(float(get_settings_value('SmartPropEditor', 'realtime_saving_delay', 5)))
        self.realtime_save_timer = QTimer(self)
        self.realtime_save_timer.setInterval(delay)
        self.realtime_save_timer.timeout.connect(self.realtime_save_all)

        # Set initial UI state based on document availability
        self.update_placeholder_visibility()

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
            parent=self.ui.explorer_layout_widget
        )
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)

    def buttons(self):
        self.ui.open_file_button.clicked.connect(lambda: self.open_file())
        self.ui.open_file_as_button.clicked.connect(lambda: self.open_file(external=True))
        self.ui.save_file_button.clicked.connect(lambda: self.save_file())
        self.ui.save_as_file_button.clicked.connect(lambda: self.save_file(external=True))
        self.ui.cerate_file_button.clicked.connect(self.create_new_file)
        self.ui.realtime_save_checkbox.clicked.connect(self.realtime_save_action)

    def realtime_save_action(self):
        self.realtime_save = self.ui.realtime_save_checkbox.isChecked()
        if get_settings_bool('SmartPropEditor', 'enable_transparency_window', True):
            if self.realtime_save:
                transparency = float(get_settings_value('SmartPropEditor', 'transparency_window', 70)) / 100
                self.parent.setWindowOpacity(transparency)
            else:
                self.parent.setWindowOpacity(1)
        # Start or stop the realtime save timer
        if self.realtime_save:
            self.realtime_save_timer.start()
        else:
            self.realtime_save_timer.stop()

    def realtime_save_all(self):
        # Iterate over all open tabs/documents and auto-save if modified
        for i in range(self.ui.DocumentTabWidget.count()):
            doc = self.ui.DocumentTabWidget.widget(i)
            if hasattr(doc, 'is_modified') and doc.is_modified():
                # Auto-save document (assumed to be non-external save)
                if hasattr(doc, 'save_file'):
                    doc.save_file(external=False)
                    base_name = "Untitled"
                    if doc.opened_file:
                        base_name = os.path.splitext(os.path.basename(doc.opened_file))[0]
                    self.update_document_tab_title(doc, base_name)

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
            doc.save_file(external=external)
            base_name = "Untitled"
            if doc.opened_file:
                base_name = os.path.splitext(os.path.basename(doc.opened_file))[0]
            self.update_document_tab_title(doc, base_name)

    def open_file(self, external=False):
        """
        Opens a .vsmart or .vdata file and creates a new document tab.
        If 'external' is True, uses a file dialog; otherwise uses the path from the explorer.
        Ensures only one instance of an opened file name is open at a time.
        """
        filename = None
        if external:
            # Open a file dialog to select the file
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
            # Only .vsmart or .vdata
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
        else:
            error_dialog = ErrorInfo(text="No file selected", details="Please select a file to open.")
            error_dialog.exec_()

    def _setup_document_signals(self, doc, tab_title):
        """
        Helper method to connect document change signals (if any) and set initial tab text.
        Ensures the tab name is updated when the document is edited.
        """
        # Connect the _edited signal from the document to update the tab title
        if hasattr(doc, "_edited"):
            doc._edited.connect(lambda: self.update_document_tab_title(doc, tab_title))
        self.update_document_tab_title(doc, tab_title)

    def update_document_tab_title(self, doc, base_name):
        """
        If doc is modified, prepend '*' to the tab name; otherwise use base_name.
        """
        idx = self.ui.DocumentTabWidget.indexOf(doc)
        if idx != -1 and hasattr(doc, 'is_modified'):
            text = f"*{base_name}" if doc.is_modified() else base_name
            self.ui.DocumentTabWidget.setTabText(idx, text)

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
        self.ui.DocumentTabWidget.removeTab(index)
        if removed_widget is not None:
            removed_widget.deleteLater()
        self.update_placeholder_visibility()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartPropEditorMainWindow()
    window.show()
    sys.exit(app.exec())