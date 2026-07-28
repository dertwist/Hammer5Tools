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
from PySide6.QtGui import QAction, QFont, QIcon, QMouseEvent, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.common import fast_deepcopy
from src.editors.smartprop_editor._common import get_clean_class_name
from src.editors.smartprop_editor.commands import PropertySnapshotCommand
from src.editors.smartprop_editor.objects import (
    filters_list,
    operators_list,
    selection_criteria_list,
)
from src.editors.smartprop_editor.properties_group_frame import PropertiesGroupFrame
from src.editors.smartprop_editor.property import compact
from src.editors.smartprop_editor.props.model import ComponentRef
from src.styles.property_icons import IconCache
from src.widgets.popup_menu.main import PopupMenu
from src.widgets.tree import HierarchyTreeWidget


# Clipboard string pattern for SmartProp property items
CLIPBOARD_PREFIX = "hammer5tools:smartprop_editor_property"


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


_TRANSPARENT_LABEL = "QLabel { background: transparent; padding: 0px; margin: 0px; border: none; }"


class ElementRowWidget(QFrame):
    """The single, always-present row for the element itself (row 0). Unlike
    modifiers/criteria it's never reordered or deleted, so it stays a plain
    row rather than living inside a HierarchyTreeWidget."""

    selected = Signal(object)  # ComponentRef

    SELECTION_COLOR = "#4F5259"
    HOVER_COLOR = "#33363D"

    def __init__(self, ref: ComponentRef, parent=None):
        super().__init__(parent)
        self.ref = ref
        self._is_selected = False

        self.setFrameShape(QFrame.NoFrame)
        self.setFixedHeight(26)
        self.setFocusPolicy(Qt.ClickFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        self.lbl_icon = QLabel(self)
        self.lbl_icon.setFixedSize(18, 18)
        self.lbl_icon.setScaledContents(True)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet(_TRANSPARENT_LABEL)
        layout.addWidget(self.lbl_icon)

        self.lbl_title = QLabel(self)
        font = QFont()
        font.setPixelSize(12)
        font.setBold(True)
        self.lbl_title.setFont(font)
        self.lbl_title.setStyleSheet("QLabel { background: transparent; border: none; }")
        layout.addWidget(self.lbl_title)

        self.lbl_hint = QLabel(self)
        font_hint = QFont()
        font_hint.setPixelSize(11)
        self.lbl_hint.setFont(font_hint)
        self.lbl_hint.setStyleSheet("QLabel { background: transparent; border: none; color: #888888; }")
        self.lbl_hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.lbl_hint, 1)

        self._update_appearance()

    def update_data(self, data: dict):
        if not isinstance(data, dict):
            return
        raw_class = data.get("_class", "")
        self.lbl_title.setText(prettify_class_name(raw_class))
        if self.ref.item and hasattr(self.ref.item, "icon") and not self.ref.item.icon(0).isNull():
            icon = self.ref.item.icon(0)
        else:
            icon = IconCache.get_node_icon("element")
        self.lbl_icon.setPixmap(icon.pixmap(18, 18))
        self.lbl_hint.setText(get_summary_hint(data))

    def set_selected(self, selected: bool):
        if self._is_selected != selected:
            self._is_selected = selected
            self._update_appearance()

    def is_selected(self) -> bool:
        return self._is_selected

    def _update_appearance(self):
        if self._is_selected:
            self.setStyleSheet(f"ElementRowWidget {{ background-color: {self.SELECTION_COLOR}; border-radius: 2px; }}")
        else:
            self.setStyleSheet(
                f"ElementRowWidget {{ background-color: transparent; border-radius: 2px; }}"
                f"ElementRowWidget:hover {{ background-color: {self.HOVER_COLOR}; }}"
            )

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.ref)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        act_copy = QAction("Copy Component", self)
        menu.addAction(act_copy)
        if menu.exec_(event.globalPos()) == act_copy:
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
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAlternatingRowColors(True)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.setStyleSheet(f"""
            QTreeWidget {{ background: transparent; border: none; outline: none; }}
            QTreeWidget::item {{ height: {self.ROW_H - 2}px; border: none; background: transparent; }}
            QTreeWidget::item:alternate {{ background-color: {compact.BG_ALT}; }}
            QTreeWidget::item:selected {{ background-color: #4F5259; }}
            QTreeWidget::item:hover {{ background-color: #33363D; }}
            QTreeWidget::branch {{ background: transparent; border: none; }}
        """)

    def dropEvent(self, event):
        super().dropEvent(event)
        # Defer: ComponentList.rebuild() (triggered downstream of reordered)
        # calls tree.clear(), destroying every QTreeWidgetItem — including the
        # ones this very dropEvent's Qt-native drag-and-drop machinery is still
        # unwinding/cleaning up in the same call stack. Tearing that down
        # synchronously crashes; let the drop fully finish first.
        QTimer.singleShot(0, self.reordered.emit)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            items = self.selectedItems()
            if items:
                self.deleteRequested.emit(items)
                return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        # Always sized to fit its own content exactly (refresh_height), so
        # there's never anything to scroll internally. Unlike mouse press,
        # ignoring a QWheelEvent does *not* get retried on the parent widget —
        # forward it explicitly to the nearest QScrollArea ancestor's viewport
        # (the actual scroll target; the QScrollArea widget itself won't scroll
        # from a forwarded event, only its viewport will).
        w = self.parentWidget()
        while w is not None:
            if isinstance(w, QScrollArea):
                QApplication.sendEvent(w.viewport(), event)
                return
            w = w.parentWidget()
        event.ignore()

    def refresh_height(self):
        self.setFixedHeight(max(self.topLevelItemCount(), 0) * self.ROW_H + 4)
        # setFixedHeight() is a no-op (no resize event, no implicit repaint) when
        # the item count — and therefore the computed height — didn't change,
        # e.g. after a reorder. The item model is already correct at that point
        # (geometry queries return the right rects), but the *paint* can stay
        # stale until something else forces a repaint (moving/selecting another
        # row), making the last row appear to vanish in the meantime. Force
        # both explicitly rather than relying on an implicit resize.
        self.doItemsLayout()
        self.viewport().update()


class ComponentList(QWidget):
    """Section 1 component list widget."""

    componentSelected = Signal(object)  # ComponentRef or None when empty

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
        self.criteria_tree.customContextMenuRequested.connect(
            lambda pos: self._tree_context_menu(self.criteria_tree, pos)
        )
        self.container_layout.addWidget(self.criteria_tree)

        self.container_layout.addStretch(1)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_element(self, tree_item) -> None:
        """Rebuild component list from hierarchy tree item."""
        self.tree_item = tree_item
        self.rebuild()
        self._select_ref(ComponentRef(self.tree_item, "element", -1), emit_signal=True)

    def selected_refs(self) -> list[ComponentRef]:
        """Return list of currently selected ComponentRef objects, read live
        from whichever surface (element row / either tree) currently holds
        the selection."""
        refs: list[ComponentRef] = []
        if self.elem_row.is_selected():
            refs.append(self.elem_row.ref)
        for it in self.modifiers_tree.selectedItems():
            ref = it.data(0, Qt.UserRole)
            if ref is not None:
                refs.append(ref)
        for it in self.criteria_tree.selectedItems():
            ref = it.data(0, Qt.UserRole)
            if ref is not None:
                refs.append(ref)
        return refs

    def sizeHint(self):
        """Report height based on actual content — uncapped, same treatment as
        the property panel below it — so the layout expands this section to
        fit however many components there are instead of truncating it at an
        arbitrary row count. The internal scroll area (see __init__) is still
        there as a fallback for whatever the window itself can't fit."""
        MARGIN = 6
        h = MARGIN
        for i in range(self.container_layout.count()):
            item = self.container_layout.itemAt(i)
            w = item.widget() if item else None
            if w is None:
                continue
            # ComponentTree.sizeHint() is QTreeWidget's default — unrelated to
            # the fixed height refresh_height() actually sets — so it would
            # silently reintroduce a cap-like mismatch here. Its current
            # height() (and every other child's here) is authoritative once
            # laid out; only fall back to sizeHint() before that's happened.
            wh = w.height()
            if wh <= 0:
                sh = w.sizeHint()
                wh = sh.height() if sh.isValid() else ComponentTree.ROW_H
            h += wh
        h = max(ComponentTree.ROW_H * 2 + MARGIN, h)
        s = super().sizeHint()
        return QSize(s.width(), h)

    def minimumSizeHint(self):
        s = super().minimumSizeHint()
        return QSize(s.width(), 54)

    def rebuild(self):
        """Refresh element row + both trees from current tree_item data."""
        if not self.tree_item:
            self.elem_row.ref = ComponentRef(None, "element", -1)
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

    # ── Internal: populate / select ─────────────────────────────────────────────

    def _populate_tree(self, tree: ComponentTree, kind: str, values: list):
        tree.blockSignals(True)
        tree.clear()
        for i, val in enumerate(values):
            if not isinstance(val, dict):
                continue
            ref = ComponentRef(self.tree_item, kind, i)
            raw_class = val.get("_class", "")
            titem = QTreeWidgetItem()
            titem.setText(0, prettify_class_name(raw_class))
            titem.setText(1, get_summary_hint(val))
            titem.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            titem.setIcon(0, _component_icon(kind, raw_class))
            titem.setData(0, Qt.UserRole, ref)
            tree.addTopLevelItem(titem)
        tree.blockSignals(False)
        tree.refresh_height()

    def _select_ref(self, ref: ComponentRef, emit_signal: bool = True):
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

    # ── Selection signal handlers ────────────────────────────────────────────

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

    # ── Add / Paste ──────────────────────────────────────────────────────────

    def _on_add_modifier(self):
        if not self.tree_item:
            return
        items = operators_list + filters_list
        menu = PopupMenu(items, add_once=False, window_name="SPE_add_modifier")
        menu.add_property_signal.connect(lambda name, value: self._add_component_dict("modifier", value))
        menu.show()

    def _on_add_criterion(self):
        if not self.tree_item:
            return
        menu = PopupMenu(selection_criteria_list, add_once=False, window_name="SPE_add_criterion")
        menu.add_property_signal.connect(lambda name, value: self._add_component_dict("criterion", value))
        menu.show()

    def _add_component_dict(self, group_type: str, item_dict: Any):
        if not self.tree_item:
            return
        if isinstance(item_dict, str):
            try:
                item_dict = ast.literal_eval(item_dict)
            except Exception:
                return
        if not isinstance(item_dict, dict):
            return

        new_comp = fast_deepcopy(item_dict)
        if "m_bEnabled" not in new_comp:
            new_comp["m_bEnabled"] = True

        old_data = fast_deepcopy(self.tree_item.data(0, Qt.UserRole))
        new_data = fast_deepcopy(old_data)
        container_key = "m_Modifiers" if group_type == "modifier" else "m_SelectionCriteria"
        arr = new_data.setdefault(container_key, [])
        arr.append(new_comp)

        self.tree_item.setData(0, Qt.UserRole, new_data)
        self._push_snapshot_command(old_data, new_data)
        self.rebuild()

        new_ref = ComponentRef(self.tree_item, "modifier" if group_type == "modifier" else "criterion", len(arr) - 1)
        self._select_ref(new_ref)

    def _on_paste_modifier(self):
        self._paste_component_for_group("modifier")

    def _on_paste_criterion(self):
        self._paste_component_for_group("selection_criteria")

    def _paste_component_for_group(self, target_group: str):
        if not self.tree_item:
            return
        clip_text = QApplication.clipboard().text()
        parts = clip_text.split(";;")
        if len(parts) < 4 or parts[0] != CLIPBOARD_PREFIX:
            return
        clip_group = parts[3]
        if clip_group != target_group and not (target_group == "selection_criteria" and clip_group == "criterion"):
            return
        try:
            val_dict = ast.literal_eval(parts[2])
        except Exception:
            return

        group_type = "modifier" if target_group == "modifier" else "criterion"
        self._add_component_dict(group_type, val_dict)

    # ── Copy ─────────────────────────────────────────────────────────────────

    def _copy_component(self, ref: ComponentRef):
        data = self.tree_item.data(0, Qt.UserRole) if self.tree_item else None
        target = ref.target(data) if isinstance(data, dict) else None
        if not target:
            return
        class_name = target.get("_class", "")
        group_type = "modifier" if ref.kind == "modifier" else ("selection_criteria" if ref.kind == "criterion" else "element")
        clip_str = f"{CLIPBOARD_PREFIX};;{class_name};;{repr(target)};;{group_type}"
        QApplication.clipboard().setText(clip_str)

    def _tree_context_menu(self, tree: ComponentTree, pos):
        item = tree.itemAt(pos)
        if item is None:
            return
        ref = item.data(0, Qt.UserRole)
        if ref is None:
            return
        if not item.isSelected():
            tree.setCurrentItem(item)
            item.setSelected(True)
        menu = QMenu(tree)
        act_copy = menu.addAction("Copy Component")
        act_delete = menu.addAction("Delete Component")
        action = menu.exec_(tree.viewport().mapToGlobal(pos))
        if action == act_copy:
            self._copy_component(ref)
        elif action == act_delete:
            refs = [it.data(0, Qt.UserRole) for it in tree.selectedItems() if it.data(0, Qt.UserRole) is not None]
            self._delete_components(refs)

    # ── Delete ───────────────────────────────────────────────────────────────

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

    # ── Reorder (from ComponentTree.reordered, after a drag-drop) ────────────

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

    # ── Reorder (direct, single-move API — kept for programmatic/test use) ──

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
