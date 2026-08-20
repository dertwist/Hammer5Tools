import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QAbstractItemView
)
from PySide6.QtGui import QUndoStack, QUndoCommand, QMouseEvent, QPainter, QPen, QColor, QBrush
from PySide6.QtCore import Qt, QRect
try:
    from .commands import AddItemCommand, RemoveItemCommand, MoveItemsCommand, DuplicateItemsCommand, SelectItemsCommand
except:
    from commands import AddItemCommand, RemoveItemCommand, MoveItemsCommand, DuplicateItemsCommand, SelectItemsCommand

class HierarchyTreeWidget(QTreeWidget):
    def __init__(self, undo_stack, list_mode=False):
        """
        :param undo_stack:
        :param list_mode:
        Means that tree widget will not have child elements, so it will works the same as the widget list. Drag and drop actions will just move items up and down, but not change parent of items
        """
        super().__init__()
        self.undo_stack = undo_stack
        self.undo_stack.setUndoLimit(400)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(True)
        self._ignore_next_drop = False
        # Optional hook for file drops coming from outside the tree (e.g. the explorer).
        # Signature: handler(paths: list[str], target_item: QTreeWidgetItem | None)
        self.external_drop_handler = None
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropMode(QTreeWidget.InternalMove)
        self.list_mode = list_mode
        self.setIndentation(18)
        self.setStyleSheet("HierarchyTreeWidget::branch { background: transparent; }")

    def drawBranches(self, painter: QPainter, rect: QRect, index):
        if getattr(self, 'list_mode', False):
            super().drawBranches(painter, rect, index)
            return

        painter.save()

        line_color = QColor("#636363")
        pen = QPen(line_color, 1, Qt.SolidLine)
        painter.setPen(pen)

        indent = self.indentation()
        if indent <= 0:
            indent = 18

        cy = rect.center().y()

        ancestors = []
        curr = index
        while curr.isValid():
            ancestors.append(curr)
            curr = curr.parent()
        ancestors.reverse()

        depth = len(ancestors) - 1

        # 1. Draw ancestor vertical lines and branch connections
        for level in range(depth):
            child_anc = ancestors[level + 1]
            has_sibling_below = child_anc.sibling(child_anc.row() + 1, 0).isValid()
            spine_cx = rect.left() + (level + 1) * indent + indent // 2

            if level < depth - 1:
                if has_sibling_below:
                    painter.drawLine(spine_cx, rect.top(), spine_cx, rect.bottom())
            else:
                top_y = rect.top()
                bottom_y = rect.bottom() if has_sibling_below else cy
                painter.drawLine(spine_cx, top_y, spine_cx, bottom_y)

                item_x = rect.left() + (depth + 1) * indent
                target_x = spine_cx + indent if self.model().hasChildren(child_anc) else item_x
                painter.drawLine(spine_cx, cy, target_x, cy)

        # 2. Current item's expander & step to next spine
        has_children = self.model().hasChildren(index)
        is_expanded = self.isExpanded(index)
        expander_cx = rect.left() + depth * indent + indent // 2

        if is_expanded and has_children:
            next_spine_cx = rect.left() + (depth + 1) * indent + indent // 2
            painter.drawLine(expander_cx, cy, next_spine_cx, cy)
            painter.drawLine(next_spine_cx, cy, next_spine_cx, rect.bottom())

        if depth == 0 and has_children:
            item_x = rect.left() + indent
            painter.drawLine(expander_cx, cy, item_x, cy)

        # 3. Draw expand/collapse circular button if item has children
        if has_children:
            r = 4
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setBrush(QBrush(QColor("#363636")))
            painter.setPen(QPen(QColor("#727272"), 1))
            painter.drawEllipse(expander_cx - r, cy - r, r * 2, r * 2)

            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setPen(QPen(QColor("#b6b6b6"), 1))
            painter.drawLine(expander_cx - 2, cy, expander_cx + 2, cy)

            if not is_expanded:
                painter.drawLine(expander_cx, cy - 2, expander_cx, cy + 2)

        painter.restore()

    def _external_drop_paths(self, event):
        """Local file paths of an external drop, or None if this is a normal internal drag."""
        if self.external_drop_handler is None or event.source() is self:
            return None
        mime = event.mimeData()
        if not mime.hasUrls():
            return None
        paths = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
        return paths or None

    def dragEnterEvent(self, event):
        if self._external_drop_paths(event):
            # Copy, never move: a MoveAction would make the source view delete the files.
            event.setDropAction(Qt.CopyAction)
            event.accept()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._external_drop_paths(event):
            event.setDropAction(Qt.CopyAction)
            event.accept()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        paths = self._external_drop_paths(event)
        if paths:
            event.setDropAction(Qt.CopyAction)
            event.accept()
            self.external_drop_handler(paths, self.itemAt(event.position().toPoint()))
            return

        if self._ignore_next_drop:
            self._ignore_next_drop = False
            super().dropEvent(event)
            return

        selected_items = self.selectedItems()
        if not selected_items:
            event.ignore()
            return

        # Store old parent and index for each selected item
        old_info = {
            item: (item.parent(), item.parent().indexOfChild(item) if item.parent() else self.indexOfTopLevelItem(item))
            for item in selected_items
        }

        # Perform the default drop handling
        super().dropEvent(event)

        # In list mode, ensure all items are top-level after drop
        if self.list_mode:
            for item in selected_items:
                if item.parent() is not None:
                    item.parent().removeChild(item)
                    self.addTopLevelItem(item)

        # Collect move infos for items whose position changed
        move_infos = []
        for item in selected_items:
            new_parent = item.parent()
            new_index = new_parent.indexOfChild(item) if new_parent else self.indexOfTopLevelItem(item)
            old_parent, old_index = old_info[item]
            if (old_parent, old_index) != (new_parent, new_index) and new_index != -1:
                move_infos.append({
                    'item': item,
                    'old_parent': old_parent,
                    'old_index': old_index,
                    'new_parent': new_parent,
                    'new_index': new_index
                })

        if move_infos:
            self.undo_stack.push(MoveItemsCommand(self, move_infos))

        event.accept()
    def DeleteSelectedItems(self):
        selected_items = self.selectedItems()
        if not selected_items:
            return
        cmd = RemoveItemCommand(self, selected_items)
        self.undo_stack.push(cmd)
    def AddItem(self, item):
        if not isinstance(item, QTreeWidgetItem):
            raise TypeError("Item must be a QTreeWidgetItem instance.")
        
        if self.list_mode:
            parent = self.invisibleRootItem()
        else:
            parent = self.currentItem()
            if parent is None:
                parent = self.invisibleRootItem()
            elif not (parent.flags() & Qt.ItemIsDropEnabled):
                # Leaf-only item types (e.g. Model/SmartProp) refuse ItemIsDropEnabled;
                # add beside them instead of inside them.
                parent = parent.parent() or self.invisibleRootItem()
        cmd = AddItemCommand(self, parent, item=item)
        self.undo_stack.push(cmd)
        if self.currentItem() is not None:
            self.setCurrentItem(item)
            self.currentItem().setExpanded(True)
            self.setFocus()
    def DuplicateSelectedItems(self, ElementIDGenerator=None):
        selected_items = self.selectedItems()
        if not selected_items:
            return
        cmd = DuplicateItemsCommand(self, selected_items, ElementIDGenerator)
        self.undo_stack.push(cmd)

    def setSelectedItemsWithUndo(self, items):
        """Set selected items with undo support"""
        old_selected = self.selectedItems()
        # Only create command if selection actually changes
        if set(old_selected) != set(items):
            cmd = SelectItemsCommand(self, old_selected, items)
            self.undo_stack.push(cmd)
    def mousePressEvent(self, event: QMouseEvent):
        item = self.itemAt(event.pos())
        if item is None and event.button() == Qt.LeftButton:
            self.clearSelection()
            self.setCurrentItem(None)
        super().mousePressEvent(event)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTreeWidgetItem, QPushButton
    from PySide6.QtGui import QUndoStack
    import sys

    class Winds(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("HierarchyTreeWidget Test")
            self.resize(400, 300)
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)

            self.undo_stack = QUndoStack()
            self.tree = HierarchyTreeWidget(self.undo_stack, list_mode=True)
            self.tree.setHeaderLabels(["Name"])
            self.tree.setRootIsDecorated(False)  # Hide root

            # Add children to invisible root
            child1 = QTreeWidgetItem(["Child 1"])
            child2 = QTreeWidgetItem(["Child 2"])
            self.tree.addTopLevelItem(child1)
            self.tree.addTopLevelItem(child2)

            layout.addWidget(self.tree)

            from PySide6.QtGui import QShortcut, QKeySequence
            QShortcut(QKeySequence("Delete"), self, activated=self.tree.DeleteSelectedItems)
            QShortcut(QKeySequence("Ctrl+D"), self, activated=self.tree.DuplicateSelectedItems)
            QShortcut(QKeySequence("Ctrl+N"), self, activated=self.add_item_shortcut)
            QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.undo_stack.undo)
            QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=self.undo_stack.redo)


        def add_item_shortcut(self):
            item = QTreeWidgetItem(["New Item"])
            self.tree.AddItem(item)

    app = QApplication(sys.argv)
    win = Winds()
    win.show()
    sys.exit(app.exec())