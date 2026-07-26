# de_firewatch — packed reorganisation plan

Rerun of the organisation pass, with two changes from last time: assets are packed
per-prop instead of split across `models/` and `materials/`, and duplicate
materials collapse onto one generic name.

Numbers below are measured, not estimated — `scratch/r1_plan.py` produces both this
plan's figures and the move map (`r1_map.json`) that executes it, so they cannot drift.

---

## Target layout

```
models/firewatch/<category>/<prop>/     vmdl + fbx + vmat + tga, together
models/firewatch/_shared/<name>/        materials used across props
```

`materials/firewatch/thirdparty/` disappears. Categories keep their current names
(`props/containers`, `nature/foliage`, `structures/buildings`, …).

The layout is already proven in this install: `csgo_addons/de_boreen` ships
`models/boreen/graybox/car_dodge_a/{dodge_a.vmdl, dodge_a.fbx, car_dodge_body.vmat}`
and `models/background/mountains/mountain_generic_01_a/{*.vmdl, *.fbx, *.vmat, Color.png}`.
Nothing in Source 2 requires materials under `materials/` — vtex compiles whatever a
vmat points at.

### Your example, as it actually lands

```
models/firewatch/props/containers/barrel/
    barrel.vmdl
    barrel2.vmdl
    barrel.fbx
    barrel2.fbx
    barrel.vmat          <- mi_barrel + mi_barrel_birght merged
```

**One correction to what I showed you earlier:** there is no `barrel_color.tga` in
that folder. The barrel's colour/normal/rough maps are the `propset_02` atlas, shared
with 6 other props (lrack, rack, drawer, campfire01, campfire02, house). Copying them
into `barrel/` would duplicate 4.2 MB per map — the opposite of what you asked for. So
`barrel.vmat` sits next to `barrel.vmdl` and points at
`models/firewatch/_shared/propset_02/propset_02_color.tga`.

Props with their own textures do get the fully self-contained folder:

```
models/firewatch/nature/foliage/bush/
    bush.vmdl  bush.fbx  bush.vmat
    bush_color.tga  bush_normal.tga  bush_trans.tga
```

### What forces a material into `_shared/`

Either of:
- used by more than 2 models, or
- used by models in more than one category.

The second rule matters. Without it a rope material glued `firelookouttower.vmdl` into
`props/debris/rope01/`, and a road material pulled `houseroad.vmdl` into `barrel/`.
With it, all 247 pack folders hold at most 4 models, and the 10 multi-model folders are
all genuine variant sets:

| folder | models |
|---|---|
| `structures/buildings/house` | garage01, garage02, house, repairshop |
| `props/containers/barrel` | barrel, barrel2 |
| `props/small/slipper` | slipper_l, slipper_r |
| `props/containers/ashtray` | ashtray_01, ashtray_02 |
| `nature/rocks/big_stone_3` | big_stone_3, big_stone_4 |
| `nature/foliage/driedgroundalpha` | driedgroundalpha01, driedgroundalpha02 |
| `infra/polesmerged` | electricpole, polesmerged |
| `props/furniture/chair` | chair, table |
| `props/containers/can_3` | can_l, can_s |
| `vehicles/cart` | cart, tiresmall |

---

## Scope

**In:** everything under `models/firewatch/thirdparty/` and
`materials/firewatch/thirdparty/` — 259 vmdl, 259 fbx, 167 vmat, 587 tga, 115 `.txt`
vtex sidecars.

**Untouched:** `models/dev`, `models/engine`, `models/props_survival`,
`materials/dev`, `materials/radgen`, `materials/models/**`, `materials/firewatch/sky`,
`materials/firewatch/thirdparty/decals`, `models/1.vmdl`, `models/2.vmdl`.

**Frozen — yours, not touched at all:** `rock_01.vmat`, `rock_02.vmat`,
`rock_03.vmat`, `rock_04.vmat` and the 19 tga files they reference. They stay at
`materials/firewatch/thirdparty/nature/rocks/` byte-for-byte, so their paths in the
vmaps stay valid and nothing about them changes. The 17 rock models that use them do
move; their remaps will point back at the unchanged material paths.

Say the word if you'd rather they moved to a clean path too — it's a pure path change
with identical contents, but "don't touch" reads as leave them alone, so that's the
default.

Note `mi_rock_1/2/3.vmat` are *not* yours — they're the unused imported rocks, 0 models,
unreachable from any map. They're in the delete list. `rock_3_*.tga` (five files,
byte-identical to your `rock_03_*.tga`) is also an unreferenced leftover; I've left it
out of the delete list because the name sits too close to yours. Your call.

---

## Material merges: 167 → 111

33 merged away, 23 deleted. Every merge below is between materials pointing at an
**identical texture set** — same colour, normal, rough, metal, ao. You picked
"collapse tint variants too", so groups differing only in `g_vColorTint` collapse as
well and keep the brightest tint.

| new name | ← merged from | models |
|---|---|---|
| `_shared/wood_damaged` | mi_woodenpiles, mi_box, mi_houseplanks, mi_oldplankwood, mi_repairshop_wood, woodenpiles_1…10 | 15 → 1 |
| `_shared/wood_damaged_trim` | mi_table01, mi_table05, mi_woodenpiles1, mi_cliffhanger_wood, mi_petrolrefillstore | 5 → 1 |
| `_shared/metal_painted` | mi_house_leg, mi_fence_metal, mi_house_base, mi_oldplank_metal | 4 → 1 |
| `_shared/grass_atlas` | mi_flower, mi_deadgrass, mi_drygrass, mi_grass01 | 4 → 1 |
| `_shared/leaf_atlas` | mi_driedleaves, mi_groundplant01, mi_cornustreeleaves | 3 → 1 |
| `_shared/net` | mi_fence_net, mi_tileablenet | 2 → 1 |
| `_shared/metal_roof` | mi_house_metal, mi_house_roof | 2 → 1 |
| `_shared/wood_trim` | mi_table04, mi_woodenplanks_ | 2 → 1 |
| **`props/containers/barrel/barrel`** | **mi_barrel, mi_barrel_birght** | **2 → 1** |
| `props/containers/cup02/propset_small` | mi_cup_colorvar, mi_propset06_bucket | 2 → 1 |
| `nature/rocks/big_stone_3/cliff` | mi_medium_clifs, mi_big_clifs | 2 → 1 |
| `structures/buildings/house/trim_wood` | mi_trimbrownwood, mi_trimwhitewood | 2 → 1 |
| `vehicles/cart/suv_under` | m_suv_under, mi_tire_cart | 2 → 1 |

The names in column 1 are hand-picked. Left to itself the merge keeps whichever name
had the most models, which reads badly at scale — the generic wood would be called
`table01` and the generic metal `house_leg`. Names are a single dict in `r1_plan.py`;
change any you dislike before the move runs.

### Two things to look at before you approve this

**1. `wood_damaged` is a 15-way merge.** It makes every damaged-wood surface in the
map the same material: woodpiles, crates (`mi_box`), house siding (`mi_houseplanks`),
the repairshop (`mi_repairshop_wood`), old planks. The four source tints were
1.0 / 0.93 / 0.77 / 0.68, so the darker surfaces get visibly lighter. That is what
"combine them into a single generic material" means, and it's the single biggest
reduction in the plan — but it's also the one change you're most likely to look at
in-engine and want back. Reverting to 4 materials, one per tint, is a one-line change.

**2. 10 of those 15 are a live bug, not a duplicate.** `woodpile.vmdl` has ten
material slots, `woodenpiles_1` through `woodenpiles_10`, and **all ten point at
`materials/default/`** — the woodpile renders untextured grey right now, while the
correct wood material sits next to it. The merge fixes that as a side effect.

### Deletes (23 materials)

18 vehicle placeholders with all-default textures and no model (`glass_inst_8/9/13/18`,
`sedan02_body_inst_6/10/14/21`, `sedan02_interior_inst_7/11/15/17`, `lights_02_16/20`,
`car_glass`, `mi_glass_inst`, `mi_grill01_inst`, `wheelset_01_inst_2`,
`mi_sedan02_body_inst`) plus `mi_rock_1/2/3` and `mi_big_clifs`. All are unreachable
from any vmdl, vmap or vsmart.

### Still unwired afterwards (8 materials)

`basematerial`, `mi_glass02_inst`, `glass02`, `mi_wire_02`, `mi_grating`,
`mi_overview`, `worldgridmaterial`, `sedan02_body` — every texture slot is
`materials/default/`. They're referenced by real models, so they can't be deleted, but
no texture exists to wire them to. They need authoring, or the models need
reassigning. Out of scope here; listing them so they're not a surprise.

---

## Textures: 587 → 362 relocated

| | count | |
|---|---|---|
| relocated with their material | 362 | renamed to `<material>_<slot>.tga` |
| frozen (`rock_01..04`) | 19 | untouched |
| referenced by nothing | 209 | 1.99 GB — 187 already in `_library/` |

The 115 `.txt` sidecars are vtex compile settings for the tga beside them and move with
it. Missing this would silently reset compression settings on every affected texture.

`_library/` stays. It is not a graveyard — live materials point into it
(`mi_barrel` reads `_library/propset_02_color.tga`), which is also why the last pass's
reachability numbers looked worse than they were.

Two loose ends found while measuring: `_library/roada_color.tga` and
`_shared/t_roada_a.tga` are byte-identical at 67 MB each, and one vmat references a
`.png` (`_library/propset_02_mask.png`) where every other tint mask is a tga.

---

## Reference rewriting: 1333 references

| file | refs | unique |
|---|---|---|
| `maps/overview.vmap` | 652 | 218 |
| `maps/showcase.vmap` | 408 | 144 |
| `smartprops/woodpile.vsmart` | 129 | 9 |
| `smartprops/firetower.vsmart` | 32 | 16 |
| `smartprops/repairshop.vsmart` | 30 | 17 |
| `smartprops/fence01–04.vsmart` | 73 | 30 |
| `electricpole`, `firebarrel`, `petrolrefillstore`, `woodenpile_4` | 9 | 7 |

Plus the 259 vmdl remaps and the vmat→vmat references.

Both vmaps have grown a lot since the last pass (overview 30 MB, showcase 14 MB) —
that's your work, and the rewrite preserves it: `ReferenceUpdater` splices the DMX
prefix block (thumbnail + asset cache) back after Datamodel.NET rewrites the body.
That's covered by a round-trip test in `dev/test_reference_updater.py`.

**CS2 is not running right now** — confirmed. Last time a live Hammer session
overwrote these files three times from its stale in-memory state. Keep it closed until
the move finishes.

`de_firewatch.vmap` still references the pack zero times. All placements live in
`overview.vmap` and `showcase.vmap`.

---

## Phases

Each is one commit on `main`, so any phase can be reverted alone.

| # | phase | effect |
|---|---|---|
| 0 | verify tree clean, snapshot the pre-move audit | no change |
| 1 | merge the 33 duplicate materials, rewrite every reference to a merged material | 167 → 134 vmat |
| 2 | delete the 23 dead materials (after asserting zero live references) | 134 → 111 vmat |
| 3 | move + rename into `models/firewatch/<cat>/<prop>/`, tga + `.txt` sidecars with them | 247 folders |
| 4 | rewrite the 1333 references in 2 vmaps + 11 vsmarts + 259 vmdl remaps, one batch pass | paths valid |
| 5 | delete the now-empty `materials/firewatch/thirdparty/` (minus frozen rocks) | tree clean |
| 6 | regression gate: model count in = out, every material reachable, zero broken texture refs | verify |

Phase 6 is the same gate as last time and it is the phase that matters. Last run I
deleted 277 textures whose references had silently failed to rewrite because the line
regex was anchored `[ \t]*$` against CRLF files. `lib.assert_no_refs()` now aborts
before any deletion if a single live reference remains, and phase 2 and 5 both call it.

## Follow-up outside this plan

`vmdl_writer.py:240,256` and `scene_worker.py:240` derive material paths by string-
replacing `models/` with `materials/`. Future Unreal imports will therefore keep landing
split, not packed. Worth changing if this layout is what you want going forward — small
diff, but it's a code change to H5T rather than a data change to the addon, so it isn't
part of these phases.
