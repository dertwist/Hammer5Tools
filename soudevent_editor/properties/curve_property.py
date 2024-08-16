from PySide6.QtWidgets import QWidget, QComboBox, QCompleter, QDoubleSpinBox, QHBoxLayout, QPushButton, QListWidgetItem, QMenu, QApplication, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QStandardItem, QStandardItemModel, QCursor,QAction
from soudevent_editor.properties.ui_curve_property import Ui_PropertyWidet
from soudevent_editor.properties.property_actions import PropertyActions
import ast
from PySide6.QtCore import Qt, Signal


class CustomWidget(QWidget):
    valueChanged = Signal(list)
    outputlist = []
    def __init__(self, custom_list, first_value_d, second_value_d, parent=None):
        super(CustomWidget, self).__init__(parent)
        self.lay = QHBoxLayout(self)
        self.lay.setAlignment(Qt.AlignLeft)

        for i in range(6):
            double_spin_box = QDoubleSpinBox()
            double_spin_box.setPrefix(f"{first_value_d}  " if i == 0 else f"{second_value_d} " if i == 1 else "")
            double_spin_box.setMaximum(99999)
            double_spin_box.setMinimum(-99999)
            double_spin_box.setValue(custom_list[i])
            self.lay.addWidget(double_spin_box, alignment=Qt.AlignRight)
            double_spin_box.valueChanged.connect(lambda value, index=i: self.onValueChanged())
        self.onValueChanged()

        self.lay.setContentsMargins(0, 0, 0, 0)

    def onValueChanged(self):
        outputlist = []
        for item in range(6):
            outputlist.append(self.lay.itemAt(item).widget().value())

        self.valueChanged.emit(outputlist)
        self.outputlist = outputlist


class CurveProperty(QWidget):
    def __init__(self, name, display_name, value, widget_list, first_value_d, second_value_d):
        super().__init__()
        self.ui = Ui_PropertyWidet()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.widget_list = []
        self.second_value_d = second_value_d
        self.first_value_d = first_value_d
        self.display_name = display_name
        self.name = name

        self.value = ast.literal_eval(value)
        print(self.value)
        for item in self.value:
            print(item)

        self.init_ui()

    # Inside the CurveProperty class
    def init_ui(self):
        self.ui.label.setText(self.display_name)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        for item in self.value:
            if isinstance(item, list):
                item_widget = QListWidgetItem()
                self.ui.listWidget.addItem(item_widget)
                custom_widget = CustomWidget(custom_list=item, first_value_d=self.first_value_d, second_value_d=self.second_value_d)
                self.ui.listWidget.setItemWidget(item_widget, custom_widget)
                self.widget_list.append(custom_widget)
                custom_widget.valueChanged.connect(lambda value: self.on_update_value)

        self.calculate_height()

    def on_update_value(self):
        listout = []
        for i in range(len(self.widget_list)):
            listout.append(self.widget_list[i].outputlist)
        self.value = listout


    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent

    def calculate_height(self):
        count = len(self.widget_list)
        self.setMinimumSize(QSize(0, ((count * 34) + 65)))
        self.setMaximumSize(QSize(16777215, ((count * 34) + 65)))

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
        item_widget = QListWidgetItem()
        self.ui.listWidget.addItem(item_widget)
        custom_widget = CustomWidget(custom_list=[0,0,0,0,0,0], first_value_d=self.first_value_d, second_value_d=self.second_value_d)
        self.ui.listWidget.setItemWidget(item_widget, custom_widget)
        self.widget_list.append(custom_widget)
        custom_widget.valueChanged.connect(lambda value: self.on_update_value)
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