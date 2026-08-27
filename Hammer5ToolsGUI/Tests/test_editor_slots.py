"""The editor registry replaces three hardcoded lists that had to stay in sync.

These exercise the fan-out functions with plain fakes: no QApplication, because
the registry only ever touches getattr/setattr plus layout()/close()/deleteLater().
"""

from gui.shell.editors import EditorSlot, collect_unsaved, register_builders, teardown


class _Layout:
    def __init__(self):
        self.removed = []

    def removeWidget(self, widget):
        self.removed.append(widget)


class _Page:
    def __init__(self, layout=None):
        self._layout = _Layout() if layout is None else layout

    def layout(self):
        return self._layout


class _Editor:
    def __init__(self, unsaved=()):
        self._unsaved = list(unsaved)
        self.closed = False
        self.deleted = False

    def unsaved_files(self):
        return self._unsaved

    def close(self):
        self.closed = True

    def deleteLater(self):
        self.deleted = True


class _Window:
    pass


def _slots(built=None, eager_page=None):
    """Two rebuildable slots (one CS2-gated) plus one eagerly-built slot."""
    built = [] if built is None else built
    return (
        EditorSlot('always', "Always", _Page(), lambda: built.append('always')),
        EditorSlot('gated', "Gated", _Page(), lambda: built.append('gated'), requires_cs2=True),
        EditorSlot('eager', "Eager", _Page() if eager_page is None else eager_page),
    )


def test_cs2_gated_editors_are_not_registered_without_cs2():
    slots = _slots()
    builders = {}
    register_builders(slots, builders, cs2_available=False)
    assert list(builders) == [slots[0].page]

    builders = {}
    register_builders(slots, builders, cs2_available=True)
    assert list(builders) == [slots[0].page, slots[1].page]


def test_eagerly_built_slots_are_never_registered_or_torn_down():
    slots = _slots()
    builders = {}
    register_builders(slots, builders, cs2_available=True)
    assert slots[2].page not in builders

    window = _Window()
    window.eager = _Editor()
    teardown(window, slots)
    # Survives the addon switch: still present, never closed.
    assert window.eager.closed is False
    assert window.eager is not None


def test_teardown_removes_from_layout_then_clears_the_attribute():
    slots = _slots()
    window = _Window()
    window.always = _Editor()
    editor = window.always

    teardown(window, slots)

    assert slots[0].page.layout().removed == [editor]
    assert editor.closed and editor.deleted
    assert window.always is None


def test_teardown_skips_editors_that_were_never_built():
    slots = _slots()
    window = _Window()  # no attributes set at all
    teardown(window, slots)  # must not raise
    assert getattr(window, 'always', None) is None


def test_unsaved_files_are_labelled_by_editor_and_keep_slot_order():
    slots = _slots()
    window = _Window()
    window.always = _Editor([("a.vsmart", 'save_a')])
    window.eager = _Editor([("b.wav", 'save_b')])

    assert collect_unsaved(window, slots) == [
        ("Always", "a.vsmart", 'save_a'),
        ("Eager", "b.wav", 'save_b'),
    ]


def test_editor_without_unsaved_files_contributes_nothing():
    slots = _slots()
    window = _Window()
    window.always = object()  # no unsaved_files method
    assert collect_unsaved(window, slots) == []


def test_slots_with_no_page_are_skipped_everywhere():
    slots = (EditorSlot('missing', "Missing", None, lambda: None),)
    window = _Window()
    window.missing = _Editor([("x", 'save_x')])

    builders = {}
    register_builders(slots, builders, cs2_available=True)
    assert builders == {}
    teardown(window, slots)          # must not raise on page=None
    assert collect_unsaved(window, slots) == []
