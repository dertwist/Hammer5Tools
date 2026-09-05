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

from .vmat_writer import write_vmat
from .texture_utils import DEFAULT_TEXTURE_SIZE_LIMIT, limit_texture_size

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


def ue_material_to_vmat_path(ue_path: str, root: str = "materials", strip_prefix: bool = True) -> str:
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


def get_texture_index(bulk_dir: str, force_rescan: bool = False) -> dict:
    """Build or retrieve an in-memory stem->filepath index for bulk_dir to eliminate O(N) disk walks."""
    if not bulk_dir or not os.path.isdir(bulk_dir):
        return {}
    bulk_dir_norm = os.path.normpath(bulk_dir)
    if not force_rescan and bulk_dir_norm in _texture_index_cache:
        cached = _texture_index_cache[bulk_dir_norm]
        if cached:
            return cached

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


def clear_texture_index_cache():
    """Clear in-memory texture index cache (e.g. after fresh asset export)."""
    _texture_index_cache.clear()


def find_bulk_texture(bulk_dir: str, ue_tex_path: str, tex_index: dict = None):
    """Resolve a UE texture reference to its bulk-exported image by stem using O(1) lookup."""
    if not ue_tex_path:
        return None
    if "'" in ue_tex_path:
        match = re.search(r"'(.*?)'", ue_tex_path)
        if match:
            ue_tex_path = match.group(1)
    filename = os.path.basename(ue_tex_path.replace("\\", "/"))
    stem = os.path.splitext(filename)[0].split(".", 1)[0].lower()
    idx = tex_index
    if idx is None and bulk_dir:
        idx = get_texture_index(bulk_dir)

    if idx:
        res = idx.get(stem)
        if res:
            return res
        if stem.startswith("t_"):
            res = idx.get(stem[2:])
        elif stem.startswith("tex_"):
            res = idx.get(stem[4:])
        else:
            res = idx.get("t_" + stem) or idx.get("tex_" + stem)
        if res:
            return res

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
    # The letters are the channel order, same as every entry here.
    "rmh":  {"r": "rough", "g": "metal", "b": "height"},
    "mrao": {"r": "metal", "g": "rough", "b": "ao"},
    "arm":  {"r": "ao",    "g": "rough", "b": "metal"},
    "srm":  {                "g": "rough", "b": "metal"},
    "srmh": {                "g": "rough", "b": "metal", "a": "height"},
    "m":    {"r": "metal", "g": "rough"},
    "mr":   {"r": "metal", "g": "rough"},
}

CHANNELS = ("r", "g", "b", "a")

# Slots a packed channel can legally feed — all single-channel greyscale maps.
CHANNEL_SLOTS = (
    "rough", "metal", "ao", "height", "opacity",
    "rough1", "metal1", "ao1", "height1",
    "rough2", "metal2", "ao2", "height2",
    "rough3", "metal3", "ao3", "height3",
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

_COLOR_TOKENS = {"base", "basecolor", "diffuse", "albedo", "color", "diff", "alb", "d", "c", "bc"}
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
    ("orm",      _ORM_TOKENS),

    ("normal2",  {"normal2", "nrm2", "norm2"}),
    ("normal3",  {"normal3", "nrm3", "norm3"}),
    ("normal",   _NORMAL_TOKENS),

    ("rough2",   {"rough2", "roughness2"}),
    ("rough3",   {"rough3", "roughness3"}),
    ("rough",    _ROUGH_TOKENS),

    ("metal2",   {"metal2", "metallic2", "metalness2"}),
    ("metal3",   {"metal3", "metallic3", "metalness3"}),
    ("metal",    _METAL_TOKENS),

    ("ao2",      {"ao2", "occlusion2"}),
    ("ao3",      {"ao3", "occlusion3"}),
    ("ao",       _AO_TOKENS),

    ("height2",  {"height2", "displacement2", "disp2", "blendmask", "blendmask2"}),
    ("height3",  {"height3", "displacement3", "disp3", "blendmask3"}),
    ("height",   _HEIGHT_TOKENS),

    ("tintmask", {"tintmask", "tint_mask"}),
    ("mask1",    {"mask1", "mask_1"}),
    ("mask2",    {"mask2", "mask_2"}),
    ("mask3",    {"mask3", "mask_3"}),
    ("color2",   {"basecolor2", "diffuse2", "albedo2", "color2"}),
    ("color3",   {"basecolor3", "diffuse3", "albedo3", "color3"}),
    ("emissive", {"emissive", "emmisive", "emission", "emi"}),
    ("color",    _COLOR_TOKENS),
]
_COLOR_EXCLUDE = {"var", "variation", "mask", "tint"}


from .shader_schemas import (
    get_slots_for_shader,
    get_channel_slots_for_shader,
)


def norm_key(s: str) -> str:
    """Normalize a texture parameter name for fuzzy matching (strips spaces, underscores, prefixes)."""
    if not s:
        return ""
    s = s.lower().replace("_", "").replace(" ", "")
    for prefix in ("texture", "param", "t"):
        if s.startswith(prefix) and len(s) > len(prefix):
            s = s[len(prefix):]
    return s


def _classify_textures(textures: dict, slot_overrides: dict = None, shader: str = None) -> dict:
    """
    Map {ue_param_name: ue_tex_path} -> {slot: (param, path, channel)} choosing
    the best primary texture per slot. `channel` is None for a whole-texture
    binding, or one of "r"/"g"/"b"/"a" to take a single channel out of a packed
    mask.

    slot_overrides: optional {param_name (case-insensitive): override} from the
    slot-mapping dialog; these always beat the heuristic.
    """
    if not textures or not isinstance(textures, dict):
        return {}

    allowed_slots = set(get_slots_for_shader(shader)) if shader else None
    valid_slots = dict(_SLOT_TOKENS)
    out = {}
    used_params = set()

    overrides_norm = {}
    has_explicit_overrides = False
    if slot_overrides and isinstance(slot_overrides, dict):
        for k, v in slot_overrides.items():
            if k:
                overrides_norm[k.lower()] = v
                overrides_norm[norm_key(k)] = v
                has_explicit_overrides = True

    for param_name, tex_path in textures.items():
        key_lower = param_name.lower()
        key_norm = norm_key(param_name)
        forced = overrides_norm.get(key_lower) or overrides_norm.get(key_norm)
        if forced is None:
            continue
        used_params.add(param_name)
        if isinstance(forced, dict):
            for slot, channel in forced.items():
                if slot in ("split_alpha", "split_rgba"):
                    continue
                if channel in ("rgb", "r", "g", "b", "a"):
                    out[slot] = (param_name, tex_path, channel)
                elif isinstance(channel, str) and channel:
                    out[slot] = (param_name, tex_path, None)
        elif forced and (forced in valid_slots or any(forced == s for s, _ in _SLOT_TOKENS)):
            out[forced] = (param_name, tex_path, None)

    # If the user explicitly provided slot_overrides for this master material,
    # ONLY bind what was explicitly requested — do NOT run heuristic fallback guessing!
    if has_explicit_overrides:
        return out

    # Helper map for base slot vs layer slot token requirements
    slot_map_tokens = {
        "color": _COLOR_TOKENS, "normal": _NORMAL_TOKENS, "rough": _ROUGH_TOKENS,
        "metal": _METAL_TOKENS, "ao": _AO_TOKENS, "height": _HEIGHT_TOKENS, "orm": _ORM_TOKENS,
    }

    # Heuristic matching for remaining parameters
    for slot, tokens in _SLOT_TOKENS:
        if allowed_slots is not None and slot not in allowed_slots and not slot.startswith("orm"):
            continue
        if slot in out:
            continue
        candidates = []
        base_kind = re.sub(r"\d+$", "", slot)
        kind_tokens = slot_map_tokens.get(base_kind, tokens)
        layer_num = slot[-1] if slot[-1].isdigit() else ""

        for param_name, tex_path in textures.items():
            if param_name in used_params:
                continue
            p_toks = _tokens(param_name) | _tokens(os.path.basename(tex_path or ""))
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
    "wear", "edge", "overlay", "secondary", "layer2", "top", "wet", "wetness",
    "water", "puddle", "rain", "tint", "mask", "intensity", "strength", "strenght",
}
# The colour tint is deliberately NOT auto-picked. A Master Material's vectors
# routinely include half a dozen colours — a dirt overlay, a fresnel rim, a
# variation tint — and guessing which one is the base colour from its name got
# it wrong often enough that a wrongly tinted material was the common outcome,
# not the exception. A tint the user did not ask for is worse than no tint: an
# untinted material reads as neutral, a wrongly tinted one looks like a broken
# texture. Map a vector to g_vColorTint in the Params tab of the texture swap
# dialog to set it. Roughness and metalness keep their heuristic — those pick
# from far fewer candidates and are corrected the same way when they miss.


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


# vmat params write_vmat takes as dedicated arguments rather than emitting as a
# generic extra. Mapping a UE param to one of these routes it there — replacing
# the heuristic pick for the scalars, and supplying the only value there is for
# g_vColorTint, which is not guessed at all.
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
    scalars_map = {k.lower(): v for k, v in (scalars or {}).items()}
    vectors_map = {k.lower(): v for k, v in (vectors or {}).items()}
    switches_map = {k.lower(): v for k, v in (switches or {}).items()}

    for ue_name, target in (param_overrides or {}).items():
        if not target:
            continue
        key_low = ue_name.lower()
        if key_low in scalars_map and target not in user_scalars:
            user_scalars[target] = float(scalars_map[key_low])
            claimed.add(target)
        elif key_low in vectors_map and target not in user_vectors:
            v = vectors_map[key_low]
            user_vectors[target] = (float(v.get("r", 1.0)), float(v.get("g", 1.0)), float(v.get("b", 1.0)))
            claimed.add(target)
        elif key_low in switches_map and target in _FLAG_TARGETS and target not in user_flags:
            if bool(switches_map[key_low]):
                user_flags.append(target)
                claimed.add(target)
    return user_scalars, user_vectors, user_flags, claimed


# --- shader selection from material domain/blend --------------------------

def is_decal(flags: dict) -> bool:
    """True if the material's (or its base Material's) domain marks it as a
    UE deferred decal — the signal that determines the Source 2 shader."""
    return (flags or {}).get("domain") == "MD_DeferredDecal"


# The shader used when a caller supplies none. A stated constant, not an
# inference: the shader for a material comes from the saved remap table, and a
# converter that quietly picked its own was indistinguishable from one ignoring
# the table. See converter.seed_shader_for for where defaults are chosen — once,
# visibly, and on their way to disk.
DEFAULT_SHADER = "csgo_environment.vfx"


class MaterialResult:
    def __init__(self, vmat_path: str, textures_written: int, missing: list, is_decal: bool = False, mapped_info: str = ""):
        self.vmat_path = vmat_path
        self.textures_written = textures_written
        self.missing = missing
        self.is_decal = is_decal
        self.mapped_info = mapped_info


from .texture_utils import invert_y_normal as invert_y_normal_map

# _pick_vector_color was removed: the colour tint is user-mapped only. It
# auto-picked a tint from the material's vectors and was the source of
# g_vColorTint "[0 0 0 0]" appearing in converted decals. Map a vector to
# g_vColorTint in the Params tab to set one.

# Derived from _PACKED_LAYOUTS rather than hand-listed: the two had already
# drifted (the layouts knew "mrao" and "arm", the regex did not), which left
# those stems carrying a packed suffix into their split output names.
_PACKED_SUFFIX_RE = re.compile(
    r"[_\-](?:" + "|".join(sorted(_PACKED_LAYOUTS, key=len, reverse=True)) + r"|packed|mask|raw)$",
    re.IGNORECASE,
)


def strip_packed_suffix(stem: str) -> str:
    """Strip packed texture suffixes (_ORM, _RMA, _SRMH, _MASK, _PACKED) from filename stem."""
    if not stem:
        return ""
    return _PACKED_SUFFIX_RE.sub("", stem)


# Every way a source texture announces what it holds. These are dropped from the
# output name so the CS2 slot can take their place — an author's "_diff" is only
# a claim about the input, and after a packed mask is split it is actively wrong.
_CHANNEL_SUFFIX_RE = re.compile(
    r"(?:[_\-])(?:"
    r"diff|diffuse|d|alb|albedo|basecolor|base_color|bc|c|col|color|"
    r"nm|n|nrm|norm|normal|"
    r"rough|roughness|r|metal|metallic|metalness|m|"
    r"ao|occlusion|height|disp|displacement|h|"
    r"spec|specular|s|gloss|glossiness|g|"
    r"opac|opacity|alpha|a|trans|translucency|mask|msk"
    r")$",
    re.IGNORECASE,
)


def texture_base_name(stem: str) -> str:
    """Source texture stem -> the base name its converted maps share.

    "p02_wall_01_diff" -> "p02_wall_01", so the color/normal/rough written from
    that material all sit together as p02_wall_01_color / _normal / _rough.
    A stem that is nothing but a suffix keeps its spelling rather than becoming "".
    """
    if not stem:
        return ""
    base = _CHANNEL_SUFFIX_RE.sub("", strip_packed_suffix(stem))
    return base.strip("_-") or stem


def out_name(stem: str, slot: str) -> str:
    """The filename a converted texture is written under: "<base>_<slot>".

    Naming by destination rather than by source is what makes a slot mapping
    legible on disk — "prop_rmh" split into three files reads as prop_rough /
    prop_metal / prop_ao instead of three variations on the packed name.
    """
    base = texture_base_name(stem)
    return f"{base}_{slot}" if base else slot


_FLAG_SWITCH_MAP = {
    ("twosided", "two_sided", "renderbackfaces", "render_backfaces"): "F_RENDER_BACKFACES",
    ("alphatest", "alpha_test", "usealphatest", "use_alpha_test", "masked"): "F_ALPHA_TEST",
    ("fogenabled", "fog_enabled", "enablefog", "fog"): "g_bFogEnabled",
    ("modeltint", "model_tint", "usemodeltint"): "g_bModelTint1",
    ("depthfeather", "depth_feather"): "F_DEPTH_FEATHER",
    ("tintmask", "tint_mask"): "F_TINT_MASK",
}


def _pick_boolean_flags(switches: dict) -> list:
    """Auto-pick feature flags from UE boolean switch parameters."""
    if not switches or not isinstance(switches, dict):
        return []

    flags = []
    lowered = {str(k).lower().replace(" ", "_"): bool(v) for k, v in switches.items()}

    for aliases, flag in _FLAG_SWITCH_MAP.items():
        for alias in aliases:
            if alias in lowered:
                if lowered[alias] and flag not in flags:
                    flags.append(flag)
                break
            matching_key = None
            for key, val in lowered.items():
                if alias in key:
                    matching_key = key
                    break
            if matching_key and lowered[matching_key] and flag not in flags:
                flags.append(flag)
                break

    return flags


def convert_material(mat_data: dict, bulk_dir: str, output_dir: str,
                     shader: str = None, slot_overrides: dict = None,
                     tex_index: dict = None,
                     param_overrides: dict = None,
                     strip_prefix: bool = True,
                     tex_format: str = "tga",
                     invert_y_normal: bool = True,
                     max_texture_size: int = DEFAULT_TEXTURE_SIZE_LIMIT,
                     feature_flags: dict = None,
                     blend_mode: int = 0) -> MaterialResult:
    """
    Write a vmat (+ converted/split textures) from a dump-material result.
    Returns MaterialResult with the vmat path relative to the output root.

    `shader` comes from the caller's saved remap table and is never inferred
    here; omitting it falls back to DEFAULT_SHADER rather than reading the UE
    flags for a shader nobody asked for. (`is_decal` still reads the flags, but
    only to choose the texture *packing* — a decal composites its opacity into
    the colour alpha — not to override the shader.)

    slot_overrides: optional {param_name: slot_name or None} forwarded to
    _classify_textures to override its heuristic pick (see slot_mapping.py).

    param_overrides: optional {ue_param_name: vmat_param_name} from the Params
    tab. A mapping wins over the heuristic auto-pick for roughness/metalness, and
    is the *only* source of the colour tint — nothing is guessed there. Any other
    target is emitted as an extra scalar/vector on the vmat. See _apply_param_overrides.

    feature_flags: optional {F_*: "0"/"1"} from the Feature Inspector panel
    (slot_mapping.ShaderRemapperDialog). These are now threaded through to
    write_vmat and toggle shader sections — previously this output was discarded.

    blend_mode: F_BLEND_MODE int for csgo_static_overlay (0=Default,
    1=Translucent, 2=Alpha Test, 3=Mod2x, 4=Additive, 5=Multiply, 6=ModThenAdd).
    Decals default to 1 (Translucent) to match Hammer's decal authoring.
    """
    flags = mat_data.get("flags") or {}
def process_material_textures(mat_data: dict, bulk_dir: str, output_dir: str,
                              shader: str = None, slot_overrides: dict = None,
                              tex_index: dict = None,
                              strip_prefix: bool = True,
                              tex_format: str = "tga",
                              invert_y_normal: bool = True,
                              max_texture_size: int = DEFAULT_TEXTURE_SIZE_LIMIT) -> tuple:
    """Extract, split, composite, and save textures for a material instance.
    Returns: (slots_dict, written_count, clean_missing_list, split_summary)
    """
    flags = mat_data.get("flags") or {}
    decal = is_decal(flags) or (shader == "csgo_static_overlay.vfx")
    shader = shader or DEFAULT_SHADER

    mi_path = mat_data.get("material", "")
    vmat_rel = ue_material_to_vmat_path(mi_path, strip_prefix=strip_prefix)
    folder_rel = os.path.dirname(vmat_rel).replace("\\", "/")   # "materials/…"

    def save(img, name, ext=None) -> str:
        ext = ext or tex_format
        rel = f"{folder_rel}/{name}.{ext}"
        dst = os.path.join(output_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        img = limit_texture_size(img, max_texture_size)
        if ext.lower() == "tga":
            img.save(dst, rle=True)
        else:
            img.save(dst)
        return rel

    picks = _classify_textures(mat_data.get("textures"), slot_overrides, shader=shader)
    slots = {}
    written = 0
    missing = []
    split_details = []

    def load(slot):
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
            stem = strip_ue_prefix(stem)
        stem = strip_packed_suffix(stem)
        return src, stem.lower(), pick[2]

    handled = set()
    if decal:
        src, stem, color_ch = load("color")
        opacity_src, op_stem, opacity_ch = load("opacity")
        if not opacity_src:
            opacity_src, op_stem, opacity_ch = load("trans")
        if opacity_src:
            handled.add("opacity")
            handled.add("trans")
        if src:
            handled.add("color")
            color_img = Image.open(src)
            if color_ch == "rgb":
                color_img = color_img.convert("RGB")
            else:
                color_img = color_img.convert("RGBA")

            color_rel = save(color_img, out_name(stem, "color"))
            slots["color"] = color_rel

            if opacity_src:
                mask_img = Image.open(opacity_src)
                if opacity_ch in CHANNELS:
                    mask = mask_img.convert("RGBA").split()[CHANNELS.index(opacity_ch)]
                elif opacity_ch == "a" or "A" in mask_img.getbands() or mask_img.mode in ("RGBA", "LA", "PA"):
                    mask = mask_img.convert("RGBA").split()[3]
                else:
                    mask = mask_img.convert("L")
                trans_rel = save(mask.convert("L"), out_name(op_stem or stem, "trans"))
                slots["opacity"] = trans_rel
                slots["trans"] = trans_rel
                written += 1
                split_details.append("Color (RGB) & Translucency (Alpha)")
            else:
                slots["opacity"] = color_rel
                slots["trans"] = color_rel
            written += 1

    color_normal_slots = (
        "color", "normal", "opacity", "trans", "tintmask",
        "color1", "normal1", "opacity1", "trans1",
        "color2", "normal2", "opacity2", "trans2",
        "color3", "normal3", "opacity3", "trans3",
    )
    for slot in color_normal_slots:
        if slot in handled:
            continue
        src, stem, channel = load(slot)
        if src:
            img = Image.open(src)
            if channel == "a":
                if "A" in img.getbands() or img.mode in ("RGBA", "LA", "PA"):
                    band = img.convert("RGBA").split()[3]
                    slots[slot] = save(band.convert("L"), out_name(stem, slot))
                    split_details.append(f"{slot} (Alpha channel)")
                else:
                    missing.append(slot)
                    continue
            elif channel == "rgb":
                rgb_img = img.convert("RGB")
                if invert_y_normal and slot.startswith("normal"):
                    rgb_img = invert_y_normal_map(rgb_img)
                slots[slot] = save(rgb_img, out_name(stem, slot))
                split_details.append(f"{slot} (RGB)")
            else:
                rgba_img = img.convert("RGBA")
                if invert_y_normal and slot.startswith("normal"):
                    rgba_img = invert_y_normal_map(rgba_img)
                slots[slot] = save(rgba_img, out_name(stem, slot))
                split_details.append(f"{slot}")
            written += 1

    greyscale_slots = (
        "rough", "metal", "ao", "height",
        "rough1", "metal1", "ao1", "height1",
        "rough2", "metal2", "ao2", "height2",
        "rough3", "metal3", "ao3", "height3",
    )
    for slot in greyscale_slots:
        if slot in handled:
            continue
        src, stem, channel = load(slot)
        if not src:
            continue
        img = Image.open(src)
        if channel:
            if channel == "a" and "A" not in img.getbands():
                missing.append(slot)
                continue
            band = img.convert("RGBA").split()[CHANNELS.index(channel)]
            slots[slot] = save(band.convert("L"), out_name(stem, slot))
            split_details.append(f"{slot} ({channel.upper()} channel)")
        else:
            slots[slot] = save(img.convert("L"), out_name(stem, slot))
            split_details.append(f"{slot}")
        written += 1

    clean_missing = sorted(list(set(missing) - set(slots.keys())))
    split_summary = ", ".join(split_details) if split_details else ""
    return slots, written, clean_missing, split_summary


def convert_material(mat_data: dict, bulk_dir: str, output_dir: str,
                     shader: str = None, slot_overrides: dict = None,
                     tex_index: dict = None,
                     param_overrides: dict = None,
                     strip_prefix: bool = True,
                     tex_format: str = "tga",
                     invert_y_normal: bool = True,
                     max_texture_size: int = DEFAULT_TEXTURE_SIZE_LIMIT,
                     feature_flags: dict = None,
                     blend_mode: int = 0) -> MaterialResult:
    """Write a vmat (+ converted/split textures) from a dump-material result."""
    flags = mat_data.get("flags") or {}
    decal = is_decal(flags) or (shader == "csgo_static_overlay.vfx")
    shader = shader or DEFAULT_SHADER

    mi_path = mat_data.get("material", "")
    vmat_rel = ue_material_to_vmat_path(mi_path, strip_prefix=strip_prefix)
    vmat_abs = os.path.join(output_dir, vmat_rel)

    slots, written, missing, split_summary = process_material_textures(
        mat_data, bulk_dir, output_dir, shader=shader, slot_overrides=slot_overrides,
        tex_index=tex_index, strip_prefix=strip_prefix, tex_format=tex_format,
        invert_y_normal=invert_y_normal, max_texture_size=max_texture_size
    )

    color_tint = None
    rough_scale = _pick_scalar(mat_data.get("scalars"), "roughness", "tileable 1 roughness")
    metal_scale = _pick_scalar(mat_data.get("scalars"), "metallic", "metalness", default=0.0)

    # Param-mapping UI: a user mapping to a heuristic target wins over the
    # auto-pick; anything else is emitted as an extra scalar/vector.
    user_scalars, user_vectors, user_flags, claimed = _apply_param_overrides(
        mat_data.get("scalars"), mat_data.get("vectors"), mat_data.get("switches"), param_overrides)
    if "g_vColorTint" in claimed:
        color_tint = user_vectors.pop("g_vColorTint")
    # No else: the tint is user-mapped only. Auto-picking one from the
    # material's vectors wrote g_vColorTint "[0 0 0 0]" — a black tint nobody
    # asked for — into every decal that happened to declare a dark colour.

    if not (slot_overrides or param_overrides or feature_flags):
        auto_flags = _pick_boolean_flags(mat_data.get("switches"))
        for f in auto_flags:
            if f not in user_flags:
                user_flags.append(f)

    # csgo_static_overlay gates TextureNormal/Rough/Metal/AO behind F_LIT, which
    # is off by default — so a mapped normal was written into the vmat's
    # UnusedVariables block and quietly ignored by the shader, which reads as
    # the mapping having been dropped. Supplying one of those maps is the
    # request; turn the feature on so it takes effect. An explicit F_LIT from
    # the Feature Inspector always wins.
    feature_flags = dict(feature_flags or {})
    _LIT_SLOTS = ("normal", "rough", "metal", "ao")
    if any(slots.get(s) for s in _LIT_SLOTS) and "F_LIT" not in feature_flags:
        from .shader_schemas import get_shader_schema
        schema = get_shader_schema(shader)
        if schema and any(f.name == "F_LIT" for f in (getattr(schema, "features", None) or ())):
            feature_flags["F_LIT"] = "1"

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
               alpha_test_ref=alpha_test_ref, render_backfaces=render_backfaces,
               feature_flags=feature_flags, blend_mode=blend_mode)
    clean_missing = sorted(list(set(missing) - set(slots.keys())))
    mapped_info = ", ".join(sorted(slots.keys())) if slots else ""
    return MaterialResult(vmat_rel, written, clean_missing, is_decal=decal, mapped_info=mapped_info)


def demo():
    # Output textures are named for the CS2 slot they feed, not the source's
    # claim about itself: a packed mask split three ways must not leave three
    # files all called "<something>_rmh".
    assert out_name("prop_diff", "color") == "prop_color"
    assert out_name("prop_rmh", "rough") == "prop_rough"
    assert out_name("prop_rmh", "metal") == "prop_metal"
    assert out_name("prop_diff", "opacity") == "prop_opacity"
    assert out_name("p02_wall_01_nm", "normal") == "p02_wall_01_normal"
    assert out_name("t_awning_01_orm", "ao") == "t_awning_01_ao"
    # A stem with nothing to strip still gets its slot.
    assert out_name("bare", "color") == "bare_color"
    # A stem that is *only* a suffix keeps its spelling instead of becoming "_color".
    assert out_name("diff", "color") == "diff_color"

    # The packed-suffix regex is derived from _PACKED_LAYOUTS, so every layout
    # the classifier can split is also one the namer can strip. Hand-listing
    # them had already let "mrao" and "arm" drift out of the regex.
    for token in _PACKED_LAYOUTS:
        assert strip_packed_suffix(f"x_{token}") == "x", token

    # An acronym layout splits by its own letter order.
    token, layout = packed_layout("Mask", "prop_rmh.tga")
    assert token == "rmh" and layout == {"r": "rough", "g": "metal", "b": "height"}, layout

    # End to end: the two source maps land as four slot-named outputs.
    picks = _classify_textures({"Albedo": "/G/T/prop_diff.prop_diff",
                                "RMH": "/G/T/prop_rmh.prop_rmh"})
    assert set(picks) == {"color", "rough", "metal", "height"}, picks
    assert picks["rough"][2] == "r" and picks["metal"][2] == "g" and picks["height"][2] == "b"

    # An explicit slot mapping beats the heuristic, and its channel survives —
    # dropping it is what made a decal's alpha mapping read as luminance.
    picks = _classify_textures(
        {"Albedo_Map": "/G/T/d_dirt_01.d_dirt_01"},
        {"Albedo_Map": {"split_alpha": True, "color": "rgb", "opacity": "a"}},
        shader="csgo_static_overlay.vfx",
    )
    assert picks["color"][2] == "rgb", picks
    assert picks["opacity"][2] == "a", picks

    # No shader is inferred from the material's own data. A UE deferred decal
    # used to be forced onto csgo_static_overlay regardless of what the saved
    # remap table said, which silently overrode exactly the materials a user is
    # most likely to have remapped on purpose.
    import tempfile
    decal_data = {"material": "/Game/M/MI_D.MI_D", "flags": {"domain": "MD_DeferredDecal"},
                  "textures": {}, "scalars": {}, "vectors": {}, "switches": {}}
    out = tempfile.mkdtemp()
    res = convert_material(decal_data, None, out, shader="csgo_environment.vfx")
    written = open(os.path.join(out, res.vmat_path), encoding="utf-8", errors="replace").read()
    assert "csgo_environment.vfx" in written, written[:200]
    assert "csgo_static_overlay.vfx" not in written, "decal branch overrode the chosen shader"
    # And with no shader given, the stated constant — not a reading of `flags`.
    res = convert_material(decal_data, None, tempfile.mkdtemp())
    assert DEFAULT_SHADER == "csgo_environment.vfx"

    # A decal honors every mapped slot, not just colour. The decal path used to
    # write the colour and return, so a mapped "Normal_Map -> normal" was
    # dropped and showed up in the vmat's UnusedVariables as TextureNormal "".
    src_dir = tempfile.mkdtemp()
    for name in ("deco_diff", "deco_nm"):
        Image.new("RGBA", (4, 4), (128, 128, 255, 200)).save(os.path.join(src_dir, f"{name}.tga"), rle=True)
    decal_tex = {
        "material": "/Game/M/MI_Deco.MI_Deco",
        "flags": {"domain": "MD_DeferredDecal"},
        "textures": {"Albedo_Map": "/Game/T/deco_diff.deco_diff",
                     "Normal_Map": "/Game/T/deco_nm.deco_nm"},
        "scalars": {}, "vectors": {"Base Color": {"r": 0.0, "g": 0.0, "b": 0.0}}, "switches": {},
    }
    out = tempfile.mkdtemp()
    res = convert_material(
        decal_tex, src_dir, out, shader="csgo_static_overlay.vfx", blend_mode=1,
        slot_overrides={"Albedo_Map": {"split_alpha": True, "color": "rgb", "opacity": "a"},
                        "Normal_Map": "normal"},
    )
    body = open(os.path.join(out, res.vmat_path), encoding="utf-8").read()
    assert 'TextureNormal "materials' in body, body
    assert 'TextureColor "materials' in body, body
    assert res.missing == [], res.missing
    # ...and no tint is invented from the material's own vectors. A dark base
    # colour used to become g_vColorTint "[0 0 0 0]" on every such decal.
    assert 'g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"' in body, body

    print("ok")


if __name__ == "__main__":
    demo()
