"""
Manual override for material_converter._classify_textures' heuristic slot
picks and CS2 material feature flag inspector.

Lets the user preview one Master Material's detected texture params
(via bridge.dump_material) and reassign which vmat slot each maps to, exclude
it entirely, route individual channels for packed masks (like SRMH/ORM), or
enable automatic alpha channel splitting per map.

Also provides a Valve Hammer-style CS2 Material Feature Inspector panel to toggle
material feature flags (shadows, 2-sided rendering, Z-buffering, layer 2/3, detail, wetness, etc.).
"""

import json
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox, QLabel,
    QDialogButtonBox, QWidget, QScrollArea, QFrame, QPushButton, QToolButton, QTabWidget,
    QColorDialog, QCheckBox, QSplitter,
)

from src.settings.main import get_settings_value, set_settings_value
from src.styles.common import (
    apply_stylesheets,
    qt_stylesheet_button,
    qt_stylesheet_checkbox,
    qt_stylesheet_combobox,
    qt_stylesheet_toolbutton,
)


_DISABLED_STYLE_APPEND = """
QPushButton:disabled, QToolButton:disabled {
    background-color: #18181A;
    color: #666666;
    border-color: #2A2A2D;
}
QCheckBox:disabled {
    color: #666666;
}
QComboBox:disabled {
    background-color: #18181A;
    color: #666666;
    border-color: #2A2A2D;
}
"""


def force_apply_stylesheets(parent: QWidget) -> None:
    """Force-applies registered Qt stylesheets to all child widgets with crisp gray text for disabled controls."""
    for cb in parent.findChildren(QCheckBox):
        cb.setStyleSheet(f"{qt_stylesheet_checkbox}\n{_DISABLED_STYLE_APPEND}")
    for pb in parent.findChildren(QPushButton):
        pb.setStyleSheet(f"{qt_stylesheet_button}\n{_DISABLED_STYLE_APPEND}")
    for tb in parent.findChildren(QToolButton):
        tb.setStyleSheet(f"{qt_stylesheet_toolbutton}\n{_DISABLED_STYLE_APPEND}")
    for combo in parent.findChildren(QComboBox):
        combo.setStyleSheet(f"{qt_stylesheet_combobox}\n{_DISABLED_STYLE_APPEND}")
from .material_converter import (
    _SLOT_TOKENS, CHANNELS, CHANNEL_SLOTS, packed_layout, find_bulk_texture,
    get_slots_for_shader, get_channel_slots_for_shader,
)
from .shader_schemas import (
    SHADERS,
    SCALAR_TARGETS as _SCALAR_TARGETS,
    VECTOR_TARGETS as _VECTOR_TARGETS,
    SWITCH_TARGETS as _SWITCH_TARGETS,
    FEATURE_DEPENDENCIES,
    get_targets_for_shader,
    validate_feature_flags,
)

_AUTO = "Auto"
_SKIP = "Skip"
_SPLIT_ALPHA = "Split Alpha (RGB + A)"
_SPLIT_RGBA = "Split RGBA (R + G + B + A)"
_UNUSED = "—"

_CHANNEL_LABELS = {"r": "R", "g": "G", "b": "B", "a": "A"}


def load_overrides() -> dict:
    raw = get_settings_value("UnrealConverter", "slot_overrides_json", "{}")
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
    raw = get_settings_value("UnrealConverter", "param_overrides_json", "{}")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_param_overrides(overrides: dict):
    set_settings_value("UnrealConverter", "param_overrides_json", json.dumps(overrides))


def _tex_name(ue_path: str) -> str:
    """'/Game/T/Box_SRM.Box_SRM' -> 'Box_SRM'."""
    return str(ue_path or "").split("/")[-1].split(".")[0]


class _ParamRow(QFrame):
    """One UE texture parameter: thumbnail preview, name, and vmat slot mapping options."""

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
        self.target.addItems([_AUTO, _SKIP] + self.slots + [_SPLIT_ALPHA, _SPLIT_RGBA])
        self.target.setToolTip(
            "Where this texture's pixels go in the .vmat:\n"
            "• Auto: uses the name-matching heuristic.\n"
            "• Skip: excludes texture map.\n"
            "• Slot Name: binds whole texture map to slot.\n"
            "• Split Alpha (RGB + A): extracts base RGB image + standalone Alpha (A) mask file using custom channel grid.\n"
            "• Split RGBA (R + G + B + A): extracts Red, Green, Blue, and Alpha into standalone mask images using custom channel grid."
        )
        head.addWidget(self.target)
        outer.addLayout(head)

        # Per-channel custom grid, shown dynamically in Split Alpha (RGB, A) & Split RGBA (R, G, B, A) modes.
        self.channel_box = QWidget()
        self.channel_grid_layout = QGridLayout(self.channel_box)
        self.channel_grid_layout.setContentsMargins(0, 2, 0, 0)
        self.channel_grid_layout.setSpacing(4)
        self.channel_combos = {}
        outer.addWidget(self.channel_box)

        self.target.currentTextChanged.connect(self._sync_channel_box)
        self._apply_initial(override)
        self._sync_channel_box(self.target.currentText())

    def update_shader(self, shader: str, feature_flags: dict = None):
        self.shader = shader
        self.slots = get_slots_for_shader(shader, feature_flags=feature_flags)
        self.channel_slots = get_channel_slots_for_shader(shader, feature_flags=feature_flags)

        curr_target = self.target.currentText()
        split_options = [_SPLIT_ALPHA, _SPLIT_RGBA]
        valid_targets = [_AUTO, _SKIP] + self.slots + split_options

        self.target.blockSignals(True)
        self.target.clear()
        self.target.addItems(valid_targets)
        if curr_target in valid_targets:
            self.target.setCurrentText(curr_target)
        else:
            self.target.setCurrentText(_AUTO)
        self.target.blockSignals(False)

        self._rebuild_channel_grid(self.target.currentText())

    def _rebuild_channel_grid(self, text: str):
        while self.channel_grid_layout.count():
            item = self.channel_grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.channel_combos = {}

        if text == _SPLIT_ALPHA:
            cols = [("rgb", "RGB (Base Map)"), ("a", "Alpha (A)")]
        elif text == _SPLIT_RGBA:
            cols = [("r", "R"), ("g", "G"), ("b", "B"), ("a", "A")]
        else:
            return

        for col, (ch_key, ch_label) in enumerate(cols):
            label = QLabel(ch_label)
            label.setAlignment(Qt.AlignCenter)
            combo = QComboBox()
            combo.setStyleSheet(f"{qt_stylesheet_combobox}\n{_DISABLED_STYLE_APPEND}")
            combo.addItem(_UNUSED)
            combo.addItems(self.channel_slots)
            self.channel_grid_layout.addWidget(label, 0, col)
            self.channel_grid_layout.addWidget(combo, 1, col)
            self.channel_combos[ch_key] = combo

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
            if override.get("split_rgba"):
                self.target.setCurrentText(_SPLIT_RGBA)
            elif override.get("split_alpha"):
                self.target.setCurrentText(_SPLIT_ALPHA)

            slot_mapping = override.get("channels") or override.get("slot") or override
            if isinstance(slot_mapping, dict):
                for slot, ch in slot_mapping.items():
                    if ch in self.channel_combos and slot in self.channel_slots:
                        self.channel_combos[ch].setCurrentText(slot)
                return
            if isinstance(slot_mapping, str) and slot_mapping in self.slots:
                return

        if override is _EXPLICIT_SKIP:
            self.target.setCurrentText(_SKIP)
            return

        if isinstance(override, str) and override in self.slots:
            self.target.setCurrentText(override)
            return

        self.target.setCurrentText(_AUTO)

    def _sync_channel_box(self, text):
        is_split = text in (_SPLIT_ALPHA, _SPLIT_RGBA)
        self.channel_box.setVisible(is_split)
        if is_split:
            self._rebuild_channel_grid(text)

    def value(self):
        """The stored override for this parameter, or _NO_OVERRIDE."""
        text = self.target.currentText()

        if text == _AUTO:
            return _NO_OVERRIDE
        if text == _SKIP:
            return None
        if text == _SPLIT_ALPHA:
            routed = {"split_alpha": True}
            for ch, combo in self.channel_combos.items():
                slot = combo.currentText()
                if slot != _UNUSED:
                    routed[slot] = ch
            return routed
        if text == _SPLIT_RGBA:
            routed = {"split_rgba": True}
            for ch, combo in self.channel_combos.items():
                slot = combo.currentText()
                if slot != _UNUSED:
                    routed[slot] = ch
            return routed

        return text


_NO_OVERRIDE = object()
_EXPLICIT_SKIP = object()


class _VectorParamRow(QHBoxLayout):
    """View row for Vector parameter with interactive QColorDialog swatch."""

    def __init__(self, name: str, val: dict, combo: QComboBox, parent=None):
        super().__init__()
        self.name = name
        self.val = dict(val) if isinstance(val, dict) else {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}

        self.swatch = QPushButton()
        self.swatch.setFixedSize(28, 22)
        self.swatch.setToolTip("Click to pick custom color tint")
        self.swatch.setCursor(Qt.PointingHandCursor)
        self.swatch.clicked.connect(self._on_pick_color)
        self._update_swatch_style()

        r = self.val.get("r", 1.0)
        g = self.val.get("g", 1.0)
        b = self.val.get("b", 1.0)
        val_fmt = f"<span style='background-color:#2A2A2D; color:#4EC9B0; padding:2px 6px; border-radius:3px; font-family:monospace;'>[{r:.2f}, {g:.2f}, {b:.2f}]</span>"
        label = QLabel(f"{name}  {val_fmt}")

        self.addWidget(self.swatch)
        self.addWidget(label, 1)
        self.addWidget(combo)

    def _update_swatch_style(self):
        r = int(self.val.get("r", 1.0) * 255)
        g = int(self.val.get("g", 1.0) * 255)
        b = int(self.val.get("b", 1.0) * 255)
        self.swatch.setStyleSheet(
            f"QPushButton {{ background-color: rgb({r},{g},{b}); border: 1px solid #555; border-radius: 3px; }}"
            f"QPushButton:hover {{ border: 1px solid #888; }}"
        )

    def _on_pick_color(self):
        r = int(self.val.get("r", 1.0) * 255)
        g = int(self.val.get("g", 1.0) * 255)
        b = int(self.val.get("b", 1.0) * 255)
        init_color = QColor(r, g, b)
        color = QColorDialog.getColor(init_color, None, f"Select Color Tint for {self.name}")
        if color.isValid():
            self.val["r"] = color.red() / 255.0
            self.val["g"] = color.green() / 255.0
            self.val["b"] = color.blue() / 255.0
            self._update_swatch_style()


class _ParamMappingTab(QWidget):
    """Migrate UE scalar/vector/switch params to Source 2 vmat params."""

    def __init__(self, scalars: dict, vectors: dict, switches: dict,
                 initial: dict = None, shader: str = None, parent=None):
        super().__init__(parent)
        self._rows = {}
        self.shader = shader
        self._scalars_items = sorted((scalars or {}).items())
        self._vectors_items = sorted((vectors or {}).items())
        self._switches_items = sorted((switches or {}).items())
        initial = initial or {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        self._add_scalars(outer, self._scalars_items, initial)
        self._add_vectors(outer, self._vectors_items, initial)
        self._add_switches(outer, self._switches_items, initial)

    def update_shader(self, shader: str):
        self.shader = shader
        scalar_targets = get_targets_for_shader(shader, _SCALAR_TARGETS)
        vector_targets = get_targets_for_shader(shader, _VECTOR_TARGETS)
        switch_targets = get_targets_for_shader(shader, _SWITCH_TARGETS)

        for name, combo in self._rows.items():
            curr_val = combo.currentData()
            if any(name == item_name for item_name, _ in self._scalars_items):
                t_list = scalar_targets
            elif any(name == item_name for item_name, _ in self._vectors_items):
                t_list = vector_targets
            else:
                t_list = switch_targets

            combo.blockSignals(True)
            combo.clear()
            for label_text, data in t_list:
                combo.addItem(label_text, data)
            idx = combo.findData(curr_val)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentIndex(0)
            combo.blockSignals(False)

    def _add_scalars(self, parent_layout, items, initial):
        if not items:
            return
        group = QFrame()
        group.setFrameShape(QFrame.StyledPanel)
        gl = QVBoxLayout(group)
        gl.setContentsMargins(8, 6, 8, 6)
        gl.setSpacing(4)
        gl.addWidget(QLabel("<b>Scalars (float)</b>"))
        targets = get_targets_for_shader(self.shader, _SCALAR_TARGETS)
        for name, val in items:
            row = QHBoxLayout()
            val_fmt = f"<span style='background-color:#2A2A2D; color:#4EC9B0; padding:2px 6px; border-radius:3px; font-family:monospace;'>{val:.4f}</span>"
            label = QLabel(f"{name}  {val_fmt}")
            combo = QComboBox()
            for label_text, data in targets:
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
        targets = get_targets_for_shader(self.shader, _VECTOR_TARGETS)
        for name, val in items:
            combo = QComboBox()
            for label_text, data in targets:
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
        targets = get_targets_for_shader(self.shader, _SWITCH_TARGETS)
        for name, val in items:
            row = QHBoxLayout()
            badge = "<span style='background-color:#1E3A1E; color:#4EC9B0; padding:2px 8px; border-radius:3px; font-weight:bold;'>ON</span>" if val else "<span style='background-color:#2D2D2D; color:#888888; padding:2px 8px; border-radius:3px;'>OFF</span>"
            label = QLabel(f"{name}  {badge}")
            combo = QComboBox()
            for label_text, data in targets:
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


class _FeatureInspectorWidget(QScrollArea):
    """CS2 Material Feature Inspector panel matching Hammer's layout."""

    feature_changed = Signal(str, str)
    features_changed = Signal(dict)
    shader_changed = Signal(str)

    def __init__(self, shader: str, feature_flags: dict = None, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumWidth(280)
        self.shader = shader or "csgo_environment.vfx"
        self.feature_flags = dict(feature_flags or {})
        self.checkboxes = {}

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Top Bar: Shader Selector
        top_box = QHBoxLayout()
        top_box.setSpacing(4)
        top_box.addWidget(QLabel("<b>Shader:</b>"))
        self.shader_combo = QComboBox()
        self.shader_combo.addItems(SHADERS)
        idx = self.shader_combo.findText(self.shader)
        if idx >= 0:
            self.shader_combo.setCurrentIndex(idx)
        self.shader_combo.setToolTip("Select target CS2 shader for this material.")
        self.shader_combo.currentTextChanged.connect(self._on_shader_changed)
        top_box.addWidget(self.shader_combo, 1)
        layout.addLayout(top_box)

        # Sections Container
        self.sections_container = QWidget()
        self.sections_layout = QVBoxLayout(self.sections_container)
        self.sections_layout.setContentsMargins(0, 0, 0, 0)
        self.sections_layout.setSpacing(6)
        layout.addWidget(self.sections_container)

        layout.addStretch(1)
        self.setWidget(container)

        self._build_feature_sections()

    def _build_feature_sections(self):
        for i in reversed(range(self.sections_layout.count())):
            item = self.sections_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self.checkboxes.clear()

        shader_low = str(self.shader).lower().strip()
        if "overlay" in shader_low or "decal" in shader_low:
            sections = [
                ("Lighting", [
                    ("F_LIT", "Lit (Enables Normal, Rough, Metal, AO, Self Illum)"),
                ]),
                ("Shadows", [
                    ("F_DO_NOT_CAST_SHADOWS", "Do Not Cast Shadows"),
                ]),
                ("2-Sided Rendering", [
                    ("F_RENDER_BACKFACES", "Render Backfaces"),
                    ("F_DONT_FLIP_BACKFACE_NORMALS", "Dont Flip Backface Normals"),
                ]),
                ("Z-Buffering", [
                    ("F_DISABLE_Z_BUFFERING", "Disable Z Buffering"),
                ]),
            ]
        elif "effects" in shader_low:
            sections = [
                ("Shadows", [
                    ("F_DO_NOT_CAST_SHADOWS", "Do Not Cast Shadows"),
                ]),
                ("2-Sided Rendering", [
                    ("F_RENDER_BACKFACES", "Render Backfaces"),
                    ("F_DONT_FLIP_BACKFACE_NORMALS", "Dont Flip Backface Normals"),
                ]),
                ("Z-Buffering", [
                    ("F_DISABLE_Z_BUFFERING", "Disable Z Buffering"),
                ]),
                ("Z-Prepass", [
                    ("F_DISABLE_Z_PREPASS", "Disable Z Prepass"),
                ]),
                ("Depth Feather", [
                    ("F_DEPTH_FEATHER", "Depth Feather"),
                ]),
                ("Translucent", [
                    ("F_ADDITIVE_BLEND", "Additive Blend"),
                ]),
                ("Per-Instance Tint Mask", [
                    ("F_TINT_MASK", "Per-Instance Tint Mask"),
                ]),
            ]
        else:
            sections = [
                ("Shadows", [
                    ("F_DO_NOT_CAST_SHADOWS", "Do Not Cast Shadows"),
                ]),
                ("2-Sided Rendering", [
                    ("F_RENDER_BACKFACES", "Render Backfaces"),
                    ("F_DONT_FLIP_BACKFACE_NORMALS", "Dont Flip Backface Normals"),
                ]),
                ("Z-Buffering", [
                    ("F_DISABLE_Z_BUFFERING", "Disable Z Buffering"),
                    ("F_DEPTH_BIAS", "Depth Bias"),
                    ("F_OCCLUSION_CULLING_BOUNDS_SCALE", "Occlusion Culling Bounds Scale"),
                ]),
                ("Z-Prepass", [
                    ("F_DISABLE_Z_PREPASS", "Disable Z Prepass"),
                ]),
                ("Translucent / Blend Mode", [
                    ("F_ALPHA_TEST", "Alpha Test"),
                    ("F_ADDITIVE_BLEND", "Additive Blend"),
                ]),
                ("Layer 2", [
                    ("F_BLEND_BY_FACING_DIRECTION_2", "Blend By Facing Direction 2"),
                    ("F_BLEND_EFFECTS_2", "Blend Effects 2"),
                    ("F_BORDER_ROUGHNESS_2", "Border Roughness 2"),
                ]),
                ("Layer 3", [
                    ("F_ENABLE_LAYER_3", "Enable Layer 3"),
                    ("F_BLEND_BY_FACING_DIRECTION_3", "Blend By Facing Direction 3"),
                    ("F_BLEND_EFFECTS_3", "Blend Effects 3"),
                    ("F_BORDER_ROUGHNESS_3", "Border Roughness 3"),
                ]),
                ("Detail", [
                    ("F_DETAIL_NORMAL", "Detail Normal"),
                ]),
                ("Wetness", [
                    ("F_WETNESS", "Wetness"),
                ]),
                ("Blending", [
                    ("F_USE_NEW_BLENDING", "Use New Blending"),
                ]),
                ("Color Effects", [
                    ("F_SHARED_COLOR_OVERLAY", "Shared Color Overlay"),
                ]),
                ("Tint Mask", [
                    ("F_TINT_MASK", "Tint Mask"),
                ]),
                ("Depth Feather", [
                    ("F_DEPTH_FEATHER", "Depth Feather"),
                ]),
                ("Visualizations", [
                    ("F_ENABLE_VISUALIZATIONS", "Enable Visualizations"),
                ]),
            ]

        self.feature_flags = validate_feature_flags(self.shader, self.feature_flags)

        for title, flags in sections:
            group = QFrame()
            group.setFrameShape(QFrame.StyledPanel)
            gl = QVBoxLayout(group)
            gl.setContentsMargins(4, 4, 4, 4)
            gl.setSpacing(4)

            hdr = QLabel(f"<b>{title}</b>")
            hdr.setAlignment(Qt.AlignCenter)
            hdr.setStyleSheet(
                "QLabel { background-color: #2D2D30; color: #E0E0E0; padding: 3px; font-size: 11px; font-weight: bold; border-radius: 2px; }"
            )
            gl.addWidget(hdr)

            for flag_name, flag_label in flags:
                cb = QCheckBox(flag_label)
                cb.setStyleSheet("QCheckBox:disabled { color: #666666; }")
                val = str(self.feature_flags.get(flag_name, "0")) in ("1", "True", "true")
                cb.setChecked(val)
                cb.toggled.connect(lambda checked, fn=flag_name: self._on_cb_toggled(fn, checked))
                gl.addWidget(cb)
                self.checkboxes[flag_name] = cb

            self.sections_layout.addWidget(group)

        self._update_prerequisite_states()
        force_apply_stylesheets(self)

    def _update_prerequisite_states(self):
        shader_rules = FEATURE_DEPENDENCIES.get(self.shader, {})
        for flag_name, cb in self.checkboxes.items():
            reqs = shader_rules.get(flag_name, [])
            enabled = True
            for req in reqs:
                req_cb = self.checkboxes.get(req)
                if req_cb and not req_cb.isChecked():
                    enabled = False
                    break
            cb.setEnabled(enabled)
            if not enabled and cb.isChecked():
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)

    def _on_cb_toggled(self, flag_name: str, checked: bool):
        self.feature_flags[flag_name] = "1" if checked else "0"
        self.feature_flags = validate_feature_flags(self.shader, self.feature_flags)

        for fn, cb in self.checkboxes.items():
            val = str(self.feature_flags.get(fn, "0")) in ("1", "True", "true")
            if cb.isChecked() != val:
                cb.blockSignals(True)
                cb.setChecked(val)
                cb.blockSignals(False)

        self._update_prerequisite_states()
        self.feature_changed.emit(flag_name, "1" if checked else "0")
        self.features_changed.emit(dict(self.feature_flags))

    def _on_shader_changed(self, new_shader: str):
        self.shader = new_shader
        self._build_feature_sections()
        self.shader_changed.emit(new_shader)
        self.features_changed.emit(dict(self.feature_flags))

    def value(self) -> dict:
        return dict(self.feature_flags)


class ShaderRemapperDialog(QDialog):
    """Configures texture parameter -> vmat slot overrides, parameter mappings,
    and CS2 material feature flags for a Master Material.
    """

    def __init__(self, master_name: str, textures: dict, initial_overrides: dict = None,
                 shader: str = None, scalars: dict = None, vectors: dict = None, switches: dict = None,
                 initial_param_overrides: dict = None, feature_flags: dict = None,
                 bulk_dir: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Shader Remapper — {master_name}")
        self.resize(960, 650)

        self.master_name = master_name
        self.textures = textures or {}
        self.shader = shader or "csgo_environment.vfx"
        self.bulk_dir = bulk_dir
        self.result_overrides = {}
        self.result_param_overrides = {}
        self.result_feature_flags = dict(feature_flags or {})
        self.result_shader = self.shader

        existing = initial_overrides or {}

        layout = QVBoxLayout(self)

        # Main Side-by-Side Splitter Layout
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter, 1)

        # --- Left Panel: CS2 Feature Inspector & Shader Selector ---
        self._feature_inspector = _FeatureInspectorWidget(
            self.shader, feature_flags=self.result_feature_flags, parent=self
        )
        self._feature_inspector.shader_changed.connect(self._on_shader_changed)
        self._feature_inspector.features_changed.connect(self._on_features_changed)
        main_splitter.addWidget(self._feature_inspector)

        # --- Right Panel: Unified Scroll Area (Texture Slots & Params) ---
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(6, 6, 6, 6)
        right_layout.setSpacing(10)

        # 1. Texture Slots Group
        tex_group = QFrame()
        tex_group.setFrameShape(QFrame.StyledPanel)
        tex_gl = QVBoxLayout(tex_group)
        tex_gl.setContentsMargins(6, 6, 6, 6)
        tex_gl.setSpacing(6)

        tex_hdr = QLabel("<b>Texture Slot Assignments</b>")
        tex_hdr.setAlignment(Qt.AlignCenter)
        tex_hdr.setStyleSheet(
            "QLabel { background-color: #2D2D30; color: #E0E0E0; padding: 4px; font-size: 11px; font-weight: bold; border-radius: 2px; }"
        )
        tex_gl.addWidget(tex_hdr)

        self._rows = []
        if not self.textures:
            tex_gl.addWidget(QLabel("No texture parameters found on this Master Material."))
        else:
            for param, path in sorted(self.textures.items()):
                override = existing[param] if param in existing else _NO_OVERRIDE
                if param in existing and existing[param] is None:
                    override = _EXPLICIT_SKIP
                row = _ParamRow(param, path, override, bulk_dir=self.bulk_dir, shader=self.shader)
                self._rows.append(row)
                tex_gl.addWidget(row)

        right_layout.addWidget(tex_group)

        # 2. Shader Parameter Overrides Group
        params_group = QFrame()
        params_group.setFrameShape(QFrame.StyledPanel)
        params_gl = QVBoxLayout(params_group)
        params_gl.setContentsMargins(6, 6, 6, 6)
        params_gl.setSpacing(6)

        params_hdr = QLabel("<b>Shader Parameter Overrides</b>")
        params_hdr.setAlignment(Qt.AlignCenter)
        params_hdr.setStyleSheet(
            "QLabel { background-color: #2D2D30; color: #E0E0E0; padding: 4px; font-size: 11px; font-weight: bold; border-radius: 2px; }"
        )
        params_gl.addWidget(params_hdr)

        self._params_tab = _ParamMappingTab(scalars, vectors, switches, initial_param_overrides, shader=self.shader)
        params_gl.addWidget(self._params_tab)

        right_layout.addWidget(params_group)

        right_layout.addStretch(1)
        right_scroll.setWidget(right_container)

        main_splitter.addWidget(right_scroll)

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)

        # Bottom Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setContentsMargins(4, 8, 4, 4)
        btn_box.setSpacing(8)

        reset_btn = QPushButton("Reset to Auto")
        reset_btn.setToolTip("Reset all texture slot overrides to automatic detection")
        reset_btn.clicked.connect(self._on_reset)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)

        btn_box.addWidget(reset_btn)
        btn_box.addStretch(1)
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)

        layout.addLayout(btn_box)

        force_apply_stylesheets(self)

    def _on_features_changed(self, feature_flags: dict):
        self.result_feature_flags = dict(feature_flags)
        for row in self._rows:
            row.update_shader(self.shader, feature_flags=self.result_feature_flags)

    def _on_shader_changed(self, new_shader: str):
        self.shader = new_shader
        self.result_shader = new_shader
        for row in self._rows:
            row.update_shader(new_shader, feature_flags=self.result_feature_flags)
        if hasattr(self, "_params_tab"):
            self._params_tab.update_shader(new_shader)

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
        self.result_feature_flags = self._feature_inspector.value()
        self.result_shader = self.shader
        self.accept()


# Alias for backwards compatibility
SlotMappingDialog = ShaderRemapperDialog
