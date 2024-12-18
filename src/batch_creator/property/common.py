from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsWidget, QGraphicsPathItem, QTreeWidget, QSpacerItem, QSizePolicy
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPathItem, QFrame, QLineEdit, QPlainTextEdit,QToolButton, QToolTip
from PySide6.QtGui import QPainterPath, QPen, QColor, QGuiApplication, QPainter
from PySide6.QtCore import QEasingCurve, Qt, Signal, QLineF, QRectF
from src.popup_menu.popup_menu_main import PopupMenu
from src.preferences import debug, get_addon_dir
from src.common import convert_snake_case
try:
    from src.soundevent_editor.property.ui_curve import Ui_CurveWidget
except:
    pass
from src.widgets import FloatWidget, LegacyWidget, BoolWidget, DeleteButton, Button, ComboboxDynamicItems, Spacer

import re, os

#===============================================================<  Properties >============================================================

class PropertyBase(QWidget):
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
        # self.on_property_update()

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

class PropertyReplacement(PropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: str = None, tree: QTreeWidget = None, objects: list = None):
        """
        Combox property

        value : str
        """
        super().__init__(parent, label_text, value)

        self.tree: QTreeWidget = tree
        self.value_class = label_text
        self.objects = objects
        # Init combobox
        self.combobox = QLineEdit()
        self.combobox.setMinimumWidth(256)
        self.combobox.textChanged.connect(self.on_property_update)
        self.layout().addWidget(self.combobox)
        self.set_value(value)
        # if value == "None":
        #     pass
        # else:
        #     self.combobox.setCurrentText(str(value))


        # Init Search button
        self.search_button = Button()
        self.search_button.set_icon_search()
        self.search_button.setMaximumWidth(32)
        self.search_button.clicked.connect(self.call_search_popup_menu)
        self.layout().addWidget(self.search_button)
        self.on_property_update()

        # Init spacer
        spacer = Spacer()
        self.layout().addWidget(spacer)

        self.setContentsMargins(0,0,0,0)
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)

    def init_combobox(self):
        pass
    def set_value(self, value: str):
        self.combobox.setText(str(value))

    def on_property_update(self):
        """Send signal that user changed the property"""
        value = self.combobox.text()
        self.value_update(value)
        self.edited.emit()

    def value_update(self, value):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        self.value = {self.value_class: value}
    def init_label_color(self):
        return "#F4A9F6"

    def call_search_popup_menu(self):
        elements = []
        for item in self.objects:
            __element = {item:item}
            elements.append(__element)
        self.popup_menu = PopupMenu(elements, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
        self.popup_menu.show()
