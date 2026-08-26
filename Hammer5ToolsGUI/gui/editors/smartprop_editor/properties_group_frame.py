import ast
from gui.editors.smartprop_editor.ui_properties_group_frame import Ui_Form

from PySide6.QtWidgets import QWidget, QFrame, QApplication
from PySide6.QtCore import Signal, QSize
from gui.property.methods import PropertyMethods
from gui.widgets import ErrorInfo
from gui.editors.smartprop_editor.property import compact
from gui.editors.smartprop_editor._common import parse_component_clipboard
from gui.styles.common import set_style_property

# Group type color constants
_GROUP_COLORS = {
    'modifier': '#8B5E3C',           # bronze
    'selection_criteria': '#2E6B9E',  # steel blue
}


class PropertiesGroupFrame(QWidget):
    add_signal = Signal()
    paste_signal = Signal()
    def __init__(self, widget_list=None, name=None, group_type=None):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.property_class.setAcceptDrops(False)
        self.name = name
        self.group_type = group_type

        self.layout = self.ui.layout
        self.ui.add_button.clicked.connect(self.add_action)

        self.ui.paste_button.clicked.connect(self.paste_action)

        # CS2 tool icons for the header buttons.
        self.ui.add_button.setIcon(compact.cs2_icon('add'))
        self.ui.add_button.setIconSize(QSize(16, 16))
        self.ui.paste_button.setIcon(compact.cs2_icon('paste'))
        self.ui.paste_button.setIconSize(QSize(16, 16))

        # The header's bottom line now comes from the field bottom-borders
        # (name + gap filler), exactly like the default/element header — no
        # separate frame border needed.

        self.ui.property_class.setText(self.name)
        self.widget_list = widget_list

        self._drop_indicator = None

        self._apply_group_color()

        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

    def _apply_group_color(self):
        color = _GROUP_COLORS.get(self.group_type)
        if color:
            set_style_property(self.ui.label, "h5Component", "smartpropGroupColorLabel")
            set_style_property(self.ui.label, "h5GroupType", self.group_type)

    def add_action(self):
        self.add_signal.emit()

    def paste_action(self):
        # Validate clipboard group_type before pasting
        if self.group_type:
            clipboard = QApplication.clipboard()
            clipboard_text = clipboard.text()
            clip_group, pasted_dicts = parse_component_clipboard(clipboard_text)
            if clip_group and pasted_dicts:
                target_norm = "modifier" if self.group_type in ("modifier", "modifiers", "operators") else "selection_criteria"
                clip_norm = "modifier" if clip_group in ("modifier", "modifiers", "operators") else "selection_criteria"
                if target_norm != clip_norm:
                    friendly_src = clip_group.replace('_', ' ')
                    friendly_dst = self.group_type.replace('_', ' ')
                    ErrorInfo(
                        text=f"Cannot paste a '{friendly_src}' into '{friendly_dst}' group."
                    ).exec()
                    return
        self.paste_signal.emit()

    def show_child(self):
        if not self.ui.show_child.isChecked():
            self.ui.frame_layout.setMaximumSize(16666, 0)
        else:
            self.ui.frame_layout.setMaximumSize(16666, 16666)

    def _show_drop_indicator(self, index):
        self._hide_drop_indicator()
        indicator = QFrame()
        indicator.setFixedHeight(2)
        indicator.setProperty("h5Component", "smartpropDropIndicator")
        indicator.setObjectName("_drop_indicator")
        self.layout.insertWidget(index, indicator)
        self._drop_indicator = indicator

    def _hide_drop_indicator(self):
        if self._drop_indicator is not None:
            self.layout.removeWidget(self._drop_indicator)
            self._drop_indicator.deleteLater()
            self._drop_indicator = None

    mousePressEvent = PropertyMethods.mousePressEvent
    mouseMoveEvent = PropertyMethods.mouseMoveEvent
    dragEnterEvent = PropertyMethods.dragEnterEvent
    dragMoveEvent = PropertyMethods.dragMoveEvent
    dragLeaveEvent = PropertyMethods.dragLeaveEvent
    dropEvent = PropertyMethods.dropEvent
