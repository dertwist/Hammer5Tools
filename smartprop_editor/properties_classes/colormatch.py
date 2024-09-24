import ast
import re

from qt_styles.qt_smartprops_tree_stylesheet import QT_Stylesheet_smartprop_tree
from smartprop_editor.objects import surfaces_list
from smartprop_editor.properties_classes.ui_colormatch import Ui_Widget
from completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QCompleter, QColorDialog, QTreeWidgetItem, QMenu, QToolButton
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence
from qt_styles.qt_global_stylesheet import QT_Stylesheet_global

from smartprop_editor.properties_classes.color import PropertyColor


class PropertyColorMatch(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value

        self.color = [255, 255, 255]
        # self.ui.logic_switch.setCurrentIndex(0)

        self.variables_scrollArea = variables_scrollArea

        self.dialog = QColorDialog()
        self.dialog.setStyleSheet(QT_Stylesheet_global)


        output = re.sub(r'm_fl|m_n|m_b|m_s|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        # self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        if isinstance(value, list):
            print(value)

        self.ui.add_surface.clicked.connect(self.add_surface)

        self.on_changed()
    def add_surface(self):

        delete_button = QToolButton()
        delete_button.clicked.connect(self.delete_action)
        ColorInstance = PropertyColor('m_Color', [244,24,21], self.variables_scrollArea)
        ColorInstance.ui.layout.addWidget(delete_button)
        self.ui.layout_color.insertWidget(0,ColorInstance)

        self.on_changed()

    def delete_action(self, widget):
        print(widget)

    def on_changed(self):
        # self.logic_switch()
        self.change_value()
        self.edited.emit()
    def change_value(self):
        value = []
        for i in range(self.ui.layout_color.count()):
            item = self.ui.layout_color.itemAt(i)
            value.append({item.value_class: {item.value}})
        self.value = {self.value_class: value}


    def get_variables(self, search_term=None):
        self.variables_scrollArea
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out
