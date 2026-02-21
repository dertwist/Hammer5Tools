"""Soundevent playback utility for CS2 via netcon.

This module provides a simple, fire-and-forget function to trigger
CS2 sound events using the already running CS2 instance started with
-netconport 2121. It uses the netconsole TCP transport located in dev/rcon_protocol.py.

Constraints:
- Fire-and-forget: no completion/finish detection.
- Fail silently if CS2 is not running or connection fails (returns False).
- Do not spawn a CS2 process. Only talk to an existing one.

If settings provide host/port values, they are used. Otherwise
defaults are host=127.0.0.1, port=2121.
"""
from __future__ import annotations

import socket
from contextlib import closing
from typing import Callable, Optional

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton

try:
    # Use settings if available to allow overriding host/port
    from src.settings.main import get_settings_value, debug  # type: ignore
    from src.styles.common import qt_stylesheet_button  # type: ignore
except Exception:  # Fallbacks if settings are not importable in some contexts
    def get_settings_value(section: str, key: str, default: Optional[str] = None) -> Optional[str]:
        return default
    def debug(msg: str):
        print(msg)
    qt_stylesheet_button = ""


def _get_netcon_target() -> tuple[str, int]:
    """Resolve netcon target host and port from settings with sane defaults."""
    host = get_settings_value('CS2', 'netcon_host', '127.0.0.1') or '127.0.0.1'
    try:
        port_str = get_settings_value('CS2', 'netcon_port', '2121') or '2121'
        port = int(float(port_str))
    except Exception:
        port = 2121
    return host, port


def _send_netcon_command(cmd: str) -> bool:
    """Send a single command line to CS2 netconsole.

    Args:
        cmd: The command to send (a single line, newline will be appended)

    Returns:
        True if the command was sent successfully, False otherwise.
    """
    host, port = _get_netcon_target()
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as client:
            client.settimeout(0.25)
            client.connect((host, port))
            # best-effort: ignore response and close immediately
            payload = (cmd.rstrip("\n") + "\n").encode('utf-8')
            client.sendall(payload)
        return True
    except Exception as e:
        # Silent failure per spec, but keep an internal debug log entry
        try:
            debug(f"[soundevent_player] Netcon send failed: {e}")
        except Exception:
            pass
        return False


def play_soundevent(event_name: str) -> bool:
    """Trigger a CS2 sound event by name using netconsole.

    This is fire-and-forget and will not raise dialogs. If CS2 is not
    running or netcon is unreachable, returns False.

    The function now sends two commands in order:
    1) snd_sos_stop_all_soundevents
    2) snd_sos_start_soundevent <event_name>

    Args:
        event_name: Sound event name to start (e.g., 'Player.Footstep')

    Returns:
        True if both commands were sent successfully, False otherwise.
    """
    if not event_name or not isinstance(event_name, str):
        return False
    # Stop any currently playing sound events, then start the requested one.
    ok1 = _send_netcon_command("snd_sos_stop_all_soundevents")
    ok2 = _send_netcon_command(f"snd_sos_start_soundevent {event_name}")
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
        if qt_stylesheet_button:
            self.play_button.setStyleSheet(qt_stylesheet_button)
        self.play_button.clicked.connect(self._on_play_clicked)
        self._layout.addWidget(self.play_button)

        # Stop button to stop all currently playing sound events
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.setIcon(QIcon(":/valve_common/icons/tools/common/control_stop.png"))
        if qt_stylesheet_button:
            self.stop_button.setStyleSheet(qt_stylesheet_button)
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
        # Send command via netcon (fire-and-forget)
        play_soundevent(str(name))

    def _on_stop_clicked(self):
        """Handle stop button click: stop all sound events."""
        _send_netcon_command("snd_sos_stop_all_soundevents")
