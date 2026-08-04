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
    QDialogButtonBox, QWidget, QScrollArea, QFrame, QPushButton,
)

from src.settings.main import get_settings_value, set_settings_value
from .material_converter import (
    _classify_textures, _SLOT_TOKENS, CHANNELS, CHANNEL_SLOTS, packed_layout,
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


def _tex_name(ue_path: str) -> str:
    """'/Game/T/Box_SRM.Box_SRM' -> 'Box_SRM'."""
    return str(ue_path or "").split("/")[-1].split(".")[0]


class _ParamRow(QFrame):
    """One UE texture parameter: what it is, and where its pixels should go."""

    def __init__(self, param: str, tex_path: str, auto_slot: str, override, parent=None):
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

        hint = auto_slot or "not used"
        self.hint = QLabel(f"Auto would pick: {hint}")
        self.hint.setEnabled(False)
        outer.addWidget(self.hint)

        self._apply_initial(auto_slot, override)
        self.target.currentTextChanged.connect(self._sync_channel_box)
        self._sync_channel_box(self.target.currentText())

    def _apply_initial(self, auto_slot, override):
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
        self.hint.setVisible(text == _AUTO)

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


class SlotMappingDialog(QDialog):
    """Configures texture parameter -> vmat slot overrides for a Master Material.
    All Material Instances inheriting from this Master Material use these mappings."""

    def __init__(self, master_name: str, textures: dict, initial_overrides: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Texture slots — {master_name}")
        self.resize(680, 560)

        self.master_name = master_name
        self.textures = textures or {}
        self.result_overrides = {}

        existing = initial_overrides or {}
        auto_picks = _classify_textures(self.textures)   # {slot: (param, path, channel)}
        param_to_auto = {}
        for slot, (param, _path, channel) in auto_picks.items():
            label = f"{slot} ({_CHANNEL_LABELS[channel]})" if channel else slot
            param_to_auto.setdefault(param, []).append(label)

        layout = QVBoxLayout(self)
        info = QLabel(
            f"<b>{master_name}</b> — every Material Instance under this master uses these "
            f"assignments.<br>Packed masks (SRMH, ORM, RMA…) are detected automatically; use "
            f"<i>{_SPLIT}</i> to route channels yourself."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._rows = []
        if not self.textures:
            layout.addWidget(QLabel("No texture parameters found on this Master Material."))
        else:
            body = QWidget()
            body_layout = QVBoxLayout(body)
            body_layout.setContentsMargins(0, 0, 0, 0)
            body_layout.setSpacing(6)
            for param, path in sorted(self.textures.items()):
                override = existing[param] if param in existing else _NO_OVERRIDE
                if param in existing and existing[param] is None:
                    override = _EXPLICIT_SKIP
                row = _ParamRow(param, path, ", ".join(param_to_auto.get(param, [])), override)
                self._rows.append(row)
                body_layout.addWidget(row)
            body_layout.addStretch(1)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(body)
            layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        reset = QPushButton("Reset to auto")
        reset.clicked.connect(self._on_reset)
        buttons.addButton(reset, QDialogButtonBox.ResetRole)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
        self.accept()
