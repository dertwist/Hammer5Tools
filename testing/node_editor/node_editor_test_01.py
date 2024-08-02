import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsItem, \
    QGraphicsEllipseItem, QGraphicsLineItem, QVBoxLayout, QWidget, QPushButton, QGraphicsTextItem, QTextEdit, QMenu
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QContextMenuEvent, QAction

class Socket(QGraphicsEllipseItem):
    def __init__(self, parent, position):
        super().__init__(-5, -5, 10, 10, parent)
        self.setBrush(QBrush(QColor(0, 0, 0)))
        self.setPos(position)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)

class Node(QGraphicsEllipseItem):
    def __init__(self, x, y, text):
        super().__init__(-50, -50, 100, 100)
        self.setBrush(QBrush(QColor(200, 200, 255)))
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setPos(x, y)

        self.text = QGraphicsTextItem(text, self)
        self.text.setDefaultTextColor(Qt.black)
        self.text.setPos(-30, -10)

        self.sockets = []
        self.add_socket(QPointF(-50, 0))  # Left socket
        self.add_socket(QPointF(50, 0))   # Right socket

    def add_socket(self, position):
        socket = Socket(self, position)
        self.sockets.append(socket)

class MathNode(Node):
    def __init__(self, x, y, operation):
        super().__init__(x, y, operation)
        self.operation = operation

class InputNode(Node):
    def __init__(self, x, y):
        super().__init__(x, y, "Input")

class OutputNode(Node):
    def __init__(self, x, y):
        super().__init__(x, y, "Output")

class Connection(QGraphicsLineItem):
    def __init__(self, start_socket, end_socket):
        super().__init__()
        self.start_socket = start_socket
        self.end_socket = end_socket
        self.update_position()
        self.setPen(QPen(Qt.black, 2))

    def update_position(self):
        line = QLineF(self.start_socket.scenePos(), self.end_socket.scenePos())
        self.setLine(line)

class NodeEditor(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.connections = []

    def add_node(self, x, y, text):
        node = Node(x, y, text)
        self.scene().addItem(node)
        return node

    def add_math_node(self, x, y, operation):
        node = MathNode(x, y, operation)
        self.scene().addItem(node)
        return node

    def add_input_node(self, x, y):
        node = InputNode(x, y)
        self.scene().addItem(node)
        return node

    def add_output_node(self, x, y):
        node = OutputNode(x, y)
        self.scene().addItem(node)
        return node

    def add_connection(self, start_socket, end_socket):
        connection = Connection(start_socket, end_socket)
        self.connections.append(connection)
        self.scene().addItem(connection)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        for connection in self.connections:
            connection.update_position()

    def contextMenuEvent(self, event: QContextMenuEvent):
        context_menu = QMenu(self)
        add_node_action = QAction("Add Node", self)
        add_node_action.triggered.connect(lambda: self.add_node(event.pos().x(), event.pos().y(), "Node"))
        context_menu.addAction(add_node_action)

        add_input_action = QAction("Add Input", self)
        add_input_action.triggered.connect(lambda: self.add_input_node(event.pos().x(), event.pos().y()))
        context_menu.addAction(add_input_action)

        add_output_action = QAction("Add Output", self)
        add_output_action.triggered.connect(lambda: self.add_output_node(event.pos().x(), event.pos().y()))
        context_menu.addAction(add_output_action)

        add_plus_action = QAction("Add Plus", self)
        add_plus_action.triggered.connect(lambda: self.add_math_node(event.pos().x(), event.pos().y(), "Plus"))
        context_menu.addAction(add_plus_action)

        add_minus_action = QAction("Add Minus", self)
        add_minus_action.triggered.connect(lambda: self.add_math_node(event.pos().x(), event.pos().y(), "Minus"))
        context_menu.addAction(add_minus_action)

        add_multiply_action = QAction("Add Multiply", self)
        add_multiply_action.triggered.connect(lambda: self.add_math_node(event.pos().x(), event.pos().y(), "Multiply"))
        context_menu.addAction(add_multiply_action)

        add_divide_action = QAction("Add Divide", self)
        add_divide_action.triggered.connect(lambda: self.add_math_node(event.pos().x(), event.pos().y(), "Divide"))
        context_menu.addAction(add_divide_action)

        context_menu.exec(event.globalPos())

class DebugWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Debug Window")
        self.setGeometry(900, 100, 400, 600)
        self.layout = QVBoxLayout()
        self.debug_text = QTextEdit()
        self.layout.addWidget(self.debug_text)
        self.setLayout(self.layout)

    def log(self, message):
        self.debug_text.append(message)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Node Editor")
        self.setGeometry(100, 100, 800, 600)

        self.node_editor = NodeEditor()
        self.setCentralWidget(self.node_editor)

        self.toolbar = self.addToolBar("Toolbar")
        add_node_button = QPushButton("Add Node")
        add_node_button.clicked.connect(self.add_node)
        self.toolbar.addWidget(add_node_button)

        add_input_button = QPushButton("Add Input")
        add_input_button.clicked.connect(self.add_input_node)
        self.toolbar.addWidget(add_input_button)

        add_output_button = QPushButton("Add Output")
        add_output_button.clicked.connect(self.add_output_node)
        self.toolbar.addWidget(add_output_button)

        add_plus_button = QPushButton("Add Plus")
        add_plus_button.clicked.connect(lambda: self.add_math_node("Plus"))
        self.toolbar.addWidget(add_plus_button)

        add_minus_button = QPushButton("Add Minus")
        add_minus_button.clicked.connect(lambda: self.add_math_node("Minus"))
        self.toolbar.addWidget(add_minus_button)

        add_multiply_button = QPushButton("Add Multiply")
        add_multiply_button.clicked.connect(lambda: self.add_math_node("Multiply"))
        self.toolbar.addWidget(add_multiply_button)

        add_divide_button = QPushButton("Add Divide")
        add_divide_button.clicked.connect(lambda: self.add_math_node("Divide"))
        self.toolbar.addWidget(add_divide_button)

        self.debug_window = DebugWindow()
        self.debug_window.show()

    def add_node(self):
        node = self.node_editor.add_node(0, 0, "Node")
        self.debug_window.log(f"Added Node at (0, 0)")

    def add_input_node(self):
        node = self.node_editor.add_input_node(0, 0)
        self.debug_window.log(f"Added Input Node at (0, 0)")

    def add_output_node(self):
        node = self.node_editor.add_output_node(0, 0)
        self.debug_window.log(f"Added Output Node at (0, 0)")

    def add_math_node(self, operation):
        node = self.node_editor.add_math_node(0, 0, operation)
        self.debug_window.log(f"Added {operation} Node at (0, 0)")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())