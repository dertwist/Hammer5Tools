# Hammer5Tools Automation (CLI & Core DLL)

`Hammer5ToolsGUI.exe` hosts both the desktop GUI and the headless `cli` mode,
while `Hammer5Tools.Core.dll` exposes the underlying Source 2, Unreal, VMAP,
SmartProp, and compilation engines over a NativeAOT C ABI.

---

## 1. CLI Mode

Headless `cli` dispatch happens at the very top of `Hammer5ToolsGUI/gui/main.py`
before Qt, OpenGL, COM, or the single-instance GUI lock are initialized. Agents
can run CLI commands **even while the Hammer5Tools GUI is open**.

- **Installed build**: invoke `app\Hammer5ToolsGUI.exe cli ...` (not `Hammer5Tools.exe`).
- **Source checkout**: invoke `.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli ...`.

### Common Commands

```powershell
# List every registered tool and its JSON input schema
Hammer5ToolsGUI.exe cli capabilities

# Check Core ABI, CS2 path, and configured addon
Hammer5ToolsGUI.exe cli core-status

# Generic tool invocation (supports every registered automation tool)
Hammer5ToolsGUI.exe cli call hammer5tools.vmat_edit --args '{"path":"C:/addon/materials/surface.vmat","set_slots":{"TextureColor":"materials/new_color.png"},"dry_run":true}'

# Format readers
Hammer5ToolsGUI.exe cli vmdl-read C:\addon\models\prop.vmdl
Hammer5ToolsGUI.exe cli vmat-read C:\addon\materials\surface.vmat
Hammer5ToolsGUI.exe cli vtex-read C:\addon\materials\color.vtex
Hammer5ToolsGUI.exe cli vsmart-read C:\addon\smartprops\fence.vsmart
Hammer5ToolsGUI.exe cli vsmart-eval C:\addon\smartprops\fence.vsmart
Hammer5ToolsGUI.exe cli vdata-read C:\addon\scripts\weapons.vdata
Hammer5ToolsGUI.exe cli vsnap-read C:\addon\particles\cloud.vsnap

# VMAP & Unreal
Hammer5ToolsGUI.exe cli vmap-references C:\addon\maps\example.vmap
Hammer5ToolsGUI.exe cli vmap-rewrite C:\addon\maps\example.vmap '{"models/old.vmdl":"models/new.vmdl"}' --dry-run
Hammer5ToolsGUI.exe cli unreal-info C:\UEProject\Content
Hammer5ToolsGUI.exe cli unreal-list C:\UEProject\Content --substring Brick
Hammer5ToolsGUI.exe cli unreal-references C:\UEProject\Content /Game/Props/Chair

# Compilation, validation, dependencies, VPK
Hammer5ToolsGUI.exe cli compile C:\addon\models\prop.vmdl --background
Hammer5ToolsGUI.exe cli validate --addon example
Hammer5ToolsGUI.exe cli find-unused C:\addon\maps\example.vmap
Hammer5ToolsGUI.exe cli resolve-deps C:\addon\models\prop.vmdl
Hammer5ToolsGUI.exe cli vpk-search brick --ext vmat_c
```

### Path Resolution, Safety & Compilation Jobs

- **Path confinement**: Relative asset paths resolve against explicit `addon_root`
  or the configured addon at request time, and cannot escape that root through
  junctions. Absolute paths remain supported.
- **Dry runs**: Modifying tools support `"dry_run": true` (`--dry-run`) to stage
  and validate edits without modifying files on disk. Writes replace files
  atomically and retain backups.
- **Background compilation**: `compile_asset` (with `background: true`) and
  `compile_assets` return a `job_id`. Poll with `hammer5tools.compile_job_status`,
  read output with `hammer5tools.compile_log`, or cancel with
  `hammer5tools.compile_job_cancel`.
- **Pagination**: Reference and listing tools default to 50 rows; inspect
  `total` and `truncated` and pass `limit` / `offset` to page through results.

---

## 2. Direct DLL Usage (`Hammer5Tools.Core.dll`)

For batching hundreds of operations or calling Core APIs directly from Python,
agents can load `Hammer5Tools.Core.dll` via `ctypes` (no .NET runtime or
`pythonnet` required).

### Option A: Using `CoreBridge` (Source Checkout)

```python
import sys
sys.path.insert(0, r"E:\CG\Projects\Other\Hammer5Tools\Hammer5ToolsGUI")

from core.bridge import CoreBridge

bridge = CoreBridge()
print(bridge.core_status())
```

### Option B: Standalone `ctypes` Script (Installed Build or Any Python)

In an installed build, `Hammer5Tools.Core.dll` and `libSkiaSharp.dll` live under
`app\runtime\core\` (or `Hammer5ToolsGUI\core\` in a source checkout).

```python
import ctypes
import json
import os
from pathlib import Path

core_dir = Path(r"C:\path\to\Hammer5Tools\app\runtime\core")
os.add_dll_directory(str(core_dir))

# Preload libSkiaSharp.dll if present so NativeAOT P/Invoke resolves it cleanly
skia = core_dir / "libSkiaSharp.dll"
if skia.is_file():
    ctypes.CDLL(str(skia))

lib = ctypes.CDLL(str(core_dir / "Hammer5Tools.Core.dll"))

# Verify ABI version (currently 2)
lib.h5t_core_abi_version.argtypes = []
lib.h5t_core_abi_version.restype = ctypes.c_int
assert lib.h5t_core_abi_version() == 2
```

### Additive JSON Exports (`AutomationApi.cs`)

All `h5t_*_json` automation exports share the same `cdecl` signature:
`(const uint8* reqPtr, int reqLen, void** outPtr, int* outLen) -> int`:

- `h5t_resolve_asset_path_json`
- `h5t_model_bounds_json`
- `h5t_texture_inspect_json`, `h5t_texture_split_json`, `h5t_texture_pack_json`
- `h5t_vmap_insert_json`, `h5t_vmap_nodes_json`, `h5t_vmap_transform_json`, `h5t_vmap_group_json`, `h5t_vmap_zoo_json`
- `h5t_vmat_author_json`, `h5t_vmat_batch_json`
- `h5t_vmdl_author_json`, `h5t_vmdl_batch_json`
- `h5t_compile_assets_json`, `h5t_compile_job_status_json`, `h5t_compile_job_cancel_json`, `h5t_compile_log_json`

Always free returned buffers using the Core free export (see
`Hammer5ToolsGUI/core/native.py` for the reference wrapper `SmartPropNativeClient`).

---

## 3. Source 2 Formats & Built-in Guides

Deep format documentation is bundled inside the app and accessible via:

```powershell
Hammer5ToolsGUI.exe cli call hammer5tools.guide --args '{"topic":"<topic>"}'
```

| Format | Extension | Purpose & Key Notes |
| --- | --- | --- |
| Map | `.vmap` | DMX map file. Never hand-author `CMapMesh`; use `vmap_write_blockout` / `vmap_insert` / `vmap_nodes` / `vmap_transform` / `vmap_group`. |
| Model | `.vmdl` | KV3 model source. Use `vmdl_read`, `vmdl_write`, `vmdl_edit`, `vmdl_batch`, `model_bounds`. |
| Material | `.vmat` | KV3 material source. Use `vmat_read`, `vmat_write`, `vmat_edit`, `vmat_batch`. |
| Texture | `.vtex` | KV3 texture metadata. Use `vtex_read`, `vtex_write`, `vtex_edit`, `texture_inspect`, `texture_split`, `texture_pack`. |
| SmartProp | `.vsmart` | KV3 procedural prop. Prefer `vsmart_patch` for node edits; verify with `vsmart_lint` and `vsmart_evaluate`. |
| GameData | `.vdata` | KV3 structured tables. Use `vdata_read`, `vdata_write`, `vdata_edit`. |
| Point Cloud | `.vsnap` | Particle/point snap data. Use `vsnap_read`, `vsnap_write`, `vsnap_generate`, `vsnap_edit`. |
| Archive | `.vpk` | Compiled game archives. Search/extract stock assets with `vpk_search` and `vpk_extract`. |

See `SKILL.md` for the full list of 13 `hammer5tools.guide` topics and agent working rules.
