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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QComboBox, QLabel,
    QDialogButtonBox, QWidget, QScrollArea, QFrame, QPushButton, QTabWidget,
)

from src.settings.main import get_settings_value, set_settings_value
from src.styles.common import apply_stylesheets
from .material_converter import (
    _SLOT_TOKENS, CHANNELS, CHANNEL_SLOTS, packed_layout,
)

_SLOTS = [slot for slot, _keys in _SLOT_TOKENS if slot != "orm"]
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


# Curated Source 2 (csgo_environment.vfx) param targets, grouped by UE value
# type. The first entry (empty value) means "leave to auto / don't map". A wrong
# pick is harmless — Source 2 ignores unknown params.
_SCALAR_TARGETS = [
    ("(don't map)", ""),
    ("Roughness scale", "g_flRoughnessScale"),
    ("Metalness scale", "g_flMetalnessScale"),
    ("Model tint amount", "g_flModelTintAmount"),
    ("Alpha test reference", "g_flAlphaTestReference"),
    ("Texcoord rotation", "g_flTexCoordRotation1"),
    ("Wetness darkening", "g_flWetnessDarkeningStrength1"),
]
_VECTOR_TARGETS = [
    ("(don't map)", ""),
    ("Color tint", "g_vColorTint"),
    ("Texcoord scale", "g_vTexCoordScale1"),
    ("Texcoord offset", "g_vTexCoordOffset1"),
    ("Texcoord center", "g_vTexCoordCenter1"),
]
_SWITCH_TARGETS = [
    ("(don't map)", ""),
    ("Alpha test", "F_ALPHA_TEST"),
    ("Render backfaces", "F_RENDER_BACKFACES"),
    ("Fog enabled", "g_bFogEnabled"),
]


def _tex_name(ue_path: str) -> str:
    """'/Game/T/Box_SRM.Box_SRM' -> 'Box_SRM'."""
    return str(ue_path or "").split("/")[-1].split(".")[0]


class _ParamRow(QFrame):
    """One UE texture parameter: what it is, and where its pixels should go."""

    def __init__(self, param: str, tex_path: str, override, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.param = param

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        head = QHBoxLayout()
        name = QLabel(f"<b>{param}</b>")
        tex = QLabel(_tex_name(tex_path))
        tex.setEnabled(False)  # themed as secondary text by the global QSS
        head.addWidget(name)
        head.addWidget(tex, 1)

        self.target = QComboBox()
        self.target.addItems([_AUTO, _SKIP] + _SLOTS + [_SPLIT])
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
            combo.addItems(CHANNEL_SLOTS)
            grid.addWidget(label, 0, col)
            grid.addWidget(combo, 1, col)
            self.channel_combos[ch] = combo
        outer.addWidget(self.channel_box)

        self._apply_initial(override)
        self.target.currentTextChanged.connect(self._sync_channel_box)
        self._sync_channel_box(self.target.currentText())

    def _apply_initial(self, override):
        if isinstance(override, dict):
            self.target.setCurrentText(_SPLIT)
            for slot, ch in override.items():
                if ch in self.channel_combos and slot in CHANNEL_SLOTS:
                    self.channel_combos[ch].setCurrentText(slot)
            return
        if override is _EXPLICIT_SKIP:
            self.target.setCurrentText(_SKIP)
            return
        if isinstance(override, str) and override in _SLOTS:
            self.target.setCurrentText(override)
            return
        self.target.setCurrentText(_AUTO)
        # Pre-fill the channel grid with the layout this mask would use, so
        # switching to Split starts from the detected convention rather than
        # an empty form.
        _tok, layout = packed_layout(self.param)
        for ch, slot in (layout or {}).items():
            if ch in self.channel_combos and slot in CHANNEL_SLOTS:
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
                    routed[slot] = ch   # stored slot -> channel
            return routed or None
        return text


# "no override stored" and "stored as excluded" both need to be distinguishable
# from each other and from a slot name; None already means excluded on disk.
_NO_OVERRIDE = object()
_EXPLICIT_SKIP = object()


class _ParamMappingTab(QWidget):
    """Migrate UE scalar/vector/switch params to Source 2 vmat params.

    One row per declared parameter, grouped by value type. Each row's combo
    picks a csgo_environment.vfx target (or "(don't map)"). The dialog reads
    the result via :meth:`value` at save time.
    """

    def __init__(self, scalars: dict, vectors: dict, switches: dict,
                 initial: dict = None, parent=None):
        super().__init__(parent)
        self._rows = {}   # ue_param_name -> QComboBox (so value() can read them)
        initial = initial or {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)

        self._add_section(body_layout, "Scalars (float)", sorted((scalars or {}).items()), _SCALAR_TARGETS, initial, lambda v: f"{v:.4f}")
        self._add_section(body_layout, "Vectors (color)", sorted((vectors or {}).items()), _VECTOR_TARGETS, initial,
                          lambda v: f"{v.get('r', 0):.2f}, {v.get('g', 0):.2f}, {v.get('b', 0):.2f}")
        self._add_section(body_layout, "Switches (bool)", sorted((switches or {}).items()), _SWITCH_TARGETS, initial,
                          lambda v: "on" if v else "off")

        body_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    def _add_section(self, parent_layout, title, items, targets, initial, fmt):
        """One labelled group of param rows. `targets` is the (label, value)
        list for that value type's combo."""
        if not items:
            return
        group = QFrame()
        group.setFrameShape(QFrame.StyledPanel)
        gl = QVBoxLayout(group)
        gl.setContentsMargins(8, 6, 8, 6)
        gl.setSpacing(4)
        header = QLabel(f"<b>{title}</b>")
        gl.addWidget(header)
        for name, val in items:
            row = QHBoxLayout()
            label = QLabel(f"{name}  ({fmt(val)})")
            label.setEnabled(False)
            combo = QComboBox()
            for label_text, data in targets:
                combo.addItem(label_text, data)
            # Pre-select the stored override if any; else the first "(don't map)".
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

    Two tabs: "Texture Slots" (texture param -> vmat slot) and "Params"
    (scalar/vector/switch -> vmat param). Both apply to every instance under the
    master material.
    """

    def __init__(self, master_name: str, textures: dict, initial_overrides: dict = None,
                 scalars: dict = None, vectors: dict = None, switches: dict = None,
                 initial_param_overrides: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Texture slots — {master_name}")
        self.resize(680, 560)

        self.master_name = master_name
        self.textures = textures or {}
        self.result_overrides = {}
        self.result_param_overrides = {}

        existing = initial_overrides or {}

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        # --- Tab 1: Texture Slots (the original dialog body) ---
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
                row = _ParamRow(param, path, override)
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

        # The dialog inherits the app-wide global sheet; this picks up the
        # shared per-widget sheets for the rows and the button box.
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
