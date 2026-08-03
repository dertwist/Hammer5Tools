"""
``mark_paint_through()`` must stop a child hiding its parent's custom painting.

The global stylesheet gives every widget in the application an opaque
background:

    QWidget { background-color: #151515; }

A widget that draws in its own paintEvent is fine on its own — Qt paints the
styled background first and the paintEvent over it. The trap is its *children*:
each one is opaque too, so it covers whatever the parent drew underneath it.
That is how the SmartProp property panel's zebra stripes and selection
highlight shipped invisible while every offscreen check passed — the checks
never applied the application stylesheet.

The exemption is ``QWidget[paintThrough="true"] { background: transparent; }``,
which relies on an attribute selector outranking a plain type selector. Two
things this pins down, both of which cost real debugging time to establish:

  * marking the *child* is what works;
  * marking the parent that does the painting does nothing at all.
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

from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from src.styles.common import PAINT_THROUGH_PROPERTY, mark_paint_through
from src.styles.qt_global_stylesheet import QT_Stylesheet_global

PAINTED = "#FF0000"    # what the parent draws
BLANKET = "#151515"    # what the global sheet paints over everything


class _Painted(QWidget):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(PAINTED))
        painter.end()


def _sample(app, mark_parent: bool, mark_child: bool) -> str:
    """Colour at a point covered by the child, over a parent that paints red."""
    parent = _Painted()
    parent.resize(120, 60)
    if mark_parent:
        mark_paint_through(parent)
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(0, 0, 0, 0)
    child = QWidget(parent)
    if mark_child:
        mark_paint_through(child)
    layout.addWidget(child)
    parent.show()
    for _ in range(8):
        app.processEvents()
    colour = parent.grab().toImage().pixelColor(10, 10).name().upper()
    parent.hide()
    return colour


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(QT_Stylesheet_global)

    plain = _sample(app, mark_parent=False, mark_child=False)
    assert plain == BLANKET.upper(), (
        f"expected an unmarked child to cover the parent's painting with "
        f"{BLANKET}, got {plain}. If the blanket QWidget background rule was "
        f"removed from QT_Stylesheet_global, this whole check is obsolete."
    )
    print(f"[PASS] an unmarked child covers the parent's painting ({plain})")

    marked = _sample(app, mark_parent=False, mark_child=True)
    assert marked == PAINTED.upper(), (
        f"mark_paint_through() did not make the child transparent: parent "
        f"painted {PAINTED}, sampled {marked}. The "
        f'QWidget[{PAINT_THROUGH_PROPERTY}="true"] rule in QT_Stylesheet_global '
        f"is missing or outranked."
    )
    print(f"[PASS] a marked child lets the parent's painting through ({marked})")

    wrong_end = _sample(app, mark_parent=True, mark_child=False)
    assert wrong_end == BLANKET.upper(), (
        f"marking the painting parent appeared to help ({wrong_end}); the "
        f"documented rule is that only the child matters. If Qt's behaviour "
        f"changed here, mark_paint_through()'s docstring needs updating."
    )
    print(f"[PASS] marking the painting parent changes nothing ({wrong_end})")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
