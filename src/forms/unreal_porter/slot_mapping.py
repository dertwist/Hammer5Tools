"""
Manual override for material_converter._classify_textures' heuristic slot
picks. Lets the user preview one Master Material's detected texture params
(via bridge.dump_material) and reassign which vmat slot each maps to, exclude
it entirely, or — for packed masks like SRMH/ORM — route each colour channel
to a different slot.

Overrides are keyed by UE parameter name, not per-material: Material
Instances sharing a master material repeat the same parameter names, so one
override (e.g. "BaseColor2" -> emissive) applies to all of them.

Stored form per parameter:
    None                        exclude the parameter
    "rough"                     bind the whole texture to that slot
    {"rough": "g", "ao": "r"}   route individual channels (slot -> channel)
"""

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox, QLabel,
    QDialogButtonBox, QWidget, QScrollArea, QFrame, QPushButton, QTabWidget,
    QColorDialog,
)

from src.settings.main import get_settings_value, set_settings_value
from src.styles.common import apply_stylesheets
from .material_converter import (
    _SLOT_TOKENS, CHANNELS, CHANNEL_SLOTS, packed_layout, find_bulk_texture,
    get_slots_for_shader, get_channel_slots_for_shader,
)

_SLOTS = [
    "color", "normal", "rough", "metal", "ao", "height", "opacity", "emissive",
    "color2", "normal2", "rough2", "metal2", "ao2", "height2",
    "color3", "normal3", "rough3", "metal3", "ao3", "height3",
    "color4", "normal4", "rough4", "metal4", "ao4", "height4",
]
_AUTO = "Auto"
_SKIP = "Don't use"
_SPLIT = "Split channels…"
_UNUSED = "—"

_CHANNEL_LABELS = {"r": "R", "g": "G", "b": "B", "a": "A"}


def load_overrides() -> dict:
    """{param_name: slot_name | None | {slot: channel}}."""
    raw = get_settings_value("UnrealConverter", "slot_overrides_json", "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_overrides(overrides: dict):
    set_settings_value("UnrealConverter", "slot_overrides_json", json.dumps(overrides))


def load_param_overrides() -> dict:
    """{ue_param_name: vmat_param_name} for scalar/vector/switch mapping."""
    raw = get_settings_value("UnrealConverter", "param_overrides_json", "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_param_overrides(overrides: dict):
    set_settings_value("UnrealConverter", "param_overrides_json", json.dumps(overrides))


# Curated Source 2 (csgo_environment.vfx & csgo_environment_blend.vfx) param targets,
# grouped by UE value type.
_SCALAR_TARGETS = [
    ("(don't map)", ""),
    ("Roughness scale (Layer 1)", "g_flRoughnessScale"),
    ("Metalness scale (Layer 1)", "g_flMetalnessScale"),
    ("Model tint amount", "g_flModelTintAmount"),
    ("HeightMap scale (Layer 1)", "g_flHeightMapScale1"),
    ("HeightMap zero point (Layer 1)", "g_flHeightMapZeroPoint1"),
    ("HeightMap scale (Layer 2)", "g_flHeightMapScale2"),
    ("HeightMap zero point (Layer 2)", "g_flHeightMapZeroPoint2"),
    ("HeightMap scale (Layer 3)", "g_flHeightMapScale3"),
    ("HeightMap zero point (Layer 3)", "g_flHeightMapZeroPoint3"),
    ("Blend softness (Layer 2)", "g_flBlendSoftness2"),
    ("Blend softness (Layer 3)", "g_flBlendSoftness3"),
    ("Border offset (Layer 2)", "g_flBorderOffset2"),
    ("Border softness (Layer 2)", "g_flBorderSoftness2"),
    ("Border spread (Layer 2)", "g_flBorderSpread2"),
    ("Bevel strength (Layer 2)", "g_flBevelStrength2"),
    ("Bevel softness (Layer 2)", "g_flBevelSoftness2"),
    ("Bevel curve (Layer 2)", "g_flBevelCurve2"),
    ("Bevel spread (Layer 2)", "g_flBevelSpread2"),
    ("Texture brightness (Layer 1)", "g_fTextureColorBrightness1"),
    ("Texture contrast (Layer 1)", "g_fTextureColorContrast1"),
    ("Texture saturation (Layer 1)", "g_fTextureColorSaturation1"),
    ("Texture brightness (Layer 2)", "g_fTextureColorBrightness2"),
    ("Texture contrast (Layer 2)", "g_fTextureColorContrast2"),
    ("Texture saturation (Layer 2)", "g_fTextureColorSaturation2"),
    ("Texture brightness (Layer 3)", "g_fTextureColorBrightness3"),
    ("Texture contrast (Layer 3)", "g_fTextureColorContrast3"),
    ("Texture saturation (Layer 3)", "g_fTextureColorSaturation3"),
    ("Texture roughness brightness (Layer 2)", "g_fTextureRoughnessBrightness2"),
    ("Texture roughness contrast (Layer 2)", "g_fTextureRoughnessContrast2"),
    ("Texture roughness brightness (Layer 3)", "g_fTextureRoughnessBrightness3"),
    ("Texture roughness contrast (Layer 3)", "g_fTextureRoughnessContrast3"),
    ("Alpha test reference", "g_flAlphaTestReference"),
    ("Texcoord rotation (Layer 1)", "g_flTexCoordRotation1"),
    ("Texcoord rotation (Layer 2)", "g_flTexCoordRotation2"),
    ("Wetness darkening (Layer 1)", "g_flWetnessDarkeningStrength1"),
]

_VECTOR_TARGETS = [
    ("(don't map)", ""),
    ("Color tint / Model tint (g_vColorTint)", "g_vColorTint"),
    ("Texture color tint (Layer 1)", "g_vTextureColorTint1"),
    ("Texture color tint (Layer 2)", "g_vTextureColorTint2"),
    ("Texture color tint (Layer 3)", "g_vTextureColorTint3"),
    ("Border tint (Layer 2)", "g_vBorderTint2"),
    ("Border tint (Layer 3)", "g_vBorderTint3"),
    ("Bevel layer amount (Layer 2)", "g_vBevelLayerAmount2"),
    ("Border layer amount (Layer 2)", "g_vBorderLayerAmount2"),
    ("Texcoord scale (Layer 1)", "g_vTexCoordScale1"),
    ("Texcoord scale (Layer 2)", "g_vTexCoordScale2"),
    ("Texcoord scale (Layer 3)", "g_vTexCoordScale3"),
    ("Texcoord offset (Layer 1)", "g_vTexCoordOffset1"),
    ("Texcoord offset (Layer 2)", "g_vTexCoordOffset2"),
    ("Texcoord center (Layer 1)", "g_vTexCoordCenter1"),
    ("AO levels (Layer 1)", "g_vAmbientOcclusionLevels1"),
    ("AO levels (Layer 2)", "g_vAmbientOcclusionLevels2"),
    ("AO levels (Layer 3)", "g_vAmbientOcclusionLevels3"),
]

_SWITCH_TARGETS = [
    ("(don't map)", ""),
    ("Alpha test", "F_ALPHA_TEST"),
    ("Render backfaces", "F_RENDER_BACKFACES"),
    ("Enable Layer 3", "F_ENABLE_LAYER_3"),
    ("Enable Layer 4", "F_ENABLE_LAYER_4"),
    ("Enable Blend Effects (Layer 2)", "F_BLEND_EFFECTS_2"),
    ("Fog enabled", "g_bFogEnabled"),
    ("Model tint (Layer 1)", "g_bModelTint1"),
    ("Model tint (Layer 2)", "g_bModelTint2"),
    ("Model tint (Layer 3)", "g_bModelTint3"),
    ("Border tint mask (Layer 2)", "g_bBorderTintMask2"),
]


def _tex_name(ue_path: str) -> str:
    """'/Game/T/Box_SRM.Box_SRM' -> 'Box_SRM'."""
    return str(ue_path or "").split("/")[-1].split(".")[0]


class _ParamRow(QFrame):
    """One UE texture parameter: thumbnail preview, name, and vmat slot mapping."""

    def __init__(self, param: str, tex_path: str, override, bulk_dir: str = None, shader: str = None, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.param = param
        self.shader = shader
        self.slots = get_slots_for_shader(shader)
        self.channel_slots = get_channel_slots_for_shader(shader)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        head = QHBoxLayout()

        # Image thumbnail preview
        self.thumb = QLabel()
        self.thumb.setFixedSize(38, 38)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet(
            "QLabel { border: 1px solid #383838; background-color: #1A1A1C; border-radius: 4px; color: #888; font-size: 9px; font-weight: bold; }"
        )
        self._load_thumbnail(bulk_dir, tex_path)
        head.addWidget(self.thumb)

        info_box = QVBoxLayout()
        info_box.setSpacing(1)
        name = QLabel(f"<b>{param}</b>")
        tex = QLabel(_tex_name(tex_path))
        tex.setEnabled(False)  # themed as secondary text by global QSS
        info_box.addWidget(name)
        info_box.addWidget(tex)
        head.addLayout(info_box, 1)

        self.target = QComboBox()
        self.target.addItems([_AUTO, _SKIP] + self.slots + [_SPLIT])
        self.target.setToolTip(
            "Where this texture's pixels go in the .vmat.\n"
            "Auto uses the name-matching heuristic; Split channels routes each\n"
            "colour channel of a packed mask to a different slot."
        )
        head.addWidget(self.target)
        outer.addLayout(head)

        # Per-channel grid, shown only in Split mode.
        self.channel_box = QWidget()
        grid = QGridLayout(self.channel_box)
        grid.setContentsMargins(0, 2, 0, 0)
        grid.setSpacing(4)
        self.channel_combos = {}
        for col, ch in enumerate(CHANNELS):
            label = QLabel(_CHANNEL_LABELS[ch])
            label.setAlignment(Qt.AlignCenter)
            combo = QComboBox()
            combo.addItem(_UNUSED)
            combo.addItems(self.channel_slots)
            grid.addWidget(label, 0, col)
            grid.addWidget(combo, 1, col)
            self.channel_combos[ch] = combo
        outer.addWidget(self.channel_box)

        self._apply_initial(override)
        self.target.currentTextChanged.connect(self._sync_channel_box)
        self._sync_channel_box(self.target.currentText())

    def _load_thumbnail(self, bulk_dir: str, tex_path: str, tex_index: dict = None):
        stem = _tex_name(tex_path)
        if bulk_dir and tex_path:
            img_path = find_bulk_texture(bulk_dir, tex_path, tex_index=tex_index)
            if img_path:
                from .master_material_list import get_cached_pixmap
                pm = get_cached_pixmap(img_path, size=36)
                if pm and not pm.isNull():
                    self.thumb.setPixmap(pm)
                    self.thumb.setToolTip(f"{stem}\n({img_path})")
                    return
        ext = stem.split("_")[-1].upper() if "_" in stem else "TEX"
        self.thumb.setText(ext[:4])
        self.thumb.setToolTip(stem or "Texture preview unavailable")

    def _apply_initial(self, override):
        if isinstance(override, dict):
            self.target.setCurrentText(_SPLIT)
            for slot, ch in override.items():
                if ch in self.channel_combos and slot in self.channel_slots:
                    self.channel_combos[ch].setCurrentText(slot)
            return
        if override is _EXPLICIT_SKIP:
            self.target.setCurrentText(_SKIP)
            return
        if isinstance(override, str) and override in self.slots:
            self.target.setCurrentText(override)
            return
        self.target.setCurrentText(_AUTO)
        _tok, layout = packed_layout(self.param)
        for ch, slot in (layout or {}).items():
            if ch in self.channel_combos and slot in self.channel_slots:
                self.channel_combos[ch].setCurrentText(slot)

    def _sync_channel_box(self, text):
        self.channel_box.setVisible(text == _SPLIT)

    def value(self):
        """The stored override for this parameter, or _NO_OVERRIDE."""
        text = self.target.currentText()
        if text == _AUTO:
            return _NO_OVERRIDE
        if text == _SKIP:
            return None
        if text == _SPLIT:
            routed = {}
            for ch, combo in self.channel_combos.items():
                slot = combo.currentText()
                if slot != _UNUSED:
                    routed[slot] = ch
            return routed or None
        return text


_NO_OVERRIDE = object()
_EXPLICIT_SKIP = object()


class _VectorParamRow(QHBoxLayout):
    """Fancy view row for Vector parameter with interactive QColorDialog swatch."""

    def __init__(self, name: str, val: dict, combo: QComboBox, parent=None):
        super().__init__()
        self.name = name
        self.val = dict(val) if isinstance(val, dict) else {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}

        self.swatch = QPushButton()
        self.swatch.setFixedSize(36, 22)
        self.swatch.setToolTip("Click to open color picker")
        self.swatch.clicked.connect(self._pick_color)

        self.val_label = QLabel()
        self.val_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self._update_display()

        left = QHBoxLayout()
        left.setSpacing(6)
        name_lbl = QLabel(f"<b>{name}</b>")
        left.addWidget(name_lbl)
        left.addWidget(self.swatch)
        left.addWidget(self.val_label, 1)

        self.addLayout(left, 1)
        self.addWidget(combo)

    def _update_display(self):
        r = max(0, min(255, int(self.val.get("r", 1.0) * 255)))
        g = max(0, min(255, int(self.val.get("g", 1.0) * 255)))
        b = max(0, min(255, int(self.val.get("b", 1.0) * 255)))
        a = self.val.get("a", 1.0)

        self.swatch.setStyleSheet(
            f"QPushButton {{ background-color: rgb({r}, {g}, {b}); border: 1px solid #555; border-radius: 4px; }}"
            f"QPushButton:hover {{ border: 1px solid #007ACC; }}"
        )
        rf, gf, bf = self.val.get("r", 1.0), self.val.get("g", 1.0), self.val.get("b", 1.0)
        self.val_label.setText(
            f"<span style='color:#007ACC; font-weight:bold;'>[{rf:.3f} {gf:.3f} {bf:.3f} {a:.3f}]</span> "
            f"<span style='color:#888888;'>#{r:02X}{g:02X}{b:02X}</span>"
        )

    def _pick_color(self):
        r = max(0, min(255, int(self.val.get("r", 1.0) * 255)))
        g = max(0, min(255, int(self.val.get("g", 1.0) * 255)))
        b = max(0, min(255, int(self.val.get("b", 1.0) * 255)))
        cur = QColor(r, g, b)
        col = QColorDialog.getColor(cur, None, f"Select Color — {self.name}")
        if col.isValid():
            self.val["r"] = round(col.redF(), 4)
            self.val["g"] = round(col.greenF(), 4)
            self.val["b"] = round(col.blueF(), 4)
            self._update_display()


class _ParamMappingTab(QWidget):
    """Migrate UE scalar/vector/switch params to Source 2 vmat params.

    One row per declared parameter, grouped by value type with fancy controls.
    """

    def __init__(self, scalars: dict, vectors: dict, switches: dict,
                 initial: dict = None, parent=None):
        super().__init__(parent)
        self._rows = {}
        initial = initial or {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)

        self._add_scalars(body_layout, sorted((scalars or {}).items()), initial)
        self._add_vectors(body_layout, sorted((vectors or {}).items()), initial)
        self._add_switches(body_layout, sorted((switches or {}).items()), initial)

        body_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    def _add_scalars(self, parent_layout, items, initial):
        if not items:
            return
        group = QFrame()
        group.setFrameShape(QFrame.StyledPanel)
        gl = QVBoxLayout(group)
        gl.setContentsMargins(8, 6, 8, 6)
        gl.setSpacing(4)
        gl.addWidget(QLabel("<b>Scalars (float)</b>"))
        for name, val in items:
            row = QHBoxLayout()
            val_fmt = f"<span style='background-color:#2A2A2D; color:#4EC9B0; padding:2px 6px; border-radius:3px; font-family:monospace;'>{val:.4f}</span>"
            label = QLabel(f"{name}  {val_fmt}")
            combo = QComboBox()
            for label_text, data in _SCALAR_TARGETS:
                combo.addItem(label_text, data)
            stored = initial.get(name, "")
            idx = combo.findData(stored)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            row.addWidget(label, 1)
            row.addWidget(combo)
            gl.addLayout(row)
            self._rows[name] = combo
        parent_layout.addWidget(group)

    def _add_vectors(self, parent_layout, items, initial):
        if not items:
            return
        group = QFrame()
        group.setFrameShape(QFrame.StyledPanel)
        gl = QVBoxLayout(group)
        gl.setContentsMargins(8, 6, 8, 6)
        gl.setSpacing(4)
        gl.addWidget(QLabel("<b>Vectors & Colors</b>"))
        for name, val in items:
            combo = QComboBox()
            for label_text, data in _VECTOR_TARGETS:
                combo.addItem(label_text, data)
            stored = initial.get(name, "")
            idx = combo.findData(stored)
            combo.setCurrentIndex(idx if idx >= 0 else 0)

            vrow = _VectorParamRow(name, val, combo)
            gl.addLayout(vrow)
            self._rows[name] = combo
        parent_layout.addWidget(group)

    def _add_switches(self, parent_layout, items, initial):
        if not items:
            return
        group = QFrame()
        group.setFrameShape(QFrame.StyledPanel)
        gl = QVBoxLayout(group)
        gl.setContentsMargins(8, 6, 8, 6)
        gl.setSpacing(4)
        gl.addWidget(QLabel("<b>Switches (bool)</b>"))
        for name, val in items:
            row = QHBoxLayout()
            badge = "<span style='background-color:#1E3A1E; color:#4EC9B0; padding:2px 8px; border-radius:3px; font-weight:bold;'>ON</span>" if val else "<span style='background-color:#2D2D2D; color:#888888; padding:2px 8px; border-radius:3px;'>OFF</span>"
            label = QLabel(f"{name}  {badge}")
            combo = QComboBox()
            for label_text, data in _SWITCH_TARGETS:
                combo.addItem(label_text, data)
            stored = initial.get(name, "")
            idx = combo.findData(stored)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            row.addWidget(label, 1)
            row.addWidget(combo)
            gl.addLayout(row)
            self._rows[name] = combo
        parent_layout.addWidget(group)

    def value(self) -> dict:
        """{ue_param_name: vmat_param_name}, dropping unmapped entries."""
        out = {}
        for name, combo in self._rows.items():
            target = combo.currentData()
            if target:
                out[name] = target
        return out


class SlotMappingDialog(QDialog):
    """Configures texture parameter -> vmat slot overrides for a Master Material.
    All Material Instances inheriting from this Master Material use these mappings.
    """

    def __init__(self, master_name: str, textures: dict, initial_overrides: dict = None,
                 shader: str = None, scalars: dict = None, vectors: dict = None, switches: dict = None,
                 initial_param_overrides: dict = None, bulk_dir: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Texture slots — {master_name}")
        self.resize(700, 580)

        self.master_name = master_name
        self.textures = textures or {}
        self.shader = shader
        self.bulk_dir = bulk_dir
        self.result_overrides = {}
        self.result_param_overrides = {}

        existing = initial_overrides or {}

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        # --- Tab 1: Texture Slots ---
        tex_tab = QWidget()
        tex_layout = QVBoxLayout(tex_tab)
        tex_layout.setContentsMargins(0, 0, 0, 0)
        self._rows = []
        if not self.textures:
            tex_layout.addWidget(QLabel("No texture parameters found on this Master Material."))
        else:
            body = QWidget()
            body_layout = QVBoxLayout(body)
            body_layout.setContentsMargins(0, 0, 0, 0)
            body_layout.setSpacing(6)
            for param, path in sorted(self.textures.items()):
                override = existing[param] if param in existing else _NO_OVERRIDE
                if param in existing and existing[param] is None:
                    override = _EXPLICIT_SKIP
                row = _ParamRow(param, path, override, bulk_dir=self.bulk_dir, shader=self.shader)
                self._rows.append(row)
                body_layout.addWidget(row)
            body_layout.addStretch(1)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(body)
            tex_layout.addWidget(scroll, 1)
        tabs.addTab(tex_tab, "Texture Slots")

        # --- Tab 2: Params (scalar/vector/switch -> vmat param) ---
        self._params_tab = _ParamMappingTab(scalars, vectors, switches, initial_param_overrides)
        tabs.addTab(self._params_tab, "Params")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        reset = QPushButton("Reset to auto")
        reset.clicked.connect(self._on_reset)
        buttons.addButton(reset, QDialogButtonBox.ResetRole)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        apply_stylesheets(self)

    def _on_reset(self):
        for row in self._rows:
            row.target.setCurrentText(_AUTO)

    def _on_save(self):
        overrides = {}
        for row in self._rows:
            value = row.value()
            if value is not _NO_OVERRIDE:
                overrides[row.param] = value
        self.result_overrides = overrides
        self.result_param_overrides = self._params_tab.value()
        self.accept()
