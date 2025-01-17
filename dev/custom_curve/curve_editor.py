import sys

import matplotlib
import matplotlib.pyplot as pyplot
from PySide6.QtWidgets import QDoubleSpinBox, QLabel

matplotlib.use('Qt5Agg')
from PySide6.QtGui import Qt
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
    QHBoxLayout, QMessageBox)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from src.widgets import FloatWidget
from dev.custom_curve.custom_curve import (CurvePoint,
    setup_all_curve_values, sample_curve)
from src.widgets_common import Button, DeleteButton

DEFAULT_VALUES = [[20, 3, 0, 0, 2, 3], [260, 1, 0, 0, 2, 3]]


class CurveGraphForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Distance-Volume Curve Graph")
        self.setStyleSheet("background-color: #2E2E2E; color: #FFFFFF;")

        self.points = []
        self.float_widgets = []
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.init_ui()
        self.plot_graph()

    def init_ui(self):
        self.figure = Figure(facecolor='#2E2E2E')
        self.canvas = FigureCanvas(self.figure)
        self.main_layout.addWidget(self.canvas)

        self.add_column_labels()

        for values in DEFAULT_VALUES:
            self.add_float_widget(values)

        add_point_button = QPushButton("Add Point")
        add_point_button.setStyleSheet("background-color: #444444; color: #FFFFFF;")
        add_point_button.clicked.connect(self.add_point)
        self.main_layout.addWidget(add_point_button)

    def add_column_labels(self):
        label_layout = QHBoxLayout()
        texts = ['Distance', 'Volume', 'Slope Left', 'Slope Right', 'Mode Left', 'Mode Right']
        for text in texts:
            label = QLabel(text)
            label.setStyleSheet("color: #FFFFFF;")
            label_layout.addWidget(label)
        self.main_layout.addLayout(label_layout)

    def add_point(self):
        self.add_float_widget([0.0, 0.0, 0.0, 0.0, 0, 0])

    def create_float_widget(self, value, slider_range, int_output):
        float_widget = FloatWidget(vertical=True, slider_scale=2, slider_range=slider_range, int_output=int_output)
        float_widget.SpinBox.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        float_widget.set_value(value)
        float_widget.edited.connect(self.plot_graph)
        return float_widget

    def add_float_widget(self, values):
        widget_layout = QHBoxLayout()
        slider_ranges = [[-2, 2], [-2, 2], [-2, 2], [-2, 2], [0, 4], [0, 4]]
        int_outputs = [False, False, False, False, True, True]

        for value, slider_range, int_output in zip(values, slider_ranges, int_outputs):
            float_widget = self.create_float_widget(value, slider_range, int_output)
            widget_layout.addWidget(float_widget)
            self.float_widgets.append(float_widget)

        self.main_layout.addLayout(widget_layout)

    def plot_graph(self):
        self.points = []
        distances_from_widgets = []

        for i in range(0, len(self.float_widgets), 6):
            try:
                distance = self.float_widgets[i].value
                volume = self.float_widgets[i + 1].value
                slopeLeft = self.float_widgets[i + 2].value
                slopeRight = self.float_widgets[i + 3].value
                modeLeft = int(self.float_widgets[i + 4].value)
                modeRight = int(self.float_widgets[i + 5].value)

                point = CurvePoint(distance, volume, slopeLeft, slopeRight, modeLeft, modeRight)
                self.points.append(point)
                distances_from_widgets.append(distance)

            except (ValueError, AttributeError):
                QMessageBox.warning(self, "Invalid Input", f"Invalid data in widget set {i // 6 + 1}. Please check the values.")
                return

        if not distances_from_widgets:
            return

        min_distance = min(distances_from_widgets)
        max_distance = max(distances_from_widgets)

        setup_all_curve_values(self.points, len(self.points))

        distances = [d for d in range(int(min_distance), int(max_distance) + 1)]
        volumes = [sample_curve(d, self.points, len(self.points)) for d in distances]

        self.figure.clear()
        ax = self.figure.add_subplot(111, facecolor='#2E2E2E')
        with pyplot.style.context('dark_background'):
            ax.plot(distances, volumes, color='cyan')
            ax.grid(True, color=(80/255, 80/255, 80/255))
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')

        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CurveGraphForm()
    app.setStyle('Fusion')
    window.show()
    sys.exit(app.exec())