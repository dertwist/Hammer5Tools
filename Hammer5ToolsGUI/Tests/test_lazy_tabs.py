"""Editors build on first tab activation, not all at once.

Fewer live widgets is the only measured lever on live-theme-switch cost, so the
regression-prone paths are the ones that reach an editor without the user
clicking its tab: quick-open and the startup tab restore.
"""
import pytest

from PySide6.QtWidgets import QApplication, QTabWidget, QWidget, QVBoxLayout

from gui.app_core import Widget


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class _Host:
    """A Widget stand-in holding only what the lazy-tab code touches."""

    _ensure_tab = Widget._ensure_tab
    current_tab = Widget.current_tab
    open_file_in_smartprop = Widget.open_file_in_smartprop
    open_file_in_soundevent = Widget.open_file_in_soundevent

    def __init__(self):
        self.tabs = QTabWidget()
        self.built = []
        pages = {}
        for name in ("BatchCreator_tab", "smartpropeditor_tab", "soundeditor_tab"):
            page = QWidget()
            QVBoxLayout(page)
            self.tabs.addTab(page, name)
            pages[name] = page
        self.ui = type("ui", (), dict(pages, MainWindowTools_tabs=self.tabs))()
        self._tab_builders = {p: (lambda n=n, p=p: self._build(n)) for n, p in pages.items()}
        self.tabs.currentChanged.connect(self._ensure_tab)

    def _build(self, name):
        self.built.append(name)
        setattr(self, {"smartpropeditor_tab": "SmartPropEditorMainWindow",
                       "soundeditor_tab": "SoundEventEditorMainWindow"}.get(name, name),
                _Editor())

    def check_addon_mismatch(self, hint):
        return True


class _Editor:
    def __init__(self):
        self.opened = None

    def open_file(self, filename):
        self.opened = filename

    def load_soundevents(self, filepath):
        self.opened = filepath


def test_only_the_visible_tab_builds(qapp):
    host = _Host()
    host._ensure_tab()
    assert host.built == ["BatchCreator_tab"]

    host.tabs.setCurrentIndex(1)
    host.tabs.setCurrentIndex(1)
    assert host.built == ["BatchCreator_tab", "smartpropeditor_tab"]


def test_quick_open_builds_the_target_editor(qapp):
    host = _Host()
    host.open_file_in_smartprop("C:/x.vsmart")
    assert host.SmartPropEditorMainWindow.opened.endswith("x.vsmart")

    # Already on the sound tab and still unbuilt (no currentChanged to come):
    # the explicit _ensure_tab() call is the only thing that builds it.
    host = _Host()
    host.tabs.blockSignals(True)
    host.tabs.setCurrentIndex(2)
    host.tabs.blockSignals(False)
    host.open_file_in_soundevent("C:/y.vsndevts")
    assert host.SoundEventEditorMainWindow.opened.endswith("y.vsndevts")


def test_restored_startup_tab_is_not_empty(qapp, monkeypatch):
    monkeypatch.setattr("gui.app_core.get_settings_value", lambda *a: "2")
    host = _Host()
    host.current_tab(False)
    assert host.built == ["soundeditor_tab"]
