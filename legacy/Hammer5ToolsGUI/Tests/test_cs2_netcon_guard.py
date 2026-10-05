"""No console command may reach CS2 without checking it is reachable first.

CS2 only opens the command pipe when Hammer5Tools launched it. Sending blind
meant the UI looked like it worked while nothing happened.
"""

from __future__ import annotations

import os
import sys

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

app = QApplication.instance() or QApplication(sys.argv)

from gui.other.cs2_netcon import CS2Netcon
from gui.widgets import require_cs2
from gui.widgets import common


@pytest.fixture
def cs2(monkeypatch):
    """Fake CS2: record what would be sent and what the user would be told."""

    class Fake:
        available = False
        sent: list = []
        notices: list = []

    Fake.sent = []
    Fake.notices = []
    # The notice is rate limited; each test starts from a clean slate.
    common._last_cs2_notice = 0.0
    monkeypatch.setattr(CS2Netcon, "is_available", staticmethod(lambda *a, **k: Fake.available))
    monkeypatch.setattr(CS2Netcon, "send", staticmethod(lambda cmd: Fake.sent.append(cmd) or True))
    monkeypatch.setattr(
        QMessageBox,
        "information",
        staticmethod(lambda parent, title, text, *a, **k: Fake.notices.append((title, text))),
    )
    return Fake


def test_guard_passes_when_cs2_is_reachable(cs2):
    cs2.available = True
    assert require_cs2("do a thing") is True
    assert cs2.notices == []


def test_guard_explains_itself_when_cs2_is_missing(cs2):
    assert require_cs2("do a thing") is False
    (title, text), = cs2.notices
    assert title == "CS2 is not running"
    assert text.startswith("To do a thing, CS2 must be launched through Hammer5Tools.")
    # The wording has to name the alternative, or users retry the same way.
    assert "launch options" in text


def test_playing_a_soundevent_sends_nothing_without_cs2(cs2):
    from gui.editors.soundevent_editor.soundevent_player import play_soundevent

    assert play_soundevent("amb.test") is False
    assert cs2.sent == []
    assert len(cs2.notices) == 1


def test_playing_a_soundevent_sends_once_cs2_is_up(cs2):
    from gui.editors.soundevent_editor.soundevent_player import play_soundevent

    cs2.available = True
    assert play_soundevent("amb.test") is True
    assert cs2.sent == [
        "snd_sos_stop_all_soundevents",
        "snd_sos_start_soundevent amb.test",
    ]
    assert cs2.notices == []


def test_the_stop_button_is_guarded_too(cs2):
    from gui.editors.soundevent_editor.soundevent_player import SoundEventPlayerWidget

    widget = SoundEventPlayerWidget()
    widget.set_event_resolver(lambda: "amb.test")
    widget._on_stop_clicked()
    assert cs2.sent == []
    assert len(cs2.notices) == 1
    widget.deleteLater()


def test_a_short_notice_uses_a_plain_message_box(cs2):
    """ErrorInfo's details pane and Report button belong to real failures."""
    import inspect

    from gui.widgets import common

    source = inspect.getsource(common.require_cs2)
    assert "QMessageBox.information" in source
    assert "ErrorInfo(" not in source  # the comment may name it; a call must not


def test_the_notice_does_not_repeat_on_every_click(cs2):
    """Selecting sound events fires the guard per click; one box is enough."""
    for _ in range(5):
        assert require_cs2("play a soundevent") is False
    assert len(cs2.notices) == 1
