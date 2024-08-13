from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from soudevent_editor.properties.ui_origin_property import Ui_PropertyWidet
from soudevent_editor.properties.property_actions import PropertyActions
import ast, re
from PySide6.QtGui import QGuiApplication

class OriginProperty(QWidget):
    def __init__(self, name, display_name, value, widget_list):
        super().__init__()
        self.ui = Ui_PropertyWidet()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.x_axis.setAcceptDrops(False)
        self.ui.y_axis.setAcceptDrops(False)
        self.ui.z_axis.setAcceptDrops(False)
        self.widget_list = widget_list
        self.name = name
        self.display_name = display_name

        if '[' in value and ']' in value:
            self.value = ast.literal_eval(value)
            for item in self.value:
                print(item)
        else:
            self.value = value

        self.init_ui()


    def init_ui(self):
        self.ui.label.setText(self.display_name)
        self.ui.x_axis.setValue(self.value[0])
        self.ui.y_axis.setValue(self.value[1])
        self.ui.z_axis.setValue(self.value[2])

        self.ui.x_axis.valueChanged.connect(self.update_value)
        self.ui.y_axis.valueChanged.connect(self.update_value)
        self.ui.z_axis.valueChanged.connect(self.update_value)
        # self.ui.lineEdit.setText(str(self.value))
        # self.ui.lineEdit.textChanged.connect(self.update_value_from_lineedit)

        self.ui.paste_button.clicked.connect(self.paste_from_clipboard)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def paste_from_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard_text = clipboard.text()
        if clipboard_text.endswith('}'):
            origin_list = re.search(r'origin = "(.*?)"', clipboard_text).group(1)
            origin_list = origin_list.split()
            self.ui.x_axis.setValue(float(origin_list[0]))
            self.ui.y_axis.setValue(float(origin_list[1]))
            self.ui.z_axis.setValue(float(origin_list[2]))



    def update_value(self):
        list_out = self.ui.x_axis.value(),self.ui.y_axis.value(), self.ui.z_axis.value()
        print(list_out)
        self.value = [self.ui.x_axis.value(),self.ui.y_axis.value(), self.ui.z_axis.value()]
        print(self.value)

    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent
    def show_context_menu(self):
        PropertyActions.show_context_menu(self, event=self.event, property_class=self)
