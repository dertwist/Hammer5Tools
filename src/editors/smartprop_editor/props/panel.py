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

from src.editors.smartprop_editor.props.components import ComponentList
from src.editors.smartprop_editor.props.help import HelpPanel
from src.editors.smartprop_editor.props.model import ComponentRef
from src.editors.smartprop_editor.props.legacy_property_list import LegacyPropertyList

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

        # Allow HelpPanel (index 1) to be collapsed down to 0
        self.splitter.setCollapsible(1, True)

        # Stretch factors: properties get the room, help strip stays preferred
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([420, 80])

        root.addWidget(self.components_list, 0)
        root.addWidget(self.splitter, 1)

        # ── Wire signals ───────────────────────────────────────────────────
        self.components_list.componentSelected.connect(self._on_component_selected)
        self.property_list.propertySelected.connect(self.help_panel.set_property_help)

    # ── Public API ──────────────────────────────────────────────────────────

    def set_element(self, tree_item) -> None:
        """Point property panel at hierarchy tree item."""
        self.current_item = tree_item
        self.components_list.set_element(tree_item)
        if not tree_item:
            self.property_list.set_components([])
            self.help_panel.clear_help()

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
