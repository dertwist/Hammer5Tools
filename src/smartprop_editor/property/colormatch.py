import re

from src.smartprop_editor.property.ui_colormatch import Ui_Widget
from PySide6.QtWidgets import QWidget, QColorDialog, QToolButton
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from src.qt_styles.qt_global_stylesheet import QT_Stylesheet_global

from src.smartprop_editor.property.color import PropertyColor


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

        self.variables_scrollArea = variables_scrollArea

        self.dialog = QColorDialog()
        self.dialog.setStyleSheet(QT_Stylesheet_global)


        output = re.sub(r'm_fl|m_n|m_b|m_s|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        # self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    for key, value in item.items():
                        self.add_color_widget(key, value)

        self.ui.add_color_widget.clicked.connect(lambda: self.add_color_widget(key='m_Color', value=[255,255,255]))

        self.on_changed()

    def add_color_widget(self, key, value):
        ColorInstance = PropertyColor(key, value, self.variables_scrollArea)
        delete_button = QToolButton()
        delete_button.setStyleSheet("""QToolButton {
	icon: url(:/icons/delete_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg);
    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 0px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #E3E3E3;
    background-color: #1C1C1C;
}
QToolButton:hover {
    background-color: #414956;
    color: white;
}
QToolButton:pressed {
    background-color: red;
    background-color: #1C1C1C;
    margin: 1 px;
    margin-left: 2px;
    margin-right: 2px;
    font: 580 9pt "Segoe UI";

}""")
        delete_icon_path = ":/icons/delete_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"
        delete_icon = QIcon(delete_icon_path)
        delete_button.setIcon(delete_icon)
        delete_button.clicked.connect(lambda: self.delete_action(ColorInstance))
        ColorInstance.ui.layout.addWidget(delete_button)
        ColorInstance.edited.connect(self.on_changed)
        self.ui.layout_color.addWidget(ColorInstance)
        self.on_changed()

    def delete_action(self, widget):
        widget.deleteLater()

    def on_changed(self):
        # self.logic_switch()
        self.change_value()
        self.edited.emit()
    def change_value(self):
        value = []
        for i in range(self.ui.layout_color.count()):
            item = self.ui.layout_color.itemAt(i).widget()
            if isinstance(item, PropertyColor):
                value.append(item.value)
        self.value = {self.value_class: value}


    def get_variables(self, search_term=None):
        self.variables_scrollArea
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out
