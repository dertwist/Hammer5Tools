import pyqtgraph as pg
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QFrame)
from PySide6.QtCore import Signal, Qt
from src.widgets import BoxSlider
from src.editors.soundevent_editor.property.curve.algorithm import (CurvePoint, setup_all_curve_values, sample_curve)
from src.widgets.common import DeleteButton, Button
from src.editors.soundevent_editor.property.curve.ui_main import Ui_CurveWidget


class DataPointItem(QWidget):
    edited = Signal()
    slider_pressed = Signal()   # emitted when any BoxSlider drag starts
    committed = Signal()        # emitted when any BoxSlider drag ends

    # Column configurations with customizable labels
    COLUMNS = [
        {"name": "distance", "label": "Distance", "step": 1, "digits": 3, "range": [0, 0], "sensitivity": 1.0},
        {"name": "volume", "label": "Volume", "step": 0.1, "digits": 3, "range": [0, 0], "sensitivity": 0.2},
        {"name": "slope_left", "label": "Slope Left", "step": 0.01, "digits": 3, "range": [-10, 10],"sensitivity": 0.1},
        {"name": "slope_right", "label": "Slope Right", "step": 0.01, "digits": 3, "range": [-10, 10],"sensitivity": 0.1},
        {"name": "mode_left", "label": "Mode Left", "step": 0.1, "digits": 0, "range": [0, 4], "sensitivity": 1.0},
        {"name": "mode_right", "label": "Mode Right", "step": 0.1, "digits": 0, "range": [0, 4], "sensitivity": 1.0}
    ]

    def __init__(self, values, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.values = values.copy() if values else [0, 0, 0, 0, 2, 3]
        self.widgets = {
            'float_widgets': [],
            'action_buttons': {},
            'layouts': {},
            'frames': {}
        }
        # Default: not suppressing signals. Parent widget may toggle this flag during bulk population
        self._suppress_signals = False
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
            float_widget = self._create_float_widget(value, column)
            layout.addWidget(float_widget)
            self.widgets['float_widgets'].append(float_widget)
            self.widgets['layouts'][float_widget] = layout

        self.setup_action_buttons()

    def _create_float_widget(self, value, column):
        """Create a BoxSlider widget with specified parameters"""
        float_widget = BoxSlider(
            slider_scale=2,
            slider_range=column["range"],
            value_step=column["step"],
            digits=column["digits"],
            sensitivity=column["sensitivity"]
        )
        # If parent is in bulk-populate mode, block signals while setting initial value to avoid spurious edits
        parent_suppress = getattr(self.parent_widget, '_suppress_signals', False)
        if parent_suppress:
            float_widget.blockSignals(True)

        float_widget.set_value(value)

        # Connect signals after initial set_value
        float_widget.edited.connect(self.on_edited)
        float_widget.slider_pressed.connect(self.slider_pressed)
        float_widget.committed.connect(self.committed)

        if parent_suppress:
            # Re-enable normal signal delivery for user interactions after setup
            float_widget.blockSignals(False)
        return float_widget

    def setup_action_buttons(self):
        """Setup delete and duplicate buttons within a dedicated frame"""
        action_frame = self._create_action_frame()
        action_layout = QHBoxLayout(action_frame)
        self._setup_action_layout(action_layout)

        delete_button = self._create_delete_button()
        duplicate_button = self._create_duplicate_button()

        action_layout.addWidget(delete_button)
        action_layout.addWidget(duplicate_button)

        self.widgets['action_buttons'].update({
            'delete': delete_button,
            'duplicate': duplicate_button
        })
        self.widgets['frames']['action'] = action_frame
        self.widgets['layouts']['action'] = action_layout

    def _create_action_frame(self):
        """Create and configure the action buttons frame"""
        frame = QFrame(self)
        frame.setMaximumWidth(64)
        frame.setFrameShape(QFrame.NoFrame)
        frame.setContentsMargins(0, 0, 0, 0)
        self.parent_widget.ui.actions.addWidget(frame)
        return frame

    def _setup_action_layout(self, layout):
        """Configure the action buttons layout"""
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

    def _create_delete_button(self):
        """Create and configure the delete button"""
        button = DeleteButton(self)
        button.set_size(30, 30)
        button.clicked.connect(self.delete_item)
        return button

    def _create_duplicate_button(self):
        """Create and configure the duplicate button"""
        button = Button()
        button.set_size(30, 30)
        button.set_icon_paste()
        button.clicked.connect(self.duplicate_item)
        return button

    def on_edited(self):
        """Handle value editing"""
        # Respect parent suppression flag (set during programmatic population or undo/redo restore)
        if getattr(self.parent_widget, '_suppress_signals', False) or getattr(self, '_suppress_signals', False):
            return
        self.edited.emit()

    def get_values(self):
        """Get current values from all widgets"""
        return [widget.value for widget in self.widgets['float_widgets']]

    def duplicate_item(self):
        """Create a duplicate of this datapoint"""
        if self.parent_widget:
            values = self.get_values()
            self.parent_widget.add_datapoint(values)

    def delete_item(self):
        """Remove this item and its associated widgets"""
        if self.parent_widget:
            # remove from parent's list and UI, then trigger parent to update state
            try:
                self.parent_widget.datapoint_items.remove(self)
            except ValueError:
                pass
            self.cleanup()
            # Allow deletion to be handled as a user action (so it can be captured by undo)
            if not getattr(self.parent_widget, '_suppress_signals', False):
                self.parent_widget.plot_graph()
            else:
                # If in suppressed mode, still refresh graph but don't notify parent higher-level
                self.parent_widget.plot_graph()
            self.deleteLater()

    def cleanup(self):
        """Clean up all widgets and their layouts"""
        # Clean up float widgets
        for widget in self.widgets['float_widgets']:
            layout = self.widgets['layouts'].get(widget)
            if layout:
                layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()

        # Clean up action buttons
        for button in self.widgets['action_buttons'].values():
            button.setParent(None)
            button.deleteLater()

        # Clean up frames
        for frame in self.widgets['frames'].values():
            frame.setParent(None)
            frame.deleteLater()

        # Clear all widget collections
        for collection in self.widgets.values():
            if isinstance(collection, dict):
                collection.clear()
            elif isinstance(collection, list):
                collection.clear()


class SoundEventEditorPropertyCurve(QWidget):
    edited = Signal()
    slider_pressed = Signal()   # emitted when any datapoint BoxSlider drag starts
    committed = Signal()        # emitted when any datapoint BoxSlider drag ends

    # Constants
    MIN_POINTS_REQUIRED = 2
    CURVE_STEPS = 256
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

        # Flag used to suppress signals/undo pushes while programmatically populating or restoring state
        self._suppress_signals = False
        self.current_element_name = None

        # Update labels if provided
        if labels:
            self.update_labels(labels)

        self.setup_graph()
        self.setup_connections()

        # Initialize with provided values
        if value:
            self.value_update(value)
            for point_values in value:
                # When initializing from a value, suppress emitting edits (undo should not capture programmatic load)
                self._suppress_signals = True
                try:
                    self.add_datapoint(point_values)
                finally:
                    self._suppress_signals = False
            self.on_property_update()

    def update_labels(self, labels):
        """Update column labels"""
        self.ui.label_01.setText(labels[0])
        self.ui.label_02.setText(labels[1])

    def value_update(self, value):
        """Update the widget's value"""
        self.value = {self.value_class: value}

    def setup_graph(self):
        """Setup the graph widget with proper styling"""
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setContextMenuPolicy(Qt.NoContextMenu)
        self.graph_widget.setAntialiasing(True)
        self.graph_widget.setBackground(self.BACKGROUND_COLOR)
        self.ui.verticalLayout_4.addWidget(self.graph_widget)

        plot_item = self.graph_widget.getPlotItem()
        plot_item.setMenuEnabled(False)

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
        # Create datapoint. DataPointItem will internally block signals for initial value if parent is suppressing
        datapoint = DataPointItem(values=values, parent=self)
        # Wire up signals (these should be connected, but DataPointItem will avoid emitting during suppressed loads)
        datapoint.edited.connect(self.on_property_update)
        datapoint.slider_pressed.connect(self.slider_pressed)
        datapoint.committed.connect(self.committed)
        self.datapoint_items.append(datapoint)
        # Only notify outer systems if not suppressing (e.g., when user triggers changes)
        if not getattr(self, '_suppress_signals', False):
            self.on_property_update()
        else:
            # Still refresh the graph to reflect programmatic changes but do not emit the edited signal
            self.plot_graph()

    def on_property_update(self):
        """Handle updates to curve properties"""
        # If we are restoring state or programmatically populating, avoid emitting an edited signal
        values = [item.get_values() for item in self.datapoint_items]
        self.value_update(values)
        self.plot_graph()
        if not getattr(self, '_suppress_signals', False):
            self.edited.emit()

    def resizeEvent(self, event):
        """Handle widget resize events"""
        self.on_property_update()
        super().resizeEvent(event)

    # --- New API for context/undo handling ---
    def set_context_element(self, name: str):
        """Set the current element name/context for this property widget.

        This updates a visible label (plot title) so the user sees which element is being edited.
        Call this when the properties panel is switched to a new tree element.
        """
        self.current_element_name = name
        try:
            # Use the plot title to display current element and property class
            title = name if not self.value_class else f"{name} — {self.value_class}"
            self.plot_item.setTitle(title)
        except Exception:
            # If plot_item isn't ready or fails, ignore silently
            pass

    def begin_bulk_update(self):
        """Call before programmatic population/restoration to suppress undo/signal pushes."""
        self._suppress_signals = True

    def end_bulk_update(self):
        """Call after programmatic population/restoration to re-enable signal pushing."""
        self._suppress_signals = False
        # After finishing population, ensure UI and graph are in sync
        self.on_property_update()
