from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsWidget, QGraphicsPathItem
from PySide6.QtCore import QEasingCurve, Qt
from PySide6.QtGui import QPainterPath, QPen, QColor
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPathItem
from PySide6.QtWidgets import QGraphicsView, QGraphicsPathItem, QGraphicsScene
from PySide6.QtGui import QPainterPath
import numpy as np
from PySide6.QtCore import QEasingCurve, QRectF
from PySide6.QtGui import QPainterPath, QPen, QColor
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPathItem
import numpy as np
from scipy.interpolate import CubicSpline
from src.preferences import debug
from PySide6.QtCore import QEasingCurve
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Signal
from PySide6.QtGui import QPainterPath
import numpy as np
from src.preferences import debug
from src.common import convert_snake_case
from src.soudevent_editor.property.ui_curve import Ui_CurveWidget
from src.widgets import FloatWidget, LegacyWidget, BoolWidget, DeleteButton

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
    # def on_property_update(self):
    #     """Send signal that user changed the property"""
    #     self.value_update()
    #     self.edited.emit()
    # def value_update(self):
    #     """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
    #     self.value = {}
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
        return "#4CE4C7"

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
        return "#25A7BC"
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
        return "#BCB925"
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
        return "#D20103"

class SoundEventEditorPropertyCurve(QWidget):
    edited = Signal()
    def __init__(self, parent=None, label_text: str = None, value: dict = None, labels: list=None):
        """
        Bool property

        value : dict
        """
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
        # Set widget size according to datapoint count
        # connections
        self.ui.add_data_point_button.clicked.connect(lambda : self.add_datapoint())

    def add_datapoint(self, value: list = None):
        """Adding datapoint"""
        if value is None:
            value = [0,0, 0,0,2,3]
        self.datapoint_instance = CurveWidgetDatapoint(value=value, labels_color=self.labels_color)
        self.datapoint_instance.edited.connect(self.on_property_update)
        self.ui.datapoints_layout.addWidget(self.datapoint_instance)
        self.on_property_update()
    def on_property_update(self):
        """Send signal that user changed the property"""
        __value = []
        for index in range(self.ui.datapoints_layout.count()):
            widget = self.ui.datapoints_layout.itemAt(index).widget()
            if isinstance(widget, CurveWidgetDatapoint):
                __list = widget.value
                if isinstance(__list, list):
                    __value.append(__list)
                debug(f'on_property_update: widget:{widget}, value:{__value}')
        self.value_update(__value)
        self.set_widget_size(__value)
        self.preview_update(__value)
        self.edited.emit()


    def value_update(self, value):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        self.value = {self.value_class: value}

    def set_widget_size(self, __value):
        """Set maximum height"""
        # height = self.ui.datapoints_layout.count()
        count = len(__value)

        height = count * 48 + 256
        debug(f"set_widget_size, height: {height}")
        self.setMaximumHeight(height)
        self.setMinimumHeight(height)
    def preview_update(self, values):
        """
        Updates the preview with the given values.
        :param values: A list of y-values representing the curve data points.
        """
        if not values or not isinstance(values, list) or len(values) < 2:
            raise ValueError("Invalid input: 'values' must be a list with at least 2 values.")

        print(f"preview_update: values to process: {values}")

        # Ensure the scene is set up
        self.setup_scene()

        # Draw the curve using the given values
        self.preview_curve(values=[0,6,8], widget=self.ui.graphicsView_01)

    def setup_scene(self):
        """
        Ensures the graphics view has an associated scene and disables scrolling.
        """
        if self.ui.graphicsView_01.scene() is None:
            scene = QGraphicsScene()
            self.ui.graphicsView_01.setScene(scene)

        # Disable scrollbars to prevent unwanted scrolling
        self.ui.graphicsView_01.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.graphicsView_01.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def scale_values(self, values, width, height):
        """
        Scales the given y-values to fit within the widget's height.
        :param values: List of y-values to scale.
        :param width: The width of the widget.
        :param height: The height of the widget.
        :return: Tuple of scaled x and y values.
        """
        # Generate x values evenly spaced across the widget's width
        x_values = [i * (width / (len(values) - 1)) for i in range(len(values))]

        # Flip y-values for Qt's coordinate system and clamp within the widget's height
        y_values = [max(0, min(height, height - y)) for y in values]

        return x_values, y_values

    def preview_curve(self, values=None, widget=None):
        """
        Renders a sharp, linear curve based on the given values in the specified widget.
        :param values: List of y-values for the curve.
        :param widget: QGraphicsView widget to render the curve on.
        """
        if widget is None:
            raise ValueError("Widget cannot be None")
        if values is None or len(values) < 2:
            raise ValueError("Values list must contain at least two elements")

        # Get the size of the widget's viewport
        viewport_size = widget.viewport().size()
        width = viewport_size.width()
        height = viewport_size.height()

        # Set the scene size to match the widget's viewport
        widget.scene().setSceneRect(0, 0, width, height)

        # Scale x and y values to fit the widget
        x_values, y_values = self.scale_values(values, width, height)

        # Create a QPainterPath for the curve
        path = QPainterPath()
        path.moveTo(x_values[0], y_values[0])
        for x, y in zip(x_values[1:], y_values[1:]):
            path.lineTo(x, y)

        # Create a QGraphicsPathItem to display the curve
        curve_item = QGraphicsPathItem(path)

        # Set the pen color and style for the curve
        pen = QPen(QColor("gray"))
        pen.setWidth(2)  # Optional: Adjust the width of the curve
        curve_item.setPen(pen)

        # Clear the scene before adding the new curve to avoid overlaps
        scene = widget.scene()
        scene.clear()
        scene.addItem(curve_item)

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

        for index in range(len(value)):
            if index == 1:
                self.create_widget_control(value[index], False, labels_color[0])
            elif index == 2:
                self.create_widget_control(value[index], False, labels_color[1])
            else:
                self.create_widget_control(value[index], True, '#FFFFFF')

        # Init delete button
        self.delete_button = DeleteButton(self)
        self.layout().addWidget(self.delete_button)
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