from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from soudevent_editor.properties.ui_volume_property import Ui_LegacyPropertyWidet
from soudevent_editor.properties.property_actions import PropertyActions

class VolumeProperty(QWidget):
    def __init__(self, name, value, status_bar, widget_list):
        super().__init__()
        self.ui = Ui_LegacyPropertyWidet()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.horizontalSlider.setAcceptDrops(False)
        self.ui.doubleSpinBox.setAcceptDrops(False)
        self.widget_list = widget_list
        self.name = name
        self.value = float(value)
        self.status_bar = status_bar
        self.init_ui()

    def init_ui(self):
        self.ui.horizontalSlider.setValue(self.value * 10)
        self.ui.doubleSpinBox.setValue(self.value)
        self.ui.horizontalSlider.valueChanged.connect(self.update_horizontalSlider)
        self.ui.doubleSpinBox.valueChanged.connect(self.update_doubleSpinBox)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def update_horizontalSlider(self):
        self.value = self.ui.horizontalSlider.value() / 10
        print(self.value)
        self.ui.doubleSpinBox.setValue(self.value)

    def update_doubleSpinBox(self):
        self.value = self.ui.doubleSpinBox.value()
        self.ui.horizontalSlider.setValue(self.value * 10)

    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent
    def show_context_menu(self):
        PropertyActions.show_context_menu(self, event=self.event, property_class=self)
