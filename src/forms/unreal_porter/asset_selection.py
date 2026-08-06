"""Pick which project assets to port, and pull in what they depend on.

Porting a map without its meshes, or a mesh without its materials, produces a
scene full of missing references — so a selection is only ever a starting
point. expand_references walks the actual asset data through the CUE4Parse
bridge and adds everything the chosen assets point at, transitively.
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTreeWidgetItem, QDialogButtonBox,
)

from src.common import enable_dark_title_bar
from src.settings.main import get_settings_bool, set_settings_bool
from src.styles.common import apply_stylesheets
from src.widgets.tree import HierarchyTreeWidget

KEY_ROLE = Qt.UserRole + 1

# Asset categories, in the order they are shown. The keys are the FILE_TYPES the
# converter uses; "Scenes" is called Maps everywhere a user sees it, because that
# is what the assets are.
CATEGORY_LABELS = {
    "Models": "Models",
    "Materials": "Materials",
    "Textures": "Textures",
    "Blueprints": "Blueprints",
    "Scenes": "Maps",
}

# Unreal's own naming convention is the only reliable type signal in a file
# listing — the extension is .uasset for everything except maps. Prefixes are
# checked before folders so a T_ texture parked in Materials/ is still a texture.
_PREFIXES = {
    "Textures": ("t_", "tex_", "rvt_", "svt_"),
    "Materials": ("m_", "mi_", "mm_", "mf_", "mpc_"),
    "Models": ("sm_", "sk_", "st_"),
    "Blueprints": ("bp_", "bpi_", "abp_"),
}
_FOLDERS = {
    "Textures": ("/textures/", "/texture/", "/tex/"),
    "Materials": ("/materials/", "/material/", "/material_instances/", "/mastermaterials/"),
    "Models": ("/meshes/", "/mesh/", "/models/", "/staticmeshes/", "/props/"),
    "Blueprints": ("/blueprints/", "/blueprint/", "/bp/"),
}


def classify(key: str):
    """The category an asset key belongs to, or None if it doesn't look like any."""
    lowered = key.replace("\\", "/").lower()
    if lowered.endswith(".umap"):
        return "Scenes"
    name = os.path.basename(lowered)
    for category, prefixes in _PREFIXES.items():
        if name.startswith(prefixes):
            return category
    for category, folders in _FOLDERS.items():
        if any(folder in lowered for folder in folders):
            return category
    return None


def category_counts(keys) -> dict:
    """{category: count} for the categories actually present."""
    counts = {}
    for key in keys:
        category = classify(key)
        if category:
            counts[category] = counts.get(category, 0) + 1
    return counts


def format_counts(keys) -> str:
    """"Models 43  |  Maps 7  |  Other 12  —  62 total" — empty categories omitted.

    Every key is accounted for. classify() only recognises Unreal's own naming
    convention, and plenty of projects (marketplace packs especially) do not
    follow it — so dropping what it cannot place made the label read "Maps 1"
    for a 237-asset project. Unclassified assets port exactly like any other;
    they just cannot be named here, which is what "Other" says.
    """
    keys = list(keys)
    if not keys:
        return ""
    counts = category_counts(keys)
    parts = [f"{label} {counts[category]}"
             for category, label in CATEGORY_LABELS.items() if counts.get(category)]
    other = len(keys) - sum(counts.values())
    if other:
        parts.append(f"Other {other}")
    return "  |  ".join(parts) + f"  —  {len(keys)} total"


def asset_stem(key: str) -> str:
    """Filename without extension, lowercased — the join key between a file
    path ("…/Content/Meshes/SM_Chair.uasset") and a UE object reference
    ("/Game/Meshes/SM_Chair.SM_Chair")."""
    return os.path.splitext(os.path.basename(key))[0].lower()


def ref_stem(ref: str) -> str:
    """The asset stem a UE object reference points at."""
    tail = str(ref).replace("\\", "/").rsplit("/", 1)[-1]
    return tail.split(".", 1)[0].lower()


def key_to_object_path(key: str) -> str:
    """File key -> the UE object path the converters expect.

    "MyProj/Content/Meshes/SM_Chair.uasset" -> "/Game/Meshes/SM_Chair.SM_Chair"
    Everything up to and including Content/ is the mount point, which UE
    addresses as /Game/.
    """
    path = os.path.splitext(key.replace("\\", "/"))[0]
    lowered = path.lower()
    marker = "/content/"
    if lowered.startswith("content/"):
        path = path[len("content/"):]
    elif marker in lowered:
        path = path[lowered.index(marker) + len(marker):]
    name = path.rsplit("/", 1)[-1]
    return f"/Game/{path}.{name}"


def _index_by_stem(keys) -> dict:
    index = {}
    for key in keys:
        index.setdefault(asset_stem(key), key)
    return index


# Every reference read is its own bridge process, and each one mounts the whole
# project before reading anything — the cost is startup, not the asset. Running
# them concurrently hides that; the work happens in the child processes, so
# threads are enough.
# ponytail: one process per asset is the ceiling. A bridge command that mounts
# once and dumps references for every asset would collapse this to a single
# invocation and make scanning a whole project viable.
REF_SCAN_WORKERS = 8


def expand_references(bridge, keys, all_keys, log_cb=None, progress_cb=None, max_rounds=6,
                      refs_map=None, new_refs=None, is_cancelled=None) -> set:
    """The chosen assets plus everything they depend on, transitively.

    refs_map — the graph cached in the analysis manifest — resolves a key with
    no work at all. Anything it does not cover is read from the bridge, several
    assets at a time, and recorded into new_refs so the caller can persist it;
    that way each asset is scanned once per project state, not once per pick.

    Unresolvable references (engine content, assets outside the project) are
    dropped rather than reported one by one; they are normal and there are a
    lot of them.

    If is_cancelled is a no-arg callable returning truthy, scanning stops
    between rounds and within the in-flight batch (the bridge call itself also
    honors the flag), returning what has been resolved so far.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def log(msg, level="info"):
        if log_cb:
            log_cb(msg, level)

    index = _index_by_stem(all_keys)
    selected = set(keys)
    pending = set(keys)
    added_total = 0
    unreadable = []

    if new_refs is None:
        new_refs = {}

    def resolve_stem(ref_str: str) -> set:
        st = ref_stem(ref_str)
        if not st:
            return set()
        if st in index:
            return {index[st]}
        matches = set()
        candidates = (
            f"mi_{st}", f"mi_{st}_01", f"mi_{st}_01a", f"mi_{st}a",
            f"m_{st}", f"m_{st}_01", f"mat_{st}", f"mat_{st}_01",
        )
        for cand in candidates:
            if cand in index:
                matches.add(index[cand])
        return matches

    def scan(key):
        """One asset's references, resolved to the project assets they name."""
        refs = bridge.iter_refs(os.path.splitext(key)[0], is_cancelled=is_cancelled)
        hits = set()
        for ref in refs:
            hits.update(resolve_stem(ref))
        hits.discard(key)
        return key, sorted(hits)

    cancelled = False
    for _round in range(max_rounds):
        if not pending:
            break
        # Stop dispatching new rounds once cancelled; whatever was resolved in
        # earlier rounds is still worth keeping.
        if is_cancelled is not None and is_cancelled():
            cancelled = True
            break
        discovered = set()
        to_scan = []
        for key in sorted(pending):
            cached = (refs_map or {}).get(key, new_refs.get(key))
            if not cached:
                to_scan.append(key)
            else:
                discovered.update(cached)

        done = 0
        with ThreadPoolExecutor(max_workers=REF_SCAN_WORKERS) as pool:
            futures = {pool.submit(scan, key): key for key in to_scan}
            for future in as_completed(futures):
                done += 1
                if progress_cb:
                    progress_cb(done, len(to_scan))
                try:
                    key, hits = future.result()
                except Exception as e:
                    # Expected for textures: an uncooked .uasset holds only
                    # editor source data, so CUE4Parse throws deserialising the
                    # export. Harmless here — a texture references nothing
                    # anyway — so it is one summary line at the end, not one
                    # warning per asset. Cached as "no references" either way,
                    # so it is not retried on the next pick.
                    key = futures[future]
                    unreadable.append((os.path.basename(key), str(e)))
                    new_refs[key] = []
                    continue
                new_refs[key] = hits
                discovered.update(hits)

        discovered -= selected
        selected |= discovered
        added_total += len(discovered)
        pending = discovered

    if cancelled:
        log("Reference scan cancelled — keeping what was resolved so far.", "warn")

    if unreadable:
        log(f"{len(unreadable)} asset(s) could not be scanned for references "
            f"(normal for textures) — e.g. {unreadable[0][0]}: {unreadable[0][1]}", "warn")
    if added_total:
        log(f"Pulled in {added_total} referenced asset(s) alongside the {len(keys)} selected.", "info")
    else:
        log("No additional references found.", "info")
    return selected


class AssetSelectionDialog(QDialog):
    """Checkbox tree over the project's asset paths.

    Returns only what the user ticked — reference expansion happens after,
    against the bridge, where it can report progress.
    """

    def __init__(self, asset_keys, preselected=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select assets")
        self.resize(720, 720)
        enable_dark_title_bar(self)
        self.setStyleSheet("background-color: #151515;")

        self._asset_keys = sorted(asset_keys)
        self._leaves = []
        self._updating = False
        self.selected_keys = set()

        self._build_ui()
        self._populate(preselected or set())
        self._apply_filter()
        apply_stylesheets(self)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        top = QHBoxLayout()
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by name…")
        self.filter_edit.textChanged.connect(self._apply_filter)
        top.addWidget(self.filter_edit, 1)
        check_all = QPushButton("Check all")
        check_all.clicked.connect(lambda: self._set_all(Qt.Checked))
        top.addWidget(check_all)
        uncheck_all = QPushButton("Uncheck all")
        uncheck_all.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        top.addWidget(uncheck_all)
        layout.addLayout(top)

        # The file types used to be a separate "Convert file types" group on the
        # General tab, which meant picking assets and picking what to do with
        # them happened in two places that could disagree. They are one filter
        # now, still backed by the type_enabled_* settings the converter reads.
        types = QHBoxLayout()
        types.addWidget(QLabel("Types:"))
        self.type_checks = {}
        counts = category_counts(self._asset_keys)
        for category, label in CATEGORY_LABELS.items():
            check = QCheckBox(f"{label} {counts.get(category, 0)}")
            check.setChecked(get_settings_bool("UnrealConverter", f"type_enabled_{category}", True))
            check.toggled.connect(
                lambda checked, c=category: self._on_type_toggled(c, checked)
            )
            self.type_checks[category] = check
            types.addWidget(check)
        types.addStretch(1)
        layout.addLayout(types)

        # Throwaway undo stack: the tree is read-only here, we want its look
        # (branch drawing, row height) and none of its editing.
        self.tree = HierarchyTreeWidget(QUndoStack())
        self.tree.setHeaderHidden(True)
        self.tree.setDragEnabled(False)
        self.tree.setAcceptDrops(False)
        self.tree.setDragDropMode(HierarchyTreeWidget.NoDragDrop)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree, 1)

        self.count_label = QLabel()
        layout.addWidget(self.count_label)

        note = QLabel(
            "Assets referenced by your selection (a map's meshes, a mesh's materials, "
            "a material's textures) are added automatically when you confirm."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #808080;")
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, preselected):
        self._updating = True
        folders = {}  # path prefix -> QTreeWidgetItem
        for key in self._asset_keys:
            parts = key.replace("\\", "/").split("/")
            parent = None
            for depth, part in enumerate(parts[:-1]):
                prefix = "/".join(parts[:depth + 1])
                item = folders.get(prefix)
                if item is None:
                    item = QTreeWidgetItem([part])
                    # Deliberately not ItemIsAutoTristate: Qt recomputes an
                    # auto-tristate parent from its children the moment you set
                    # it, so a folder click reads back as Unchecked before it can
                    # propagate down. Both directions are handled below instead.
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Unchecked)
                    if parent is None:
                        self.tree.addTopLevelItem(item)
                    else:
                        parent.addChild(item)
                    folders[prefix] = item
                parent = item

            leaf = QTreeWidgetItem([parts[-1]])
            leaf.setFlags(leaf.flags() | Qt.ItemIsUserCheckable)
            leaf.setData(0, KEY_ROLE, key)
            leaf.setCheckState(0, Qt.Checked if key in preselected else Qt.Unchecked)
            (parent or self.tree.invisibleRootItem()).addChild(leaf)
            self._leaves.append(leaf)

        self._updating = False
        self._update_count()

    # checkbox plumbing

    def _on_item_changed(self, item, column):
        if self._updating or column != 0:
            return
        self._updating = True
        state = item.checkState(0)
        if item.childCount() and state != Qt.PartiallyChecked:
            self._set_subtree(item, state)
        self._refresh_ancestors(item)
        self._updating = False
        self._update_count()

    def _set_subtree(self, item, state):
        """A folder's tick reaches everything under it — except rows the filter
        is hiding, which the user cannot see and did not mean to include."""
        for i in range(item.childCount()):
            child = item.child(i)
            if child.isHidden():
                continue
            child.setCheckState(0, state)
            self._set_subtree(child, state)

    def _refresh_ancestors(self, item):
        """A folder shows checked / partial / unchecked from its visible children."""
        parent = item.parent()
        while parent is not None:
            visible = [parent.child(i) for i in range(parent.childCount())
                       if not parent.child(i).isHidden()]
            states = {c.checkState(0) for c in visible}
            if not states or states == {Qt.Unchecked}:
                parent.setCheckState(0, Qt.Unchecked)
            elif states == {Qt.Checked}:
                parent.setCheckState(0, Qt.Checked)
            else:
                parent.setCheckState(0, Qt.PartiallyChecked)
            parent = parent.parent()

    def _set_all(self, state):
        self._updating = True
        for leaf in self._leaves:
            if not leaf.isHidden():
                leaf.setCheckState(0, state)
        for leaf in self._leaves:
            if not leaf.isHidden():
                self._refresh_ancestors(leaf)
        self._updating = False
        self._update_count()

    def checked_keys(self) -> set:
        return {leaf.data(0, KEY_ROLE) for leaf in self._leaves if leaf.checkState(0) == Qt.Checked}

    def _update_count(self):
        self.count_label.setText(f"{len(self.checked_keys())} of {len(self._leaves)} asset(s) selected")

    # filtering

    def _on_type_toggled(self, category, checked):
        set_settings_bool("UnrealConverter", f"type_enabled_{category}", checked)
        self._apply_filter(self.filter_edit.text())
        self._update_count()

    def _enabled_types(self) -> set:
        return {c for c, check in self.type_checks.items() if check.isChecked()}

    def _apply_filter(self, text=""):
        needle = text.strip().lower()
        allowed = self._enabled_types()
        for leaf in self._leaves:
            key = leaf.data(0, KEY_ROLE)
            hidden = bool(needle) and needle not in leaf.text(0).lower()
            category = classify(key)
            # Unclassified assets stay visible: hiding what we could not identify
            # would silently drop it from the port with no way to notice.
            if category is not None and category not in allowed:
                hidden = True
            leaf.setHidden(hidden)
        for i in range(self.tree.topLevelItemCount()):
            self._prune(self.tree.topLevelItem(i))

    def _prune(self, item) -> bool:
        """Hide folders with nothing visible under them. Returns visibility."""
        if item.data(0, KEY_ROLE) is not None:
            return not item.isHidden()
        visible = False
        for i in range(item.childCount()):
            visible = self._prune(item.child(i)) or visible
        item.setHidden(not visible)
        return visible

    def _on_accept(self):
        self.selected_keys = self.checked_keys()
        self.accept()


def demo():
    keys = [
        "P/Content/Maps/Arena.umap",
        "P/Content/Meshes/SM_Chair.uasset",
        "P/Content/Materials/MI_Wood.uasset",
        "P/Content/Textures/T_Wood_D.uasset",
    ]
    assert asset_stem(keys[1]) == "sm_chair"
    assert ref_stem("/Game/Meshes/SM_Chair.SM_Chair") == "sm_chair"
    # UE also writes references in Class'/Path/Name.Name' form.
    assert ref_stem("Texture2D'/Game/Textures/T_Wood_D.T_Wood_D'") == "t_wood_d"

    # A file key must round-trip to the object path the converters use, so a
    # directly-picked mesh lands at the same output path as a map-referenced one.
    assert key_to_object_path(keys[1]) == "/Game/Meshes/SM_Chair.SM_Chair"
    assert key_to_object_path("Content/A/B.uasset") == "/Game/A/B.B"
    assert ref_stem(key_to_object_path(keys[1])) == asset_stem(keys[1])

    # The scan reads a dump as text rather than parsing it, so the pattern that
    # picks references out of it is what the whole expansion hangs on.
    from .bridge_client import _REF_FIELD
    found = set(_REF_FIELD.findall(
        '  "StaticMaterials": [\n'
        '    {\n'
        '      "MaterialInterface": {\n'
        '        "ObjectName": "MaterialInstanceConstant\'MI_Wood\'",\n'
        '        "ObjectPath": "/Game/Materials/MI_Wood.MI_Wood"\n'
    ))
    assert {"MaterialInstanceConstant'MI_Wood'", "/Game/Materials/MI_Wood.MI_Wood"}.issubset(found), found

    class FakeBridge:
        """Arena -> SM_Chair -> MI_Wood -> T_Wood_D, one hop per dump."""
        refs = {
            "P/Content/Maps/Arena": {"/Game/Meshes/SM_Chair.SM_Chair"},
            "P/Content/Meshes/SM_Chair": {"/Game/Materials/MI_Wood.MI_Wood"},
            "P/Content/Materials/MI_Wood": {"/Game/Textures/T_Wood_D.T_Wood_D"},
            "P/Content/Textures/T_Wood_D": set(),
        }

        def iter_refs(self, obj, is_cancelled=None):
            return self.refs[obj]

    # Selecting only the map must drag the whole chain along, transitively.
    got = expand_references(FakeBridge(), {keys[0]}, keys)
    assert got == set(keys), got
    # A leaf with no references stays alone.
    assert expand_references(FakeBridge(), {keys[3]}, keys) == {keys[3]}

    class BrokenBridge:
        def iter_refs(self, obj, is_cancelled=None):
            raise RuntimeError("bridge down")

    # A dump failure must not lose the user's own selection.
    assert expand_references(BrokenBridge(), {keys[0]}, keys) == {keys[0]}

    # A cached graph resolves the same chain without touching the bridge at all.
    cached = {keys[0]: [keys[1]], keys[1]: [keys[2]], keys[2]: [keys[3]], keys[3]: []}
    assert expand_references(BrokenBridge(), {keys[0]}, keys, refs_map=cached) == set(keys)
    # A key the cache does not cover still falls back to the bridge.
    partial = {keys[0]: [keys[1]]}
    assert expand_references(FakeBridge(), {keys[0]}, keys, refs_map=partial) == set(keys)

    # Whatever had to be read is handed back resolved to project keys, so the
    # caller can persist it and never pay for those assets again.
    fresh = {}
    expand_references(FakeBridge(), {keys[0]}, keys, new_refs=fresh)
    assert fresh == {keys[0]: [keys[1]], keys[1]: [keys[2]], keys[2]: [keys[3]], keys[3]: []}, fresh
    # An asset that cannot be read is remembered as "no references" rather than
    # rescanned on every pick.
    broken = {}
    expand_references(BrokenBridge(), {keys[0]}, keys, new_refs=broken)
    assert broken == {keys[0]: []}, broken

    # Classification drives both the stats line and the type filter, so a
    # misread prefix silently hides assets from the port.
    assert classify("P/Content/Maps/Arena.umap") == "Scenes"
    assert classify("P/Content/Meshes/SM_Chair.uasset") == "Models"
    assert classify("P/Content/Materials/MI_Wood.uasset") == "Materials"
    assert classify("P/Content/Textures/T_Wood_D.uasset") == "Textures"
    assert classify("P/Content/Blueprints/BP_Door.uasset") == "Blueprints"
    # Prefix beats folder: a texture parked in Materials/ is still a texture.
    assert classify("P/Content/Materials/T_Wood_D.uasset") == "Textures"
    # No prefix falls back to the folder.
    assert classify("P/Content/Meshes/Chair.uasset") == "Models"
    # Nothing recognisable stays unclassified rather than being guessed.
    assert classify("P/Content/Misc/Thing.uasset") is None

    assert category_counts(keys) == {"Scenes": 1, "Models": 1, "Materials": 1, "Textures": 1}
    line = format_counts(keys)
    assert line == "Models 1  |  Materials 1  |  Textures 1  |  Maps 1  —  4 total", line
    # Empty categories are omitted, not printed as zero.
    assert format_counts(["P/Content/Maps/A.umap"]) == "Maps 1  —  1 total"
    assert format_counts([]) == ""

    # The label must account for every asset. A pack that ignores Unreal's
    # naming convention classifies as nothing, and silently dropping those made
    # the label report 5 assets for a project holding 237.
    unnamed = ["P/Content/Props/Bin_01.uasset", "P/Content/Props/Fan.uasset"]
    line = format_counts(unnamed + ["P/Content/Maps/A.umap"])
    assert line == "Maps 1  |  Other 2  —  3 total", line
    assert format_counts(unnamed) == "Other 2  —  2 total"

    _demo_tree(keys)
    print("ok")


def _demo_tree(keys):
    """Checkbox propagation. Qt fights the obvious implementation here (see the
    ItemIsAutoTristate note in _populate), so it gets a real check."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    dlg = AssetSelectionDialog(keys + ["P/Content/Meshes/Props/SM_Barrel.uasset"])

    content = dlg.tree.topLevelItem(0).child(0)
    by_name = {content.child(i).text(0): content.child(i) for i in range(content.childCount())}

    # A folder tick reaches nested children, not just direct ones.
    by_name["Meshes"].setCheckState(0, Qt.Checked)
    assert dlg.checked_keys() == {"P/Content/Meshes/SM_Chair.uasset",
                                 "P/Content/Meshes/Props/SM_Barrel.uasset"}, dlg.checked_keys()
    # Partially filled folders read as partial, all the way up.
    by_name["Meshes"].child(0).setCheckState(0, Qt.Unchecked)
    assert by_name["Meshes"].checkState(0) == Qt.PartiallyChecked
    assert dlg.tree.topLevelItem(0).checkState(0) == Qt.PartiallyChecked

    by_name["Meshes"].setCheckState(0, Qt.Unchecked)
    assert not dlg.checked_keys(), dlg.checked_keys()

    # Check all only takes what the filter leaves visible.
    dlg.filter_edit.setText("barrel")
    dlg._set_all(Qt.Checked)
    assert dlg.checked_keys() == {"P/Content/Meshes/Props/SM_Barrel.uasset"}, dlg.checked_keys()
    assert by_name["Maps"].isHidden(), "folder with no visible children stayed visible"
    dlg.deleteLater()


if __name__ == "__main__":
    demo()
