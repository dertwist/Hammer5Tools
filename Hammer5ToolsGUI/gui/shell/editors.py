"""The editors the main window hosts, and the operations that fan out over them.

Adding an editor means adding one ``EditorSlot`` to the window's slot list and
one build method — not editing three hardcoded lists (lazy tab builders,
addon-switch teardown, unsaved-file collection) that had to be kept in sync.

The functions here take the window as a plain object and only touch
``getattr``/``setattr`` plus ``layout()``/``close()``/``deleteLater()`` on the
editors, so they are testable without a QApplication.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class EditorSlot:
    """One editor hosted in a main-window tab.

    ``build`` is the callable that constructs the editor on first tab
    activation. A slot with ``build=None`` is built eagerly elsewhere (once, in
    ``setup_tabs``) and is never rebuilt or torn down on an addon switch — it
    still takes part in unsaved-file collection.

    ``page`` may be None for a tab that was not created, in which case the slot
    is skipped everywhere.
    """

    attr: str
    label: str
    page: object
    build: Callable[[], None] | None = None
    requires_cs2: bool = False

    @property
    def rebuildable(self) -> bool:
        return self.build is not None and self.page is not None


def register_builders(slots, builders: dict, cs2_available: bool) -> None:
    """Map each rebuildable tab page to its build callable in ``builders``.

    Slots marked ``requires_cs2`` are left out when CS2 is unavailable, so their
    tab stays empty rather than building an editor that cannot work.
    """
    for slot in slots:
        if not slot.rebuildable:
            continue
        if slot.requires_cs2 and not cs2_available:
            continue
        builders[slot.page] = slot.build


def teardown(window, slots) -> None:
    """Close and drop every rebuildable editor, clearing its window attribute.

    Removing the widget from its layout before deleting it keeps the layout from
    holding a stale item until deleteLater runs.
    """
    for slot in slots:
        if not slot.rebuildable:
            continue
        editor = getattr(window, slot.attr, None)
        if editor is None:
            continue
        layout = slot.page.layout()
        if layout is not None:
            layout.removeWidget(editor)
        editor.close()
        editor.deleteLater()
        setattr(window, slot.attr, None)


def collect_unsaved(window, slots) -> list:
    """(editor_label, file_label, save_callable) for every unsaved open file.

    An editor without an ``unsaved_files`` method simply contributes nothing.
    """
    unsaved = []
    for slot in slots:
        if slot.page is None:
            continue
        editor = getattr(window, slot.attr, None)
        if editor is None:
            continue
        for file_label, save in getattr(editor, "unsaved_files", list)():
            unsaved.append((slot.label, file_label, save))
    return unsaved
