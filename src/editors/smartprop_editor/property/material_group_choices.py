import re

from src.editors.smartprop_editor.property.ui_material_replacements import Ui_Widget
from src.editors.smartprop_editor.property.string import PropertyString
from src.editors.smartprop_editor.property.float import PropertyFloat
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QSizePolicy, QSpacerItem
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon


class MaterialGroupChoiceRow(QWidget):
    edited = Signal()

    def __init__(self, name="", weight=1.0, variables_scrollArea=None, element_id_generator=None, parent=None):
        super().__init__(parent)
        self.variables_scrollArea = variables_scrollArea
        self.element_id_generator = element_id_generator

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        self.name_widget = PropertyString(
            element_id_generator=element_id_generator,
            value_class='m_MaterialGroupName',
            value=name,
            variables_scrollArea=variables_scrollArea,
            expression_bool=False,
            placeholder="Material group name",
            filter_types=['String'],
            parent=self,
        )
        self.name_widget.ui.property_class.setText("Group Name")
        self.name_widget.edited.connect(self._on_changed)

        self.weight_widget = PropertyFloat(
            element_id_generator=element_id_generator,
            value_class='m_flWeight',
            value=weight,
            slider_range=[0, 1],
            variables_scrollArea=variables_scrollArea,
            parent=self,
        )
        self.weight_widget.ui.property_class.setText("Weight")
        self.weight_widget.edited.connect(self._on_changed)

        layout.addWidget(self.name_widget)
        layout.addWidget(self.weight_widget)

        delete_btn = QToolButton()
        delete_btn.setStyleSheet("""QToolButton {
    icon: url(:/icons/delete_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg);
    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 0px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 4px;
    color: #E3E3E3;
    background-color: #1C1C1C;
}
QToolButton:hover { background-color: #414956; color: white; }
QToolButton:pressed { background-color: #1C1C1C; }""")
        delete_btn.setIcon(QIcon(":/icons/delete_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        layout.addWidget(delete_btn)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        def _do_delete():
            self.edited.emit()
            self.deleteLater()
        delete_btn.clicked.connect(_do_delete)

    def _on_changed(self):
        self.edited.emit()

    @property
    def value(self):
        name_val = None
        weight_val = 1.0
        if hasattr(self.name_widget, 'value') and isinstance(self.name_widget.value, dict):
            name_val = self.name_widget.value.get('m_MaterialGroupName')
        elif self.name_widget.value is not None:
            name_val = self.name_widget.value
            
        if hasattr(self.weight_widget, 'value') and isinstance(self.weight_widget.value, dict):
            w = self.weight_widget.value.get('m_flWeight')
            if w is not None:
                weight_val = w
        elif self.weight_widget.value is not None:
            weight_val = self.weight_widget.value
            
        return {
            "m_MaterialGroupName": name_val if name_val is not None else "",
            "m_flWeight": weight_val,
        }


class PropertyMaterialGroupChoices(QWidget):
    edited = Signal()

    def __init__(self, value_class, value, variables_scrollArea, element_id_generator):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.element_id_generator = element_id_generator
        self.variables_scrollArea = variables_scrollArea

        output = "Material Group Choices"
        self.ui.property_class.setText(output)
        self.ui.add_replacement_widget.setText("Add Choice")

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    name = item.get("m_MaterialGroupName", "")
                    weight = item.get("m_flWeight", 1.0)
                    self._add_row(name, weight)

        self.ui.add_replacement_widget.clicked.connect(lambda: self._add_row("", 1.0))

        self._change_value()

    def _add_row(self, name="", weight=1.0):
        row = MaterialGroupChoiceRow(
            name=name,
            weight=weight,
            variables_scrollArea=self.variables_scrollArea,
            element_id_generator=self.element_id_generator
        )
        row.edited.connect(self._on_changed)
        self.ui.layout_replacements.addWidget(row)
        self._on_changed()

    def _on_changed(self):
        self._change_value()
        self.edited.emit()

    def _change_value(self):
        items = []
        for i in range(self.ui.layout_replacements.count()):
            widget = self.ui.layout_replacements.itemAt(i).widget()
            if isinstance(widget, MaterialGroupChoiceRow):
                items.append(widget.value)
        self.value = {self.value_class: items}
