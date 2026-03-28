import os
import re

try:
    from lxml import etree
except Exception:
    etree = None

SVG_NS = "http://www.w3.org/2000/svg"
OUT_W = 32
OUT_H = 32

# Structural elements must NEVER have a matrix transform added
STRUCTURAL_TAGS = {"defs", "style", "title", "desc", "metadata", "script"}

# Remove these to clean up the file
INKSCAPE_ATTRS = (
    "sodipodi:docname", "inkscape:version", "inkscape:export-filename",
    "inkscape:export-xdpi", "inkscape:export-ydpi"
)


def _strip_ns(tag):
    return tag.split("}")[-1].lower() if "}" in tag else tag.lower()


def _parse_transform(t: str):
    if not t:
        return [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    t = t.strip()
    m = re.match(r"matrix\(([^)]+)\)", t)
    if m:
        vals = [float(x) for x in re.split(r"[,\s]+", m.group(1).strip()) if x]
        return vals if len(vals) == 6 else [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    m = re.match(r"translate\(([^)]+)\)", t)
    if m:
        v = [float(x) for x in re.split(r"[,\s]+", m.group(1).strip()) if x]
        return [1.0, 0.0, 0.0, 1.0, v[0], v[1] if len(v) > 1 else 0.0]
    m = re.match(r"scale\(([^)]+)\)", t)
    if m:
        v = [float(x) for x in re.split(r"[,\s]+", m.group(1).strip()) if x]
        sx = v[0]
        sy = v[1] if len(v) > 1 else sx
        return [sx, 0.0, 0.0, sy, 0.0, 0.0]
    return [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]


def _compose(sx, sy, tx, ty, m):
    a, b, c, d, e, f = m
    return [sx * a, sy * b, sx * c, sy * d, sx * e + tx, sy * f + ty]


def _matrix_to_str(m):
    c = [0.0 if abs(x) < 1e-9 else x for x in m]
    return f"matrix({c[0]:.6g},{c[1]:.6g},{c[2]:.6g},{c[3]:.6g},{c[4]:.6g},{c[5]:.6g})"


def rescale_svg(svg_path: str, out_path: str):
    if etree is None:
        raise ImportError("lxml is required for SVG rescaling. Install it with: pip install lxml")

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(svg_path, parser)
    root = tree.getroot()
    svg_elem = root if root.tag.endswith("svg") else root.find(f"{{{SVG_NS}}}svg")

    vb = svg_elem.get("viewBox")
    width = None
    if svg_elem.get("width") and "%" not in svg_elem.get("width"):
        width = float(svg_elem.get("width").replace("px", ""))

    vx, vy, vw, vh = 0.0, 0.0, width or OUT_W, width or OUT_H
    if vb:
        parts = vb.replace(",", " ").split()
        if len(parts) == 4:
            vx, vy, vw, vh = [float(p) for p in parts]

    # Clean hidden elements
    for el in reversed(list(svg_elem.iter())):
        style = (el.get("style") or "").replace(" ", "")
        if "display:none" in style or el.get("display") == "none":
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    for attr in INKSCAPE_ATTRS:
        svg_elem.attrib.pop(attr, None)

    sx, sy = OUT_W / vw, OUT_H / vh
    tx, ty = -vx * sx, -vy * sy

    for child in list(svg_elem):
        tag = _strip_ns(child.tag)

        if tag in STRUCTURAL_TAGS:
            child.attrib.pop("transform", None)
            continue

        existing = _parse_transform(child.get("transform") or "")
        composed = _compose(sx, sy, tx, ty, existing)

        if all(abs(composed[i] - r) < 1e-9 for i, r in enumerate([1, 0, 0, 1, 0, 0])):
            child.attrib.pop("transform", None)
        else:
            child.set("transform", _matrix_to_str(composed))

    svg_elem.set("width", "100%")
    svg_elem.set("height", "100%")
    svg_elem.set("viewBox", f"0 0 {OUT_W} {OUT_H}")
    svg_elem.set("version", "1.1")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    tree.write(out_path, xml_declaration=True, encoding="UTF-8", pretty_print=True)
