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

# src/icons (compact.py lives at src/editors/smartprop_editor/property/).
_ICON_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "icons",
)


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

# palette
BG = "#2e2e2e"
BG_ALT = "#353535"
FG = "#e5e5e5"
FG_DIM = "#a2a8b1"
HOVER = "#515965"
ACCENT = "#b3d096"

# Alternating row backgrounds (zebra striping replaces the separator line).
# Straddle the #2e2e2e panel base: one row a little brighter, the next a little
# darker. The old pair (#2e2e2e / #333333) was a 5-value step and read as flat.
ROW_BG_EVEN = "#353535"
ROW_BG_ODD = "#2f2f31"
# Background of the property row the user has selected (copy/paste + help target).
ROW_BG_SELECTED = "#3b3f48"

# Vector component tag colours (kept close to the existing H5T hues).
VEC_XYZ = ("#ECA4A0", "#B6EFA2", "#A4B6EF")   # X / Y / Z  (red / green / blue)
VEC_PYR = ("#ECA4A0", "#B6EFA2", "#A4B6EF")   # P / Y / R  (pitch / yaw / roll)


# stylesheets
#
# The alternating row background lives in frame_qss(), keyed on a dynamic
# property, so restriping never re-parses a sheet. Every setStyleSheet call
# re-parses and re-polishes the whole widget subtree; the old per-row zebra pass
# touched ~60 widgets per property-frame rebuild and measured ~180 ms on its own.
# Object name stamped on every compact row container so the transparency rule
# below can target it. A plain ``.QWidget`` selector will not do: it matches
# exact QWidget instances only, and every row is a QWidget *subclass*
# (PropertyFloat, PropertyBool, ...).
ROW_OBJECT_NAME = "compactPropertyRow"

#: Dynamic property carrying a row frame's stripe: "even", "odd" or "sel".
#: Paired with the rules in frame_qss().
ZEBRA_PROPERTY = "zebraRow"


def widget_qss():
    """Flat container: no padding, no border. Background is painted by the parent.

    ``background: transparent`` is load-bearing, not cosmetic. The application
    stylesheet carries an unqualified ``QWidget { background-color: #272727; }``
    rule that matches every widget in the app, and QStyleSheetStyle paints it
    over anything drawn in a parent's paintEvent — which silently flattened the
    zebra stripes and the selection highlight to one colour. A rule in the
    widget's own sheet wins over the application sheet, so the rows opt out
    here and let PropertyFrame.paintEvent show through.
    """
    return (
        "QWidget#%s { background: transparent; }"
        # Reaches every QFrame nested in the row, including the plain grouping
        # frames the .ui files add (vector3d's frame_4, say) which declare no
        # sheet of their own and would otherwise take the application's opaque
        # background. Controls that need a real background — comboboxes, text
        # fields, buttons — set it in their own sheet, which wins over this one.
        "QFrame { background: transparent; }"
        ".QWidget { color:%s; border:0px; padding:0px; background: transparent;"
        " font: 8pt \"Segoe UI\"; }"
        ".QWidget::selected { background-color:%s; }" % (ROW_OBJECT_NAME, FG, HOVER)
    )


def frame_qss():
    """Flat row frame, carrying its own zebra stripe.

    The stripe colours live here, keyed on the ``zebraRow`` dynamic property,
    rather than being painted behind the row by the containing frame. Painting
    behind only shows through while *every* widget above the stripe is
    transparent, and in this app that is a losing bet — four separate ancestors
    (the row frames, vector3d's frame_4, property_frame's frame_layout, and
    finally QMainWindow itself) each carried an unqualified background rule and
    each flattened the rows in turn. An opaque background on the frame that owns
    the row cannot be covered by anything above it.

    Cost is unchanged: this sheet is still applied exactly once per frame, in
    compact_frame(). Restriping is setProperty + a repolish of that one frame,
    not a fresh setStyleSheet over the row's whole subtree.
    """
    return (
        ".QFrame { color:%s; border:0px; background: transparent;"
        " font: 8pt \"Segoe UI\"; }"
        ".QFrame[%s=\"even\"] { background-color:%s; }"
        ".QFrame[%s=\"odd\"] { background-color:%s; }"
        ".QFrame[%s=\"sel\"] { background-color:%s; }"
        % (FG,
           ZEBRA_PROPERTY, ROW_BG_EVEN,
           ZEBRA_PROPERTY, ROW_BG_ODD,
           ZEBRA_PROPERTY, ROW_BG_SELECTED)
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
    border: 1px solid #5e5e5e; background-color: %(bg)s;
    selection-background-color: %(hover)s; outline: 0px;
}
QComboBox QAbstractItemView::item { padding: 3px 6px; color: #bebebe; border: 0px; }
QComboBox QAbstractItemView::item:selected { background-color: %(hover)s; color: white; }
""" % {"dim": FG_DIM, "alt": BG_ALT, "hover": HOVER, "bg": BG}


# Flat, short value combobox (the actual choice field).
VALUE_COMBOBOX_QSS = """
QComboBox {
    font: 8pt "Segoe UI";
    border: 0px; border-bottom: 1px solid #4a4a4a; border-radius: 0px;
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
    border: 1px solid #5e5e5e; background-color: %(bg)s;
    selection-background-color: %(hover)s; outline: 0px;
}
QComboBox QAbstractItemView::item { padding: 3px 6px; color: #bebebe; border: 0px; }
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
    image: url(://icons/check_box_outline_blank_16dp.svg);
}
QCheckBox::indicator:checked {
    image: url(://icons/select_check_box_16dp.svg);
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


# helpers
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


def compact_frame(frame):
    """Row frame: min ROW_H, allowed to grow to ROW_MAX (expression mode).

    The only setStyleSheet a row frame ever gets — the stripe itself is switched
    later through the zebraRow property (assign_zebra).
    """
    frame.setMinimumHeight(ROW_H)
    frame.setMaximumHeight(ROW_MAX)
    frame.setStyleSheet(frame_qss())


def zebra_color(idx):
    return ROW_BG_ODD if (idx % 2) else ROW_BG_EVEN


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
    frames are skipped entirely. A palette is not an option here — QStyleSheetStyle
    overwrites the palette of any widget it polishes, and every row carries a
    stylesheet.
    """
    for frame, value in zebra_plan(layout, selected):
        frame.setProperty(ZEBRA_PROPERTY, value)
        style = frame.style()
        style.unpolish(frame)
        style.polish(frame)


def _paint_bg(widget, qss, selector, color):
    """Opaque ``color`` background for a widget nothing else paints behind.

    For the detail-prop editor, which restyles a handful of rows at a time and
    can afford a setStyleSheet each. SmartProp's property rows go through
    assign_zebra instead — they rebuild in bulk, where this cost ~180 ms. The
    ``_bg`` guard keeps a repeated call with an unchanged colour free.
    """
    try:
        if getattr(widget, "_bg", None) == color:
            return
        widget.setStyleSheet("%s %s { background-color:%s; }" % (qss, selector, color))
        widget._bg = color
    except Exception:
        pass


def set_widget_bg(prop, color):
    """Set a standalone container's own background."""
    _paint_bg(prop, widget_qss(), ".QWidget", color)


def set_frame_bg(frame, color):
    """Set a single row-frame's background."""
    _paint_bg(frame, frame_qss(), ".QFrame", color)


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
    prop.setObjectName(ROW_OBJECT_NAME)
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
    prop.setObjectName(ROW_OBJECT_NAME)
    prop.setStyleSheet(widget_qss())

    compact_frame(prop.ui.frame)
    prop._compact_frames = [prop.ui.frame]

    prop.ui.horizontalLayout_2.setSpacing(0)
    prop.ui.horizontalLayout_2.setContentsMargins(6, 0, 4, 0)
    prop.ui.layout.setSpacing(4)

    style_label(prop.ui.property_class, color=label_color)
