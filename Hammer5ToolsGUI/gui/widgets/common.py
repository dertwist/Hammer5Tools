import ast
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QDoubleSpinBox, QFrame, QSpacerItem, QSizePolicy, \
    QComboBox, QTreeWidget, QTreeWidgetItem, QDialog, QMessageBox, QPushButton, QApplication, QLabel, QLineEdit, \
    QCheckBox, QVBoxLayout, QToolBox, QToolButton
from PySide6.QtGui import QStandardItemModel
from PySide6.QtGui import QIcon, QColor, QFont
import sys, webbrowser
from gui.styles.common import *
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QTextEdit, QDoubleSpinBox, QFrame, QSpacerItem, \
    QSizePolicy, QComboBox, QTreeWidget, QTreeWidgetItem, QDialog, QMessageBox, QPushButton, QApplication, QLabel, \
    QLineEdit, QCheckBox, QVBoxLayout, QToolBox, QToolButton, QGroupBox, QButtonGroup
from PySide6.QtGui import QStandardItemModel
from PySide6.QtGui import QIcon, QColor, QFont
import sys, webbrowser
from gui.styles.common import *
from PySide6.QtWidgets import QMessageBox, QFileDialog, QScrollArea
from PySide6.QtGui import QIcon
import os, webbrowser
from gui.common import discord_feedback_channel
from logging import error
import traceback, ctypes
from gui.common import enable_dark_title_bar
try:
    import winsound
except ImportError:
    winsound = None


class ErrorInfo(QDialog):
    def __init__(self, text="Error", details="", is_warning=False, dont_show_setting=None, title=None):
        super().__init__()
        dialog_title = title if title is not None else ("Warning" if is_warning else "Error")
        self.setWindowTitle(dialog_title)
        self.setWindowIcon(QIcon("../appicon.ico"))
        enable_dark_title_bar(self)
        self.setMinimumSize(600, 400)
        self.setModal(True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.details = details
        self.dont_show_setting = dont_show_setting

        if winsound is None:
            pass
        elif is_warning:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        else:
            winsound.MessageBeep(winsound.MB_ICONHAND)

        main_layout = QVBoxLayout(self)

        self.message_label = QLabel(text)
        self.message_label.setWordWrap(True)
        main_layout.addWidget(self.message_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlainText(self.details)
        self.details_text.setProperty("h5Component", "errorInfoDetails")
        self.details_text.setProperty("h5State", "warning" if is_warning else "error")
        main_layout.addWidget(self.details_text)

        buttons_layout = QHBoxLayout()

        self.save_button = QPushButton("Save Details")
        self.save_button.clicked.connect(self.save_details)
        buttons_layout.addWidget(self.save_button)

        self.report_button = QPushButton("Report")
        self.report_button.clicked.connect(self.report_issue)
        buttons_layout.addWidget(self.report_button)

        if self.dont_show_setting:
            self.dont_show_button = QPushButton("Don't show again")
            self.dont_show_button.clicked.connect(self.dont_show_again)
            buttons_layout.addWidget(self.dont_show_button)

        # Spacer to push Close button to the right
        buttons_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_button)

        main_layout.addLayout(buttons_layout)

    def dont_show_again(self):
        if self.dont_show_setting:
            from gui.settings.common import set_settings_bool
            if isinstance(self.dont_show_setting, (tuple, list)):
                section, key = self.dont_show_setting
                set_settings_bool(section, key, False)
            elif callable(self.dont_show_setting):
                self.dont_show_setting()
        self.close()

    def save_details(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Error Details",
            "error_details.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, 'w') as file:
                    file.write(self.details)
            except Exception as e:
                error_dialog = QMessageBox(self)
                error_dialog.setWindowTitle("Save Error")
                error_dialog.setText(f"An error occurred while saving the file:\n{e}")
                error_dialog.setIcon(QMessageBox.Critical)
                error_dialog.exec_()

    def report_issue(self):
        webbrowser.open(discord_feedback_channel)
        # Close the dialog after reporting the issue
        self.close()


class UnsavedFilesDialog(QDialog):
    """Info dialog listing every unsaved file across the editors.

    ``entries`` is an iterable of ``(editor_name, file_label, save_callable)``;
    ``save_callable`` may be None when the document has no path to save to.
    Accepted means the caller may proceed (files saved, or user chose to discard).
    """

    def __init__(self, entries, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Unsaved Files")
        self.setWindowIcon(QIcon("../appicon.ico"))
        enable_dark_title_bar(self)
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        header = QLabel("These files have unsaved changes. Save them before switching the addon:")
        header.setWordWrap(True)
        layout.addWidget(header)

        rows_host = QWidget()
        self._rows_layout = QVBoxLayout(rows_host)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(rows_host)
        scroll.setMaximumHeight(260)
        layout.addWidget(scroll)

        self._savers = [self._add_row(*entry) for entry in entries]
        self._rows_layout.addStretch()

        buttons = QHBoxLayout()
        save_all_button = QPushButton("Save All")
        save_all_button.clicked.connect(self.save_all)
        buttons.addWidget(save_all_button)
        buttons.addStretch()
        switch_button = QPushButton("Switch Anyway")
        switch_button.clicked.connect(self.accept)
        buttons.addWidget(switch_button)
        cancel_button = QPushButton("Cancel")
        cancel_button.setDefault(True)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def _add_row(self, editor_name, file_label, save):
        row = QHBoxLayout()
        label = QLabel(f"{editor_name}  —  {os.path.basename(str(file_label))}")
        label.setToolTip(str(file_label))
        row.addWidget(label, 1)
        button = QPushButton("Save")
        button.setEnabled(save is not None)
        if save is None:
            button.setToolTip("This document has no file path yet, save it from its editor.")
        row.addWidget(button)
        self._rows_layout.addLayout(row)

        def do_save():
            if not button.isEnabled():
                return save is not None  # already saved, or nothing to save to
            try:
                save()
            except Exception as e:
                QMessageBox.critical(self, "Save failed", f"{file_label}\n\n{e}")
                return False
            button.setEnabled(False)
            button.setText("Saved")
            return True

        button.clicked.connect(do_save)
        return do_save

    def save_all(self):
        if all([saver() for saver in self._savers]):
            self.accept()


def exception_handler(func):
    """
    A decorator that wraps the passed in function and logs exceptions should one occur.
    It also displays an error dialog with the exception details.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_message = f"An error occurred in `{func.__name__}`: {e}"
            error_details = traceback.format_exc()
            error(error_message)

            # Ensure the dialog is executed in the main thread
            app = QApplication.instance()
            if app is not None:
                ErrorInfo(text=error_message, details=error_details).exec_()
            else:
                print("Error: QApplication instance is not available.")

            # Return None or a default value
            return None

    return wrapper


# Buttons
class Button(QPushButton):
    def __init__(self, size: int = None, icon: str = None, height: int = None, width: int = None, text: str = None):
        super().__init__()
        if text is not None:
            self.set_text(text)
        if size is not None:
            self.set_size(size, size)
        self.set_size(height, width)
        if icon is not None:
            self.set_icon(icon)
        self.setProperty("h5Component", "legacyButton")

    def set_size(self, height: int = None, width: int = None):
        if height is not None:
            self.setMaximumHeight(height)
            self.setMinimumHeight(height)

        if width is not None:
            self.setMinimumWidth(width)
            self.setMaximumWidth(width)

        if height is not None and width is not None:
            icon_size = min(height, width) * 0.6
            self.setIconSize(QSize(icon_size, icon_size))

    def set_icon(self, url):
        self.setIcon(QIcon(url))

    def set_text(self, text):
        self.setText(text)

    def set_icon_delete(self):
        self.set_icon(":/icons/delete_24dp.svg")

    def set_icon_paste(self):
        self.set_icon(":/icons/content_paste_24dp.svg")

    def set_icon_search(self):
        self.set_icon(":/icons/search_24dp.svg")

    def set_icon_add(self):
        self.set_icon(":/icons/add_24dp.svg")

    def set_icon_polyline(self):
        self.set_icon(":/icons/polyline_24dp.png")

    def set_icon_question(self):
        self.set_icon(":/icons/help_24dp.svg")
    def set_icon_bookmark_add(self):
        self.set_icon(":/icons/bookmark_add_24dp.svg")
    def set_icon_bookmark_added(self):
        self.set_icon(":/icons/bookmark_added_24dp.svg")
    def set_icon_folder_open(self):
        self.set_icon(":/icons/folder_open.svg")
    def set_icon_sync(self):
        self.set_icon(":/icons/sync_24dp.svg")
    def set_icon_info(self):
        self.set_icon(":/icons/sync_24dp.svg")

class DeleteButton(Button):
    def __init__(self, instance: QWidget = None):
        super().__init__()
        if instance is None:
            raise ValueError("Instance cannot be None")

        self.instance = instance
        self.clicked.connect(self.delete)
        self.set_icon_delete()

    def delete(self):
        """Delete the associated instance."""
        try:
            self.instance.close()
        except Exception as e:
            print(f"Error deleting instance: {e}")
