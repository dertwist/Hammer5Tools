"""Token cost of the vanilla Source 2 tasks, before and after the automation work.

Not a test: a measurement script. Run it against a content tree that has real
assets in it.

    python Hammer5ToolsGUI/Tests/benchmark_agent_tasks.py <a content directory>

"Before" reconstructs the previous behaviour (whole document returned, and
returned twice) rather than reaching into git history, so the two columns are
produced by the same run over the same assets.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from automation.formats.vmat_io import read_vmat, read_vmat_full  # noqa: E402
from automation.formats.vsmart_io import read_vsmart, read_vsmart_full  # noqa: E402
from automation.formats.vsmart_lint import lint_vsmart  # noqa: E402
from automation.operations.dependencies import resolve_dependencies  # noqa: E402


def tokens(payload) -> int:
    """Approximate tokens the way a JSON-RPC response is actually billed."""
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))) // 4


def before_read(path: str) -> int:
    """The old read: extracted fields plus the entire document under `raw`."""
    return tokens(read_vsmart_full(path))


def task_inspect_parameters(path: str) -> tuple[int, int]:
    """Task: what parameters does this SmartProp expose?"""
    return before_read(path), tokens(read_vsmart(path))


def task_change_one_parameter(path: str) -> tuple[int, int]:
    """Task: change one parameter's default.

    Before: read the whole document, then write the whole document back.
    After: address the one field, then patch it.
    """
    document = read_vsmart_full(path)
    variables = document.get("variables") or []
    if not variables:
        return 0, 0
    name = variables[0].get("m_VariableName", "")

    before = before_read(path) * 2
    selected = read_vsmart(path, select=f"m_Variables[m_VariableName={name}].m_DefaultValue")
    after = tokens(selected) + tokens({"op": "set", "target": f"m_Variables[m_VariableName={name}]", "value": 1.0})
    return before, after


def task_diagnose_broken_prop(path: str) -> tuple[int, int]:
    """Task: find why a SmartProp renders nothing.

    Before: read the whole document and reason over it unaided.
    After: one lint call naming the failure mode and its fix.
    """
    return before_read(path), tokens(lint_vsmart(path))


def task_retarget_a_material(path: str) -> tuple[int, int]:
    """Task: look at a material's texture slots in order to re-point them.

    Before: the whole parsed Layer0 came back alongside the extracted slots.
    After: the extracted view only.
    """
    return tokens(read_vmat_full(path)), tokens(read_vmat(path))


def task_map_dependencies(path: str) -> tuple[int, int]:
    """Task: what does this map pull in?

    Before: the per-kind lists plus a flat list that repeats every one of them.
    After: the per-kind lists, and only whatever no category claimed.
    """
    complete = resolve_dependencies(path, limit=None, include_all=True)
    trimmed = resolve_dependencies(path)
    return tokens(complete), tokens(trimmed)


_TASKS = {
    "inspect exposed parameters": ("*.vsmart", task_inspect_parameters),
    "change one parameter": ("*.vsmart", task_change_one_parameter),
    "diagnose a prop that renders nothing": ("*.vsmart", task_diagnose_broken_prop),
    "retarget a material": ("*.vmat", task_retarget_a_material),
    "read a map's dependencies": ("*.vmap", task_map_dependencies),
}


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    root = pathlib.Path(argv[0])
    if not root.is_dir():
        print(f"Not a directory: {argv[0]}")
        return 2

    print(f"{'task':38} {'files':>6} {'before':>10} {'after':>10} {'saved':>7}")
    print("-" * 76)
    for label, (pattern, task) in _TASKS.items():
        assets = sorted(root.rglob(pattern))
        if not assets:
            print(f"{label:38} {'-':>6}   no {pattern} found")
            continue
        before = after = measured = 0
        for asset in assets:
            try:
                asset_before, asset_after = task(str(asset))
            except Exception:
                continue
            before += asset_before
            after += asset_after
            measured += 1
        saved = 100 - (after * 100 / before) if before else 0.0
        print(f"{label:38} {measured:>6} {before:>10,} {after:>10,} {saved:>6.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
