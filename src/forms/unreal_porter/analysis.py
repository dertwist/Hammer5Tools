"""Analyze a UE project once, then reuse the result until the project changes.

Mounting a project through the CUE4Parse bridge and listing its assets costs a
subprocess and several seconds — long enough that doing it on every dialog open,
every addon switch and again at export time is the difference between a tool
that feels instant and one that doesn't. So the asset list is written to a JSON
manifest keyed by project path, alongside a fingerprint of the project's content
files. A stale fingerprint means reanalyze; a matching one means read the JSON.

The fingerprint is a filesystem walk (name, size, mtime) rather than a content
hash: it is one to two orders of magnitude cheaper on a project with thousands
of uassets, and it catches every edit a user can make through the Editor.
"""
import hashlib
import json
import os
import time

from src.common import user_data_dir

CACHE_DIR = user_data_dir / "unreal_porter_analysis"

# Only these count towards the fingerprint. Unreal churns Saved/, Intermediate/
# and DerivedDataCache/ constantly without the content meaning anything different.
ASSET_EXTS = (".uasset", ".umap")
IGNORED_DIRS = {"saved", "intermediate", "deriveddatacache", "build", "binaries", ".git"}

MANIFEST_VERSION = 1


def manifest_path(uproject_path: str):
    """Where a project's manifest lives. Keyed by a hash of the project path so
    two projects with the same folder name never collide."""
    digest = hashlib.sha1(os.path.normcase(os.path.abspath(uproject_path)).encode("utf-8")).hexdigest()[:16]
    stem = os.path.splitext(os.path.basename(uproject_path))[0]
    return CACHE_DIR / f"{stem}.{digest}.json"


def fingerprint(content_dir: str) -> str:
    """A cheap signature of the project's content files."""
    parts = []
    for dirpath, dirnames, filenames in os.walk(content_dir):
        dirnames[:] = [d for d in dirnames if d.lower() not in IGNORED_DIRS]
        for filename in filenames:
            if not filename.lower().endswith(ASSET_EXTS):
                continue
            full = os.path.join(dirpath, filename)
            try:
                stat = os.stat(full)
            except OSError:
                continue
            rel = os.path.relpath(full, content_dir).replace("\\", "/")
            parts.append(f"{rel}|{stat.st_size}|{stat.st_mtime_ns}")
    parts.sort()
    digest = hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()
    return f"{len(parts)}:{digest}"


def load(uproject_path: str, content_dir: str):
    """The cached analysis if it still matches the project, else None."""
    path = manifest_path(uproject_path)
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, ValueError):
        return None
    if manifest.get("version") != MANIFEST_VERSION:
        return None
    if manifest.get("fingerprint") != fingerprint(content_dir):
        return None
    return manifest


def save(uproject_path: str, content_dir: str, assets, info, materials=None) -> dict:
    manifest = {
        "version": MANIFEST_VERSION,
        "uproject": uproject_path,
        "content_dir": content_dir,
        "fingerprint": fingerprint(content_dir),
        "analyzed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "info": info or {},
        "assets": sorted(assets),
        # Master Material groups from the same pass. JSON turns the instance
        # tuples into lists, which unpack identically where they are consumed.
        "materials": materials or {},
    }
    path = manifest_path(uproject_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write-then-replace: a half-written manifest that still parses would be
    # cached as a complete asset list.
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    os.replace(tmp, path)
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

    info = bridge.info()
    assets = bridge.list("")
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

        # Round-trip: a fresh manifest loads, a stale one does not.
        assert load(uproject, content) is None, "loaded a manifest that was never written"
        groups = {"M_Master": {"shader": "csgo_environment.vfx",
                               "instances": [("MI_Wood", "P/Content/MI_Wood", {})],
                               "textures": {}, "slot_overrides": {}, "count": 1}}
        save(uproject, content, ["P/Content/Meshes/SM_Chair.uasset"], {"game": "P"}, groups)
        cached = load(uproject, content)
        assert cached and cached["assets"] == ["P/Content/Meshes/SM_Chair.uasset"], cached
        # The material groups must survive the JSON round-trip in a shape the
        # converter can still unpack (tuples come back as lists).
        stem, path, data = cached["materials"]["M_Master"]["instances"][0]
        assert (stem, path) == ("MI_Wood", "P/Content/MI_Wood"), (stem, path)

        with open(os.path.join(content, "Meshes", "SM_Table.uasset"), "w") as f:
            f.write("c")
        assert load(uproject, content) is None, "a new asset did not invalidate the cache"

        # Two projects sharing a filename must not share a manifest.
        other = os.path.join(content, "P.uproject")
        open(other, "w").close()
        assert manifest_path(uproject) != manifest_path(other)

        manifest_path(uproject).unlink()

    print("ok")


if __name__ == "__main__":
    demo()
