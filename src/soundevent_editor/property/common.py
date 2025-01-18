from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QTreeWidget, QSpacerItem, QSizePolicy
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPathItem, QFrame, QLineEdit
from PySide6.QtGui import QPainterPath, QPen, QColor, QGuiApplication, QPainter
from PySide6.QtCore import Qt, Signal
from src.popup_menu.popup_menu_main import PopupMenu
from src.preferences import debug, get_addon_dir
from src.common import convert_snake_case
try:
    from src.soundevent_editor.property.curve.ui_main import Ui_CurveWidget
except:
    pass
from src.widgets import FloatWidget, LegacyWidget, BoolWidget, DeleteButton, Button, ComboboxDynamicItems, Spacer
from src.soundevent_editor.common import vsnd_filepath_convert
from src.soundevent_editor.property.curve_editor import CurveEditor

import re, os

#===============================================================<  Properties >============================================================

class SoundEventEditorPropertyBase(QWidget):
    edited = Signal()
    def __init__(self, parent=None, label_text: str = None, value: dict = None):
        """Base property class. There is only a label widget and a frame. New widget can be replaced or added"""
        super().__init__(parent)

        # Value variable
        self.value = value
        self.value_class = label_text

        # Init
        self.set_widget_size()
        self.init_root_layout()
        self.init_label(label_text)
        # self.on_property_update()

        self.setStyleSheet(""".QFrame {
    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 0px;
    border-left: 0px;
    border-right: 0px;
	border-top: 0px;
    border-color: rgba(50, 50, 50, 255);
    color: #E3E3E3;
    background-color: #1C1C1C;
}

.QFrame::hover {
}
.QFrame::selected {
    background-color: #414956;
}""")

    def init_root_layout(self):
        """Adding a root layout in which should be placed all widgets that would be in this class and from encapsulation. Not recommended to overwrite this function"""
        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)
    def init_label(self, label_text):
        """Adding received text to the label widget"""
        if label_text is None:
            label_text = "Label"
        label_instance = QLabel()
        label_instance.setText(convert_snake_case(label_text))
        label_instance.setStyleSheet(f"""
        color: {self.init_label_color()}""")
        self.root_layout.addWidget(label_instance)
    def init_label_color(self):
        return "#C7C7BB"
    def add_property_widget(self, widget):
        """Adding property widget to the root"""
        self.root_layout.addWidget(widget)
    def set_widget_size(self):
        """Set maximum height"""
        self.setMaximumHeight(44)
        self.setMinimumHeight(44)
class SoundEventEditorPropertyFloat(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: dict = None, slider_range: list = [0, 0],only_positive: bool = False):
        """
        Float property. Accepts inputs:

        slider_range: list = [-10.0,10.0]
        only_positive: bool = False

        """
        super().__init__(parent, label_text, value)
        float_value  = 0
        if isinstance(value, float):
            float_value = value
        self.float_widget_instance = FloatWidget(slider_range=slider_range, only_positive=only_positive, value=float_value, spacer_enable=False)
        self.float_widget_instance.edited.connect(self.on_property_update)
        self.add_property_widget(self.float_widget_instance)
        self.value_class = label_text
        self.init_float_widget()

        # Updating value
        self.value_update()

    def init_widget(self):
        """Initialize float widget instance"""
        # self.float_widget_instance = FloatWidget(slider_range=self.slider_range, only_positive=self.only_positive)
        pass
        # self.add_property_widget(self.float_widget_instance)

    def init_float_widget(self):
        """Adding parameter init for float widget instance"""

    def on_property_update(self):
        """Send signal that user changed the property"""
        self.value_update()
        self.edited.emit()

    def value_update(self):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        _value = self.float_widget_instance.value
        self.value = {self.value_class: _value}
    def init_label_color(self):
        return "#73d1bf"

class SoundEventEditorPropertyInt(SoundEventEditorPropertyFloat):
    def __init__(self, parent=None, label_text: str = None, value: dict = None, slider_range: list = [0, 0], only_positive: bool = False):
        """
        Int property. Accepts inputs:

        slider_range: list = [-10,10]
        only_positive: bool = False

        """
        # Call the parent constructor to ensure float_widget_instance is initialized
        super().__init__(parent, label_text, value, slider_range, only_positive)
        # self.float_widget_instance.int_output = True

    def init_float_widget(self):
        """Adding parameter init for float widget instance"""
        # Ensure float_widget_instance is initialized before accessing it
        # if hasattr(self, 'float_widget_instance'):
        self.float_widget_instance.int_output = True
    def init_label_color(self):
        return "#4ca0ad"
class SoundEventEditorPropertyLegacy(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: dict = None):
        """
        Legacy property (placeholder)
        """
        super().__init__(parent, label_text, value)
        self.legacy_widget_instance = LegacyWidget(value=value, spacer_enable=False)
        self.legacy_widget_instance.edited.connect(self.on_property_update)
        self.add_property_widget(self.legacy_widget_instance)
        self.value_class = label_text

        # Updating value
        self.value_update(value)

    def on_property_update(self, value):
        """Send signal that user changed the property"""
        self.value_update(value)
        self.edited.emit()

    def value_update(self, value):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        self.value = {self.value_class: value}
    def init_label_color(self):
        return "#d9b34c"
class SoundEventEditorPropertyBool(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: dict = None):
        """
        Bool property

        value : dict
        """
        super().__init__(parent, label_text, value)
        self.bool_widget_instance = BoolWidget(value=value, spacer_enable=True)
        self.bool_widget_instance.edited.connect(self.on_property_update)
        self.add_property_widget(self.bool_widget_instance)
        self.value_class = label_text

        # Updating value
        self.value_update(value)

    def on_property_update(self, value):
        """Send signal that user changed the property"""
        self.value_update(value)
        self.edited.emit()

    def value_update(self, value):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        self.value = {self.value_class: value}
    def init_label_color(self):
        return "#d1494a"

class SoundEventEditorPropertyVector3(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: list = None):
        """
        Vector3 Property. Have a button to paste the value form hammer editor.
        """
        super().__init__(parent, label_text, value)

        self.value_class = label_text

        # Init Vertical layout
        self.init_vertical_layout()

        # Init values
        self.float_widget_instances = []
        for float_value in value:
            self.add_float_widget(float_value)

        # init button
        self.paste_button = Button()
        self.paste_button.set_text("Paste from clipboard")
        self.paste_button.set_icon_paste()
        self.paste_button.clicked.connect(self.paste_from_clipboard)
        self.vertical_layout.addWidget(self.paste_button)
        # Updating value
        self.value_update()
    def add_float_widget(self, value):
        """Adding float widget instance using given name"""
        float_value = 0
        if isinstance(value, float):
            float_value = value
        float_widget_instance = FloatWidget(value=float_value, spacer_enable=False)
        float_widget_instance.edited.connect(self.on_property_update)
        float_widget_instance.setMaximumHeight(30)
        float_widget_instance.setMinimumHeight(30)
        self.vertical_layout.addWidget(float_widget_instance)
        self.float_widget_instances.append(float_widget_instance)  # Append to the list

    def init_vertical_layout(self):
        """Init paste button. The paste button suppose to be used take position form transforms when you copy transforms to the clipboard from hammer editor"""
        # Create a QFrame to hold the vertical layout
        self.frame = QFrame(self)
        self.frame.setObjectName("frame")
        self.frame.setStyleSheet("""QFrame#frame {border: None;}""")
        self.frame.setContentsMargins(0,0,0,0)
        self.frame.setFrameShape(QFrame.StyledPanel)  # Optional: Set the frame shape
        self.frame.setFrameShadow(QFrame.Raised)      # Optional: Set the frame shadow


        # Initialize the vertical layout
        self.vertical_layout = QVBoxLayout(self.frame)

        # Add the frame to the root layout
        self.root_layout.addWidget(self.frame)

    def init_root_layout(self):
        """Adding a root layout in which should be placed all widgets that would be in this class and from encapsulation. Not recommended to overwrite this function"""
        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)

    def paste_from_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard_text = clipboard.text()
        if clipboard_text.endswith('}'):
            origin_list = re.search(r'origin = "(.*?)"', clipboard_text).group(1)
            origin_list = origin_list.split()
            for index in range(len(self.float_widget_instances)):
                widget_instance: FloatWidget = self.float_widget_instances[index]
                __single_axis = float(origin_list[index])
                widget_instance.set_value(__single_axis)
        if "setpos" in clipboard_text:
            setpos_match = re.search(r'setpos\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)', clipboard_text)
            if setpos_match:
                setpos_values = [float(setpos_match.group(1)), float(setpos_match.group(2)),
                                 float(setpos_match.group(3))]
                for index, value in enumerate(setpos_values):
                    if index < len(self.float_widget_instances):
                        widget_instance: FloatWidget = self.float_widget_instances[index]
                        widget_instance.set_value(value)

    def on_property_update(self):
        """Send signal that user changed the property"""
        self.value_update()
        self.edited.emit()

    def value_update(self):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        _value = []
        for widget_instance in self.float_widget_instances:
            __single_axis = widget_instance.value
            _value.append(__single_axis)
        self.value = {self.value_class: _value}

    def init_label_color(self):
        return "#7DDA58"
    def set_widget_size(self):
        """Set maximum height"""
        # height = 44 * 3 + 40
        # self.setMaximumHeight(height)
        # self.setMinimumHeight(height)

class SoundEventEditorPropertyCurve(QWidget):
    edited = Signal()

    def __init__(self, parent=None, label_text: str = None, value: dict = None, labels: list = None):
        super().__init__(parent)
        self.ui = Ui_CurveWidget()
        self.ui.setupUi(self)
        self.value_class = label_text

        # Updating value
        self.value_update(value)

        # Init labels
        if labels is None:
            labels = ['Label 00', 'Label 01']
        # Texts
        self.ui.label_01.setText(labels[0])
        self.ui.label_02.setText(labels[1])

        self.ui.preview_label_01.setText(labels[0])
        self.ui.preview_label_02.setText(labels[1])
        # Colors
        label_01_color = "#dbff99"
        label_02_color = "#CAF9E9"
        self.ui.label_01.setStyleSheet(f"color: {label_01_color};")
        self.ui.label_02.setStyleSheet(f"color: {label_02_color};")

        self.ui.preview_label_02.setStyleSheet(f"color: {label_02_color};")
        self.ui.preview_label_01.setStyleSheet(f"color: {label_01_color};")

        self.labels_color = [label_01_color, label_02_color]

        # Populate datapoints
        for list in value:
            self.add_datapoint(list)
        self.on_property_update()
        # Set widget size according to datapoint count
        # connections
        self.ui.add_data_point_button.clicked.connect(lambda: self.add_datapoint())

    def resizeEvent(self, event):
        self.on_property_update()

    def add_datapoint(self, value: list = None):
        if value is None:
            value = [0, 0, 0, 0, 2, 3]
        self.datapoint_instance = CurveWidgetDatapoint(value=value, labels_color=self.labels_color)
        self.datapoint_instance.edited.connect(self.on_property_update)
        self.ui.datapoints_layout.addWidget(self.datapoint_instance)
        self.on_property_update()

    def on_property_update(self):
        __value = []
        for index in range(self.ui.datapoints_layout.count()):
            widget = self.ui.datapoints_layout.itemAt(index).widget()
            if isinstance(widget, CurveWidgetDatapoint):
                __list = widget.value
                if isinstance(__list, list):
                    __value.append(__list)
        self.value_update(__value)
        self.set_widget_size(__value)
        self.preview_update(__value)
        self.edited.emit()

    def value_update(self, value):
        self.value = {self.value_class: value}

    def set_widget_size(self, __value):
        count: int = 0
        count = count + len(__value)
        height = count * 44 + 50
        debug(f"set_widget_size, height: {height}, len __value:{count}")
        self.ui.top.setMaximumHeight(height)
        self.ui.top.setMinimumHeight(height)

    def preview_update(self, values):
        def get_value(list_value: list, index: int):
            __data: list = []
            for datapoint in list_value:
                __data.append(datapoint[index])
            while len(__data) < 2:
                __data.append(0)
            return __data

        __data_01 = get_value(list_value=values, index=0)
        __data_02 = get_value(list_value=values, index=1)

        self.setup_scene()

        self.preview_curve(values=__data_01, widget=self.ui.graphicsView_01)
        self.preview_curve(values=__data_02, widget=self.ui.graphicsView_02)

    def setup_scene(self):
        if self.ui.graphicsView_01.scene() is None:
            scene = QGraphicsScene()
            self.ui.graphicsView_01.setScene(scene)
        if self.ui.graphicsView_02.scene() is None:
            scene = QGraphicsScene()
            self.ui.graphicsView_02.setScene(scene)

        self.ui.graphicsView_01.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.graphicsView_01.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Enable antialiasing
        self.ui.graphicsView_01.setRenderHint(QPainter.Antialiasing, True)
        self.ui.graphicsView_02.setRenderHint(QPainter.Antialiasing, True)

        # Add grid lines to the scene


    def _addGridLines(self, scene):
        rect = scene.sceneRect()
        width = rect.width()
        height = rect.height()

        # Draw vertical grid lines
        for i in range(0, int(width), 50):
            scene.addLine(i, 0, i, height, QPen(QColor(100, 100, 100, 50), 1, Qt.DotLine))

        # Draw horizontal grid lines
        for j in range(0, int(height), 50):
            scene.addLine(0, j, width, j, QPen(QColor(100, 100, 100, 50), 1, Qt.DotLine))

    def scale_values(self, values, width, height):
        x_values = [i * (width / (len(values) - 1)) for i in range(len(values))]

        min_value = min(values)
        max_value = max(values)
        value_range = max_value - min_value

        if value_range > 0:
            y_values = [(height - ((y - min_value) / value_range) * height) for y in values]
        else:
            y_values = [height / 2] * len(values)

        return x_values, y_values

    def bezier_interpolate(self, x_values, y_values, num_points):
        if len(x_values) != len(y_values):
            raise ValueError("x_values and y_values must have the same length")

        interpolated_x = []
        interpolated_y = []

        for i in range(len(x_values) - 1):
            x_start, x_end = x_values[i], x_values[i + 1]
            y_start, y_end = y_values[i], y_values[i + 1]

            control_x1 = x_start + (x_end - x_start) / 3
            control_y1 = y_start
            control_x2 = x_start + 2 * (x_end - x_start) / 3
            control_y2 = y_end

            for j in range(num_points):
                t = j / num_points
                x = (1 - t) ** 3 * x_start + 3 * (1 - t) ** 2 * t * control_x1 + 3 * (1 - t) * t ** 2 * control_x2 + t ** 3 * x_end
                y = (1 - t) ** 3 * y_start + 3 * (1 - t) ** 2 * t * control_y1 + 3 * (1 - t) * t ** 2 * control_y2 + t ** 3 * y_end
                interpolated_x.append(x)
                interpolated_y.append(y)

        interpolated_x.append(x_values[-1])
        interpolated_y.append(y_values[-1])

        return interpolated_x, interpolated_y

    def preview_curve(self, values=None, widget=None):
        if widget is None:
            raise ValueError("Widget cannot be None")
        if values is None or len(values) < 2:
            raise ValueError("Values list must contain at least two elements")


        viewport_size = widget.viewport().size()
        width = viewport_size.width()
        height = viewport_size.height()

        widget.scene().setSceneRect(0, 0, width, height)

        x_values, y_values = self.scale_values(values, width, height)

        interpolated_x, interpolated_y = self.bezier_interpolate(x_values, y_values, num_points=10)

        path = QPainterPath()
        path.moveTo(interpolated_x[0], interpolated_y[0])
        for x, y in zip(interpolated_x[1:], interpolated_y[1:]):
            path.lineTo(x, y)

        curve_item = QGraphicsPathItem(path)

        pen = QPen(QColor("gray"))
        pen.setWidth(2)
        curve_item.setPen(pen)

        scene = widget.scene()
        scene.clear()
        self._addGridLines(widget.scene())
        scene.addItem(curve_item)
class SoundEventEditorPropertyList(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: list = None, tree: QTreeWidget = None):
        """
        Vector3 Property. Have a button to paste the value form hammer editor.
        """
        super().__init__(parent, label_text, value)
        self.tree = tree

        self.value_class = label_text

        self.setAcceptDrops(True)

        # Init Vertical layout
        self.init_vertical_layout()

        # Init values
        self.float_widget_instances = []

        # init button
        self.init_button()


        # Populate items
        if isinstance(value, list):
            for item in reversed(value):
                self.add_element(item)
        else:
            self.add_element(value)
        # Updating value
        self.value_update()
    def add_element(self, value: str = None):
        """Adding float widget instance using given name"""
        widget_instance = ListElement(value=value)
        widget_instance.edited.connect(self.on_property_update)
        self.vertical_layout.addWidget(widget_instance)
        self.on_property_update()

    def init_button(self):
        self.button = Button()
        self.button.set_text("Add")
        self.button.set_icon_add()
        self.button.clicked.connect(lambda :self.add_element())
        self.vertical_layout.addWidget(self.button)

    def init_vertical_layout(self):
        """Init paste button. The paste button suppose to be used take position form transforms when you copy transforms to the clipboard from hammer editor"""
        # Create a QFrame to hold the vertical layout
        self.frame = QFrame(self)
        self.frame.setObjectName("frame")
        self.frame.setStyleSheet("""QFrame#frame {border: None;}""")
        self.frame.setContentsMargins(0,0,0,0)
        self.frame.setFrameShape(QFrame.StyledPanel)  # Optional: Set the frame shape
        self.frame.setFrameShadow(QFrame.Raised)      # Optional: Set the frame shadow


        # Initialize the vertical layout
        self.vertical_layout = QVBoxLayout(self.frame)
        self.vertical_layout.setSpacing(0)

        self.spacer = QSpacerItem(40, 2, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.vertical_layout.layout().addItem(self.spacer)
        # Add the frame to the root layout
        self.root_layout.addWidget(self.frame)

    def init_root_layout(self):
        """Adding a root layout in which should be placed all widgets that would be in this class and from encapsulation. Not recommended to overwrite this function"""
        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)

    def on_property_update(self):
        """Send signal that user changed the property"""
        self.value_update()
        self.edited.emit()

    def value_update(self):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        _value = []
        for index in range(self.vertical_layout.count()):
            __widget_instance = self.vertical_layout.layout().itemAt(index).widget()
            if isinstance(__widget_instance, ListElement):
                __single_axis = __widget_instance.value
                if __single_axis != "" and __single_axis is not None:
                    _value.append(__single_axis)
        if _value == []:
            _value = ""
        self.value = {self.value_class: _value}

    def init_label_color(self):
        return "#F6C273"
    def set_widget_size(self):
        """Set maximum height"""
        # height = 44 * 3 + 40
        # self.setMaximumHeight(height)
        # self.setMinimumHeight(height)

class SoundEventEditorPropertyFiles(SoundEventEditorPropertyList):
    def __init__(self, parent=None, label_text: str = None, value: list = None):
        """
        Files Property. Have a button to create an element in the list.
        """
        super().__init__(parent, label_text, value)
    def add_element(self, value: str = None):
        """Adding float widget instance using given name"""
        widget_instance = FileElement(value=value)
        widget_instance.edited.connect(self.on_property_update)
        self.vertical_layout.insertWidget(0, widget_instance)
        self.on_property_update()
class SoundEventEditorPropertySoundEvent(SoundEventEditorPropertyList):
    def __init__(self, parent=None, label_text: str = None, value: list = None, tree: QTreeWidget = None):
        """
        Files Property. Have a button to create an element in the list.
        """
        super().__init__(parent, label_text, value, tree)
        self.tree = tree
    def add_element(self, value: str = None):
        """Adding float widget instance using given name"""
        widget_instance = SoundEventElement(value=value, tree=self.tree)
        widget_instance.edited.connect(self.on_property_update)
        self.vertical_layout.addWidget(widget_instance)
        self.vertical_layout.insertWidget(0, widget_instance)
        self.on_property_update()
class SoundEventEditorPropertyCombobox(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: str = None, tree: QTreeWidget = None, objects: list = None):
        """
        Combox property

        value : str
        """
        super().__init__(parent, label_text, value)

        self.tree: QTreeWidget = tree
        self.value_class = label_text
        self.objects = objects
        # Init combobox
        self.combobox = ComboboxDynamicItems()
        self.combobox.items = self.objects
        self.combobox.setMinimumWidth(256)
        self.combobox.updateItems()
        self.combobox.currentTextChanged.connect(self.on_property_update)
        self.layout().addWidget(self.combobox)
        self.set_value(value)
        # if value == "None":
        #     pass
        # else:
        #     self.combobox.setCurrentText(str(value))


        # Init Search button
        self.search_button = Button()
        self.search_button.set_icon_search()
        self.search_button.setMaximumWidth(32)
        self.search_button.clicked.connect(self.call_search_popup_menu)
        self.layout().addWidget(self.search_button)
        self.on_property_update()

        # Init spacer
        spacer = Spacer()
        self.layout().addWidget(spacer)

        self.setContentsMargins(0,0,0,0)
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)

    def init_combobox(self):
        pass
    def set_value(self, value: str):
        if value != "None":
            if value not in self.combobox.items:
                self.combobox.items.append(value)
                self.combobox.addItem(value)
            self.combobox.setCurrentText(str(value))

    def on_property_update(self):
        """Send signal that user changed the property"""
        value = self.combobox.currentText()
        self.value_update(value)
        self.edited.emit()

    def value_update(self, value):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        self.value = {self.value_class: value}
    def init_label_color(self):
        return "#F4A9F6"

    def call_search_popup_menu(self):
        elements = []
        for item in self.objects:
            __element = {item:item}
            elements.append(__element)
        self.popup_menu = PopupMenu(elements, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
        self.popup_menu.show()

class SoundEventEditorPropertyBaseSoundEvent(SoundEventEditorPropertyCombobox):
    def __init__(self, parent=None, label_text: str = None, value: str = None, tree: QTreeWidget = None, objects: list = None):
        """
        Combox property

        value : str
        """
        super().__init__(parent, label_text, value, tree, objects)
        self.combobox.clicked.connect(self.update_soundevnets)
        self.update_soundevnets()

    def update_soundevnets(self):
        self.combobox.items = self.get_soundenvets()
        self.combobox.updateItems()

    def get_soundenvets(self, elements_dict = False):
        elements = []
        tree_root = self.tree.invisibleRootItem()
        for index in range(tree_root.childCount()):
            __tree_item = tree_root.child(index)
            __name = __tree_item.text(0)
            if elements_dict:
                __element = {__name: __name}
            else:
                __element = __name
            elements.append(__element)
        return elements
    def call_search_popup_menu(self):
        if self.tree is None:
            pass
        else:
            elements = self.get_soundenvets(elements_dict=True)
            self.popup_menu = PopupMenu(elements, add_once=False)
            self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
            self.popup_menu.show()
#==========================================================<  Properties Widgets  >=======================================================

class CurveWidgetDatapoint(QWidget):
    edited = Signal()
    def __init__(self, value: list = None, labels_color: list = None):
        """A line of six float widgets (last 4 hidden by default)"""
        super().__init__()
        # Variables
        self.value: list = []
        if value is None:
            value = [0,0, 0,0,2,3]
        debug(f"CurveWidgetDatapoint value: {value}")

        if labels_color is None:
            labels_color = ['#FFFFFF', '#FFFFFF']
        # Init layout
        self.layout_horizontal = QHBoxLayout()
        self.setLayout(self.layout_horizontal)
        self.curve_points = []

        for index in range(len(value)):
            if index == 0:
                self.create_widget_control(value[index], False, labels_color[0])
            elif index == 1:
                self.create_widget_control(value[index], False, labels_color[1])
            else:
                self.curve_points.append(value[index])



        # Curve button
        self.edit_curve_button = Button()
        self.edit_curve_button.set_icon_polyline()
        self.edit_curve_button.clicked.connect(lambda : self.show_curve_editor(self.curve_points))
        self.layout().addWidget(self.edit_curve_button)

        # Delete button
        self.delete_button = DeleteButton(self)
        self.layout().addWidget(self.delete_button)


        self.on_update()

        # Fixed height of property
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)
    def show_curve_editor(self, values):
        self.curve_editor = CurveEditor(values[0], values[1], values[2], values[3])
        self.curve_editor.edited.connect(self.set_curvature_points)
        self.curve_editor.show()
    def set_curvature_points(self, values):
        self.curve_points = values
        self.on_update()
    def create_widget_control(self, value: float, hidden: bool, color: str):
        """Creating float widget with value and adding"""
        float_instance = FloatWidget(value=value, spacer_enable=False)
        # float_instance.setStyleSheet(f"color:{color};")
        float_instance.set_color(color)
        float_instance.on_Slider_updated()
        float_instance.edited.connect(self.on_update)
        if hidden:
            float_instance.hide()
        self.layout().addWidget(float_instance)

    def on_update(self):
        self.value = self.get_value()
        self.edited.emit()

    def get_value(self):
        """
        Getting value

        returns: list
        """
        __data = []
        for index in range(self.layout().count()):
            widget = self.layout().itemAt(index).widget()
            if isinstance(widget, FloatWidget):
                __value = widget.value
                __data.append(__value)
        for point in self.curve_points:
            __data.append(point)
        debug(f'getting value widget control curve property, data: {__data}')
        return __data
    def closeEvent(self, event):
        self.value = None
        self.edited.emit()
        self.deleteLater()
    def hide_widget_controls(self):
        """
        Hides widget controls. I don't know what does last four numbers mean, so let's just hide them.

        --Tmp--

        """
        for index in range(self.layout().count()):
            if index >= 2:
             self.layout().itemAt(index).widget().hide()

    def show_widget_controls(self):
        """
        Showing widget controls

        --Tmp--

        """
        for index in range(self.layout().count()):
            if index >= 2:
             self.layout().itemAt(index).widget().show()

class SoundEventEditorPropertyEditLine(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: str = None, tree: QTreeWidget = None, objects: list = None):
        """
        Combox property

        value : str
        """
        super().__init__(parent, label_text, value)

        self.tree: QTreeWidget = tree
        self.value_class = label_text
        self.objects = objects
        # Init combobox
        self.combobox = QLineEdit()
        self.combobox.setMinimumWidth(256)
        self.combobox.textChanged.connect(self.on_property_update)
        self.layout().addWidget(self.combobox)
        self.set_value(value)
        # if value == "None":
        #     pass
        # else:
        #     self.combobox.setCurrentText(str(value))


        # Init Search button
        self.search_button = Button()
        self.search_button.set_icon_search()
        self.search_button.setMaximumWidth(32)
        self.search_button.clicked.connect(self.call_search_popup_menu)
        self.layout().addWidget(self.search_button)
        self.on_property_update()

        # Init spacer
        spacer = Spacer()
        self.layout().addWidget(spacer)

        self.setContentsMargins(0,0,0,0)
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)

    def init_combobox(self):
        pass
    def set_value(self, value: str):
        self.combobox.setText(str(value))

    def on_property_update(self):
        """Send signal that user changed the property"""
        value = self.combobox.text()
        self.value_update(value)
        self.edited.emit()

    def value_update(self, value):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        self.value = {self.value_class: value}
    def init_label_color(self):
        return "#F4A9F6"

    def call_search_popup_menu(self):
        elements = []
        for item in self.objects:
            __element = {item:item}
            elements.append(__element)
        self.popup_menu = PopupMenu(elements, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
        self.popup_menu.show()
class SoundEventEditorPropertyBaseLegacy(SoundEventEditorPropertyEditLine):
    def __init__(self, parent=None, label_text: str = None, value: str = None, tree: QTreeWidget = None, objects: list = None):
        """
        Combox property

        value : str
        """
        super().__init__(parent, label_text, value, tree, objects)

    def get_soundenvets(self, elements_dict = False):
        elements = []
        tree_root = self.tree.invisibleRootItem()
        for index in range(tree_root.childCount()):
            __tree_item = tree_root.child(index)
            __name = __tree_item.text(0)
            if elements_dict:
                __element = {__name: __name}
            else:
                __element = __name
            elements.append(__element)
        return elements
    def call_search_popup_menu(self):
        if self.tree is None:
            pass
        else:
            elements = self.get_soundenvets(elements_dict=True)
            self.popup_menu = PopupMenu(elements, add_once=False)
            self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
            self.popup_menu.show()
    def init_label_color(self):
        return "#8684b8"

class ListElement(QWidget):
    edited = Signal()
    def __init__(self, value: str = None):
        """A line of six float widgets (last 4 hidden by default)"""
        super().__init__()
        # Variables
        self.value: list = []
        if value is None:
            value: str = "None"
        # Init layout
        self.layout_horizontal = QHBoxLayout()
        self.setLayout(self.layout_horizontal)

        # Init editline
        self.editline = QLineEdit()
        self.editline.setPlaceholderText("Type...")
        if value == "None":
            pass
        else:
            self.editline.setText(str(value))
        self.editline.textChanged.connect(self.on_update)
        self.layout().addWidget(self.editline)


        # Init Search button
        self.search_button = Button()
        self.search_button.set_icon_search()
        self.search_button.clicked.connect(self.call_search_popup_menu)
        self.layout().addWidget(self.search_button)

        # Init delete button
        self.delete_button = DeleteButton(self)
        self.layout().addWidget(self.delete_button)
        self.on_update()

        self.setContentsMargins(0,0,0,0)
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)

    def set_value(self, value: str = None):
        """Sets editline value"""
        self.editline.setText(str(value))

    def call_search_popup_menu(self):
        elements = []
        self.popup_menu = PopupMenu(elements, add_once=True)
        self.popup_menu.exec()

    def on_update(self):
        self.value = self.get_value()
        self.edited.emit()
    def get_value(self):
        return self.editline.text()
    def closeEvent(self, event):
        self.value = None
        self.edited.emit()
        self.deleteLater()
class FileElement(ListElement):
    def __init__(self, value: str = None):
        super().__init__(value)
    def call_search_popup_menu(self):
        elements = []
        __sounds_path = os.path.join(get_addon_dir(), 'sounds')
        __addon_path = get_addon_dir()
        for dirpath, dirnames, filenames in os.walk(__sounds_path):
            for filename in filenames:
                __filepath = os.path.join(dirpath, filename)
                __filepath = vsnd_filepath_convert(__filepath)

                __element = {filename: __filepath}
                elements.append(__element)
        self.popup_menu = PopupMenu(elements, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
        self.popup_menu.show()
class SoundEventElement(ListElement):
    def __init__(self, value: str = None, tree: QTreeWidget = None):
        super().__init__(value)
        self.tree = tree

    def call_search_popup_menu(self):
        if self.tree is None:
            pass
        else:
            elements = []
            tree_root = self.tree.invisibleRootItem()
            for index in range(tree_root.childCount()):
                __tree_item = tree_root.child(index)
                __name = __tree_item.text(0)
                __element = {__name:__name}
                elements.append(__element)
            self.popup_menu = PopupMenu(elements, add_once=False)
            self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
            self.popup_menu.show()