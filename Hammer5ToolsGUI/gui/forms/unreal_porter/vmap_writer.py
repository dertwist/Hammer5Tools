"""Prepare normalized Unreal placements for the Core-owned VMAP writer."""

from collections.abc import Callable, Iterable
from dataclasses import replace
from typing import Optional

from core.bridge import CoreBridge

from .light_entities import CUBEMAP_COMPONENTS, LIGHT_COMPONENTS, SKY_COMPONENTS, ue_actor_to_entity
from .transform import UETransform, UnitScale, convert_transform, mirror_placement
from .vmdl_writer import mirrored_model_path, ue_mesh_to_model_path

_SIMPLE_COMPONENT = "StaticMeshComponent"
_PROP_STATIC = {
    "classname": "prop_static", "model": "", "skin": "default", "solid": "6",
    "rendercolor": "255 255 255", "disableshadows": "0",
}


def actor_transform(actor: dict, unit_scale: float = UnitScale.ONE_TO_ONE):
    """Convert one normalized Unreal actor transform into Source coordinates."""
    location, rotation, scale = actor["location"], actor["rotation"], actor["scale"]
    return convert_transform(
        UETransform(
            (location["x"], location["y"], location["z"]),
            (rotation["pitch"], rotation["yaw"], rotation["roll"]),
            (scale["x"], scale["y"], scale["z"]),
        ),
        unit_scale=unit_scale,
    )


class VmapWriteResult:
    """Python-native scene conversion summary consumed by SceneModelsWorker."""

    def __init__(self):
        self.placed = 0
        self.placed_smartprops = 0
        self.placed_decals = 0
        self.placed_lights = 0
        self.placed_sky = 0
        self.placed_cubemaps = 0
        self.skipped = 0
        self.skipped_types = {}
        self.models = set()
        self.decal_materials = set()
        self.mirrored_meshes = set()

    def note_skip(self, component_type):
        self.skipped += 1
        self.skipped_types[component_type] = self.skipped_types.get(component_type, 0) + 1


def _placement(kind, name, transform, *, properties=None, resource_path=None):
    return {
        "Kind": kind, "Name": name, "Origin": list(transform.origin),
        "Angles": list(transform.angles), "Scales": list(transform.scales),
        "Properties": properties, "ResourcePath": resource_path,
    }


def write_vmap(
    actors: Iterable[dict],
    output_path: str,
    model_resolver: Optional[Callable[[str], str]] = None,
    unit_scale: float = UnitScale.ONE_TO_ONE,
    strip_prefix: bool = True,
    import_lights: bool = False,
    import_sky: bool = False,
    import_cubemaps: bool = False,
    import_decals: bool = True,
    mirror_negative_scale: bool = True,
) -> VmapWriteResult:
    """Convert normalized actors and write their VMAP through SourcePorter Core."""
    if model_resolver is None:
        model_resolver = lambda mesh: ue_mesh_to_model_path(mesh, strip_prefix=strip_prefix)

    from .material_converter import ue_material_to_vmat_path
    from .vmdl_writer import strip_ue_prefix

    result, placements = VmapWriteResult(), []
    gated = {}
    for kinds, enabled in (
        (LIGHT_COMPONENTS, import_lights), (SKY_COMPONENTS, import_sky),
        (CUBEMAP_COMPONENTS, import_cubemaps), (("DecalComponent",), import_decals),
    ):
        for component_type in kinds:
            gated[component_type] = enabled

    for actor in actors:
        component_type = actor.get("componentType", "")
        mesh, blueprint = actor.get("mesh"), actor.get("blueprint")
        decal_material = actor.get("material") if component_type == "DecalComponent" else None
        if component_type in gated:
            if not gated[component_type]:
                result.note_skip(component_type)
                continue
        elif component_type != _SIMPLE_COMPONENT and component_type != "BlueprintActor" and not blueprint:
            result.note_skip(component_type)
            continue

        transform = actor_transform(actor, unit_scale)
        name = actor.get("actor") or f"ent_{len(placements) + 1001}"
        entity = ue_actor_to_entity(actor, unit_scale) if component_type in gated else None
        if entity:
            _, properties = entity
            placements.append(_placement("Entity", name, transform, properties=properties))
            if component_type in SKY_COMPONENTS:
                result.placed_sky += 1
            elif component_type in CUBEMAP_COMPONENTS:
                result.placed_cubemaps += 1
            else:
                result.placed_lights += 1
        elif component_type == "BlueprintActor" or blueprint:
            clean_name = strip_ue_prefix(blueprint or name) if strip_prefix else (blueprint or name)
            placements.append(_placement("SmartProp", name, transform,
                                         resource_path=f"smartprops/{clean_name.lower()}.vsmart"))
            result.placed_smartprops += 1
        elif component_type == "DecalComponent" and decal_material:
            material = ue_material_to_vmat_path(decal_material, strip_prefix=strip_prefix)
            placements.append(_placement("Decal", name, transform, resource_path=material))
            result.decal_materials.add(decal_material)
            result.placed_decals += 1
        elif component_type == _SIMPLE_COMPONENT and mesh:
            model, angles, scales = model_resolver(mesh), transform.angles, transform.scales
            if mirror_negative_scale:
                angles, scales, mirror_axes = mirror_placement(angles, scales)
                if any(mirror_axes):
                    result.mirrored_meshes.add((mesh, mirror_axes))
                    model = mirrored_model_path(model, mirror_axes)
            placed_transform = replace(transform, angles=angles, scales=scales)
            placements.append(_placement("Entity", name, placed_transform,
                                         properties=dict(_PROP_STATIC, model=model)))
            result.models.add(model)
            result.placed += 1

    core_result = CoreBridge.instance().write_unreal_map(output_path, {"Placements": placements})
    if core_result.diagnostics:
        raise RuntimeError("; ".join(core_result.diagnostics))
    return result


def demo():
    actor = {
        "location": {"x": 300, "y": 400, "z": 50},
        "rotation": {"pitch": 20, "yaw": 60, "roll": 30},
        "scale": {"x": 2, "y": 2, "z": 2},
    }
    transform = actor_transform(actor)
    assert tuple(round(value, 6) for value in transform.origin) == (300.0, -400.0, 50.0)
    assert tuple(round(value, 6) for value in transform.angles) == (-20.0, -60.0, 30.0)


if __name__ == "__main__":
    demo()
