import ast

from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QDoubleSpinBox, QFrame, QSpacerItem, QSizePolicy, QComboBox, QTreeWidget, QTreeWidgetItem, QDialog, QMessageBox, QPushButton, QApplication, QLabel, QLineEdit, QCheckBox, QVBoxLayout, QToolBox, QToolButton
from PySide6.QtGui import QStandardItemModel
from PySide6.QtGui import QIcon, QColor, QFont
import sys, webbrowser
from src.qt_styles.common import *

#================================================================<  Buttons  >==============================================================
class Button(QPushButton):
    def __init__(self):
        super().__init__()
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