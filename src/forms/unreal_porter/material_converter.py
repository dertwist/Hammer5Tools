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


def ue_material_to_vmat_path(ue_path: str, root: str = "materials", strip_prefix: bool = False) -> str:
    """/Game/FireWatchTower/Materials/Material_Instances/MI_Barrel(.MI_Barrel)
        -> materials/firewatchtower/mi_barrel.vmat (or barrel.vmat if strip_prefix=True)"""
    if "'" in ue_path:
        match = re.search(r"'(.*?)'", ue_path)
        if match:
            ue_path = match.group(1)
    ue_path = ue_path.strip()

    p = ue_path.split(".", 1)[0].replace("/Game/", "").replace("/game/", "").strip("/")
    p = strip_ue_asset_folders(p)
    if strip_prefix:
        from .vmdl_writer import strip_ue_prefix
        folder, _, leaf = p.rpartition("/")
        p = f"{folder}/{strip_ue_prefix(leaf)}" if folder else strip_ue_prefix(leaf)
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


# Channel layout of a packed mask, keyed by the token that names it. Maps an
# image channel -> vmat slot; channels left out are dropped, which is how SRM/
# SRMH's specular channel disappears (csgo_environment has no specular slot).
# Longer keys are probed first so "srmh" wins over "srm".
_PACKED_LAYOUTS = {
    "orm":  {"r": "ao",    "g": "rough", "b": "metal"},
    "ormh": {"r": "ao",    "g": "rough", "b": "metal", "a": "height"},
    "orh":  {"r": "ao",    "g": "rough", "b": "height"},
    "rma":  {"r": "rough", "g": "metal", "b": "ao"},
    "rmah": {"r": "rough", "g": "metal", "b": "ao",    "a": "height"},
    "mrao": {"r": "metal", "g": "rough", "b": "ao"},
    "arm":  {"r": "ao",    "g": "rough", "b": "metal"},
    "srm":  {                "g": "rough", "b": "metal"},
    "srmh": {                "g": "rough", "b": "metal", "a": "height"},
}

CHANNELS = ("r", "g", "b", "a")

# Slots a packed channel can legally feed — all single-channel greyscale maps.
CHANNEL_SLOTS = (
    "rough", "metal", "ao", "height", "opacity",
    "rough1", "metal1", "ao1", "height1",
    "rough2", "metal2", "ao2", "height2",
    "rough3", "metal3", "ao3", "height3",
    "rough4", "metal4", "ao4", "height4",
)


def packed_layout(param_name: str, tex_path: str = ""):
    """(token, {channel: slot}) if this parameter names a packed mask, else
    (None, None). The texture filename is considered too, since authors often
    name the param "Mask" but the file "Foo_SRM"."""
    toks = _tokens(param_name) | _tokens(os.path.basename(tex_path or ""))
    for key in sorted(_PACKED_LAYOUTS, key=len, reverse=True):
        if key in toks:
            return key, dict(_PACKED_LAYOUTS[key])
    return None, None


_LAYER2_TOKENS = {"top", "dirt", "moss", "layer2", "2", "l2", "secondary", "overlay"}
_LAYER3_TOKENS = {"layer3", "3", "l3", "tertiary"}
_LAYER4_TOKENS = {"layer4", "4", "l4"}

_COLOR_TOKENS = {"base", "basecolor", "diffuse", "albedo", "color", "diff", "alb", "d", "c"}
_NORMAL_TOKENS = {"normal", "nrm", "n", "norm"}
_ROUGH_TOKENS = {"rough", "roughness", "r"}
_METAL_TOKENS = {"metal", "metallic", "metalness", "m"}
_AO_TOKENS = {"ao", "occlusion"}
_HEIGHT_TOKENS = {"height", "displacement", "disp", "h"}
_ORM_TOKENS = set(_PACKED_LAYOUTS) | {"packed"}

# Slot -> matching token set. Order = priority (first match wins per param).
# Whole-token matching avoids false hits like "rma" inside "noRMAl".
_SLOT_TOKENS = [
    ("opacity",  {"opacity", "opac", "alpha"}),
    ("orm2",     {"orm2", "srm2", "srmh2", "packed2", "layer2_orm"}),
    ("orm3",     {"orm3", "srm3", "srmh3", "packed3", "layer3_orm"}),
    ("orm4",     {"orm4", "srm4", "srmh4", "packed4", "layer4_orm"}),
    ("orm",      _ORM_TOKENS),

    ("normal2",  {"normal2", "nrm2", "norm2"}),
    ("normal3",  {"normal3", "nrm3", "norm3"}),
    ("normal4",  {"normal4", "nrm4", "norm4"}),
    ("normal",   _NORMAL_TOKENS),

    ("rough2",   {"rough2", "roughness2"}),
    ("rough3",   {"rough3", "roughness3"}),
    ("rough4",   {"rough4", "roughness4"}),
    ("rough",    _ROUGH_TOKENS),

    ("metal2",   {"metal2", "metallic2", "metalness2"}),
    ("metal3",   {"metal3", "metallic3", "metalness3"}),
    ("metal4",   {"metal4", "metallic4", "metalness4"}),
    ("metal",    _METAL_TOKENS),

    ("ao2",      {"ao2", "occlusion2"}),
    ("ao3",      {"ao3", "occlusion3"}),
    ("ao4",      {"ao4", "occlusion4"}),
    ("ao",       _AO_TOKENS),

    ("height2",  {"height2", "displacement2", "disp2", "blendmask", "blendmask2"}),
    ("height3",  {"height3", "displacement3", "disp3", "blendmask3"}),
    ("height4",  {"height4", "displacement4", "disp4", "blendmask4"}),
    ("height",   _HEIGHT_TOKENS),

    ("color2",   {"basecolor2", "diffuse2", "albedo2", "color2"}),
    ("color3",   {"basecolor3", "diffuse3", "albedo3", "color3"}),
    ("color4",   {"basecolor4", "diffuse4", "albedo4", "color4"}),
    ("emissive", {"emissive", "emmisive", "emission", "emi"}),
    ("color",    _COLOR_TOKENS),
]
_COLOR_EXCLUDE = {"var", "variation", "mask", "tint"}


def _classify_textures(textures: dict, slot_overrides: dict = None) -> dict:
    """
    Map {ue_param_name: ue_tex_path} -> {slot: (param, path, channel)} choosing
    the best primary texture per slot. `channel` is None for a whole-texture
    binding, or one of "r"/"g"/"b"/"a" to take a single channel out of a packed
    mask. A layer index token ("Diffuse 1") is penalised so the base layer
    ("M_Diffuse") wins.

    slot_overrides: optional {param_name (case-insensitive): override} from the
    slot-mapping dialog; these always beat the heuristic. An override is either
      * None                        — exclude the parameter,
      * "rough"                     — bind the whole texture to that slot, or
      * {"rough": "g", "ao": "r"}   — route individual channels to slots.
    """
    if not textures or not isinstance(textures, dict):
        return {}

    overrides = {k.lower(): v for k, v in (slot_overrides or {}).items()}
    valid_slots = dict(_SLOT_TOKENS)
    out = {}
    used_params = set()

    # Apply explicit overrides first
    for param_name, tex_path in textures.items():
        key = param_name.lower()
        if key not in overrides:
            continue
        forced = overrides[key]
        used_params.add(param_name)
        if isinstance(forced, dict):
            for slot, channel in forced.items():
                if slot in CHANNEL_SLOTS and channel in CHANNELS:
                    out[slot] = (param_name, tex_path, channel)
        elif forced and (forced in valid_slots or any(forced == s for s, _ in _SLOT_TOKENS)):
            out[forced] = (param_name, tex_path, None)

    # Helper map for base slot vs layer slot token requirements
    slot_map_tokens = {
        "color": _COLOR_TOKENS, "normal": _NORMAL_TOKENS, "rough": _ROUGH_TOKENS,
        "metal": _METAL_TOKENS, "ao": _AO_TOKENS, "height": _HEIGHT_TOKENS, "orm": _ORM_TOKENS,
    }

    # Heuristic matching for remaining parameters
    for slot, tokens in _SLOT_TOKENS:
        if slot in out:
            continue
        candidates = []
        base_kind = re.sub(r"\d+$", "", slot)
        kind_tokens = slot_map_tokens.get(base_kind, tokens)
        layer_num = slot[-1] if slot[-1].isdigit() else ""

        for param_name, tex_path in textures.items():
            if param_name in used_params:
                continue
            p_toks = _tokens(param_name)
            if slot.startswith("color") and p_toks & _COLOR_EXCLUDE:
                continue

            matching = p_toks & tokens
            if not matching and base_kind:
                # Check for layer + kind combination (e.g. 'top' + 'basecolor' -> color2)
                has_kind = bool(p_toks & kind_tokens)
                if not has_kind and slot.startswith("orm"):
                    has_kind = bool(_tokens(os.path.basename(tex_path or "")) & _ORM_TOKENS)

                if has_kind:
                    if layer_num == "2" and (p_toks & _LAYER2_TOKENS):
                        matching = {"layer2"}
                    elif layer_num == "3" and (p_toks & _LAYER3_TOKENS):
                        matching = {"layer3"}
                    elif layer_num == "4" and (p_toks & _LAYER4_TOKENS):
                        matching = {"layer4"}

            if matching:
                score = len(matching) * 10 - (len(p_toks) - len(matching))
                if re.search(r"\b(layer|uv|v|mask|sub)\d*\b", param_name, re.I) and not layer_num:
                    score -= 5
                candidates.append((score, param_name, tex_path))
        if candidates:
            candidates.sort(key=lambda c: c[0], reverse=True)
            top_param, top_path = candidates[0][1], candidates[0][2]
            used_params.add(top_param)
            if slot.startswith("orm"):
                _tok, layout = packed_layout(top_param, top_path)
                suffix = slot[3:] if len(slot) > 3 else ""
                for channel, mapped in (layout or {}).items():
                    target_slot = f"{mapped}{suffix}"
                    out.setdefault(target_slot, (top_param, top_path, channel))
            else:
                out[slot] = (top_param, top_path, None)

    return out


# Master Materials expose many tints and scalars beside the base one — a dirt
# overlay colour, a metal tint, a fresnel rim, a detail roughness. These tokens
# mark a parameter as one of those secondary effects, which have no
# csgo_environment equivalent and must never be mistaken for the base value.
_SECONDARY_TOKENS = {
    "dirt", "metal", "metall", "metallic", "fresnel", "emissive", "emmisive",
    "spec", "specular", "rim", "subsurface", "sss", "detail", "snow", "moss",
    "wear", "edge", "overlay", "secondary", "layer2", "top",
}
# What names the *base* colour: a qualifier ("diffuse") and/or a noun ("color").
_TINT_QUALIFIERS = {"base", "basecolor", "diffuse", "albedo", "main", "model"}
_TINT_NOUNS = {"color", "colour", "tint"}


def _pick_tint(vectors: dict):
    """The base colour tint declared by the material or its master.

    Matches on whole tokens rather than substrings: the old substring list only
    knew "base color"/"diffuse tint", so a master declaring "diffuse color"
    (very common) silently produced an untinted white material.
    """
    best, best_score = None, 0
    for name, v in (vectors or {}).items():
        toks = _tokens(name)
        if toks & _SECONDARY_TOKENS:
            continue
        score = 0
        if toks & _TINT_QUALIFIERS:
            score += 2
        if toks & _TINT_NOUNS:
            score += 1
        if not score:
            continue
        # Prefer the least-qualified name when several remain.
        score = score * 10 - len(toks)
        if score > best_score:
            best, best_score = v, score
    if best is None:
        return None
    return (best.get("r", 1.0), best.get("g", 1.0), best.get("b", 1.0))


def _pick_scalar(scalars: dict, *keys, default=1.0):
    """A scalar by name, from the instance or inherited from its master.

    Exact matches win; otherwise the least-qualified name containing all of a
    key's tokens is used, so "Roughness" is picked over "Dirt Roughness" and a
    master's "Roughness Multiplier" is still found.
    """
    lowered = {name.lower(): v for name, v in (scalars or {}).items()}
    for key in keys:
        if key in lowered:
            return float(lowered[key])

    best, best_extra = None, None
    for name, v in (scalars or {}).items():
        toks = _tokens(name)
        for key in keys:
            key_toks = _tokens(key)
            if not key_toks or not key_toks <= toks:
                continue
            # Only tokens *beyond* the requested key can mark this as a
            # secondary effect — asking for "metallic" must not be blocked by
            # "metal" being a secondary token in its own right.
            extra_toks = toks - key_toks
            if extra_toks & _SECONDARY_TOKENS:
                continue
            if best_extra is None or len(extra_toks) < best_extra:
                best, best_extra = v, len(extra_toks)
            break
    return float(best) if best is not None else default


# vmat params the heuristic already fills. When the user maps a UE param to one
# of these, the user's value replaces the heuristic pick; mapping to anything
# else emits an extra scalar/vector on the vmat.
_HEURISTIC_SCALAR_TARGETS = {"g_flRoughnessScale", "g_flMetalnessScale"}
_HEURISTIC_VECTOR_TARGETS = {"g_vColorTint"}
# Mapping a UE switch to one of these forces that feature/flag on, regardless of
# its bool value (CS2 flags are presence-based, not value-based).
_FLAG_TARGETS = {"F_ALPHA_TEST", "F_RENDER_BACKFACES"}


def _apply_param_overrides(scalars, vectors, switches, param_overrides):
    """Resolve {ue_param_name: vmat_param_name} into typed vmat values.

    Returns (user_scalars, user_vectors, user_flags, claimed) where:
      * user_scalars  {vmat_param: float}     — scalars to emit/override
      * user_vectors  {vmat_param: (r,g,b)}   — vectors to emit/override
      * user_flags    [vmat_flag, ...]        — feature flags to force on
      * claimed       set(vmat_param)         — every target the user took,
        so the heuristic can be suppressed for just those and left intact
        for everything else (partial override, not all-or-nothing).

    First-write-wins keeps the outcome deterministic when two UE names map to
    the same target: the first one encountered (iteration order of the override
    dict) wins, mirroring the bridge's own parent-chain merge.
    """
    user_scalars, user_vectors, user_flags, claimed = {}, {}, [], set()
    for ue_name, target in (param_overrides or {}).items():
        if not target:
            continue
        if ue_name in (scalars or {}) and target not in user_scalars:
            user_scalars[target] = float(scalars[ue_name])
            claimed.add(target)
        elif ue_name in (vectors or {}) and target not in user_vectors:
            v = vectors[ue_name]
            user_vectors[target] = (float(v.get("r", 1.0)), float(v.get("g", 1.0)), float(v.get("b", 1.0)))
            claimed.add(target)
        elif ue_name in (switches or {}) and target in _FLAG_TARGETS and target not in user_flags:
            if bool(switches[ue_name]):
                user_flags.append(target)
                claimed.add(target)
    return user_scalars, user_vectors, user_flags, claimed


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
                     tex_index: dict = None,
                     param_overrides: dict = None,
                     strip_prefix: bool = False) -> MaterialResult:
    """
    Write a vmat (+ converted/split textures) from a dump-material result.
    Returns MaterialResult with the vmat path relative to the output root.
    Shader defaults to csgo_environment.vfx, or csgo_static_overlay.vfx if the
    material's UE domain is MD_DeferredDecal (see pick_shader).

    slot_overrides: optional {param_name: slot_name or None} forwarded to
    _classify_textures to override its heuristic pick (see slot_mapping.py).

    param_overrides: optional {ue_param_name: vmat_param_name} from the Params
    tab. A mapping wins over the heuristic auto-pick for tint/roughness/metalness
    (e.g. mapping a vector to "g_vColorTint" suppresses _pick_tint); any other
    target is emitted as an extra scalar/vector on the vmat. See _apply_param_overrides.
    """
    flags = mat_data.get("flags") or {}
    decal = is_decal(flags)
    shader = shader or pick_shader(flags)

    mi_path = mat_data.get("material", "")
    vmat_rel = ue_material_to_vmat_path(mi_path, strip_prefix=strip_prefix)
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
        """(source file, stem, channel) for a slot — channel is None when the
        whole texture binds, or "r"/"g"/"b"/"a" for one band of a packed mask."""
        pick = picks.get(slot)
        if not pick:
            return None, None, None
        src = find_bulk_texture(bulk_dir, pick[1], tex_index=tex_index)
        if not src:
            missing.append(slot)
            return None, None, None
        stem = os.path.splitext(os.path.basename(src))[0]
        if strip_prefix:
            from .vmdl_writer import strip_ue_prefix
            # Only the T_ prefix goes — the channel suffix (_ALB/_N/_ORM) is what
            # keeps this material's maps in separate files.
            stem = strip_ue_prefix(stem)
        return src, stem.lower(), pick[2]

    if decal:
        # csgo_static_overlay's default Hammer template only exposes TextureColor
        # (no separate normal/AO/metalness slot) — the decal's shape comes from
        # that texture's alpha channel, so UE's separate Opacity mask is
        # composited into it.
        src, stem, _ch = load("color")
        opacity_src, _stem, _ch = load("opacity")
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
        # Decals have a smaller param surface, but a user-mapped tint still wins.
        _us, user_vectors, _uf, claimed = _apply_param_overrides(
            mat_data.get("scalars"), mat_data.get("vectors"), mat_data.get("switches"), param_overrides)
        if "g_vColorTint" in claimed:
            color_tint = user_vectors.get("g_vColorTint")
        write_decal_vmat(vmat_abs, slots, color_tint=color_tint)
        return MaterialResult(vmat_rel, written, missing, is_decal=True)

    # color / normal — straight convert to TGA (handles base & multi-layer slots)
    color_normal_slots = (
        "color", "normal",
        "color1", "normal1",
        "color2", "normal2",
        "color3", "normal3",
        "color4", "normal4",
    )
    for slot in color_normal_slots:
        src, stem, _ch = load(slot)
        if src:
            slots[slot] = save(Image.open(src).convert("RGBA"), stem)
            written += 1

    # Greyscale slots. _classify_textures has already expanded any packed mask
    # into per-channel bindings, so a packed source and a dedicated one-off map
    # are handled the same way here.
    greyscale_slots = (
        "rough", "metal", "ao", "height",
        "rough1", "metal1", "ao1", "height1",
        "rough2", "metal2", "ao2", "height2",
        "rough3", "metal3", "ao3", "height3",
        "rough4", "metal4", "ao4", "height4",
    )
    for slot in greyscale_slots:
        src, stem, channel = load(slot)
        if not src:
            continue
        img = Image.open(src)
        if channel:
            if channel == "a" and "A" not in img.getbands():
                # Param says the mask carries height in alpha (…_SRMH) but the
                # exported file is 3-channel — convert("RGBA") would invent an
                # opaque alpha and write a solid-white height map.
                missing.append(slot)
                continue
            band = img.convert("RGBA").split()[CHANNELS.index(channel)]
            slots[slot] = save(band.convert("L"), f"{stem}_{slot}")
        else:
            slots[slot] = save(img.convert("L"), stem)
        written += 1

    color_tint = _pick_tint(mat_data.get("vectors"))
    rough_scale = _pick_scalar(mat_data.get("scalars"), "roughness", "tileable 1 roughness")
    metal_scale = _pick_scalar(mat_data.get("scalars"), "metallic", "metalness", default=0.0)

    # Param-mapping UI: a user mapping to a heuristic target wins over the
    # auto-pick; anything else is emitted as an extra scalar/vector.
    user_scalars, user_vectors, user_flags, claimed = _apply_param_overrides(
        mat_data.get("scalars"), mat_data.get("vectors"), mat_data.get("switches"), param_overrides)
    if "g_vColorTint" in claimed:
        v = user_vectors.pop("g_vColorTint")
        color_tint = v
    if "g_flRoughnessScale" in claimed:
        rough_scale = user_scalars.pop("g_flRoughnessScale")
    if "g_flMetalnessScale" in claimed:
        metal_scale = user_scalars.pop("g_flMetalnessScale")
    render_backfaces = "F_RENDER_BACKFACES" in user_flags
    if "F_ALPHA_TEST" in user_flags and slots.get("trans"):
        alpha_test_ref = 0.5
    else:
        alpha_test_ref = None

    # Anything left in user_scalars/user_vectors has no heuristic equivalent —
    # emit it verbatim so the user's explicit mappings always reach the vmat.
    write_vmat(vmat_abs, slots, shader=shader, color_tint=color_tint,
               roughness_scale=rough_scale, metalness_scale=metal_scale,
               extra_scalars=user_scalars or None, extra_vectors=user_vectors or None,
               alpha_test_ref=alpha_test_ref, render_backfaces=render_backfaces)
    return MaterialResult(vmat_rel, written, missing)
