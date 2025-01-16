import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QDialog, QVBoxLayout, QPushButton, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem
from PySide6.QtGui import QPainter, QPen, QColor, QMouseEvent, QFont
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
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0, 0)
        self.drag_start_pos = QPointF()
        self.is_dragging_dot = [-1] * 4

        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        self.debug_text = self.scene.addText("")
        self.debug_text.setDefaultTextColor(QColor(0, 0, 255))  # Blue debug text
        font = QFont()
        font.setPointSize(8)
        self.debug_text.setFont(font)

    def setCurve(self, curve):
        self.curve = curve
        self.update_scene()

    def normalizeView(self):
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0, 0)
        self.update_scene()

    def update_scene(self):
        self.scene.clear()
        width = self.width()
        height = self.height()

        pen = QPen(QColor(150, 150, 150))
        for i in range(0, 1001):
            t = i / 1000.0
            point = self.curve.evaluate(t)
            x = point.x() * width * self.zoom_factor + self.pan_offset.x()
            y = (1 - point.y()) * height * self.zoom_factor + self.pan_offset.y()
            if 0 <= x <= width and 0 <= y <= height:
                self.scene.addLine(x - 1, y, x + 1, y, pen)

        dot_radius = 6
        pen = QPen(QColor(150, 150, 40), 2)
        for i, dot in enumerate(self.curve.dots):
            x = dot.x() * width * self.zoom_factor + self.pan_offset.x()
            y = (1 - dot.y()) * height * self.zoom_factor + self.pan_offset.y()
            ellipse = QGraphicsEllipseItem(x - dot_radius, y - dot_radius, 2 * dot_radius, 2 * dot_radius)
            ellipse.setBrush(QColor(255, 100, 100) if self.is_dragging_dot[i] != -1 else QColor(150, 150, 150))
            self.scene.addItem(ellipse)

            if i == 2 or i == 3:
                anchor_x = self.curve.dots[i - 2].x() * width * self.zoom_factor + self.pan_offset.x()
                anchor_y = (1 - self.curve.dots[i - 2].y()) * height * self.zoom_factor + self.pan_offset.y()
                line = QGraphicsLineItem(anchor_x, anchor_y, x, y)
                line.setPen(pen)
                self.scene.addItem(line)

    def wheelEvent(self, event):
        zoom_in = event.angleDelta().y() > 0
        zoom_factor = 1.1 if zoom_in else 1 / 1.1
        self.zoom_factor *= zoom_factor
        self.update_scene()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            for i, dot in enumerate(self.curve.dots):
                width = self.width()
                height = self.height()
                x = dot.x() * width * self.zoom_factor + self.pan_offset.x()
                y = (1 - dot.y()) * height * self.zoom_factor + self.pan_offset.y()
                if (event.position() - QPointF(x, y)).manhattanLength() < 20:
                    self.is_dragging_dot[i] = i
                    self.setCursor(Qt.ClosedHandCursor)
                    return

            self.drag_start_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        width = self.width()
        height = self.height()
        if any(drag_idx != -1 for drag_idx in self.is_dragging_dot):
            for i, dragging in enumerate(self.is_dragging_dot):
                if dragging != -1:
                    x = (event.position().x() - self.pan_offset.x()) / (width * self.zoom_factor)
                    y = 1 - (event.position().y() - self.pan_offset.y()) / (height * self.zoom_factor)
                    self.curve.dots[i] = QPointF(max(0, min(1, x)), max(0, min(1, y)))
                    self.update_scene()
        elif event.buttons() & Qt.LeftButton:
            delta = event.position() - self.drag_start_pos
            self.pan_offset += delta
            self.drag_start_pos = event.position()
            self.update_scene()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging_dot = [-1] * 4
            self.setCursor(Qt.OpenHandCursor)

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
        normalize_button.clicked.connect(self.curve_widget.normalizeView)

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