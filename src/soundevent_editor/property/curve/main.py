import sys
import pyqtgraph as pg
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QMessageBox, QLabel
from PySide6.QtCore import Signal
from src.widgets import BoxSlider
from src.soundevent_editor.property.curve.algorithm import CurvePoint, setup_all_curve_values, sample_curve
from src.widgets_common import DeleteButton
from src.common import JsonToKv3

DEFAULT_VALUES = [[20, 3, 0, 0, 2, 3], [260, 1, 0, 0, 2, 3]]

class DataPointItem(QWidget):
    edited = Signal()

    def __init__(self, values, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        self.float_widgets = []

        value_steps = [1, 1, 0.001, 0.001, 1, 1]
        digits_list = [3, 3, 3, 3, 0, 0]
        slider_ranges = [[0, 0], [0, 0], [-2, 2], [-2, 2], [0, 4], [0, 4]]
        int_outputs = [False, False, False, False, True, True]

        for value, slider_range, int_output, value_step, digits in zip(values, slider_ranges, int_outputs, value_steps, digits_list):
            float_widget = BoxSlider(slider_scale=2, slider_range=slider_range, int_output=int_output, value_step=value_step, digits=digits)
            float_widget.set_value(value)
            float_widget.edited.connect(self.on_edited)
            self.layout.addWidget(float_widget)
            self.float_widgets.append(float_widget)

        delete_button = DeleteButton(self)
        delete_button.clicked.connect(self.delete_item)
        self.layout.addWidget(delete_button)

    def on_edited(self):
        self.edited.emit()

    def get_values(self):
        return [widget.value for widget in self.float_widgets]

    def delete_item(self):
        parent = self.parent_widget
        self.setParent(None)
        self.deleteLater()

        if parent:
            parent.datapoint_items.remove(self)
            parent.plot_graph()

class CurveGraphForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Distance-Volume Curve Graph")
        self.setStyleSheet("background-color: #1C1C1C; color: #FFFFFF;")

        self.points = []
        self.datapoint_items = []
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.init_ui()
        self.plot_graph()

    def init_ui(self):
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setAntialiasing(True)  # Enable antialiasing for smoother curves
        self.graph_widget.setBackground('#1C1C1C')
        self.main_layout.addWidget(self.graph_widget)
        self.plot_item = self.graph_widget.getPlotItem()
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.getAxis("bottom").setPen(pg.mkPen(color='#232323', width=2))
        self.plot_item.getAxis("left").setPen(pg.mkPen(color='#232323', width=2))

        add_point_button = QPushButton("Add Point")
        add_point_button.setStyleSheet("background-color: #444444; color: #FFFFFF;")
        add_point_button.clicked.connect(self.add_point)
        self.main_layout.addWidget(add_point_button)

        output_button = QPushButton("Output Values")
        output_button.setStyleSheet("background-color: #444444; color: #FFFFFF;")
        output_button.clicked.connect(self.output_values)
        self.main_layout.addWidget(output_button)

        self.add_column_labels()
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

        if len(self.points) > 1:
            setup_all_curve_values(self.points, len(self.points))
        else:
            QMessageBox.warning(self, "Insufficient Data", "At least two points are required to plot the curve.")
            return

        num_steps = 200
        step = (max_distance - min_distance) / num_steps

        distances = []
        current_distance = min_distance
        for _ in range(num_steps + 1):
            distances.append(current_distance)
            current_distance += step

        volumes = [sample_curve(d, self.points, len(self.points)) for d in distances]

        self.plot_item.clear()
        self.plot_item.plot(distances, volumes, pen=pg.mkPen('#7F7F7F', width=1.5))

    def output_values(self):
        values_list = [item.get_values() for item in self.datapoint_items]
        print(values_list)
        input_a = values_list
        kv3_output = JsonToKv3(input_a)
        clipboard = QApplication.clipboard()
        clipboard.setText(kv3_output)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CurveGraphForm()
    app.setStyle('Fusion')
    window.show()
    sys.exit(app.exec())