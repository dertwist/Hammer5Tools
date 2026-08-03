"""
Every stylesheet in the source must actually parse.

Qt does not raise on a malformed stylesheet. It prints one line to stderr —

    Could not parse stylesheet of object QLabel(0x1d7f56cb1c0)

— throws the *whole* sheet away, and carries on. The widget then renders with
no styling at all, which is easy to mistake for a layout or colour problem.
Four real offenders were found this way, none of them visible by eye:

  * two ``QLabel`` blocks in ``qt_stylesheet_classes`` missing their closing
    brace, applied to every label at startup through ``apply_stylesheets()``;
  * a block using ``#`` for comments — in QSS ``#`` starts an ID selector;
  * a stray comma between two declarations.

Two sources are checked, because a sheet can reach a widget either way:

  * literals, f-strings and ``%``-formats passed straight to setStyleSheet();
  * module-level stylesheet constants, which never appear at a call site.

Interpolated values are replaced with a dummy before parsing — this checks the
*shape* of a sheet, which is what breaks, not the colours substituted into it.
"""

import ast
import importlib
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtWidgets import QApplication, QLabel

STYLE_MODULES = [
    "src.styles.common",
    "src.styles.widgets",
    "src.styles.qt_global_stylesheet",
]

_failures: list[tuple[str, str]] = []
_current: dict = {}


def _handler(mode, context, message):
    if "Could not parse" in message:
        _failures.append((_current["where"], _current["sheet"]))


def _resolve(node) -> str | None:
    """Source text of a stylesheet argument, with interpolations stubbed out."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            str(part.value) if isinstance(part, ast.Constant) else "#000000"
            for part in node.values
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        left = _resolve(node.left)
        if left is None:
            return None
        return re.sub(r"%\([^)]*\)?[sdif]|%[sdif]", "#000000", left)
    return None


def _check(where: str, sheet: str) -> bool:
    if ":" not in sheet:
        return False
    _current["where"] = where
    _current["sheet"] = sheet.strip().replace("\n", " ")[:100]
    QLabel().setStyleSheet(sheet)
    return True


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    qInstallMessageHandler(_handler)

    checked = 0
    for path in sorted((ROOT / "src").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setStyleSheet"
                and node.args
            ):
                continue
            sheet = _resolve(node.args[0])
            if sheet and _check(f"{path.relative_to(ROOT)}:{node.lineno}", sheet):
                checked += 1
    print(f"[..] {checked} stylesheets passed to setStyleSheet()")

    for name in STYLE_MODULES:
        module = importlib.import_module(name)
        for attr in dir(module):
            value = getattr(module, attr)
            entries = []
            if isinstance(value, str):
                entries = [(attr, value)]
            elif isinstance(value, dict):
                entries = [
                    (f"{attr}[{k!r}]", v) for k, v in value.items() if isinstance(v, str)
                ]
            for label, sheet in entries:
                if "{" in sheet and _check(f"{name}.{label}", sheet):
                    checked += 1
    print(f"[..] plus the stylesheet constants in {len(STYLE_MODULES)} style modules")

    if _failures:
        print(f"\n{len(_failures)} stylesheet(s) Qt could not parse:\n")
        for where, sheet in _failures:
            print(f"  {where}\n      {sheet}\n")
        raise AssertionError(
            f"{len(_failures)} malformed stylesheet(s) — Qt discards the whole "
            f"sheet, so the affected widgets render unstyled"
        )

    print(f"\n[PASS] all {checked} stylesheets parse")
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
