"""
Manual override for material_converter._classify_textures' heuristic slot
picks. Lets the user preview one Material Instance's detected texture params
(via bridge.dump_material) and reassign which vmat slot each maps to, or
exclude it entirely — e.g. "BaseColor2" heuristically lands on "color", but
the user can force it to "emissive" instead.

Overrides are keyed by UE parameter name, not per-material: Material
Instances sharing a master material repeat the same parameter names, so one
override (e.g. "BaseColor2" -> emissive) applies to all of them.
"""

import json

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLabel,
    QDialogButtonBox,
)

from src.settings.main import get_settings_value, set_settings_value
from .material_converter import _classify_textures, _SLOT_TOKENS

_SLOTS = [slot for slot, _keys in _SLOT_TOKENS]
_AUTO = "(auto)"
_SKIP = "(skip)"


def load_overrides() -> dict:
    """{param_name: slot_name or None}. None means the param is excluded."""
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


class SlotMappingDialog(QDialog):
    """Configures texture parameter -> vmat slot overrides for a Master Material.
    All Material Instances inheriting from this Master Material will use these slot mappings."""

    def __init__(self, master_name: str, textures: dict, initial_overrides: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Map texture slots — Master Material: {master_name}")
        self.resize(600, 400)

        self.master_name = master_name
        self.textures = textures or {}
        self.result_overrides = {}

        existing = initial_overrides or {}
        auto_picks = _classify_textures(self.textures)  # {slot: (param, path)}
        param_to_auto_slot = {param: slot for slot, (param, _p) in auto_picks.items()}

        self._combos = {}  # param -> QComboBox

        layout = QVBoxLayout(self)
        info_label = QLabel(
            f"<b>Master Material:</b> {master_name}<br>"
            f"Set texture parameter assignments below. All Material Instances belonging to "
            f"this Master Material will inherit these slot mappings when converted into .vmat."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        if not self.textures:
            layout.addWidget(QLabel("No texture parameters found on this Master Material."))
        else:
            form = QFormLayout()
            for param, path in sorted(self.textures.items()):
                combo = QComboBox()
                combo.addItem(_AUTO)
                combo.addItem(_SKIP)
                combo.addItems(_SLOTS)

                if param in existing:
                    forced = existing[param]
                    combo.setCurrentText(_SKIP if forced is None else forced)
                else:
                    auto_slot = param_to_auto_slot.get(param)
                    combo.setCurrentText(auto_slot if auto_slot in _SLOTS else _AUTO)
                self._combos[param] = combo

                row = QHBoxLayout()
                row.addWidget(QLabel(str(path)), 1)
                row.addWidget(combo)
                form.addRow(param, row)
            layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_save(self):
        overrides = {}
        for param, combo in self._combos.items():
            text = combo.currentText()
            if text == _AUTO:
                continue
            elif text == _SKIP:
                overrides[param] = None
            else:
                overrides[param] = text
        self.result_overrides = overrides
        self.accept()
