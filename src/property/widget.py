import sys
from typing import List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QScrollArea, QMenu, QCheckBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPixmap, QUndoCommand, QUndoStack, QKeySequence, QShortcut
from random import random

import dataclasses
@dataclasses.dataclass
class VsmartProperty:
    m_label: str
    m_ElementID: int
    m_class: str
    m_data: dict = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "m_Label": self.m_label,
            "m_ElemetID": self.m_ElementID,
            "m_Class": self.m_class,
            "m_Data": self.m_data,
            "m_ShowChild": self.m_data
        }
# PropertyViewport is a widget that contains PropertyWidget instances.
# Each property has a label, ID, class, and data.
# The way m_data is edited depends on the editor:
# - In the Vsmart format, m_data is edited using a list of controls.
# - In the soundvents format, each property is edited with a single widget.

class PropertyWidget(QFrame):
    """
    Individual list entry. It now shows only its label – no push-buttons –
    and offers a context-menu with Duplicate / Cut / Paste.
    """
    # already existing signals (Up/Down/Copy kept for compatibility – never emitted)
    selectedChanged = Signal(bool)
    requestMoveUp = Signal(object)
    requestMoveDown = Signal(object)
    requestCopy = Signal(object)
    requestDuplicate = Signal(object)
    requestRemove = Signal(object)
    requestDrag = Signal(object, object)  # (self, QMouseEvent)
    requestSelect = Signal(object, object)  # (self, QMouseEvent)

    # new signals for the context-menu
    requestCut = Signal(object)
    requestPaste = Signal(object)

    modified = Signal(object)

    def __init__(self, PropertyViewport=None, parent=None, small_mode=False):
        super().__init__()
        self.setObjectName("PropertyWidget")
        if PropertyViewport is None:
            raise ValueError("PropertyWidget cannot be instantiated directly. Use PropertyViewport instead.")
        self.PropertyViewport = PropertyViewport
        text = f"{random():.4f}"

        self.selected: bool = False

        # ---------- initial style ----------
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.updateStyle()

        # ---------- main layout ----------
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # ---------- frame (header) ----------
        self._frame_widget = QWidget()
        self._frame_widget.setFixedHeight(32)
        self._frame_widget.setStyleSheet("background: transparent;")
        self._frame_layout = QHBoxLayout(self._frame_widget)
        self._frame_layout.setContentsMargins(4, 0, 4, 4)
        self._frame_layout.setSpacing(4)


        self.drag_handler = QLabel()
        self.drag_handler.setText("⋮")
        self.drag_handler.setStyleSheet("color: #888; font-size: 32px; padding: 0px;")
        self.drag_handler.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._frame_layout.addWidget(self.drag_handler)

        # Quick operation buttons (toggle, add, edit) - all on the left
        self.show_content = QCheckBox()
        self.show_content.setChecked(False)  # Hide content by default
        self.show_content.setToolTip("Show/Hide content")
        self.show_content.stateChanged.connect(self.toggleContent)
        self._frame_layout.addWidget(self.show_content)

        self.add_button = self.createAddButton()
        self._frame_layout.addWidget(self.add_button)

        self.edit_button = self.createEditButton()
        self._frame_layout.addWidget(self.edit_button)

        self.label = QLabel(text)
        self.label.setStyleSheet("color: white;")
        self._frame_layout.addWidget(self.label)

        self._frame_layout.addStretch()

        self._main_layout.addWidget(self._frame_widget)

        # ---------- content area ----------
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(8, 0, 0, 0)
        self._content_layout.setSpacing(2)
        self._main_layout.addWidget(self._content_widget)
        self._content_widget.setVisible(False)  # Hide content by default

        self.populateControls()
        # ---------- drag helpers ----------
        self.setMouseTracking(True)
        self.drag_start_pos: QPoint | None = None

        self.updateSize()

    def createAddButton(self):
        btn = QLabel("+")
        btn.setStyleSheet("color: #3A79C9; font-weight: bold; font-size: 18px; padding: 0 6px;")
        btn.setToolTip("Add")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Connect to add action if needed
        return btn
    def addProperty(self):
        property_widget = QFrame()
        layout = QVBoxLayout(property_widget)  # Ensure the QFrame has a layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(QLineEdit())
        property_widget.setMinimumHeight(36)
        return property_widget

    def createEditButton(self):
        btn = QLabel("✎")
        btn.setStyleSheet("color: #3A79C9; font-size: 16px; padding: 0 6px;")
        btn.setToolTip("Edit")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Connect to edit action if needed
        return btn

    def getContentHeight(self):
        height = 0
        if self.show_content.isChecked():
            for i in range(self._content_layout.count()):
                height = height + self._content_layout.itemAt(i).widget().minimumHeight()
        return height

    def updateSize(self):
        height = (32 + int(self.getContentHeight()))
        self.setMaximumHeight(height)
        self.setMinimumHeight(height)

    def toggleContent(self, state):
        self._content_widget.setVisible(bool(state))
        self.updateSize()

    def getData(self):
        pass

    def populateControls(self):
        self._content_layout.addWidget(self.addProperty())
        self._content_layout.addWidget(self.addProperty())

    def modificated(self):
        '''Getting data from all controls and emit signal with this data'''
        data = self.getData()
        self.modified.emit(data)

    # ---------------------------------------------------- mouse events
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position().toPoint()
            self.requestSelect.emit(self, event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Only start drag if mouse started on drag_handler
        if (self.drag_start_pos and
                (event.position().toPoint() - self.drag_start_pos).manhattanLength() > 10):
            # Check if drag started on the drag handler
            if self.drag_handler.geometry().contains(self.mapFromGlobal(self.cursor().pos())):
                self.requestDrag.emit(self, event)
                self.drag_start_pos = None
        super().mouseMoveEvent(event)

    # ---------------------------------------------------- context menu
    def contextMenuEvent(self, event):
        """
        Right-click menu showing Duplicate / Cut / Paste / Remove.
        Paste is enabled only when there is something in the window’s cut-buffer or copy-buffer.
        """
        menu = QMenu(self)

        act_duplicate = menu.addAction("Duplicate")
        act_cut = menu.addAction("Cut")
        act_paste = menu.addAction("Paste")
        act_remove = menu.addAction("Remove")
        act_copy = menu.addAction("Copy")

        # Use the instance's buffers and selection
        wnd = self.PropertyViewport if not isinstance(self.PropertyViewport, type) else self.window()
        act_paste.setEnabled(bool(getattr(wnd, "cut_buffer", None) or getattr(wnd, "copy_buffer", None)))
        act_remove.setEnabled(bool(getattr(wnd, "selected_frames", None)) or True)

        chosen = menu.exec(event.globalPos())
        if chosen is act_duplicate:
            self.requestDuplicate.emit(self)
        elif chosen is act_cut:
            self.requestCut.emit(self)
        elif chosen is act_paste:
            self.requestPaste.emit(self)
        elif chosen is act_remove:
            self.requestRemove.emit(self)
        elif chosen is act_copy:
            self.requestCopy.emit(self)

    # ---------------------------------------------------- style helpers
    def updateStyle(self):
        """Apply colours / borders according to selection state."""
        if self.selected:
            # 2 px outline, transparent fill
            self.setStyleSheet("""
                QFrame#PropertyWidget {
                    background-color: #1C1C1C;
                    border: 2px solid #3A79C9;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#PropertyWidget {
                    background-color: #1C1C1C;
                    border: 2px solid transparent;
                }
            """)