from src.editors.smartprop_editor.ui_properties_group_frame import Ui_Form


from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal
from src.property.methods import PropertyMethods


class PropertiesGroupFrame(QWidget):
    add_signal = Signal()
    paste_signal = Signal()
    def __init__(self, widget_list=None, name=None):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.property_class.setAcceptDrops(False)
        self.name = name


        self.layout = self.ui.layout
        self.ui.add_button.clicked.connect(self.add_action)

        self.ui.paste_button.clicked.connect(self.paste_action)

        self.ui.property_class.setText(self.name)
        self.widget_list = widget_list

        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

        # self.init_ui()
    def add_action(self):
        self.add_signal.emit()
    def paste_action(self):
        self.paste_signal.emit()
    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666,0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    mousePressEvent = PropertyMethods.mousePressEvent
    mouseMoveEvent = PropertyMethods.mouseMoveEvent
    dragEnterEvent = PropertyMethods.dragEnterEvent
    dropEvent = PropertyMethods.dropEvent
