"""The console channel: launch flags, command framing, and log listening.

CS2 removed -netconport, so commands now go through the pipe CS2 opens for
-concommandpipe and output is read from the -con_logfile log. These cover the
parts that can break without CS2 running.
"""

from __future__ import annotations

import threading

import pytest

from gui.other import cs2_netcon
from gui.other.cs2_netcon import LAUNCH_ARGS, PIPE_IN, PIPE_OUT, CS2Console


@pytest.fixture
def pipe(monkeypatch):
    """Stand in for the pipe server: record the lines that would be written."""

    class FakePipe:
        started = False
        connected = True
        written: list = []

        def start(self):
            FakePipe.started = True
            return True

        def is_connected(self):
            return FakePipe.connected

        def write_lines(self, lines):
            if not FakePipe.connected:
                return False
            FakePipe.written.extend(lines)
            return True

    fake = FakePipe()
    FakePipe.written = []
    FakePipe.connected = True
    monkeypatch.setattr(cs2_netcon, "_pipes", fake)
    return FakePipe


def test_launch_flags_are_added(pipe):
    commands = CS2Console.prepare_launch(" -addon de_test -tool hammer")
    assert LAUNCH_ARGS in commands
    assert "-insecure" in commands          # the engine refuses the pipe without it
    assert PIPE_IN in commands and PIPE_OUT in commands
    assert "-con_logfile" in commands


def test_the_pipes_are_served_before_cs2_starts(pipe):
    """CS2 is the pipe client and asserts at boot when the pipe is missing."""
    CS2Console.prepare_launch("")
    assert pipe.started is True


def test_the_dead_netconport_flag_is_dropped(pipe):
    """Saved launch options still carry it; CS2 no longer knows the flag."""
    commands = CS2Console.prepare_launch(" -tools -netconport 2121 -steam")
    assert "-netconport" not in commands
    assert "2121" not in commands
    assert "-tools" in commands and "-steam" in commands


def test_flags_are_not_added_twice(pipe):
    once = CS2Console.prepare_launch(" -tools")
    twice = CS2Console.prepare_launch(once)
    assert twice.count("-concommandpipe") == 1


def test_each_command_is_its_own_line(pipe):
    """A ';' inside a quoted ent_fire parameter must not split the command."""
    assert CS2Console.send_many([
        'ent_fire !self addoutput "OnUser1 a;b;c"',
        "sv_cheats 1",
    ]) is True
    assert pipe.written == [
        'ent_fire !self addoutput "OnUser1 a;b;c"',
        "sv_cheats 1",
    ]


def test_blank_commands_are_not_sent(pipe):
    assert CS2Console.send("") is False
    assert CS2Console.send_many(["", "   "]) is False
    assert pipe.written == []


def test_sending_fails_when_cs2_is_not_attached(pipe):
    pipe.connected = False
    assert CS2Console.is_available() is False
    assert CS2Console.send("sv_cheats 1") is False


def test_listen_reports_the_sentinel(tmp_path, monkeypatch, pipe):
    log = tmp_path / "console.log"
    log.write_text("old line\n", encoding="utf-8")
    monkeypatch.setattr(CS2Console, "log_path", staticmethod(lambda: log))

    seen: list = []
    offset = CS2Console.log_offset()

    def append_later():
        with open(log, "a", encoding="utf-8") as handle:
            handle.write("building...\nCubemap build complete\n")

    threading.Timer(0.2, append_later).start()
    found = CS2Console.listen(on_line=seen.append, sentinel="Cubemap build complete",
                              timeout=10.0, start_offset=offset)

    assert found is True
    assert "building..." in seen
    assert "old line" not in seen   # only output produced after we started


def test_listen_gives_up_on_timeout(tmp_path, monkeypatch, pipe):
    log = tmp_path / "console.log"
    log.write_text("", encoding="utf-8")
    monkeypatch.setattr(CS2Console, "log_path", staticmethod(lambda: log))
    assert CS2Console.listen(sentinel="never appears", timeout=0.3) is False


def test_listen_survives_cs2_restarting(tmp_path, monkeypatch, pipe):
    """A fresh CS2 truncates the log; listening must not stall past the end."""
    log = tmp_path / "console.log"
    log.write_text("a" * 5000 + "\n", encoding="utf-8")
    monkeypatch.setattr(CS2Console, "log_path", staticmethod(lambda: log))

    seen: list = []

    def restart():
        log.write_text("fresh boot\nMainMenu ready\n", encoding="utf-8")

    threading.Timer(0.2, restart).start()
    found = CS2Console.listen(on_line=seen.append, sentinel="MainMenu ready",
                              timeout=10.0, start_offset=5001)
    assert found is True


def test_send_and_listen_needs_a_delivered_command(pipe):
    pipe.connected = False
    assert CS2Console.send_and_listen("buildcubemaps", "done", timeout=0.2) is False


def test_query_returns_none_when_the_console_socket_is_taken(monkeypatch, pipe):
    """vconsole2.exe holds the single VConsole slot; callers handle None."""
    monkeypatch.setattr(CS2Console, "_vconsole_exchange", staticmethod(lambda *a: ""))
    assert CS2Console.query("r_always_render_all_windows") is None


def test_query_parses_the_cvar_reply(monkeypatch, pipe):
    monkeypatch.setattr(CS2Console, "_vconsole_exchange",
                        staticmethod(lambda *a: "r_always_render_all_windows = true ( def. false )"))
    assert CS2Console.query("r_always_render_all_windows") == "true"


def test_query_parses_a_reply_wrapped_in_vconsole_framing(monkeypatch, pipe):
    """The reply is not at a line start: VConsole packet bytes precede it."""
    framed = "PRNT\x00\xd4\x00\x00\x00:\x00\x00\t@\x98\xadqueusv_gravity = 800\n\x00"
    monkeypatch.setattr(CS2Console, "_vconsole_exchange", staticmethod(lambda *a: framed))
    assert CS2Console.query("sv_gravity") == "800"


def test_query_does_not_match_a_different_cvar(monkeypatch, pipe):
    monkeypatch.setattr(CS2Console, "_vconsole_exchange",
                        staticmethod(lambda *a: "mp_sv_gravity_scale = 3\n"))
    assert CS2Console.query("sv_gravity") is None


def test_the_old_name_still_works():
    """Call sites import CS2Netcon; the transport changed, the name did not."""
    assert cs2_netcon.CS2Netcon is CS2Console
