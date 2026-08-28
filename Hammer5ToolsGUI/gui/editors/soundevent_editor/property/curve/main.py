import logging

import pyqtgraph as pg
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QFrame)
from PySide6.QtCore import Signal, Qt, QEvent
from gui.styles import theme
from gui.widgets import BoxSlider
from gui.editors.soundevent_editor.property.curve.algorithm import (CurvePoint, setup_all_curve_values, sample_curve)
from gui.widgets.common import DeleteButton, Button
from gui.editors.soundevent_editor.property.curve.ui_main import Ui_CurveWidget

log = logging.getLogger(__name__)


class DataPointItem(QWidget):
    edited = Signal()
    slider_pressed = Signal()   # emitted when any BoxSlider drag starts
    committed = Signal()        # emitted when any BoxSlider drag ends

    # Column configuration. Ranges follow what CS2 actually ships: across the
    # 105130 control points in pak01_dir.vpk, x and y are never negative, while
    # slopes are negative at ~20% of points and reach -10082, so a bounded slope
    # range would silently rewrite authored curves on save. [0, 0] means
    # unbounded in BoxSlider.
    COLUMNS = [
        {"name": "distance", "label": "Distance", "step": 1, "digits": 3, "range": [0, 0], "sensitivity": 1.0, "only_positive": True},
        {"name": "volume", "label": "Volume", "step": 0.1, "digits": 3, "range": [0, 0], "sensitivity": 0.2, "only_positive": True},
        {"name": "slope_left", "label": "Slope Left", "step": 0.01, "digits": 3, "range": [0, 0], "sensitivity": 0.1},
        {"name": "slope_right", "label": "Slope Right", "step": 0.01, "digits": 3, "range": [0, 0], "sensitivity": 0.1},
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
            sensitivity=column["sensitivity"],
            only_positive=column.get("only_positive", False),
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
        for widget in self.widgets['float_widgets']:
            layout = self.widgets['layouts'].get(widget)
            if layout:
                layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()

        for button in self.widgets['action_buttons'].values():
            button.setParent(None)
            button.deleteLater()

        # Clean up frames
        for frame in self.widgets['frames'].values():
            frame.setParent(None)
            frame.deleteLater()

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
    CURVE_WIDTH = 1.5
    AXIS_WIDTH = 2
    # Tangent arm length, as a share of the plotted x span. Only the slope is
    # stored, so the arm has no length of its own to preserve.
    HANDLE_FRACTION = 0.07
    ANCHOR_SIZE = 11
    HANDLE_SIZE = 8

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
        """Build the plot and its permanent graphics items.

        Every item below is created once and only ever re-fed with setData /
        setPos. Nothing is added or destroyed while the mouse is down, so a
        drag can never lose the item holding the grab.
        """
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setContextMenuPolicy(Qt.NoContextMenu)
        self.graph_widget.setAntialiasing(True)
        self.ui.verticalLayout_4.addWidget(self.graph_widget)

        self.plot_item = self.graph_widget.getPlotItem()
        self.plot_item.setMenuEnabled(False)
        self.plot_item.setMouseEnabled(x=False, y=False)
        self.plot_item.showGrid(x=True, y=True, alpha=self.GRID_ALPHA)

        self.curve_item = pg.PlotCurveItem()
        self.plot_item.addItem(self.curve_item)
        # connect='pairs' draws each consecutive point pair as its own segment,
        # so one item covers every tangent arm.
        self.arms_item = pg.PlotDataItem(connect='pairs')
        self.plot_item.addItem(self.arms_item)

        self._anchor_items = []                 # TargetItem per curve point
        self._handle_items = []                 # (left, right) TargetItem per point
        self._updating_items = False            # True while we drive setPos ourselves
        self._drag_active = False
        self._dragged_item = None

        self._apply_plot_theme()

    def _apply_plot_theme(self):
        """Repaint the plot from the active theme.

        pyqtgraph pens and brushes are plain objects the stylesheet never
        reaches, so they have to be re-made on every theme change.
        """
        colors = theme.get_theme()
        self.graph_widget.setBackground(colors.background)
        self.curve_item.setPen(pg.mkPen(colors.text_muted, width=self.CURVE_WIDTH))
        self.arms_item.setPen(pg.mkPen(colors.border_strong, width=1))
        self._style_targets()
        for axis in ["bottom", "left"]:
            self.plot_item.getAxis(axis).setPen(
                pg.mkPen(color=colors.border, width=self.AXIS_WIDTH)
            )
            self.plot_item.getAxis(axis).setTextPen(pg.mkPen(color=colors.text_muted))
        self.plot_graph()

    def changeEvent(self, event):
        super().changeEvent(event)
        # A live theme switch repolishes every widget, which lands here.
        if event.type() == QEvent.StyleChange:
            self._apply_plot_theme()

    def showEvent(self, event):
        super().showEvent(event)
        # Widgets built before the switch catch up the first time they show.
        self._apply_plot_theme()

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
            log.exception("Failed to plot curve %s", self.value_class)

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
        """Re-evaluate the spline and push it into the permanent items."""
        setup_all_curve_values(self.points, len(self.points))
        min_distance = min(self.distances_from_widgets)
        max_distance = max(self.distances_from_widgets)

        step = (max_distance - min_distance) / self.CURVE_STEPS
        distances = [min_distance + step * i
                    for i in range(self.CURVE_STEPS + 1)]
        volumes = [sample_curve(d, self.points, len(self.points))
                  for d in distances]

        self.curve_item.setData(distances, volumes)
        self._apply_view_range(min_distance, max_distance)
        self._sync_handle_items()
        self._position_handle_items()

    def _apply_view_range(self, min_distance: float, max_distance: float):
        """Pin the axes to the authored range instead of the sampled one.

        The spline overshoots between control points, so an auto-ranging view
        rescales on every mouse move during a drag. CS2 never authors a
        negative x or y, so the axes are clipped at zero and the overshoot is
        simply drawn off the bottom.
        """
        top = max([1.0] + [item.get_values()[1] for item in self.datapoint_items])
        self._view_top = top
        self.plot_item.disableAutoRange()
        self.plot_item.setXRange(min_distance, max_distance, padding=0.02)
        self.plot_item.setYRange(0.0, top, padding=0.05)

    # --- editable anchors and tangent handles ---

    def _handle_length(self) -> float:
        """Tangent arm length in x units."""
        if not self.distances_from_widgets:
            return 1.0
        span = max(self.distances_from_widgets) - min(self.distances_from_widgets)
        return (span or 1.0) * self.HANDLE_FRACTION

    def _handle_offset(self, slope: float) -> tuple:
        """Arm offset for a slope, shortened so a steep tangent stays on screen.

        Only the direction carries meaning — the stored value is a slope, not a
        handle position — so a slope of -10082 is drawn as a short steep arm
        rather than one that leaves the plot.
        """
        dx = self._handle_length()
        dy = dx * slope
        limit = getattr(self, '_view_top', 1.0) * 0.25
        if limit and abs(dy) > limit:
            scale = limit / abs(dy)
            dx *= scale
            dy *= scale
        return dx, dy

    def _make_target(self, size: int, symbol: str):
        target = pg.TargetItem(pos=(0, 0), size=size, symbol=symbol, movable=True)
        self.plot_item.addItem(target)
        return target

    def _sync_handle_items(self):
        """Grow or shrink the item pool to match the number of curve points.

        Only ever called between gestures — the count cannot change mid-drag.
        """
        while len(self._anchor_items) > len(self.points):
            anchor = self._anchor_items.pop()
            left, right = self._handle_items.pop()
            for item in (anchor, left, right):
                self.plot_item.removeItem(item)

        while len(self._anchor_items) < len(self.points):
            index = len(self._anchor_items)
            anchor = self._make_target(self.ANCHOR_SIZE, 'o')
            left = self._make_target(self.HANDLE_SIZE, 's')
            right = self._make_target(self.HANDLE_SIZE, 's')
            anchor.sigPositionChanged.connect(
                lambda _item, i=index: self._on_anchor_moved(i))
            left.sigPositionChanged.connect(
                lambda _item, i=index: self._on_handle_moved(i, 'left'))
            right.sigPositionChanged.connect(
                lambda _item, i=index: self._on_handle_moved(i, 'right'))
            for item in (anchor, left, right):
                item.sigPositionChangeFinished.connect(self._on_drag_finished)
            self._anchor_items.append(anchor)
            self._handle_items.append((left, right))
        self._style_targets()

    def _style_targets(self):
        """Repaint anchors and handles from the active theme."""
        colors = theme.get_theme()
        for anchor in self._anchor_items:
            anchor.setPen(pg.mkPen(colors.accent, width=2))
            anchor.setBrush(pg.mkBrush(colors.accent))
        for left, right in self._handle_items:
            for handle in (left, right):
                handle.setPen(pg.mkPen(colors.text_muted, width=2))
                handle.setBrush(pg.mkBrush(colors.surface_raised))

    def _position_handle_items(self):
        """Place every anchor and handle, and redraw the arms between them.

        The item under the mouse keeps the position pyqtgraph gave it —
        it recomputes that from the cursor on every move, so moving it here
        would only fight the gesture — and the arm is drawn to where it
        actually is, not to where its slope would otherwise put it.
        """
        arm_x, arm_y = [], []
        self._updating_items = True
        try:
            for index, item in enumerate(self.datapoint_items):
                values = item.get_values()
                x, y = values[0], values[1]
                left_dx, left_dy = self._handle_offset(values[2])
                right_dx, right_dy = self._handle_offset(values[3])

                anchor = self._anchor_items[index]
                left, right = self._handle_items[index]
                placed = {}
                for target, pos in (
                    (anchor, (x, y)),
                    (left, (x - left_dx, y - left_dy)),
                    (right, (x + right_dx, y + right_dy)),
                ):
                    if target is self._dragged_item:
                        point = target.pos()
                        placed[target] = (float(point.x()), float(point.y()))
                    else:
                        target.setPos(pos)
                        placed[target] = pos

                origin = placed[anchor]
                for end in (placed[left], placed[right]):
                    arm_x.extend([end[0], origin[0]])
                    arm_y.extend([end[1], origin[1]])
        finally:
            self._updating_items = False
        self.arms_item.setData(arm_x, arm_y)

    def _column(self, index: int, column: int, value: float):
        """Write one datapoint column. Signals stay suppressed during a drag."""
        self.datapoint_items[index].widgets['float_widgets'][column].set_value(value)

    def _clamp_x(self, index: int, x: float) -> float:
        """Keep the points monotonic in x and non-negative, as CS2 authors them."""
        values = [item.get_values()[0] for item in self.datapoint_items]
        margin = self._handle_length() * 0.05
        x = max(0.0, x)
        if index > 0:
            x = max(x, values[index - 1] + margin)
        if index < len(values) - 1:
            x = min(x, values[index + 1] - margin)
        return x

    def _slope_side(self, index: int, side: str) -> str:
        """Which slope a handle actually steers, given the point's modes.

        Mode 3 means that side is tied to the other one, so dragging it has to
        write the slope it mirrors or the drag would appear to do nothing.
        """
        values = self.datapoint_items[index].get_values()
        if side == 'right' and int(values[5]) == 3:
            return 'left'
        if side == 'left' and int(values[4]) == 3:
            return 'right'
        return side

    def _begin_drag(self, item):
        if self._drag_active:
            return
        self._drag_active = True
        self._dragged_item = item
        # One undo entry for the whole gesture, same contract as BoxSlider.
        self._suppress_signals = True
        self.slider_pressed.emit()

    def _on_drag_finished(self, _item=None):
        if not self._drag_active:
            return
        self._drag_active = False
        self._dragged_item = None
        self._suppress_signals = False
        self.on_property_update()
        self.committed.emit()

    def _redraw_during_drag(self):
        self._collect_points()
        if self._validate_points():
            self._calculate_and_draw_curve()

    def _on_anchor_moved(self, index: int):
        if self._updating_items or index >= len(self.datapoint_items):
            return
        anchor = self._anchor_items[index]
        self._begin_drag(anchor)
        position = anchor.pos()
        self._column(index, 0, self._clamp_x(index, float(position.x())))
        self._column(index, 1, max(0.0, float(position.y())))
        self._redraw_during_drag()

    def _on_handle_moved(self, index: int, side: str):
        if self._updating_items or index >= len(self.datapoint_items):
            return
        handle = self._handle_items[index][0 if side == 'left' else 1]
        self._begin_drag(handle)

        values = self.datapoint_items[index].get_values()
        anchor_x, anchor_y = values[0], values[1]
        position = handle.pos()
        # Guard against a division by zero when the handle is dragged onto or
        # past its anchor.
        floor = self._handle_length() * 0.02
        if side == 'left':
            slope = (anchor_y - float(position.y())) / max(anchor_x - float(position.x()), floor)
        else:
            slope = (float(position.y()) - anchor_y) / max(float(position.x()) - anchor_x, floor)

        target = self._slope_side(index, side)
        slope_column = 2 if target == 'left' else 3
        mode_column = 4 if target == 'left' else 5
        self._column(index, slope_column, slope)
        # Modes 0, 1 and 4 derive the slope and would discard the drag, so
        # dragging switches that side to the authored mode.
        if int(values[mode_column]) != 2:
            self._column(index, mode_column, 2)
        self._redraw_during_drag()

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
