import sys
import pyqtgraph as pg
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QMessageBox, QFrame)
from PySide6.QtCore import Signal, Qt
from src.widgets import BoxSlider
from src.soundevent_editor.property.curve.algorithm import (CurvePoint,
                                                          setup_all_curve_values,
                                                          sample_curve)
from src.widgets_common import DeleteButton, Button
from src.soundevent_editor.property.curve.ui_main import Ui_CurveWidget


class DataPointItem(QWidget):
    edited = Signal()

    # Column configurations with customizable labels
    COLUMNS = [
        {"name": "distance", "label": "Distance", "step": 10, "digits": 3, "range": [0, 0], "sensitivity": 1.0},
        {"name": "volume", "label": "Volume", "step": 1, "digits": 3, "range": [0, 0], "sensitivity": 0.2},
        {"name": "slope_left", "label": "Slope Left", "step": 0.001, "digits": 3, "range": [-2, 2], "sensitivity": 0.01},
        {"name": "slope_right", "label": "Slope Right", "step": 0.001, "digits": 3, "range": [-2, 2], "sensitivity": 0.01},
        {"name": "mode_left", "label": "Mode Left", "step": 0.1, "digits": 0, "range": [0, 4], "sensitivity": 1.0},
        {"name": "mode_right", "label": "Mode Right", "step": 0.1, "digits": 0, "range": [0, 4], "sensitivity": 1.0}
    ]

    def __init__(self, values, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.values = values.copy() if values else [0, 0, 0, 0, 2, 3]
        self.float_widgets = []
        self.action_buttons = {}
        self.widget_map = {}
        self.setup_widgets()

    def setup_widgets(self):
        """Setup BoxSlider widgets and action buttons with proper mapping"""
        layouts = [
            self.parent_widget.ui.value_01,
            self.parent_widget.ui.value_02,
            self.parent_widget.ui.value_03,
            self.parent_widget.ui.value_04,
            self.parent_widget.ui.value_05,
            self.parent_widget.ui.value_06
        ]

        # Create and map float widgets
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
            self.widget_map[float_widget] = layout

        # Setup action buttons
        self.setup_action_buttons()

    def setup_action_buttons(self):
        """Setup delete and duplicate buttons within a dedicated frame."""

        # Create a frame for action buttons
        self.action_buttons_frame = QFrame(self)
        self.action_buttons_frame.setMaximumWidth(64)
        self.action_buttons_frame.setFrameShape(QFrame.NoFrame)
        self.action_buttons_frame.setContentsMargins(0, 0, 0, 0)  # Set margins to 0
        action_buttons_layout = QHBoxLayout(self.action_buttons_frame)
        action_buttons_layout.setContentsMargins(0, 0, 0, 0)
        action_buttons_layout.setSpacing(0)  # Remove spacing between buttons
        self.parent_widget.ui.actions.addWidget(self.action_buttons_frame)

        # Delete button
        delete_button = DeleteButton(self)
        delete_button.set_size(24, 24)
        delete_button.clicked.connect(self.delete_item)
        action_buttons_layout.addWidget(delete_button)
        self.action_buttons['delete'] = delete_button
        self.widget_map[delete_button] = action_buttons_layout  # Map to the new layout

        # Duplicate button
        duplicate_button = Button()
        duplicate_button.set_size(24, 24)
        duplicate_button.set_icon_paste()
        duplicate_button.clicked.connect(self.duplicate_item)
        action_buttons_layout.addWidget(duplicate_button)
        self.action_buttons['duplicate'] = duplicate_button
        self.widget_map[duplicate_button] = action_buttons_layout  # Map to the new layout

    def on_edited(self):
        """Handle value editing"""
        self.edited.emit()

    def get_values(self):
        """Get current values from all widgets"""
        return [widget.value for widget in self.float_widgets]

    def duplicate_item(self):
        """Create a duplicate of this datapoint"""
        if self.parent_widget:
            values = self.get_values()
            self.parent_widget.add_datapoint(values)

    def delete_item(self):
        """Remove this item and its associated widgets from parent"""
        if self.parent_widget:
            # Remove from parent's datapoint items list
            self.parent_widget.datapoint_items.remove(self)

            # Remove all widgets from their respective layouts
            for widget, layout in self.widget_map.items():
                layout.removeWidget(widget)
                widget.deleteLater()

            # Update the graph
            self.parent_widget.plot_graph()

            # Delete the item itself
            self.deleteLater()

    def cleanup(self):
        """Explicit cleanup method"""
        for widget in self.widget_map.keys():
            widget.setParent(None)
            widget.deleteLater()
        self.widget_map.clear()
        self.float_widgets.clear()
        self.action_buttons.clear()


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

    def __init__(self, parent=None, label_text: str = None, value: dict = None, labels=None):
        super().__init__(parent)
        self.ui = Ui_CurveWidget()
        self.ui.setupUi(self)
        self.value_class = label_text
        self.datapoint_items = []
        self.points = []

        # Update labels if provided
        if labels:
            self.update_labels(labels)

        self.setup_graph()
        self.setup_connections()

        # Initialize with provided values
        if value:
            self.value_update(value)
            for point_values in value:
                self.add_datapoint(point_values)
            self.on_property_update()

    def update_labels(self, labels):
        """Update column labels"""
        if isinstance(labels, dict):
            if 'distance' in labels:
                self.ui.label_01.setText(labels['distance'])
            if 'volume' in labels:
                self.ui.label_02.setText(labels['volume'])

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
            pass

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