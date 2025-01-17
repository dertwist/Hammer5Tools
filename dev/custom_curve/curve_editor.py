import sys

import matplotlib
matplotlib.use('Qt5Agg')

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from dev.custom_curve.custom_curve import (CurvePoint,
    setup_all_curve_values, sample_curve)

DEFAULT_VALUES = [[20, 3, 0, 0, 2, 3], [260, 1, 0, 0, 2, 3]]

class CurveGraphForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Distance-Volume Curve Graph")

        self.points = []
        self.init_ui()
        self.plot_graph()  # Plot initial graph

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Graph
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)

        # Plot button
        plot_button = QPushButton("Plot Graph")
        plot_button.clicked.connect(self.plot_graph)
        main_layout.addWidget(plot_button)

        # Table for curve points
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Distance", "Volume", "Slope Left", "Slope Right", "Mode Left", "Mode Right"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row_data in DEFAULT_VALUES:
            self.add_table_row(row_data)

        self.table.cellChanged.connect(self.on_cell_changed)
        main_layout.addWidget(self.table)

        # Add Point Button
        add_point_button = QPushButton("Add Point")
        add_point_button.clicked.connect(self.add_point)
        main_layout.addWidget(add_point_button)

        self.setLayout(main_layout)

    def add_point(self):
        self.add_table_row([0.0, 0.0, 0.0, 0.0, 0, 0])  # Default values for new points

    def add_table_row(self, row_data):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        for col, value in enumerate(row_data):
            item = QTableWidgetItem(str(value))
            self.table.setItem(row_count, col, item)

    def on_cell_changed(self, row, column):
        try:
            item = self.table.item(row, column)
            if item is not None:  # Check if item exists (can be None during deletion)
                if column in (0, 1):
                    float(item.text())
                elif column in (2, 3, 4, 5):
                    if item.text():
                        if column in (4, 5):
                            int(item.text())
                        else:
                            float(item.text())
                self.plot_graph()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric data.")
            if item is not None:  # Check before clearing
                self.table.setItem(row, column, QTableWidgetItem(""))

    def plot_graph(self):
        self.points = []
        distances_from_table = []
        for row in range(self.table.rowCount()):
            try:
                distance = float(self.table.item(row, 0).text())
                volume = float(self.table.item(row, 1).text())
                slopeLeft = float(self.table.item(row, 2).text() or "0")
                slopeRight = float(self.table.item(row, 3).text() or "0")
                modeLeft = int(self.table.item(row, 4).text() or "0")
                modeRight = int(self.table.item(row, 5).text() or "0")

                point = CurvePoint(distance, volume, slopeLeft, slopeRight, modeLeft, modeRight)
                self.points.append(point)
                distances_from_table.append(distance)

            except (ValueError, AttributeError):  # Handle empty cells or invalid input
                QMessageBox.warning(self, "Invalid Input", f"Invalid data in row {row + 1}. Please check the values.")
                return

        if not distances_from_table:  # Check if no valid distances were found
            return

        min_distance = min(distances_from_table)
        max_distance = max(distances_from_table)

        setup_all_curve_values(self.points, len(self.points))

        distances = [d for d in range(int(min_distance), int(max_distance) + 1)]  # Include max_distance
        volumes = [sample_curve(d, self.points, len(self.points)) for d in distances]

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(distances, volumes)
        ax.set_xlabel("Distance")
        ax.set_ylabel("Volume")
        ax.set_title("Distance-Volume Curve")
        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CurveGraphForm()
    window.show()
    sys.exit(app.exec())