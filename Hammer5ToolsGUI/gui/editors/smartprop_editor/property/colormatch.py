import re

from gui.editors.smartprop_editor.property.ui_colormatch import Ui_Widget
from gui.editors.smartprop_editor.property import compact
from PySide6.QtWidgets import QWidget, QColorDialog, QToolButton
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon

from gui.editors.smartprop_editor.property.color import PropertyColor


class PropertyColorMatch(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea, element_id_generator):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.element_id_generator = element_id_generator

        self.color = [255, 255, 255]

        self.variables_scrollArea = variables_scrollArea

        self.dialog = QColorDialog()


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

        # Compact Source2-style header row; the colour list below it may grow.
        compact.apply_plain_row(self, self.ui.frame, self.ui.property_class,
                                label_color="#A375FF", clamp_height=False)

    def add_color_widget(self, key, value):
        ColorInstance = PropertyColor(
            key,
            value,
            self.variables_scrollArea,
            element_id_generator=self.element_id_generator,
            parent=self,
        )
        delete_button = QToolButton()
        delete_button.setProperty("h5Component", "smartpropDeleteIconButtonWide")
        delete_icon_path = ":/icons/delete_24dp.svg"
        delete_icon = QIcon(delete_icon_path)
        delete_button.setIcon(delete_icon)
        delete_button.clicked.connect(lambda: self.delete_action(ColorInstance))
        # Right after the swatch, not appended: the row ends in an expanding
        # spacer, so appending put delete against the far right of the panel.
        ColorInstance.ui.layout.insertWidget(
            ColorInstance.ui.layout.indexOf(ColorInstance.ui.value) + 1, delete_button
        )
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