import ast
import textwrap

from PySide6.QtCore import QSignalBlocker, QSize, Qt, Signal
from PySide6.QtGui import QCursor, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QToolTip,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from gui.editors.soundevent_editor.property.common import (
    SoundEventEditorPropertyBase,
    SoundEventEditorPropertyBaseLegacy,
    SoundEventEditorPropertyBool,
    SoundEventEditorPropertyCombobox,
    SoundEventEditorPropertyComment,
    SoundEventEditorPropertyFiles,
    SoundEventEditorPropertyFloat,
    SoundEventEditorPropertyLegacy,
    SoundEventEditorPropertyList,
    SoundEventEditorPropertySoundEvent,
    SoundEventEditorPropertyVector3,
)
from gui.editors.soundevent_editor.property.curve.main import SoundEventEditorPropertyCurve
from gui.editors.soundevent_editor.property_schema import get_spec
from gui.widgets.property_methods import PropertyDragDropMixin
from gui.common import JsonToKv3, convert_snake_case
from gui.styles.common import set_style_property
from gui.editors.soundevent_editor.property_tooltips import get_tooltip
from gui.editors.soundevent_editor.common import vsnd_filepath_convert


# Property kind -> (widget class, does the widget need the soundevent tree?).
# Which kind a key gets is decided by property_schema.SPECS.
_WIDGETS = {
    'float': (SoundEventEditorPropertyFloat, False),
    'bool': (SoundEventEditorPropertyBool, False),
    'string_bool': (SoundEventEditorPropertyBool, False),
    'comment': (SoundEventEditorPropertyComment, False),
    'legacy': (SoundEventEditorPropertyLegacy, False),
    'vector3': (SoundEventEditorPropertyVector3, False),
    'curve': (SoundEventEditorPropertyCurve, False),
    'files': (SoundEventEditorPropertyFiles, False),
    'soundevent': (SoundEventEditorPropertySoundEvent, True),
    'combobox': (SoundEventEditorPropertyCombobox, True),
    'base': (SoundEventEditorPropertyBaseLegacy, True),
}

#: The line down the left edge of every row — the only chrome left after the
#: header came off. It is neutral until the value differs from the saved file,
#: then it takes the modified colour.
RAIL_WIDTH = 3
#: h5ColorRole used when a property widget declares no type colour of its own.
DEFAULT_COLOR_ROLE = "c7c7bb"
INFO_ICON = ":/valve_common/icons/tools/common/icon_info_sm.png"
INFO_BUTTON_SIZE = 18


def kv3_snippet(data: dict) -> str:
    """``data`` as a KV3 body — no encoding header, no outer braces.

    That is the form a property takes inside a .vsndevts, so what the clipboard
    holds can be pasted either back into the editor or straight into the file.
    """
    _, _, body = JsonToKv3(data).partition("-->")
    body = body.strip()
    if body.startswith("{") and body.endswith("}"):
        body = body[1:-1]
    return textwrap.dedent(body).strip("\n")


class SoundEventEditorPropertyFrame(QWidget):
    """One property row: a colour rail, the property's editor, an info button.

    The row has no header bar. Every editor already draws the property's name in
    its type colour, so the header only repeated it — dropping it along with the
    collapse box and the copy/delete buttons is what makes the panel compact.
    Copy and delete moved to the row's context menu and to Ctrl+C / Delete,
    which the row handles while it has focus, and the row itself is the drag
    handle the header's grip used to be.
    """
    edited = Signal()
    deleted = Signal(str)       # emits the property name just before the frame is destroyed
    slider_pressed = Signal()   # emitted when a float slider drag starts
    committed = Signal()        # emitted when a float slider drag ends
    activated = Signal()        # the row was clicked or took focus
    navigate = Signal(int)      # Up/Down pressed while focused: -1 / +1

    def __init__(self, _data: dict = None, widget_list: QHBoxLayout = None, tree:QTreeWidget = None):
        """Data variable is _data:d can receive only dict value"""
        super().__init__()

        # If dict value is empty, just skip initialization of the frame and delete item itself
        if widget_list is None:
            raise ValueError
        if _data is None:
            self.deleteLater()
            return

        # Variables
        self.tree = tree
        self.value = dict()
        self.name = str(next(iter(_data)))
        #: Name shown to the user. Merged min/max pairs override it with the
        #: pair's title; the filter in main.py searches it.
        self.display_name = convert_snake_case(self.name)
        self.widget_list = widget_list
        self.property_instance = None
        self._property_widgets = []

        self.setAcceptDrops(True)
        # Focusable so Ctrl+C / Delete can act on "the row the user is in"
        # without stealing those keys from a text field that has focus.
        self.setFocusPolicy(Qt.StrongFocus)
        self.setProperty("h5Component", "soundeventPropertyRow")
        # A QWidget subclass paints no QSS background without this, which the
        # selected-row highlight needs.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.init_row()

        self.populate_properties(data=_data)

        self.init_info()

        # Silent init — populate value without emitting
        self.value = self.serialize_properties()

    def init_row(self):
        """Build the row: rail, the editor column, and the info button."""
        row = QHBoxLayout(self)
        # Left inset so the rail reads as a child marker under its group bar,
        # which is what the old header's indent did.
        row.setContentsMargins(8, 1, 0, 1)
        row.setSpacing(4)

        self.rail = QFrame(self)
        self.rail.setFixedWidth(RAIL_WIDTH)
        self.rail.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.rail.setProperty("h5Component", "soundeventPropertyRail")
        row.addWidget(self.rail)

        self.content = QFrame(self)
        self.content.setProperty("h5Component", "soundeventPropertyContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        row.addWidget(self.content, 1)

        self.info_button = QToolButton(self)
        self.info_button.setProperty("h5Component", "soundeventInfoButton")
        self.info_button.setIcon(QIcon(INFO_ICON))
        self.info_button.setIconSize(QSize(12, 12))
        self.info_button.setFixedSize(INFO_BUTTON_SIZE, INFO_BUTTON_SIZE)
        self.info_button.setFocusPolicy(Qt.NoFocus)
        self.info_button.clicked.connect(self.show_info)
        row.addWidget(self.info_button, 0, Qt.AlignTop)

    def init_info(self):
        """Point the info button at this property's tooltip.

        The button is the tooltip's only home now that the named header is gone,
        so a property without documented behavior simply has no button.
        """
        tooltip = get_tooltip(self.name)
        self.info_button.setToolTip(tooltip)
        self.info_button.setVisible(bool(tooltip))

    def show_info(self):
        """Show the property's tooltip on demand, for touch/keyboard users."""
        QToolTip.showText(QCursor.pos(), self.info_button.toolTip(), self.info_button)

    # Selection and state

    def set_selected(self, selected: bool):
        """Highlight this row as the one copy/delete hotkeys will act on."""
        set_style_property(self, "selected", bool(selected))

    def set_modified(self, modified: bool):
        """Colour the rail to mark a value that differs from the saved file."""
        set_style_property(self.rail, "h5State", "modified" if modified else "")

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.activated.emit()

    def keyPressEvent(self, event):
        """Row-level hotkeys, replacing the copy and delete buttons."""
        if event.matches(QKeySequence.Copy):
            self.copy_action()
        elif event.key() == Qt.Key_Delete:
            self.delete_action()
        elif event.key() in (Qt.Key_Up, Qt.Key_Down) and not event.modifiers():
            self.navigate.emit(-1 if event.key() == Qt.Key_Up else 1)
        else:
            # Unhandled keys must reach the properties window, which owns
            # Ctrl+F (new property) and Ctrl+V (paste).
            super().keyPressEvent(event)
            return
        event.accept()

    # Properties

    @staticmethod
    def _coerce(name: str, value):
        """Raw file value -> what the property widget for ``name`` expects."""
        if isinstance(value, str):
            try:
                value = ast.literal_eval(value)
            except Exception:
                pass
        if get_spec(name).kind == 'string_bool':
            # Shipped music events store these as the strings 'true'/'false',
            # but BoolWidget needs a real bool.
            value = value == 'true' if isinstance(value, str) else bool(value)
        return value

    def add_property(self, name: str, value:str):
        """
        Adding a property to the frame widget.
        Import properties classes form another file
        """
        value = self._coerce(name, value)

        spec = get_spec(name)
        widget_class, needs_tree = _WIDGETS[spec.kind]
        options = dict(spec.options)
        if needs_tree:
            options['tree'] = self.tree
        self.property_instance = widget_class(label_text=name, value=value, **options)
        self.property_instance.edited.connect(self.on_property_updated)
        # Bubble up slider press/release signals (only FloatWidget-backed properties emit them)
        if hasattr(self.property_instance, 'slider_pressed'):
            self.property_instance.slider_pressed.connect(self.slider_pressed)
        if hasattr(self.property_instance, 'committed'):
            self.property_instance.committed.connect(self.committed)
        if not isinstance(self.property_instance, SoundEventEditorPropertyBase):
            # Curve editors draw no label of their own, and the header that
            # used to name them is gone.
            self.content_layout.addWidget(self._name_label(name))
        self.content_layout.addWidget(self.property_instance)
        self._property_widgets.append(self.property_instance)

    def _name_label(self, name: str) -> QLabel:
        label = QLabel(convert_snake_case(name), self.content)
        label.setProperty("h5Component", "editorPropertyLabel")
        label.setProperty("h5ColorRole", DEFAULT_COLOR_ROLE)
        return label

    def on_property_updated(self):
        """If some of the properties were changed send signa with dict value"""
        self.value = self.serialize_properties()
        self.edited.emit()

    def populate_properties(self, data: dict):
        """Adding properties from received data"""
        if data:
            for name, value in data.items():
                self.add_property(name, value)

    def serialize_properties(self):
        """Geather all values into dict value"""
        _data = {}
        for widget_instance in self._property_widgets:
            _data.update(widget_instance.value)
        return _data

    def set_values(self, data: dict) -> bool:
        """Show ``data`` in the widgets this frame already has.

        Returns False when the frame cannot represent the data (a different
        property, a different widget count, or a widget that has no in-place
        update) — the caller then throws the frame away and builds a new one.
        Reuse is what makes undo/redo and event switching cheap: refreshing a
        frame is a handful of setText calls, building one is a whole widget tree.
        """
        try:
            widgets = list(self._property_widgets)
            if len(widgets) != len(data):
                return False
            for widget, (name, value) in zip(widgets, data.items()):
                if getattr(widget, 'value_class', None) != name or not hasattr(widget, 'set_value'):
                    return False
                # Block the property's own signals: the inner widgets still run
                # their handlers (so the property's value stays in sync) but no
                # `edited` reaches the properties window and pushes an undo entry.
                blocker = QSignalBlocker(widget)
                widget.set_value(self._coerce(name, value))
                del blocker
        except Exception:
            return False
        self.value = self.serialize_properties()
        return True

    def get_property(self, index):
        """Getting single property from the frame widget"""
        pass
    def deserialize_property(self, _data: dict = None):
        """Deserialize property from json"""

    # Actions

    def copy_action(self):
        """Put this property on the clipboard as KV3."""
        QApplication.clipboard().setText(kv3_snippet(self.serialize_properties()))

    def delete_action(self):
        """Set value to None, then send signal that updates value then delete self"""
        self.deleted.emit(self.name)
        for widget_instance in self._property_widgets:
            widget_instance.deleteLater()
        self._property_widgets = []
        self.value = None
        self.edited.emit()
        self.deleteLater()

    def set_context_element(self, name: str):
        """Forward the active element name to the inner property widget.

        Curve editors put it in their plot title, which is how a curve row says
        which event it belongs to.
        """
        forward = getattr(self.property_instance, 'set_context_element', None)
        if callable(forward):
            forward(name)

    # Drag and drop

    def mousePressEvent(self, event):
        """The whole row is the drag handle the header's grip used to be."""
        if event.button() == Qt.LeftButton:
            self._drag_start_position = event.pos()
        self.setFocus(Qt.MouseFocusReason)

    mouseMoveEvent = PropertyDragDropMixin.mouseMoveEvent
    dragEnterEvent = PropertyDragDropMixin.dragEnterEvent
    def dropEvent(self, event):
        if event.source() == self:
            return

        mime_data = event.mimeData()
        if mime_data.hasText():
            if event.source() != self:
                source_index = self.widget_list.layout().indexOf(event.source())
                target_index = self.widget_list.layout().indexOf(self)

                widget: SoundEventEditorPropertyFrame = self.widget_list.layout().itemAt(target_index).widget()
                widget_property = widget._property_widgets[0] if widget._property_widgets else None
                if isinstance(widget_property, SoundEventEditorPropertyList):
                    urls = mime_data.urls()
                    url_set = set(url.toString() for url in urls)
                    for url in url_set:
                        __value = url.replace("file:///", "")
                        __value = vsnd_filepath_convert(__value)
                        widget_property.add_element(__value)

                elif source_index != -1 and target_index != -1:
                    if source_index < self.widget_list.layout().count():
                        source_widget = self.widget_list.layout().takeAt(source_index).widget()
                        if source_widget:
                            self.widget_list.layout().insertWidget(target_index, source_widget)

        event.accept()
