import re

from src.editors.smartprop_editor.property.ui_material_replacements import Ui_Widget
from src.editors.smartprop_editor.property.string import PropertyString
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QSizePolicy, QSpacerItem
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon


class MaterialReplacementRow(QWidget):
    """Single row widget for one material replacement pair (original -> replacement).
    Uses PropertyString for each field to support literal strings, variable refs, and expressions.
    """
    edited = Signal()

    def __init__(self, original="", replacement="", variables_scrollArea=None, element_id_generator=None, parent=None):
        super().__init__(parent)
        self.variables_scrollArea = variables_scrollArea
        self.element_id_generator = element_id_generator

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        filter_types = ['Material', 'String']
        placeholder = "Material path or variable"

        self.original_widget = PropertyString(
            element_id_generator=element_id_generator,
            value_class='m_OriginalMaterial',
            value=original,
            variables_scrollArea=variables_scrollArea,
            expression_bool=False,
            placeholder=placeholder,
            filter_types=filter_types,
            parent=self,
        )
        self.original_widget.ui.property_class.setText("Origin")
        self.original_widget.edited.connect(self._on_changed)

        self.replacement_widget = PropertyString(
            element_id_generator=element_id_generator,
            value_class='m_ReplacementMaterial',
            value=replacement,
            variables_scrollArea=variables_scrollArea,
            expression_bool=False,
            placeholder=placeholder,
            filter_types=filter_types,
            parent=self,
        )
        self.replacement_widget.ui.property_class.setText("Target")
        self.replacement_widget.edited.connect(self._on_changed)

        layout.addWidget(self.original_widget)
        layout.addWidget(QLabel("→"))
        layout.addWidget(self.replacement_widget)

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
        orig_val = None
        repl_val = None
        if hasattr(self.original_widget, 'value') and isinstance(self.original_widget.value, dict):
            orig_val = self.original_widget.value.get('m_OriginalMaterial')
        elif self.original_widget.value is not None:
            orig_val = self.original_widget.value
        if hasattr(self.replacement_widget, 'value') and isinstance(self.replacement_widget.value, dict):
            repl_val = self.replacement_widget.value.get('m_ReplacementMaterial')
        elif self.replacement_widget.value is not None:
            repl_val = self.replacement_widget.value
        return {
            "m_OriginalMaterial": orig_val if orig_val is not None else "",
            "m_ReplacementMaterial": repl_val if repl_val is not None else "",
        }


class PropertyMaterialReplacements(QWidget):
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

        output = re.sub(r'm_fl|m_n|m_b|m_s|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)
        self.ui.property_class.setText(output)

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    orig = item.get("m_OriginalMaterial", "")
                    repl = item.get("m_ReplacementMaterial", "")
                    self._add_row(orig, repl)

        self.ui.add_replacement_widget.clicked.connect(lambda: self._add_row("", ""))

        self._change_value()

    def _add_row(self, original="", replacement=""):
        row = MaterialReplacementRow(
            original=original,
            replacement=replacement,
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
            if isinstance(widget, MaterialReplacementRow):
                items.append(widget.value)
        self.value = {self.value_class: items}
