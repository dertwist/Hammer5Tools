# Import statements adjusted to use organization-specific modules
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QSlider
)
from PySide6.QtGui import QPainterPath, QPen
from PySide6.QtCore import Qt, QPointF, QRectF
import numpy as np
import sys

class CurveViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Curve Viewer with Adjustable Parameters")
        self.setGeometry(100, 100, 800, 600)

        # Main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)

        # Graphics view and scene
        self.view = QGraphicsView()
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)
        self.main_layout.addWidget(self.view)

        # Path item for the curve
        self.path_item = self.scene.addPath(QPainterPath(), QPen(Qt.green, 2))

        # Define static control points
        self.control_points = [
            QPointF(0, 100),
            QPointF(100, 200),
            QPointF(200, 50),
            QPointF(300, 300),
            QPointF(400, 150),
            QPointF(500, 250),
            QPointF(600, 100),
            QPointF(700, 200)
        ]

        # Default parameters
        self.m_n1 = 0
        self.m_n2 = 0
        self.m_r1 = 0
        self.m_r2 = 0

        # Adjust the preview view limits
        self.limit_preview_view()

        # Add sliders for parameters
        self.add_parameter_sliders()

        # Display the curve
        self.update_curve()

    def limit_preview_view(self):
        """Limit the preview view to a specific area."""
        # Define the rectangle area (adjust as needed)
        view_rect = QRectF(0, 0, 800, 300)  # x, y, width, height

        # Set the scene rectangle to limit the visible area
        self.scene.setSceneRect(view_rect)

        # Adjust the view to fit the scene rectangle
        self.view.fitInView(view_rect, Qt.KeepAspectRatio)

    def add_parameter_sliders(self):
        """Add sliders to adjust the parameters m_n1, m_n2, m_r1, m_r2."""
        self.sliders_layout = QHBoxLayout()
        self.main_layout.addLayout(self.sliders_layout)

        # m_n1 slider
        self.m_n1_label = QLabel("m_n1: 0")
        self.m_n1_slider = QSlider(Qt.Horizontal)
        self.m_n1_slider.setRange(-10, 10)
        self.m_n1_slider.setValue(self.m_n1)
        self.m_n1_slider.valueChanged.connect(self.update_m_n1)
        self.sliders_layout.addWidget(self.m_n1_label)
        self.sliders_layout.addWidget(self.m_n1_slider)

        # m_n2 slider
        self.m_n2_label = QLabel("m_n2: 0")
        self.m_n2_slider = QSlider(Qt.Horizontal)
        self.m_n2_slider.setRange(-10, 10)
        self.m_n2_slider.setValue(self.m_n2)
        self.m_n2_slider.valueChanged.connect(self.update_m_n2)
        self.sliders_layout.addWidget(self.m_n2_label)
        self.sliders_layout.addWidget(self.m_n2_slider)

        # m_r1 slider
        self.m_r1_label = QLabel("m_r1: 0")
        self.m_r1_slider = QSlider(Qt.Horizontal)
        self.m_r1_slider.setRange(-10, 10)
        self.m_r1_slider.setValue(self.m_r1)
        self.m_r1_slider.valueChanged.connect(self.update_m_r1)
        self.sliders_layout.addWidget(self.m_r1_label)
        self.sliders_layout.addWidget(self.m_r1_slider)

        # m_r2 slider
        self.m_r2_label = QLabel("m_r2: 0")
        self.m_r2_slider = QSlider(Qt.Horizontal)
        self.m_r2_slider.setRange(-10, 10)
        self.m_r2_slider.setValue(self.m_r2)
        self.m_r2_slider.valueChanged.connect(self.update_m_r2)
        self.sliders_layout.addWidget(self.m_r2_label)
        self.sliders_layout.addWidget(self.m_r2_slider)

    def update_m_n1(self, value):
        self.m_n1 = value
        self.m_n1_label.setText(f"m_n1: {value}")
        self.update_curve()

    def update_m_n2(self, value):
        self.m_n2 = value
        self.m_n2_label.setText(f"m_n2: {value}")
        self.update_curve()

    def update_m_r1(self, value):
        self.m_r1 = value
        self.m_r1_label.setText(f"m_r1: {value}")
        self.update_curve()

    def update_m_r2(self, value):
        self.m_r2 = value
        self.m_r2_label.setText(f"m_r2: {value}")
        self.update_curve()

    def compute_curve(self):
        """Compute the curve using the custom curvature algorithm."""
        if len(self.control_points) < 2:
            return []

        a = np.array([self.control_points[0].x(), self.control_points[0].y()])
        b = np.array([self.control_points[-1].x(), self.control_points[-1].y()])
        D = b - a

        x_values = np.linspace(a[0], b[0], 100)
        y_values = []

        m_n1 = self.m_n1 / 10.0
        m_n2 = self.m_n2 / 10.0
        m_r1 = self.m_r1 / 10.0
        m_r2 = self.m_r2 / 10.0

        for x in x_values:
            v = (x - a[0]) / D[0]
            v_c = np.clip(v, 0, 1)

            P1 = ((m_n2 + m_n1) * D[0] - (2 * D[1])) * v_c
            P2 = -m_r1 - (2 * m_r2)
            P3 = P1 + P2 * D[0] + D[1] * 3
            P4 = P3 * v_c + m_r2 * D[0]

            y = P4 * v_c + a[1]
            y_values.append(y)

        return list(zip(x_values, y_values))

    def update_curve(self):
        """Update the curve based on the control points and parameters."""
        curve_points = self.compute_curve()
        if not curve_points:
            self.path_item.setPath(QPainterPath())
            return

        path = QPainterPath()
        path.moveTo(curve_points[0][0], curve_points[0][1])

        for x, y in curve_points[1:]:
            path.lineTo(x, y)

        self.path_item.setPath(path)
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = CurveViewer()
    viewer.show()
    sys.exit(app.exec())