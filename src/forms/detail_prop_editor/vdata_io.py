"""Read/write scripts/detail_prop_types.vdata as plain Python dicts."""

import os

from keyvalues3.keyvalues3 import Flag, flagged_value

from src.common import Kv3ToJson, JsonToKv3
from src.settings.common import get_addon_dir

from .schema import (
    GENERIC_DATA_TYPE, VDATA_RELATIVE_PATH,
    MODEL_FIELDS, TYPE_FIELDS, default_model, default_type,
)


def get_vdata_path(addon_dir: str = None) -> str:
    """Absolute path to the current addon's detail_prop_types.vdata."""
    addon_dir = addon_dir or get_addon_dir()
    if not addon_dir:
        return None
    return os.path.join(addon_dir, *VDATA_RELATIVE_PATH.split("/"))


def _unflag(value):
    """kv3 returns resource_name:"..." as a flagged_value — we want the string."""
    return value.value if isinstance(value, flagged_value) else value


def _normalize_model(raw: dict) -> dict:
    """Fill a loaded model with schema defaults, keeping any unknown keys."""
    model = default_model()
    known = {f.key for f in MODEL_FIELDS}
    for key, value in (raw or {}).items():
        value = _unflag(value)
        if key in known:
            model[key] = value
        else:
            model[key] = value  # preserve fields the schema doesn't know about
    if not isinstance(model.get("m_ModelName"), str):
        model["m_ModelName"] = ""
    for key in ("m_vRandomRotationMin", "m_vRandomRotationMax"):
        angle = model.get(key)
        if not isinstance(angle, list) or len(angle) != 3:
            model[key] = list(default_model()[key])
        else:
            model[key] = [float(v) for v in angle]
    return model


def _normalize_type(raw: dict) -> dict:
    raw = raw or {}
    detail_type = {f.key: f.default for f in TYPE_FIELDS}
    for key, value in raw.items():
        if key != "m_Models":
            detail_type[key] = _unflag(value)   # keeps unknown fields too
    models = raw.get("m_Models") or []
    detail_type["m_Models"] = [_normalize_model(m) for m in models] or [default_model()]
    return detail_type


def load_vdata(path: str) -> dict:
    """
    Parse the file into {type_name: CDetailPropType}. A missing or empty file
    yields a single 'placeholder' type so the editor always has something to show.
    """
    if not path or not os.path.exists(path):
        return {"placeholder": default_type()}

    with open(path, "r", encoding="utf-8") as file:
        raw = Kv3ToJson(file.read())

    if not isinstance(raw, dict):
        return {"placeholder": default_type()}

    types = {}
    for name, value in raw.items():
        if name == "generic_data_type" or not isinstance(value, dict):
            continue
        types[name] = _normalize_type(value)
    return types or {"placeholder": default_type()}


def _is_default(field, value) -> bool:
    if isinstance(field.default, list):
        try:
            return [float(v) for v in value] == [float(v) for v in field.default]
        except (TypeError, ValueError):
            return False
    if isinstance(field.default, bool):
        return bool(value) is field.default
    if isinstance(field.default, float):
        try:
            return abs(float(value) - field.default) < 1e-9
        except (TypeError, ValueError):
            return False
    return value == field.default


def _serialize_model(model: dict) -> dict:
    """Emit m_ModelName always, plus every field that differs from its default."""
    out = {"m_ModelName": flagged_value(model.get("m_ModelName") or "", Flag.resource_name)}
    known = {f.key for f in MODEL_FIELDS}
    for f in MODEL_FIELDS:
        if f.key == "m_ModelName":
            continue
        value = model.get(f.key, f.default)
        if _is_default(f, value):
            continue
        out[f.key] = list(value) if isinstance(value, list) else value
    for key, value in model.items():
        if key not in known:
            out[key] = value
    return out


def _serialize_type(detail_type: dict) -> dict:
    out = {}
    known = {f.key for f in TYPE_FIELDS} | {"m_Models"}
    for f in TYPE_FIELDS:
        value = detail_type.get(f.key, f.default)
        if not _is_default(f, value):
            out[f.key] = value
    for key, value in detail_type.items():
        if key not in known:
            out[key] = value
    out["m_Models"] = [_serialize_model(m) for m in detail_type.get("m_Models", [])]
    return out


def save_vdata(path: str, types: dict):
    """Write the type map back out as kv3, creating scripts/ if needed."""
    payload = {"generic_data_type": GENERIC_DATA_TYPE}
    for name, detail_type in types.items():
        payload[name] = _serialize_type(detail_type)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(JsonToKv3(payload))
