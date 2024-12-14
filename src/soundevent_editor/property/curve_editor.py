from PySide6.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QSlider, QLabel, QVBoxLayout, QHBoxLayout, QWidget
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen, QFont, QPainter
import numpy as np

class CurveEditor(QWidget):
    edited = Signal(list)

    def __init__(self, m_n1=0, m_n2=0, m_r1=2, m_r2=3):
        super().__init__()
        self.m_n1 = m_n1
        self.m_n2 = m_n2
        self.m_r1 = m_r1
        self.m_r2 = m_r2
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        self.view = QGraphicsView()
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.main_layout.addWidget(self.view)
        self.scene.setSceneRect(0, 0, 800, 600)
        self._addGridLines()
        self._addAxes()
        self.background = self.scene.addRect(
            self.scene.sceneRect(), brush=QBrush(QColor(30, 30, 30, 100))
        )
        self.path = self.scene.addPath(QPainterPath(), QPen(Qt.green, 2))
        self._createParameterControls()
        self.drawSpline()

    def _addGridLines(self):
        for i in range(0, 801, 50):
            self.scene.addLine(i, 0, i, 600, QPen(QColor(100, 100, 100, 50), 1, Qt.DotLine))
        for j in range(0, 601, 50):
            self.scene.addLine(0, j, 800, j, QPen(QColor(100, 100, 100, 50), 1, Qt.DotLine))

    def _addAxes(self):
        self.scene.addLine(0, 300, 800, 300, QPen(QColor(255, 255, 255, 150), 2))
        self.scene.addLine(400, 0, 400, 600, QPen(QColor(255, 255, 255, 150), 2))

    def _createParameterControls(self):
        self.slider_layout = QHBoxLayout()
        self.main_layout.addLayout(self.slider_layout)
        font = QFont('Arial', 12)
        self.m_n1_label = QLabel(f"m_n1: {self.m_n1:.2f}")
        self.m_n1_label.setFont(font)
        self.m_n1_slider = QSlider(Qt.Horizontal)
        self.m_n1_slider.setMinimum(-50)
        self.m_n1_slider.setMaximum(50)
        self.m_n1_slider.setValue(int(self.m_n1 * 10))
        self.m_n1_slider.valueChanged.connect(self.update_m_n1)
        self.slider_layout.addWidget(self.m_n1_label)
        self.slider_layout.addWidget(self.m_n1_slider)
        self.m_n2_label = QLabel(f"m_n2: {self.m_n2:.2f}")
        self.m_n2_label.setFont(font)
        self.m_n2_slider = QSlider(Qt.Horizontal)
        self.m_n2_slider.setMinimum(-50)
        self.m_n2_slider.setMaximum(50)
        self.m_n2_slider.setValue(int(self.m_n2 * 10))
        self.m_n2_slider.valueChanged.connect(self.update_m_n2)
        self.slider_layout.addWidget(self.m_n2_label)
        self.slider_layout.addWidget(self.m_n2_slider)
        self.m_r1_label = QLabel(f"m_r1: {self.m_r1:.2f}")
        self.m_r1_label.setFont(font)
        self.m_r1_slider = QSlider(Qt.Horizontal)
        self.m_r1_slider.setMinimum(-50)
        self.m_r1_slider.setMaximum(50)
        self.m_r1_slider.setValue(int(self.m_r1 * 10))
        self.m_r1_slider.valueChanged.connect(self.update_m_r1)
        self.slider_layout.addWidget(self.m_r1_label)
        self.slider_layout.addWidget(self.m_r1_slider)
        self.m_r2_label = QLabel(f"m_r2: {self.m_r2:.2f}")
        self.m_r2_label.setFont(font)
        self.m_r2_slider = QSlider(Qt.Horizontal)
        self.m_r2_slider.setMinimum(-50)
        self.m_r2_slider.setMaximum(50)
        self.m_r2_slider.setValue(int(self.m_r2 * 10))
        self.m_r2_slider.valueChanged.connect(self.update_m_r2)
        self.slider_layout.addWidget(self.m_r2_label)
        self.slider_layout.addWidget(self.m_r2_slider)

    def update_m_n1(self, value):
        self.m_n1 = value / 10.0
        self.m_n1_label.setText(f"m_n1: {self.m_n1:.2f}")
        self.drawSpline()

    def update_m_n2(self, value):
        self.m_n2 = value / 10.0
        self.m_n2_label.setText(f"m_n2: {self.m_n2:.2f}")
        self.drawSpline()

    def update_m_r1(self, value):
        self.m_r1 = value / 10.0
        self.m_r1_label.setText(f"m_r1: {self.m_r1:.2f}")
        self.drawSpline()

    def update_m_r2(self, value):
        self.m_r2 = value / 10.0
        self.m_r2_label.setText(f"m_r2: {self.m_r2:.2f}")
        self.drawSpline()

    def compute_curve(self):
        a = np.array([800, 0])
        b = np.array([0, 300])
        D = b - a
        x_values = np.linspace(b[0], a[0], 500)
        y_values = []
        m_n1 = self.m_n1 / 10.0
        m_n2 = self.m_n2 / 10.0
        m_r1 = self.m_r1 / 10.0
        m_r2 = self.m_r2 / 10.0
        for x in x_values:
            v = (x - a[0]) / D[0]
            v_c = np.clip(v, 0, 1)
            P1 = ((m_n2 + m_r1) * D[0] - (2 * D[1])) * v_c
            P2 = -m_r1 - (2 * m_n2)
            P3 = P1 + P2 * D[0] + D[1] * 3
            P4 = P3 * v_c + m_n2 * D[0]
            y = P4 * v_c + a[1]
            y_values.append(y)
        curve_points = list(zip(x_values, y_values))
        clipped_points = [
            (x, y) for x, y in curve_points
            if 0 <= x <= 800 and 0 <= y <= 600
        ]
        return clipped_points

    def drawSpline(self):
        curve_points = self.compute_curve()
        if not curve_points:
            self.path.setPath(QPainterPath())
            return
        path = QPainterPath()
        path.moveTo(curve_points[0][0], curve_points[0][1])
        for x, y in curve_points[1:]:
            path.lineTo(x, y)
        self.path.setPath(path)
        self.edited.emit([self.m_n1, self.m_n2, self.m_r1, self.m_r2])

    def resizeEvent(self, event):
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        super().resizeEvent(event)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    editor = CurveEditor()
    editor.show()
    sys.exit(app.exec())