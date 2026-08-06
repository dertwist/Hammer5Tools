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
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox,
    QToolButton, QScrollArea,
)

from src.styles.common import apply_stylesheets
from .material_converter import _classify_textures, find_bulk_texture

# material_remap_arrow.png is not in resources.qrc, so it is loaded from disk —
# same approach as src/widgets/model_browser/main.py. Resolves to src/icons/...
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_REMAP_ICON = os.path.join(_SRC_DIR, "icons", "tools", "modeldoc_editor",
                           "material_remap_arrow.png")

from .shader_schemas import SHADERS

_CHANNEL_LABELS = {"r": "R", "g": "G", "b": "B", "a": "A"}


def describe_bindings(textures: dict, slot_overrides: dict = None, shader: str = None) -> str:
    """One-line summary of what the current mapping resolves to, e.g.
    'color←Diffuse  normal←Normal  rough←SRMH.G  metal←SRMH.B'."""
    picks = _classify_textures(textures or {}, slot_overrides, shader=shader)
    return format_picks_summary(picks)


def format_picks_summary(picks: dict) -> str:
    if not picks:
        return "No texture slots resolved — this material will convert flat."
    parts = []
    for slot in sorted(picks):
        param, _path, channel = picks[slot]
        suffix = f".{_CHANNEL_LABELS[channel]}" if channel else ""
        parts.append(f"{slot}←{param}{suffix}")
    return "   ".join(parts)


_THUMBNAIL_CACHE = {}


def get_cached_pixmap(img_path: str, size: int = 24) -> QPixmap:
    if not img_path:
        return None
    key = (img_path, size)
    if key in _THUMBNAIL_CACHE:
        return _THUMBNAIL_CACHE[key]
    if os.path.exists(img_path):
        pm = QPixmap(img_path)
        if not pm.isNull():
            scaled = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            _THUMBNAIL_CACHE[key] = scaled
            return scaled
    _THUMBNAIL_CACHE[key] = None
    return None


class MasterMaterialCard(QFrame):
    """One Master Material: whether to convert it, its target CS2 shader, and
    the texture-slot mapping every instance under it inherits.

    Row layout: [checkbox] | <name> (instances) | [shader combo] | [remap btn].
    Cards alternate two background tones so the eye can track a row across a
    long list.
    """

    map_slots_requested = Signal(str)

    def __init__(self, master_name: str, info: dict, parity: bool = False, bulk_dir: str = None, tex_index: dict = None, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.master_name = master_name
        self.bulk_dir = bulk_dir
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

        self.info = info
        self.shader_combo = QComboBox()
        self.shader_combo.addItems(SHADERS)
        predicted = info.get("shader", "csgo_environment.vfx")
        idx = self.shader_combo.findText(predicted)
        if idx >= 0:
            self.shader_combo.setCurrentIndex(idx)
        self.shader_combo.setToolTip("Target CS2 shader for this Master Material")
        self.shader_combo.currentTextChanged.connect(self._on_shader_changed)
        head.addWidget(self.shader_combo)

        self.map_button = QToolButton()
        self.map_button.setToolTip(f"Shader Remapper: Configure CS2 shader, feature flags, and texture slot mappings for {master_name}")
        self.map_button.setIcon(QIcon(_REMAP_ICON))
        self.map_button.clicked.connect(lambda: self.map_slots_requested.emit(self.master_name))
        head.addWidget(self.map_button)
        outer.addLayout(head)

        b_row = QHBoxLayout()
        b_row.setSpacing(6)

        self.thumbs_container = QWidget()
        self.thumbs_layout = QHBoxLayout(self.thumbs_container)
        self.thumbs_layout.setContentsMargins(0, 0, 0, 0)
        self.thumbs_layout.setSpacing(3)
        b_row.addWidget(self.thumbs_container)

        self.bindings = QLabel()
        self.bindings.setWordWrap(True)
        self.bindings.setEnabled(False)
        self.bindings.setTextInteractionFlags(Qt.TextSelectableByMouse)
        b_row.addWidget(self.bindings, 1)

        outer.addLayout(b_row)

        apply_stylesheets(self)
        self.refresh(info, bulk_dir=self.bulk_dir, tex_index=tex_index)

    def _on_shader_changed(self, new_shader: str):
        if hasattr(self, "info") and self.info:
            self.info["shader"] = new_shader
            self.refresh(self.info)

    def refresh(self, info: dict, bulk_dir: str = None, tex_index: dict = None):
        self.info = info
        if bulk_dir:
            self.bulk_dir = bulk_dir
        textures = info.get("textures", {})
        slot_overrides = info.get("slot_overrides", {})
        shader = info.get("shader") or self.shader_combo.currentText()
        picks = _classify_textures(textures, slot_overrides, shader=shader)
        self.bindings.setText(format_picks_summary(picks))
        self._update_thumbnails(picks, tex_index=tex_index)

    def _update_thumbnails(self, picks: dict, tex_index: dict = None):
        while self.thumbs_layout.count():
            item = self.thumbs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.bulk_dir or not picks:
            self.thumbs_container.setVisible(False)
            return

        shown_paths = set()
        count = 0
        for slot, (param, tex_path, _channel) in sorted(picks.items()):
            if count >= 4:
                break
            if tex_path in shown_paths:
                continue
            shown_paths.add(tex_path)
            img_path = find_bulk_texture(self.bulk_dir, tex_path, tex_index=tex_index)
            if img_path:
                pm = get_cached_pixmap(img_path, size=24)
                if pm and not pm.isNull():
                    lbl = QLabel()
                    lbl.setFixedSize(24, 24)
                    lbl.setPixmap(pm)
                    lbl.setStyleSheet("border: 1px solid #3A3A3C; border-radius: 3px; background-color: #111;")
                    lbl.setToolTip(f"{slot}: {param}")
                    self.thumbs_layout.addWidget(lbl)
                    count += 1

        self.thumbs_container.setVisible(count > 0)


class MasterMaterialList(QScrollArea):
    """Scrollable column of MasterMaterialCards."""

    map_slots_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.cards = {}
        self.bulk_dir = None

        self._body = QWidget()
        self._layout = QVBoxLayout(self._body)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._empty = QLabel("Run Scan to discover Master Materials.")
        self._empty.setEnabled(False)
        self._layout.addWidget(self._empty)
        self._layout.addStretch(1)
        self.setWidget(self._body)

    def populate(self, master_groups: dict, bulk_dir: str = None):
        self.bulk_dir = bulk_dir
        self._body.setUpdatesEnabled(False)
        try:
            while self._layout.count():
                item = self._layout.takeAt(0)
                w = item.widget()
                if w and w is not self._empty:
                    w.setParent(None)
                    w.deleteLater()
            self.cards.clear()

            self._empty.setVisible(not master_groups)
            self._layout.addWidget(self._empty)

            from .material_converter import get_texture_index
            tex_index = get_texture_index(self.bulk_dir) if self.bulk_dir else None

            for i, (name, info) in enumerate(sorted(master_groups.items())):
                card = MasterMaterialCard(name, info, parity=(i % 2 == 1), bulk_dir=self.bulk_dir, tex_index=tex_index)
                card.map_slots_requested.connect(self.map_slots_requested)
                self._layout.addWidget(card)
                self.cards[name] = card

            self._layout.addStretch(1)
        finally:
            self._body.setUpdatesEnabled(True)

    def refresh(self, master_name: str, info: dict):
        card = self.cards.get(master_name)
        if card:
            from .material_converter import get_texture_index
            tex_index = get_texture_index(self.bulk_dir) if self.bulk_dir else None
            card.refresh(info, bulk_dir=self.bulk_dir, tex_index=tex_index)

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
    stale_combo = widget.shader_combos()["Decal"]
    widget.populate({"only": {"count": 1, "textures": {}}})
    assert set(widget.cards) == {"only"}

    # The accessors must track the repopulate, not outlive it. Callers read these
    # live for exactly this reason: a dict held across a populate() points at
    # deleted C++ objects, which is what crashed the convert pipeline.
    assert set(widget.shader_combos()) == {"only"}
    assert set(widget.checkboxes()) == {"only"}
    app.processEvents()          # let deleteLater() actually reap the old cards
    try:
        stale_combo.currentText()
    except RuntimeError:
        pass                     # expected: the underlying widget is gone
    widget.populate({})
    assert widget.shader_combos() == {} and widget.checkboxes() == {}

    if "--show" in sys.argv:
        widget.populate({"bese_material": {"count": 22, "textures": {
            "Diffuse": "/Game/T/Box_D.Box_D", "SRMH": "/Game/T/Box_SRM.Box_SRM"}}})
        widget.resize(760, 300)
        widget.show()
        return app.exec()
    print("ok")


if __name__ == "__main__":
    demo()
