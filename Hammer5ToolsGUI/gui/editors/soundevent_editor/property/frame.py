import ast

from PySide6.QtWidgets import QWidget, QHBoxLayout, QApplication, QTreeWidget
from PySide6.QtCore import QSignalBlocker, Signal

from gui.editors.soundevent_editor.property.common import (
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
from gui.editors.soundevent_editor.property.ui_frame import Ui_Form
from gui.widgets.property_methods import PropertyDragDropMixin
from gui.common import convert_snake_case
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


class SoundEventEditorPropertyFrame(QWidget):
    """PropertyFrame suppose to collect properties and gives dict value"""
    edited = Signal()
    deleted = Signal(str)       # emits the property name just before the frame is destroyed
    slider_pressed = Signal()   # emitted when a float slider drag starts
    committed = Signal()        # emitted when a float slider drag ends
    def __init__(self, _data: dict = None, widget_list: QHBoxLayout = None, tree:QTreeWidget = None):
        """Data variable is _data:d can receive only dict value"""
        super().__init__()

        # If dict value is empty, just skip initialization of the frame and delete item itself
        if widget_list is None:
            raise ValueError
        if _data is None:
            self.deleteLater()
        else:
            # Init UI file
            self.ui = Ui_Form()
            self.ui.setupUi(self)
            self.ui.verticalLayout.setContentsMargins(14, 0, 0, 0)
            self.ui.header.setProperty("h5Component", "soundeventPropertyHeader")
            self.setAcceptDrops(True)

            # Variables
            self.tree = tree
            self.value = dict()
            self.name = str(next(iter(_data)))
            self.widget_list = widget_list
            self._height = 24

            self.populate_properties(data=_data)

            self.init_connections()
            self.init_header()

            # Silent init — populate value without emitting
            self.value = self.serialize_properties()

    def init_connections(self):
        """Adding connections to the buttons"""
        self.ui.show_child.clicked.connect(self.show_child_action)
        self.ui.delete_button.clicked.connect(self.delete_action)
        self.ui.copy_button.clicked.connect(self.copy_action)
    def init_header(self):
        """Setup for header frame"""
        self.ui.property_class.setText(convert_snake_case(self.name))
        self.ui.property_class.setToolTip(get_tooltip(self.name))

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
        self.ui.content.layout().addWidget(self.property_instance)
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
        if _data is None:
            pass
        else:
            for index in range(self.ui.content.layout().count()):
                widget_instance = self.ui.content.layout().itemAt(index).widget()
                value_dict = widget_instance.value
                _data.update(value_dict)
            return _data

    def set_values(self, data: dict) -> bool:
        """Show ``data`` in the widgets this frame already has.

        Returns False when the frame cannot represent the data (a different
        property, a different widget count, or a widget that has no in-place
        update) — the caller then throws the frame away and builds a new one.
        Reuse is what makes undo/redo and event switching cheap: refreshing a
        frame is a handful of setText calls, building one loads a .ui form and
        a whole widget tree.
        """
        layout = self.ui.content.layout()
        try:
            widgets = [layout.itemAt(index).widget() for index in range(layout.count())]
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
        """Copy action"""
        clipboard = QApplication.clipboard()
        _data = self.serialize_properties()
        _data = str(_data)
        clipboard.setText(_data)

    def delete_action(self):
        """Set value to None, then send signal that updates value then delete self"""
        self.deleted.emit(self.name)
        for index in range(self.ui.content.layout().count()):
            widget_instance = self.ui.content.layout().itemAt(index).widget()
            widget_instance.deleteLater()
        self.value = None
        self.edited.emit()
        self.deleteLater()


    def show_child_action(self):
        """Showing child widgets, resizes the layout to hide or show child"""
        if not self.ui.show_child.isChecked():
            self.ui.content.setMaximumHeight(0)
        else:
            self.ui.content.setMaximumHeight(16666)

    def set_context_element(self, name: str):
        """Forward the active element name to the inner property widget, if supported.
        """

    # Drag and drop

    mousePressEvent = PropertyDragDropMixin.mousePressEvent
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
                widget_property = widget.ui.content.layout().itemAt(0).widget()
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
