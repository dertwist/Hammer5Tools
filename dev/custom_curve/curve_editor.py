import sys
import pyqtgraph as pg
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QMessageBox, QLabel, QDoubleSpinBox
from PySide6.QtGui import Qt
from PySide6.QtCore import Signal
from src.widgets import FloatWidget
from dev.custom_curve.custom_curve import CurvePoint, setup_all_curve_values, sample_curve
from src.widgets_common import DeleteButton

DEFAULT_VALUES = [[20, 3, 0, 0, 2, 3], [260, 1, 0, 0, 2, 3]]

class DataPointItem(QWidget):
    edited = Signal()

    def __init__(self, values, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        self.float_widgets = []

        slider_ranges = [[-2, 2], [-2, 2], [-2, 2], [-2, 2], [0, 4], [0, 4]]
        int_outputs = [False, False, False, False, True, True]

        for value, slider_range, int_output in zip(values, slider_ranges, int_outputs):
            float_widget = FloatWidget(vertical=True, slider_scale=2, slider_range=slider_range, int_output=int_output)
            float_widget.SpinBox.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            float_widget.set_value(value)
            float_widget.Slider.setMinimumHeight(128)
            float_widget.edited.connect(self.on_edited)
            self.layout.addWidget(float_widget)
            self.float_widgets.append(float_widget)

        delete_button = DeleteButton(self)
        delete_button.clicked.connect(self.deleteLater)
        self.layout.addWidget(delete_button)

    def on_edited(self):
        self.edited.emit()

    def get_values(self):
        return [widget.value for widget in self.float_widgets]

class CurveGraphForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Distance-Volume Curve Graph")
        self.setStyleSheet("background-color: #2E2E2E; color: #FFFFFF;")

        self.points = []
        self.datapoint_items = []
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.init_ui()
        self.plot_graph()

    def init_ui(self):
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setBackground('#2E2E2E')
        self.main_layout.addWidget(self.graph_widget)
        self.plot_item = self.graph_widget.getPlotItem()
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.getAxis("bottom").setPen("white")
        self.plot_item.getAxis("left").setPen("white")

        self.add_column_labels()

        add_point_button = QPushButton("Add Point")
        add_point_button.setStyleSheet("background-color: #444444; color: #FFFFFF;")
        add_point_button.clicked.connect(self.add_point)
        self.main_layout.addWidget(add_point_button)

        for values in DEFAULT_VALUES:
            self.add_datapoint_item(values)

    def add_column_labels(self):
        label_layout = QHBoxLayout()
        texts = ['Distance', 'Volume', 'Slope Left', 'Slope Right', 'Mode Left', 'Mode Right']
        for text in texts:
            label = QLabel(text)
            label.setStyleSheet("color: #FFFFFF;")
            label_layout.addWidget(label)
        self.main_layout.addLayout(label_layout)

    def add_point(self):
        self.add_datapoint_item([0.0, 0.0, 0.0, 0.0, 0, 0])

    def add_datapoint_item(self, values):
        datapoint_item = DataPointItem(values, self)
        datapoint_item.edited.connect(self.plot_graph)
        self.main_layout.addWidget(datapoint_item)
        self.datapoint_items.append(datapoint_item)

    def plot_graph(self):
        self.points = []
        distances_from_widgets = []

        for item in self.datapoint_items:
            try:
                values = item.get_values()
                distance, volume, slopeLeft, slopeRight, modeLeft, modeRight = values

                point = CurvePoint(distance, volume, slopeLeft, slopeRight, modeLeft, modeRight)
                self.points.append(point)
                distances_from_widgets.append(distance)

            except (ValueError, AttributeError):
                QMessageBox.warning(self, "Invalid Input", "Invalid data in one of the datapoint items. Please check the values.")
                return

        if not distances_from_widgets:
            return

        min_distance = min(distances_from_widgets)
        max_distance = max(distances_from_widgets)

        setup_all_curve_values(self.points, len(self.points))

        # Optimization: Reduce the number of points plotted, handle float steps
        num_steps = 200  # Or any other desired resolution
        step = (max_distance - min_distance) / num_steps

        # Generate distances using a loop and rounding to handle float steps
        distances = []
        current_distance = min_distance
        for _ in range(num_steps + 1): # +1 to include the last point
            distances.append(current_distance)
            current_distance += step

        volumes = [sample_curve(d, self.points, len(self.points)) for d in distances]

        self.plot_item.clear()
        self.plot_item.plot(distances, volumes, pen=pg.mkPen('c'))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CurveGraphForm()
    app.setStyle('Fusion')
    window.show()
    sys.exit(app.exec())