"""
Core data model and generic .vmat emitter for the CS2 shader schema package.

A ShaderSchema declares, per shader:
  * valid texture slots,
  * material-editor feature flags (F_*) + their UI grouping and prerequisite rules,
  * optional blend modes (F_BLEND_MODE values),
  * an ordered list of Blocks, each a titled section of parameters guarded by a
    when-condition over the runtime Ctx.

format_vmat() walks the blocks, emits the active ones in declared order, sources
each parameter value from explicit overrides → bound texture slots → the param's
declared default, and auto-appends an UnusedVariables block listing every
non-flag parameter whose emit condition was false — exactly what Hammer's own
material editor writes.

All whitespace is CRLF + tabs to match Hammer's authoring format on Windows.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# Parameter kinds. "scalar"/"int"/"bool" are single numbers; "vector2"/"vector3"
# are plain numeric tuples; "color" is an RGB tuple rendered to 6-decimal gamma
# literal form; "texture" is a path string (or empty when unbound).
KIND_SCALAR = "scalar"
KIND_INT = "int"
KIND_BOOL = "bool"
KIND_VECTOR2 = "vector2"
KIND_VECTOR3 = "vector3"
KIND_IVECTOR2 = "ivector2"   # integer 2-component, e.g. g_vAnimationGrid "[1 1]"
KIND_COLOR = "color"
KIND_TEXTURE = "texture"


@dataclass(frozen=True)
class Param:
    """One authored .vmat parameter line under a Block."""
    name: str
    kind: str
    default: Any = None
    # Optional inline trailing comment, e.g. "// Additive". Rendered verbatim.
    comment: str = ""
    # Optional comment resolver: returns a trailing comment string (e.g.
    # "// Translucent") computed from the resolved value. Used for F_BLEND_MODE
    # where the comment names the selected mode. Overrides the static `comment`.
    comment_fn: Optional[Callable[[Any, "Ctx"], str]] = None
    # Optional default resolver: when the param has no explicit value and no
    # bound slot, this computes the default from Ctx (e.g. an unbound roughness
    # texture renders as a uniform color from g_flRoughnessScale). Used by the
    # carried-forward environment shader to match its scale-dependent texture
    # defaults. Overrides the static `default` when present.
    default_fn: Optional[Callable[["Ctx"], Any]] = None
    # For textures: the input slot whose bound path feeds this param (e.g. "color"
    # -> TextureColor). When the slot is unbound the empty-string default renders.
    slot: Optional[str] = None
    # Optional per-param emit gate evaluated against Ctx. None = always emit when
    # the owning Block is active. Used for params that toggle independently of a
    # whole section (e.g. TextureTranslucency only when alpha-test/blend present).
    when: Optional[Callable[["Ctx"], bool]] = None
    # Optional "is this param compiled into the material at all" gate. A param
    # that is not defined for the current feature combo is neither emitted nor
    # listed in UnusedVariables (it does not exist in the shader). None = always
    # defined. Used to model Source 2 static-combo param visibility, e.g. the
    # alpha-test pair on csgo_static_overlay is undefined for blend mode 1.
    defined: Optional[Callable[["Ctx"], bool]] = None

    @property
    def is_flag(self) -> bool:
        return self.name.startswith("F_")


@dataclass(frozen=True)
class Block:
    """A titled //---- section ---- of parameters, optionally gated."""
    title: str
    params: Tuple[Param, ...] = ()
    # None = always. Truthy → section + its params are emitted.
    when: Optional[Callable[["Ctx"], bool]] = None


@dataclass(frozen=True)
class FeatureDef:
    """A material-editor feature flag.

    Most features are boolean checkboxes (range 0..1). Some are enum-valued
    (range 0..N, e.g. F_BORDER_BLEND_MODE_2 0..3, F_DETAIL_TEXTURE 0..4) — those
    render as a dropdown in the inspector and their 'on' state is value != 0.

    Three FeatureRule kinds are modeled, matching the shader FEATURES block:
      * requires  — FeatureRule Requires(this, parent...): parents must be on
                    before this is enabled (greyed out otherwise).
      * excludes  — FeatureRule Allow1(this, other): mutual exclusion. Turning
                    this on forces 'other' off (and vice versa).
      * child_of  — FeatureRule ChildOf(this, parent): like requires but also
                    hides/disables this unless parent is on. Functionally a
                    stronger requires gate for UI purposes.
    """
    name: str        # "F_LIT", "F_RENDER_BACKFACES", "F_BORDER_BLEND_MODE_2"
    label: str       # "Render Backfaces"
    section: str     # UI group: "Lighting", "2-Sided Rendering", ...
    default: int = 0
    # For enum features: the max value (range_max=1 means boolean). When >1,
    # `options` names each value for the dropdown.
    range_max: int = 1
    options: Tuple[str, ...] = ()
    # FeatureRule Requires(child, parents...) and ChildOf(child, parent).
    requires: Tuple[str, ...] = ()
    child_of: Tuple[str, ...] = ()
    # FeatureRule Allow1(a, b): turning this on forces each `excludes` flag off.
    excludes: Tuple[str, ...] = ()

    @property
    def is_enum(self) -> bool:
        return self.range_max > 1


@dataclass(frozen=True)
class BlendMode:
    """A selectable F_BLEND_MODE value (static_overlay only)."""
    value: int
    name: str


@dataclass(frozen=True)
class ShaderSchema:
    """The full authoring contract for one CS2 shader."""
    shader: str
    verified: bool                       # True = matched against Hammer reference vmats
    slots: Tuple[str, ...]               # valid texture slot names for this shader
    features: Tuple[FeatureDef, ...] = ()
    blend_modes: Tuple[BlendMode, ...] = ()
    blocks: Tuple[Block, ...] = ()

    def feature(self, name: str) -> Optional[FeatureDef]:
        for f in self.features:
            if f.name == name:
                return f
        return None

    def blend_mode_name(self, value: int) -> str:
        for bm in self.blend_modes:
            if bm.value == value:
                return bm.name
        return ""



class Ctx:
    """Resolved authoring state passed to Block/Param when-conditions and the
    emitter: active feature flags, the chosen blend mode (0 = none/default), the
    set of bound texture slots {slot: path}, and typed per-param overrides."""
    __slots__ = ("flags", "blend_mode", "slots", "values")

    def __init__(self, flags: Dict[str, Any], blend_mode: int,
                 slots: Dict[str, str], values: Dict[str, Any]):
        self.flags = flags
        self.blend_mode = blend_mode
        self.slots = slots
        # F_BLEND_MODE is just the int form of the blend_mode selector — keep the
        # values dict in sync so an F_BLEND_MODE Param resolves to ctx.blend_mode
        # without every caller having to set it twice.
        self.values = dict(values)
        if blend_mode:
            self.values.setdefault("F_BLEND_MODE", blend_mode)

    def flag(self, name: str) -> bool:
        return _truthy(self.flags.get(name))

    def value(self, name: str, default: Any = None) -> Any:
        v = self.values.get(name)
        return default if v is None else v


def _truthy(v: Any) -> bool:
    """Source 2 flag values arrive as int 0/1, str "0"/"1"/"True", or bool."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip() not in ("", "0", "false", "False")
    return bool(v)



def _fmt_scalar(v: Any, precision: int = 3) -> str:
    if isinstance(v, str):
        return v
    return f"{float(v):.{precision}f}"


def _fmt_int(v: Any) -> str:
    if isinstance(v, str):
        return v
    return str(int(v))


def _fmt_vector(v: Any, precision: int = 3) -> str:
    """Render a 2-component vector as '[a b]'."""
    comps = list(v) if not isinstance(v, str) else [v]
    return "[" + " ".join(f"{float(c):.{precision}f}" for c in comps) + "]"


def _fmt_ivector(v: Any) -> str:
    """Render an integer 2-component vector as '[1 1]' (no decimal padding)."""
    comps = list(v) if not isinstance(v, str) else [v]
    return "[" + " ".join(str(int(c)) for c in comps) + "]"


def _fmt_color(v: Any) -> str:
    """Render an RGB color as '[r g b 0.000000]' (6-decimal gamma literal)."""
    if isinstance(v, str):
        return v
    r, g, b = float(v[0]), float(v[1]), float(v[2])
    return f"[{r:.6f} {g:.6f} {b:.6f} 0.000000]"


def _fmt_value(param: Param, v: Any, *, compact: bool = False) -> str:
    """Render a parameter's value for the .vmat line.

    compact=True is used inside UnusedVariables, where Hammer writes scalars
    without trailing-zero padding ('1', '0.5', '0') instead of '"1.000"'. The
    caller wraps the non-compact result in quotes; compact values are also quoted
    (UnusedVariables lines are quoted), just with the short scalar string.
    """
    kind = param.kind
    if kind == KIND_TEXTURE:
        return str(v) if v else ""
    if kind == KIND_COLOR:
        return _fmt_color(v)
    if kind == KIND_VECTOR2:
        return _fmt_vector(v, precision=3)
    if kind == KIND_VECTOR3:
        return _fmt_vector(v, precision=3)
    if kind == KIND_IVECTOR2:
        return _fmt_ivector(v)
    if kind == KIND_INT:
        return _fmt_int(v)
    if kind == KIND_BOOL:
        return "1" if _truthy(v) else "0"
    # scalar
    if compact:
        # Compact scalar: drop trailing zeros to match Hammer's UnusedVariables
        # form ('1', '0.5', '0') rather than the padded body form ('1.000').
        if isinstance(v, str):
            return v
        f = float(v)
        if f == int(f):
            return str(int(f))
        return f"{f:.{3}f}".rstrip("0").rstrip(".")
    return _fmt_scalar(v, precision=3)



def _resolve_value(param: Param, ctx: Ctx) -> Any:
    """Source a parameter value: explicit override → bound slot → declared default."""
    if param.name in ctx.values:
        return ctx.values[param.name]
    if param.kind == KIND_TEXTURE and param.slot:
        bound = ctx.slots.get(param.slot)
        if bound:
            return bound
        # fall through to default / default_fn (renders as empty for textures)
    if param.default_fn is not None:
        try:
            return param.default_fn(ctx)
        except Exception:
            pass
    return param.default


def _param_defined(param: Param, ctx: Ctx) -> bool:
    if param.defined is not None:
        try:
            return bool(param.defined(ctx))
        except Exception:
            return False
    return True


def _param_active(param: Param, ctx: Ctx) -> bool:
    if param.when is not None:
        try:
            return bool(param.when(ctx))
        except Exception:
            return False
    return True


def _block_active(block: Block, ctx: Ctx) -> bool:
    if block.when is not None:
        try:
            return bool(block.when(ctx))
        except Exception:
            return False
    return True


def format_vmat(schema: ShaderSchema, ctx: Ctx) -> str:
    """Render the full .vmat body (without the leading 'Layer0 {' wrapper) for
    the given schema and resolved authoring context.

    Emits the shader line, every active block in declared order with sourced
    parameter values, then an auto-computed UnusedVariables block listing each
    non-flag parameter whose emit condition was false. Returns the text to be
    wrapped in 'Layer0 {\\n ... \\n}' by the caller.
    """
    lines: List[str] = [f'\tshader "{schema.shader}"']

    emitted_names: set = set()
    unused: List[str] = []   # compact '"name" "value"' entries

    for block in schema.blocks:
        active = _block_active(block, ctx)
        if active:
            lines.append("")
            lines.append(f"\t//---- {block.title} ----")
            for param in block.params:
                if not _param_defined(param, ctx):
                    continue  # not compiled in for this combo: never emitted, never unused
                if not _param_active(param, ctx):
                    if not param.is_flag:
                        v = _resolve_value(param, ctx)
                        unused.append(_unused_entry(param, v))
                    continue
                v = _resolve_value(param, ctx)
                lines.append(_emit_line(param, v))
                emitted_names.add(param.name)
        else:
            # Whole block inactive: every defined non-flag param is unused.
            for param in block.params:
                if param.is_flag:
                    continue
                if not _param_defined(param, ctx):
                    continue
                v = _resolve_value(param, ctx)
                unused.append(_unused_entry(param, v))

    if unused:
        lines.append("")
        lines.append("\tUnusedVariables")
        lines.append("\t{")
        lines.extend(f"\t\t{e}" for e in unused)
        lines.append("\t}")

    return "\n".join(lines)


def _emit_line(param: Param, v: Any) -> str:
    """One authored parameter line, quoted for g_*/Texture*, bare for F_*."""
    if param.is_flag:
        # F_* feature flags render unquoted: 'F_LIT 1' or 'F_BLEND_MODE 4 // Additive'
        s = _fmt_int(v) if v is not None else "1"
        line = f"\t{param.name} {s}"
        comment = param.comment
        if param.comment_fn is not None:
            try:
                comment = param.comment_fn(v, None) or ""
            except Exception:
                comment = ""
        if comment:
            line += f" {comment}"
        return line
    s = _fmt_value(param, v)
    return f'\t{param.name} "{s}"'


def _unused_entry(param: Param, v: Any) -> str:
    """Compact UnusedVariables entry: '\"name\" \"value\"'."""
    s = _fmt_value(param, v, compact=True)
    return f'"{param.name}" "{s}"'



def validate_feature_flags(schema: ShaderSchema, flags: Dict[str, Any]) -> Dict[str, Any]:
    """Return a normalized copy of `flags` with all FeatureRule constraints
    enforced. Three rule kinds are modeled (matching the shader FEATURES block):

      * Requires(child, parents) / ChildOf(child, parent): if `child` is on but
        any parent is off, the child is forced off (its prerequisites aren't met).
      * Allow1(a, b) mutual exclusion: if `a` is turned on, `b` is forced off.
        (The caller toggling `a` is the active intent; the sibling yields.)

    Enum-valued features (range_max > 1) are 'on' when their value is non-zero,
    so the same rules apply. The function never silently enables a flag — it
    only enforces gates and exclusions, mirroring how Hammer's editor behaves."""
    if not flags:
        return {}
    out = {k: v for k, v in flags.items()}
    feat_by_name = {f.name: f for f in schema.features}

    # Repeat until stable: enabling/disabling one flag can cascade (e.g. turning
    # a parent off should then gate its children). A couple of passes suffice.
    for _ in range(8):
        changed = False
        for feat in schema.features:
            val = _feat_value(out, feat)
            parents = feat.requires + feat.child_of
            if val != 0 and parents:
                # Prerequisite not met — child must be off.
                if any(_feat_value(out, feat_by_name.get(p)) == 0 for p in parents if p in feat_by_name):
                    out[feat.name] = "0"
                    changed = True
                    continue
            if val != 0 and feat.excludes:
                # Allow1: this flag being on forces each excluded sibling off.
                for sib in feat.excludes:
                    sib_feat = feat_by_name.get(sib)
                    if sib_feat and _feat_value(out, sib_feat) != 0:
                        out[sib] = "0"
                        changed = True
        if not changed:
            break
    return out


def _feat_value(flags: Dict[str, Any], feat: Optional[FeatureDef]) -> int:
    """Numeric value of a feature in flags (0 when unset). Handles bool/int/str."""
    if feat is None:
        return 0
    v = flags.get(feat.name, feat.default)
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            return 1 if v.strip().lower() in ("true", "on") else 0
    return 1 if v else 0
