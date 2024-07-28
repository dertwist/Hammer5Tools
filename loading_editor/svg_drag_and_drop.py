import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QMainWindow, QApplication
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QImage, QPainter


class ImageLabel(QLabel):  # Inherit from QLabel instead of QSvgWidget
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setText('Drag and drop an icon in svg format')
        self.setStyleSheet("margin: 0px; border: 0px;")  # Remove margin and border

    def updatePixmap(self, image):
        super().setPixmap(image)


class Svg_Drag_and_Drop(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(400, 400)
        self.setAcceptDrops(True)
        mainLayout = QVBoxLayout()
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)
        self.photoViewer = ImageLabel()
        mainLayout.addWidget(self.photoViewer)
        self.setStyleSheet("margin: 0px; border: 0px;")  # Remove margin and border for the main window
        self.file_path = None  # Initialize the file_path variable

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if all(url.toLocalFile().lower().endswith('.svg') for url in urls):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                file_name = os.path.basename(file_path)
                if file_path.lower().endswith('.svg'):
                    self.photoViewer.updatePixmap(QPixmap(file_path))
                    self.photoViewer.setText(f'{file_name}')
                    self.file_path = file_path  # Store the file path
                else:
                    self.photoViewer.setText('Only SVG files are accepted.')
            event.acceptProposedAction()
        else:
            event.ignore()

    def loading_editor_get_svg(self):
        if not self.file_path or not self.file_path.lower().endswith('.svg'):
            raise ValueError("The file is not an SVG file.")
        return self.file_path

# Example usage:
# app = QApplication([])
# window = Svg_Drag_and_Drop()
# window.show()
# app.exec()