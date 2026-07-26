# de_firewatch — asset organization plan

Addon: `E:\SteamLibrary\...\csgo_addons\de_firewatch`
Pack: `firewatchtower` (UE5 port, commits `d438177` assetpack + `5e0ddd1` materials import)

---

## 1. What's actually there

| | count | notes |
|---|---|---|
| `models/firewatchtower/**` | 259 vmdl + 259 fbx | 118 MB. All 259 are placed in maps/smartprops — nothing is dead. |
| `materials/firewatchtower/**` | 313 vmat, 899 tga, 1 png | **9.5 GB** |
| vmat shaders | 313 × `csgo_environment.vfx` | one exception: `mi_fence_net.vmat` |

### The core problem: two overlapping imports

`d438177` and `5e0ddd1` each imported the same source pack under a different convention, and neither replaced the other.

| | Pass A (`d438177`) | Pass B (`5e0ddd1`) |
|---|---|---|
| vmat names | `mi_bush.vmat` | `bush.vmat` |
| texture names | `t_bush_b` / `t_bush_n` / `t_bush_orm_{ao,rough,metal}` | `bush_{color,normal,rough,metal,ao}` |
| wired to vmdls | **yes — 118 live** | **no — 152 orphans** |
| PBR completeness | gaps (several `_b` never imported) | complete sets |
| scalar sanity | broken (roughness up to 16.19) | sane |

**276 texture pairs are byte-identical between the two sets.** 373 redundant files = **3.76 GB**.
Another **295 MB / 86 files** are flat constant fills (43 all-black, 27 all-white, 8 flat normals) that should be vmat scalars, not 2K TGAs.

→ **~4.0 GB (42%) is reclaimable before any real work.**

### Material defects (the "wrong textures / no alphas" you hit)

1. **No alpha anywhere.** 34 TGAs carry real alpha data. 40 materials use one as `TextureColor1` with **no `F_ALPHA_TEST`**. Every bush, grass, leaf, fern, net and grating renders as an opaque quad.
   Only `mi_fence_net.vmat` was hand-fixed — and its `TextureTranslucency1` points at `net_color_alpha.png` (a PNG, not the project's TGA convention).
2. **Zero `F_RENDER_BACKFACES`.** All foliage cards are single-sided.
3. **Cross-wired textures.** 88 live vmats reference a texture belonging to a different asset. *Most are legitimate* (UE material instances sharing a trimsheet/atlas — `mi_barrel` → `t_propset_02_*` is correct). ~32 have a plausible correctly-named alternative and need eyeballing. Two are unambiguous:
   - `mi_cloth.vmat` → `TextureColor1 = t_metal_b.tga` (should be `cloth_color.tga`)
   - `mi_car_02.vmat` → whole set points at `t_car_01_*` (should be `car_02_*`)
   - `mi_fence_net.vmat` → `TextureColor1 = t_rust_b.tga`; `t_net_b` was never imported, but `net_color.tga` exists **and carries the alpha**.
4. **20 vmats have roughness scalars > 1** (up to 16.19) — a bad UE→S2 param conversion. All foliage/terrain.
5. **32 vmats have no normal map.**

---

## 2. Target layout

```
materials/firewatch/thirdparty/<category>/<name>_{color,normal,rough,metal,ao,trans}.tga
                                          /<name>.vmat
models/firewatch/thirdparty/<category>/<name>.vmdl + .fbx
```

Naming convention: **Pass B's** (`_color/_normal/_rough/_metal/_ao`) — it matches what H5T's own
`src/forms/unreal_converter/vmat_writer.py` emits, so future re-imports land in the same shape.
Drop the `mi_` / `t_` prefixes.

### Categories (auto-derived from names, 251/259 classified)

| category | n | category | n |
|---|---|---|---|
| `nature/foliage` | 32 | `props/small` | 29 |
| `nature/trees` | 8 | `props/containers` | 19 |
| `nature/rocks` | 20 | `props/debris` | 15 |
| `nature/terrain` | 9 | `props/furniture` | 14 |
| `structures/tower` | 14 | `props/lighting` | 3 |
| `structures/buildings` | 9 | `construction/wood` | 34 |
| `structures/fences` | 10 | `construction/metal` | 6 |
| `structures/walls_windows` | 7 | `vehicles` | 16 |
| `infra` | 6 | *unclassified* | 8 (`tweak1..7`) |

Two classifier fixes needed before running: `carboard1..5` currently match `vehicles` on the substring
"car" (they're cardboard → `props/debris`), and `tweak*` need a manual call.

---

## 3. Tooling — what exists, what's missing

### `src/forms/asset_manager/` — move + reference fixup
`ReferenceUpdater` + `MoveWorker` already do exactly this job: move a file, then rewrite every
reference to it across `.vmdl/.vsmart/.vmat/.vmap/...`, including **binary** vmaps via Datamodel.NET.
Two blockers before it can be pointed at ~1500 files:

- **B1 — it's O(moves × addon).** [`update_references()`](src/forms/asset_manager/reference_updater.py:128) walks the entire addon and
  load/saves the 12 MB `de_firewatch.vmap` **once per moved file**. 1500 moves is not going to finish.
  Fix: add a batch entry point taking `dict[old_rel, new_rel]` and doing one walk, one vmap load/save.
- **B2 — it silently drops the vmap prefix block.** [`_update_vmap_references()`](src/forms/asset_manager/reference_updater.py:104) saves via
  Datamodel.NET, whose binary writer discards the DMX prefix-attribute block (map thumbnail +
  asset-reference cache) — this is documented in [`src/gitvmapmerge.py:27`](src/gitvmapmerge.py:27), which already carries the
  fix: `_splice_prefix()` at [`src/gitvmapmerge.py:109`](src/gitvmapmerge.py:109). `ReferenceUpdater` just doesn't call it.

### `src/forms/unreal_converter/texture_utils.py` — texture ops
Has ORM/RMA/ORH unpacking. **No alpha extraction.** Missing piece is one function:

```python
def extract_alpha(color_path: str, out_path: str) -> str | None:
    """Split the alpha channel of an RGBA color map into its own 8-bit TGA."""
    img = Image.open(color_path)
    if img.mode != "RGBA":
        return None
    a = img.getchannel("A")
    if a.getextrema()[0] == a.getextrema()[1]:
        return None          # constant alpha — nothing to extract
    a.save(out_path)
    return out_path
```

### `src/forms/unreal_converter/vmat_writer.py` — vmat emitter
`write_vmat()` has no alpha-test path. Add an `alpha_test=True` branch emitting the block already
proven working in `mi_fence_net.vmat`:

```
F_ALPHA_TEST 1
TextureTranslucency1 "<...>_trans.tga"
g_flAlphaTestReference "0.500"
g_flAntiAliasedEdgeStrength "1.000"
```
plus `F_RENDER_BACKFACES 1` for foliage.

### `src/forms/cleanup/` — orphan/unused finder, reuse as-is for the delete pass.

---

## 4. Phases

Every phase is one commit, so `git diff` is the review surface and any step reverts cleanly.

### Phase 0 — safety net
Commit current state. Confirm `_bakeresourcecache` / `de_firewatch_bakeresourcecache.vpk` are
gitignored (they're regenerated). Copy `de_firewatch.vmap` aside as ground truth for Phase 2 verification.

### Phase 1 — dedup (no renames yet)
Hash all 927 TGAs. For each of the 296 duplicate groups pick the canonical name (Pass B convention),
repoint every vmat reference to it, delete the rest. **−3.76 GB, −373 files.**
*Verify: zero broken texture refs; `git diff --stat` shows only deletions + vmat text edits.*

### Phase 2 — flatten constants
Replace the 86 flat TGAs with vmat scalars (`TextureMetalness1 "[0 0 0 0]"`) or
`materials/default/default_*.tga`. **−295 MB.**
*Verify: no vmat references a deleted file.*

### Phase 3 — fix materials (the actual quality work)
Ordered by payoff:
1. **Alpha.** Run `extract_alpha` over the 34 alpha-carrying color maps → `<name>_trans.tga`.
   Rewrite the 40 affected vmats with the alpha-test block. Delete `net_color_alpha.png`.
2. **Backfaces.** `F_RENDER_BACKFACES 1` on everything in `nature/foliage` + `nature/trees`.
3. **Scalars.** Clamp the 20 out-of-range roughness values to `[0,1]` — or better, point them at the
   Pass B `_rough.tga` that already exists for each.
4. **Cross-wiring.** Auto-fix the 2 unambiguous ones. Emit the other ~30 as a review table
   (vmat → current texture → candidate) — do **not** auto-rewrite; the shared-trimsheet cases are correct.
5. **Missing normals.** Report the 32; fill from Pass B where a `_normal.tga` exists.

*Verify: compile the pack in Hammer, eyeball `maps/Showcase.vmap`.*

### Phase 4 — prune orphans
Delete the 152 orphan Pass-B vmats **whose textures are now referenced by the surviving vmats**
(they've served their purpose as the texture source). Re-run the reference audit first — anything
still referenced from a vmap stays.

### Phase 5 — the move
Only now, on a deduped and fixed set (~550 textures, ~161 vmats, 259 models instead of ~1500 files):
1. Land the B1 batch fix + B2 prefix-splice fix in `ReferenceUpdater`.
2. Build the full rename map (`old_rel → new_rel`) as a reviewable CSV — categories included.
3. Dry-run: apply the map to a *copy* of the addon, diff the reference audit.
4. Apply. One walk, one vmap rewrite.
5. Delete the empty `materials/firewatchtower` / `models/firewatchtower` trees.

*Verify: re-run the audit — 0 broken refs, 259 vmdls still resolving from `de_firewatch.vmap`,
vmap prefix block byte-identical in size class, map opens in Hammer with no missing-model errors.*

### Phase 6 — regression gate
Re-run the audit script and diff against the Phase-0 baseline. The invariant that must hold:
**the set of (model, resolved material, resolved texture-pixels) triples is unchanged** — only paths moved.

---

## 5. Sequencing rationale

Dedup and fixes come **before** the move on purpose: the move is the expensive, risky,
hard-to-review step, and doing it first would mean moving 4 GB of files we're about to delete and
rewriting references we're about to change again. Fix in place where paths are still familiar,
then move once.

## 6. Open calls for you

1. **`tweak1..7` + `tweak`** (8 models) — what are these? Terrain blend tweaks?
2. **`models/firewatchtower/meshes/merged/`** (4 models: bridges, merged structure, poles) — own
   `merged/` category or distribute into `infra`/`structures`?
3. **`materials/firewatchtower/meshes/`** (29 vmats: car glass, sedan body/interior instances,
   woodenpiles 1-10, `worldgridmaterial`) — these are FBX-embedded material stubs. Fold into
   `vehicles`/`construction/wood`, or keep a `_raw/` bucket?
4. **Alpha-test cutoff** — `0.5` is the `mi_fence_net` value. Foliage often wants lower (`0.33`) for
   thicker cards. Per-category override, or one global value?
5. **`propset_04` / `trimsheet` / `wood_trim` / `metal_base` / `sedan*_seats`** carry alpha but are
   *not* cutout materials (alpha is 0.4–100% mid-range — it's a blend/detail mask, not a shape mask).
   Confirm those get skipped by the alpha pass.
