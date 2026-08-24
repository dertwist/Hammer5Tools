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

from hammer5tools_gui.styles.common import apply_stylesheets
from .material_converter import (
    _classify_textures, find_bulk_texture, _pick_scalar, _pick_boolean_flags,
)

# material_remap_arrow.png is not in resources.qrc, so it is loaded from disk —
# same approach as src/widgets/model_browser/main.py. Resolves to src/icons/...
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_REMAP_ICON = os.path.join(_SRC_DIR, "icons", "tools", "modeldoc_editor",
                           "material_remap_arrow.png")

from .shader_schemas import SHADERS

_CHANNEL_LABELS = {"r": "R", "g": "G", "b": "B", "a": "A", "rgb": "RGB"}


def describe_bindings(textures: dict, slot_overrides: dict = None, shader: str = None, info: dict = None) -> str:
    """One-line summary of what the current mapping resolves to, e.g.
    'color←Diffuse  normal←Normal  rough←SRMH.G  metal←SRMH.B'."""
    picks = _classify_textures(textures or {}, slot_overrides, shader=shader)
    return format_picks_summary(picks, info=info)


def format_picks_summary(picks: dict, info: dict = None) -> str:
    parts = []
    if picks:
        for slot in sorted(picks):
            param, _path, channel = picks[slot]
            suffix = f".{_CHANNEL_LABELS.get(channel, str(channel).upper())}" if channel else ""
            parts.append(f"{slot}←{param}{suffix}")

    scalars = (info or {}).get("scalars") or {}
    switches = (info or {}).get("switches") or {}

    pbr_parts = []

    rough = _pick_scalar(scalars, "roughness", "tileable 1 roughness", default=None)
    if rough is not None:
        pbr_parts.append(f"Roughness: {rough:.2f}")

    metal = _pick_scalar(scalars, "metallic", "metalness", default=None)
    if metal is not None and metal > 0:
        pbr_parts.append(f"Metalness: {metal:.2f}")

    auto_flags = _pick_boolean_flags(switches)
    if auto_flags:
        clean_flags = [f.replace("F_", "").replace("g_b", "").replace("1", "") for f in auto_flags]
        pbr_parts.append("Flags: " + ", ".join(clean_flags))

    if parts:
        summary = "   ".join(parts)
        if pbr_parts:
            summary += "  │  " + "   ".join(pbr_parts)
        return summary

    if pbr_parts:
        return "Color/PBR Material (No Textures) — " + "   ".join(pbr_parts)

    return "Default PBR material (No textures or color parameters resolved)."


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
        bg = "#2f2f31" if parity else "#2e2e2e"
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
        if count <= 1:
            title = QLabel(f"<b>{master_name}</b> <span style='color:#a5a5a5;'>(standalone material)</span>")
        else:
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
        self.bindings.setText(format_picks_summary(picks, info=info))
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

    @staticmethod
    def _make_standalone_divider(label_text: str) -> QFrame:
        """Divider with a label separating material groups (e.g. multi-instance vs standalone)."""
        container = QFrame()
        container.setFrameShape(QFrame.NoFrame)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 4)
        layout.setSpacing(8)

        def _line():
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("color: #464649;")
            return line

        layout.addWidget(_line(), 1)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #a5a5a5; font: 600 9pt 'Segoe UI'; background: transparent;")
        layout.addWidget(lbl)
        layout.addWidget(_line(), 1)
        apply_stylesheets(container)
        return container

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

            # Sort by instance count descending so the most-used masters are on top.
            sorted_groups = sorted(
                master_groups.items(),
                key=lambda item: item[1].get("count", len(item[1].get("instances", []))),
                reverse=True,
            )

            # Partition into multi-instance and single-instance (standalone) groups.
            multi = [(n, i) for n, i in sorted_groups
                     if i.get("count", len(i.get("instances", []))) > 1]
            single = [(n, i) for n, i in sorted_groups
                      if i.get("count", len(i.get("instances", []))) <= 1]

            idx = 0
            for name, info in multi:
                card = MasterMaterialCard(name, info, parity=(idx % 2 == 1), bulk_dir=self.bulk_dir, tex_index=tex_index)
                card.map_slots_requested.connect(self.map_slots_requested)
                self._layout.addWidget(card)
                self.cards[name] = card
                idx += 1

            if single:
                self._layout.addWidget(
                    self._make_standalone_divider("Standalone Materials (no instances)")
                )
                for name, info in single:
                    card = MasterMaterialCard(name, info, parity=(idx % 2 == 1), bulk_dir=self.bulk_dir, tex_index=tex_index)
                    card.map_slots_requested.connect(self.map_slots_requested)
                    self._layout.addWidget(card)
                    self.cards[name] = card
                    idx += 1

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
    """Builds the list with multi-instance and standalone masters, verifies
    sorting (descending by count) and the divider. Pass --show to open the
    window and eyeball it.

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
        "M_SingleUse": {"count": 1, "shader": "csgo_environment.vfx",
                        "textures": {"Diffuse": "/Game/T/Floor_D.Floor_D"}},
    })
    assert set(widget.cards) == {"bese_material", "Decal", "M_SingleUse"}
    summary = widget.cards["bese_material"].bindings.text()
    assert "rough←SRMH.G" in summary, summary
    assert "metal←SRMH.B" in summary, summary
    assert "color←Diffuse" in summary, summary

    # Verify card ordering: multi-instance first (sorted desc by count),
    # then the divider widget, then single-instance.
    card_widgets = [widget._layout.itemAt(i).widget()
                    for i in range(widget._layout.count())
                    if widget._layout.itemAt(i).widget()]
    card_names = [w.master_name for w in card_widgets if isinstance(w, MasterMaterialCard)]
    assert card_names == ["bese_material", "Decal", "M_SingleUse"], card_names

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
        widget.populate({
            "bese_material": {"count": 22, "textures": {
                "Diffuse": "/Game/T/Box_D.Box_D", "SRMH": "/Game/T/Box_SRM.Box_SRM"}},
            "M_Foliage": {"count": 8, "shader": "csgo_foliage.vfx", "textures": {}},
            "M_StandaloneWood": {"count": 1, "shader": "csgo_environment.vfx", "textures": {
                "Diffuse": "/Game/T/Wood_D.Wood_D"}},
            "M_StandaloneMetal": {"count": 1, "shader": "csgo_environment.vfx", "textures": {}},
        })
        widget.resize(760, 400)
        widget.show()
        return app.exec()
    print("ok")


if __name__ == "__main__":
    demo()
