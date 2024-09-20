import ast
import re

from qt_styles.qt_smartprops_tree_stylesheet import QT_Stylesheet_smartprop_tree
from smartprop_editor.objects import surfaces_list
from smartprop_editor.properties_classes.ui_filtersurface import Ui_Widget
from completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QCompleter, QColorDialog, QTreeWidgetItem, QMenu
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence
from qt_styles.qt_global_stylesheet import QT_Stylesheet_global
from popup_menu.popup_menu_main import PopupMenu


class PropertySurface(QWidget):
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


        self.ui.surfaces_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.surfaces_tree.customContextMenuRequested.connect(self.open_hierarchy_menu)

        self.dialog = QColorDialog()
        self.dialog.setStyleSheet(QT_Stylesheet_global)


        output = re.sub(r'm_fl|m_n|m_b|m_s|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        # self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        if isinstance(value, list):
            for key in value:
                item = QTreeWidgetItem()
                item.setText(0, key)
                self.ui.surfaces_tree.invisibleRootItem().addChild(item)

        self.ui.add_surface.clicked.connect(self.surface_popup)

        self.on_changed()
    def add_surface(self, name, value):
        item = QTreeWidgetItem()
        item.setText(0, name)
        self.ui.surfaces_tree.invisibleRootItem().addChild(item)
        self.on_changed()


    def open_hierarchy_menu(self, position):
        menu = QMenu()
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.delete_selected_tree_items())
        menu.exec(self.ui.surfaces_tree.viewport().mapToGlobal(position))

    def delete_selected_tree_items(self):
        selected_items = self.ui.surfaces_tree.selectedItems()
        for item in selected_items:
            parent = item.parent()
            if parent is not None:
                parent.removeChild(item)
            else:
                self.ui.surfaces_tree.invisibleRootItem().removeChild(item)
        self.on_changed()


    def surface_popup(self):
        elements_in_popupmenu = []
        existing_items = []
        for i in range(self.ui.surfaces_tree.topLevelItemCount()):
            item = self.ui.surfaces_tree.topLevelItem(i)
            existing_items.append(item.text(0))
        for item in surfaces_list:
            for key, value in item.items():
                if key in existing_items:
                    pass
                else:
                    elements_in_popupmenu.append(item)

        self.popup_menu = PopupMenu(elements_in_popupmenu, add_once=True)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.add_surface(name, value))
        self.popup_menu.show()

    def logic_switch(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.text_line.hide()
            self.ui.value.hide()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.text_line.hide()
            self.ui.value.show()
        else:
            self.text_line.show()
            self.ui.value.hide()

    def on_changed(self):
        # self.logic_switch()
        self.change_value()
        self.edited.emit()
    def change_value(self):
        value = []
        for i in range(self.ui.surfaces_tree.topLevelItemCount()):
            item = self.ui.surfaces_tree.topLevelItem(i)
            value.append(item.text(0))
        self.value = {self.value_class: value}


    def get_variables(self, search_term=None):
        self.variables_scrollArea
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out
