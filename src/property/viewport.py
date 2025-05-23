import sys
from typing import List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QScrollArea, QMenu, QCheckBox
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
            "m_Data": self.m_data
        }
#PropertyViewport is a widget that constais properties (PropertyWidget). Each property have label, id, class and data. How to work with this data depends on the editor.
# Vsmart format requires a list of controls to edit m_data, but soundvents format just one widget per property.

class PropertyWidget(QFrame):
    """
    Individual list entry. It now shows only its label – no push-buttons –
    and offers a context-menu with Duplicate / Cut / Paste.
    """
    # already existing signals (Up/Down/Copy kept for compatibility – never emitted)
    selectedChanged  = Signal(bool)
    requestMoveUp    = Signal(object)
    requestMoveDown  = Signal(object)
    requestCopy      = Signal(object)
    requestDuplicate = Signal(object)
    requestRemove    = Signal(object)
    requestDrag      = Signal(object, object)     # (self, QMouseEvent)
    requestSelect    = Signal(object, object)     # (self, QMouseEvent)

    # new signals for the context-menu
    requestCut   = Signal(object)
    requestPaste = Signal(object)
    
    modified = Signal(object)

    def __init__(self):
        super().__init__()
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
        self._frame_layout.setContentsMargins(4, 0, 4, 0)
        self._frame_layout.setSpacing(4)

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

    def createEditButton(self):
        btn = QLabel("✎")
        btn.setStyleSheet("color: #3A79C9; font-size: 16px; padding: 0 6px;")
        btn.setToolTip("Edit")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Connect to edit action if needed
        return btn
    def getContentHeight(self):
        return int(0)
    def updateSize(self):
        height = (32 + int(self.getContentHeight()))
        self.setMaximumHeight(height)
        self.setMinimumHeight(height)
    def toggleContent(self, state):
        self._content_widget.setVisible(bool(state))
        
    def getData(self):
        pass
    def populateControls(self):
        pass
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
        if (self.drag_start_pos and
                (event.position().toPoint() - self.drag_start_pos).manhattanLength() > 10):
            self.requestDrag.emit(self, event)
            self.drag_start_pos = None
        super().mouseMoveEvent(event)

    # ---------------------------------------------------- context menu
    def contextMenuEvent(self, event):
        """
        Right-click menu showing Duplicate / Cut / Paste / Remove.
        Paste is enabled only when there is something in the window’s cut-buffer.
        """
        menu = QMenu(self)

        act_duplicate = menu.addAction("Duplicate")
        act_cut       = menu.addAction("Cut")
        act_paste     = menu.addAction("Paste")
        act_remove    = menu.addAction("Remove")

        # Enable paste only if there is something in the buffer
        wnd = self.window()
        if isinstance(wnd, PropertyViewport):
            act_paste.setEnabled(bool(wnd.cut_buffer))
            act_remove.setEnabled(bool(wnd.selected_frames) or True)
        else:
            act_paste.setEnabled(False)
            act_remove.setEnabled(True)

        chosen = menu.exec(event.globalPos())
        if chosen is act_duplicate:
            self.requestDuplicate.emit(self)
        elif chosen is act_cut:
            self.requestCut.emit(self)
        elif chosen is act_paste:
            self.requestPaste.emit(self)
        elif chosen is act_remove:
            self.requestRemove.emit(self)


    # ---------------------------------------------------- style helpers
    def updateStyle(self):
        """Apply colours / borders according to selection state."""
        if self.selected:
            # 2 px outline, transparent fill
            self.setStyleSheet("""
                QFrame {
                    background-color: #1C1C1C;
                    border: 2px solid #3A79C9;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #1C1C1C;
                    border: 2px solid transparent;
                }
            """)


class DragImage(QWidget):
    """Floating widget that shows pixmaps of dragged frames."""
    def __init__(self, frames: List[PropertyWidget], parent=None):
        super().__init__(parent,
                         Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        for frame in frames:
            pix = QPixmap(frame.size())
            frame.render(pix)
            label = QLabel()
            label.setPixmap(pix)
            layout.addWidget(label)

        self.adjustSize()


# -------------------- Undo Command Classes --------------------
class DuplicateCommand(QUndoCommand):
    def __init__(self, window, frames_to_duplicate):
        super().__init__("Duplicate")
        self.window = window
        self.frames_to_duplicate = [f for f in window.frames if f in frames_to_duplicate]
        self.new_frames = []

    def redo(self):
        for fr in self.frames_to_duplicate:
            new_frame = PropertyWidget()
            self.window.addFrameSignals(new_frame)
            idx = self.window.framesLayout.indexOf(fr)
            self.window.framesLayout.insertWidget(idx + 1, new_frame)
            self.window.frames.insert(idx + 1, new_frame)
            self.new_frames.append((idx + 1, new_frame))

    def undo(self):
        for idx, new_frame in reversed(self.new_frames):
            self.window.framesLayout.removeWidget(new_frame)
            if new_frame in self.window.frames:
                self.window.frames.remove(new_frame)
            new_frame.deleteLater()
        self.new_frames.clear()

class CutCommand(QUndoCommand):
    def __init__(self, window, frames_to_cut):
        super().__init__("Cut")
        self.window = window
        self.frames_to_cut = [f for f in window.frames if f in frames_to_cut]
        self.cut_indices = []
        self.prev_cut_buffer = window.cut_buffer.copy()

    def redo(self):
        self.window.cut_buffer = self.frames_to_cut.copy()
        self.cut_indices = []
        for fr in self.frames_to_cut:
            idx = self.window.framesLayout.indexOf(fr)
            self.cut_indices.append(idx)
            self.window.framesLayout.removeWidget(fr)
            if fr in self.window.frames:
                self.window.frames.remove(fr)
            fr.hide()
            fr.selected = False
            fr.updateStyle()
        self.window.selected_frames = []
        self.window.last_selected_index = None

    def undo(self):
        for idx, fr in sorted(zip(self.cut_indices, self.frames_to_cut)):
            self.window.framesLayout.insertWidget(idx, fr)
            self.window.frames.insert(idx, fr)
            fr.show()
        self.window.cut_buffer = self.prev_cut_buffer.copy()

class PasteCommand(QUndoCommand):
    def __init__(self, window, cut_buffer, target):
        super().__init__("Paste")
        self.window = window
        self.cut_buffer = cut_buffer.copy()
        self.target = target
        self.insert_index = None

    def redo(self):
        if self.target is None:
            self.insert_index = self.window.framesLayout.count()
        else:
            self.insert_index = self.window.framesLayout.indexOf(self.target) + 1
        for offset, fr in enumerate(self.cut_buffer):
            fr.show()
            self.window.framesLayout.insertWidget(self.insert_index + offset, fr)
        self.window.frames = [self.window.framesLayout.itemAt(i).widget()
                              for i in range(self.window.framesLayout.count())]
        self.window.cut_buffer = []

    def undo(self):
        for fr in self.cut_buffer:
            self.window.framesLayout.removeWidget(fr)
            if fr in self.window.frames:
                self.window.frames.remove(fr)
            fr.hide()
        self.window.cut_buffer = self.cut_buffer.copy()

class RemoveCommand(QUndoCommand):
    def __init__(self, window, frames_to_remove):
        super().__init__("Remove")
        self.window = window
        self.frames_to_remove = [f for f in window.frames if f in frames_to_remove]
        self.remove_indices = []

    def redo(self):
        self.remove_indices = []
        for fr in self.frames_to_remove:
            idx = self.window.framesLayout.indexOf(fr)
            self.remove_indices.append(idx)
            self.window.framesLayout.removeWidget(fr)
            if fr in self.window.frames:
                self.window.frames.remove(fr)
            fr.hide()
            fr.selected = False
            fr.updateStyle()
        self.window.selected_frames = []
        self.window.last_selected_index = None

    def undo(self):
        for idx, fr in sorted(zip(self.remove_indices, self.frames_to_remove)):
            self.window.framesLayout.insertWidget(idx, fr)
            self.window.frames.insert(idx, fr)
            fr.show()

class PropertyViewport(QMainWindow):
    """
    Main widget managing a vertically ordered list of frames.
    Drag & drop ordering, multi-selection, context-menu actions (Duplicate,
    Cut, Paste) and a visible drop-indicator are provided.
    """
    DROP_COLOR = "#3A79C9"
    DROP_HEIGHT = 4

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Frames Window")
        central = QWidget()
        self.setCentralWidget(central)
        self.mainLayout = QVBoxLayout(central)

        # ---------- scroll area ----------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.mainLayout.addWidget(scroll)

        # ---------- container inside scroll area ----------
        self.container = QWidget()
        self.framesLayout = QVBoxLayout(self.container)
        self.container.setLayout(self.framesLayout)
        scroll.setWidget(self.container)

        # Add vertical spacer at the bottom
        self.framesLayout.addStretch()

        # Make scroll area fill available space
        self.mainLayout.setStretchFactor(scroll, 1)

        # ---------- frame data ----------
        self.frames: List[PropertyWidget] = []
        for i in range(3):
            frame = PropertyWidget()
            self.addFrameSignals(frame)
            self.framesLayout.insertWidget(self.framesLayout.count() - 1, frame)
            self.frames.append(frame)

        self.selected_frames: List[PropertyWidget] = []
        self.last_selected_index: int | None = None

        # ---------- drag helpers ----------
        self.dragged_frames: List[PropertyWidget] = []
        self.drag_image: DragImage | None = None
        self.drag_offset = QPoint()

        # ---------- drop indicator ----------
        self.drop_indicator = QFrame()
        self.drop_indicator.setFixedHeight(self.DROP_HEIGHT)
        self.drop_indicator.setStyleSheet(
            f"background-color: {self.DROP_COLOR}; border: none;")
        self.drop_indicator.hide()

        # ---------- cut / paste buffer ----------
        self.cut_buffer: List[PropertyWidget] = []
        # ---------- undo stack ----------
        self.undo_stack = QUndoStack(self)
        
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.undo_stack.undo)
        
        redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        redo_shortcut.activated.connect(self.undo_stack.redo)

    # ---------------------------------------------------- utilities
    def addFrameSignals(self, frame: PropertyWidget):
        # context-menu actions
        frame.requestDuplicate.connect(self.duplicateFrame)
        frame.requestCut.connect(self.cutFrames)
        frame.requestPaste.connect(lambda f: self.pasteFrames(target=f))
        frame.requestRemove.connect(self.removeFrames)

        # drag / selection
        frame.requestDrag.connect(self.startDrag)
        frame.requestSelect.connect(self.handleSelect)

    # ---------------------------------------------------- selection
    def handleSelect(self, frame, event):
        index = self.frames.index(frame)
        modifiers = event.modifiers()

        if modifiers & Qt.KeyboardModifier.ShiftModifier and self.last_selected_index is not None:
            # ----- Range selection -----
            start, end = sorted((self.last_selected_index, index))
            for i, f in enumerate(self.frames):
                f.selected = start <= i <= end
                f.updateStyle()
            self.selected_frames = [f for f in self.frames if f.selected]
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            # ----- Toggle selection -----
            frame.selected = not frame.selected
            frame.updateStyle()
            if frame.selected:
                if frame not in self.selected_frames:
                    self.selected_frames.append(frame)
            else:
                if frame in self.selected_frames:
                    self.selected_frames.remove(frame)
            self.last_selected_index = index
        else:
            # ----- Single selection -----
            for f in self.frames:
                f.selected = False
                f.updateStyle()
            frame.selected = True
            frame.updateStyle()
            self.selected_frames = [frame]
            self.last_selected_index = index

    # ---------------------------------------------------- frame operations
    # (Up/Down buttons removed – drag & drop now handles re-ordering)

    # ---------- duplicate ----------
    def duplicateFrame(self, reference_frame: PropertyWidget):
        """
        Duplicate selected frames if any, otherwise duplicate the clicked one.
        New copies are inserted right after the original entries.
        """
        frames_to_duplicate = self.selected_frames or [reference_frame]
        self.undo_stack.push(DuplicateCommand(self, frames_to_duplicate))

    # ---------- cut ----------
    def cutFrames(self, *_):
        """
        Remove currently selected frames from the list and keep them
        in `self.cut_buffer` so the user can paste them later.
        """
        if not self.selected_frames:
            return
        self.undo_stack.push(CutCommand(self, self.selected_frames))

    # ---------- paste ----------
    def pasteFrames(self, target: PropertyWidget | None = None):
        """
        Insert previously cut frames after `target`. If target is None,
        paste them at the end of the list.
        """
        if not self.cut_buffer:
            return
        self.undo_stack.push(PasteCommand(self, self.cut_buffer, target))

    # ---------- remove ----------
    def removeFrames(self, *_):
        """
        Remove frames from the list. If multiple frames are selected,
        all of them are removed. Otherwise, only the frame that triggered
        the request is removed.
        """
        frames_to_remove = self.selected_frames or []
        if not frames_to_remove:
            # fallback: remove the sender if not multi-selected
            sender = self.sender()
            if isinstance(sender, PropertyWidget):
                frames_to_remove = [sender]
            elif hasattr(sender, 'parent') and isinstance(sender.parent(), PropertyWidget):
                frames_to_remove = [sender.parent()]
            else:
                return
        self.undo_stack.push(RemoveCommand(self, frames_to_remove))

    # ---------------------------------------------------- drag handling
    def startDrag(self, frame, event):
        # Determine which frames are dragged
        self.dragged_frames = self.selected_frames if frame.selected else [frame]

        # Drag image
        drag_pos = event.position().toPoint()
        global_pos = frame.mapToGlobal(drag_pos)
        self.drag_offset = drag_pos
        self.drag_image = DragImage(self.dragged_frames)
        self.drag_image.move(global_pos - self.drag_offset)
        self.drag_image.show()

    def _showDropIndicatorAt(self, index: int):
        """Insert the drop indicator frame into layout at given index, clamped to valid range."""
        # Remove from layout if already present
        if self.drop_indicator.parent() is not None:
            self.framesLayout.removeWidget(self.drop_indicator)

        # Clamp index to valid range (0 ... count)
        count = self.framesLayout.count()
        if index < 0:
            index = 0
        if index > count:
            index = count

        self.drop_indicator.show()
        self.framesLayout.insertWidget(index, self.drop_indicator)

    def mouseMoveEvent(self, event):
        if self.dragged_frames and self.drag_image:
            # move floating preview
            drag_pos = event.position().toPoint()
            global_pos = self.mapToGlobal(drag_pos)
            self.drag_image.move(global_pos - self.drag_offset)

            # determine potential drop position
            pos_in_container = self.container.mapFrom(self, drag_pos)
            drop_index = self.framesLayout.count()  # default: end of list

            # Only count real widgets (skip drop_indicator and spacer)
            widgets = [
                self.framesLayout.itemAt(i).widget()
                for i in range(self.framesLayout.count())
                if self.framesLayout.itemAt(i).widget() is not self.drop_indicator
                and self.framesLayout.itemAt(i).widget() is not None
            ]

            # Remove the last widget if it's the spacer (QSpacerItem returns None for widget())
            if widgets and widgets[-1] is None:
                widgets = widgets[:-1]


            for i, widget in enumerate(widgets):
                if widget in self.dragged_frames:
                    continue  # ignore currently dragged frames
                geo = widget.geometry()
                mid_y = geo.top() + geo.height() / 2
                if pos_in_container.y() < mid_y:
                    drop_index = i
                    break
            else:
                drop_index = len(widgets)

            self._showDropIndicatorAt(drop_index)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragged_frames:
            # final placement index
            if self.drop_indicator.parent() is not None:
                drop_index = self.framesLayout.indexOf(self.drop_indicator)
            else:
                drop_index = self.framesLayout.count()

            # remove indicator
            if self.drop_indicator.parent() is not None:
                self.framesLayout.removeWidget(self.drop_indicator)
            self.drop_indicator.hide()

            # remove dragged frames temporarily
            for f in self.dragged_frames:
                self.framesLayout.removeWidget(f)

            # Clamp drop_index to valid range
            count = self.framesLayout.count()
            if drop_index < 0:
                drop_index = 0
            if drop_index > count:
                drop_index = count

            # insert dragged frames at target index
            for offset, f in enumerate(self.dragged_frames):
                self.framesLayout.insertWidget(drop_index + offset, f)

            # rebuild `self.frames` to match layout order, skipping spacers
            self.frames = [self.framesLayout.itemAt(i).widget()
                           for i in range(self.framesLayout.count())
                           if self.framesLayout.itemAt(i).widget() is not None]

            # clear drag state
            self.dragged_frames = []

        # remove floating image
        if self.drag_image:
            self.drag_image.hide()
            self.drag_image.deleteLater()
            self.drag_image = None

        super().mouseReleaseEvent(event)


# ---------------------------------------------------- run example
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PropertyViewport()
    window.resize(500, 300)
    window.show()
    sys.exit(app.exec())
