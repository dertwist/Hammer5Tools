"""Static checks for .vsmart documents.

Each check here replaces a rule that would otherwise have to be carried in an
agent's context for every SmartProp it touches. The document is checked once,
and only the problems it actually has are reported.
"""

from __future__ import annotations

import pathlib
import re
from typing import Any

from automation.formats.shaping import iter_element_id_nodes
from automation.formats.vsmart_io import read_vsmart_full

# Anything an expression may reference that is not a document variable.
_INTRINSICS = frozenset({
    "InstanceIndex", "InstanceCount", "LinearScale", "RandomFloat", "RandomInt",
    "Deg2rad", "Rad2deg", "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "sqrt", "abs", "min", "max", "floor", "ceil", "round", "pow", "clamp", "lerp",
    "Pi", "pi", "e", "true", "false", "x", "y", "z", "w", "r", "g", "b", "a",
})

_LOWER_INTRINSICS = frozenset(name.lower() for name in _INTRINSICS)

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_TRIG_CALL = re.compile(r"\b(atan|asin|acos)\s*\(", re.IGNORECASE)

_NUMERIC_CLASSES = frozenset({
    "CSmartPropVariable_Float",
    "CSmartPropVariable_Int",
    "CSmartPropVariable_Vector3D",
    "CSmartPropVariable_Angles",
})


def _finding(check: str, message: str, where: str = "") -> dict[str, str]:
    finding = {"check": check, "message": message}
    if where:
        finding["where"] = where
    return finding


def _walk(node: Any, path: str = ""):
    """Yield every (path, dict) in the document."""
    if isinstance(node, dict):
        yield path, node
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _walk(item, f"{path}[{index}]")


def _expressions(root: Any) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path, node in _walk(root):
        for key in ("m_Expression", "m_HideExpression", "m_ReadOnlyExpression"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                found.append((f"{path}.{key}" if path else key, value))
    return found


def _divisors(expression: str) -> list[str]:
    """Return each divisor as written, keeping parenthesised divisors whole."""
    found: list[str] = []
    index = 0
    while True:
        index = expression.find("/", index)
        if index < 0:
            return found
        cursor = index + 1
        while cursor < len(expression) and expression[cursor].isspace():
            cursor += 1
        if cursor >= len(expression):
            return found
        if expression[cursor] == "(":
            divisor = "(" + _balanced_argument(expression, cursor) + ")"
        else:
            stop = cursor
            while stop < len(expression) and not expression[stop].isspace() and expression[stop] not in "),":
                stop += 1
            divisor = expression[cursor:stop]
        found.append(divisor)
        index = cursor + len(divisor)


def _is_safe_divisor(divisor: str) -> bool:
    """True when the divisor cannot reach zero: a non-zero literal, or guarded by max()."""
    stripped = divisor.strip().strip("()").strip()
    try:
        return float(stripped) != 0.0
    except ValueError:
        pass
    return stripped.lower().startswith("max")


def _check_unguarded_division(root: Any) -> list[dict[str, str]]:
    findings = []
    for where, expression in _expressions(root):
        for divisor in _divisors(expression):
            if _is_safe_divisor(divisor):
                continue
            findings.append(_finding(
                "unguarded-division",
                f"The divisor '{divisor}' can evaluate to 0. A 0/0 yields NaN, and one NaN "
                f"invalidates the whole transform, so the instance disappears with no "
                f"diagnostic. Wrap it in max(1.0, ...). Full expression: '{expression}'",
                where,
            ))
            break
    return findings


def _balanced_argument(expression: str, open_index: int) -> str:
    """Return the argument of a call whose opening parenthesis is at open_index."""
    depth = 0
    for index in range(open_index, len(expression)):
        if expression[index] == "(":
            depth += 1
        elif expression[index] == ")":
            depth -= 1
            if depth == 0:
                return expression[open_index + 1:index]
    return expression[open_index + 1:]


def _check_trig_of_quotient(root: Any) -> list[dict[str, str]]:
    findings = []
    for where, expression in _expressions(root):
        for match in _TRIG_CALL.finditer(expression):
            argument = _balanced_argument(expression, match.end() - 1)
            if "/" not in argument or "max" in argument.lower():
                continue
            findings.append(_finding(
                "unguarded-trig",
                f"{match.group(1)}() is fed the unguarded quotient '{argument.strip()}'. "
                f"{match.group(1)}(NaN) is NaN and propagates into the rotation matrix, "
                f"which makes every instance of this element disappear.",
                where,
            ))
    return findings


def _check_untyped_defaults(root: Any) -> list[dict[str, str]]:
    findings = []
    for variable in root.get("m_Variables") or []:
        if not isinstance(variable, dict):
            continue
        class_name = str(variable.get("_class", ""))
        if class_name not in _NUMERIC_CLASSES:
            continue
        if variable.get("m_DefaultValue", "") in ("", None):
            findings.append(_finding(
                "untyped-default",
                f"'{variable.get('m_VariableName', '?')}' is a {class_name} with an empty "
                f"default. A static evaluator reads that as 0, which can collapse instance "
                f"counts to nothing before any SetVariable runs.",
                f"m_Variables[m_VariableName={variable.get('m_VariableName', '')}]",
            ))
    return findings


def _check_empty_expression_objects(root: Any) -> list[dict[str, str]]:
    findings = []
    for path, node in _walk(root):
        value = node.get("m_Expression")
        if isinstance(value, str) and not value.strip():
            findings.append(_finding(
                "empty-expression",
                "An empty m_Expression is serialized where a number belongs. Write the "
                "numeric value (for example 0.0) instead of an empty expression object.",
                path,
            ))
    return findings


def _check_duplicate_element_ids(root: Any) -> list[dict[str, str]]:
    seen: dict[int, str] = {}
    duplicates: dict[int, list[str]] = {}
    for path, container in iter_element_id_nodes(root):
        element_id = container.get("m_nElementID")
        if not isinstance(element_id, int):
            continue
        if element_id in seen:
            duplicates.setdefault(element_id, [seen[element_id]]).append(path)
        else:
            seen[element_id] = path
    return [
        _finding(
            "duplicate-element-id",
            f"Element ID {element_id} is used {len(paths)} times. Hammer's outliner "
            f"selects ambiguously when IDs repeat; vsmart_patch reindexes on write.",
            ", ".join(paths[:4]),
        )
        for element_id, paths in sorted(duplicates.items())
    ]


def _check_linear_scale_on_endcap(root: Any) -> list[dict[str, str]]:
    findings = []
    for path, node in _walk(root):
        criteria = node.get("m_SelectionCriteria")
        has_endcap = any(
            isinstance(item, dict) and "EndCap" in str(item.get("_class", ""))
            for item in (criteria if isinstance(criteria, list) else [])
        )
        if not has_endcap:
            continue
        if "LinearScale()" in str(node.get("m_vModelScale", "")):
            findings.append(_finding(
                "endcap-linear-scale",
                "LinearScale() is applied to an EndCap-selected model. End posts must "
                "stay at scale 1.0 or the termination piece is visibly distorted.",
                path,
            ))
    return findings


def _check_category_markers(root: Any) -> list[dict[str, str]]:
    starts, ends = set(), set()
    for variable in root.get("m_Variables") or []:
        if not isinstance(variable, dict):
            continue
        name = str(variable.get("m_VariableName", ""))
        if not name.startswith("hammer5tools_category_"):
            continue
        if name.endswith("_start"):
            starts.add(name[len("hammer5tools_category_"):-len("_start")])
        elif name.endswith("_end"):
            ends.add(name[len("hammer5tools_category_"):-len("_end")])
    return [
        _finding(
            "unpaired-category",
            f"Category '{slug}' has only a {'start' if slug in starts else 'end'} marker. "
            f"Hammer5Tools needs both to close the collapsible card.",
            f"hammer5tools_category_{slug}_*",
        )
        for slug in sorted(starts.symmetric_difference(ends))
    ]


def _check_unknown_variable_references(root: Any) -> list[dict[str, str]]:
    # Hammer resolves identifiers case-insensitively: shipped presets declare
    # "Sizer_X" and reference it as "sizer_x".
    declared = {
        str(variable.get("m_VariableName", "")).lower()
        for variable in root.get("m_Variables") or []
        if isinstance(variable, dict)
    }
    findings = []
    for where, expression in _expressions(root):
        unknown = sorted({
            identifier
            for identifier in _IDENTIFIER.findall(expression)
            if identifier.lower() not in declared and identifier.lower() not in _LOWER_INTRINSICS
        })
        if unknown:
            findings.append(_finding(
                "unknown-variable",
                f"'{expression.strip()}' references {', '.join(unknown)}, which no variable "
                f"declares. Hammer evaluates an unknown name as 0, so the condition never fires.",
                where,
            ))
    return findings


_CHECKS = (
    _check_unguarded_division,
    _check_trig_of_quotient,
    _check_untyped_defaults,
    _check_empty_expression_objects,
    _check_duplicate_element_ids,
    _check_linear_scale_on_endcap,
    _check_category_markers,
    _check_unknown_variable_references,
)


def lint_document(root: Any) -> list[dict[str, str]]:
    """Run every check against an already-parsed SmartProp document."""
    findings: list[dict[str, str]] = []
    for check in _CHECKS:
        findings.extend(check(root))
    return findings


def lint_vsmart(path: str) -> dict[str, Any]:
    """Check a .vsmart file, or every .vsmart under a directory, for silent failures.

    Auditing a library one call per file costs more in round trips than the
    findings are worth, so a directory reports per-file counts and only the
    findings themselves for the files that have any.
    """
    target = pathlib.Path(path)
    if target.is_dir():
        return _lint_directory(target)

    findings = lint_document(read_vsmart_full(path)["raw"])
    return {
        "path": path.replace("\\", "/"),
        "finding_count": len(findings),
        "clean": not findings,
        "findings": findings,
    }


def _lint_directory(directory: pathlib.Path) -> dict[str, Any]:
    counts: dict[str, int] = {}
    files: list[dict[str, Any]] = []
    checked = 0

    for asset in sorted(directory.rglob("*.vsmart")):
        checked += 1
        try:
            findings = lint_document(read_vsmart_full(str(asset))["raw"])
        except (OSError, ValueError) as error:
            files.append({"path": asset.as_posix(), "error": str(error)})
            continue
        if not findings:
            continue
        for finding in findings:
            counts[finding["check"]] = counts.get(finding["check"], 0) + 1
        files.append({
            "path": asset.as_posix(),
            "finding_count": len(findings),
            "findings": findings,
        })

    return {
        "directory": directory.as_posix(),
        "files_checked": checked,
        "files_with_findings": sum(1 for item in files if item.get("finding_count")),
        "counts_by_check": dict(sorted(counts.items(), key=lambda pair: -pair[1])),
        "clean": not counts,
        "files": files,
    }
