# Unreal bridge

> Structural note: this source now lives at `Format/Unreal/` inside the single
> `Hammer5Tools.Core` project instead of a standalone `UnrealBridge` project.
> The build/usage instructions below still describe the pre-merge, still-current
> `dotnet <dll> <command>` subprocess CLI — `bridge_client.py` still shells out
> to it exactly as documented. Converting these commands into
> `[UnmanagedCallersOnly]` ABI entry points (removing the subprocess call
> entirely) is separate, not-yet-started follow-up work; this doc will be
> rewritten again once that lands.

Wraps [CUE4Parse](https://github.com/FabianFG/CUE4Parse) and exposes it as a
JSON-emitting CLI. The Unreal Converter (Python side,
`Hammer5ToolsGUI/gui/forms/unreal_porter/`) shells out to this bridge to read
Unreal Engine `.uasset` / `.umap` files directly — **no Unreal install
required**.

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

1. Install the .NET 10 SDK.
2. Clone CUE4Parse somewhere:
   ```
   git clone --depth 1 https://github.com/FabianFG/CUE4Parse.git
   ```
3. Build, pointing at the clone. `CUE4PARSE_SKIP_NATIVE=true` skips CUE4Parse's
   C++ Oodle natives — not needed for loose/uncooked assets, and it avoids a
   flaky CMake step:
   ```
   dotnet build -c Release -p:CUE4ParsePath=/abs/path/to/CUE4Parse -p:CUE4PARSE_SKIP_NATIVE=true
   ```
   Output: `bin/Release/net10.0/H5T.UnrealBridge.dll` (+ dependencies).

For distribution, publish straight into `tools/unreal_bridge/publish/` — that's
where `bridge_client.py` looks for it (both unpackaged and inside the frozen
PyInstaller build, via `makefile.py`), and where CI (`.github/workflows/*-release.yml`)
puts it after building CUE4Parse fresh each run:
```
dotnet publish tools/unreal_bridge/UnrealBridge.csproj -c Release -r win-x64 --self-contained false -p:CUE4ParsePath=/abs/path/to/CUE4Parse -p:CUE4PARSE_SKIP_NATIVE=true -o tools/unreal_bridge/publish
```
`-r win-x64 --self-contained false` trims the `runtimes/` folder down from
~40MB (every RID NuGet ships) to just win-x64, still running on H5T's bundled
.NET runtime via `dotnet H5T.UnrealBridge.dll`.

## Usage

```
dotnet H5T.UnrealBridge.dll info <contentDir>
dotnet H5T.UnrealBridge.dll list <contentDir> <substring>
dotnet H5T.UnrealBridge.dll dump <contentDir> <objectPath>
dotnet H5T.UnrealBridge.dll iter-refs <contentDir> <objectPath>
```

* `<contentDir>` — the UE project's `Content` folder.
* `<objectPath>` — package path without extension, e.g.
  `FireWatchTower/Blueprints/BP_Fence01`.
* `dump` prints all exports as JSON (the raw property tree).
* `iter-refs` resolves every object reference in a package (mesh material slots,
  material textures, component meshes, parent materials, etc.) to a flat JSON
  list of object paths. Unlike `dump`, it never serialises render data, so it is
  safe and complete for StaticMeshes whose material slots would otherwise
  serialise as null.
* Normalized commands for specific export types: `dump-scene`, `dump-blueprint`,
  `dump-material`.
