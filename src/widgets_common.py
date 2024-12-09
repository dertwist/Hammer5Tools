import ast

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QDoubleSpinBox, QFrame, QSpacerItem, QSizePolicy, QComboBox, QTreeWidget, QTreeWidgetItem, QDialog, QMessageBox, QPushButton, QApplication, QLabel, QLineEdit, QCheckBox, QVBoxLayout, QToolBox, QToolButton
from PySide6.QtGui import QStandardItemModel
from PySide6.QtGui import QIcon, QColor, QFont
import sys, webbrowser
from qt_styles.common import *

#================================================================<  Buttons  >==============================================================

class DeleteButton(QToolButton):
    def __init__(self, instance: QWidget = None):
        super().__init__()
        if instance is None:
            raise ValueError

        self.instance = instance
        self.clicked.connect(self.delete)
        self.setIcon(QIcon(":/icons/delete_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        # self.setMinimumHeight(24)
        # self.setMinimumWidth(24)
        # self.setMaximumWidth(24)
        # self.setMaximumHeight(24)
    def delete(self):
        """Deleting Instance"""
        # self.instance.close()
        self.instance.closeEvent(self.event)
        # self.instance.deleteLater()
class Button(QPushButton):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(qt_stylesheet_button)
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