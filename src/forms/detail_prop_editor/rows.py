"""
Property rows for the Detail Prop Editor.

These reuse the SmartProp editor's compact row template
(src/editors/smartprop_editor/property/compact.py) so the two editors look and
feel identical: a fixed 150px colour-coded label column, ~29px rows, zebra
striping, flat controls and inline drag-sliders.

The SmartProp property widgets themselves (PropertyFloat, PropertyBool, …) are
not reused directly because every one of them is built around the vsmart
variable/expression system — they require a variables scroll area and an element
id generator, and they expose a Default/Variable/Expression mode switch. vdata
detail props have no variables or expressions, so the rows here use the same
template with the switch left off (compact.apply_row_no_switch).
"""

import re

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QPushButton, QSizePolicy,
)

from src.widgets.widgets import FloatWidget
from src.editors.smartprop_editor.property import compact

# Label colours, matching the SmartProp property editor's type coding.
COLOR_FLOAT = "rgb(181, 255, 239)"
COLOR_STRING = "rgb(255, 209, 153)"
COLOR_BOOL = "rgb(255, 189, 190)"

_STRIP_PREFIX = re.compile(r'm_fl|m_n|m_b|m_s|m_v|m_f|m_')
_CAMEL_SPLIT = re.compile(r'([a-z0-9])([A-Z])')

def style_slider(float_widget):
    """
    Slider styling, identical to the SmartProp property editor's — with one
    scoped fix: the app-wide stylesheet's blanket `QWidget { background-color:
    #151515; }` rule (src/styles/qt_global_stylesheet.py) paints straight
    through FloatWidget and its Slider, since neither sets its own background.
    In a normal window that's invisible against the same-coloured backdrop, but
    compact.style_slider() stretches the slider across the row, so that flat
    #151515 shows up as a solid block sitting on top of the row's zebra stripe.
    Clearing just the container backgrounds here (not the QSlider chrome, which
    still comes from the global stylesheet, keeping the handle/groove identical
    to SmartProp) lets the zebra colour show through underneath.
    """
    compact.style_slider(float_widget)
    float_widget.setStyleSheet("background-color: transparent;")
    float_widget.Slider.setStyleSheet("background-color: transparent;")


def pretty_name(value_class: str) -> str:
    """'m_flRandomScaleMin' -> 'Random Scale Min', same rule SmartProp uses."""
    return _CAMEL_SPLIT.sub(r'\1 \2', _STRIP_PREFIX.sub('', value_class))


class _RowUi:
    """
    Mirrors the attribute shape SmartProp's generated row UIs expose
    (frame / horizontalLayout_2 / layout / property_class) so the compact
    template functions can style our rows unchanged.
    """

    def __init__(self, widget: QWidget):
        self.verticalLayout = QVBoxLayout(widget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)

        self.frame = QFrame(widget)
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setLineWidth(0)
        self.verticalLayout.addWidget(self.frame)

        self.horizontalLayout_2 = QHBoxLayout(self.frame)
        self.horizontalLayout_2.setSpacing(16)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)

        self.layout = QHBoxLayout()
        self.horizontalLayout_2.addLayout(self.layout)

        self.property_class = QLabel(self.frame)
        self.layout.addWidget(self.property_class)


class BaseRow(QWidget):
    """One property row: colour-coded label on the left, editor on the right."""

    edited = Signal()

    def __init__(self, field, label_color=None, parent=None):
        super().__init__(parent)
        self.field = field
        self.ui = _RowUi(self)
        self.ui.property_class.setText(field.label or pretty_name(field.key))
        self.setToolTip(f"{field.key}\n\n{field.description}")
        compact.apply_row_no_switch(self, label_color=label_color)


class FloatRow(BaseRow):
    """Numeric field — inline drag-slider, range-locked when the schema says so."""

    def __init__(self, field, value, parent=None):
        super().__init__(field, COLOR_FLOAT, parent)
        self.float_widget = FloatWidget(
            value=float(value),
            slider_range=list(field.range) if field.range else [0, 0],
            lock_range=bool(field.range),
            only_positive=bool(field.range) and field.range[0] >= 0,
            digits=field.digits,
        )
        style_slider(self.float_widget)
        self.float_widget.edited.connect(lambda _: self.edited.emit())
        self.ui.layout.addWidget(self.float_widget)

    def value(self) -> float:
        return float(self.float_widget.value)


class BoolRow(BaseRow):
    def __init__(self, field, value, parent=None):
        super().__init__(field, COLOR_BOOL, parent)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(bool(value))
        compact.style_checkbox(self.checkbox)
        self.checkbox.stateChanged.connect(lambda _: self.edited.emit())
        self.ui.layout.addWidget(self.checkbox)
        self.ui.layout.addStretch(1)

    def value(self) -> bool:
        return self.checkbox.isChecked()


class StringRow(BaseRow):
    def __init__(self, field, value, placeholder=None, parent=None):
        super().__init__(field, COLOR_STRING, parent)
        self.line = QLineEdit(str(value or ""))
        if placeholder:
            self.line.setPlaceholderText(placeholder)
        self.line.setMaximumHeight(compact.FIELD_H)
        self.line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.line.textChanged.connect(lambda _: self.edited.emit())
        self.ui.layout.addWidget(self.line)

    def value(self) -> str:
        return self.line.text().strip()


class ModelRow(StringRow):
    """Resource path field with a browse button, like SmartProp's model picker."""

    browse_requested = Signal()

    def __init__(self, field, value, parent=None):
        super().__init__(field, value, placeholder="models/…/example.vmdl", parent=parent)
        self.browse_button = QPushButton()
        self.browse_button.setIcon(QIcon(":/valve_common/icons/tools/common/browse.png"))
        self.browse_button.setFixedSize(compact.FIELD_H, compact.FIELD_H)
        self.browse_button.setToolTip("Browse for a .vmdl in the addon content folder")
        self.browse_button.clicked.connect(self.browse_requested)
        self.ui.layout.addWidget(self.browse_button)

    def set_value(self, text: str):
        self.line.setText(text)


class QAngleRow(BaseRow):
    """Pitch / yaw / roll on one row, using SmartProp's vector tag colours."""

    def __init__(self, field, value, parent=None):
        super().__init__(field, COLOR_FLOAT, parent)
        self.float_widgets = []
        for axis, name in enumerate(("P", "Y", "R")):
            tag = QLabel(name)
            tag.setStyleSheet(f"color: {compact.VEC_PYR[axis]}; font: bold 8pt 'Segoe UI'; margin-left: 2px; margin-right: 2px; border: 0px; background: transparent;")
            self.ui.layout.addWidget(tag)

            spin = FloatWidget(
                value=float(value[axis]),
                slider_range=list(field.range) if field.range else [0, 0],
                lock_range=bool(field.range),
                digits=field.digits,
            )
            style_slider(spin)
            spin.edited.connect(lambda _: self.edited.emit())
            self.ui.layout.addWidget(spin)
            self.float_widgets.append(spin)

    def value(self) -> list:
        return [float(w.value) for w in self.float_widgets]


class SectionHeader(QWidget):
    """Group divider between property sections (Model, Fade, Orientation, …)."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 8, 4, 2)
        layout.setSpacing(0)
        label = QLabel(title.upper())
        label.setStyleSheet(
            'border:0px; background: transparent; font: 600 7pt "Segoe UI";'
            ' letter-spacing: 1px; color: %s;' % compact.ACCENT
        )
        layout.addWidget(label)
        layout.addStretch(1)
        self.setStyleSheet(compact.widget_qss())


def build_row(field, value):
    """Row factory for a schema field."""
    if field.kind == "model":
        return ModelRow(field, value)
    if field.kind == "string":
        return StringRow(field, value)
    if field.kind == "bool":
        return BoolRow(field, value)
    if field.kind == "qangle":
        return QAngleRow(field, value)
    return FloatRow(field, value)


def apply_zebra(layout):
    """Paint alternating backgrounds over the rows, as PropertyFrame does."""
    index = 0
    for i in range(layout.count()):
        item = layout.itemAt(i)
        widget = item.widget() if item is not None else None
        if widget is None or not getattr(widget, "_compact_frames", None):
            continue
        compact.set_row_bg(widget, compact.zebra_color(index))
        index += 1
