"""Soundevent playback utility for CS2 via netcon.

This module provides a simple, fire-and-forget function to trigger
CS2 sound events using the already running CS2 instance started with
-netconport 2121.

Constraints:
- Fire-and-forget: no completion/finish detection.
- Tell the user and return False when CS2 is not reachable.
- Do not spawn a CS2 process. Only talk to an existing one.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton

from gui.other.cs2_netcon import CS2Netcon
from gui.widgets import require_cs2


def _send_netcon_command(cmd: str) -> bool:
    """Send a single command line to CS2 netconsole. Kept for backwards compatibility."""
    return CS2Netcon.send(cmd)


def play_soundevent(event_name: str) -> bool:
    """Trigger a CS2 sound event by name using netconsole.

    Sends two commands in order:
    1) snd_sos_stop_all_soundevents
    2) snd_sos_start_soundevent <event_name>

    Returns:
        True if both commands were sent successfully, False otherwise.
    """
    if not event_name or not isinstance(event_name, str):
        return False
    if not require_cs2("play a soundevent"):
        return False
    ok1 = CS2Netcon.send("snd_sos_stop_all_soundevents")
    ok2 = CS2Netcon.send(f"snd_sos_start_soundevent {event_name}")
    return ok1 and ok2


class SoundEventPlayerWidget(QWidget):
    """A minimal soundevent player control with Play and Stop buttons.

    This widget triggers CS2 named sound events via netconsole using
    the shared play_soundevent() function and can stop all with a Stop
    control.

    Usage:
        widget = SoundEventPlayerWidget()
        widget.set_event_resolver(lambda: current_event_name)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._event_resolver: Optional[Callable[[], Optional[str]]] = None

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Play button with the same icon style as AudioPlayer
        self.play_button = QPushButton("Play current event", self)
        self.play_button.setIcon(QIcon(":/valve_common/icons/tools/common/control_play.png"))
        self.play_button.setProperty("h5Component", "legacyButton")
        self.play_button.clicked.connect(self._on_play_clicked)
        self._layout.addWidget(self.play_button)

        # Stop button to stop all currently playing sound events
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.setIcon(QIcon(":/valve_common/icons/tools/common/control_stop.png"))
        self.stop_button.setProperty("h5Component", "legacyButton")
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self._layout.addWidget(self.stop_button)

    def set_event_resolver(self, resolver: Callable[[], Optional[str]]):
        """Set a callable that returns the current selected soundevent name."""
        self._event_resolver = resolver

    def _on_play_clicked(self):
        """Handle play button click."""
        name = None
        try:
            if self._event_resolver is not None:
                name = self._event_resolver()
        except Exception:
            name = None
        if not name:
            return
        # play_soundevent() checks that CS2 is reachable and reports if not.
        play_soundevent(str(name))

    def _on_stop_clicked(self):
        """Handle stop button click: stop all sound events."""
        if not require_cs2("stop sound events"):
            return
        _send_netcon_command("snd_sos_stop_all_soundevents")
