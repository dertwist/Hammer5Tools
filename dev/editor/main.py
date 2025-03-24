import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QTextEdit, 
                              QFileDialog, QMessageBox, QToolBar, QStatusBar, QMenu)
from PySide6.QtGui import QAction, QIcon, QKeySequence, QCursor
from PySide6.QtCore import Qt, QSize, Signal, Slot, QObject


class TextEditor(QTextEdit):
    """Custom text editor widget with change tracking"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.is_modified = False
        self.textChanged.connect(self.handle_text_changed)

    def handle_text_changed(self):
        """Mark document as modified when text changes"""
        if not self.is_modified:
            self.is_modified = True
            # Notify parent tab widget that this document has been modified
            if self.parent() and hasattr(self.parent(), 'update_tab_title'):
                self.parent().update_tab_title(self)


class EditorTabWidget(QTabWidget):
    """Tab widget to manage multiple document editors"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.close_tab)

        # Enable context menu for tabs
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_tab_context_menu)

    def add_new_document(self, file_path=None):
        """Add a new document tab"""
        editor = TextEditor(self)

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    editor.setPlainText(file.read())
                editor.file_path = file_path
                editor.is_modified = False
                tab_name = os.path.basename(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {str(e)}")
                return None
        else:
            tab_name = "Untitled"

        index = self.addTab(editor, tab_name)
        self.setCurrentIndex(index)
        return editor

    def update_tab_title(self, editor):
        """Update tab title to show modified status"""
        index = self.indexOf(editor)
        if index != -1:
            title = self.tabText(index)
            if not title.endswith('*'):
                self.setTabText(index, f"{title}*")

    def close_tab(self, index):
        """Handle tab close with unsaved changes warning"""
        editor = self.widget(index)

        if editor.is_modified:
            response = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"The document '{self.tabText(index)}' has unsaved changes. Do you want to save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )

            if response == QMessageBox.Save:
                if not self.parent().save_document(editor):
                    # If save was cancelled or failed, don't close the tab
                    return
            elif response == QMessageBox.Cancel:
                return

        self.removeTab(index)

    def show_tab_context_menu(self, position):
        """Show context menu for tabs"""
        tab_bar = self.tabBar()
        tab_index = tab_bar.tabAt(position)

        if tab_index != -1:
            context_menu = QMenu(self)

            # Detach tab action
            detach_action = QAction("Open in New Window", self)
            detach_action.triggered.connect(lambda: self.detach_tab(tab_index))
            context_menu.addAction(detach_action)

            # Close tab action
            close_action = QAction("Close", self)
            close_action.triggered.connect(lambda: self.close_tab(tab_index))
            context_menu.addAction(close_action)

            # Show the context menu
            context_menu.exec_(QCursor.pos())

    def detach_tab(self, index):
        """Detach the tab to a new window"""
        if index < 0 or index >= self.count():
            return

        # Get the tab content and title
        editor = self.widget(index)
        tab_title = self.tabText(index)

        # Create a new detached window
        detached_window = DetachedEditorWindow(self.parent().app, editor, tab_title, self.parent())

        # Remove the tab without triggering close confirmation
        self.removeTab(index)

        # Show the detached window
        detached_window.show()


class DetachedEditorWindow(QMainWindow):
    """Window for a detached editor tab"""

    def __init__(self, app, editor, title, main_window):
        super().__init__()
        self.app = app
        self.editor = editor
        self.original_title = title.rstrip('*')  # Remove asterisk if present
        self.main_window = main_window  # Store reference to main window

        # Set window properties
        self.setWindowTitle(title)
        self.resize(600, 400)

        # Take ownership of the editor
        editor.setParent(self)
        self.setCentralWidget(editor)

        # Create toolbar
        self.create_toolbar()

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Show status message
        self.status_bar.showMessage("Document opened in new window. Close window to return to main editor.", 5000)

    def create_toolbar(self):
        """Create the toolbar for the detached window"""
        toolbar = QToolBar("File Operations")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        # Save document action
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_document)
        toolbar.addAction(save_action)

        # Save As document action
        save_as_action = QAction("Save As", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(lambda: self.save_document(save_as=True))
        toolbar.addAction(save_as_action)

        # Add separator
        toolbar.addSeparator()

        # Return to main window action
        return_action = QAction("Return to Main Editor", self)
        return_action.setShortcut(QKeySequence("Ctrl+R"))
        return_action.triggered.connect(self.return_to_main)
        toolbar.addAction(return_action)

    def save_document(self, save_as=False):
        """Save the document to a file"""
        if not self.editor.file_path or save_as:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save File", "", "Text Files (*.txt);;All Files (*)"
            )

            if not file_path:
                return False  # User cancelled

            self.editor.file_path = file_path

        try:
            with open(self.editor.file_path, 'w', encoding='utf-8') as file:
                file.write(self.editor.toPlainText())

            self.editor.is_modified = False
            self.setWindowTitle(os.path.basename(self.editor.file_path))
            self.status_bar.showMessage(f"Saved to {self.editor.file_path}", 3000)
            return True

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
            return False

    def return_to_main(self):
        """Return this editor to the main window"""
        self.reattach_to_main()

    def reattach_to_main(self):
        """Reattach this editor to the main window"""
        # Add the editor back to the main window's tab widget
        self.editor.setParent(None)  # Detach from current parent
        self.main_window.tab_widget.addTab(self.editor, self.windowTitle())
        self.main_window.tab_widget.setCurrentWidget(self.editor)
        self.main_window.activateWindow()  # Bring main window to front

        # Close this window
        self.close()

    def closeEvent(self, event):
        """Handle window close with unsaved changes warning"""
        if self.editor.is_modified:
            response = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"The document has unsaved changes. Do you want to save before returning to main editor?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )

            if response == QMessageBox.Save:
                if not self.save_document():
                    event.ignore()
                    return
            elif response == QMessageBox.Cancel:
                event.ignore()
                return

        # Return the editor to the main window instead of closing it
        self.editor.setParent(None)  # Detach from current parent
        self.main_window.tab_widget.addTab(self.editor, self.windowTitle())
        self.main_window.tab_widget.setCurrentWidget(self.editor)

        event.accept()


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, app):
        super().__init__()
        self.app = app  # Store reference to QApplication
        self.setWindowTitle("Multi-Document Text Editor")
        self.resize(800, 600)

        # Create tab widget for multiple documents
        self.tab_widget = EditorTabWidget(self)
        self.setCentralWidget(self.tab_widget)

        # Create toolbar
        self.create_toolbar()

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Create a new empty document by default
        self.tab_widget.add_new_document()

    def create_toolbar(self):
        """Create the application toolbar with file operations"""
        toolbar = QToolBar("File Operations")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        # New document action
        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_document)
        toolbar.addAction(new_action)

        # Open document action
        open_action = QAction("Open", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_document)
        toolbar.addAction(open_action)

        # Save document action
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_current_document)
        toolbar.addAction(save_action)

        # Save As document action
        save_as_action = QAction("Save As", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self.save_as_current_document)
        toolbar.addAction(save_as_action)

        # Add separator
        toolbar.addSeparator()

        # Open in new window action (renamed from "Detach")
        open_window_action = QAction("Open in New Window", self)
        open_window_action.setShortcut(QKeySequence("Ctrl+W"))
        open_window_action.triggered.connect(self.open_in_new_window)
        toolbar.addAction(open_window_action)

    def new_document(self):
        """Create a new empty document"""
        self.tab_widget.add_new_document()

    def open_document(self):
        """Open an existing document"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            # Check if the file is already open
            for i in range(self.tab_widget.count()):
                editor = self.tab_widget.widget(i)
                if editor.file_path == file_path:
                    self.tab_widget.setCurrentIndex(i)
                    return

            # If not already open, create a new tab
            self.tab_widget.add_new_document(file_path)

    def get_current_editor(self):
        """Get the currently active editor"""
        return self.tab_widget.currentWidget()

    def save_current_document(self):
        """Save the current document"""
        editor = self.get_current_editor()
        if editor:
            self.save_document(editor)

    def save_as_current_document(self):
        """Save the current document with a new name"""
        editor = self.get_current_editor()
        if editor:
            self.save_document(editor, save_as=True)

    def save_document(self, editor, save_as=False):
        """Save the document to a file"""
        if not editor.file_path or save_as:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save File", "", "Text Files (*.txt);;All Files (*)"
            )

            if not file_path:
                return False  # User cancelled

            editor.file_path = file_path

        try:
            with open(editor.file_path, 'w', encoding='utf-8') as file:
                file.write(editor.toPlainText())

            editor.is_modified = False
            index = self.tab_widget.indexOf(editor)
            self.tab_widget.setTabText(index, os.path.basename(editor.file_path))
            self.status_bar.showMessage(f"Saved to {editor.file_path}", 3000)
            return True

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
            return False

    def open_in_new_window(self):
        """Open the current tab in a new window"""
        current_index = self.tab_widget.currentIndex()
        if current_index != -1:
            self.tab_widget.detach_tab(current_index)
            self.status_bar.showMessage("Document opened in new window", 3000)

    def closeEvent(self, event):
        """Handle application close with unsaved changes warning"""
        unsaved_tabs = []

        # Check tabs in the main window
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if editor.is_modified:
                unsaved_tabs.append((i, self.tab_widget.tabText(i), editor, self))

        # Check detached windows
        for window in self.app.topLevelWidgets():
            if isinstance(window, DetachedEditorWindow) and window.editor.is_modified:
                unsaved_tabs.append((0, window.windowTitle(), window.editor, window))

        if unsaved_tabs:
            message = "The following documents have unsaved changes:\n\n"
            for _, name, _, _ in unsaved_tabs:
                message += f"• {name}\n"
            message += "\nDo you want to save these changes before closing?"

            response = QMessageBox.question(
                self,
                "Unsaved Changes",
                message,
                QMessageBox.SaveAll | QMessageBox.Discard | QMessageBox.Cancel
            )

            if response == QMessageBox.SaveAll:
                for i, _, editor, window in unsaved_tabs:
                    if isinstance(window, MainWindow):
                        self.tab_widget.setCurrentIndex(i)
                        if not self.save_document(editor):
                            event.ignore()
                            return
                    else:  # DetachedEditorWindow
                        window.activateWindow()
                        if not window.save_document():
                            event.ignore()
                            return

            elif response == QMessageBox.Cancel:
                event.ignore()
                return

        # Close all detached windows
        for window in self.app.topLevelWidgets():
            if isinstance(window, DetachedEditorWindow):
                window.close()

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(app)
    window.show()
    sys.exit(app.exec())