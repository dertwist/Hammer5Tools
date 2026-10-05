"""Property zoo: one of every SmartProp property and variable editor.

`build_zoo()` instantiates every editor the property frame can dispatch to,
plus every variable body. Two things use it:

* the tests below, which guard the styling contract the compact rows depend on
  (`h5Component`, `zebraRow`) and check that the stripe actually *paints* --
  the pixel check is the one that catches a global stylesheet rule outranking
  the compact rules, which is how the row styling silently died before;
* ``python Hammer5ToolsGUI/Tests/test_smartprop_property_zoo.py``, which opens
  the whole zoo in a scrollable window so the styling can be eyeballed. Pass a
  theme level to see another palette, e.g. ``... test_smartprop_property_zoo.py 3``.
"""

import os
import sys

# Headless under pytest; the __main__ block below wants a real window,
# and QApplication is built at import time, so this has to decide here.
if __name__ != "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
gui_root = os.path.join(repo_root, "Hammer5ToolsGUI")
if gui_root not in sys.path:
    sys.path.insert(0, gui_root)

app = QApplication.instance() or QApplication(sys.argv)

from gui.editors.smartprop_editor.property import compact
from gui.editors.smartprop_editor.property.bool import PropertyBool
from gui.editors.smartprop_editor.property.color import PropertyColor
from gui.editors.smartprop_editor.property.colormatch import PropertyColorMatch
from gui.editors.smartprop_editor.property.combobox import PropertyCombobox
from gui.editors.smartprop_editor.property.comparison import PropertyComparison
from gui.editors.smartprop_editor.property.filtersurface import PropertySurface
from gui.editors.smartprop_editor.property.float import PropertyFloat
from gui.editors.smartprop_editor.property.legacy import PropertyLegacy
from gui.editors.smartprop_editor.property.material_group_choices import PropertyMaterialGroupChoices
from gui.editors.smartprop_editor.property.material_replacements import PropertyMaterialReplacements
from gui.editors.smartprop_editor.property.path_editor import PropertyPathEditor
from gui.editors.smartprop_editor.property.reference import PropertyReference
from gui.editors.smartprop_editor.property.set_variable import PropertyVariableValue
from gui.editors.smartprop_editor.property.string import PropertyString
from gui.editors.smartprop_editor.property.variable import PropertyVariableOutput
from gui.editors.smartprop_editor.property.vector3d import PropertyVector3D
from gui.editors.smartprop_editor.property.warning import PropertyWarning
from gui.editors.smartprop_editor.variables.bool import BoolVariable
from gui.editors.smartprop_editor.variables.color import ColorVariable
from gui.editors.smartprop_editor.variables.combobox import ComboboxVariable
from gui.editors.smartprop_editor.variables.float import FloatVariable
from gui.editors.smartprop_editor.variables.int import IntVariable
from gui.editors.smartprop_editor.variables.legacy import LegacyVariable
from gui.editors.smartprop_editor.variables.material import MaterialVariable
from gui.editors.smartprop_editor.variables.material_group import MaterialGroupVariable
from gui.editors.smartprop_editor.variables.model import ModelVariable
from gui.editors.smartprop_editor.variables.vector2d import Vector2DVariable
from gui.editors.smartprop_editor.variables.vector3d import Vector3DVariable
from gui.editors.smartprop_editor.variables.vector4d import Vector4DVariable
from gui.styles import manager, theme
from gui.widgets.element_id import ElementIDGenerator


#: (label, callable(ctx) -> widget). ``ctx`` carries the shared variables
#: layout and element-id generator every editor wants.
PROPERTY_EDITORS = [
    ("Bool", lambda c: PropertyBool("m_bEnabled", True, c.variables, c.ids)),
    ("Float", lambda c: PropertyFloat(c.ids, "m_flWidth", 64.0, c.variables, slider_range=[0, 4096])),
    ("Int", lambda c: PropertyFloat(c.ids, "m_nCountW", 4, c.variables, int_bool=True, slider_range=[0, 256])),
    ("String", lambda c: PropertyString(c.ids, "m_sModelName", "models/example.vmdl", c.variables,
                                        expression_bool=False, placeholder="models/example.vmdl",
                                        model_browser=True)),
    ("Expression", lambda c: PropertyString(c.ids, "m_Expression", "var_a * 2", c.variables,
                                            expression_bool=True, placeholder="Expression")),
    ("Material", lambda c: PropertyString(c.ids, "m_Material", "materials/a.vmat", c.variables,
                                          expression_bool=False, placeholder="Material name (.vmat)",
                                          browser_type="material")),
    ("SmartProp", lambda c: PropertyString(c.ids, "m_sSmartProp", "smartprops/a.vsmart", c.variables,
                                           expression_bool=False, placeholder="smartprops/a.vsmart",
                                           smartprop_browser=True)),
    ("Color", lambda c: PropertyColor("m_Color", [255, 128, 0], c.variables, c.ids)),
    ("ColorMatch", lambda c: PropertyColorMatch("m_ColorChoices", [{"m_Color": [255, 0, 0]}], c.variables, c.ids)),
    ("Combobox", lambda c: PropertyCombobox("m_PickMode", "RANDOM", c.variables,
                                            ["LARGEST_FIRST", "RANDOM", "ALL_IN_ORDER"], ["String"], c.ids)),
    ("Comparison", lambda c: PropertyComparison("m_Comparison", {"m_Name": "var_a", "m_Value": "1",
                                                                 "m_Comparison": "EQUAL"}, c.variables, c.ids)),
    ("Vector3D", lambda c: PropertyVector3D("m_vPathOffset", [0.0, 0.0, 1.0], c.variables, c.ids)),
    ("Reference", lambda c: PropertyReference("m_nReferenceID", 12, c.variables, c.ids)),
    ("SetVariable", lambda c: PropertyVariableValue("m_VariableValue", {"m_TargetName": "var_a", "m_Value": 1.0},
                                                    c.variables, c.ids)),
    ("VariableOutput", lambda c: PropertyVariableOutput("m_OutputVariable", "var_out", c.variables, c.ids)),
    ("FilterSurface", lambda c: PropertySurface("m_SurfaceNames", ["concrete"], c.variables)),
    ("MaterialReplacements", lambda c: PropertyMaterialReplacements(
        "m_MaterialReplacements", [{"m_OriginalMaterial": "a.vmat", "m_ReplacementMaterial": "b.vmat"}],
        c.variables, c.ids)),
    ("MaterialGroupChoices", lambda c: PropertyMaterialGroupChoices(
        "m_MaterialGroupChoices", [{"m_Name": "group_a", "m_flWeight": 1.0}], c.variables, c.ids)),
    ("PathEditor", lambda c: PropertyPathEditor([[0, 0, 0], [64, 0, 0]], "m_DefaultPath")),
    ("Legacy", lambda c: PropertyLegacy("m_UnknownField", "raw value", c.variables)),
    ("Warning", lambda c: PropertyWarning("Not verified", "_WARN_NOT_VERIFIED")),
]

VARIABLE_EDITORS = [
    ("Float", lambda c: FloatVariable(1.0, 0.0, 10.0, None)),
    ("Int", lambda c: IntVariable(2, 0, 10, None)),
    ("Bool", lambda c: BoolVariable(True, None, None, None)),
    ("Color", lambda c: ColorVariable([255, 128, 0], None, None, None)),
    ("Combobox", lambda c: ComboboxVariable("B", ["A", "B", "C"])),
    ("Material", lambda c: MaterialVariable("materials/a.vmat", None, None, None)),
    ("MaterialGroup", lambda c: MaterialGroupVariable("group_a", None, None, "models/a.vmdl")),
    ("Model", lambda c: ModelVariable("models/a.vmdl", None, None, None)),
    ("Vector2D", lambda c: Vector2DVariable([1.0, 2.0])),
    ("Vector3D", lambda c: Vector3DVariable([1.0, 2.0, 3.0])),
    ("Vector4D", lambda c: Vector4DVariable([1.0, 2.0, 3.0, 4.0])),
    ("Legacy", lambda c: LegacyVariable("raw", None, None, None)),
]


class _RowSelector(QObject):
    """Click-to-select for the zoo, mirroring PropertyFrame.eventFilter."""

    def __init__(self, layout, rows):
        super().__init__()
        self.layout = layout
        self.rows = rows
        self.selected = None
        for row in rows:
            row.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and obj in self.rows:
            self.select(obj)
        return super().eventFilter(obj, event)

    def select(self, row):
        self.selected = row
        compact.assign_zebra(self.layout, selected=row)


class _ZooContext:
    """The two collaborators every editor constructor asks for."""

    def __init__(self):
        self.host = QWidget()
        self.variables = QVBoxLayout(self.host)
        self.ids = ElementIDGenerator()


def build_zoo(context=None):
    """``[(section, label, widget)]`` -- one of every editor, already built."""
    context = context or _ZooContext()
    built = []
    for section, table in (("property", PROPERTY_EDITORS), ("variable", VARIABLE_EDITORS)):
        for label, factory in table:
            built.append((section, label, factory(context)))
    return context, built


#: The two stripe colours the compact-frame rules declare, as canonical
#: (Standard-theme) literals; theme.resolve_hex maps them per theme.
STRIPE_EVEN = "#353535"
#: The selected row's stripe (`zebraRow="sel"`).
SELECTION_STRIPE = "#3b3f48"


def stripes(active):
    """``(even, odd)`` stripe colours for ``active``, lowercased."""
    return (theme.resolve_hex(active, STRIPE_EVEN).lower(),
            active.surface_raised.lower())


def build_zoo_window(theme_level=theme.LEVEL_STANDARD):
    """The scrollable window the ``__main__`` block shows."""
    manager.apply(app, theme.get_theme(theme_level))

    context, built = build_zoo()
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(0)

    rows = []
    section = None
    for kind, label, widget in built:
        if kind != section:
            section = kind
            heading = QLabel("  %s editors" % kind.upper())
            heading.setProperty("h5Component", "detailSectionLabel")
            layout.addWidget(heading)
        widget.setToolTip("%s / %s" % (kind, label))
        layout.addWidget(widget)
        if kind == "property":
            rows.append(widget)
    layout.addStretch(1)

    # Stripe the property rows exactly as PropertyFrame does, and wire the
    # same click-to-select PropertyFrame.eventFilter provides -- without it
    # nothing in this window ever becomes the selected row, which reads as a
    # broken selection highlight.
    selector = _RowSelector(layout, rows)
    body._zoo_selector = selector
    compact.assign_zebra(layout)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(body)
    scroll.setWindowTitle("SmartProp property zoo")
    scroll.resize(760, 900)
    scroll._zoo_context = context  # keep the variables layout alive
    return scroll


# tests


@pytest.fixture(scope="module")
def zoo():
    manager.apply(app, theme.get_theme(theme.LEVEL_STANDARD))
    return build_zoo()


@pytest.mark.parametrize("label,factory", PROPERTY_EDITORS)
def test_every_property_editor_constructs(label, factory):
    assert factory(_ZooContext()) is not None


@pytest.mark.parametrize("label,factory", VARIABLE_EDITORS)
def test_every_variable_editor_constructs(label, factory):
    assert factory(_ZooContext()) is not None


def test_every_property_editor_is_a_compact_row(zoo):
    """Every property editor opts into the compact template.

    The ones that never did (comparison, legacy, colormatch, filtersurface,
    material_replacements, set_variable) rendered with the application's
    default surface and generic 22px controls once compile_ui.py started
    stripping the Designer stylesheets out of their .ui files.
    """
    _, built = zoo
    unstyled = [
        label for kind, label, widget in built
        if kind == "property"
        and widget.property("h5Component") != "smartpropCompactRow"
        # PropertyWarning is a banner, not a row; PathEditor is a button host.
        and label not in {"Warning", "PathEditor"}
    ]
    assert unstyled == []


def test_every_compact_row_exposes_frames_for_striping(zoo):
    _, built = zoo
    for kind, label, widget in built:
        if kind != "property" or widget.property("h5Component") != "smartpropCompactRow":
            continue
        frames = getattr(widget, "_compact_frames", None)
        assert frames, "%s has no _compact_frames, so assign_zebra() skips it" % label
        for frame in frames:
            assert frame.property("h5Component") == "smartpropCompactFrame", label


def test_every_variable_editor_is_a_variable_body(zoo):
    _, built = zoo
    missing = [label for kind, label, widget in built
               if kind == "variable"
               and widget.property("h5Component") != "smartpropVariableBody"]
    assert missing == []


@pytest.mark.parametrize("level", [theme.LEVEL_STANDARD, theme.LEVEL_BRIGHT])
def test_zebra_stripe_survives_the_global_stylesheet(level):
    """The stripe must reach the screen, not just the dynamic property.

    A bare `QFrame#frame` rule in the global sheet used to outrank
    `QFrame[h5Component="smartpropCompactFrame"][zebraRow=...]` on specificity
    -- ID beats attribute -- so every row painted one flat colour while the
    property said otherwise. Only rendering catches that.
    """
    active = theme.get_theme(level)
    manager.apply(app, active)

    context = _ZooContext()
    rows = [PropertyBool("m_bEnabled", True, context.variables, context.ids),
            PropertyBool("m_bOther", False, context.variables, context.ids)]

    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    for row in rows:
        layout.addWidget(row)
    compact.assign_zebra(layout)
    body.resize(600, 2 * compact.ROW_H)

    painted = set()
    for row in rows:
        frame = row._compact_frames[0]
        frame.resize(600, compact.ROW_H)
        frame.ensurePolished()
        pixmap = QPixmap(frame.size())
        frame.render(pixmap)
        # Right edge, vertical middle: past the label column, no control on top.
        image = pixmap.toImage()
        painted.add(image.pixelColor(image.width() - 2, image.height() // 2).name().lower())

    assert painted == set(stripes(active)), (
        "rows painted %s, expected the even/odd stripes %s"
        % (sorted(painted), sorted(stripes(active))))


def test_selected_row_paints_the_selection_stripe():
    """Selecting a row must repaint it, not just set a property.

    Same specificity trap as the zebra stripes: `[zebraRow="sel"]` loses to any
    ID selector that also matches the frame.
    """
    active = theme.get_theme(theme.LEVEL_STANDARD)
    manager.apply(app, active)

    context = _ZooContext()
    rows = [PropertyBool("m_b%d" % i, True, context.variables, context.ids)
            for i in range(3)]
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    for row in rows:
        layout.addWidget(row)

    body.resize(600, len(rows) * compact.ROW_H)

    selector = _RowSelector(layout, rows)
    selector.select(rows[1])

    frame = rows[1]._compact_frames[0]
    assert frame.property("zebraRow") == "sel"
    frame.resize(600, compact.ROW_H)
    frame.ensurePolished()
    pixmap = QPixmap(frame.size())
    frame.render(pixmap)
    image = pixmap.toImage()
    painted = image.pixelColor(image.width() - 2, image.height() // 2).name().lower()
    assert painted == theme.resolve_hex(active, SELECTION_STRIPE).lower()


#: Editors whose value is an asset path, and so must offer a picker button.
ASSET_PATH_EDITORS = {
    ("property", "String"), ("property", "Material"), ("property", "SmartProp"),
    ("variable", "Material"), ("variable", "Model"), ("variable", "MaterialGroup"),
}


def test_asset_path_fields_offer_a_picker(zoo):
    """Every .vmdl/.vmat/.vsmart field gets the model-name field's browse button.

    Same icon and size everywhere: a picker that looks different per field
    reads as a different control.
    """
    _, built = zoo
    for kind, label, widget in built:
        button = getattr(widget, "browse_button", None)
        if (kind, label) not in ASSET_PATH_EDITORS:
            continue
        assert button is not None, "%s/%s has no asset picker" % (kind, label)
        # Existence is not enough: PropertyString hides the button whenever no
        # browser_type reached it, which is how m_sModelName lost its picker.
        assert button.isVisibleTo(widget), "%s/%s picker is hidden" % (kind, label)
        assert button.size().width() == compact.BROWSE_BTN_SIZE, label
        assert button.size().height() == compact.BROWSE_BTN_SIZE, label
        assert not button.icon().isNull(), label


def test_every_browser_type_has_a_picker():
    """compact.ASSET_PICKERS names functions the browser package exports."""
    import gui.widgets.model_browser as browser
    for browser_type, (picker, tooltip) in compact.ASSET_PICKERS.items():
        assert hasattr(browser, picker), "%s -> %s" % (browser_type, picker)
        assert tooltip


def test_smartprop_qss_scopes_every_object_name():
    """An `#objectName` used app-wide must name exactly one widget.

    Object names repeat across .ui files -- `frame`, `label`, `value` and
    friends appear in almost every one -- and the application stylesheet is
    global, so `QFrame#frame` reaches unrelated editors. Worse, ID beats
    attribute on specificity, so it also silently outranks the
    `[h5Component=...]` rule written for those widgets. Either the name is
    unique in the codebase, or the selector must be anchored on an `[h5...]`
    attribute earlier in the same compound selector.
    """
    import re
    from pathlib import Path

    gui_dir = Path(gui_root) / "gui"
    qss = gui_dir / "styles" / "qss" / "features" / "smartprop_editor.qss"
    text = re.sub(r"/\*.*?\*/", "", qss.read_text(encoding="utf-8"), flags=re.S)

    sources = [p for p in list(gui_dir.rglob("*.py")) + list(gui_dir.rglob("*.ui"))
               if "__pycache__" not in p.parts]

    def name_is_unique(name):
        pattern = re.compile(r'["\']%s["\']' % re.escape(name))
        hits = sum(len(pattern.findall(p.read_text(encoding="utf-8", errors="replace")))
                   for p in sources)
        return hits <= 1

    unscoped = []
    position = 0
    for block in re.finditer(r"\{[^{}]*\}", text, flags=re.S):
        selectors = text[position:block.start()]
        line_no = text[:block.start()].count("\n") + 1
        position = block.end()
        for selector in selectors.split(","):
            selector = selector.strip()
            if "#" not in selector:
                continue
            head, _, tail = selector.partition("#")
            if "[h5" in head:
                continue
            if name_is_unique(re.match(r"\w*", tail).group(0)):
                continue
            unscoped.append("%s:%d  %s" % (qss.name, line_no, selector))

    assert unscoped == [], "unscoped ID selectors:\n" + "\n".join(unscoped)


if __name__ == "__main__":
    level = int(sys.argv[1]) if len(sys.argv) > 1 else theme.LEVEL_STANDARD
    window = build_zoo_window(level)
    window.show()
    sys.exit(app.exec())
