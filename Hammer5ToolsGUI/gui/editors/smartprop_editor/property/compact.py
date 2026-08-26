"""
Shared compact row template for SmartProp property editors.

Goal: mimic the Source 2 / Hammer property editor — a dense two-column grid
(fixed label column on the left, editor on the right), thin ~22px rows separated
by 1px lines, flat/short comboboxes, a very thin inline value-mode switch
(Default/Float/Variable/Expression), thin inline drag-sliders on numeric fields,
and colour-coded vector component tags.

Everything here is applied to a widget instance *once* (from each editor's
__init__). Because pooled widgets are reconfigured in place — never rebuilt — the
styling set here survives acquire/release, so it must NOT be value-dependent and
does not need to be re-applied in reconfigure().

Dark palette kept: #2e2e2e bg, #e5e5e5 text, #515965 hover, accent #b3d096.
"""

import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSizePolicy, QLayout

from gui.common import gui_assets_dir
from gui.styles.common import set_style_property
_ICON_DIR = gui_assets_dir("icons")


_VALVE_ICON_MAP = {
    "add": ":/valve_common/icons/tools/common/add_sm.png",
    "paste": ":/valve_common/icons/tools/common/paste_sm.png",
    "copy": ":/valve_common/icons/tools/common/copy_sm.png",
    "delete": ":/valve_common/icons/tools/common/delete_sm.png",
}


def cs2_icon(name):
    """QIcon for a vendored CS2 / Valve tool icon (using Valve common icons)."""
    if name in _VALVE_ICON_MAP:
        icon = QIcon(_VALVE_ICON_MAP[name])
        if not icon.isNull():
            return icon
    file_path = os.path.join(_ICON_DIR, "cs2_%s.png" % name)
    if os.path.exists(file_path):
        return QIcon(file_path)
    return QIcon(":/valve_common/icons/tools/common/%s.png" % name)


# geometry
ROW_H = 29          # compact row height (minimum) — 1.3x the base 22
ROW_MAX = 57        # rows may grow to this (expression mode: button + text_line)
FIELD_H = 23        # inner field height (comboboxes, text field, expr button)
LABEL_W = 150       # fixed label column width -> the two-column grid
LOGIC_W = 70        # width of the thin inline value-mode switch

# Vector component tag colours (kept close to the existing H5T hues).
VEC_XYZ = ("#ECA4A0", "#B6EFA2", "#A4B6EF")   # X / Y / Z  (red / green / blue)
VEC_PYR = ("#ECA4A0", "#B6EFA2", "#A4B6EF")   # P / Y / R  (pitch / yaw / roll)


# stylesheets
#
# The alternating row background is keyed on a dynamic property, so restriping
# never reparses a sheet. The old per-row stylesheet pass touched roughly 60
# widgets per property-frame rebuild and measured about 180 ms on its own.
# Object name stamped on every compact row container so the transparency rule
# below can target it. A plain ``.QWidget`` selector will not do: it matches
# exact QWidget instances only, and every row is a QWidget *subclass*
# (PropertyFloat, PropertyBool, ...).
ROW_OBJECT_NAME = "compactPropertyRow"

#: Dynamic property carrying a row frame's stripe: "even", "odd" or "sel".
#: Paired with the compact-frame rules in smartprop_editor.qss.
ZEBRA_PROPERTY = "zebraRow"


_LABEL_COLOR_ROLES = {
    "#ffbdbe": "bool",
    "rgb(255,189,190)": "bool",
    "#6c87ff": "integer",
    "rgb(108,135,255)": "integer",
    "#b5ffef": "float",
    "rgb(181,255,239)": "float",
    "#ff7b7d": "expression",
    "rgb(255,123,125)": "expression",
    "#ffd199": "string",
    "rgb(255,209,153)": "string",
    "#a375ff": "vector",
    "#8fb0ff": "reference",
    "#eca4a0": "axisX",
    "#b6efa2": "axisY",
    "#a4b6ef": "axisZ",
}


def _color_role(color):
    if not color:
        return "default"
    normalized = str(color).lower().replace(" ", "")
    return _LABEL_COLOR_ROLES.get(normalized, "default")



def style_checkbox(cb):
    cb.setProperty("h5Component", "smartpropCompactCheckbox")


def style_text_line(text_line):
    """String/expression inline field: single row height, small font, no
    padding, transparent background."""
    text_line.setProperty("h5Component", "smartpropCompactTextLine")
    text_line.setFixedHeight(FIELD_H)


def style_expr_button(btn):
    """Shrink the 'open expression editor' button to fit a compact row."""
    try:
        btn.setFixedSize(FIELD_H, FIELD_H)
        btn.setIconSize(QSize(16, 16))
    except Exception:
        pass


# helpers
def style_logic_switch(combo):
    """Restyle the value-mode switch: very thin, flat, fixed narrow width."""
    combo.setProperty("h5Component", "smartpropLogicSwitch")
    combo.setFixedWidth(LOGIC_W)
    combo.setMaximumHeight(FIELD_H)


def style_value_combobox(combo):
    combo.setProperty("h5Component", "smartpropValueCombobox")
    combo.setMaximumHeight(FIELD_H)


def style_label(label, color=None, width=LABEL_W, indent=0):
    label.setProperty("h5Component", "smartpropCompactLabel")
    set_style_property(label, "h5ColorRole", _color_role(color))
    set_style_property(label, "h5Indent", str(indent))
    if width is not None:
        label.setFixedWidth(width)


def style_slider(float_widget):
    """Trim the spinbox and let the inline drag-slider extend to fill the row.

    The FloatWidget ships with a trailing expanding spacer that keeps the slider
    short; removing it (and marking the slider/widget expanding) makes the slider
    stretch to the full available width and grow with the panel."""
    try:
        float_widget.SpinBox.setMaximumWidth(56)
        float_widget.Slider.setMaximumWidth(16777215)
        lay = float_widget.layout()
        if lay is not None:
            for i in reversed(range(lay.count())):
                item = lay.itemAt(i)
                if item is not None and item.spacerItem() is not None:
                    lay.takeAt(i)
        float_widget.Slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        float_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    except Exception:
        pass


def compact_frame(frame):
    """Row frame: min ROW_H, allowed to grow to ROW_MAX (expression mode).

    The base look comes from the ``smartpropCompactFrame`` selectors in
    qss/features/smartprop_editor.qss, picked up via this one dynamic
    property. The stripe itself is switched later through the zebraRow
    property (assign_zebra).
    """
    frame.setMinimumHeight(ROW_H)
    frame.setMaximumHeight(ROW_MAX)
    frame.setProperty("h5Component", "smartpropCompactFrame")


def zebra_plan(layout, selected=None):
    """``[(frame, value)]`` for every row frame whose stripe is out of date.

    Visible rows are numbered in layout order, and multi-row editors (Vector3D:
    header + X/Y/Z) advance the stripe per sub-frame so their components
    alternate too. Empty result means nothing needs restyling — which is the
    common case, and what keeps the staleness check in PropertyFrame.paintEvent
    from costing anything.
    """
    plan = []
    idx = 0
    for i in range(layout.count()):
        item = layout.itemAt(i)
        w = item.widget() if item is not None else None
        frames = getattr(w, "_compact_frames", None)
        if w is None or not frames or w.isHidden():
            continue
        for f in frames:
            if f.isHidden():
                continue
            value = "sel" if w is selected else ("odd" if idx % 2 else "even")
            if f.property(ZEBRA_PROPERTY) != value:
                plan.append((f, value))
            idx += 1
    return plan


def assign_zebra(layout, selected=None):
    """Restripe the rows in ``layout``, highlighting ``selected``.

    Replaces a per-row setStyleSheet pass that cost ~180 ms per rebuild: a
    dynamic property plus a repolish of the one frame is cheap, and untouched
    frames are skipped entirely.
    """
    for frame, value in zebra_plan(layout, selected):
        frame.setProperty(ZEBRA_PROPERTY, value)
        style = frame.style()
        style.unpolish(frame)
        style.polish(frame)


def compact_variable_frame(variable_frame, variable=None):
    """Shrink a variable-picker container so Variable mode matches the row."""
    variable_frame.setMinimumHeight(ROW_H)
    variable_frame.setMaximumHeight(ROW_H)
    if variable is not None:
        variable.setMaximumHeight(FIELD_H)
        try:
            variable.search_button.set_size(width=FIELD_H, height=FIELD_H)
        except Exception:
            pass


def is_angle_vector(value_class):
    vc = (value_class or "").lower()
    return "angle" in vc or "rotation" in vc or "rotator" in vc


def apply_single_row(prop, label_color=None):
    """
    Apply the compact template to a standard single-row editor whose generated
    UI exposes: prop.ui.frame, prop.ui.horizontalLayout_2, prop.ui.layout,
    prop.ui.property_class, prop.ui.logic_switch.
    """
    prop.setMinimumHeight(0)
    prop.setMaximumHeight(ROW_MAX)
    prop.setObjectName(ROW_OBJECT_NAME)
    prop.setProperty("h5Component", "smartpropCompactRow")

    compact_frame(prop.ui.frame)
    prop._compact_frames = [prop.ui.frame]

    prop.ui.horizontalLayout_2.setSpacing(0)
    prop.ui.horizontalLayout_2.setContentsMargins(6, 0, 4, 0)
    prop.ui.layout.setSpacing(4)

    style_label(prop.ui.property_class, color=label_color)
    style_logic_switch(prop.ui.logic_switch)
    # Vertically centre the type combobox within the row.
    prop.ui.layout.setAlignment(prop.ui.logic_switch, Qt.AlignVCenter)


def apply_row_no_switch(prop, label_color=None):
    """Compact template for a single-row editor that has no value-mode switch
    (e.g. PropertyReference): frame/label only, keeping any right-edge buttons."""
    prop.setMinimumHeight(0)
    prop.setMaximumHeight(ROW_MAX)
    prop.setObjectName(ROW_OBJECT_NAME)
    prop.setProperty("h5Component", "smartpropCompactRow")

    compact_frame(prop.ui.frame)
    prop._compact_frames = [prop.ui.frame]

    prop.ui.horizontalLayout_2.setSpacing(0)
    prop.ui.horizontalLayout_2.setContentsMargins(6, 0, 4, 0)
    prop.ui.layout.setSpacing(4)

    style_label(prop.ui.property_class, color=label_color)
