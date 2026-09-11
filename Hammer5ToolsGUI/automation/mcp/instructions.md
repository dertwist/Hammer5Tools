Use Hammer5Tools for Source 2 and Unreal asset inspection, authoring, and level maintenance. Prefer the narrowest read-only tool that answers the request. Treat content-relative asset paths as case-insensitive and use forward slashes when presenting them.

Format tools:
- Models (.vmdl): Use hammer5tools.vmdl_read, hammer5tools.vmdl_write, and hammer5tools.vmdl_edit.
- Materials (.vmat): Use hammer5tools.vmat_read, hammer5tools.vmat_write, and hammer5tools.vmat_edit.
- Textures (.vtex): Use hammer5tools.vtex_read, hammer5tools.vtex_write, and hammer5tools.vtex_edit.
- SmartProps (.vsmart): Use hammer5tools.vsmart_read, hammer5tools.vsmart_write, hammer5tools.vsmart_edit, and hammer5tools.vsmart_evaluate.
- Gamedata (.vdata): Use hammer5tools.vdata_read, hammer5tools.vdata_write, and hammer5tools.vdata_edit.
- Snapshots (.vsnap): Use hammer5tools.vsnap_read, hammer5tools.vsnap_write, hammer5tools.vsnap_generate, and hammer5tools.vsnap_edit.

Operation tools:
- Compilation: Use hammer5tools.compile_asset to invoke resourcecompiler.exe on changed assets.
- Validation: Use hammer5tools.validate_addon to diagnose broken references, and hammer5tools.find_unused_assets to locate orphans.
- Dependencies: Use hammer5tools.resolve_dependencies to recursively trace all required files for an asset.
- Level design: Use hammer5tools.vmap_rewrite_references for batch search-and-replace across map dependencies.
- Official assets: Use hammer5tools.vpk_search and hammer5tools.vpk_extract to inspect official CS2 game archives.

Safety Rules:
- When modifying existing files, always specify dry_run: true first to preview the planned changes and verify diffs before writing to disk.
- Never claim that a file was changed when dry_run: true was set or when using read-only tools.
