import os
import json
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QDockWidget, QFileDialog, 
    QMessageBox, QToolBar, QStatusBar, QApplication, QWidget, QVBoxLayout
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QKeySequence, QAction

from hierarchy_widget import HierarchyWidget
from text_view_widget import TextViewWidget
from statistics_widget import StatisticsWidget
from file_explorer_widget import FileExplorerWidget
from document import Document, DocumentTabWidget
import keyvalues3 as kv3

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON Hierarchical Editor")
        self.settings = QSettings("JSONEditor", "HierarchicalEditor")

        # Central document tab widget and a main text editor area (JSON editor updates based on hierarchy)
        self.tab_widget = DocumentTabWidget(self)
        self.setCentralWidget(self.tab_widget)

        # Create dock widgets
        self.create_dock_widgets()

        # Setup actions, menus, toolbars and status bar
        self.create_actions()
        self.create_menus()
        self.create_toolbars()
        self.create_status_bar()

        # Create a new untitled empty document by default
        self.new_document()

        # If a sample kv3 file exists, load it (optional behavior)
        sample_kv3 = os.path.join(os.path.dirname(__file__), "sample.kv3")
        if os.path.exists(sample_kv3):
            self.open_file(sample_kv3)

        # Restore previous window state if any
        self.restore_state()

    def create_dock_widgets(self):
        # Hierarchy dock widget
        self.hierarchy_dock = QDockWidget("Hierarchy", self)
        self.hierarchy_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.hierarchy_widget = HierarchyWidget()
        self.hierarchy_dock.setWidget(self.hierarchy_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.hierarchy_dock)

        # Text view dock widget
        self.text_view_dock = QDockWidget("Text View", self)
        self.text_view_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.text_view_widget = TextViewWidget()
        self.text_view_dock.setWidget(self.text_view_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.text_view_dock)

        # Statistics dock widget
        self.statistics_dock = QDockWidget("Statistics", self)
        self.statistics_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.statistics_widget = StatisticsWidget()
        self.statistics_dock.setWidget(self.statistics_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.statistics_dock)

        # File explorer dock widget
        self.file_explorer_dock = QDockWidget("File Explorer", self)
        self.file_explorer_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.file_explorer_widget = FileExplorerWidget()
        self.file_explorer_dock.setWidget(self.file_explorer_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.file_explorer_dock)

        # Resize docks for initial layout
        self.resizeDocks([self.hierarchy_dock, self.file_explorer_dock], [200, 200], Qt.Horizontal)
        self.resizeDocks([self.text_view_dock], [150], Qt.Vertical)

        # Connect signals between widgets and document
        self.hierarchy_widget.item_selected.connect(self.on_hierarchy_item_selected)
        self.file_explorer_widget.file_selected.connect(self.open_file)

    def create_actions(self):
        # File actions
        self.new_action = QAction("&New", self)
        self.new_action.setShortcut(QKeySequence.New)
        self.new_action.triggered.connect(self.new_document)

        self.open_action = QAction("&Open...", self)
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.triggered.connect(self.open_document)

        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.triggered.connect(self.save_document)

        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setShortcut(QKeySequence.SaveAs)
        self.save_as_action.triggered.connect(self.save_document_as)

        self.close_action = QAction("&Close", self)
        self.close_action.setShortcut(QKeySequence.Close)
        self.close_action.triggered.connect(self.close_document)

        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.triggered.connect(self.close)

        # Edit actions
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.undo_action.triggered.connect(self.undo)

        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut(QKeySequence.Redo)
        self.redo_action.triggered.connect(self.redo)

        # View actions for dock widget toggling
        self.toggle_hierarchy_action = QAction("&Hierarchy", self, checkable=True)
        self.toggle_hierarchy_action.setChecked(True)
        self.toggle_hierarchy_action.triggered.connect(
            lambda checked: self.hierarchy_dock.setVisible(checked))

        self.toggle_text_view_action = QAction("&Text View", self, checkable=True)
        self.toggle_text_view_action.setChecked(True)
        self.toggle_text_view_action.triggered.connect(
            lambda checked: self.text_view_dock.setVisible(checked))

        self.toggle_statistics_action = QAction("&Statistics", self, checkable=True)
        self.toggle_statistics_action.setChecked(True)
        self.toggle_statistics_action.triggered.connect(
            lambda checked: self.statistics_dock.setVisible(checked))

        self.toggle_file_explorer_action = QAction("&File Explorer", self, checkable=True)
        self.toggle_file_explorer_action.setChecked(True)
        self.toggle_file_explorer_action.triggered.connect(
            lambda checked: self.file_explorer_dock.setVisible(checked))

    def create_menus(self):
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.close_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)

        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.toggle_hierarchy_action)
        view_menu.addAction(self.toggle_text_view_action)
        view_menu.addAction(self.toggle_statistics_action)
        view_menu.addAction(self.toggle_file_explorer_action)

    def create_toolbars(self):
        file_toolbar = QToolBar("File")
        file_toolbar.addAction(self.new_action)
        file_toolbar.addAction(self.open_action)
        file_toolbar.addAction(self.save_action)
        self.addToolBar(file_toolbar)

        edit_toolbar = QToolBar("Edit")
        edit_toolbar.addAction(self.undo_action)
        edit_toolbar.addAction(self.redo_action)
        self.addToolBar(edit_toolbar)

    def create_status_bar(self):
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Ready")

    def new_document(self):
        # Create an empty document and explicitly clear its content
        document = Document()
        # Clear any default sample data for new document; set content to empty JSON object.
        document.set_content("{}")
        self.tab_widget.add_document(document)
        self.update_ui()

    def open_document(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "JSON Files (*.json);;KV3 Files (*.kv3);;All Files (*)"
        )
        if file_path:
            self.open_file(file_path)

    def open_file(self, file_path):
        # Check if already open
        for i in range(self.tab_widget.count()):
            document = self.tab_widget.document_at(i)
            if document.file_path == file_path:
                self.tab_widget.setCurrentIndex(i)
                return

        try:
            with open(file_path, 'r') as file:
                content = file.read()
            document = Document(file_path)
            # if opening a kv3 file, convert it to JSON first using keyvalues3
            if file_path.lower().endswith('.kv3'):
                try:
                    import keyvalues3
                    # keyvalues3.kv3_to_json converts kv3 format to a dictionary
                    data_dict = keyvalues3.kv3_to_json(content)
                    content = json.dumps(data_dict, indent=2)
                except Exception as conv_err:
                    raise ValueError(f"Failed to convert kv3 file: {conv_err}")
            document.set_content(content)
            self.tab_widget.add_document(document)

            # Update file explorer directory display
            directory = os.path.dirname(file_path)
            if directory:
                self.file_explorer_widget.set_directory(directory)
            self.statusBar().showMessage(f"Opened {file_path}", 3000)
            self.update_ui()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file: {str(e)}")

    def save_document(self):
        current_document = self.tab_widget.current_document()
        if not current_document:
            return
        if current_document.file_path:
            self.save_document_to_path(current_document, current_document.file_path)
        else:
            self.save_document_as()

    def save_document_as(self):
        current_document = self.tab_widget.current_document()
        if not current_document:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.save_document_to_path(current_document, file_path)

    def save_document_to_path(self, document, file_path):
        try:
            content = document.get_content()
            with open(file_path, 'w') as file:
                file.write(content)
            document.file_path = file_path
            document.set_modified(False)
            self.tab_widget.update_tab_text(document)
            # Update file explorer directory
            directory = os.path.dirname(file_path)
            if directory:
                self.file_explorer_widget.set_directory(directory)
            self.statusBar().showMessage(f"Saved {file_path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")

    def close_document(self):
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self.tab_widget.close_tab(current_index)

    def undo(self):
        current_document = self.tab_widget.current_document()
        if current_document:
            current_document.undo()

    def redo(self):
        current_document = self.tab_widget.current_document()
        if current_document:
            current_document.redo()

    def on_hierarchy_item_selected(self, item_data):
        current_document = self.tab_widget.current_document()
        if current_document:
            # Update selected item in document (which then notifies the JSON editor)
            current_document.select_item(item_data)
            # Also update the text view and statistics dock
            self.text_view_widget.set_text(json.dumps(item_data, indent=2))
            self.statistics_widget.update_statistics(item_data)

    def update_ui(self):
        has_document = self.tab_widget.count() > 0
        current_document = self.tab_widget.current_document()
        self.save_action.setEnabled(has_document)
        self.save_as_action.setEnabled(has_document)
        self.close_action.setEnabled(has_document)

        if current_document:
            # Update hierarchy widget with current document data; if document is empty, clear it.
            self.hierarchy_widget.set_data(current_document.data)
            title = f"{current_document.display_name} - JSON Hierarchical Editor"
            if current_document.is_modified():
                title = f"*{title}"
            self.setWindowTitle(title)
            self.undo_action.setEnabled(current_document.can_undo())
            self.redo_action.setEnabled(current_document.can_redo())
        else:
            self.setWindowTitle("JSON Hierarchical Editor")
            self.undo_action.setEnabled(False)
            self.redo_action.setEnabled(False)
            # Clear widgets if no document present
            self.hierarchy_widget.set_data({})
            self.text_view_widget.set_text("")
            self.statistics_widget.update_statistics({})

    def closeEvent(self, event):
        if self.tab_widget.has_unsaved_changes():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Some documents have unsaved changes. Save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                for i in range(self.tab_widget.count()):
                    document = self.tab_widget.document_at(i)
                    if document.is_modified():
                        self.tab_widget.setCurrentIndex(i)
                        self.save_document()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
        self.save_state()
        event.accept()

    def save_state(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

    def restore_state(self):
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())