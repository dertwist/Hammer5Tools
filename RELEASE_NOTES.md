## Automation

* Added CLI and MCP modes to `Hammer5ToolsGUI.exe`, so scripts and AI agents can use Hammer5Tools without the GUI.
* Available operations: read and edit Source 2 formats, compile assets, validate an addon, resolve dependencies, find unused assets, and search the game archives. Editing commands support `--dry-run`.
* Maps can now be read in detail: entities by class with their properties, brush meshes, model placements, and SmartProp placements with the variable overrides the map applied. Decals, paths, prefab instances and entity I/O connections are reachable too.
* Entity classes are described from the game's own definitions, including every keyvalue and its help text.
* SmartProps can be edited one node at a time instead of rewritten, and checked for the mistakes that make a prop silently render nothing, such as division that can produce a NaN or a stretched end cap. A whole folder can be checked in one pass.
* Added blockout map generation from `prop_static` boxes.
* Reads return a summary by default and can address a single value, so inspecting a large asset no longer means loading all of it.
* Setup instructions are in [MCP_SETUP.md](MCP_SETUP.md), and the built-in guides cover authoring conventions.

## Unreal Porter

* Added a Nanite option, off by default, which exports Nanite meshes at full density instead of Unreal's low-poly fallback mesh. It is much slower and produces far larger files, so turn it on per project when you need the detail.
* Added asset path scoping, so you can port part of a project, and exported maps now keep their folder structure.
* Added an option to compile ported assets with resourcecompiler.
* Added a maximum texture size setting with power-of-two presets.
* Material mapping now reads Unreal's own slot table instead of guessing from FBX material names, and supports UE4 material arrays and textures wired directly into a material graph.
* Improved shader seeding for water, translucent and packed-mask materials, and an improved seeder now updates its own earlier guesses while keeping your manual choices.
* The export console now shows progress and a summary instead of the full engine log.
* Faster material scans, a virtualized material list with search and filters, and no more full project rescan on every export.
* The Materials tab now opens by default.
* Fixed assets being skipped during export when their names did not match a known prefix.
* Fixed conversion failures being reported unclearly.
* Fixed a crash in CUE4Parse during asset extraction.

## Sound Event Editor

* Fixed KV3 files saved with a UTF-8 BOM failing to load, such as `.vsndevts` files written by the Source 2 tools.
* Fixed the wave selection ignoring the current theme when hovered.

## Git Sync

* Synchronizing when you are only ahead of the remote no longer stashes unticked changes.
* Added recovery if a stash fails partway through.

## General

* Update downloads now show progress inside the update dialog, and an Update button appears in the header when a new version is available.
