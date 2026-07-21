# H5T.UnrealBridge

A small .NET 10 console app that wraps [CUE4Parse](https://github.com/FabianFG/CUE4Parse)
and exposes it as a JSON-emitting CLI. The Unreal Converter (Python side,
`src/forms/unreal_converter/`) shells out to this bridge to read Unreal Engine
`.uasset` / `.umap` files directly — **no Unreal install required**.

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

For distribution, `dotnet publish` the output and copy the DLLs into
`src/external/` so H5T's existing pythonnet/coreclr setup can locate them, or
invoke the DLL via `dotnet` as a subprocess.

## Usage

```
dotnet H5T.UnrealBridge.dll info <contentDir>
dotnet H5T.UnrealBridge.dll list <contentDir> <substring>
dotnet H5T.UnrealBridge.dll dump <contentDir> <objectPath>
```

* `<contentDir>` — the UE project's `Content` folder.
* `<objectPath>` — package path without extension, e.g.
  `FireWatchTower/Blueprints/BP_Fence01`.
* `dump` prints all exports as JSON (the raw property tree). Planned normalized
  commands: `dump-scene`, `dump-blueprint`, `dump-material`.
