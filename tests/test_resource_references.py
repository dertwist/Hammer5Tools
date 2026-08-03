"""
Every ``:/...`` resource reference in the source must exist in src/resources.qrc.

A missing one is invisible at build time and only shows up as a runtime warning
on stderr — ``qt.svg: Cannot open file ':/icons/...', because: No such file or
directory`` — while the widget silently renders with no icon. That is exactly
how a batch of Material icons kept referencing their pre-rename filenames
(``delete_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg`` for ``delete_24dp.svg``)
long after the files were renamed.

Path spellings Qt treats as equivalent, and this check therefore normalises:
``:/path`` and ``://path``; and a ``<qresource>`` prefix with or without its
leading slash (``prefix="social"`` still answers to ``:/social/...``).
"""

import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QRC = ROOT / "src" / "resources.qrc"

# Extensions that get referenced as Qt resources.
_ASSET_RE = re.compile(r':(/{1,2}[A-Za-z0-9_./\-]+\.(?:svg|png|jpg|jpeg|ico|gif))')

# Referenced from a URL, not from the resource system.
_IGNORED = {"/i.imgur.com/Zvsv8t5.png"}


def declared_resources() -> set[str]:
    root = ET.parse(QRC).getroot()
    declared = set()
    for block in root.findall("qresource"):
        # rcc normalises a prefix to a leading slash, so prefix="social" and
        # prefix="/social" both answer to ":/social/...". "/" collapses to ""
        # so its entries join as "/name".
        prefix = "/" + (block.get("prefix") or "").strip("/")
        prefix = prefix.rstrip("/")
        for entry in block.findall("file"):
            name = (entry.get("alias") or entry.text or "").strip()
            declared.add(f"{prefix}/{name}")
    return declared


def referenced_resources() -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for path in (ROOT / "src").rglob("*"):
        if path.suffix not in (".py", ".ui") or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _ASSET_RE.findall(text):
            # Qt treats ":/x" and "://x" identically.
            key = "/" + match.lstrip("/")
            refs.setdefault(key, set()).add(str(path.relative_to(ROOT)))
    return refs


def main():
    declared = declared_resources()
    refs = referenced_resources()
    missing = {
        ref: files
        for ref, files in refs.items()
        if ref not in declared and ref not in _IGNORED
    }

    if missing:
        print(f"\n{len(missing)} broken resource reference(s):\n")
        for ref in sorted(missing):
            stem = Path(ref).stem.split("_")[0]
            near = sorted(d for d in declared if stem and stem in d)[:4]
            print(f"  {ref}")
            for f in sorted(missing[ref]):
                print(f"      used in: {f}")
            print(f"      similar declared: {near or '(none)'}")
        raise AssertionError(f"{len(missing)} resource reference(s) do not exist")

    print(f"[PASS] all {len(refs)} referenced resources exist in resources.qrc")
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
