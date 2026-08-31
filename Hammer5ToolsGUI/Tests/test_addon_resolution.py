"""Choosing which addon is active on startup.

The setting used to default to the literal "addon". Every path helper turned that
into <cs2>/content/csgo_addons/addon, the first editor to touch it created the
folder for real, and from then on the "is the saved addon real?" check saw a
genuine addon and stopped correcting anything.
"""
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from gui.shell import addon_selector as sel


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def selector(qapp, monkeypatch):
    """An AddonSelector whose disk and settings are entirely in memory."""
    saved = {"addon": ""}
    monkeypatch.setattr(sel, "get_cs2_path", lambda: r"C:\cs2")
    monkeypatch.setattr(sel, "get_settings_value",
                        lambda section, key, default=None: saved.get(key, default))
    monkeypatch.setattr(sel, "set_addon_name", lambda name: saved.__setitem__("addon", name))
    chooser = sel.AddonSelector(QWidget())
    chooser.saved = saved
    return chooser


def test_nothing_saved_picks_a_real_addon(selector, monkeypatch):
    monkeypatch.setattr(sel, "list_addons", lambda _: ["de_swamp", "de_ober"])

    found = selector.resolve_saved_addon()

    assert selector.saved["addon"] in found
    assert selector.saved["addon"] != "addon"


def test_a_saved_addon_that_still_exists_is_kept(selector, monkeypatch):
    selector.saved["addon"] = "de_ober"
    monkeypatch.setattr(sel, "list_addons", lambda _: ["de_swamp", "de_ober"])

    selector.resolve_saved_addon()

    assert selector.saved["addon"] == "de_ober"


def test_a_saved_addon_that_vanished_is_replaced(selector, monkeypatch):
    selector.saved["addon"] = "de_deleted"
    monkeypatch.setattr(sel, "list_addons", lambda _: ["de_swamp"])

    selector.resolve_saved_addon()

    assert selector.saved["addon"] == "de_swamp"


def test_declining_to_create_leaves_no_addon_selected(selector, monkeypatch):
    """Not a placeholder name -- nothing. Callers get None from the path helpers."""
    monkeypatch.setattr(sel, "list_addons", lambda _: [])
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))

    found = selector.resolve_saved_addon()

    assert found == []
    assert selector.saved["addon"] == ""


def test_the_create_offer_is_made_only_once_per_session(selector, monkeypatch):
    monkeypatch.setattr(sel, "list_addons", lambda _: [])
    asked = []

    def question(*args, **kwargs):
        asked.append(1)
        return QMessageBox.No

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))

    selector.resolve_saved_addon()
    selector.resolve_saved_addon()

    assert len(asked) == 1, "repopulating the combo must not re-prompt"
