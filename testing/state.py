import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QDockWidget, QTextEdit, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import QSettings
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Dock Widgets Example")

        # Create dock widgets
        self.dock1 = QDockWidget("Dock 1", self)
        self.dock1.setWidget(QTextEdit("Content of Dock 1"))
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock1)

        self.dock2 = QDockWidget("Dock 2", self)
        self.dock2.setWidget(QTextEdit("Content of Dock 2"))
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock2)

        self.dock3 = QDockWidget("Dock 3", self)
        self.dock3.setWidget(QTextEdit("Content of Dock 3"))
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock3)

        # Create buttons
        save_button = QPushButton("Save State")
        save_button.clicked.connect(self.save_state)

        restore_button = QPushButton("Restore State")
        restore_button.clicked.connect(self.restore_state)

        # Layout for buttons
        button_layout = QVBoxLayout()
        button_layout.addWidget(save_button)
        button_layout.addWidget(restore_button)

        # Central widget
        central_widget = QWidget()
        central_widget.setLayout(button_layout)
        self.setCentralWidget(central_widget)

    def save_state(self):
        settings = QSettings("MyCompany", "MyApp")

        # Save the state of each dock widget
        for dock_widget in self.findChildren(QDockWidget):
            settings.setValue(f"{dock_widget.objectName()}_state", dock_widget.saveState())

    def restore_state(self):
        settings = QSettings("MyCompany", "MyApp")

        # Restore the state of each dock widget
        for dock_widget in self.findChildren(QDockWidget):
            saved_state = settings.value(f"{dock_widget.objectName()}_state")
            if saved_state:
                dock_widget.restoreState(saved_state)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())