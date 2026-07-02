## 🔧 Main App
* Cleanup Addon: Added support for scanning `.dmx` and `.fbx` source mesh files for material (`.vmat`/`.vmt`) references to prevent them from being incorrectly deleted as junk.
* Cleanup Addon: Upgraded the `.vmdl` model parser to generically scan all asset reference patterns (including `source_filename`, `model`, `from`) and strip leading path slashes.
* Cleanup Addon: Added an early-abort verification check utilizing the resource compiler to quickly find and report missing materials and models per-map.
* Cleanup Addon: Added support for `.dirtlist` ignore files to let users define custom relative path/directory patterns to exclude from cleanup, with an "Open .dirtlist" button in the UI.