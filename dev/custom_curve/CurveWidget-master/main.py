import sys
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem
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

        # Disable scrolling
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def setCurve(self, curve):
        self.curve = curve
        self.update_scene()

    def update_scene(self):
        self.scene.clear()
        width = self.width()
        height = self.height()

        # Calculate margins
        margin_x = width * 0.04
        margin_y = height * 0.04

        pen = QPen(QColor(150, 150, 150))
        for i in range(0, 1001):
            t = i / 1000.0
            point = self.curve.evaluate(t)
            x = margin_x + point.x() * (width - 2 * margin_x)
            y = margin_y + (1 - point.y()) * (height - 2 * margin_y)
            if 0 <= x <= width and 0 <= y <= height:
                self.scene.addLine(x - 1, y, x + 1, y, pen)

        dot_radius = 6
        pen = QPen(QColor(150, 150, 40), 2)
        for i, dot in enumerate(self.curve.dots):
            x = margin_x + dot.x() * (width - 2 * margin_x)
            y = margin_y + (1 - dot.y()) * (height - 2 * margin_y)
            ellipse = QGraphicsEllipseItem(x - dot_radius, y - dot_radius, 2 * dot_radius, 2 * dot_radius)
            ellipse.setBrush(QColor(255, 100, 100))
            self.scene.addItem(ellipse)

            if i == 2 or i == 3:
                anchor_x = margin_x + self.curve.dots[i - 2].x() * (width - 2 * margin_x)
                anchor_y = margin_y + (1 - self.curve.dots[i - 2].y()) * (height - 2 * margin_y)
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
        margin_x = width * 0.04
        margin_y = height * 0.04
        bounding_box_size = 16
        for i, dot in enumerate(self.curve.dots):
            x = margin_x + dot.x() * (width - 2 * margin_x)
            y = margin_y + (1 - dot.y()) * (height - 2 * margin_y)
            if (x - bounding_box_size <= pos.x() <= x + bounding_box_size) and (y - bounding_box_size <= pos.y() <= y + bounding_box_size):
                self.selected_dot_index = i
                break

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.selected_dot_index is not None:
            pos = event.position()
            width = self.width()
            height = self.height()
            margin_x = width * 0.02
            margin_y = height * 0.02
            x = (pos.x() - margin_x) / (width - 2 * margin_x)
            y = 1 - ((pos.y() - margin_y) / (height - 2 * margin_y))
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

def main():
    app = QApplication(sys.argv)
    main_window = CurveWidgetDialog()
    main_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()