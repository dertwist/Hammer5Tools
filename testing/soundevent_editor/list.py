import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QListWidget, QTextEdit, QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("List and Detail Viewer")
        self.setGeometry(100, 100, 800, 600)

        # Main layout
        main_layout = QHBoxLayout()

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        main_layout.addWidget(self.list_widget, 1)

        # Detail widget
        self.detail_widget = QTextEdit()
        self.detail_widget.setReadOnly(True)
        main_layout.addWidget(self.detail_widget, 3)

        # Load items from file
        self.load_items_from_file()

        # Set main layout
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def load_items_from_file(self):
        try:
            with open('lists.txt', 'r') as file:
                for line in file:
                    item = line.strip()
                    if item:
                        self.list_widget.addItem(item)
        except FileNotFoundError:
            self.detail_widget.setText("Error: 'lists.txt' file not found.")

    def on_item_clicked(self, item):
        # Load data relevant to the selected item
        item_text = item.text()
        self.detail_widget.setText(f"Details for {item_text}:\n\n" + self.load_data_for_item(item_text))

    def load_data_for_item(self, item_text):
        # This function should be implemented to load the relevant data for the given item
        # For demonstration purposes, we'll just return a placeholder text
        return f"This is the detailed information for {item_text}."

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())