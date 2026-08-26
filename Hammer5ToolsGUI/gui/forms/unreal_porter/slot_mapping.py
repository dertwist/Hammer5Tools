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
    QColorDialog, QCheckBox, QRadioButton, QGroupBox, QSplitter,
)

from gui.settings.main import get_settings_value, set_settings_value
from gui.styles.common import (
    apply_stylesheets,
    qt_stylesheet_button,
    qt_stylesheet_checkbox,
    qt_stylesheet_combobox,
    qt_stylesheet_toolbutton,
    qt_stylesheet_radiobutton,
    qt_stylesheet_groupbox,
)


_DISABLED_STYLE_APPEND = """
QPushButton:disabled, QToolButton:disabled {
    background-color: #2a2a2c;
    color: #727272;
    border-color: #3b3b3e;
}
QCheckBox:disabled {
    color: #727272;
}
QRadioButton:disabled {
    color: #727272;
}
QGroupBox:disabled {
    color: #727272;
    border-color: #3b3b3e;
}
QComboBox:disabled {
    background-color: #2a2a2c;
    color: #727272;
    border-color: #3b3b3e;
}
"""


def force_apply_stylesheets(parent: QWidget) -> None:
    """Force-applies registered Qt stylesheets to all child widgets with crisp gray text for disabled controls."""
    for cb in parent.findChildren(QCheckBox):
        cb.setStyleSheet(f"{qt_stylesheet_checkbox}\n{_DISABLED_STYLE_APPEND}")
    for rb in parent.findChildren(QRadioButton):
        rb.setStyleSheet(f"{qt_stylesheet_radiobutton}\n{_DISABLED_STYLE_APPEND}")
    for gb in parent.findChildren(QGroupBox):
        gb.setStyleSheet(f"{qt_stylesheet_groupbox}\n{_DISABLED_STYLE_APPEND}")
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
    get_shader_schema,
    validate_feature_flags,
    KIND_SCALAR, KIND_INT, KIND_BOOL, KIND_VECTOR2, KIND_VECTOR3, KIND_IVECTOR2, KIND_COLOR,
)

_NO_MAP = "(skip)"


def _param_targets_for_shader(shader: str, kinds: tuple) -> list:
    """Derive the (label, vmat_param) dropdown list for a kind group from the
    schema's blocks. Replaces the legacy flat SCALAR_TARGETS/VECTOR_TARGETS/
    SWITCH_TARGETS tables + get_targets_for_shader heuristic with per-shader
    targets straight from the shader's own parameter set."""
    schema = get_shader_schema(shader)
    targets = [(_NO_MAP, "")]
    seen = set()
    if schema is None:
        return targets
    for block in schema.blocks:
        for param in block.params:
            if param.kind not in kinds:
                continue
            if param.name in seen or param.name.startswith("F_"):
                continue
            seen.add(param.name)
            # Build a readable label: section + param name.
            label = f"{block.title} — {param.name}"
            targets.append((label, param.name))
    return targets


def _scalar_targets(shader: str) -> list:
    return _param_targets_for_shader(shader, (KIND_SCALAR, KIND_INT))


def _vector_targets(shader: str) -> list:
    return _param_targets_for_shader(shader, (KIND_VECTOR2, KIND_VECTOR3, KIND_IVECTOR2, KIND_COLOR))


def _switch_targets(shader: str) -> list:
    """Feature flags (F_*) the user can map a UE switch to. These come from the
    schema's features list, not its blocks (flags live in their own sections)."""
    schema = get_shader_schema(shader)
    targets = [(_NO_MAP, "")]
    if schema is None:
        return targets
    seen = set()
    for feat in schema.features:
        if feat.name in seen:
            continue
        seen.add(feat.name)
        targets.append((f"{feat.section} — {feat.name}", feat.name))
    return targets

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
            "QLabel { border: 1px solid #383838; background-color: #1A1A1C; border-radius: 4px; color: #999; font-size: 9px; font-weight: bold; }"
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
        # Show channel grid for the initial target (Auto/Skip/slot won't show it).
        # _apply_initial may set Split Alpha/RGBA, which triggers _sync_channel_box
        # via the signal, building the grid with smart defaults.  After that,
        # _apply_initial restores the saved channel selections on top.
        # Do NOT call _sync_channel_box again — that would rebuild the grid and
        # wipe the restored selections.
        self._sync_channel_box(self.target.currentText())
        self._apply_initial(override)

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

        param_low = str(self.param or "").lower()
        is_normal = any(k in param_low for k in ("normal", "nrm", "norm"))

        for col, (ch_key, ch_label) in enumerate(cols):
            label = QLabel(ch_label)
            label.setAlignment(Qt.AlignCenter)
            combo = QComboBox()
            combo.setStyleSheet(f"{qt_stylesheet_combobox}\n{_DISABLED_STYLE_APPEND}")
            combo.addItem(_UNUSED)
            available = self.slots if ch_key == "rgb" else self.channel_slots
            combo.addItems(available)

            # Auto-select smart default slot based on channel key
            default_slot = None
            if ch_key == "rgb":
                default_slot = "normal" if is_normal else "color"
            elif ch_key == "a":
                default_slot = "opacity"
            elif ch_key == "r":
                default_slot = "rough"
            elif ch_key == "g":
                default_slot = "metal"
            elif ch_key == "b":
                default_slot = "ao"

            if default_slot:
                idx = combo.findText(default_slot)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

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
        if isinstance(override, str):
            override_str = override.strip()
            if (override_str.startswith("{") and override_str.endswith("}")) or (override_str.startswith("[") and override_str.endswith("]")):
                try:
                    import ast
                    override = ast.literal_eval(override_str)
                except Exception:
                    try:
                        import json
                        override = json.loads(override_str)
                    except Exception:
                        pass

        if isinstance(override, dict):
            if override.get("split_rgba"):
                self.target.setCurrentText(_SPLIT_RGBA)
            elif override.get("split_alpha"):
                self.target.setCurrentText(_SPLIT_ALPHA)

            slot_mapping = override.get("channels") or override.get("slot") or override
            if isinstance(slot_mapping, dict):
                for slot, ch in slot_mapping.items():
                    if ch in self.channel_combos:
                        combo = self.channel_combos[ch]
                        idx = combo.findText(slot)
                        if idx >= 0:
                            combo.setCurrentIndex(idx)
                return
            if isinstance(slot_mapping, str) and slot_mapping in self.slots:
                return

        if override is _EXPLICIT_SKIP or (isinstance(override, str) and override.lower() in ("none", "null", "skip")):
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
        val_fmt = f"<span style='background-color:#3b3b3e; color:#4EC9B0; padding:2px 6px; border-radius:3px; font-family:monospace;'>[{r:.2f}, {g:.2f}, {b:.2f}]</span>"
        label = QLabel(f"{name}  {val_fmt}")

        self.addWidget(self.swatch)
        self.addWidget(label, 1)
        self.addWidget(combo)

    def _update_swatch_style(self):
        r = int(self.val.get("r", 1.0) * 255)
        g = int(self.val.get("g", 1.0) * 255)
        b = int(self.val.get("b", 1.0) * 255)
        self.swatch.setStyleSheet(
            f"QPushButton {{ background-color: rgb({r},{g},{b}); border: 1px solid #666; border-radius: 3px; }}"
            f"QPushButton:hover {{ border: 1px solid #999; }}"
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
        scalar_targets = _scalar_targets(shader)
        vector_targets = _vector_targets(shader)
        switch_targets = _switch_targets(shader)

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
        targets = _scalar_targets(self.shader)
        for name, val in items:
            row = QHBoxLayout()
            val_fmt = f"<span style='background-color:#3b3b3e; color:#4EC9B0; padding:2px 6px; border-radius:3px; font-family:monospace;'>{val:.4f}</span>"
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
        targets = _vector_targets(self.shader)
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
        targets = _switch_targets(self.shader)
        for name, val in items:
            row = QHBoxLayout()
            badge = "<span style='background-color:#1E3A1E; color:#4EC9B0; padding:2px 8px; border-radius:3px; font-weight:bold;'>ON</span>" if val else "<span style='background-color:#3e3e3e; color:#929292; padding:2px 8px; border-radius:3px;'>OFF</span>"
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
    blend_mode_changed = Signal(int)

    def __init__(self, shader: str, feature_flags: dict = None, blend_mode: int = 0, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumWidth(280)
        self.shader = shader or "csgo_environment.vfx"
        self.feature_flags = dict(feature_flags or {})
        self.blend_mode = int(blend_mode or 0)
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

        schema = get_shader_schema(self.shader)
        self.feature_flags = validate_feature_flags(self.shader, self.feature_flags)

        sections = {}
        section_order = []
        for feat in (schema.features if schema else ()):
            if feat.section not in sections:
                sections[feat.section] = []
                section_order.append(feat.section)
            sections[feat.section].append(feat)

        if schema and schema.blend_modes and "Blend Mode" not in sections:
            insert_idx = len(section_order)
            if "Lighting" in section_order:
                insert_idx = section_order.index("Lighting") + 1
            section_order.insert(insert_idx, "Blend Mode")
            sections["Blend Mode"] = []

        for title in section_order:
            feats = sections.get(title, [])
            group = QFrame()
            group.setFrameShape(QFrame.StyledPanel)
            gl = QVBoxLayout(group)
            gl.setContentsMargins(4, 4, 4, 4)
            gl.setSpacing(4)

            hdr = QLabel(f"<b>{title}</b>")
            hdr.setAlignment(Qt.AlignCenter)
            hdr.setStyleSheet(
                "QLabel { background-color: #3e3e41; color: #e2e2e2; padding: 3px; font-size: 11px; font-weight: bold; border-radius: 2px; }"
            )
            gl.addWidget(hdr)

            if title == "Blend Mode" and schema and schema.blend_modes:
                self._build_blend_mode_group(gl, schema.blend_modes)

            for feat in feats:
                if feat.is_enum:
                    self._build_enum_feature(gl, feat)
                else:
                    self._build_bool_feature(gl, feat)

            self.sections_layout.addWidget(group)

        self._update_prerequisite_states()
        force_apply_stylesheets(self)

    def _build_blend_mode_group(self, gl, blend_modes):
        """Render CS2 F_BLEND_MODE options as a QGroupBox with radio buttons matching Hammer."""
        gbox = QGroupBox("Blend Mode")
        gb_layout = QVBoxLayout(gbox)
        gb_layout.setContentsMargins(8, 8, 8, 8)
        gb_layout.setSpacing(4)

        self._blend_radio_map = {}
        for bm in blend_modes:
            rb = QRadioButton(bm.name)
            if self.blend_mode == bm.value:
                rb.setChecked(True)
            rb.toggled.connect(lambda checked, v=bm.value: self._on_blend_radio_toggled(checked, v))
            gb_layout.addWidget(rb)
            self._blend_radio_map[bm.value] = rb

        gl.addWidget(gbox)

    def _on_blend_radio_toggled(self, checked: bool, val: int):
        if checked:
            self.blend_mode = val
            self.blend_mode_changed.emit(val)

    def _build_bool_feature(self, gl, feat):
        """Render a boolean feature (range 0..1) as a checkbox."""
        cb = QCheckBox(feat.label)
        val = str(self.feature_flags.get(feat.name, str(feat.default))) in ("1", "True", "true")
        cb.setChecked(val)
        cb.toggled.connect(lambda checked, fn=feat.name: self._on_feature_changed(fn, "1" if checked else "0"))
        gl.addWidget(cb)
        self.checkboxes[feat.name] = cb

    def _build_enum_feature(self, gl, feat):
        """Render an enum-valued feature (range 0..N) as a QGroupBox with radio buttons matching CS2."""
        gbox = QGroupBox(feat.label)
        gb_layout = QVBoxLayout(gbox)
        gb_layout.setContentsMargins(8, 8, 8, 8)
        gb_layout.setSpacing(4)

        cur = str(self.feature_flags.get(feat.name, str(feat.default)))
        buttons = {}
        for i in range(feat.range_max + 1):
            name = feat.options[i] if i < len(feat.options) else str(i)
            rb = QRadioButton(name)
            if cur == str(i):
                rb.setChecked(True)
            rb.toggled.connect(lambda checked, val=str(i), fn=feat.name: self._on_enum_radio_toggled(checked, fn, val))
            gb_layout.addWidget(rb)
            buttons[str(i)] = rb

        gl.addWidget(gbox)
        gbox._feat_buttons = buttons
        self.checkboxes[feat.name] = gbox

    def _on_enum_radio_toggled(self, checked: bool, flag_name: str, val: str):
        if checked:
            self._on_feature_changed(flag_name, val)

    def _update_prerequisite_states(self):
        schema = get_shader_schema(self.shader)
        for flag_name, widget in self.checkboxes.items():
            feat = schema.feature(flag_name) if schema else None
            parents = (feat.requires + feat.child_of) if feat else ()
            enabled = True
            for req in parents:
                req_w = self.checkboxes.get(req)
                if req_w is None:
                    continue
                if isinstance(req_w, QCheckBox):
                    if not req_w.isChecked():
                        enabled = False
                        break
                elif isinstance(req_w, QGroupBox):
                    cur_val = str(self.feature_flags.get(req, "0"))
                    if cur_val in ("0", "False", "false", ""):
                        enabled = False
                        break
            widget.setEnabled(enabled)
            if not enabled:
                if isinstance(widget, QCheckBox):
                    if widget.isChecked():
                        widget.blockSignals(True)
                        widget.setChecked(False)
                        widget.blockSignals(False)
                        self.feature_flags[flag_name] = "0"
                elif isinstance(widget, QGroupBox) and hasattr(widget, "_feat_buttons"):
                    rb_0 = widget._feat_buttons.get("0")
                    if rb_0 and not rb_0.isChecked():
                        rb_0.blockSignals(True)
                        rb_0.setChecked(True)
                        rb_0.blockSignals(False)
                        self.feature_flags[flag_name] = "0"

    def _on_feature_changed(self, flag_name: str, value: str):
        self.feature_flags[flag_name] = value
        self.feature_flags = validate_feature_flags(self.shader, self.feature_flags)

        for fn, widget in self.checkboxes.items():
            cur = str(self.feature_flags.get(fn, "0"))
            if isinstance(widget, QCheckBox):
                on = cur in ("1", "True", "true")
                if widget.isChecked() != on:
                    widget.blockSignals(True)
                    widget.setChecked(on)
                    widget.blockSignals(False)
            elif isinstance(widget, QGroupBox) and hasattr(widget, "_feat_buttons"):
                rb = widget._feat_buttons.get(cur)
                if rb and not rb.isChecked():
                    rb.blockSignals(True)
                    rb.setChecked(True)
                    rb.blockSignals(False)

        self._update_prerequisite_states()
        self.feature_changed.emit(flag_name, value)
        self.features_changed.emit(dict(self.feature_flags))

    def _on_shader_changed(self, new_shader: str):
        self.shader = new_shader
        self.blend_mode = 0
        self._build_feature_sections()
        self.shader_changed.emit(new_shader)
        self.features_changed.emit(dict(self.feature_flags))
        self.blend_mode_changed.emit(self.blend_mode)

    def value(self) -> dict:
        return dict(self.feature_flags)


class ShaderRemapperDialog(QDialog):
    """Configures texture parameter -> vmat slot overrides, parameter mappings,
    and CS2 material feature flags for a Master Material.
    """

    def __init__(self, master_name: str, textures: dict, initial_overrides: dict = None,
                 shader: str = None, scalars: dict = None, vectors: dict = None, switches: dict = None,
                 initial_param_overrides: dict = None, feature_flags: dict = None,
                 blend_mode: int = 0,
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
        self.result_blend_mode = int(blend_mode or 0)
        self.result_shader = self.shader

        existing = initial_overrides or {}

        layout = QVBoxLayout(self)

        # Main Side-by-Side Splitter Layout
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter, 1)

        # --- Left Panel: CS2 Feature Inspector & Shader Selector ---
        self._feature_inspector = _FeatureInspectorWidget(
            self.shader, feature_flags=self.result_feature_flags,
            blend_mode=self.result_blend_mode, parent=self
        )
        self._feature_inspector.shader_changed.connect(self._on_shader_changed)
        self._feature_inspector.features_changed.connect(self._on_features_changed)
        self._feature_inspector.blend_mode_changed.connect(self._on_blend_mode_changed)
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
            "QLabel { background-color: #3e3e41; color: #e2e2e2; padding: 4px; font-size: 11px; font-weight: bold; border-radius: 2px; }"
        )
        tex_gl.addWidget(tex_hdr)

        self._rows = []
        if not self.textures:
            tex_gl.addWidget(QLabel("No texture parameters found on this Master Material."))
        else:
            existing_map = {k.lower(): v for k, v in (existing or {}).items()}
            for param, path in sorted(self.textures.items()):
                p_key = param.lower()
                if p_key in existing_map:
                    override = existing_map[p_key]
                    if override is None or (isinstance(override, str) and override.lower() in ("none", "null", "skip")):
                        override = _EXPLICIT_SKIP
                else:
                    override = _NO_OVERRIDE
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
            "QLabel { background-color: #3e3e41; color: #e2e2e2; padding: 4px; font-size: 11px; font-weight: bold; border-radius: 2px; }"
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

    def _on_blend_mode_changed(self, blend_mode: int):
        self.result_blend_mode = int(blend_mode or 0)

    def _on_shader_changed(self, new_shader: str):
        self.shader = new_shader
        self.result_shader = new_shader
        # New shader may not support the old blend mode — adopt the inspector's reset.
        self.result_blend_mode = self._feature_inspector.blend_mode
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
        self.result_blend_mode = self._feature_inspector.blend_mode
        self.result_shader = self.shader
        self.accept()


# Alias for backwards compatibility
SlotMappingDialog = ShaderRemapperDialog
