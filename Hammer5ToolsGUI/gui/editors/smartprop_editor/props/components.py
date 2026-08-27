"""
ComponentList — the section-1 component list widget for the SmartProp property editor.

Displays:
- Row 0: The element itself (a simple, non-reorderable row).
- Category header: Modifiers (with Add and Paste buttons)
  - Modifiers tree — a HierarchyTreeWidget(list_mode=True), one flat, non-nesting,
    drag-reorderable row per modifier.
- Category header: Selection Criteria (with Add and Paste buttons)
  - Selection criteria tree — same, for m_SelectionCriteria.

Data flow & selection:
Selecting a row emits componentSelected(ComponentRef).
The element row is selected by default when set_element() is called.
Reordering, delete, add, and copy/paste all push PropertySnapshotCommand onto the
document's real undo_stack. The two component trees are given their own private,
throwaway QUndoStack — HierarchyTreeWidget pushes its own MoveItemsCommand /
RemoveItemCommand there when the user drags or presses Delete, but those act on
the tree's own QTreeWidgetItems, not on m_Modifiers / m_SelectionCriteria, so
they're never wired to the document's Ctrl+Z. ComponentList reconciles the
resulting item order / removal back into the real data itself (see
_apply_tree_order / _delete_components) and pushes the real command there.
"""

from __future__ import annotations

import ast
import re
from typing import Any

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QIcon, QMouseEvent, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.common import fast_deepcopy
from gui.editors.smartprop_editor._common import (
    get_clean_class_name,
    CLIPBOARD_PREFIX,
    CLIPBOARD_BATCH_PREFIX,
    parse_component_clipboard,
)
from gui.editors.smartprop_editor.commands import PropertySnapshotCommand
from gui.widgets.widgets import make_composite_icon
from gui.editors.smartprop_editor.objects import (
    filters_list,
    operators_list,
    selection_criteria_list,
)
from gui.editors.smartprop_editor.properties_group_frame import PropertiesGroupFrame
from gui.editors.smartprop_editor.props.model import ComponentRef
from gui.styles.property_icons import IconCache
from gui.styles import theme
from gui.widgets.popup_menu.main import PopupMenu
from gui.widgets.tree import HierarchyTreeWidget
from gui.settings.common import get_settings_bool


def get_summary_hint(data: dict) -> str:
    """Extract a short display hint for a component's property data."""
    if not isinstance(data, dict):
        return ""
    if "m_sModelName" in data and data["m_sModelName"]:
        val = str(data["m_sModelName"])
        return val.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if "m_sSmartProp" in data and data["m_sSmartProp"]:
        val = str(data["m_sSmartProp"])
        return val.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if "m_VariableName" in data and data["m_VariableName"]:
        return str(data["m_VariableName"])
    if "m_Name" in data and data["m_Name"]:
        return str(data["m_Name"])
    if "m_StateName" in data and data["m_StateName"]:
        return str(data["m_StateName"])
    if "m_PathName" in data and data["m_PathName"]:
        return str(data["m_PathName"])
    if "m_flRandomScaleMin" in data and "m_flRandomScaleMax" in data:
        min_v = data.get("m_flRandomScaleMin")
        max_v = data.get("m_flRandomScaleMax")
        if min_v is not None and max_v is not None:
            return f"{min_v:.2g}..{max_v:.2g}" if isinstance(min_v, (int, float)) and isinstance(max_v, (int, float)) else f"{min_v}..{max_v}"
    if "m_flProbability" in data and data["m_flProbability"] is not None:
        p = data["m_flProbability"]
        return f"{p * 100:.0f}%" if isinstance(p, (int, float)) and 0 <= p <= 1 else str(p)
    if "m_flScale" in data and data["m_flScale"] is not None:
        return str(data["m_flScale"])
    if "m_flWeight" in data and data["m_flWeight"] is not None:
        return str(data["m_flWeight"])

    skip = {"_class", "m_nElementID", "m_bEnabled", "_WARN_NOT_VERIFIED", "m_nReferenceID"}
    for k, v in data.items():
        if k not in skip and v is not None and isinstance(v, (str, int, float, bool)):
            return str(v)
    return ""


def prettify_class_name(raw_class: str) -> str:
    """Turn CSmartPropElement_PlaceOnPath -> Place On Path."""
    clean = get_clean_class_name(raw_class)
    if clean.startswith("CSmartPropModifier_"):
        clean = clean.replace("CSmartPropModifier_", "")
    elif clean.startswith("CSmartPropOperation_"):
        clean = clean.replace("CSmartPropOperation_", "")
    elif clean.startswith("CSmartPropFilter_"):
        clean = clean.replace("CSmartPropFilter_", "")
    elif clean.startswith("CSmartPropSelectionCriteria_"):
        clean = clean.replace("CSmartPropSelectionCriteria_", "")
    clean = clean.rsplit("_", 1)[-1]
    # Insert space before capital letters
    pretty = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", clean)
    return pretty.strip()


def _component_icon(kind: str, raw_class: str):
    if kind == "modifier":
        return IconCache.get_node_icon("filter") if "Filter" in raw_class else IconCache.get_modifier_icon()
    if kind == "criterion":
        return IconCache.get_selection_criteria_icon()
    return IconCache.get_modifier_icon()


class ElementRowWidget(QFrame):
    """The single, always-present row for the element itself (row 0). Unlike
    modifiers/criteria it's never reordered or deleted, so it stays a plain
    row rather than living inside a HierarchyTreeWidget."""

    selected = Signal(object)  # ComponentRef
    addNoteRequested = Signal(object)  # ComponentRef

    def __init__(self, ref: ComponentRef, parent=None):
        super().__init__(parent)
        self.ref = ref
        self._is_selected = False

        self.setFrameShape(QFrame.NoFrame)
        self.setFixedHeight(26)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setProperty("h5Component", "smartpropElementRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        self.lbl_icon = QLabel(self)
        self.lbl_icon.setFixedSize(18, 18)
        self.lbl_icon.setScaledContents(True)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setProperty("h5Component", "smartpropTransparentLabel")
        layout.addWidget(self.lbl_icon)

        self.lbl_title = QLabel(self)
        font = QFont()
        font.setPixelSize(12)
        font.setBold(True)
        self.lbl_title.setFont(font)
        self.lbl_title.setProperty("h5Component", "smartpropElementTitle")
        layout.addWidget(self.lbl_title)

        self.lbl_id = QLabel(self)
        font_id = QFont()
        font_id.setPixelSize(11)
        self.lbl_id.setFont(font_id)
        self.lbl_id.setProperty("h5Component", "smartpropElementId")
        layout.addWidget(self.lbl_id)
        layout.addStretch(1)

        self._update_appearance()

    def update_data(self, data: dict):
        if not isinstance(data, dict):
            return
        raw_class = data.get("_class", "")
        self.lbl_title.setText(prettify_class_name(raw_class))
        if self.ref.item and hasattr(self.ref.item, "icon") and not self.ref.item.icon(0).isNull():
            base_icon = self.ref.item.icon(0)
        else:
            base_icon = IconCache.get_node_icon("element")
        comp_icon = make_composite_icon(base_icon, data, size=18)
        self.lbl_icon.setPixmap(comp_icon.pixmap(18, 18))

        eid = data.get("m_nElementID")
        if eid is None and self.ref.item:
            try:
                eid_str = self.ref.item.text(3)
                if eid_str:
                    eid = int(eid_str)
            except (ValueError, TypeError, AttributeError):
                pass
        if eid is None:
            parent_list = self.parent()
            while parent_list and not hasattr(parent_list, "document"):
                parent_list = parent_list.parent()
            doc = getattr(parent_list, "document", None) if parent_list else None
            if doc and hasattr(doc, "element_id_generator"):
                eid = doc.element_id_generator.get_element_id(data)
            else:
                from gui.widgets.element_id import get_ElementID
                eid = get_ElementID(data)
            data["m_nElementID"] = eid

        if eid is not None:
            self.lbl_id.setText(f"ID:{eid}")
            self.lbl_id.show()
        else:
            self.lbl_id.setText("")
            self.lbl_id.hide()

    def set_selected(self, selected: bool):
        if self._is_selected != selected:
            self._is_selected = selected
            self._update_appearance()

    def is_selected(self) -> bool:
        return self._is_selected

    def _update_appearance(self):
        self.setProperty("selected", "true" if self._is_selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.ref)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        act_copy = QAction("Copy Component", self)
        menu.addAction(act_copy)
        action = menu.exec_(event.globalPos())
        if action == act_copy:
            self.selected.emit(self.ref)  # select first so ComponentList._copy_component has the right ref
            parent = self.parent()
            if isinstance(parent, ComponentList):
                parent._copy_component(self.ref)


class ComponentTree(HierarchyTreeWidget):
    """Flat, non-nesting, drag-reorderable list of one component array (modifiers
    or selection criteria). Renders ComponentList's data; owns none of it itself
    — see the module docstring for how drops/deletes get reconciled back."""

    reordered = Signal()
    deleteRequested = Signal(list)  # list[QTreeWidgetItem]
    copyRequested = Signal()
    cutRequested = Signal()
    pasteRequested = Signal()
    duplicateRequested = Signal()

    ROW_H = 26

    def __init__(self, parent=None):
        super().__init__(QUndoStack(), list_mode=True)
        if parent is not None:
            self.setParent(parent)
        self.setHeaderHidden(True)
        self.setColumnCount(2)
        self.setRootIsDecorated(False)  # flat list — never has children to expand
        self.setIndentation(0)
        self.setIconSize(QSize(18, 18))
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAlternatingRowColors(True)
        self.header().setStretchLastSection(True)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.setProperty("h5Component", "smartpropComponentTree")
        self.verticalScrollBar().valueChanged.connect(self._reset_scroll)
        self.horizontalScrollBar().valueChanged.connect(self._reset_scroll)

    def _reset_scroll(self, val):
        if val != 0:
            self.verticalScrollBar().setValue(0)
            self.horizontalScrollBar().setValue(0)

    def scrollTo(self, index, hint=0):
        # Disable internal scrolling of tree viewport content completely so items never get scrolled off-screen.
        self.verticalScrollBar().setValue(0)
        self.horizontalScrollBar().setValue(0)

    def calculate_content_height(self) -> int:
        count = self.topLevelItemCount()
        if count == 0:
            return 4
        items_h = 0
        for i in range(count):
            h_i = self.sizeHintForRow(i)
            if h_i <= 0:
                h_i = self.ROW_H
            items_h += max(h_i, self.ROW_H)
        return items_h + 8

    def sizeHint(self):
        return QSize(super().sizeHint().width(), self.calculate_content_height())

    def minimumSizeHint(self):
        return QSize(0, self.calculate_content_height())

    def scrollContentsBy(self, dx, dy):
        # Completely disable internal scrolling of tree viewport content.
        pass

    def dropEvent(self, event):
        super().dropEvent(event)
        # Defer: ComponentList.rebuild() (triggered downstream of reordered)
        # calls tree.clear(), destroying every QTreeWidgetItem — including the
        # ones this very dropEvent's Qt-native drag-and-drop machinery is still
        # unwinding/cleaning up in the same call stack. Tearing that down
        # synchronously crashes; let the drop fully finish first.
        QTimer.singleShot(0, self.reordered.emit)

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        from PySide6.QtGui import QKeySequence
        if event.matches(QKeySequence.Copy):
            self.copyRequested.emit()
            return
        if event.matches(QKeySequence.Cut):
            self.cutRequested.emit()
            return
        if event.matches(QKeySequence.Paste):
            self.pasteRequested.emit()
            return
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_D:
            self.duplicateRequested.emit()
            return
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            items = self.selectedItems()
            if items:
                self.deleteRequested.emit(items)
                return
        super().keyPressEvent(event)
        self.verticalScrollBar().setValue(0)
        self.horizontalScrollBar().setValue(0)

    def wheelEvent(self, event):
        # Always sized to fit its own content exactly (refresh_height), so
        # there's never anything to scroll internally. Forward wheel event to outer scroll area.
        w = self.parentWidget()
        while w is not None:
            if isinstance(w, QScrollArea):
                QApplication.sendEvent(w.viewport(), event)
                return
            w = w.parentWidget()
        event.ignore()

    def refresh_height(self):
        self.doItemsLayout()
        height = self.calculate_content_height()
        self.setFixedHeight(height)
        self.verticalScrollBar().setValue(0)
        self.horizontalScrollBar().setValue(0)
        self.viewport().update()
        self.updateGeometry()
        p = self.parentWidget()
        while p is not None:
            if isinstance(p, ComponentList):
                p.updateGeometry()
                break
            p = p.parentWidget()


class ComponentList(QWidget):
    """Section 1 component list widget."""

    componentSelected = Signal(object)  # ComponentRef or None when empty
    addNoteRequested = Signal(object)   # ComponentRef

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.document = document
        self.tree_item = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)

        # Outer scroll area: the whole section scrolls as one unit. The two
        # component trees below disable their own scrollbars and stay sized
        # to fit their content exactly, so there's only ever one scrollbar.
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(2)

        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area)

        # Row 0: the element itself.
        self.elem_row = ElementRowWidget(ComponentRef(None, "element", -1), self.container_widget)
        self.elem_row.selected.connect(self._on_elem_selected)
        self.elem_row.addNoteRequested.connect(self.addNoteRequested)
        self.container_layout.addWidget(self.elem_row)

        # Category headers — plain divider bars with Add/Paste. The collapsible
        # body they came with is never used (children live in the trees below,
        # not inside the header itself), so hide it and its toggle.
        self.header_modifiers = PropertiesGroupFrame(name="Modifiers", group_type="modifier")
        self.header_modifiers.add_signal.connect(self._on_add_modifier)
        self.header_modifiers.paste_signal.connect(self._on_paste_modifier)
        self.header_modifiers.ui.show_child.hide()
        self.header_modifiers.ui.frame_layout.hide()
        self.container_layout.addWidget(self.header_modifiers)

        self.modifiers_tree = ComponentTree(self.container_widget)
        self.modifiers_tree.itemSelectionChanged.connect(self._on_modifiers_selection_changed)
        self.modifiers_tree.reordered.connect(self._on_modifiers_reordered)
        self.modifiers_tree.deleteRequested.connect(self._on_modifiers_delete_requested)
        self.modifiers_tree.copyRequested.connect(lambda: self._copy_selected_from_tree(self.modifiers_tree))
        self.modifiers_tree.cutRequested.connect(lambda: self._cut_selected_from_tree(self.modifiers_tree))
        self.modifiers_tree.pasteRequested.connect(lambda: self._paste_component_for_group("modifier"))
        self.modifiers_tree.duplicateRequested.connect(lambda: self._duplicate_selected_from_tree(self.modifiers_tree))
        self.modifiers_tree.customContextMenuRequested.connect(
            lambda pos: self._tree_context_menu(self.modifiers_tree, pos)
        )
        self.container_layout.addWidget(self.modifiers_tree)

        self.header_criteria = PropertiesGroupFrame(name="Selection Criteria", group_type="selection_criteria")
        self.header_criteria.add_signal.connect(self._on_add_criterion)
        self.header_criteria.paste_signal.connect(self._on_paste_criterion)
        self.header_criteria.ui.show_child.hide()
        self.header_criteria.ui.frame_layout.hide()
        self.container_layout.addWidget(self.header_criteria)

        self.criteria_tree = ComponentTree(self.container_widget)
        self.criteria_tree.itemSelectionChanged.connect(self._on_criteria_selection_changed)
        self.criteria_tree.reordered.connect(self._on_criteria_reordered)
        self.criteria_tree.deleteRequested.connect(self._on_criteria_delete_requested)
        self.criteria_tree.copyRequested.connect(lambda: self._copy_selected_from_tree(self.criteria_tree))
        self.criteria_tree.cutRequested.connect(lambda: self._cut_selected_from_tree(self.criteria_tree))
        self.criteria_tree.pasteRequested.connect(lambda: self._paste_component_for_group("selection_criteria"))
        self.criteria_tree.duplicateRequested.connect(lambda: self._duplicate_selected_from_tree(self.criteria_tree))
        self.criteria_tree.customContextMenuRequested.connect(
            lambda pos: self._tree_context_menu(self.criteria_tree, pos)
        )
        self.container_layout.addWidget(self.criteria_tree)

        self.container_layout.addStretch(1)


    def set_element(self, tree_item) -> None:
        """Rebuild component list from hierarchy tree item."""
        self.tree_item = tree_item
        self.rebuild()
        if self.tree_item is not None:
            self._select_ref(ComponentRef(self.tree_item, "element", -1), emit_signal=True)

    @property
    def selected_ref(self) -> ComponentRef | None:
        """Return the primary selected ComponentRef, or None."""
        refs = self.selected_refs()
        return refs[0] if refs else None

    def selected_refs(self) -> list[ComponentRef]:
        """Return list of currently selected ComponentRef objects, read live
        from whichever surface (element row / either tree) currently holds
        the selection."""
        refs: list[ComponentRef] = []
        if self.elem_row.is_selected() and self.elem_row.ref is not None and self.elem_row.ref.item is not None:
            refs.append(self.elem_row.ref)
        for it in self.modifiers_tree.selectedItems():
            ref = it.data(0, Qt.UserRole)
            if ref is not None and getattr(ref, 'item', None) is not None:
                refs.append(ref)
        for it in self.criteria_tree.selectedItems():
            ref = it.data(0, Qt.UserRole)
            if ref is not None and getattr(ref, 'item', None) is not None:
                refs.append(ref)
        return refs

    def sizeHint(self):
        """Report height based on actual content plus layout margins and spacing,
        so the layout expands this section to fit all components without showing
        an unnecessary scrollbar in scroll_area."""
        main_m = self.layout().contentsMargins()
        h = main_m.top() + main_m.bottom()

        c_m = self.container_layout.contentsMargins()
        h += c_m.top() + c_m.bottom()

        visible_widgets = []
        for i in range(self.container_layout.count()):
            item = self.container_layout.itemAt(i)
            w = item.widget() if item else None
            if w is not None and not w.isHidden():
                visible_widgets.append(w)

        if visible_widgets:
            spacing = self.container_layout.spacing()
            h += spacing * (len(visible_widgets) - 1)
            for w in visible_widgets:
                if isinstance(w, ComponentTree):
                    wh = w.sizeHint().height()
                else:
                    sh = w.sizeHint()
                    wh = sh.height() if sh.isValid() and sh.height() > 0 else w.height()
                h += wh

        # Add buffer (+6px) for scroll area viewport frames and borders
        h += 6
        h = max(ComponentTree.ROW_H * 2 + 12, h)
        s = super().sizeHint()
        return QSize(s.width(), h)

    def minimumSizeHint(self):
        s = super().minimumSizeHint()
        return QSize(s.width(), 54)

    def rebuild(self):
        """Refresh element row + both trees from current tree_item data."""
        if not self.tree_item:
            self.elem_row.ref = None
            self.modifiers_tree.clear()
            self.criteria_tree.clear()
            self.modifiers_tree.refresh_height()
            self.criteria_tree.refresh_height()
            self.componentSelected.emit(None)
            return

        element_data = self.tree_item.data(0, Qt.UserRole)
        if not isinstance(element_data, dict):
            self.modifiers_tree.clear()
            self.criteria_tree.clear()
            self.modifiers_tree.refresh_height()
            self.criteria_tree.refresh_height()
            self.componentSelected.emit(None)
            return

        prior = self.selected_refs()

        self.elem_row.ref = ComponentRef(self.tree_item, "element", -1)
        self.elem_row.update_data(element_data)

        self._populate_tree(self.modifiers_tree, "modifier", element_data.get("m_Modifiers") or [])
        self._populate_tree(self.criteria_tree, "criterion", element_data.get("m_SelectionCriteria") or [])

        if prior:
            self._select_ref(prior[0], emit_signal=False)
        else:
            self._select_ref(ComponentRef(self.tree_item, "element", -1), emit_signal=False)

        self.updateGeometry()


    def _populate_tree(self, tree: ComponentTree, kind: str, values: list):
        tree.blockSignals(True)
        tree.clear()
        doc_gen = getattr(self.document, "element_id_generator", None) if self.document else None
        for i, val in enumerate(values):
            if not isinstance(val, dict):
                continue
            ref = ComponentRef(self.tree_item, kind, i)
            raw_class = val.get("_class", "")
            title = prettify_class_name(raw_class)

            # Ensure every modifier/criterion has a valid m_nElementID assigned
            eid = val.get("m_nElementID")
            if eid is None or not isinstance(eid, int):
                if doc_gen is not None:
                    eid = doc_gen.get_element_id(val)
                else:
                    from gui.widgets.element_id import get_ElementID
                    eid = get_ElementID(val)
                val["m_nElementID"] = eid

            titem = QTreeWidgetItem()
            titem.setText(0, title)
            titem.setText(1, f"ID:{eid}")
            titem.setForeground(1, QBrush(theme.qcolor("#6d6d6d")))
            titem.setTextAlignment(1, Qt.AlignLeft | Qt.AlignVCenter)
            base_icon = _component_icon(kind, raw_class)
            comp_icon = make_composite_icon(base_icon, val, size=18)
            titem.setIcon(0, comp_icon)

            enabled_val = val.get("m_bEnabled", True)
            if enabled_val is False or enabled_val == "false":
                titem.setForeground(0, QBrush(theme.qcolor("#777777")))

            titem.setData(0, Qt.UserRole, ref)
            tree.addTopLevelItem(titem)
        tree.blockSignals(False)
        tree.refresh_height()

    def _select_ref(self, ref: ComponentRef | None, emit_signal: bool = True):
        if ref is None or getattr(ref, "item", None) is None:
            self.elem_row.set_selected(False)
            self._select_in_tree(self.modifiers_tree, None)
            self._select_in_tree(self.criteria_tree, None)
            if emit_signal:
                self.componentSelected.emit(None)
            return
        self.elem_row.set_selected(ref.kind == "element")
        self._select_in_tree(self.modifiers_tree, ref if ref.kind == "modifier" else None)
        self._select_in_tree(self.criteria_tree, ref if ref.kind == "criterion" else None)
        if emit_signal:
            self.componentSelected.emit(ref)

    def _select_in_tree(self, tree: ComponentTree, ref):
        tree.blockSignals(True)
        tree.clearSelection()
        if ref is not None:
            for i in range(tree.topLevelItemCount()):
                titem = tree.topLevelItem(i)
                if titem.data(0, Qt.UserRole) == ref:
                    tree.setCurrentItem(titem)
                    titem.setSelected(True)
                    break
        tree.blockSignals(False)


    def _on_elem_selected(self, ref: ComponentRef):
        self.modifiers_tree.blockSignals(True)
        self.modifiers_tree.clearSelection()
        self.modifiers_tree.blockSignals(False)
        self.criteria_tree.blockSignals(True)
        self.criteria_tree.clearSelection()
        self.criteria_tree.blockSignals(False)
        self.elem_row.set_selected(True)
        self.componentSelected.emit(ref)

    def _on_modifiers_selection_changed(self):
        items = self.modifiers_tree.selectedItems()
        if not items:
            return
        self.elem_row.set_selected(False)
        self.criteria_tree.blockSignals(True)
        self.criteria_tree.clearSelection()
        self.criteria_tree.blockSignals(False)
        ref = items[-1].data(0, Qt.UserRole)
        if ref is not None:
            self.componentSelected.emit(ref)

    def _on_criteria_selection_changed(self):
        items = self.criteria_tree.selectedItems()
        if not items:
            return
        self.elem_row.set_selected(False)
        self.modifiers_tree.blockSignals(True)
        self.modifiers_tree.clearSelection()
        self.modifiers_tree.blockSignals(False)
        ref = items[-1].data(0, Qt.UserRole)
        if ref is not None:
            self.componentSelected.emit(ref)


    def _on_add_modifier(self):
        if not self.tree_item:
            return
        items = operators_list + filters_list
        hide_experimental = get_settings_bool('SmartPropEditor', 'hide_experimental', True)
        if hide_experimental:
            items = [
                item for item in items
                if not any(v.get('_WARN_NOT_VERIFIED') for v in item.values() if isinstance(v, dict))
            ]
        menu = PopupMenu(items, add_once=False, window_name="SPE_add_modifier")
        menu.add_property_signal.connect(lambda name, value: self._add_component_dict("modifier", value))
        menu.show()

    def _on_add_criterion(self):
        if not self.tree_item:
            return
        items = list(selection_criteria_list)
        hide_experimental = get_settings_bool('SmartPropEditor', 'hide_experimental', True)
        if hide_experimental:
            items = [
                item for item in items
                if not any(v.get('_WARN_NOT_VERIFIED') for v in item.values() if isinstance(v, dict))
            ]
        menu = PopupMenu(items, add_once=False, window_name="SPE_add_criterion")
        menu.add_property_signal.connect(lambda name, value: self._add_component_dict("criterion", value))
        menu.show()

    def _add_component_dict(self, group_type: str, item_dict: Any):
        if isinstance(item_dict, str):
            try:
                item_dict = ast.literal_eval(item_dict)
            except Exception:
                return
        if not isinstance(item_dict, dict):
            return
        self._add_component_dicts("modifier" if group_type == "modifier" else "criterion", [item_dict])

    def _add_component_dicts(self, group_type: str, item_dicts: list[dict], insert_after_idx: int = -1):
        if not self.tree_item or not item_dicts:
            return

        norm_group = "modifier" if group_type == "modifier" else "criterion"
        old_data = fast_deepcopy(self.tree_item.data(0, Qt.UserRole))
        new_data = fast_deepcopy(old_data)
        container_key = "m_Modifiers" if norm_group == "modifier" else "m_SelectionCriteria"
        arr = new_data.setdefault(container_key, [])

        doc_gen = getattr(self.document, "element_id_generator", None) if self.document else None

        if insert_after_idx < 0 or insert_after_idx >= len(arr):
            target_idx = len(arr)
        else:
            target_idx = insert_after_idx + 1

        added_refs = []
        for offset, item_dict in enumerate(item_dicts):
            new_comp = fast_deepcopy(item_dict)
            if "m_bEnabled" not in new_comp:
                new_comp["m_bEnabled"] = True

            # Clear m_nElementID to force generation of a new unique ID
            new_comp["m_nElementID"] = None
            if doc_gen is not None:
                eid = doc_gen.get_element_id(new_comp)
            else:
                from gui.widgets.element_id import get_ElementID
                eid = get_ElementID(new_comp)
            new_comp["m_nElementID"] = eid

            curr_insert = target_idx + offset
            arr.insert(curr_insert, new_comp)
            added_refs.append(ComponentRef(self.tree_item, norm_group, curr_insert))

        self.tree_item.setData(0, Qt.UserRole, new_data)
        self._push_snapshot_command(old_data, new_data)
        self.rebuild()

        if added_refs:
            self._select_ref(added_refs[-1])

    def _on_paste_modifier(self):
        self._paste_component_for_group("modifier")

    def _on_paste_criterion(self):
        self._paste_component_for_group("selection_criteria")

    def _paste_component_for_group(self, target_group: str, insert_after_idx: int = -1):
        if not self.tree_item:
            return
        clip_text = QApplication.clipboard().text()
        clip_group, pasted_dicts = parse_component_clipboard(clip_text)
        if not pasted_dicts or not clip_group:
            return

        target_norm = "modifier" if target_group in ("modifier", "modifiers", "operators") else "criterion"
        clip_norm = "modifier" if clip_group in ("modifier", "modifiers", "operators") else "criterion"

        if target_norm == clip_norm:
            self._add_component_dicts(target_norm, pasted_dicts, insert_after_idx=insert_after_idx)


    def _copy_selected_from_tree(self, tree: ComponentTree):
        refs = [it.data(0, Qt.UserRole) for it in tree.selectedItems() if it.data(0, Qt.UserRole) is not None]
        if refs:
            self._copy_components(refs)

    def _cut_selected_from_tree(self, tree: ComponentTree):
        refs = [it.data(0, Qt.UserRole) for it in tree.selectedItems() if it.data(0, Qt.UserRole) is not None]
        if refs:
            self._copy_components(refs)
            self._delete_components(refs)

    def _duplicate_selected_from_tree(self, tree: ComponentTree):
        refs = [it.data(0, Qt.UserRole) for it in tree.selectedItems() if it.data(0, Qt.UserRole) is not None]
        if refs:
            self._duplicate_components(refs)

    def _copy_component(self, ref: ComponentRef):
        """Single-ref copy API for backward compatibility."""
        self._copy_components([ref])

    def _copy_components(self, refs: list[ComponentRef]):
        if not self.tree_item or not refs:
            return
        data = self.tree_item.data(0, Qt.UserRole)
        if not isinstance(data, dict):
            return

        valid_refs = [r for r in refs if r is not None]
        if not valid_refs:
            return

        valid_refs = sorted(valid_refs, key=lambda x: getattr(x, 'index', 0))
        target_dicts = []
        group_type = "modifier"
        for ref in valid_refs:
            target = ref.target(data)
            if target:
                target_dicts.append(target)
                group_type = "modifier" if ref.kind == "modifier" else ("selection_criteria" if ref.kind in ("criterion", "selection_criteria") else "element")

        if not target_dicts:
            return

        if len(target_dicts) == 1:
            target = target_dicts[0]
            class_name = target.get("_class", "")
            clip_str = f"{CLIPBOARD_PREFIX};;{class_name};;{repr(target)};;{group_type}"
        else:
            clip_str = f"{CLIPBOARD_BATCH_PREFIX};;batch;;{repr(target_dicts)};;{group_type}"

        QApplication.clipboard().setText(clip_str)

    def _duplicate_components(self, refs: list[ComponentRef]):
        if not self.tree_item or not refs:
            return
        data = self.tree_item.data(0, Qt.UserRole)
        if not isinstance(data, dict):
            return

        valid_refs = [r for r in refs if r is not None and r.kind != "element"]
        if not valid_refs:
            return

        group_type = "modifier" if valid_refs[0].kind == "modifier" else "criterion"
        container_key = "m_Modifiers" if group_type == "modifier" else "m_SelectionCriteria"
        live_arr = data.get(container_key) or []

        dup_dicts = []
        max_idx = -1
        for r in sorted(valid_refs, key=lambda x: x.index):
            if 0 <= r.index < len(live_arr):
                dup_dicts.append(fast_deepcopy(live_arr[r.index]))
                max_idx = max(max_idx, r.index)

        if dup_dicts:
            self._add_component_dicts(group_type, dup_dicts, insert_after_idx=max_idx)


    def _get_active_tree(self) -> ComponentTree | None:
        focused = QApplication.focusWidget()
        if focused is not None:
            if focused == self.modifiers_tree or self.modifiers_tree.isAncestorOf(focused):
                return self.modifiers_tree
            if focused == self.criteria_tree or self.criteria_tree.isAncestorOf(focused):
                return self.criteria_tree
        if self.modifiers_tree.selectedItems():
            return self.modifiers_tree
        if self.criteria_tree.selectedItems():
            return self.criteria_tree
        return self.modifiers_tree

    def _copy_focused(self):
        tree = self._get_active_tree()
        if tree:
            self._copy_selected_from_tree(tree)

    def _cut_focused(self):
        tree = self._get_active_tree()
        if tree:
            self._cut_selected_from_tree(tree)

    def _paste_focused(self):
        tree = self._get_active_tree()
        group_type = "modifier" if tree is self.modifiers_tree else "selection_criteria"
        sel = tree.selectedItems() if tree else []
        ref = sel[-1].data(0, Qt.UserRole) if sel else None
        idx = ref.index if ref else -1
        self._paste_component_for_group(group_type, insert_after_idx=idx)

    def _duplicate_focused(self):
        tree = self._get_active_tree()
        if tree:
            self._duplicate_selected_from_tree(tree)

    def _delete_focused(self):
        tree = self._get_active_tree()
        if tree:
            items = tree.selectedItems()
            if items:
                self._delete_components([it.data(0, Qt.UserRole) for it in items if it.data(0, Qt.UserRole) is not None])

    def _tree_context_menu(self, tree: ComponentTree, pos):
        tree.setFocus()
        item = tree.itemAt(pos)
        if item is not None and not item.isSelected():
            tree.setCurrentItem(item)
            item.setSelected(True)

        ref = item.data(0, Qt.UserRole) if item else None

        menu = QMenu(tree)
        act_copy = menu.addAction("Copy (Ctrl+C)")
        act_cut = menu.addAction("Cut (Ctrl+X)")

        clip_text = QApplication.clipboard().text()
        clip_group, comp_dicts = parse_component_clipboard(clip_text)
        target_norm = "modifier" if tree is self.modifiers_tree else "criterion"
        clip_norm = "modifier" if clip_group == "modifier" else ("criterion" if clip_group == "selection_criteria" else None)
        has_clip = bool(comp_dicts and target_norm == clip_norm)
        act_paste = menu.addAction("Paste (Ctrl+V)")
        act_paste.setEnabled(has_clip)

        act_dup = menu.addAction("Duplicate (Ctrl+D)")
        menu.addSeparator()
        act_delete = menu.addAction("Delete (Delete)")

        has_selection = len(tree.selectedItems()) > 0
        act_copy.setEnabled(has_selection)
        act_cut.setEnabled(has_selection)
        act_dup.setEnabled(has_selection)
        act_delete.setEnabled(has_selection)

        global_pos = tree.viewport().mapToGlobal(pos)
        action = menu.exec_(global_pos)
        if action == act_copy:
            self._copy_selected_from_tree(tree)
        elif action == act_cut:
            self._cut_selected_from_tree(tree)
        elif action == act_paste:
            group_type = "modifier" if tree is self.modifiers_tree else "selection_criteria"
            insert_idx = ref.index if ref else -1
            self._paste_component_for_group(group_type, insert_after_idx=insert_idx)
        elif action == act_dup:
            self._duplicate_selected_from_tree(tree)
        elif action == act_delete:
            refs = [it.data(0, Qt.UserRole) for it in tree.selectedItems() if it.data(0, Qt.UserRole) is not None]
            self._delete_components(refs)


    def _on_modifiers_delete_requested(self, items: list):
        self._delete_components([it.data(0, Qt.UserRole) for it in items if it.data(0, Qt.UserRole) is not None])

    def _on_criteria_delete_requested(self, items: list):
        self._delete_components([it.data(0, Qt.UserRole) for it in items if it.data(0, Qt.UserRole) is not None])

    def _on_delete_component(self, ref: ComponentRef):
        """Delete a single component. Kept as a direct, single-ref API distinct
        from the batch _delete_components used by the trees' multi-select delete."""
        self._delete_components([ref])

    def _delete_components(self, refs: list):
        if not self.tree_item or not refs:
            return
        old_data = fast_deepcopy(self.tree_item.data(0, Qt.UserRole))
        new_data = fast_deepcopy(old_data)

        by_container: dict[str, list[int]] = {}
        for ref in refs:
            if ref is None or ref.kind == "element":
                continue
            key = ref.container()
            if not key:
                continue
            by_container.setdefault(key, []).append(ref.index)

        touched = False
        for key, indices in by_container.items():
            arr = new_data.get(key)
            if not isinstance(arr, list):
                continue
            # Remove highest indices first so earlier removals don't shift later ones.
            for idx in sorted(set(indices), reverse=True):
                if 0 <= idx < len(arr):
                    arr.pop(idx)
                    touched = True

        if not touched:
            return

        self.tree_item.setData(0, Qt.UserRole, new_data)
        self._push_snapshot_command(old_data, new_data)
        self.rebuild()
        self._select_ref(ComponentRef(self.tree_item, "element", -1))


    def _on_modifiers_reordered(self):
        self._apply_tree_order(self.modifiers_tree, "m_Modifiers")

    def _on_criteria_reordered(self):
        self._apply_tree_order(self.criteria_tree, "m_SelectionCriteria")

    def _apply_tree_order(self, tree: ComponentTree, container_key: str):
        if not self.tree_item:
            return
        old_data = fast_deepcopy(self.tree_item.data(0, Qt.UserRole))
        live_arr = old_data.get(container_key) or []

        # Read the *current* item order from the tree, but pull each item's
        # actual value fresh from live_arr (via the original index each tree
        # item was populated with) rather than from a snapshot cached on the
        # item at populate time. That snapshot goes stale the moment the user
        # edits a property in Section 2 (which updates the real data but never
        # rebuilds this tree, by design — see set_field callers), so reordering
        # was overwriting real edits with whatever the value looked like when
        # the tree was last rebuilt, silently discarding them.
        new_order = []
        for i in range(tree.topLevelItemCount()):
            ref = tree.topLevelItem(i).data(0, Qt.UserRole)
            if ref is not None and 0 <= ref.index < len(live_arr):
                new_order.append(fast_deepcopy(live_arr[ref.index]))
        if not new_order:
            return

        new_data = fast_deepcopy(old_data)
        new_data[container_key] = new_order
        if new_data == old_data:
            return

        self.tree_item.setData(0, Qt.UserRole, new_data)
        self._push_snapshot_command(old_data, new_data)
        self.rebuild()


    def _reorder_component(self, kind: str, from_idx: int, to_idx: int):
        if not self.tree_item:
            return
        old_data = fast_deepcopy(self.tree_item.data(0, Qt.UserRole))
        new_data = fast_deepcopy(old_data)
        container_key = "m_Modifiers" if kind == "modifier" else "m_SelectionCriteria"
        arr = new_data.get(container_key, [])

        if 0 <= from_idx < len(arr) and 0 <= to_idx < len(arr):
            item = arr.pop(from_idx)
            arr.insert(to_idx, item)
            self.tree_item.setData(0, Qt.UserRole, new_data)
            self._push_snapshot_command(old_data, new_data)
            self.rebuild()
            self._select_ref(ComponentRef(self.tree_item, kind, to_idx))

    def _push_snapshot_command(self, old_data: dict, new_data: dict):
        if self.document and hasattr(self.document, "undo_stack") and self.document.undo_stack:
            cmd = PropertySnapshotCommand(self.document, self.tree_item, old_data, new_data)
            self.document.undo_stack.push(cmd)
