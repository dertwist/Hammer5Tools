from src.widgets.property.commands import *
from src.widgets.property.widget import *


class DragImage(QWidget):
    """Floating widget that shows pixmaps of dragged frames."""
    def __init__(self, frames: List[PropertyWidget], parent=None):
        super().__init__(parent,
                         Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.Tool |
                         Qt.WindowType.WindowStaysOnTopHint)
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

class PropertyViewport(QMainWindow):
    """
    Main widget managing a vertically ordered list of frames.
    Drag & drop ordering, multi-selection, context-menu actions (Duplicate,
    Cut, Paste) and a visible drop-indicator are provided.
    """
    DROP_COLOR = "#3A79C9"
    DROP_HEIGHT = 4

    def __init__(self, undo_stack: QUndoStack | None = None):
        super().__init__()
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
        self.copy_buffer: List[PropertyWidget] = []
        # ---------- undo stack ----------
        if undo_stack is not None:
            self.undo_stack = undo_stack
        else:
            self.undo_stack = QUndoStack(self)

        # ---------- frame data ----------
        self.frames: List[PropertyWidget] = []
        for i in range(3):
            frame = PropertyWidget(PropertyViewport=self)
            self.addFrameSignals(frame)
            self.framesLayout.insertWidget(self.framesLayout.count() - 1, frame)
            self.frames.append(frame)

        self.selected_frames: List[PropertyWidget] = []
        self.last_selected_index: int | None = None

        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.undo_stack.undo)

        redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        redo_shortcut.activated.connect(self.undo_stack.redo)

        # Install event filter for context menu on empty space
        self.container.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.container.customContextMenuRequested.connect(self.viewportContextMenu)

        # Install mousePressEvent handler for deselection on empty space
        self.container.mousePressEvent = self.viewportContainerMousePressEvent

    # ---------------------------------------------------- utilities
    def addFrameSignals(self, frame: PropertyWidget):
        # context-menu actions
        frame.requestDuplicate.connect(self.duplicateFrame)
        frame.requestCopy.connect(lambda : self.undo_stack.push(CopyCommand(self, self.selected_frames)))
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
            # Don't deselect if clicking on an already selected frame (potential drag start)
            if not frame.selected or len(self.selected_frames) <= 1:
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
        if self.cut_buffer:
            self.undo_stack.push(PasteCommand(self, self.cut_buffer, target))
        elif self.copy_buffer:
            self.undo_stack.push(PasteCommand(self, self.copy_buffer, target))

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
        # Ensure the drag image stays on top
        self.drag_image.raise_()

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

    # Helper to get only real PropertyWidget instances from the layout
    def _real_widgets(self):
        return [
            self.framesLayout.itemAt(i).widget()
            for i in range(self.framesLayout.count())
            if isinstance(self.framesLayout.itemAt(i).widget(), PropertyWidget)
        ]

    def mouseMoveEvent(self, event):
        if self.dragged_frames and self.drag_image:
            # move floating preview
            drag_pos = event.position().toPoint()
            global_pos = self.mapToGlobal(drag_pos)
            self.drag_image.move(global_pos - self.drag_offset)
            # Ensure drag image stays visible
            self.drag_image.raise_()

            # determine potential drop position
            pos_in_container = self.container.mapFrom(self, drag_pos)
            drop_index = self.framesLayout.count()

            widgets = self._real_widgets()

            for i, widget in enumerate(widgets):
                if widget in self.dragged_frames:
                    continue  # ignore currently dragged frames
                geo = widget.geometry()
                mid_y = geo.top() + geo.height() / 2
                if pos_in_container.y() < mid_y:
                    drop_index = i +1
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
            if drop_index > count:
                drop_index = count
            drop_index = drop_index -1
            if drop_index < 0:
                drop_index = 0

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

    def viewportContextMenu(self, pos):
        # Only trigger if right-clicked on empty space (not on a widget)
        widget = self.container.childAt(pos)
        if widget is None or widget is self.container:
            menu = QMenu(self)
            act_add = menu.addAction("Add")
            act_paste = menu.addAction("Paste")

            act_paste.setEnabled(bool(self.cut_buffer or self.copy_buffer))

            chosen = menu.exec(self.container.mapToGlobal(pos))
            if chosen is act_add:
                # Insert before spacer (at end)
                self.undo_stack.push(AddCommand(self, insert_index=self.framesLayout.count() - 1))
            elif chosen is act_paste:
                # Use PasteCommand for both cut and copy buffer
                if self.cut_buffer:
                    self.undo_stack.push(PasteCommand(self, self.cut_buffer, None))
                elif self.copy_buffer:
                    self.undo_stack.push(PasteCommand(self, self.copy_buffer, None))

    def viewportContainerMousePressEvent(self, event):
        # Deselect all PropertyWidgets if clicking on empty space
        if event.button() == Qt.MouseButton.LeftButton:
            widget = self.container.childAt(event.position().toPoint())
            if widget is None or widget is self.container:
                for f in self.frames:
                    f.selected = False
                    f.updateStyle()
                self.selected_frames = []
                self.last_selected_index = None
        # Call base QWidget mousePressEvent to allow normal event processing
        QWidget.mousePressEvent(self.container, event)


# ---------------------------------------------------- run example
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PropertyViewport()
    window.resize(500, 300)
    window.show()
    sys.exit(app.exec())