"""
Material Instance -> Source 2 vmat.

Combines the two data sources:
  * parameters (which textures, tints, scalars) come from the CUE4Parse bridge
    (dump-material) — works on the uncooked project;
  * texture pixels come from the UE Bulk Export folder (T_*_B / _N / _ORM PNGs).

UE parameter names are author-defined, so a scoring heuristic maps them to the
fixed csgo_environment slots. Packed ORM/RMA masks are auto-detected and split.
Only Material *Instance* parameters convert — master-material graphs do not.
"""

import os
import re
from PIL import Image

from .vmat_writer import write_vmat, write_decal_vmat

_TEX_EXTS = (".png", ".tga", ".tif", ".tiff", ".exr", ".jpg")

# UE organizes assets into type folders (Materials/Material_Instances, Textures,
# the synthetic Game root, …) that have no equivalent in Source 2 — a Source 2
# addon keeps a material and its textures together in one flat folder. Any of
# these folder names are dropped wherever they appear in a UE path, not just at
# the front, so "FireWatchTower/Materials/Material_Instances/MI_Barrel" becomes
# "FireWatchTower/MI_Barrel" instead of mirroring UE's asset-type subfolders.
_UE_ASSET_FOLDER_NOISE = {"game", "content", "materials", "material_instances", "textures"}


def strip_ue_asset_folders(rel_path: str) -> str:
    parts = [p for p in rel_path.split("/") if p and p.lower() not in _UE_ASSET_FOLDER_NOISE]
    return "/".join(parts)


def ue_material_to_vmat_path(ue_path: str, root: str = "materials") -> str:
    """/Game/FireWatchTower/Materials/Material_Instances/MI_Barrel(.MI_Barrel)
        -> materials/firewatchtower/mi_barrel.vmat"""
    if "'" in ue_path:
        match = re.search(r"'(.*?)'", ue_path)
        if match:
            ue_path = match.group(1)
    ue_path = ue_path.strip()

    p = ue_path.split(".", 1)[0].replace("/Game/", "").replace("/game/", "").strip("/")
    p = strip_ue_asset_folders(p)
    return f"{root}/{p}.vmat".lower()


_texture_index_cache = {}


def get_texture_index(bulk_dir: str) -> dict:
    """Build or retrieve an in-memory stem->filepath index for bulk_dir to eliminate O(N) disk walks."""
    if not bulk_dir or not os.path.isdir(bulk_dir):
        return {}
    bulk_dir_norm = os.path.abspath(bulk_dir)
    if bulk_dir_norm in _texture_index_cache:
        return _texture_index_cache[bulk_dir_norm]

    index = {}
    for root, _dirs, files in os.walk(bulk_dir_norm):
        for fn in files:
            name, ext = os.path.splitext(fn)
            if ext.lower() in _TEX_EXTS:
                stem_lower = name.lower()
                if stem_lower not in index:
                    index[stem_lower] = os.path.join(root, fn)

    _texture_index_cache[bulk_dir_norm] = index
    return index


def find_bulk_texture(bulk_dir: str, ue_tex_path: str, tex_index: dict = None):
    """Resolve a UE texture reference to its bulk-exported image by stem using O(1) lookup."""
    if not ue_tex_path:
        return None
    if "'" in ue_tex_path:
        match = re.search(r"'(.*?)'", ue_tex_path)
        if match:
            ue_tex_path = match.group(1)
    ue_tex_path = ue_tex_path.strip()

    stem = ue_tex_path.split(".", 1)[0].rstrip("/").rsplit("/", 1)[-1].lower()
    if tex_index is not None:
        return tex_index.get(stem)

    if bulk_dir:
        idx = get_texture_index(bulk_dir)
        return idx.get(stem)

    return None


# --- parameter-name -> slot classification -------------------------------

def _tokens(name: str) -> set:
    """Split a parameter name into lowercase tokens (handles spaces, '_', camelCase)."""
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return {t for t in re.split(r"[^A-Za-z0-9]+", s.lower()) if t}


# Slot -> matching token set. Order = priority (first match wins per param).
# Whole-token matching avoids false hits like "rma" inside "noRMAl".
_SLOT_TOKENS = [
    ("opacity",  {"opacity", "opac", "alpha"}),
    ("orm",      {"orm", "rma", "rmah", "mrao", "arm", "packed", "orh"}),
    ("normal",   {"normal", "nrm", "n", "norm"}),
    ("rough",    {"rough", "roughness", "r"}),
    ("metal",    {"metal", "metallic", "metalness", "m"}),
    ("ao",       {"ao", "occlusion"}),
    ("height",   {"height", "displacement", "disp", "h"}),
    ("emissive", {"emissive", "emmisive", "emission", "emi"}),
    ("color",    {"base", "basecolor", "diffuse", "albedo", "color", "diff", "alb", "d", "c"}),
]
_COLOR_EXCLUDE = {"var", "variation", "mask", "tint"}


def _classify_textures(textures: dict, slot_overrides: dict = None) -> dict:
    """
    Map {ue_param_name: ue_tex_path} -> {slot: (param, path)} choosing the best
    primary texture per slot. A layer index token ("Diffuse 1") is penalised so
    the base layer ("M_Diffuse") wins.

    slot_overrides: optional {param_name (case-insensitive): slot_name or None}
    — explicit user choices from the slot-mapping dialog. These always win
    over heuristic scoring. None excludes the parameter.
    """
    if not textures or not isinstance(textures, dict):
        return {}

    overrides = {k.lower(): v for k, v in (slot_overrides or {}).items()}
    out = {}
    used_params = set()

    # Apply explicit overrides first
    for param_name, tex_path in textures.items():
        key = param_name.lower()
        if key in overrides:
            forced_slot = overrides[key]
            used_params.add(param_name)
            if forced_slot and forced_slot in dict(_SLOT_TOKENS):
                out[forced_slot] = (param_name, tex_path)

    # Heuristic matching for remaining parameters
    for slot, tokens in _SLOT_TOKENS:
        if slot in out:
            continue
        candidates = []
        for param_name, tex_path in textures.items():
            if param_name in used_params:
                continue
            p_toks = _tokens(param_name)
            if slot == "color" and p_toks & _COLOR_EXCLUDE:
                continue
            matching = p_toks & tokens
            if matching:
                score = len(matching) * 10
                if re.search(r"\b(layer|uv|v|mask|sub)\d*\b", param_name, re.I):
                    score -= 5
                candidates.append((score, param_name, tex_path))
        if candidates:
            candidates.sort(key=lambda c: c[0], reverse=True)
            top_param, top_path = candidates[0][1], candidates[0][2]
            out[slot] = (top_param, top_path)
            used_params.add(top_param)

    return out


def _pick_tint(vectors: dict):
    for name, v in (vectors or {}).items():
        n = name.lower()
        if any(k in n for k in ("base color", "basecolor", "diffuse tint", "base tint")):
            return (v.get("r", 1.0), v.get("g", 1.0), v.get("b", 1.0))
    return None


def _pick_scalar(scalars: dict, *keys, default=1.0):
    for name, v in (scalars or {}).items():
        if name.lower() in keys:
            return float(v)
    return default


# --- shader selection from material domain/blend --------------------------

def is_decal(flags: dict) -> bool:
    """True if the material's (or its base Material's) domain marks it as a
    UE deferred decal — the signal that determines the Source 2 shader."""
    return (flags or {}).get("domain") == "MD_DeferredDecal"


def pick_shader(flags: dict) -> str:
    """
    Choose the Source 2 shader for a material from its resolved UE render
    flags (domain/blend/two-sided — see bridge dump-material "flags").
    Verified against Valve's own shipped content by decompiling a real decal
    vmat_c (materials/cs_italy/decals/italy_trim_decal_1.vmat_c): deferred-decal
    UE materials map to csgo_static_overlay.vfx (F_BLEND_MODE=1, translucent).
    Everything else stays on csgo_environment.vfx (the default PBR shader).
    """
    return "csgo_static_overlay.vfx" if is_decal(flags) else "csgo_environment.vfx"


class MaterialResult:
    def __init__(self, vmat_path: str, textures_written: int, missing: list, is_decal: bool = False):
        self.vmat_path = vmat_path
        self.textures_written = textures_written
        self.missing = missing
        self.is_decal = is_decal


def convert_material(mat_data: dict, bulk_dir: str, output_dir: str,
                     shader: str = None, slot_overrides: dict = None,
                     tex_index: dict = None) -> MaterialResult:
    """
    Write a vmat (+ converted/split textures) from a dump-material result.
    Returns MaterialResult with the vmat path relative to the output root.
    Shader defaults to csgo_environment.vfx, or csgo_static_overlay.vfx if the
    material's UE domain is MD_DeferredDecal (see pick_shader).

    slot_overrides: optional {param_name: slot_name or None} forwarded to
    _classify_textures to override its heuristic pick (see slot_mapping.py).
    """
    flags = mat_data.get("flags") or {}
    decal = is_decal(flags)
    shader = shader or pick_shader(flags)

    mi_path = mat_data.get("material", "")
    vmat_rel = ue_material_to_vmat_path(mi_path)
    vmat_abs = os.path.join(output_dir, vmat_rel)
    folder_rel = os.path.dirname(vmat_rel).replace("\\", "/")   # "materials/…"

    def save(img, name) -> str:
        rel = f"{folder_rel}/{name}.tga"
        dst = os.path.join(output_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst):
            img.save(dst)
        return rel

    picks = _classify_textures(mat_data.get("textures"), slot_overrides)
    slots = {}
    written = 0
    missing = []

    def load(slot):
        param_path = picks.get(slot)
        if not param_path:
            return None, None
        src = find_bulk_texture(bulk_dir, param_path[1], tex_index=tex_index)
        if not src:
            missing.append(slot)
            return None, None
        return src, os.path.splitext(os.path.basename(src))[0].lower()

    if decal:
        # csgo_static_overlay's default Hammer template only exposes TextureColor
        # (no separate normal/AO/metalness slot) — the decal's shape comes from
        # that texture's alpha channel, so UE's separate Opacity mask is
        # composited into it.
        src, stem = load("color")
        opacity_src, _ = load("opacity")
        if src:
            color_img = Image.open(src).convert("RGBA")
            if opacity_src:
                mask = Image.open(opacity_src).convert("L")
                if mask.size != color_img.size:
                    mask = mask.resize(color_img.size)
                r, g, b, _a = color_img.split()
                color_img = Image.merge("RGBA", (r, g, b, mask))
                written += 1
            slots["color"] = save(color_img, stem)
            written += 1

        color_tint = _pick_tint(mat_data.get("vectors"))
        write_decal_vmat(vmat_abs, slots, color_tint=color_tint)
        return MaterialResult(vmat_rel, written, missing, is_decal=True)

    # color / normal — straight convert to TGA
    for slot in ("color", "normal"):
        src, stem = load(slot)
        if src:
            slots[slot] = save(Image.open(src).convert("RGBA"), stem)
            written += 1

    # ORM packed -> split (UE convention: R=Occlusion, G=Roughness, B=Metallic)
    src, stem = load("orm")
    if src:
        param_name = picks["orm"][0].lower()
        is_orh_texture = "orh" in param_name or "orh" in stem
        r, g, b, _a = Image.open(src).convert("RGBA").split()
        slots["ao"] = save(r.convert("L"), f"{stem}_ao")
        slots["rough"] = save(g.convert("L"), f"{stem}_rough")
        if is_orh_texture:
            slots["height"] = save(b.convert("L"), f"{stem}_height")
            written += 3
        else:
            slots["metal"] = save(b.convert("L"), f"{stem}_metal")
            written += 3
    else:
        # unpacked rough/metal/ao if the material provides them separately
        for slot in ("rough", "metal", "ao", "height"):
            s, st = load(slot)
            if s:
                slots[slot] = save(Image.open(s).convert("L"), st)
                written += 1

    color_tint = _pick_tint(mat_data.get("vectors"))
    rough_scale = _pick_scalar(mat_data.get("scalars"), "roughness", "tileable 1 roughness")
    metal_scale = _pick_scalar(mat_data.get("scalars"), "metallic", "metalness", default=0.0)

    write_vmat(vmat_abs, slots, shader=shader, color_tint=color_tint,
               roughness_scale=rough_scale, metalness_scale=metal_scale)
    return MaterialResult(vmat_rel, written, missing)
