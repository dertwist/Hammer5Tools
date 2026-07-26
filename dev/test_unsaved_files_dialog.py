"""Self-check for the combined unsaved-files dialog (offscreen, no user input)."""
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from PySide6.QtWidgets import QApplication, QDialog
from src.widgets.common import UnsavedFilesDialog

app = QApplication.instance() or QApplication([])

saved = []
entries = [
    ("SmartProp Editor", r"C:\addon\models\a.vsmart", lambda: saved.append("a.vsmart")),
    ("AssetGroup Maker", r"C:\addon\b.hbat", lambda: saved.append("b.hbat")),
    ("Wave Editor", "Untitled", None),  # no path -> not savable
]

# Save All with an unsavable row: stays open, saves what it can.
d = UnsavedFilesDialog(entries)
d.save_all()
assert saved == ["a.vsmart", "b.hbat"], saved
assert d.result() != QDialog.Accepted, "should not auto-accept while a file is unsaved"
d.save_all()
assert saved == ["a.vsmart", "b.hbat"], f"already-saved rows must not re-save: {saved}"

# All rows savable -> Save All closes with Accepted.
saved.clear()
d = UnsavedFilesDialog(entries[:2])
d.save_all()
assert saved == ["a.vsmart", "b.hbat"], saved
assert d.result() == QDialog.Accepted

# A failing save keeps the dialog open and the row unsaved.
import src.widgets.common as common
shown = []
common.QMessageBox.critical = staticmethod(lambda *a: shown.append(a))  # modal box would block

def boom():
    raise IOError("disk on fire")

d = UnsavedFilesDialog([("SmartProp Editor", "c.vsmart", boom)])
d.save_all()
assert d.result() != QDialog.Accepted
assert shown, "save failure must be reported"

# collect_unsaved_files aggregates per-editor entries and skips missing editors.
# (importing src.app_core spins up the whole app, so exec the method body from source)
import ast, textwrap
src = open(os.path.join(REPO, "src", "app_core.py"), encoding="utf-8").read()
fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)
          and n.name == "collect_unsaved_files")
ns = {}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "app_core", "exec"), ns)
collect_unsaved_files = ns["collect_unsaved_files"]

class FakeEditor:
    def __init__(self, files): self._files = files
    def unsaved_files(self): return self._files

class Stub:
    collect_unsaved_files = collect_unsaved_files
    BatchCreator_MainWindow = FakeEditor([("b.hbat", None)])
    SmartPropEditorMainWindow = FakeEditor([("a.vsmart", None), ("d.vsmart", None)])
    SoundEventEditorMainWindow = None
    AudioEditor_instance = object()  # no unsaved_files attribute

assert Stub().collect_unsaved_files() == [
    ("AssetGroup Maker", "b.hbat", None),
    ("SmartProp Editor", "a.vsmart", None),
    ("SmartProp Editor", "d.vsmart", None),
]

print("ok")
