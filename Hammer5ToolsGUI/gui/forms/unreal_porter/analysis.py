"""Analyze a UE project once, then reuse the result until the project changes.

Mounting a project through the CUE4Parse bridge and listing its assets costs a
subprocess and several seconds — and resolving one asset's references costs a
whole bridge process each, which is minutes across a real project. So the asset
list, the Master Material groups and the resolved reference graph are all
written to a KV3 manifest in the target addon, alongside a fingerprint of the
project's content files. A stale fingerprint means reanalyze; a matching one
means the reference walk is answered from the manifest without running at all.

The fingerprint is a filesystem walk (name, size, mtime) rather than a content
hash: it is one to two orders of magnitude cheaper on a project with thousands
of uassets, and it catches every edit a user can make through the Editor.

The manifest lives with the addon rather than in user data, so it travels with
the content it describes. One addon holds one manifest, so the project it was
built from is recorded and checked — pointing the same addon at a different
project is a miss, not a wrong answer.
"""
import hashlib
import os
import time
from pathlib import Path

from gui.common import JsonToKv3, Kv3ToJson

# Beside the export cache (main.TMP_SUBDIR), under the addon's content root.
CACHE_SUBDIR = "hammer5tools/unrealporter"
CACHE_NAME = "analyze_cache.kv3"

# Only these count towards the fingerprint. Unreal churns Saved/, Intermediate/
# and DerivedDataCache/ constantly without the content meaning anything different.
ASSET_EXTS = (".uasset", ".umap")
IGNORED_DIRS = {"saved", "intermediate", "deriveddatacache", "build", "binaries", ".git"}

# v3: refs are now scanned with the bridge's iter-refs command, which resolves
# StaticMesh material slots the old grep-over-dump approach missed. Existing v2
# manifests cached those meshes as refs:[] and would never pick up the fix.
# v5: Standalone materials now resolve expression-graph textures & split channel masks.
MANIFEST_VERSION = 5


def manifest_path(output_dir: str):
    """Where the addon's analysis manifest lives, or None without an addon."""
    return Path(output_dir) / CACHE_SUBDIR / CACHE_NAME if output_dir else None


def _same_project(manifest, uproject_path: str) -> bool:
    """Was this manifest built from the project we are about to port?

    One addon, one manifest — so unlike the old per-project cache file, the
    project has to be checked rather than assumed from the filename.
    """
    stored = str(manifest.get("uproject") or "")
    if not stored:
        return False
    return os.path.normcase(os.path.abspath(stored)) == os.path.normcase(os.path.abspath(uproject_path))


def _kv3_safe(value):
    """KV3 has no tuple type; JSON used to flatten them on the way out."""
    if isinstance(value, tuple):
        return [_kv3_safe(v) for v in value]
    if isinstance(value, list):
        return [_kv3_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _kv3_safe(v) for k, v in value.items()}
    return value


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return Kv3ToJson(f.read())
    except (OSError, ValueError, TypeError, KeyError):
        return None


def _write(path, manifest) -> bool:
    """Write-then-replace: a half-written manifest that still parses would be
    cached as a complete asset list."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".kv3.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(JsonToKv3(_kv3_safe(manifest)))
        os.replace(tmp, path)
        return True
    except (OSError, TypeError, ValueError):
        return False    # a cache we cannot persist is a slower next run, not a failure


def fingerprint(content_dir: str) -> str:
    """A cheap signature of the project's content files.

    scandir rather than walk-then-stat: the directory listing already carries
    size and mtime on Windows, so this costs a syscall per directory instead of
    one per asset — and it runs on every open of an analyzed project.
    """
    parts = []
    stack = [content_dir]
    while stack:
        try:
            with os.scandir(stack.pop()) as entries:
                listing = list(entries)
        except OSError:
            continue
        for entry in listing:
            try:
                # follow_symlinks=False matches os.walk: a symlinked directory
                # is not descended into, so a loop cannot hang the scan.
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.lower() not in IGNORED_DIRS:
                        stack.append(entry.path)
                    continue
                if not entry.name.lower().endswith(ASSET_EXTS):
                    continue
                stat = entry.stat()
            except OSError:
                continue
            rel = os.path.relpath(entry.path, content_dir).replace("\\", "/")
            parts.append(f"{rel}|{stat.st_size}|{stat.st_mtime_ns}")
    parts.sort()
    digest = hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()
    return f"{len(parts)}:{digest}"


def is_truncated(assets, info) -> bool:
    """True if an asset list is shorter than the file count the bridge reported.

    `list` and `info.totalFiles` read the same mounted file set, so a gap means
    the list came back cut short — bridge builds before the fix capped it at 200.
    A truncated manifest is worse than no manifest: the fingerprint still matches
    the project, so it is replayed forever as if it were the whole thing, and the
    port silently drops every asset past the cut.

    `info.ignored` records the entries deliberately dropped from the listing
    (editor-only packages), which are a gap in the count and not a truncation.
    """
    total = (info or {}).get("totalFiles")
    ignored = (info or {}).get("ignored") or 0
    return isinstance(total, int) and len(assets or []) + ignored < total


def update_refs(output_dir: str, refs) -> None:
    """Merge newly scanned references into the stored manifest.

    Scanning every asset up front costs one bridge process per asset and stalls
    for minutes on a real project, so the graph fills in as assets are actually
    walked and each one is only ever read once. Deliberately does not touch the
    fingerprint: this adds knowledge about the same project state, it does not
    re-validate it.
    """
    path = manifest_path(output_dir)
    if not refs or path is None:
        return
    manifest = _read(path)
    if manifest is None:
        return
    merged = dict(manifest.get("refs") or {})
    merged.update(refs)
    manifest["refs"] = merged
    _write(path, manifest)


def load(uproject_path: str, content_dir: str, output_dir: str):
    """The cached analysis if it still matches the project, else None."""
    path = manifest_path(output_dir)
    if path is None:
        return None
    manifest = _read(path)
    if manifest is None:
        return None
    if manifest.get("version") != MANIFEST_VERSION:
        return None
    if not _same_project(manifest, uproject_path):
        return None
    if is_truncated(manifest.get("assets"), manifest.get("info")):
        return None
    if manifest.get("fingerprint") != fingerprint(content_dir):
        return None
    return manifest


def save(uproject_path: str, content_dir: str, output_dir: str, assets, info,
         materials=None, refs=None) -> dict:
    manifest = {
        "version": MANIFEST_VERSION,
        "uproject": uproject_path,
        "content_dir": content_dir,
        "fingerprint": fingerprint(content_dir),
        "analyzed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "info": info or {},
        "assets": sorted(assets),
        # Master Material groups from the same pass. The instance tuples are
        # flattened to lists on the way out and unpack identically on the way in.
        "materials": materials or {},
        # asset key -> the project assets it references, resolved at analysis time.
        "refs": refs or {},
    }
    path = manifest_path(output_dir)
    if path is not None:
        _write(path, manifest)
    return manifest


def analyze(bridge, content_dir: str, log_cb=None, progress_cb=None):
    """Mount the project, list what it holds, and group its materials.

    The material scan used to run after the export; it belongs here because it
    reads the *project*, not the export, and so it can be cached with the rest
    of the analysis instead of costing a bridge dump per material every run.

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


def demo():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        content = os.path.join(tmp, "Content")
        os.makedirs(os.path.join(content, "Meshes"))
        os.makedirs(os.path.join(content, "Saved"))
        uproject = os.path.join(tmp, "P.uproject")
        open(uproject, "w").close()

        mesh = os.path.join(content, "Meshes", "SM_Chair.uasset")
        with open(mesh, "w") as f:
            f.write("a")

        first = fingerprint(content)
        assert first.startswith("1:"), first
        assert fingerprint(content) == first, "fingerprint must be stable"

        # Churn under Saved/ is not a project change.
        with open(os.path.join(content, "Saved", "log.uasset"), "w") as f:
            f.write("noise")
        assert fingerprint(content) == first, "ignored dirs leaked into the fingerprint"

        # Editing an asset is.
        time.sleep(0.01)
        with open(mesh, "w") as f:
            f.write("bb")
        changed = fingerprint(content)
        assert changed != first, "an edited asset did not change the fingerprint"

        addon = os.path.join(tmp, "addon")

        # The manifest lands where the addon keeps its other porter data.
        assert manifest_path(addon) == Path(addon) / CACHE_SUBDIR / CACHE_NAME
        # No addon selected means nowhere to cache — not a crash.
        assert manifest_path("") is None
        assert load(uproject, content, "") is None
        update_refs("", {"a": []})

        # Round-trip: a fresh manifest loads, a stale one does not.
        assert load(uproject, content, addon) is None, "loaded a manifest that was never written"
        groups = {"M_Master": {"shader": "csgo_environment.vfx",
                               "instances": [("MI_Wood", "P/Content/MI_Wood", {})],
                               "textures": {}, "slot_overrides": {}, "count": 1}}
        save(uproject, content, addon, ["P/Content/Meshes/SM_Chair.uasset"], {"game": "P"}, groups)
        cached = load(uproject, content, addon)
        assert cached and cached["assets"] == ["P/Content/Meshes/SM_Chair.uasset"], cached
        # The material groups must survive the KV3 round-trip in a shape the
        # converter can still unpack — KV3 has no tuple type, so the instance
        # tuples have to come back as lists rather than failing to write at all.
        stem, path, data = cached["materials"]["M_Master"]["instances"][0]
        assert (stem, path) == ("MI_Wood", "P/Content/MI_Wood"), (stem, path)

        # References scanned during one selection must survive into the manifest
        # so the next one does not pay for them again — and merging them must
        # not disturb the fingerprint that says the manifest is still valid.
        assets = ["P/Content/Meshes/SM_Chair.uasset", "P/Content/Materials/MI_Wood.uasset"]
        save(uproject, content, addon, assets, {"game": "P"})
        update_refs(addon, {assets[0]: [assets[1]]})
        cached = load(uproject, content, addon)
        assert cached and cached["refs"] == {assets[0]: [assets[1]]}, cached
        update_refs(addon, {assets[1]: []})
        assert load(uproject, content, addon)["refs"] == {assets[0]: [assets[1]], assets[1]: []}
        # No manifest on disk is not an error, just nothing to remember.
        update_refs(os.path.join(tmp, "empty_addon"), {assets[0]: []})

        # One addon holds one manifest, so the project it describes has to be
        # checked — repointing the addon at another project must miss, not
        # replay the first project's asset list as if it were the second's.
        other_uproject = os.path.join(tmp, "Other.uproject")
        open(other_uproject, "w").close()
        assert load(other_uproject, content, addon) is None, "another project's manifest was reused"
        assert load(uproject, content, addon) is not None

        # A list shorter than the bridge's own file count was cut off by a capped
        # bridge build; replaying it caches a partial project as if it were whole.
        save(uproject, content, addon, ["P/Content/Meshes/SM_Chair.uasset"], {"totalFiles": 563})
        assert load(uproject, content, addon) is None, "a truncated manifest was served from cache"
        assert is_truncated(["a"], {"totalFiles": 2})
        assert not is_truncated(["a", "b"], {"totalFiles": 2})
        # Manifests from before totalFiles was recorded must still load.
        assert not is_truncated(["a"], {})
        # Deliberately dropped editor-only packages are a gap in the count, not
        # a truncation — without this every project with a _BuiltData asset
        # reanalyzed on every single open and never cached anything.
        assert not is_truncated(["a"], {"totalFiles": 2, "ignored": 1})
        assert is_truncated(["a"], {"totalFiles": 3, "ignored": 1})

        save(uproject, content, addon, ["P/Content/Meshes/SM_Chair.uasset"], {"game": "P"})
        assert load(uproject, content, addon) is not None
        with open(os.path.join(content, "Meshes", "SM_Table.uasset"), "w") as f:
            f.write("c")
        assert load(uproject, content, addon) is None, "a new asset did not invalidate the cache"

    print("ok")


if __name__ == "__main__":
    demo()
