"""Checks for the viewport half of the SmartProp material/tint operations.

Core resolves SetTintColor/MaterialTint/MaterialOverride into normalized names and colours
(see SmartPropMaterialEvaluator); these cover the render-side folding that turns them into the
per-submesh tint and material substitution, without needing a GL context.
"""
from core.bridge.core import (
    SmartPropMaterialReplacement,
    SmartPropMaterialTint,
)
from gui.editors.smartprop_editor.viewport_3d.mesh_cache import GPUMaterial
from gui.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea

normalize = SmartProp3DRenderArea._normalize_material_name


class _StubCache:
    """Stands in for MeshCache: records what was requested, serves what is 'loaded'."""

    def __init__(self, loaded=None):
        self.loaded = loaded or {}
        self.requested = []

    def get_gpu_material(self, path):
        return self.loaded.get(path)

    def request_material(self, path, context_addon=None):
        self.requested.append(path)


class _StubArea:
    """A render area reduced to the material machinery under test."""

    _normalize_material_name = staticmethod(normalize)
    _instance_materials = SmartProp3DRenderArea._instance_materials
    _submesh_tint = SmartProp3DRenderArea._submesh_tint
    _resolve_submesh_material = SmartProp3DRenderArea._resolve_submesh_material

    def __init__(self, cache):
        self.mesh_cache = cache


def test_material_names_normalize_to_cores_form():
    # Core lowercases, forward-slashes and drops the compiled suffix; the viewport has to
    # reduce a model's own material path the same way or nothing ever matches.
    assert normalize("Materials\\Models\\Crate.vmat") == "materials/models/crate.vmat"
    assert normalize("/materials/models/crate.vmat_c") == "materials/models/crate.vmat"
    assert normalize("") == ""
    assert normalize(None) == ""


def test_instance_materials_reads_core_results():
    info = {
        "tint_color": (1.0, 0.5, 0.5, 1.0),
        "material_tints": (SmartPropMaterialTint("materials/a.vmat", (0.0, 1.0, 0.0, 1.0)),),
        "material_overrides": (SmartPropMaterialReplacement("materials/a.vmat", "materials/b.vmat"),),
    }
    base_tint, tints, overrides = _StubArea(_StubCache())._instance_materials(info)

    assert base_tint == (1.0, 0.5, 0.5, 1.0)
    assert tints == {"materials/a.vmat": (0.0, 1.0, 0.0, 1.0)}
    assert overrides == {"materials/a.vmat": "materials/b.vmat"}


def test_instance_materials_defaults_to_no_tint():
    assert _StubArea(_StubCache())._instance_materials({}) == (None, {}, {})


def test_material_tint_multiplies_into_the_placement_tint():
    matching = GPUMaterial(name="Materials/A.vmat")
    other = GPUMaterial(name="materials/c.vmat")
    tints = {"materials/a.vmat": (0.5, 1.0, 1.0, 1.0)}
    area = _StubArea(_StubCache())

    # The matching submesh gets both tints folded together...
    assert area._submesh_tint((0.5, 0.5, 1.0, 1.0), tints, matching) == (0.25, 0.5, 1.0, 1.0)
    # ...and an unmatched one keeps only the placement tint.
    assert area._submesh_tint((0.5, 0.5, 1.0, 1.0), tints, other) == (0.5, 0.5, 1.0, 1.0)
    # A per-material tint with no placement tint stands on its own.
    assert area._submesh_tint(None, tints, matching) == (0.5, 1.0, 1.0, 1.0)


def test_material_override_substitutes_only_once_loaded():
    original = GPUMaterial(name="materials/a.vmat")
    replacement = GPUMaterial(name="materials/b.vmat")
    overrides = {"materials/a.vmat": "materials/b.vmat"}

    # Not loaded yet: the original keeps drawing and the load is queued exactly once.
    pending = _StubArea(_StubCache())
    assert pending._resolve_submesh_material(original, overrides, None) is original
    assert pending.mesh_cache.requested == ["materials/b.vmat"]

    # Loaded: the substitute is drawn instead, and nothing further is requested.
    ready = _StubArea(_StubCache({"materials/b.vmat": replacement}))
    assert ready._resolve_submesh_material(original, overrides, None) is replacement
    assert ready.mesh_cache.requested == []

    # A material nobody overrode is untouched.
    assert ready._resolve_submesh_material(GPUMaterial(name="materials/c.vmat"), overrides, None).name \
        == "materials/c.vmat"
    assert ready._resolve_submesh_material(original, {}, None) is original
