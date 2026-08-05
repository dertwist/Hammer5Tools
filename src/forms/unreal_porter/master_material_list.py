"""
The Materials tab's Master Material list.

Replaces the old QTableWidget: a table forced every control into a fixed grid
cell, so the shader picker, the slot summary and the per-master actions all had
to fit one row height and nothing could show what a mapping actually resolves
to. Each master material is now its own card that can lay out freely and
display the slot bindings its instances will inherit.
"""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox,
    QToolButton, QScrollArea,
)

from src.styles.common import apply_stylesheets
from .material_converter import _classify_textures

# material_remap_arrow.png is not in resources.qrc, so it is loaded from disk —
# same approach as src/widgets/model_browser/main.py. Resolves to src/icons/...
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_REMAP_ICON = os.path.join(_SRC_DIR, "icons", "tools", "modeldoc_editor",
                           "material_remap_arrow.png")

SHADERS = [
    "csgo_environment.vfx",
    "csgo_static_overlay.vfx",
    "csgo_foliage.vfx",
    "csgo_glass.vfx",
    "csgo_character.vfx",
    "complex.vfx",
]

_CHANNEL_LABELS = {"r": "R", "g": "G", "b": "B", "a": "A"}


def describe_bindings(textures: dict, slot_overrides: dict = None) -> str:
    """One-line summary of what the current mapping resolves to, e.g.
    'color←Diffuse  normal←Normal  rough←SRMH.G  metal←SRMH.B'."""
    picks = _classify_textures(textures or {}, slot_overrides)
    if not picks:
        return "No texture slots resolved — this material will convert flat."
    parts = []
    for slot in sorted(picks):
        param, _path, channel = picks[slot]
        suffix = f".{_CHANNEL_LABELS[channel]}" if channel else ""
        parts.append(f"{slot}←{param}{suffix}")
    return "   ".join(parts)


class MasterMaterialCard(QFrame):
    """One Master Material: whether to convert it, its target CS2 shader, and
    the texture-slot mapping every instance under it inherits.

    Row layout: [checkbox] | <name> (instances) | [shader combo] | [remap btn].
    Cards alternate two background tones so the eye can track a row across a
    long list.
    """

    map_slots_requested = Signal(str)

    def __init__(self, master_name: str, info: dict, parity: bool = False, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.master_name = master_name
        # Zebra stripe — alternate-background-color the card itself. Scoped to
        # MasterMaterialCard so it does not repaint its child widgets.
        bg = "#1D1D1F" if parity else "#1C1C1C"
        self.setStyleSheet(f"MasterMaterialCard {{ background-color: {bg}; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(4)

        head = QHBoxLayout()
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.setToolTip("Convert the Material Instances under this Master Material")
        head.addWidget(self.checkbox)

        count = info.get("count", len(info.get("instances", [])))
        title = QLabel(f"<b>{master_name}</b> ({count} instance{'s' if count != 1 else ''})")
        head.addWidget(title)
        head.addStretch(1)

        self.shader_combo = QComboBox()
        self.shader_combo.addItems(SHADERS)
        predicted = info.get("shader", "csgo_environment.vfx")
        idx = self.shader_combo.findText(predicted)
        if idx >= 0:
            self.shader_combo.setCurrentIndex(idx)
        self.shader_combo.setToolTip("Target CS2 shader for this Master Material")
        head.addWidget(self.shader_combo)

        self.map_button = QToolButton()
        self.map_button.setToolTip(f"Configure texture parameter slot assignments for {master_name}")
        self.map_button.setIcon(QIcon(_REMAP_ICON))
        self.map_button.clicked.connect(lambda: self.map_slots_requested.emit(self.master_name))
        head.addWidget(self.map_button)
        outer.addLayout(head)

        self.bindings = QLabel()
        self.bindings.setWordWrap(True)
        self.bindings.setEnabled(False)
        self.bindings.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self.bindings)

        # Cards are built at populate-time, after the dialog's one-shot
        # apply_stylesheets, so each one styles its own children or they stay
        # with whatever the global sheet gave them.
        apply_stylesheets(self)
        self.refresh(info)

    def refresh(self, info: dict):
        self.bindings.setText(
            describe_bindings(info.get("textures", {}), info.get("slot_overrides", {}))
        )


class MasterMaterialList(QScrollArea):
    """Scrollable column of MasterMaterialCards."""

    map_slots_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.cards = {}

        self._body = QWidget()
        self._layout = QVBoxLayout(self._body)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._empty = QLabel("Run Scan to discover Master Materials.")
        self._empty.setEnabled(False)
        self._layout.addWidget(self._empty)
        self._layout.addStretch(1)
        self.setWidget(self._body)

    def populate(self, master_groups: dict):
        for card in self.cards.values():
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()

        self._empty.setVisible(not master_groups)
        for i, (name, info) in enumerate(sorted(master_groups.items())):
            card = MasterMaterialCard(name, info, parity=(i % 2 == 1))
            card.map_slots_requested.connect(self.map_slots_requested)
            self._layout.insertWidget(i + 1, card)   # after the empty label
            self.cards[name] = card

    def refresh(self, master_name: str, info: dict):
        card = self.cards.get(master_name)
        if card:
            card.refresh(info)

    # The Materials tab reads selection/shader back out of these at convert time.
    def checkboxes(self) -> dict:
        return {name: card.checkbox for name, card in self.cards.items()}

    def shader_combos(self) -> dict:
        return {name: card.shader_combo for name, card in self.cards.items()}


def demo():
    """Builds the list with two fake masters — one plain, one packed SRMH — and
    checks the binding summary without needing a UE project. Pass --show to
    open the window and eyeball it.

        python -m src.forms.unreal_porter.master_material_list [--show]
    """
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = MasterMaterialList()
    widget.populate({
        "bese_material": {
            "count": 22,
            "shader": "csgo_environment.vfx",
            "textures": {
                "Diffuse": "/Game/T/Box_D.Box_D",
                "Normal": "/Game/T/Box_N.Box_N",
                "SRMH": "/Game/T/Box_SRM.Box_SRM",
            },
        },
        "Decal": {"count": 5, "shader": "csgo_static_overlay.vfx",
                  "textures": {"Diffuse": "/Game/T/TrashDecal01_D.TrashDecal01_D"}},
    })
    assert set(widget.cards) == {"bese_material", "Decal"}
    summary = widget.cards["bese_material"].bindings.text()
    assert "rough←SRMH.G" in summary, summary
    assert "metal←SRMH.B" in summary, summary
    assert "color←Diffuse" in summary, summary
    # Repopulating must not leave the previous cards behind.
    widget.populate({"only": {"count": 1, "textures": {}}})
    assert set(widget.cards) == {"only"}

    if "--show" in sys.argv:
        widget.populate({"bese_material": {"count": 22, "textures": {
            "Diffuse": "/Game/T/Box_D.Box_D", "SRMH": "/Game/T/Box_SRM.Box_SRM"}}})
        widget.resize(760, 300)
        widget.show()
        return app.exec()
    print("ok")


if __name__ == "__main__":
    demo()
