import sys
import pyqtgraph as pg
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QMessageBox)
from PySide6.QtCore import Signal, Qt
from src.widgets import BoxSlider
from src.soundevent_editor.property.curve.algorithm import (CurvePoint,
                                                          setup_all_curve_values,
                                                          sample_curve)
from src.widgets_common import DeleteButton
from src.soundevent_editor.property.curve.ui_main import Ui_CurveWidget


class DataPointItem(QWidget):
    edited = Signal()

    # Column configurations
    COLUMNS = [
        {"name": "value_01", "step": 10, "digits": 3, "range": [0, 0], "sensitivity": 1.0},
        {"name": "value_02", "step": 1, "digits": 3, "range": [0, 0], "sensitivity": 0.2},
        {"name": "value_03", "step": 0.001, "digits": 3, "range": [-2, 2], "sensitivity": 0.01},
        {"name": "value_04", "step": 0.001, "digits": 3, "range": [-2, 2], "sensitivity": 0.01},
        {"name": "value_05", "step": 0.1, "digits": 0, "range": [0, 4], "sensitivity": 1.0},
        {"name": "value_06", "step": 0.1, "digits": 0, "range": [0, 4], "sensitivity": 1.0}
    ]

    def __init__(self, values, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.values = values
        self.float_widgets = []
        self.setup_widgets()

    def setup_widgets(self):
        """Setup BoxSlider widgets in the appropriate layouts"""
        layouts = [
            self.parent_widget.ui.value_01,
            self.parent_widget.ui.value_02,
            self.parent_widget.ui.value_03,
            self.parent_widget.ui.value_04,
            self.parent_widget.ui.value_05,
            self.parent_widget.ui.value_06
        ]

        for value, column, layout in zip(self.values, self.COLUMNS, layouts):
            float_widget = BoxSlider(
                slider_scale=2,
                slider_range=column["range"],
                value_step=column["step"],
                digits=column["digits"],
                sensitivity=column["sensitivity"]
            )
            float_widget.set_value(value)
            float_widget.edited.connect(self.on_edited)
            layout.addWidget(float_widget)
            self.float_widgets.append(float_widget)

        # Add delete button to actions layout
        delete_button = DeleteButton(self)
        delete_button.set_size(24, 24)
        delete_button.clicked.connect(self.delete_item)
        self.parent_widget.ui.actions.addWidget(delete_button)

    def on_edited(self):
        """Handle value editing"""
        self.edited.emit()

    def get_values(self):
        """Get current values from all widgets"""
        return [widget.value for widget in self.float_widgets]

    def delete_item(self):
        """Remove this item from parent"""
        if self.parent_widget:
            self.parent_widget.datapoint_items.remove(self)
            # Clean up only this item's widgets
            for widget in self.float_widgets:
                widget.deleteLater()
            # Remove only this item's widgets from layouts
            for layout in [
                self.parent_widget.ui.value_01,
                self.parent_widget.ui.value_02,
                self.parent_widget.ui.value_03,
                self.parent_widget.ui.value_04,
                self.parent_widget.ui.value_05,
                self.parent_widget.ui.value_06,
                self.parent_widget.ui.actions
            ]:
                # Find and remove only this item's widget from each layout
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget() and item.widget() in self.float_widgets + [self.findChild(DeleteButton)]:
                        item.widget().deleteLater()
                        break
            self.parent_widget.plot_graph()
        self.deleteLater()


class SoundEventEditorPropertyCurve(QWidget):
    edited = Signal()

    # Constants
    MIN_POINTS_REQUIRED = 2
    CURVE_STEPS = 200
    GRID_ALPHA = 0.3
    CURVE_COLOR = '#7F7F7F'
    CURVE_WIDTH = 1.5
    BACKGROUND_COLOR = '#1C1C1C'
    AXIS_COLOR = '#232323'
    AXIS_WIDTH = 2

    def __init__(self, parent=None, label_text: str = None, value: dict = None, labels = None):
        super().__init__(parent)
        self.ui = Ui_CurveWidget()
        self.ui.setupUi(self)
        self.value_class = label_text
        self.datapoint_items = []
        self.points = []

        self.setup_graph()
        self.setup_connections()

        # Initialize with provided values
        if value:
            self.value_update(value)
            for point_values in value:
                self.add_datapoint(point_values)
            self.on_property_update()

    def value_update(self, value):
        """Update the widget's value"""
        self.value = {self.value_class: value}

    def setup_graph(self):
        """Setup the graph widget with proper styling"""
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setAntialiasing(True)
        self.graph_widget.setBackground(self.BACKGROUND_COLOR)
        self.ui.verticalLayout_4.addWidget(self.graph_widget)

        self.plot_item = self.graph_widget.getPlotItem()
        self.plot_item.showGrid(x=True, y=True, alpha=self.GRID_ALPHA)

        for axis in ["bottom", "left"]:
            self.plot_item.getAxis(axis).setPen(
                pg.mkPen(color=self.AXIS_COLOR, width=self.AXIS_WIDTH)
            )

    def setup_connections(self):
        """Setup widget connections"""
        self.ui.add_data_point_button.clicked.connect(
            lambda: self.add_datapoint()
        )

    def plot_graph(self):
        """Plot the curve based on current datapoints"""
        try:
            self._collect_points()
            if not self._validate_points():
                return
            self._calculate_and_draw_curve()
        except Exception:
            pass  # Silently handle errors

    def _collect_points(self):
        """Collect points from all datapoint widgets"""
        self.points = []
        self.distances_from_widgets = []

        for item in self.datapoint_items:
            values = item.get_values()
            point = CurvePoint(*values)
            self.points.append(point)
            self.distances_from_widgets.append(values[0])

    def _validate_points(self):
        """Validate collected points"""
        return bool(self.distances_from_widgets and len(self.points) >= self.MIN_POINTS_REQUIRED)

    def _calculate_and_draw_curve(self):
        """Calculate and draw the curve"""
        setup_all_curve_values(self.points, len(self.points))
        min_distance = min(self.distances_from_widgets)
        max_distance = max(self.distances_from_widgets)

        step = (max_distance - min_distance) / self.CURVE_STEPS
        distances = [min_distance + step * i
                    for i in range(self.CURVE_STEPS + 1)]
        volumes = [sample_curve(d, self.points, len(self.points))
                  for d in distances]

        self.plot_item.clear()
        self.plot_item.plot(
            distances,
            volumes,
            pen=pg.mkPen(self.CURVE_COLOR, width=self.CURVE_WIDTH)
        )

    def add_datapoint(self, values: list = None):
        """Add a new datapoint to the curve"""
        values = values or [0, 0, 0, 0, 2, 3]
        datapoint = DataPointItem(values=values, parent=self)
        datapoint.edited.connect(self.on_property_update)
        self.datapoint_items.append(datapoint)
        self.on_property_update()

    def on_property_update(self):
        """Handle updates to curve properties"""
        values = [item.get_values() for item in self.datapoint_items]
        self.value_update(values)
        self.plot_graph()
        self.edited.emit()

    def resizeEvent(self, event):
        """Handle widget resize events"""
        self.on_property_update()
        super().resizeEvent(event)