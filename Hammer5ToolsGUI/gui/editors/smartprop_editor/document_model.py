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
from copy import deepcopy
from dataclasses import dataclass, field

from gui.editors.smartprop_editor.objects import variable_prefix

log = logging.getLogger(__name__)

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


@dataclass
class SmartPropNode:
    """One hierarchy element whose children are model-owned."""

    data: dict
    children: list["SmartPropNode"] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, value: Mapping) -> "SmartPropNode":
        data = deepcopy(dict(value))
        child_values = data.pop("m_Children", []) or []
        return cls(data=data, children=[cls.from_mapping(child) for child in child_values])

    @property
    def element_id(self):
        return self.data.get("m_nElementID")

    def to_mapping(self) -> dict:
        value = deepcopy(self.data)
        if self.children or "m_Children" in self.data:
            value["m_Children"] = [child.to_mapping() for child in self.children]
        return value

    def find(self, element_id) -> "SmartPropNode | None":
        if self.element_id == element_id:
            return self
        for child in self.children:
            found = child.find(element_id)
            if found is not None:
                return found
        return None


@dataclass
class SmartPropDocumentState:
    """Qt-free state for one SmartProp document.

    Widgets render this mapping but must not become its authoritative owner.
    The explicit sections provide the migration boundary for the hierarchy,
    variables, and choices adapters.
    """

    metadata: dict = field(default_factory=dict)
    hierarchy: list[SmartPropNode] = field(default_factory=list)
    variables: list[dict] = field(default_factory=list)
    choices: list[dict] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, document: Mapping) -> "SmartPropDocumentState":
        if not isinstance(document, Mapping):
            raise TypeError("A SmartProp document must be a mapping")
        root = deepcopy(dict(document))
        children = root.pop("m_Children", []) or []
        variables = root.pop("m_Variables", []) or []
        choices = root.pop("m_Choices", []) or []
        return cls(
            metadata=root,
            hierarchy=[SmartPropNode.from_mapping(child) for child in children],
            variables=variables,
            choices=choices,
        )

    @property
    def children(self) -> list[dict]:
        return [node.to_mapping() for node in self.hierarchy]

    def find(self, element_id) -> SmartPropNode | None:
        for node in self.hierarchy:
            found = node.find(element_id)
            if found is not None:
                return found
        return None

    def to_mapping(self) -> dict:
        """Return an independent mapping suitable for CoreBridge serialization."""
        document = deepcopy(self.metadata)
        document["m_Children"] = self.children
        if self.variables:
            document["m_Variables"] = deepcopy(self.variables)
        if self.choices:
            document["m_Choices"] = deepcopy(self.choices)
        return document


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
# The Core owns the SmartProp format; it is what the game and compiler agree
# with. The GUI deliberately has no second parser/writer fallback: silently
# changing implementations made saved output depend on whether the native
# library happened to initialise.


def parse_smartprop(text: str) -> dict:
    """Read SmartProp KV3 text into a document."""
    text = normalize_kv3_text(text)
    try:
        from core.bridge import CoreBridge
        return CoreBridge.instance().deserialize_smartprop(text)
    except Exception as error:
        log.error("Core failed to parse SmartProp document", exc_info=True)
        raise RuntimeError("SmartProp parsing requires Hammer5Tools Core") from error


def format_smartprop(document: Mapping, one_line_properties: bool = False) -> str:
    """Write a document back out as SmartProp KV3 text."""
    try:
        from core.bridge import CoreBridge
        return CoreBridge.instance().serialize_smartprop(document)
    except Exception as error:
        log.error("Core failed to serialize SmartProp document", exc_info=True)
        raise RuntimeError("SmartProp serialization requires Hammer5Tools Core") from error


#: Per-class fallback when a variable has no default value yet.
_VARIABLE_DEFAULTS = {
    "Color": [255, 255, 255],
    "Bool": False,
    "Vector3D": [1, 1, 1],
    "Vector2D": [0, 0],
    "Vector4D": [0, 0, 0, 0],
    "Int": 0,
    "Float": 0.0,
}

_CATEGORY_LABEL_RE = re.compile(r"---------- (.*) ----------")


def _variable_default(var_class, value):
    """The default to serialize for a variable, filling in a per-class fallback."""
    if value is None:
        return deepcopy(_VARIABLE_DEFAULTS.get(var_class, ""))
    if var_class == "Color" and (
        value == "" or not isinstance(value, (list, tuple)) or len(value) < 3
    ):
        return [255, 255, 255]
    return value


def variable_rows_to_kv3(rows):
    """Convert variable rows into the document's ``m_Variables`` list.

    ``rows`` is {index: [name, var_class, var_value, visible_in_editor,
    display_name]} as produced by ``_common.read_variable_rows``. Pure data in,
    pure data out: no Qt, so the mapping rules are testable on their own.
    """
    variables = []
    for _index, row in sorted(rows.items()):
        name, var_class, var_value, visible_in_editor, display_name = row
        variable = {
            "_class": variable_prefix + var_class,
            "m_VariableName": name,
            "m_bExposeAsParameter": visible_in_editor,
            "m_DefaultValue": _variable_default(var_class, var_value["default"]),
            "m_nElementID": var_value["m_nElementID"],
        }
        if display_name not in (None, ""):
            variable["m_DisplayName"] = display_name

        if name and is_category_marker(name):
            if name.endswith("_start"):
                match = _CATEGORY_LABEL_RE.search(display_name or "")
                variable["m_Hammer5ToolsCategoryName"] = (
                    match.group(1).strip() if match else "Category name"
                )
            else:
                variable["m_Hammer5ToolsCategoryName"] = "New category"

        minimum, maximum = var_value["min"], var_value["max"]
        if minimum is not None and var_class in ("Float", "Int"):
            key = "m_flParamaterMinValue" if var_class == "Float" else "m_nParamaterMinValue"
            variable[key] = minimum
        if maximum is not None and var_class in ("Float", "Int"):
            key = "m_flParamaterMaxValue" if var_class == "Float" else "m_nParamaterMaxValue"
            variable[key] = maximum

        if var_value["model"] is not None:
            variable["m_sModelName"] = var_value["model"]
        if var_value["m_HideExpression"] is not None:
            variable["m_HideExpression"] = var_value["m_HideExpression"]
        read_only = var_value.get("m_ReadOnlyExpression")
        if read_only is not None:
            variable["m_ReadOnlyExpression"] = read_only

        variables.append(variable)
    return variables
