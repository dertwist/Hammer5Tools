import sys, os
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QScrollArea, QStackedLayout
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QDrag
from PySide6.QtCore import Qt, QMimeData
from loading_editor.ui_loading_editor_image_frame_widget import Ui_loading_editor_image_frame_widget_ui

class ImageFrame(QWidget):
    def __init__(self, image_path, main_window, parent=None):
        super().__init__(parent)
        self.ui = Ui_loading_editor_image_frame_widget_ui()
        self.ui.setupUi(self)
        self.image_path = image_path
        self.main_window = main_window

        self.image_label = self.ui.image_src_frame

        self.delete_button = self.ui.close_image_button
        self.delete_button.clicked.connect(self.delete_self)

        self.load_image()

    def delete_self(self):
        self.setParent(None)
        self.main_window.remove_image_frame(self)
        self.deleteLater()

    def load_image(self):
        pixmap = QPixmap(self.image_path)
        max_size = 200  # Set maximum size (both width and height)
        pixmap = pixmap.scaled(max_size, max_size, Qt.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)
        picture_name = os.path.basename(self.image_path)
        self.ui.image_name.setText(os.path.basename(self.image_path))

class loading_editor_image_drag_and_drop_area_window(QMainWindow):
    MAX_IMAGE_FRAMES = 10  # Maximum number of image frames

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Drag and Drop Images")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.stacked_layout = QStackedLayout(self.central_widget)
        self.stacked_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea(self.central_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: 0px;")  # Remove the border from the scroll area

        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidget(self.scroll_widget)

        self.stacked_layout.addWidget(self.scroll_area)

        # Create the label and add it to the stacked layout
        self.info_label = QLabel("Drag and drop images")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("""
            font-family: "Segoe UI";
            color: #9D9D9D;
            font: 580 10pt "Segoe UI";
            background-color: rgba(255, 255, 255, 200);  # Semi-transparent background
            border: 0px;  # Remove border from the label
        """)
        self.stacked_layout.addWidget(self.info_label)

        self.image_frames = []

        # Remove border from the central widget
        self.central_widget.setStyleSheet("border: 0px;")

        # Show the label if no images are present
        self.update_info_label_visibility()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                image_path = url.toLocalFile()
                self.add_image_frame(image_path)
            event.acceptProposedAction()

    def add_image_frame(self, image_path):
        if len(self.image_frames) >= self.MAX_IMAGE_FRAMES:
            print("Maximum number of image frames reached.")
            return

        image_frame = ImageFrame(image_path, self)
        self.image_frames.append(image_frame)

        self.rearrange_image_frames()
        self.update_info_label_visibility()

    def remove_image_frame(self, image_frame):
        self.image_frames.remove(image_frame)
        self.rearrange_image_frames()
        self.update_info_label_visibility()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.rearrange_image_frames()

    def rearrange_image_frames(self):
        # Clear current layout
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                self.scroll_layout.removeWidget(widget)
                widget.deleteLater()

        # Re-add image frames
        row_layout = None
        frame_width = 200  # Width of each image frame
        margin = 10  # Margin between image frames
        left_margin = 10  # Left margin for the horizontal layout
        right_margin = 40  # Right margin for the layout
        total_width = self.central_widget.width()
        max_frames_per_row = max(1, (total_width - right_margin) // (frame_width + margin))

        for index, frame in enumerate(self.image_frames):
            if index % max_frames_per_row == 0:
                row_layout = QHBoxLayout()
                self.scroll_layout.addLayout(row_layout)
                row_layout.setAlignment(Qt.AlignLeft)
                row_layout.setContentsMargins(0, 0, 0, 0)  # Set the left margin
            row_layout.addWidget(frame)

    def update_info_label_visibility(self):
        if len(self.image_frames) == 0:
            self.stacked_layout.setCurrentWidget(self.info_label)
        else:
            self.stacked_layout.setCurrentWidget(self.scroll_area)

    def loading_editor_get_all_images(self):
        return [frame.image_path for frame in self.image_frames]

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = loading_editor_image_drag_and_drop_area_window()
    window.show()
    sys.exit(app.exec())
