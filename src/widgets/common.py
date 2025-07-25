import ast
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QDoubleSpinBox, QFrame, QSpacerItem, QSizePolicy, \
    QComboBox, QTreeWidget, QTreeWidgetItem, QDialog, QMessageBox, QPushButton, QApplication, QLabel, QLineEdit, \
    QCheckBox, QVBoxLayout, QToolBox, QToolButton
from PySide6.QtGui import QStandardItemModel
from PySide6.QtGui import QIcon, QColor, QFont
import sys, webbrowser
from src.styles.common import *
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QTextEdit, QDoubleSpinBox, QFrame, QSpacerItem, \
    QSizePolicy, QComboBox, QTreeWidget, QTreeWidgetItem, QDialog, QMessageBox, QPushButton, QApplication, QLabel, \
    QLineEdit, QCheckBox, QVBoxLayout, QToolBox, QToolButton, QGroupBox, QButtonGroup
from PySide6.QtGui import QStandardItemModel
from PySide6.QtGui import QIcon, QColor, QFont
import sys, webbrowser
from src.styles.common import *
from PySide6.QtWidgets import QMessageBox, QFileDialog
from PySide6.QtGui import QIcon
import webbrowser
from src.common import discord_feedback_channel
from logging import error
import traceback, ctypes
from src.common import enable_dark_title_bar
import winsound


# Dialogs
class ErrorInfo(QDialog):
    def __init__(self, text="Error", details=""):
        super().__init__()
        self.setWindowTitle("Error")
        self.setWindowIcon(QIcon("../appicon.ico"))
        enable_dark_title_bar(self)
        self.setMinimumSize(600, 400)
        self.setModal(True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.details = details
        winsound.MessageBeep(winsound.MB_ICONHAND)
        # Main layout
        main_layout = QVBoxLayout(self)

        # Error message label
        self.message_label = QLabel(text)
        self.message_label.setWordWrap(True)
        main_layout.addWidget(self.message_label)

        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlainText(self.details)
        self.details_text.setStyleSheet("background-color: #1C1C1C; border-color: #974533")
        main_layout.addWidget(self.details_text)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        # Save Details button
        self.save_button = QPushButton("Save Details")
        self.save_button.clicked.connect(self.save_details)
        buttons_layout.addWidget(self.save_button)

        # Report button
        self.report_button = QPushButton("Report")
        self.report_button.clicked.connect(self.report_issue)
        buttons_layout.addWidget(self.report_button)

        # Spacer to push Close button to the right
        buttons_layout.addStretch()

        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_button)

        main_layout.addLayout(buttons_layout)

    def save_details(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Error Details",
            "error_details.txt",
            "Text Files (*.txt);;All Files (*)",
            options=options
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


#================================================================<  Buttons  >==============================================================
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
        self.setStyleSheet(qt_stylesheet_button)

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
        self.set_icon(":/icons/delete_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")

    def set_icon_paste(self):
        self.set_icon(":/icons/content_paste_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")

    def set_icon_search(self):
        self.set_icon(":/icons/search_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")

    def set_icon_add(self):
        self.set_icon(":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")

    def set_icon_polyline(self):
        self.set_icon(":/icons/polyline_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png")

    def set_icon_question(self):
        self.set_icon(":/icons/help_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")
    def set_icon_bookmark_add(self):
        self.set_icon(":/icons/bookmark_add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")
    def set_icon_bookmark_added(self):
        self.set_icon(":/icons/bookmark_added_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")
    def set_icon_folder_open(self):
        self.set_icon(":/icons/folder_open.svg")
    def set_icon_sync(self):
        self.set_icon(":/icons/sync_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")
    def set_icon_info(self):
        self.set_icon(":/icons/sync_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")

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


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QSpacerItem, QSizePolicy
    )
    from PySide6.QtGui import QIcon
    from src.widgets.common import Button, DeleteButton, CheckBox
    from src.styles.common import apply_stylesheets
    from src.common import enable_dark_title_bar


    class ButtonCheckboxShowcase(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Button and CheckBox Showcase")
            self.setWindowIcon(QIcon("../appicon.ico"))
            enable_dark_title_bar(self)
            self.setMinimumSize(600, 400)

            main_layout = QVBoxLayout(self)

            # --- Buttons Showcase ---
            button_group = QGroupBox("Buttons")
            button_layout = QHBoxLayout()

            # Standard Button with text
            btn_text = Button(text="Standard")
            button_layout.addWidget(btn_text)

            # Button with icon (add)
            btn_add = Button(text="Add", icon=":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")
            button_layout.addWidget(btn_add)

            # Button with icon (search)
            btn_search = Button(icon=":/icons/search_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", text="Search")
            button_layout.addWidget(btn_search)

            # Button with custom size
            btn_large = Button(text="Large", size=48)
            button_layout.addWidget(btn_large)

            # Button with only icon (delete)
            btn_icon_only = Button(icon=":/icons/delete_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", size=32)
            button_layout.addWidget(btn_icon_only)

            # DeleteButton (requires a QWidget instance, so we use self)
            btn_delete = DeleteButton(instance=self)
            btn_delete.setText("Delete (closes window)")
            button_layout.addWidget(btn_delete)

            button_group.setLayout(button_layout)
            main_layout.addWidget(button_group)

            # --- CheckBox Showcase ---
            checkbox_group = QGroupBox("CheckBoxes")
            checkbox_layout = QHBoxLayout()

            # Unchecked
            cb_unchecked = CheckBox(text="Unchecked", checked=False)
            checkbox_layout.addWidget(cb_unchecked)

            # Checked
            cb_checked = CheckBox(text="Checked", checked=True)
            checkbox_layout.addWidget(cb_checked)

            # Custom label
            cb_custom = CheckBox(text="Custom Label")
            checkbox_layout.addWidget(cb_custom)

            checkbox_group.setLayout(checkbox_layout)
            main_layout.addWidget(checkbox_group)

            # Spacer to push everything to the top
            main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

            # Apply styles to all widgets
            apply_stylesheets(self)
    app = QApplication(sys.argv)
    showcase = ButtonCheckboxShowcase()
    showcase.show()
    sys.exit(app.exec())