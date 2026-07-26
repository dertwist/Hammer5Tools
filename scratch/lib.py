"""Shared helpers for the de_firewatch reorg passes."""
import os, re, struct, hashlib, collections

ROOT = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_firewatch"

# Trailing group captures the \r of a CRLF file: these vmats are a mix of both
# line endings, and anchoring on [ \t]*$ silently matches nothing on the CRLF half.
TEX_LINE = re.compile(r'^([ \t]*)(Texture\w+)([ \t]+)"([^"\r\n]*)"([ \t\r]*)$', re.M)


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/").lower()


def abspath(r):
    return os.path.join(ROOT, r.replace("/", os.sep))


def walk_ext(sub, *exts):
    out = []
    for dp, _, fns in os.walk(os.path.join(ROOT, sub)):
        for fn in fns:
            if fn.lower().endswith(exts):
                out.append(os.path.join(dp, fn))
    return sorted(out)


def scannable():
    """Every text file that can hold an asset path reference."""
    out = []
    for sub in ("materials", "models", "smartprops", "maps", "particles", "particels", "postprocess", "scripts", "lighting"):
        d = os.path.join(ROOT, sub)
        if not os.path.isdir(d):
            continue
        for dp, _, fns in os.walk(d):
            for fn in fns:
                if fn.lower().endswith((".vmat", ".vmdl", ".vsmart", ".vpcf", ".vpost", ".vphys", ".vanim", ".vseq", ".kv3", ".txt")):
                    out.append(os.path.join(dp, fn))
    return sorted(out)


def tga_stats(path):
    """(kind, w, h, per-channel min/max) for uncompressed TGA type 2/3; None otherwise."""
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < 18:
        return None
    idlen, imgtype, bpp = data[0], data[2], data[16]
    if imgtype not in (2, 3):
        return None
    w, h = struct.unpack("<HH", data[12:16])
    n = bpp // 8
    off = 18 + idlen
    px = data[off:off + w * h * n]
    if len(px) < w * h * n:
        return None
    if imgtype == 3:
        return dict(kind="gray", w=w, h=h, bpp=bpp, ch=[(min(px), max(px))])
    ch = [(min(px[i::n]), max(px[i::n])) for i in range(n)]   # B, G, R, [A]
    return dict(kind="rgba" if n == 4 else "rgb", w=w, h=h, bpp=bpp, ch=ch)


def flat_value(st):
    """Constant fill value as (b,g,r[,a]) if every channel is constant, else None."""
    if st is None:
        return None
    if all(lo == hi for lo, hi in st["ch"]):
        return tuple(lo for lo, _ in st["ch"])
    return None


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def read_text(p):
    # newline="" keeps CRLF intact so rewrites don't churn every line
    with open(p, encoding="utf-8", errors="ignore", newline="") as fh:
        return fh.read()


def write_text(p, s):
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)


def texture_refs(vmat_path):
    """[(slot, value)] for every Texture* line in a vmat, values as-written."""
    return [(m.group(2), m.group(4)) for m in TEX_LINE.finditer(read_text(vmat_path))]


def rewrite_texture_lines(text, fn):
    """fn(slot, value) -> new value or None to leave alone. Returns (text, n_changed)."""
    n = 0

    def sub(m):
        nonlocal n
        indent, slot, gap, val, tail = m.groups()
        new = fn(slot, val)
        if new is None or new == val:
            return m.group(0)
        n += 1
        return f'{indent}{slot}{gap}"{new}"{tail}'

    return TEX_LINE.sub(sub, text), n


def assert_no_refs(doomed, where="materials"):
    """Abort if any vmat still points at a file we're about to delete.

    The dedup pass deleted 277 textures whose references had silently failed to
    rewrite (CRLF vs LF in the line regex). Nothing gets removed now until this
    passes.
    """
    doomed = set(doomed)
    live = []
    for vm in walk_ext(where, ".vmat"):
        for slot, val in texture_refs(vm):
            v = val.lower().replace("\\", "/")
            if v in doomed:
                live.append((rel(vm), slot, v))
    if live:
        for r in live[:20]:
            print("   STILL REFERENCED:", r)
        raise SystemExit(f"ABORT: {len(live)} live references to {len({x[2] for x in live})} "
                         f"files marked for deletion - nothing was deleted")


SLOT_CANON = {
    "TextureColor": "color", "TextureNormal": "normal", "TextureRoughness": "rough",
    "TextureMetalness": "metal", "TextureAmbientOcclusion": "ao", "TextureHeight": "height",
    "TextureTranslucency": "trans", "TextureTintMask": "mask",
}


def slot_kind(slot):
    return SLOT_CANON.get(re.sub(r"\d+$", "", slot))


SUFFIX_CANON = {
    "color": "color", "b": "color", "d": "color", "bc": "color", "basecolor": "color",
    "normal": "normal", "n": "normal",
    "rough": "rough", "roughness": "rough",
    "metal": "metal", "metalness": "metal",
    "ao": "ao", "o": "ao",
    "height": "height", "trans": "trans", "alpha": "trans",
}
SUFFIX_RE = re.compile(r"^(?P<stem>.+?)_(?P<suf>" + "|".join(sorted(SUFFIX_CANON, key=len, reverse=True)) + r")$")


_REMAP = re.compile(r'to\s*=\s*"([^"]+)"')
_BIN_VMAT = re.compile(rb"materials/[A-Za-z0-9_/\.\-]+\.vmat", re.I)
_VMAT_REF = re.compile(r'"(materials/[A-Za-z0-9_/\.\-]+\.vmat)"', re.I)
_BIN_DIRS = ("maps", "smartprops", "particles", "particels", "lighting", "postprocess", "panorama", "scripts")


def live_vmats():
    """Materials reachable from a vmdl remap, a binary vmap/vsmart, or another vmat."""
    vmats = {rel(p) for p in walk_ext("materials", ".vmat")}
    roots = set()
    for vm in walk_ext("models", ".vmdl"):
        roots |= {m.lower() for m in _REMAP.findall(read_text(vm))}
    for sub in _BIN_DIRS:
        d = os.path.join(ROOT, sub)
        if not os.path.isdir(d):
            continue
        for dp, _, fns in os.walk(d):
            for fn in fns:
                try:
                    data = open(os.path.join(dp, fn), "rb").read()
                except OSError:
                    continue
                roots |= {m.decode("ascii", "ignore").lower() for m in _BIN_VMAT.findall(data)}

    live, queue = set(), [r for r in roots if r in vmats]
    while queue:                                       # blend shaders chain vmat -> vmat
        v = queue.pop()
        if v in live:
            continue
        live.add(v)
        queue += [r.lower() for r in _VMAT_REF.findall(read_text(abspath(v)))
                  if r.lower() in vmats and r.lower() not in live]
    return live, vmats


def split_name(basename):
    """'t_bush_orm_ao.tga' -> ('bush', 'ao'); returns (stem, canon_suffix|None)."""
    n = basename.lower()
    if n.endswith(".tga"):
        n = n[:-4]
    m = SUFFIX_RE.match(n)
    if not m:
        return re.sub(r"^(t_|mi_|m_)", "", n), None
    stem, suf = m.group("stem"), SUFFIX_CANON[m.group("suf")]
    stem = re.sub(r"^(t_|mi_|m_)", "", stem)
    stem = re.sub(r"_orm$|_rma$|_orh$", "", stem)
    stem = stem.rstrip("_")
    return stem, suf
