import ast
from src.editors.smartprop_editor.ui_properties_group_frame import Ui_Form

from PySide6.QtWidgets import QWidget, QFrame, QApplication
from PySide6.QtCore import Signal
from src.property.methods import PropertyMethods
from src.widgets import ErrorInfo

# Group type color constants
_GROUP_COLORS = {
    'modifier': '#8B5E3C',           # bronze
    'selection_criteria': '#2E6B9E',  # steel blue
}
_DROP_INDICATOR_COLOR = '#5599FF'


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

        self.ui.property_class.setText(self.name)
        self.widget_list = widget_list

        self._drop_indicator = None

        self._apply_group_color()

        self.show_child()
        self.ui.show_child.clicked.connect(self.show_child)

    def _apply_group_color(self):
        color = _GROUP_COLORS.get(self.group_type)
        if color:
            self.ui.label.setStyleSheet(
                f"image: url(:/icons/more_vert.png);\n"
                f"padding-left: 3px;\n"
                f"padding-right: 3px;\n"
                f"border: 2px solid #CCCCCC;\n"
                f"border-top: 0px;\n"
                f"border-right: 0px;\n"
                f"border-bottom: 0px;\n"
                f"border-left: 3px solid {color};\n"
                f"border-radius: 0px;\n"
                f"background-color: #242424;"
            )

    def add_action(self):
        self.add_signal.emit()

    def paste_action(self):
        # Validate clipboard group_type before pasting
        if self.group_type:
            clipboard = QApplication.clipboard()
            clipboard_text = clipboard.text()
            clipboard_data = clipboard_text.split(";;")
            if len(clipboard_data) >= 4 and clipboard_data[0] == "hammer5tools:smartprop_editor_property":
                clip_group_type = clipboard_data[3] if len(clipboard_data) > 3 else None
                if clip_group_type and clip_group_type != self.group_type:
                    friendly_src = clip_group_type.replace('_', ' ')
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

    # ---- Drop indicator ----
    def _show_drop_indicator(self, index):
        self._hide_drop_indicator()
        indicator = QFrame()
        indicator.setFixedHeight(2)
        indicator.setStyleSheet(f"background-color: {_DROP_INDICATOR_COLOR};")
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
