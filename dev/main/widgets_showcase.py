from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from src.widgets import FloatWidget, SpinBoxSlider
import sys

class WidgetsShowcaseWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Widgets Showcase")
        self.setGeometry(100, 100, 400, 300)

        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Add FloatWidget to the layout
        self.float_test = FloatWidget(vertical=True)
        main_layout.addWidget(self.float_test)


        self.float_test_2 = FloatWidget(spacer_enable=False)
        main_layout.addWidget(self.float_test_2)

        self.float_test_3 = SpinBoxSlider(spacer_enable=False)
        main_layout.addWidget(self.float_test_3)

        # Set the central widget
        self.setCentralWidget(main_widget)

def main():
    app = QApplication(sys.argv)
    window = WidgetsShowcaseWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()