"""Brighten the dark theme across the entire codebase.

Applies a deterministic old->new color mapping (calibrated against a
Photoshop-brightened reference screenshot: new = old + 0.08 * (255 - old),
with the two dominant colors snapped to measured pixel values) to every
hex literal and rgb()/rgba()/QColor() triplet in the GUI Python and UI files.

Only exact matches of CHROME colors are replaced; semantic colors
(syntax highlighting, type badges, meters, gizmo axes, icon fills) are
left untouched. resources_rc.py is skipped entirely (compiled SVG icons).

Usage:
    python dev/scripts/brighten_colors.py --scan      # inventory only
    python dev/scripts/brighten_colors.py --dry-run   # show planned replacements
    python dev/scripts/brighten_colors.py             # rewrite files in place
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "Hammer5ToolsGUI" / "hammer5tools_gui"

# Files whose colors are semantic (meaning-carrying) and must not shift,
# plus files that only contain colors the exact-match table never targets.
EXCLUDED_FILES = {
    "resources_rc.py",          # compiled .qrc SVG icon fills
    "property_icons.py",        # property type icon pastels
    "gizmo.py",                 # OpenGL axis colors (floats, not hex)
    "highlighter.py",           # assetgroup filter syntax highlighting
    "set_variable.py",          # property type indicator text colors
}

def _lift(r, g, b):
    """Blend a color ~8% toward white, matching the reference screenshot."""
    return tuple(round(c + 0.08 * (255 - c)) for c in (r, g, b))

def _hexes(pairs):
    return {"#%02x%02x%02x" % rgb: "#%02x%02x%02x" % new for rgb, new in pairs}

def _make_map(spec):
    """spec: {old_hex: new_hex}. Returns lookup keyed by (r, g, b)."""
    out = {}
    for old, new in spec.items():
        key = (int(old[1:3], 16), int(old[3:5], 16), int(old[5:7], 16))
        val = (int(new[1:3], 16), int(new[3:5], 16), int(new[5:7], 16))
        out[key] = val
    return out

# ---------------------------------------------------------------------------
# Color mapping: old -> new, generated as new = old + 0.08 * (255 - old)
# per channel (calibrated against the reference screenshot), except two
# anchors measured directly from its pixel histogram:
#   #151515 -> #272727 (dominant background), #414956 -> #515965 (selection).
# Only chrome (UI surface) colors are listed; semantic colors are absent on
# purpose so exact-match replacement can never touch them.
# ---------------------------------------------------------------------------
CHROME_HEX = [
    # core design tokens
    "#151515", "#161616", "#1a1a1a", "#1c1c1c", "#1d1d1f", "#121212",
    "#18181a", "#1e1e1e", "#1f1f1f", "#212121", "#222222", "#232323",
    "#242424", "#242426", "#252525", "#252526", "#262626", "#26262a",
    "#26262b", "#272729", "#27272a", "#292929", "#2a2929", "#2a2a2a",
    "#2a2a2d", "#2a2e38", "#2c2c2c", "#2d2d2d", "#2d2d30", "#2d333b",
    "#2e2e2e", "#2e2f30", "#2e2e32", "#2f2f2f", "#323232", "#333333",
    "#333336", "#33363d", "#333a48", "#353535", "#363639", "#3a3a3a",
    "#3c3c3c", "#3d3d3d", "#3d3d42", "#3e3e3e", "#3e4451", "#3e4b5e",
    "#404040", "#414956", "#434343", "#444444", "#4a4a4a", "#4a5a6a",
    "#4f5259", "#505050", "#555555", "#606060", "#606c77", "#61666e",
    "#666666", "#6b6b6b", "#6c6c6c", "#6d6d6d", "#71717a", "#7a7a7a",
    "#7f7f7f", "#808080", "#888888", "#8a8a8a", "#8e8e93", "#909090",
    "#999999", "#9a9f91", "#9aa0aa", "#9d9d9d", "#a0a0a0", "#a3a3a3",
    "#a7a9a9", "#aaaaaa", "#ababab", "#acacac", "#b0b0b0", "#b8b8b8",
    "#bababa", "#bbbbbb", "#c3c3c3", "#c8c8c8", "#cbcbcb", "#cccccc",
    "#d0d0d0", "#e0e0e0", "#e3e3e3",
    # bluish panels / about-dialog sub-palette / viewport frame
    "#1e222a", "#282c34", "#2c3e50", "#4e5563", "#abb2bf",
    # accent-ish chrome
    "#accc8d", "#4caf50", "#23272d", "#008cba", "#3a78c4", "#3d88bd",
    "#515966",
]

CHROME_TRIPLETS = [
    (28, 28, 28), (29, 29, 31), (30, 30, 30), (40, 40, 40), (54, 54, 57),
    (64, 64, 64), (65, 73, 86), (68, 68, 68), (100, 100, 100),
    (109, 109, 109), (125, 125, 125), (157, 157, 157), (170, 170, 170),
    (188, 188, 188), (227, 227, 227),
]

MEASURED_ANCHORS = {"#151515": "#272727", "#414956": "#515965"}


def _build_spec():
    spec = {}
    for old in CHROME_HEX:
        r, g, b = (int(old[i:i + 2], 16) for i in (1, 3, 5))
        nr, ng, nb = _lift(r, g, b)
        spec[old] = "#%02x%02x%02x" % (nr, ng, nb)
    spec.update(MEASURED_ANCHORS)
    return spec


HEX_SPEC = _build_spec()

RGB_MAP = _make_map(HEX_SPEC)
RGB_MAP.update({t: _lift(*t) for t in CHROME_TRIPLETS})

HEX_RE = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{8}|[0-9a-fA-F]{3})(?![0-9a-fA-F])")
TRIPLET_RE = re.compile(
    r"(rgba?\s*\(\s*|QColor\s*\(\s*)(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})"
)


def target_files():
    for path in sorted(SRC.rglob("*")):
        if not path.suffix in (".py", ".ui"):
            continue
        if path.name in EXCLUDED_FILES:
            continue
        yield path


def transform(text, stats, relpath):
    def hex_sub(m):
        h = m.group(1)
        if len(h) == 3:
            key = "#" + "".join(c * 2 for c in h.lower())
            if key in HEX_SPEC:
                new = HEX_SPEC[key]
                stats[(key, new)] += 1
                return "#" + "".join(c for c in new[1::2])  # keep #RGB shorthand
            return m.group(0)
        if len(h) == 8:  # #AARRGGBB: Qt reads as ARGB; transform RGB part only
            key = "#" + h[2:8].lower()
            if key in HEX_SPEC:
                stats[(key, HEX_SPEC[key])] += 1
                return "#" + h[:2] + HEX_SPEC[key][1:]
            return m.group(0)
        key = ("#" + h).lower()
        if key in HEX_SPEC:
            stats[(key, HEX_SPEC[key])] += 1
            return HEX_SPEC[key]
        return m.group(0)

    def triplet_sub(m):
        prefix = m.group(1)
        key = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
        if key in RGB_MAP:
            new = RGB_MAP[key]
            stats[(key, new)] += 1
            return "%s%d, %d, %d" % (prefix, *new)
        return m.group(0)

    text = HEX_RE.sub(hex_sub, text)
    text = TRIPLET_RE.sub(triplet_sub, text)
    return text


def scan():
    hex_counts = defaultdict(int)
    tri_counts = defaultdict(int)
    for path in target_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in HEX_RE.finditer(text):
            h = m.group(1).lower()
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            hex_counts[h if len(h) == 6 else h[:6] + ("+a" if len(h) == 8 else "")] += 1
        for m in TRIPLET_RE.finditer(text):
            tri_counts[tuple(int(g) for g in m.groups()[1:])] += 1

    def sat(h):
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return max(r, g, b) - min(r, g, b)

    print("=== distinct hex: %d ===" % len(hex_counts))
    for h in sorted(hex_counts, key=lambda k: -hex_counts[k]):
        key = "#" + h[:6]
        tag = "MAP" if key in HEX_SPEC else "   "
        print("%s #%s  n=%-4d sat=%-3d %s" % (tag, h, hex_counts[h], sat(h[:6]),
                                              "->" + HEX_SPEC[key] if key in HEX_SPEC else ""))
    print()
    print("=== distinct triplets: %d ===" % len(tri_counts))
    for t in sorted(tri_counts, key=lambda k: -tri_counts[k]):
        tag = "MAP" if t in RGB_MAP else "   "
        new = RGB_MAP.get(t, ("", "", ""))
        print("%s (%d,%d,%d)  n=%-4d %s" % (tag, *t, tri_counts[t],
              "-> (%d, %d, %d)" % new if t in RGB_MAP else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true", help="inventory colors only")
    ap.add_argument("--dry-run", action="store_true", help="report replacements without writing")
    args = ap.parse_args()

    if args.scan:
        scan()
        return

    stats = defaultdict(int)
    files_changed = 0
    for path in target_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        new_text = transform(text, stats, path)
        if new_text != text:
            files_changed += 1
            print("rewrite:", path.relative_to(REPO))
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8", newline="")

    print()
    print("files changed: %d" % files_changed)
    total = 0
    for (old, new), n in sorted(stats.items(), key=lambda kv: -kv[1]):
        total += n
        print("  %s -> %s   x%d" % (old, new, n))
    print("total replacements: %d" % total)


if __name__ == "__main__":
    sys.exit(main())
