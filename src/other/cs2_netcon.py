"""CS2 netconsole command sender.

Generic, reusable utility for sending console commands to a running CS2
instance via the netconsole TCP transport (-netconport 2121).

Usage:
    from src.other.cs2_netcon import CS2Netcon

    ok = CS2Netcon.send("sv_cheats 1")
    ok = CS2Netcon.send_many(["sv_cheats 1", "bot_kick"])

All methods are fire-and-forget:
- They never raise exceptions.
- They return True on success, False on failure.
- They do not spawn CS2; they only talk to an already-running instance.

IMPORTANT – why we do NOT join with semicolons:
  CS2's netcon TCP transport is line-oriented: each newline-terminated line is
  treated as one console command. The CS2 console's quote-aware semicolon
  splitting only happens when text is typed interactively. Over TCP, a raw ";"
  always acts as a command separator — even inside double-quoted strings — so
  ent_fire addoutput commands whose parameter contains ";" would be split at
  the wrong place. Sending each command on its own line avoids this entirely.
"""
from __future__ import annotations

import re
import socket
import time
import threading
from contextlib import closing
from typing import Callable, Optional, Sequence

try:
    from src.settings.main import get_settings_value, debug  # type: ignore
except Exception:
    def get_settings_value(section: str, key: str, default=None):
        return default
    def debug(msg: str):
        print(msg)


class CS2Netcon:
    """Static helper class for sending commands to CS2 via netconsole."""

    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 2121
    TIMEOUT = 2.0

    @staticmethod
    def _get_target() -> tuple[str, int]:
        """Resolve host/port from settings, falling back to defaults."""
        host = get_settings_value('CS2', 'netcon_host', CS2Netcon.DEFAULT_HOST) or CS2Netcon.DEFAULT_HOST
        try:
            port = int(float(get_settings_value('CS2', 'netcon_port', str(CS2Netcon.DEFAULT_PORT)) or CS2Netcon.DEFAULT_PORT))
        except Exception:
            port = CS2Netcon.DEFAULT_PORT
        return host, port

    @staticmethod
    def query(cvar: str, timeout: float = 3.0) -> Optional[str]:
        """Query a CS2 cvar and return its current value as a string.

        Sends the cvar name as a command and reads the response line which
        CS2 formats as:  "<cvar> = <value> ( def. ... )"  or
                         "<cvar> = <value>"
        Returns the raw value string (e.g. "true", "false", "1", "0"),
        or None if CS2 is unreachable or the response cannot be parsed.

        Args:
            cvar:    The cvar name to query (e.g. "r_always_render_all_windows").
            timeout: How long to wait for the response in seconds.

        Returns:
            Value string or None.
        """
        host, port = CS2Netcon._get_target()
        pattern = re.compile(
            r'^\s*' + re.escape(cvar) + r'\s*=\s*(\S+)',
            re.MULTILINE | re.IGNORECASE
        )
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                sock.settimeout(timeout)
                sock.connect((host, port))
                sock.sendall((cvar.strip() + "\n").encode('utf-8'))
                response = b""
                deadline = time.time() + timeout
                try:
                    while time.time() < deadline:
                        sock.settimeout(max(0.1, deadline - time.time()))
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        response += chunk
                        # Check accumulated response for the cvar pattern
                        text = response.decode('utf-8', errors='replace')
                        match = pattern.search(text)
                        if match:
                            value = match.group(1).strip(' "\'')
                            debug(f"[CS2Netcon] Query '{cvar}' = '{value}'")
                            return value
                except (TimeoutError, socket.timeout):
                    pass  # timeout is expected once all output is consumed

            # Final attempt to parse whatever we got
            text = response.decode('utf-8', errors='replace')
            match = pattern.search(text)
            if match:
                value = match.group(1).strip(' "\'')
                debug(f"[CS2Netcon] Query '{cvar}' = '{value}'")
                return value
            debug(f"[CS2Netcon] Query '{cvar}': could not parse response: {text!r}")
            return None
        except ConnectionRefusedError:
            debug(f"[CS2Netcon] Query: connection refused")
            return None
        except Exception as e:
            debug(f"[CS2Netcon] Query failed: {e}")
            return None

    @staticmethod
    def send(command: str) -> bool:
        """Send a single console command to CS2.

        Args:
            command: A single CS2 console command string.

        Returns:
            True if the command was delivered, False otherwise.
        """
        if not command or not isinstance(command, str):
            return False
        return CS2Netcon.send_many([command])

    @staticmethod
    def send_many(commands: Sequence[str]) -> bool:
        """Send multiple console commands to CS2.

        Each command is sent as a separate newline-terminated line over a
        single persistent TCP connection. This is the correct way to send
        commands that may contain semicolons inside quoted strings (e.g.
        ent_fire addoutput parameters).

        Args:
            commands: Sequence of CS2 console command strings.

        Returns:
            True if all commands were delivered, False otherwise.
        """
        filtered = [c.strip() for c in commands if c and isinstance(c, str) and c.strip()]
        if not filtered:
            return False

        host, port = CS2Netcon._get_target()
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                sock.settimeout(CS2Netcon.TIMEOUT)
                sock.connect((host, port))
                # Send every command as its own newline-terminated line.
                # Do NOT join with ";" — the netcon transport does not parse
                # quotes, so a ";" inside an ent_fire addoutput string would
                # be treated as a command separator at the TCP level.
                payload = "\n".join(c.rstrip("\n") for c in filtered) + "\n"
                sock.sendall(payload.encode('utf-8'))
            debug(f"[CS2Netcon] Sent {len(filtered)} command(s) ({len(payload)} bytes) to {host}:{port}")
            return True
        except ConnectionRefusedError:
            debug(f"[CS2Netcon] Connection refused – CS2 not running or netconport not set")
            return False
        except TimeoutError:
            debug(f"[CS2Netcon] Connection timed out to {host}:{port}")
            return False
        except Exception as e:
            debug(f"[CS2Netcon] Send failed: {e}")
            return False

    @staticmethod
    def send_and_listen(
        command: str,
        sentinel: str,
        on_line: 'Optional[Callable[[str], None]]' = None,
        timeout: float = 300.0,
        poll_interval: float = 0.1,
        stop_event: 'Optional[threading.Event]' = None,
    ) -> bool:
        """Send a command and keep reading output until *sentinel* appears in a line.

        This keeps the TCP connection open and streams every line back via the
        *on_line* callback.  It returns True when the sentinel is found, or
        False on timeout / error / abort.

        Args:
            command:        Console command to send (e.g. "buildcubemaps").
            sentinel:       A substring to look for in the output that signals
                            completion (e.g. "Cubemap build complete").
            on_line:        Optional callback invoked with each output line.
            timeout:        Maximum seconds to wait for the sentinel.
            poll_interval:  Seconds between recv attempts when no data arrives.
            stop_event:     Optional threading.Event; if set, aborts early.

        Returns:
            True if the sentinel was detected, False otherwise.
        """
        host, port = CS2Netcon._get_target()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(poll_interval)
            sock.connect((host, port))

            # Send the command
            sock.sendall((command.strip() + "\n").encode('utf-8'))
            debug(f"[CS2Netcon] send_and_listen: sent '{command}' to {host}:{port}")

            buffer = b""
            deadline = time.time() + timeout

            while time.time() < deadline:
                if stop_event and stop_event.is_set():
                    debug("[CS2Netcon] send_and_listen: aborted via stop_event")
                    sock.close()
                    return False

                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        # Server closed the connection
                        break
                    buffer += chunk
                except (TimeoutError, socket.timeout):
                    continue
                except OSError:
                    break

                # Process complete lines
                while b"\n" in buffer:
                    line_bytes, buffer = buffer.split(b"\n", 1)
                    line = line_bytes.decode('utf-8', errors='replace').rstrip()
                    if line:
                        if on_line:
                            on_line(line)
                        if sentinel in line:
                            debug(f"[CS2Netcon] send_and_listen: sentinel '{sentinel}' found")
                            sock.close()
                            return True

            sock.close()
            debug(f"[CS2Netcon] send_and_listen: timed out after {timeout}s")
            return False
        except ConnectionRefusedError:
            debug("[CS2Netcon] send_and_listen: connection refused")
            return False
        except Exception as e:
            debug(f"[CS2Netcon] send_and_listen failed: {e}")
            return False

