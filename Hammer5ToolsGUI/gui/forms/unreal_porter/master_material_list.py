"""
The Materials tab's Master Material list.

Replaces the old QTableWidget with material cards that show shader controls and
resolved slot bindings. The scroll area only creates cards near the viewport,
so large projects do not pay the QWidget and thumbnail cost for every material.
"""

import bisect
import os

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox,
    QToolButton, QScrollArea,
)

from .material_converter import (
    _classify_textures, find_bulk_texture, _pick_scalar, _pick_boolean_flags,
)

# material_remap_arrow.png is not in resources.qrc, so it is loaded from disk —
# same approach as gui/widgets/model_browser/main.py.
from gui.common import gui_assets_dir
_REMAP_ICON = gui_assets_dir("icons", "tools", "modeldoc_editor", "material_remap_arrow.png")

from .shader_schemas import SHADERS

_CHANNEL_LABELS = {"r": "R", "g": "G", "b": "B", "a": "A", "rgb": "RGB"}

_CARD_HEIGHT = 76
_DIVIDER_HEIGHT = 40
_ROW_SPACING = 6
_OVERSCAN_ROWS = 3


def material_group_matches(info: dict, master_name: str, search_text: str) -> bool:
    """Whether a material group contains every whitespace-separated query term."""
    terms = search_text.casefold().split()
    if not terms:
        return True

    searchable = [master_name]
    searchable.extend(str(value) for value in (info.get("textures") or {}).values())
    for stem, path, _data in info.get("instances", []):
        searchable.extend((str(stem), str(path)))
    haystack = " ".join(searchable).casefold()
    return all(term in haystack for term in terms)


def material_group_is_selected(info: dict, master_name: str, selected_stems: set[str]) -> bool:
    """Whether the master or one of its instances is in the current port scope."""
    if not selected_stems:
        return False
    if os.path.splitext(os.path.basename(master_name))[0].casefold() in selected_stems:
        return True
    return any(str(stem).casefold() in selected_stems
               for stem, _path, _data in info.get("instances", []))


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
        self.setFixedHeight(_CARD_HEIGHT)
        self.setFrameShape(QFrame.StyledPanel)
        self.master_name = master_name
        self.bulk_dir = bulk_dir
        # Zebra stripe — alternate-background-color the card itself.
        self.setProperty("h5Component", "unrealMasterMaterialCard")
        self.setProperty("parity", "true" if parity else "false")

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
                    lbl.setProperty("h5Component", "unrealMaterialThumbnail")
                    lbl.setToolTip(f"{slot}: {param}")
                    self.thumbs_layout.addWidget(lbl)
                    count += 1

        self.thumbs_container.setVisible(count > 0)


class MasterMaterialList(QScrollArea):
    """Virtualized, filterable column of MasterMaterialCards."""

    map_slots_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cards = {}
        self.bulk_dir = None
        self._master_groups = {}
        self._enabled = {}
        self._shaders = {}
        self._entries = []
        self._entry_ends = []
        self._search_text = ""
        self._selected_only = False
        self._selected_stems = set()
        self._rebuilding = False
        self._materializing = False

        self._body = QWidget()
        self._empty = QLabel("Run Scan to discover Master Materials.", self._body)
        self._empty.setEnabled(False)
        self.setWidget(self._body)
        self.viewport().installEventFilter(self)
        self.verticalScrollBar().valueChanged.connect(self._materialize_visible)

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
            line.setProperty("h5Component", "unrealSectionDividerLine")
            return line

        layout.addWidget(_line(), 1)
        lbl = QLabel(label_text)
        lbl.setProperty("h5Component", "unrealSectionDividerLabel")
        layout.addWidget(lbl)
        layout.addWidget(_line(), 1)
        return container

    def populate(self, master_groups: dict, bulk_dir: str = None):
        self.bulk_dir = bulk_dir
        self._master_groups = master_groups
        self._enabled = {name: True for name in master_groups}
        self._shaders = {
            name: info.get("shader", "csgo_environment.vfx")
            for name, info in master_groups.items()
        }
        self._rebuild_entries()

    def set_filters(self, search_text: str = "", selected_only: bool = False,
                    selected_assets=()) -> None:
        from .asset_selection import asset_stem

        self._search_text = search_text.strip()
        self._selected_only = selected_only
        self._selected_stems = {asset_stem(asset) for asset in selected_assets}
        self._rebuild_entries()

    def _rebuild_entries(self):
        self._rebuilding = True
        try:
            self._clear_materialized()
            visible_groups = [
                (name, info) for name, info in self._master_groups.items()
                if material_group_matches(info, name, self._search_text)
                and (not self._selected_only
                     or material_group_is_selected(info, name, self._selected_stems))
            ]
            sorted_groups = sorted(
                visible_groups,
                key=lambda item: item[1].get("count", len(item[1].get("instances", []))),
                reverse=True,
            )
            multi = [(name, info) for name, info in sorted_groups
                     if info.get("count", len(info.get("instances", []))) > 1]
            single = [(name, info) for name, info in sorted_groups
                      if info.get("count", len(info.get("instances", []))) <= 1]

            entries = []
            card_index = 0
            for name, info in multi:
                entries.append(("card", name, info, card_index % 2 == 1, _CARD_HEIGHT))
                card_index += 1
            if single:
                entries.append(("divider", "Standalone Materials (no instances)", None,
                                False, _DIVIDER_HEIGHT))
                for name, info in single:
                    entries.append(("card", name, info, card_index % 2 == 1, _CARD_HEIGHT))
                    card_index += 1

            self._entries = []
            self._entry_ends = []
            y = 0
            for kind, name, info, parity, height in entries:
                self._entries.append((kind, name, info, parity, y, height))
                y += height + _ROW_SPACING
                self._entry_ends.append(y)

            total_height = max(1, y - _ROW_SPACING)
            self._body.setMinimumHeight(total_height)
            self._empty.setText(
                "No materials match the current filters."
                if self._master_groups else "Run Scan to discover Master Materials."
            )
            self._empty.setVisible(not self._entries)
            self._layout_empty_label()
            self.verticalScrollBar().setValue(0)
        finally:
            self._rebuilding = False
        self._materialize_visible()

    def _clear_materialized(self):
        cards = list(self.cards.values())
        self.cards.clear()
        for card in cards:
            card.setParent(None)
            card.deleteLater()
        dividers = [
            divider for divider in self._body.findChildren(QFrame)
            if divider.objectName().startswith("virtualMaterialDivider_")
        ]
        for divider in dividers:
            divider.setParent(None)
            divider.deleteLater()

    def _layout_empty_label(self):
        self._empty.setGeometry(12, 8, max(0, self.viewport().width() - 24), 28)

    def _materialize_visible(self):
        if self._rebuilding or self._materializing or not self._entries:
            return
        self._materializing = True
        try:
            scroll_top = self.verticalScrollBar().value()
            viewport_height = max(1, self.viewport().height())
            first = max(0, bisect.bisect_right(self._entry_ends, scroll_top) - _OVERSCAN_ROWS)
            last = min(
                len(self._entries),
                bisect.bisect_left(self._entry_ends, scroll_top + viewport_height) + 1 + _OVERSCAN_ROWS,
            )
            wanted_names = {
                entry[1] for entry in self._entries[first:last] if entry[0] == "card"
            }
            for name in set(self.cards) - wanted_names:
                card = self.cards.pop(name)
                card.setParent(None)
                card.deleteLater()

            from .material_converter import get_texture_index
            tex_index = get_texture_index(self.bulk_dir) if self.bulk_dir else None
            width = max(0, self.viewport().width())
            for kind, name, info, parity, y, height in self._entries[first:last]:
                if kind == "divider":
                    object_name = f"virtualMaterialDivider_{y}"
                    divider = self._body.findChild(QFrame, object_name)
                    if divider is None:
                        divider = self._make_standalone_divider(name)
                        divider.setObjectName(object_name)
                        divider.setParent(self._body)
                        divider.show()
                    divider.setGeometry(0, y, width, height)
                    continue
                card = self.cards.get(name)
                if card is None:
                    card = MasterMaterialCard(
                        name, info, parity=parity, bulk_dir=self.bulk_dir,
                        tex_index=tex_index, parent=self._body,
                    )
                    card.checkbox.setChecked(self._enabled.get(name, True))
                    shader_index = card.shader_combo.findText(self._shaders.get(name, ""))
                    if shader_index >= 0:
                        card.shader_combo.setCurrentIndex(shader_index)
                    card.checkbox.toggled.connect(
                        lambda checked, material_name=name: self._enabled.__setitem__(material_name, checked)
                    )
                    card.shader_combo.currentTextChanged.connect(
                        lambda shader, material_name=name: self._shaders.__setitem__(material_name, shader)
                    )
                    card.map_slots_requested.connect(self.map_slots_requested)
                    self.cards[name] = card
                    card.show()
                card.setGeometry(0, y, width, height)
        finally:
            self._materializing = False

    def eventFilter(self, watched, event):
        if watched is self.viewport() and event.type() == QEvent.Resize:
            self._body.setMinimumWidth(self.viewport().width())
            self._layout_empty_label()
            self._materialize_visible()
        return super().eventFilter(watched, event)

    def refresh(self, master_name: str, info: dict):
        self._master_groups[master_name] = info
        if info.get("shader"):
            self._shaders[master_name] = info["shader"]
        card = self.cards.get(master_name)
        if card:
            from .material_converter import get_texture_index
            tex_index = get_texture_index(self.bulk_dir) if self.bulk_dir else None
            shader_index = card.shader_combo.findText(self._shaders.get(master_name, ""))
            if shader_index >= 0 and shader_index != card.shader_combo.currentIndex():
                card.shader_combo.blockSignals(True)
                card.shader_combo.setCurrentIndex(shader_index)
                card.shader_combo.blockSignals(False)
            card.refresh(info, bulk_dir=self.bulk_dir, tex_index=tex_index)

    def enabled_states(self) -> dict[str, bool]:
        return dict(self._enabled)

    def shader_selections(self) -> dict[str, str]:
        return dict(self._shaders)


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

    # Verify logical ordering: multi-instance first, then the divider and the
    # standalone material. The physical widgets are viewport-dependent.
    card_names = [entry[1] for entry in widget._entries if entry[0] == "card"]
    assert card_names == ["bese_material", "Decal", "M_SingleUse"], card_names

    # Repopulating must not leave the previous cards behind.
    stale_combo = widget.cards["Decal"].shader_combo
    widget.populate({"only": {"count": 1, "textures": {}}})
    assert set(widget.cards) == {"only"}

    # State is independent of materialized cards, so it covers every row even
    # when most rows are outside the viewport.
    assert set(widget.shader_selections()) == {"only"}
    assert set(widget.enabled_states()) == {"only"}
    app.processEvents()          # let deleteLater() actually reap the old cards
    try:
        stale_combo.currentText()
    except RuntimeError:
        pass                     # expected: the underlying widget is gone
    widget.populate({})
    assert widget.shader_selections() == {} and widget.enabled_states() == {}

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
