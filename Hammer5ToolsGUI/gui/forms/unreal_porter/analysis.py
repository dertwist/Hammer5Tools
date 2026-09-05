"""Live analysis of an Unreal Engine project through the CUE4Parse bridge.

Surveys the project's mounted assets and groups its master materials on demand,
keeping analysis results in memory for the lifetime of the open converter dialog.
"""


def is_truncated(assets, info) -> bool:
    """True if an asset list is shorter than the file count the bridge reported.

    `list` and `info.totalFiles` read the same mounted file set, so a gap means
    the list came back cut short — bridge builds before the fix capped it at 200.
    A truncated asset list will silently drop assets past the cut.

    `info.ignored` records the entries deliberately dropped from the listing
    (editor-only packages), which are a gap in the count and not a truncation.
    """
    total = (info or {}).get("totalFiles")
    ignored = (info or {}).get("ignored") or 0
    return isinstance(total, int) and len(assets or []) + ignored < total


def analyze(bridge, content_dir: str, log_cb=None, progress_cb=None):
    """Mount the project, list what it holds, and group its materials.

    The material scan reads the project directly rather than the export cache.

    Addon-specific shader choices are deliberately not applied here — see
    converter.apply_saved_swaps.
    """
    from .converter import scan_master_materials

    # Core reuses one mounted provider across calls; this run has to see the
    # project as it is on disk now, not as the last analysis found it.
    bridge.reset()
    info = bridge.info()
    assets, ignored = bridge.list_counted("")
    info = {**(info or {}), "ignored": ignored}
    if is_truncated(assets, info) and log_cb:
        log_cb(
            f"Bridge listed only {len(assets)} of {info.get('totalFiles')} files — "
            "the port will miss assets.",
            "warn",
        )
    materials = scan_master_materials(
        content_dir, None, bridge, output_dir=None,
        log_cb=log_cb, progress_cb=progress_cb,
    )
    return assets, info, materials
