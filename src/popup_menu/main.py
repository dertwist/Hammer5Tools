from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy
)
from PySide6.QtGui import QCursor, QKeyEvent
from PySide6.QtCore import QEvent, Qt, Signal
from src.popup_menu.ui_main import Ui_PoPupMenu
from src.widgets_common import Button
import webbrowser
from src.settings.main import set_config_value, get_config_value


class PropertyItemWidget(QWidget):
    property_clicked = Signal(str, str, bool, object)

    def __init__(self, key, value, help_url=None, window_name=None, add_once=False, ignore_items=None, bookmarked_items=None, popup_menu=None, parent=None):
        super().__init__(parent)
        self.key = key
        self.value = value
        self.help_url = help_url
        self.window_name = window_name
        self.add_once = add_once
        self.ignore_items = ignore_items or set()
        self.bookmarked_items = bookmarked_items or set()
        self.popup_menu = popup_menu
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.key)
        self.label.mousePressEvent = self.on_label_clicked
        layout.addWidget(self.label)

        if self.help_url:
            help_button = Button(size=32)
            help_button.set_icon_question()
            help_button.clicked.connect(self.on_help_button_clicked)
            layout.addWidget(help_button)

        if self.window_name:
            bookmark_button = Button(size=32)
            bookmark_button.set_icon_bookmark_added() if self.key in self.bookmarked_items else bookmark_button.set_icon_bookmark_add()
            bookmark_button.clicked.connect(self.toggle_bookmark)
            layout.addWidget(bookmark_button)

    def apply_styles(self):
        self.label.setStyleSheet(self.get_label_stylesheet())

    def on_label_clicked(self, event):
        if self.add_once and (self.key, str(self.value)) in self.ignore_items:
            return
        remove_item = self.add_once and (self.key, str(self.value)) not in self.ignore_items
        self.property_clicked.emit(self.key, str(self.value), remove_item, self.label)

    def on_help_button_clicked(self):
        base_url = "https://developer.valvesoftware.com/wiki/"
        cleaned_label = self.clean_spaces(self.key or "Workflow")
        url = f"{base_url}{self.help_url or ''}#{cleaned_label}"
        webbrowser.open(url)

    def toggle_bookmark(self):
        if self.key in self.bookmarked_items:
            self.bookmarked_items.discard(self.key)
        else:
            self.bookmarked_items.add(self.key)
        if self.window_name:
            set_config_value('Bookmarks', self.window_name, ','.join(self.bookmarked_items))
        if self.popup_menu:
            self.popup_menu.repopulate_items()

    def get_label_stylesheet(self):
        return """
            QLabel {
                font: 580 10pt "Segoe UI";
                border-bottom: 0.5px solid black;
                border-radius: 0px;
                border-color: rgba(40, 40, 40, 255);
                padding-top: 8px;
                padding-bottom: 8px;
            }
            QLabel:hover {
                background-color: #414956;
            }
            QLabel[selected="true"] {
                background-color: #2A2E38;
            }
        """

    @staticmethod
    def clean_spaces(text):
        return text.replace(" ", "_")


class PopupMenu(QDialog):
    label_clicked = Signal(str)
    add_property_signal = Signal(str, str)

    def __init__(self, properties, add_once=False, ignore_list=None, parent=None, help_url=None, window_name=None):
        super().__init__(parent)
        self.help_url = help_url
        self.properties = properties
        self.window_name = window_name
        self.ui = Ui_PoPupMenu()
        self.ui.setupUi(self)
        self.add_once = add_once
        self.ignore_items = self.convert_ignore_list(ignore_list)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setGeometry(200, 200, 400, 400)
        self.current_selection_index = -1
        self.visible_labels = []
        self.bookmarked_items = set()
        self.removed_items = set()
        self.setup_ui()
        self.init_bookmarks()
        self.populate_properties()

    def convert_ignore_list(self, ignore_list):
        ignore_list = ignore_list or []
        converted_ignore = set()
        for item in ignore_list:
            if isinstance(item, str):
                converted_ignore.add((item, item))
            else:
                k, v = item
                converted_ignore.add((k, str(v)))
        return converted_ignore

    def setup_ui(self):
        self.ui.lineEdit.textChanged.connect(self.search_text_changed)
        self.ui.lineEdit.setFocus()
        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setContentsMargins(0, 0, 2, 0)
        self.bookmarked_layout = QVBoxLayout()
        self.bookmarked_layout.setContentsMargins(0, 0, 0, 0)
        self.regular_layout = QVBoxLayout()
        self.regular_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.addLayout(self.bookmarked_layout)
        self.separator = QWidget()
        self.separator.setFixedHeight(2)
        self.separator.setStyleSheet("background-color: #363639;")
        self.separator.setVisible(False)
        self.scroll_layout.addWidget(self.separator)
        self.scroll_layout.addLayout(self.regular_layout)
        self.scroll_layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))
        scroll_content = QWidget()
        scroll_content.setLayout(self.scroll_layout)
        self.ui.scrollArea.setWidget(scroll_content)

    def init_bookmarks(self):
        if self.window_name:
            saved_bookmarks = get_config_value('Bookmarks', self.window_name)
            if saved_bookmarks:
                self.bookmarked_items = set(saved_bookmarks.split(','))

    def repopulate_items(self):
        self.clear_layout(self.bookmarked_layout)
        self.clear_layout(self.regular_layout)
        self.populate_properties()
        self.separator.setVisible(bool(self.bookmarked_items))

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            self.cleanup_layout_item(item)

    def populate_properties(self):
        bookmarked_list = []
        for prop_dict in self.properties:
            for key, val in prop_dict.items():
                if self.add_once and (key, str(val)) in self.removed_items:
                    continue
                item_widget = PropertyItemWidget(
                    key=key,
                    value=val,
                    help_url=self.help_url,
                    window_name=self.window_name,
                    add_once=self.add_once,
                    ignore_items=self.ignore_items,
                    bookmarked_items=self.bookmarked_items,
                    popup_menu=self,
                    parent=self
                )
                item_widget.property_clicked.connect(self.on_property_clicked)
                if key in self.bookmarked_items:
                    bookmarked_list.append((key, item_widget))
                else:
                    self.regular_layout.addWidget(item_widget)

        for i, (key, widget) in enumerate(bookmarked_list):
            if i == len(bookmarked_list) - 1:
                widget.label.setStyleSheet(self.get_last_bookmark_stylesheet())
            self.bookmarked_layout.addWidget(widget)

        self.separator.setVisible(bool(self.bookmarked_items))

    def on_property_clicked(self, key, val, remove_item, label):
        self.add_property_signal.emit(key, val)
        if remove_item:
            self.removed_items.add((key, val))
            self.remove_layout_item(key, label)

    def get_last_bookmark_stylesheet(self):
        return """
            QLabel {
                font: 580 10pt "Segoe UI";
                border-bottom: 0px solid black;
                border-radius: 0px;
                border-color: rgba(40, 40, 40, 255);
                padding-top: 8px;
                padding-bottom: 8px;
            }
            QLabel:hover {
                background-color: #414956;
            }
            QLabel[selected="true"] {
                background-color: #2A2E38;
            }
        """

    def remove_layout_item(self, key, label):
        layouts = [self.bookmarked_layout, self.regular_layout]
        for layout in layouts:
            for i in range(layout.count()):
                widget_item = layout.itemAt(i)
                if not widget_item:
                    continue
                widget = widget_item.widget()
                if not widget:
                    continue
                if isinstance(widget, PropertyItemWidget) and widget.label == label:
                    item_to_remove = layout.takeAt(i)
                    if item_to_remove:
                        self.cleanup_layout_item(item_to_remove)
                    self.separator.setVisible(self.bookmarked_layout.count() > 0)
                    self.update_visible_labels()
                    return

    def cleanup_layout_item(self, item):
        widget = item.widget()
        if widget:
            widget.deleteLater()
        else:
            layout = item.layout()
            if layout:
                while layout.count():
                    child = layout.takeAt(0)
                    self.cleanup_layout_item(child)

    def update_visible_labels(self):
        self.visible_labels.clear()
        scroll_content = self.ui.scrollArea.widget()
        if not scroll_content or not scroll_content.layout():
            return

        for i in range(scroll_content.layout().count()):
            child_item = scroll_content.layout().itemAt(i)
            if not child_item:
                continue
            child_layout = child_item.layout()
            child_widget = child_item.widget()

            if child_layout:
                for j in range(child_layout.count()):
                    sub_item = child_layout.itemAt(j)
                    if sub_item and sub_item.widget():
                        widget = sub_item.widget()
                        if isinstance(widget, PropertyItemWidget) and widget.label.isVisible():
                            self.visible_labels.append(widget.label)
            elif child_widget and isinstance(child_widget, PropertyItemWidget):
                if child_widget.label.isVisible():
                    self.visible_labels.append(child_widget.label)

    def navigate_selection(self, direction):
        self.update_visible_labels()
        if not self.visible_labels:
            return

        self.current_selection_index = (self.current_selection_index + direction) % len(self.visible_labels)
        self.update_selection_highlighting()
        selected_label = self.visible_labels[self.current_selection_index]
        self.ui.scrollArea.ensureWidgetVisible(selected_label)

    def update_selection_highlighting(self):
        for i, label in enumerate(self.visible_labels):
            label.setProperty("selected", i == self.current_selection_index)
            label.style().unpolish(label)
            label.style().polish(label)

    def activate_selection(self):
        self.update_visible_labels()
        if self.visible_labels and 0 <= self.current_selection_index < len(self.visible_labels):
            label = self.visible_labels[self.current_selection_index]
            if label.mousePressEvent:
                label.mousePressEvent(None)

    def search_text_changed(self):
        search_text = self.ui.lineEdit.text().lower()
        self._search_in_layout(self.bookmarked_layout, search_text)
        self._search_in_layout(self.regular_layout, search_text)

        if search_text == '':
            self.separator.setVisible(bool(self.bookmarked_items))
        else:
            self.separator.setVisible(False)

        self.current_selection_index = -1
        self.update_visible_labels()
        if self.visible_labels:
            self.current_selection_index = 0
            self.update_selection_highlighting()

    def _search_in_layout(self, layout, search_text):
        for i in range(layout.count()):
            widget_item = layout.itemAt(i)
            if not widget_item:
                continue
            widget = widget_item.widget()

            if widget and isinstance(widget, PropertyItemWidget):
                text_match = search_text in widget.label.text().lower()
                widget.setVisible(text_match)
            else:
                child_layout = widget_item.layout()
                if child_layout:
                    self._search_in_layout(child_layout, search_text)

    def keyPressEvent(self, event: QKeyEvent):
        key_handlers = {
            Qt.Key_Down: lambda: self.navigate_selection(1),
            Qt.Key_Up: lambda: self.navigate_selection(-1),
            Qt.Key_Return: self.activate_selection,
            Qt.Key_Enter: self.activate_selection,
            Qt.Key_Space: self.activate_selection
        }
        handler = key_handlers.get(event.key())
        if handler:
            handler()
            event.accept()
        else:
            super().keyPressEvent(event)

    def event(self, event):
        if event.type() == QEvent.WindowDeactivate:
            self.close()
            return True
        return super().event(event)

    def showEvent(self, event):
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        window_geometry = self.geometry()

        x = min(
            max(QCursor.pos().x(), screen_geometry.left()),
            screen_geometry.right() - window_geometry.width()
        )
        y = min(
            max(QCursor.pos().y(), screen_geometry.top()),
            screen_geometry.bottom() - window_geometry.height()
        )

        self.move(x, y)
        super().showEvent(event)

    def closeEvent(self, event):
        self.clear_layout(self.bookmarked_layout)
        self.clear_layout(self.regular_layout)
        self.ui.scrollArea.setWidget(None)
        self.ui = None
        self.bookmarked_items.clear()
        self.removed_items.clear()
        self.visible_labels.clear()
        super().closeEvent(event)