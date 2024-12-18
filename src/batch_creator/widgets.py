from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsWidget, QGraphicsPathItem, QTreeWidget, QSpacerItem, QSizePolicy
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPathItem, QFrame, QLineEdit, QPlainTextEdit,QToolButton, QToolTip
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QTextOption
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPath, QPen, QColor, QGuiApplication, QPainter
from PySide6.QtCore import QEasingCurve, Qt, Signal, QLineF, QRectF
from src.popup_menu.popup_menu_main import PopupMenu
from src.preferences import debug, get_addon_dir
from src.common import convert_snake_case
from src.batch_creator.context_menu import ReplacementsContextMenu
from src.batch_creator.highlighter import CustomHighlighter
from src.qt_styles.common import *
try:
    from src.soundevent_editor.property.ui_curve import Ui_CurveWidget
except:
    pass
from src.widgets import FloatWidget, LegacyWidget, BoolWidget, DeleteButton, Button, ComboboxDynamicItems, Spacer

import re, os
class ExplorerItem(QWidget):
    edited = Signal()
    def __init__(self, parent=None, label_text: str = None, value: dict = None):
        """Base property class. There is only a label widget and a frame. New widget can be replaced or added"""
        super().__init__(parent)

        # Value variable
        self.value = value
        self.value_class = label_text

        # Init
        self.set_widget_size()
        self.init_root_layout()
        self.init_label(label_text)

        self.setStyleSheet(""".QFrame {
        font: 580 10pt "Segoe UI";
        border: 2px solid black;
        border-radius: 0px;
        border-left: 0px;
        border-right: 0px;
        border-top: 0px;
        border-color: rgba(50, 50, 50, 255);
        color: #E3E3E3;
        background-color: #1C1C1C;
        }
        
        .QFrame::hover {
        }
        .QFrame::selected {
            background-color: #414956;
        }""")

        self.open_button = Button()
        self.root_layout.addWidget(self.open_button)

    def init_root_layout(self):
        """Adding a root layout in which should be placed all widgets that would be in this class and from encapsulation. Not recommended to overwrite this function"""
        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)
    def init_label(self, label_text):
        """Adding received text to the label widget"""
        if label_text is None:
            label_text = "Label"
        label_instance = QLabel()
        label_instance.setText(convert_snake_case(label_text))
        label_instance.setStyleSheet(f"""
        color: {self.init_label_color()}""")
        self.root_layout.addWidget(label_instance)
    def init_label_color(self):
        return "#C7C7BB"
    def add_property_widget(self, widget):
        """Adding property widget to the root"""
        self.root_layout.addWidget(widget)
    def set_widget_size(self):
        """Set maximum height"""
        self.setMaximumHeight(44)
        self.setMinimumHeight(44)