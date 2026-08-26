from PySide6.QtWidgets import QTabBar, QTabWidget, QToolButton, QWidget
from PySide6.QtCore import Qt, QSize, QPoint, Signal
from PySide6.QtGui import QIcon, QMouseEvent

try:
    import gui.resources_rc
except ImportError:
    pass


class DocumentTabBar(QTabBar):
    """Custom tab bar designed for multi-document interfaces.

    Features:
    - Middle-click on any tab closes that document.
    - An embedded 'New Document' button dynamically positioned immediately adjacent
      to the right of the document tabs.
    - Valve Source 2 / Hammer 5 dark styling and icon support.
    """

    new_tab_requested = Signal()
    newTabRequested = Signal()  # Alias for camelCase compatibility

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("is_document_tab_bar", True)
        self.setDrawBase(False)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setElideMode(Qt.ElideRight)

        # Embedded New Document (+) Button
        self.new_tab_btn = QToolButton(self)
        self.new_tab_btn.setObjectName("DocumentNewTabButton")
        self.new_tab_btn.setFixedSize(18, 18)
        self.new_tab_btn.setIconSize(QSize(11, 11))
        self.new_tab_btn.setIcon(QIcon(":/valve_common/icons/tools/common/add_sm.png"))
        self.new_tab_btn.setToolTip("New Document (Ctrl+N)")
        self.new_tab_btn.setCursor(Qt.PointingHandCursor)
        self.new_tab_btn.clicked.connect(self._on_new_tab_clicked)
        self._update_new_tab_btn_pos()

    def _on_new_tab_clicked(self):
        self.new_tab_requested.emit()
        self.newTabRequested.emit()

    def set_new_tab_tooltip(self, text: str):
        """Set the tooltip for the new document button."""
        self.new_tab_btn.setToolTip(text)

    def set_new_tab_button_visible(self, visible: bool):
        """Toggle visibility of the new document button."""
        self.new_tab_btn.setVisible(visible)
        if visible:
            self._update_new_tab_btn_pos()

    def _update_new_tab_btn_pos(self):
        """Position the new document button immediately after the last tab."""
        if not hasattr(self, "new_tab_btn") or self.new_tab_btn is None:
            return
        btn_w = self.new_tab_btn.width()
        btn_h = self.new_tab_btn.height()
        if self.count() > 0:
            last_rect = self.tabRect(self.count() - 1)
            x = last_rect.right() + 4
            y = last_rect.top() + max(0, (last_rect.height() - btn_h) // 2)
            self.new_tab_btn.move(x, y)
        else:
            y = max(0, (self.height() - btn_h) // 2)
            self.new_tab_btn.move(4, y)
        if self.isVisible():
            self.new_tab_btn.show()

    def tabLayoutChange(self):
        super().tabLayoutChange()
        self._update_new_tab_btn_pos()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_new_tab_btn_pos()

    def tabInserted(self, index: int):
        super().tabInserted(index)
        self._update_new_tab_btn_pos()

    def tabRemoved(self, index: int):
        super().tabRemoved(index)
        self._update_new_tab_btn_pos()

    def tabMoved(self, from_idx: int, to_idx: int):
        super().tabMoved(from_idx, to_idx)
        self._update_new_tab_btn_pos()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_new_tab_btn_pos()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            idx = self.tabAt(pos)
            if idx >= 0:
                self.tabCloseRequested.emit(idx)
                event.accept()
                return
        super().mouseReleaseEvent(event)


class DocumentTabWidget(QTabWidget):
    """Multi-document tab container widget with integrated DocumentTabBar."""

    new_tab_requested = Signal()
    newTabRequested = Signal()  # Alias for camelCase compatibility

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._doc_tab_bar = DocumentTabBar(self)
        self.setTabBar(self._doc_tab_bar)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)

        self._doc_tab_bar.new_tab_requested.connect(self.new_tab_requested.emit)
        self._doc_tab_bar.newTabRequested.connect(self.newTabRequested.emit)

    @property
    def new_tab_btn(self) -> QToolButton:
        return self._doc_tab_bar.new_tab_btn

    @property
    def tab_bar(self) -> DocumentTabBar:
        return self._doc_tab_bar

    def set_new_tab_tooltip(self, text: str):
        self._doc_tab_bar.set_new_tab_tooltip(text)

    def set_new_tab_button_visible(self, visible: bool):
        self._doc_tab_bar.set_new_tab_button_visible(visible)
