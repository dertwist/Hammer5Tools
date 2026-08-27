"""Plain-Python model behind the SmartProp editor's KV3 document.

Deliberately free of any Qt import. The editor keeps its document state in
widgets (a QTreeWidget hierarchy, a variables layout), which makes the rules
for reading that state hard to test and easy to duplicate -- the variable
decode below existed twice in document.py with different bugs, and the KV3
text normalisation existed three times across document.py, vsmart.py and
manual_editor.py. Rules that are about the document rather than the widgets
belong here.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

import keyvalues3 as kv3
from keyvalues3.textwriter import KV3EncoderOptions

from gui.editors.smartprop_editor.objects import variable_prefix

log = logging.getLogger(__name__)

_KV3_HEADER = (
    "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} "
    "format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->"
)

# Hammer5Tools writes category separators as ordinary variables with a marker
# name. Both spellings are in the wild: files written before nested categories
# existed use the first.
_CATEGORY_MARKER_RES = (
    re.compile(r"hammer5tools_category_([a-z0-9]+)_(start|end)"),
    re.compile(r"hammer5tools_category_(.*)_category_(.*)_(start|end)"),
)

_CATEGORY_END_LABEL = "                                             "

# Value keys that only apply to a numeric variable, per class.
_RANGE_KEYS = {
    "Float": ("m_flParamaterMinValue", "m_flParamaterMaxValue"),
    "Int": ("m_nParamaterMinValue", "m_nParamaterMaxValue"),
}


def normalize_kv3_text(text: str) -> str:
    """Undo the two things various exporters emit that the KV3 parser rejects."""
    text = re.sub(r"= resource_name:", "= ", text)
    return text.replace("null,", "")


def is_category_marker(name: str | None) -> bool:
    """True when a variable name is a category separator rather than a variable."""
    if not name:
        return False
    return any(pattern.match(name) for pattern in _CATEGORY_MARKER_RES)


def category_label(name: str, category_name: str) -> str:
    """The display text a category marker shows in the variables list."""
    return f"---------- {category_name} ----------" if name.endswith("_start") else _CATEGORY_END_LABEL


def rename_references(value, old_name: str, new_name: str):
    """Rewrite whole-word references to a variable through nested KV3 data."""
    pattern = re.compile(rf"\b{re.escape(old_name)}\b")

    def rewrite(node):
        if isinstance(node, str):
            return pattern.sub(new_name, node)
        if isinstance(node, list):
            return [rewrite(item) for item in node]
        if isinstance(node, dict):
            return {key: rewrite(item) for key, item in node.items()}
        return node

    return rewrite(value)


@dataclass
class Variable:
    """One decoded entry of a document's m_Variables list."""

    name: str | None
    var_class: str
    display_name: str | None
    visible_in_editor: bool
    value: dict = field(default_factory=dict)
    is_category: bool = False

    @property
    def element_id(self):
        return self.value.get("m_nElementID")


def decode_variable(entry: dict) -> Variable:
    """Turn one raw KV3 variable into the shape the editor's widgets take."""
    var_class = entry.get("_class", "").replace(variable_prefix, "")
    name = entry.get("m_VariableName")
    is_category = is_category_marker(name)
    category_name = entry.get("m_Hammer5ToolsCategoryName")

    if is_category and category_name is not None:
        display_name = category_label(name, category_name)
    else:
        # Older files carried the label under two other keys. Only a missing
        # key falls through -- an empty string is a label the user set.
        display_name = entry.get("m_DisplayName")
        if display_name is None:
            display_name = entry.get("m_sCommentary")
        if display_name is None:
            display_name = entry.get("m_ParameterName")

    value = {
        "default": entry.get("m_DefaultValue"),
        "model": entry.get("m_sModelName"),
        "m_nElementID": entry.get("m_nElementID"),
        "m_HideExpression": entry.get("m_HideExpression"),
        "m_ReadOnlyExpression": entry.get("m_ReadOnlyExpression"),
    }
    min_key, max_key = _RANGE_KEYS.get(var_class, (None, None))
    value["min"] = entry.get(min_key) if min_key else None
    value["max"] = entry.get(max_key) if max_key else None

    return Variable(
        name=name,
        var_class=var_class,
        display_name=display_name,
        visible_in_editor=bool(entry.get("m_bExposeAsParameter")),
        value=value,
        is_category=is_category,
    )


# ── Reading and writing the document ────────────────────────────────────
#
# The Core owns the SmartProp format; it is what the game and the compiler
# agree with. The keyvalues3 fallbacks below exist only so a machine whose
# optional .NET runtime will not initialise can still open and save files,
# and they are the reason every caller must come through here rather than
# reaching for keyvalues3 directly.


def parse_smartprop(text: str) -> dict:
    """Read SmartProp KV3 text into a document."""
    text = normalize_kv3_text(text)
    try:
        from core.bridge import CoreBridge
        return CoreBridge.instance().deserialize_smartprop(text)
    except Exception as error:
        log.info(f"Core unavailable, parsing SmartProp with keyvalues3: {error}")
        if "<!-- kv3 encoding:" not in text:
            text = _KV3_HEADER + "\n{" + text + "\n}"
        return kv3.textreader.KV3TextReader().parse(text).value


def format_smartprop(document: Mapping, one_line_properties: bool = False) -> str:
    """Write a document back out as SmartProp KV3 text."""
    try:
        from core.bridge import CoreBridge
        return CoreBridge.instance().serialize_smartprop(document)
    except Exception as error:
        log.info(f"Core unavailable, writing SmartProp with keyvalues3: {error}")
        from gui.editors.smartprop_editor._common import disable_line_value_length_limit_keys
        options = KV3EncoderOptions(
            serialize_enums_as_ints=False,
            no_header=False,
            disable_line_value_length_limit_keys=(
                disable_line_value_length_limit_keys if one_line_properties else None
            ),
        )
        return kv3.textwriter.encode(
            kv3.KV3File(value=dict(document), format=kv3.FORMAT_GENERIC), options=options
        )
