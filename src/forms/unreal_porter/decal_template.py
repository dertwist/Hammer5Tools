"""
Geometry template for a Source 2 static overlay decal (CMapStaticOverlay).

Reverse-engineered from a real Hammer-authored decal in a shipped CS2 addon
(decaltest.vmap, provided for this purpose) — CMapStaticOverlay is not a
simple point entity but a native half-edge polygon-mesh primitive, matching
csgo_static_overlay.vfx. The reference decal is a single 256x256 axis-aligned
quad; that topology is bundled here as constants so every UE decal actor is
placed by cloning this exact geometry and only changing origin/angles/scales
and the material — never re-deriving mesh topology per instance (the
highest-risk part of getting a novel decal size/shape topologically right).

Half-edge layout (4 verts, 4 edges, 1 face) — do not hand-edit without
re-verifying against a real Hammer-saved CMapStaticOverlay.
"""

# Local-space quad corners (Hammer/Source units), Z is a small offset off the
# projection plane exactly as authored by Hammer's Decal tool.
POSITIONS = [
    (-128.0, -128.0, 34.0),
    (128.0, -128.0, 34.0),
    (128.0, 128.0, 34.0),
    (-128.0, 128.0, 34.0),
]

UVS = [(1.0, 1.0), (0.0, 0.0), (1.0, 0.0), (0.0, 0.0),
       (0.0, 0.0), (0.0, 0.0), (0.0, 1.0), (0.0, 0.0)]
NORMALS = [(0.0, 0.0, 1.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0, 0.0),
           (0.0, 0.0, 1.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0, 0.0)]
TANGENTS = [(1.0, 0.0, 0.0, -1.0), (0.0, 0.0, 0.0, 0.0), (1.0, 0.0, 0.0, -1.0), (0.0, 0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0, -1.0), (0.0, 0.0, 0.0, 0.0), (1.0, 0.0, 0.0, -1.0), (0.0, 0.0, 0.0, 0.0)]
EDGE_FLAGS = [0, 0, 0, 0]

TEXTURE_SCALE = (0.25, 0.25)
TEXTURE_AXIS_U = (1.0, 0.0, 0.0, 0.0)
TEXTURE_AXIS_V = (0.0, -1.0, 0.0, 512.0)

VERTEX_EDGE_INDICES = [0, 2, 4, 6]
VERTEX_DATA_INDICES = [0, 1, 2, 3]
EDGE_VERTEX_INDICES = [1, 0, 2, 1, 3, 2, 0, 3]
EDGE_OPPOSITE_INDICES = [1, 0, 3, 2, 5, 4, 7, 6]
EDGE_NEXT_INDICES = [2, 7, 4, 1, 6, 3, 0, 5]
EDGE_FACE_INDICES = [0, -1, 0, -1, 0, -1, 0, -1]
EDGE_DATA_INDICES = [0, 0, 1, 1, 2, 2, 3, 3]
EDGE_VERTEX_DATA_INDICES = [0, 1, 2, 3, 4, 5, 6, 7]
FACE_EDGE_INDICES = [6]
FACE_DATA_INDICES = [0]

# Scalar defaults captured from the same reference decal.
DEFAULTS = {
    "disableShadows": 0,
    "bakelighting": True,
    "cubeMapName": "",
    "emissiveLightingEnabled": True,
    "emissiveLightingBoost": 1.0,
    "lightingDummy": False,
    "bakeLightDoubleSided": False,
    "visexclude": False,
    "disablemerging": False,
    "renderwithdynamic": False,
    "renderToCubemaps": True,
    "keep_vertices": False,
    "fademindist": -1.0,
    "fademaxdist": 0.0,
    "disableHeightDisplacement": False,
    "smoothingAngle": 40.0,
    "renderAmt": 255,
    "physicsType": "default",
    "physicsCollisionProperty": "",
    "physicsGroup": "",
    "physicsInteractsAs": "",
    "physicsInteractsWith": "",
    "physicsInteractsExclude": "",
    "physicsSimplificationOverride": False,
    "physicsSimplificationError": 0.0,
    "renderOrder": 0,
    "disabledInLowQuality": False,
    "useBaseNormals": False,
    "projectionFar": 128.0,
    "projectOnBackFaces": False,
    "backFacingAngle": 90.0,
    "projectionMode": 0,
    "randomSeed": 0,
    "customVisGroup": "",
}
