import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QVBoxLayout, QPushButton, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QMouseEvent
from PySide6.QtCore import Qt, QPointF

class Curve:
    def __init__(self):
        self.dots = [QPointF(0.0, 0.0), QPointF(1.0, 1.0), QPointF(0.25, 0.75), QPointF(0.75, 0.25)]

    def evaluate(self, t):
        a, b, p1, p2 = self.dots
        return (
            (1 - t)**3 * a +
            3 * (1 - t)**2 * t * p1 +
            3 * (1 - t) * t**2 * p2 +
            t**3 * b
        )

class CurveWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.curve = Curve()
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        self.debug_text = self.scene.addText("")
        self.debug_text.setDefaultTextColor(QColor(0, 0, 255))  # Blue debug text
        font = QFont()
        font.setPointSize(8)
        self.debug_text.setFont(font)

        self.selected_dot_index = None

    def setCurve(self, curve):
        self.curve = curve
        self.update_scene()

    def update_scene(self):
        self.scene.clear()
        width = self.width()
        height = self.height()

        pen = QPen(QColor(150, 150, 150))
        for i in range(0, 1001):
            t = i / 1000.0
            point = self.curve.evaluate(t)
            x = point.x() * width
            y = (1 - point.y()) * height
            if 0 <= x <= width and 0 <= y <= height:
                self.scene.addLine(x - 1, y, x + 1, y, pen)

        dot_radius = 6
        pen = QPen(QColor(150, 150, 40), 2)
        for i, dot in enumerate(self.curve.dots):
            x = dot.x() * width
            y = (1 - dot.y()) * height
            ellipse = QGraphicsEllipseItem(x - dot_radius, y - dot_radius, 2 * dot_radius, 2 * dot_radius)
            ellipse.setBrush(QColor(255, 100, 100))
            self.scene.addItem(ellipse)

            if i == 2 or i == 3:
                anchor_x = self.curve.dots[i - 2].x() * width
                anchor_y = (1 - self.curve.dots[i - 2].y()) * height
                line = QGraphicsLineItem(anchor_x, anchor_y, x, y)
                line.setPen(pen)
                self.scene.addItem(line)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_scene()

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position()
        width = self.width()
        height = self.height()
        bounding_box_size = 16
        for i, dot in enumerate(self.curve.dots):
            x = dot.x() * width
            y = (1 - dot.y()) * height
            if (x - bounding_box_size <= pos.x() <= x + bounding_box_size) and (y - bounding_box_size <= pos.y() <= y + bounding_box_size):
                self.selected_dot_index = i
                break

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.selected_dot_index is not None:
            pos = event.position()
            width = self.width()
            height = self.height()
            x = pos.x() / width
            y = 1 - (pos.y() / height)
            self.curve.dots[self.selected_dot_index] = QPointF(x, y)
            self.update_scene()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.selected_dot_index = None

class CurveWidgetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Curve Widget Dialog")
        self.resize(800, 600)

        layout = QVBoxLayout()
        self.curve_widget = CurveWidget(self)
        layout.addWidget(self.curve_widget)
        self.setLayout(layout)

        self.curve_widget.setCurve(Curve())

        normalize_button = QPushButton("Normalize View", self)
        layout.addWidget(normalize_button)
        normalize_button.clicked.connect(self.curve_widget.update_scene)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Window")
        self.setGeometry(100, 100, 400, 300)

        self.button = QPushButton("Open Curve Widget Dialog", self)
        self.button.clicked.connect(self.on_pushButton_clicked)
        self.setCentralWidget(self.button)

    def on_pushButton_clicked(self):
        dialog = CurveWidgetDialog(self)
        dialog.show()

def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()