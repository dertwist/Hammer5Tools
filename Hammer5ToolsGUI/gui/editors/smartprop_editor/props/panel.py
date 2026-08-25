"""
SmartPropPropertyPanel — Combined 3-section Property Panel.

Layout (top-to-bottom):
  ┌─────────────────────────────────────┐
  │  ▼ Components                       │  ← Section 1 (ComponentList) — sized
  │                                      │    to its own content, not resizable
  ├─────────────────────────────────────┤    against Section 2 (no splitter here)
  │  ▼ Properties                       │  ← Section 2 (LegacyPropertyList)
  ├─────────────────────────────────────┤
  │  Title / Body description …         │  ← Section 3 (HelpPanel)
  └─────────────────────────────────────┘

Section 1 sits in the plain outer layout, sized to its own content. Sections 2 & 3
live inside a QSplitter so the user can trade space between properties
and the help strip.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFrame,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gui.editors.smartprop_editor.props.components import ComponentList
from gui.editors.smartprop_editor.props.help import HelpPanel
from gui.editors.smartprop_editor.props.model import ComponentRef
from gui.editors.smartprop_editor.props.legacy_property_list import LegacyPropertyList

# ── Colours ────────────────────────────────────────────────────────────────
_HDR_BG      = "#2c2c2c"
_HDR_BG_HVR  = "#363636"
_HDR_FG      = "#cccccc"
_HDR_BORDER  = "#434343"
_ARROW_OPEN  = "▼"
_ARROW_SHUT  = "►"


class _CollapsibleSection(QWidget):
    """
    A header bar that toggles the visibility of a child content widget.
    When collapsed the section shrinks to just the header height.
    When expanded it shows the content; size hint is driven by content
    so the splitter allocates only as much space as the content needs.
    """

    _HEADER_H = 22

    def __init__(self, title: str, content: QWidget, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar ─────────────────────────────────────────────────────
        self._header = QFrame(self)
        self._header.setFixedHeight(self._HEADER_H)
        self._header.setStyleSheet(f"""
            QFrame {{
                background-color: {_HDR_BG};
                border-bottom: 1px solid {_HDR_BORDER};
            }}
            QFrame:hover {{
                background-color: {_HDR_BG_HVR};
            }}
        """)
        hdr_layout = QVBoxLayout(self._header)
        hdr_layout.setContentsMargins(4, 0, 4, 0)
        hdr_layout.setSpacing(0)

        self._toggle_btn = QToolButton(self._header)
        self._toggle_btn.setText(f"  {_ARROW_OPEN}  {title}")
        self._toggle_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)   # expanded by default
        self._toggle_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._toggle_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                text-align: left;
                color: {_HDR_FG};
                font: 580 8pt "Segoe UI";
                padding: 0px 2px;
            }}
        """)
        self._toggle_btn.toggled.connect(self._on_toggled)
        hdr_layout.addWidget(self._toggle_btn)
        root.addWidget(self._header)

        # ── Content ────────────────────────────────────────────────────────
        self._content = content
        self._content.setParent(self)
        root.addWidget(self._content, 1)

    def sizeHint(self):
        h = self._HEADER_H
        if self._toggle_btn.isChecked() and self._content.isVisible():
            h += self._content.sizeHint().height()
        s = super().sizeHint()
        return QSize(s.width(), h)

    def minimumSizeHint(self):
        h = self._HEADER_H
        if self._toggle_btn.isChecked() and self._content.isVisible():
            h += self._content.minimumSizeHint().height()
        s = super().minimumSizeHint()
        return QSize(s.width(), h)

    def _on_toggled(self, checked: bool):
        arrow = _ARROW_OPEN if checked else _ARROW_SHUT
        title = self._toggle_btn.text().split("  ", 2)[-1]
        self._toggle_btn.setText(f"  {arrow}  {title}")
        self._content.setVisible(checked)
        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()

    def is_expanded(self) -> bool:
        return self._toggle_btn.isChecked()

    def set_expanded(self, value: bool):
        self._toggle_btn.setChecked(value)


# ── Main Panel ──────────────────────────────────────────────────────────────

class SmartPropPropertyPanel(QWidget):
    """Unified 3-section SmartProp Property Editor Panel."""

    _HELP_MIN_H = 80    # px — minimum height for the help strip

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.document = document
        self.current_item = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Section 1: Component List ──────────────────────────────────────
        self.components_list = ComponentList(document=self.document, parent=self)
        self.components_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # ── Section 2: Property List ───────────────────────────────────────
        self.property_list = LegacyPropertyList(
            document=self.document, parent=self
        )
        self.property_panel = self.property_list

        # ── Section 3: Help strip ──────────────────────────────────────────
        self.help_panel = HelpPanel(parent=self)
        self.help_panel.setMinimumHeight(0)
        self.help_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # ── Splitter holds Section 2 + Section 3 ────────────────────────────
        self.splitter = QSplitter(Qt.Vertical, self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(4)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3b3b3b;
            }
            QSplitter::handle:hover {
                background-color: #4A7EBB;
            }
        """)
        self.splitter.addWidget(self.property_list)
        self.splitter.addWidget(self.help_panel)

        # Allow HelpPanel (index 1) to be collapsed down to 0, PropertyList never collapsed
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, True)

        # Stretch factors: properties get the room, help strip stays preferred
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([600, 110])

        root.addWidget(self.components_list, 0)
        root.addWidget(self.splitter, 1)

        # ── Wire signals ───────────────────────────────────────────────────
        self.components_list.componentSelected.connect(self._on_component_selected)
        self.components_list.addNoteRequested.connect(self._on_add_note_requested)
        self.property_list.propertySelected.connect(self.help_panel.set_property_help)
        self.help_panel.noteEdited.connect(self._on_note_edited)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_splitter_initialized", False):
            self._splitter_initialized = True
            total_h = self.height()
            help_h = 110
            prop_h = max(100, total_h - help_h)
            self.splitter.setSizes([prop_h, help_h])

    # ── Public API ──────────────────────────────────────────────────────────

    def set_element(self, tree_item) -> None:
        """Point property panel at hierarchy tree item."""
        self.current_item = tree_item
        self.components_list.set_element(tree_item)
        if not tree_item:
            self.property_list.set_components([])
            self.help_panel.clear_help()

    @property
    def selected_ref(self) -> ComponentRef | None:
        return self.components_list.selected_ref

    def selected_refs(self) -> list[ComponentRef]:
        return self.components_list.selected_refs()

    def apply_external_data(self, item, new_data, changed_keys=()):
        """Forward external updates (undo/redo) to component list and property list."""
        if item is self.current_item:
            structural = not changed_keys or any(
                k in ("m_Modifiers", "m_SelectionCriteria")
                or (k.startswith("m_Modifiers[") and "." not in k)
                or (k.startswith("m_SelectionCriteria[") and "." not in k)
                for k in changed_keys
            )
            if structural:
                self.components_list.rebuild()
            selected = self.components_list.selected_ref
            if selected is not None:
                self.help_panel.set_component_help(selected)
        self.property_list.apply_external_data(item, new_data, changed_keys)

    # ── Internal slots ──────────────────────────────────────────────────────

    def _on_component_selected(self, ref: ComponentRef | None):
        if not ref:
            self.property_list.set_components([])
            self.help_panel.clear_help()
            return

        refs = self.components_list.selected_refs()
        self.property_list.set_components(refs)
        self.help_panel.set_component_help(ref)

    def _on_add_note_requested(self, ref: ComponentRef):
        self.help_panel.open_note(ref)

    def _on_note_edited(self, ref: ComponentRef, note_text: str):
        if self.document is None or ref.item is None:
            return
        item = ref.item
        from gui.common import fast_deepcopy
        old_data = fast_deepcopy(item.data(0, Qt.UserRole))
        if not isinstance(old_data, dict):
            return
        new_data = fast_deepcopy(old_data)
        target = ref.target(new_data)
        if not isinstance(target, dict):
            return

        from gui.editors.smartprop_editor.note_utils import set_note
        set_note(target, note_text)

        if new_data == old_data:
            return

        item.setData(0, Qt.UserRole, new_data)

        # Update Section 1 headers/rows
        if self.components_list and self.components_list.tree_item is item:
            if ref.kind == "element":
                self.components_list.elem_row.update_data(new_data)
            else:
                self.components_list.modifiers_tree.viewport().update()
                self.components_list.criteria_tree.viewport().update()

        # Update main hierarchy tree
        if hasattr(self.document, "ui") and hasattr(self.document.ui, "tree_hierarchy_widget"):
            tree = self.document.ui.tree_hierarchy_widget
            if hasattr(tree, "viewport"):
                tree.viewport().update()

        self.document._modified = True
        self.document._edited.emit()

        stack = getattr(self.document, "undo_stack", None)
        if stack is not None and not getattr(self.document, "_property_undo_guard", 0):
            from gui.editors.smartprop_editor.commands import PropertySnapshotCommand
            stack.push(PropertySnapshotCommand(self.document, item, old_data, new_data))
