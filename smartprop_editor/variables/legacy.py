from smartprop_editor.variables.ui_legacy import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QCursor, QDrag, QAction
import ast


class Var_class_legacy(QWidget):
    def __init__(self, var_value):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.var_value = var_value
        self.ui.value.setText(var_value)