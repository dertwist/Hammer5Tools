from PySide6.QtWidgets import QWidget, QComboBox, QCompleter, QDoubleSpinBox, QHBoxLayout, QPushButton, QListWidgetItem, QMenu, QApplication, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QStandardItem, QStandardItemModel, QCursor,QAction
from soudevent_editor.properties.ui_files_property import Ui_PropertyWidet
from soudevent_editor.properties.property_actions import PropertyActions
import ast
from PySide6.QtCore import Qt, Signal


class FilesProperty(QWidget):
    def __init__(self, name, display_name, value, widget_list):
        super().__init__()
        self.ui = Ui_PropertyWidet()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.widget_list = []
        self.display_name = display_name
        self.name = name

        try:
            self.value = ast.literal_eval(value)
        except:
            self.value = [value]

        self.init_ui()

    # Inside the CurveProperty class
    def init_ui(self):
        self.ui.label.setText(self.display_name)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        for item in self.value:
            item_widget = QListWidgetItem(item)
            item_widget.setFlags(item_widget.flags() | Qt.ItemIsEditable)  # Allow item editing
            self.ui.listWidget.addItem(item_widget)
            self.ui.listWidget.itemChanged.connect(self.on_update_value)

        self.calculate_height()

    def on_update_value(self):
        listout = []
        for i in range(self.ui.listWidget.count()):
            listout.append(self.ui.listWidget.item(i).text())
        self.value = listout


    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent

    def calculate_height(self):
        count = self.ui.listWidget.count()
        self.setMinimumSize(QSize(0, ((count * 34) + 100)))
        self.setMaximumSize(QSize(16777215, ((count * 34) + 100)))

    def delete_item_from_list(self):
        item_widget = self.ui.listWidget.currentItem()
        if item_widget:
            row = self.ui.listWidget.row(item_widget)
            self.ui.listWidget.takeItem(row)
            del self.widget_list[row]  # Remove the corresponding widget from the list
            item_widget = None
            self.on_update_value()
        self.calculate_height()
    def add_item_to_list(self):
        item_widget = QListWidgetItem('vsnd')
        item_widget.setFlags(item_widget.flags() | Qt.ItemIsEditable)  # Allow item editing
        self.ui.listWidget.addItem(item_widget)
        self.ui.listWidget.itemChanged.connect(self.on_update_value)
        self.calculate_height()
    def show_context_menu(self, event):

        if self.ui.listWidget is QApplication.focusWidget():
            context_menu = QMenu(self)
            delete_action = context_menu.addAction("Delete")
            delete_action.triggered.connect(self.delete_item_from_list)
            delete_action = context_menu.addAction("Add")
            delete_action.triggered.connect(self.add_item_to_list)
            action = context_menu.exec_(QCursor().pos())

        else:
            PropertyActions.show_context_menu(self, event=self.event, property_class=self)