# Unreal bridge

Wraps [CUE4Parse](https://github.com/FabianFG/CUE4Parse) and exposes it through
the same `[UnmanagedCallersOnly]` native ABI as the rest of `Hammer5Tools.Core`
(see `UnrealBridgeApi.cs`; the CUE4Parse-facing logic itself is
`Format/Unreal/UnrealBridgeProgram.cs`). The Unreal Converter (Python side,
`Hammer5ToolsGUI/gui/forms/unreal_porter/bridge_client.py`) calls it in-process
through `core/native.py`/`bridge/core.py` — no subprocess, no
separate `.NET` runtime invocation — to read Unreal Engine `.uasset` / `.umap`
files directly. **No Unreal install required.**

## What works (validated against an uncooked UE 5.7 project)

CUE4Parse reads UObject **property data** out of loose, uncooked editor assets,
which is exactly the "entity" data the converter needs:

| Unreal source            | Readable? | Target  |
|--------------------------|-----------|---------|
| Blueprints (SCS nodes)   | ✅ yes    | vsmart  |
| Maps (actors + transforms)| ✅ yes   | vmap    |
| Material instances (params)| ✅ yes  | vmat    |
| Static mesh **geometry** | ❌ no*    | vmdl    |
| Texture **pixels**       | ❌ no*    | vtex    |

\* Uncooked assets store only editor source data (`StaticMeshDescriptionBulkData`,
`FbxStaticMeshImportData`) — the cooked GPU render buffers / mip chains are
generated at cook time and are not present. Mesh/texture **references and material
assignments** are still readable; the raw geometry/pixels need a UE-side export
or a cooked build.

## Build

Part of the single `Hammer5Tools.Core` project — see the repo root's build
instructions (`makefile.py`'s `build_libraries()`). CUE4Parse is a required
dependency for a full build/publish (see `Hammer5Tools.Core.csproj`'s
`CUE4ParsePath`-conditioned `ItemGroup`s):

1. Install the .NET 10 SDK.
2. Clone CUE4Parse somewhere and apply the NativeAOT patch:
   ```
   git clone --depth 1 https://github.com/FabianFG/CUE4Parse.git
   git -C CUE4Parse apply <path-to-Hammer5Tools>/Hammer5ToolsCore/external/cue4parse_nativeaot.patch
   ```
3. Point `CUE4ParsePath` (an MSBuild property, or the `CUE4ParsePathEnv`
   environment variable) at the clone. `CUE4PARSE_SKIP_NATIVE=true` skips
   CUE4Parse's C++ Oodle natives — not needed for loose/uncooked assets, and
   it avoids a flaky CMake step. Both release CI workflows
   (`.github/workflows/*-release.yml`) set this up automatically before
   calling `python makefile.py --build-all`.

## Commands

Each is a JSON-in/JSON-out native entry point (`h5t_unreal_*`), called through
`CoreBridge.unreal_*` — see `core/bridge/core.py`. All take a
`contentDir` (the UE project's `Content` folder) plus a command-specific field:

* `info` — project stats (file counts, sample paths).
* `list` — every mounted path containing a substring (case-insensitive).
* `dump` — raw JSON of every export in a package (the full property tree).
* `iter_refs` — every object reference in a package (mesh material slots,
  material textures, component meshes, parent materials, etc.), flat and
  deduplicated. Unlike `dump`, it never serialises render data, so it is safe
  and complete for StaticMeshes whose material slots would otherwise
  serialise as null.
* `dump_scene`, `dump_blueprint`, `dump_material` — normalized, typed
  extraction for maps/Blueprints/materials respectively.
* `export_landscape` — bakes a map's first landscape actor to an OBJ mesh
  (optionally heightmap/weightmap PNGs too).
