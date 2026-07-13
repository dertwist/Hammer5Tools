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

Dark palette kept: #1C1C1C bg, #E3E3E3 text, #414956 hover, accent #accc8d.
"""

import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSizePolicy, QLayout

# src/icons (compact.py lives at src/editors/smartprop_editor/property/).
_ICON_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "icons",
)


def cs2_icon(name):
    """QIcon for a vendored CS2 tool icon (src/icons/cs2_<name>.png)."""
    return QIcon(os.path.join(_ICON_DIR, "cs2_%s.png" % name))


# ---- geometry -------------------------------------------------------------
ROW_H = 29          # compact row height (minimum) — 1.3x the base 22
ROW_MAX = 57        # rows may grow to this (expression mode: button + text_line)
FIELD_H = 23        # inner field height (comboboxes, text field, expr button)
LABEL_W = 150       # fixed label column width -> the two-column grid
LOGIC_W = 70        # width of the thin inline value-mode switch

# ---- palette --------------------------------------------------------------
BG = "#1C1C1C"
BG_ALT = "#232323"
FG = "#E3E3E3"
FG_DIM = "#9AA0AA"
HOVER = "#414956"
ACCENT = "#accc8d"

# Alternating row backgrounds (zebra striping replaces the separator line).
ROW_BG_EVEN = "#1C1C1C"
ROW_BG_ODD = "#212121"

# Vector component tag colours (kept close to the existing H5T hues).
VEC_XYZ = ("#ECA4A0", "#B6EFA2", "#A4B6EF")   # X / Y / Z  (red / green / blue)
VEC_PYR = ("#ECA4A0", "#B6EFA2", "#A4B6EF")   # P / Y / R  (pitch / yaw / roll)


# ---- stylesheets ----------------------------------------------------------
def widget_qss(bg=BG):
    """Flat container: no padding, no border."""
    return (
        ".QWidget { background-color:%s; color:%s; border:0px; padding:0px;"
        " font: 8pt \"Segoe UI\"; }"
        ".QWidget::selected { background-color:%s; }" % (bg, FG, HOVER)
    )


def frame_qss(bg=BG):
    """Flat row frame — no separator line; the alternating bg divides rows."""
    return (
        ".QFrame { background-color:%s; color:%s; border:0px;"
        " font: 8pt \"Segoe UI\"; }" % (bg, FG)
    )


# Very thin, flat value-mode switch (Default/Float/Variable/Expression).
LOGIC_SWITCH_QSS = """
QComboBox {
    font: 600 7pt "Segoe UI";
    border: 0px; border-radius: 0px;
    color: %(dim)s; background-color: transparent;
    padding: 0px 2px; margin: 0px;
    min-height: 23px; max-height: 23px;
}
QComboBox:hover { background-color: %(hover)s; color: white; }
QComboBox::drop-down {
    width: 11px; border: 0px; margin: 0px;
    background: url(://icons/arrow_drop_down_16dp.svg) no-repeat center;
}
QComboBox QAbstractItemView {
    border: 1px solid #505050; background-color: %(bg)s;
    selection-background-color: %(hover)s; outline: 0px;
}
QComboBox QAbstractItemView::item { padding: 3px 6px; color: #B8B8B8; border: 0px; }
QComboBox QAbstractItemView::item:selected { background-color: %(hover)s; color: white; }
""" % {"dim": FG_DIM, "alt": BG_ALT, "hover": HOVER, "bg": BG}


# Flat, short value combobox (the actual choice field).
VALUE_COMBOBOX_QSS = """
QComboBox {
    font: 8pt "Segoe UI";
    border: 0px; border-bottom: 1px solid #3A3A3A; border-radius: 0px;
    color: %(fg)s; background-color: %(bg)s;
    padding: 0px 4px; margin: 0px;
    min-height: 23px; max-height: 23px;
}
QComboBox:hover { background-color: %(hover)s; color: white; }
QComboBox::drop-down {
    width: 12px; border: 0px; margin: 0px;
    background: url(://icons/arrow_drop_down_16dp.svg) no-repeat center;
}
QComboBox QAbstractItemView {
    border: 1px solid #505050; background-color: %(bg)s;
    selection-background-color: %(hover)s; outline: 0px;
}
QComboBox QAbstractItemView::item { padding: 3px 6px; color: #B8B8B8; border: 0px; }
QComboBox QAbstractItemView::item:selected { background-color: %(hover)s; color: white; }
""" % {"fg": FG, "bg": BG, "hover": HOVER}


def label_qss(color=None, indent=0):
    color_line = "color:%s;" % color if color else ""
    indent_line = "padding-left:%dpx;" % indent if indent else ""
    return (
        "border:0px; background-color: rgba(255,255,255,0);"
        " font: 8pt \"Segoe UI\"; padding-right: 6px; %s %s" % (indent_line, color_line)
    )


# Compact checkbox: keep indicator icons, drop the background fill.
CHECKBOX_QSS = """
QCheckBox { background: transparent; border: 0px; padding: 0px; }
QCheckBox::indicator:unchecked {
    image: url(://icons/check_box_outline_blank_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);
}
QCheckBox::indicator:checked {
    image: url(://icons/select_check_box_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);
}
QCheckBox:hover { background: transparent; }
"""


def style_checkbox(cb):
    cb.setStyleSheet(CHECKBOX_QSS)


def style_text_line(text_line):
    """String/expression inline field: single row height, small font, no
    padding, transparent background."""
    text_line.setStyleSheet(
        'QPlainTextEdit { background: transparent; border: 0px; padding: 0px;'
        ' color: %s; font: 7pt "Segoe UI"; }' % FG
    )
    text_line.setFixedHeight(FIELD_H)


def style_expr_button(btn):
    """Shrink the 'open expression editor' button to fit a compact row."""
    try:
        btn.setFixedSize(FIELD_H, FIELD_H)
        btn.setIconSize(QSize(16, 16))
    except Exception:
        pass


# ---- helpers --------------------------------------------------------------
def style_logic_switch(combo):
    """Restyle the value-mode switch: very thin, flat, fixed narrow width."""
    combo.setStyleSheet(LOGIC_SWITCH_QSS)
    combo.setFixedWidth(LOGIC_W)
    combo.setMaximumHeight(FIELD_H)


def style_value_combobox(combo):
    combo.setStyleSheet(VALUE_COMBOBOX_QSS)
    combo.setMaximumHeight(FIELD_H)


def style_label(label, color=None, width=LABEL_W, indent=0):
    label.setStyleSheet(label_qss(color, indent))
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


def compact_frame(frame, bg=BG):
    """Row frame: min ROW_H, allowed to grow to ROW_MAX (expression mode)."""
    frame.setMinimumHeight(ROW_H)
    frame.setMaximumHeight(ROW_MAX)
    frame.setStyleSheet(frame_qss(bg))


def set_widget_bg(prop, color):
    """Set the container widget's own background (shows only in any gaps)."""
    prop.setStyleSheet(widget_qss(color))


def set_frame_bg(frame, color):
    """Set a single row-frame's background."""
    try:
        frame.setStyleSheet(frame_qss(color))
    except Exception:
        pass


def zebra_color(idx):
    return ROW_BG_ODD if (idx % 2) else ROW_BG_EVEN


def set_row_bg(prop, color):
    """Apply a single background to a compact row and all its frame(s)."""
    set_widget_bg(prop, color)
    for f in getattr(prop, "_compact_frames", ()):  # frame instances
        set_frame_bg(f, color)


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
    prop.setStyleSheet(widget_qss())

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
    prop.setStyleSheet(widget_qss())

    compact_frame(prop.ui.frame)
    prop._compact_frames = [prop.ui.frame]

    prop.ui.horizontalLayout_2.setSpacing(0)
    prop.ui.horizontalLayout_2.setContentsMargins(6, 0, 4, 0)
    prop.ui.layout.setSpacing(4)

    style_label(prop.ui.property_class, color=label_color)
