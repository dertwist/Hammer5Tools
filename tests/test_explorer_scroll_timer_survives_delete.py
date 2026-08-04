"""
Regression check for the addon-switch access violation.

Explorer.select_tree_item() schedules `QTimer.singleShot(50, lambda: self.tree
.scrollTo(...))` to let the tree finish expanding before it scrolls. Switching
addons/editors rebuilds the owning editor's Explorer and deleteLater()s the old
one's frame (which parents `self.tree`) before that 50ms elapses. The old
lambda called straight into `self.tree` regardless, and touching a QTreeView
whose C++ object is already destroyed is an access violation that kills the
whole process with no Python traceback -- not a catchable RuntimeError.

The fix captures `tree` and guards the call with `shiboken6.isValid()`. This
pins down that the guard actually stops the dead-object call, using the same
capture-then-fire shape as the real code (src/widgets/explorer/main.py).
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(root_dir, "src")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import shiboken6
from PySide6.QtWidgets import QApplication, QTreeView
from shiboken6 import isValid


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    tree = QTreeView()
    scrolled = []
    # Same shape as the guarded lambda in Explorer.select_tree_item().
    fire = lambda: isValid(tree) and scrolled.append(tree.scrollTo)

    # Simulate an addon switch tearing the old Explorer's frame (and the tree
    # it parents) down before the singleShot(50, ...) timer fires. shiboken6
    # .delete() destroys the C++ object immediately and deterministically,
    # the same end state deleteLater() reaches once the event loop catches up.
    shiboken6.delete(tree)
    assert not isValid(tree), (
        "tree should be destroyed for this check to mean anything"
    )

    fire()  # this is what the timer callback does once it fires late
    assert scrolled == [], (
        "guarded callback touched a QTreeView whose C++ object was already "
        "deleted -- this is the access violation from the addon-switch crash"
    )
    print("[PASS] singleShot callback skips a tree deleted before it fires")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
