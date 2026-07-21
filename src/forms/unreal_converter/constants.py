"""
Static metadata for the Unreal Converter.

This tool is a *content migration helper / entity converter*, not a full
automated exporter. A lot of Unreal features have no meaningful Source 2
equivalent and must be rebuilt by hand. The lists below drive:
  * the persistent warning banner on the General tab, and
  * the scan-time detection that logs a warning when such assets are found.
"""

import re

# ---------------------------------------------------------------------------
# File-type categories (drive the General-tab enable checkboxes + the tabs)
# ---------------------------------------------------------------------------

FILE_TYPES = ["Scenes", "Models", "Materials", "Blueprints", "Textures"]

FILE_TYPE_TARGETS = {
    "Scenes":     "vmap",
    "Models":     "vmdl",
    "Materials":  "vmat",
    "Blueprints": "vsmart",
    "Textures":   "vtex",
}

FILE_TYPE_DESCRIPTIONS = {
    "Scenes":     "vmap  (map actors -> prop_static entities)",
    "Models":     "vmdl  (mesh wrapper referencing exported FBX/glTF)",
    "Materials":  "vmat  (material instance params -> csgo_environment)",
    "Blueprints": "vsmart (content-assembly blueprints -> smart props)",
    "Textures":   "vtex  (textures, incl. splitting packed ORM/RMA maps)",
}


# ---------------------------------------------------------------------------
# Things that CANNOT be converted automatically -> warn the user up front
# ---------------------------------------------------------------------------

class Unsupported:
    """A category of Unreal content the converter cannot translate."""

    def __init__(self, key, label, reason, patterns):
        self.key = key
        self.label = label
        self.reason = reason
        # Compiled case-insensitive filename patterns used for scan detection.
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    def matches(self, name: str) -> bool:
        return any(p.search(name) for p in self.patterns)


UNSUPPORTED = [
    Unsupported(
        "master_materials",
        "Master materials / material graphs",
        "Source 2 has its own shaders. Node graphs and custom HLSL do not "
        "translate — only Material Instance parameters (textures + scalars) "
        "are converted. Rebuild master materials manually.",
        [r"^MM_", r"^M_", r"MasterMaterial", r"Material_Functions", r"^MF_"],
    ),
    Unsupported(
        "nanite",
        "Nanite meshes",
        "Nanite virtualized geometry has no Source 2 equivalent. Export a "
        "regular LOD/triangulated mesh from Unreal before converting.",
        [r"_Nanite", r"Nanite"],
    ),
    Unsupported(
        "niagara",
        "Niagara / Cascade particles",
        "Particle systems are an entirely different system in Source 2 (vpcf) "
        "and are not auto-converted. Rebuild in the CS2 particle editor.",
        [r"^NS_", r"^FX_", r"^PS_", r"Niagara", r"Cascade"],
    ),
    Unsupported(
        "landscape",
        "Landscape / terrain",
        "Unreal Landscape heightmaps map to Source 2 displacement/heightfield "
        "through a separate pipeline, not this converter.",
        [r"Landscape", r"^LS_", r"Terrain"],
    ),
    Unsupported(
        "virtual_texture",
        "Virtual / runtime virtual textures",
        "RVT and streaming virtual textures are not exportable here. Bake to "
        "standard textures in Unreal first.",
        [r"^RVT_", r"VirtualTexture", r"^VT_"],
    ),
    Unsupported(
        "logic_blueprints",
        "Logic / gameplay blueprints",
        "Only content-assembly blueprints (bundles of meshes with transforms) "
        "map to vsmart. Event graphs and gameplay logic do not convert.",
        [r"^BP_GM_", r"^BP_Ctrl", r"^GM_", r"GameMode", r"Controller", r"^ABP_"],
    ),
    Unsupported(
        "lighting",
        "Lumen lighting / lightmaps",
        "Lighting is not migrated. Light actors and Lumen data must be "
        "re-authored in Hammer.",
        [r"^L_", r"Lightmap", r"Lumen"],
    ),
]


def scan_unsupported(filenames):
    """
    Given an iterable of filenames, return {category_key: [matched names]} for
    every unsupported category that has at least one hit. Used to raise
    scan-time warnings in the console.
    """
    hits = {}
    for name in filenames:
        for cat in UNSUPPORTED:
            if cat.matches(name):
                hits.setdefault(cat.key, []).append(name)
    return hits


def get_unsupported(key):
    for cat in UNSUPPORTED:
        if cat.key == key:
            return cat
    return None
