"""One channel to a running CS2 instance: send console commands, listen to output.

CS2 dropped the netconsole: `-netconport` is absent from every binary in build
1.41.7.8 (Aug 2026), so nothing ever listened on port 2121 again and every send
failed silently. The transport is now:

    send    the console command pipe CS2 opens for -concommandpipe
    listen  the console log CS2 writes for -con_logfile, tailed
    query   the VConsole socket on port 29000, best effort (see query())

Why this combination: the VConsole socket serves exactly one client, so using it
for sends would lock the user out of vconsole2.exe. The pipe is independent --
commands sent through it run while VConsole is attached -- but the engine only
redirects command output to the pipe's write side for synchronous execution,
and piped commands are queued, so output comes from the log instead.

CS2 is the *client* of the pipe: it opens the path we pass it, and asserts at
boot (writing a minidump) when the pipe is not already there. So the pipe must
exist before CS2 starts and the path must be a full \\\\.\\pipe\\NAME. Every
launch therefore goes through prepare_launch(), which also adds -insecure --
the engine refuses -concommandpipe without it.

Usage:
    from gui.other.cs2_netcon import CS2Console

    commands = CS2Console.prepare_launch(commands)   # before spawning CS2
    CS2Console.send("sv_cheats 1")
    CS2Console.send_many(["sv_cheats 1", "bot_kick"])
    CS2Console.listen(print, sentinel="Cubemap build complete", timeout=600)

All methods are fire-and-forget: they never raise, and report failure by
returning False/None.
"""
from __future__ import annotations

import ctypes
import logging
import os
import re
import socket
import struct
import sys
import threading
import time
from contextlib import closing
from pathlib import Path
from typing import Callable, Optional, Sequence

log = logging.getLogger(__name__)

# Pipe paths and log name are fixed: CS2 gets them on its command line, and a
# single Hammer5Tools talks to a single CS2.
PIPE_IN = r"\\.\pipe\hammer5tools_cmd"
PIPE_OUT = r"\\.\pipe\hammer5tools_out"
LOG_NAME = "hammer5tools_console.log"

# -insecure is mandatory: engine2 rejects the flag without it
# ("-concommandpipe requires -insecure").
LAUNCH_ARGS = f"-insecure -concommandpipe {PIPE_IN},{PIPE_OUT} -con_logfile {LOG_NAME}"

_IS_WINDOWS = sys.platform == "win32"

# Win32 named pipe constants
_PIPE_ACCESS_DUPLEX = 0x00000003
_PIPE_TYPE_BYTE = 0x00000000  # CS2 wraps the handle in a C FILE*, so byte mode
_INVALID_HANDLE = ctypes.c_void_p(-1).value
_ERROR_PIPE_CONNECTED = 535
_PIPE_BUFFER = 1 << 20

if _IS_WINDOWS:
    _k32 = ctypes.windll.kernel32
    _k32.CreateNamedPipeW.restype = ctypes.c_void_p
    _k32.CreateNamedPipeW.argtypes = [
        ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
        ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
    ]
    _k32.ConnectNamedPipe.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    _k32.WriteFile.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p,
    ]
    _k32.FlushFileBuffers.argtypes = [ctypes.c_void_p]
    _k32.DisconnectNamedPipe.argtypes = [ctypes.c_void_p]
    _k32.CloseHandle.argtypes = [ctypes.c_void_p]
else:  # pragma: no cover - the tool only ships on Windows
    _k32 = None


class _PipeServer:
    """Keeps the command pipes served so CS2 can connect whenever it starts.

    CS2 is restarted often (map builds kill and relaunch it), so each pipe is
    served by a thread that re-creates its instance as soon as the old client
    goes away.
    """

    def __init__(self):
        self._handles: dict[str, Optional[int]] = {PIPE_IN: None, PIPE_OUT: None}
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}

    def start(self) -> bool:
        """Serve both pipes. Idempotent; safe to call before every launch."""
        if not _IS_WINDOWS:
            return False
        for path in (PIPE_IN, PIPE_OUT):
            thread = self._threads.get(path)
            if thread is None or not thread.is_alive():
                thread = threading.Thread(
                    target=self._serve, args=(path,), daemon=True,
                    name=f"cs2-pipe{path.rsplit(chr(92), 1)[-1]}")
                self._threads[path] = thread
                thread.start()
        return True

    def _serve(self, path: str) -> None:
        while True:
            handle = _k32.CreateNamedPipeW(
                path, _PIPE_ACCESS_DUPLEX, _PIPE_TYPE_BYTE, 4,
                _PIPE_BUFFER, _PIPE_BUFFER, 0, None)
            if handle == _INVALID_HANDLE or not handle:
                # Another Hammer5Tools already owns the name, or the OS said no.
                time.sleep(2.0)
                continue
            connected = _k32.ConnectNamedPipe(handle, None)
            if not connected and _k32.GetLastError() != _ERROR_PIPE_CONNECTED:
                _k32.CloseHandle(ctypes.c_void_p(handle))
                time.sleep(0.5)
                continue

            with self._lock:
                self._handles[path] = handle
            # Hold the instance until CS2 goes away, then serve a fresh one --
            # a zero-byte write is the cheapest way to notice a dead client.
            while self._probe(handle):
                time.sleep(1.0)
            with self._lock:
                if self._handles.get(path) == handle:
                    self._handles[path] = None
            _k32.DisconnectNamedPipe(ctypes.c_void_p(handle))
            _k32.CloseHandle(ctypes.c_void_p(handle))

    @staticmethod
    def _probe(handle: int) -> bool:
        """Whether the client is still attached (zero-byte write)."""
        written = ctypes.c_uint32(0)
        return bool(_k32.WriteFile(ctypes.c_void_p(handle), b"", 0,
                                   ctypes.byref(written), None))

    def is_connected(self) -> bool:
        with self._lock:
            handle = self._handles.get(PIPE_IN)
        return bool(handle) and self._probe(handle)

    def write_lines(self, lines: Sequence[str]) -> bool:
        """Write newline-terminated command lines to the pipe CS2 reads."""
        with self._lock:
            handle = self._handles.get(PIPE_IN)
        if not handle:
            return False
        payload = ("".join(line.rstrip("\n") + "\n" for line in lines)).encode("utf-8")
        written = ctypes.c_uint32(0)
        ok = _k32.WriteFile(ctypes.c_void_p(handle), payload, len(payload),
                            ctypes.byref(written), None)
        if not ok:
            # Client is gone; let the serving thread put up a fresh instance.
            with self._lock:
                if self._handles.get(PIPE_IN) == handle:
                    self._handles[PIPE_IN] = None
            return False
        _k32.FlushFileBuffers(ctypes.c_void_p(handle))
        return written.value == len(payload)


_pipes = _PipeServer()


class CS2Console:
    """Send console commands to CS2 and listen to its console output."""

    VCONSOLE_HOST = "127.0.0.1"
    VCONSOLE_PORT = 29000
    # The VConsole server greets a client it actually serves with a large dump;
    # a near-empty greeting means another client (vconsole2.exe) holds the slot.
    _VCONSOLE_GREETING_MIN = 100_000

    # ---------------------------------------------------------------- launch

    @staticmethod
    def prepare_launch(commands: str) -> str:
        """Serve the command pipes and return *commands* with our flags added.

        Must be called before CS2 is spawned: CS2 opens the pipe on startup and
        asserts if it is missing. Also drops the dead -netconport flag that older
        settings still carry.

        Args:
            commands: The CS2 command line built from settings.

        Returns:
            The command line to actually launch with.
        """
        _pipes.start()
        commands = re.sub(r"\s*-netconport\s+\S+", "", commands or "")
        if "-concommandpipe" not in commands:
            commands = f"{commands} {LAUNCH_ARGS}".strip()
        return commands

    @staticmethod
    def log_path() -> Optional[Path]:
        """Absolute path of the console log CS2 writes, or None if unknown."""
        try:
            from gui.settings.common import get_cs2_path
        except Exception:
            return None
        cs2_path = get_cs2_path()
        if not cs2_path:
            return None
        return Path(cs2_path) / "game" / "csgo" / LOG_NAME

    # --------------------------------------------------------------- sending

    @staticmethod
    def is_available(timeout: float = 0.3) -> bool:
        """Whether CS2 is attached to our command pipe.

        Only a CS2 that Hammer5Tools launched is attached, so this doubles as
        "was CS2 started through the tool". *timeout* is accepted for callers
        written against the old socket transport; the check is local and fast.
        """
        return _pipes.is_connected()

    @staticmethod
    def wait_until_available(timeout: float = 180.0,
                             stop_event: Optional[threading.Event] = None) -> bool:
        """Block until CS2 attaches to the command pipe (or *timeout*)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if stop_event is not None and stop_event.is_set():
                return False
            if _pipes.is_connected():
                return True
            time.sleep(1.0)
        return False

    @staticmethod
    def send(command: str) -> bool:
        """Send a single console command to CS2."""
        if not command or not isinstance(command, str):
            return False
        return CS2Console.send_many([command])

    @staticmethod
    def send_many(commands: Sequence[str]) -> bool:
        """Send several console commands, one per line.

        Each command goes on its own line: the engine reads the pipe as a text
        stream, so a ";" inside a quoted ent_fire parameter would otherwise be
        treated as a command separator.

        Returns:
            True if every command was delivered.
        """
        filtered = [c.strip() for c in commands if c and isinstance(c, str) and c.strip()]
        if not filtered:
            return False
        return _pipes.write_lines(filtered)

    # ------------------------------------------------------------- listening

    @staticmethod
    def listen(on_line: Optional[Callable[[str], None]] = None,
               sentinel: Optional[str] = None,
               timeout: float = 300.0,
               poll_interval: float = 0.1,
               stop_event: Optional[threading.Event] = None,
               start_offset: Optional[int] = None) -> bool:
        """Tail CS2's console log, feeding lines to *on_line*.

        Args:
            on_line:      Called with each new console line.
            sentinel:     Substring that ends the wait; None tails until timeout.
            timeout:      Maximum seconds to wait.
            poll_interval: Seconds between reads when the log is idle.
            stop_event:   Set to abort early.
            start_offset: Byte offset to read from; defaults to the current end.

        Returns:
            True when *sentinel* was seen, False on timeout, abort or no log.
        """
        path = CS2Console.log_path()
        if path is None:
            return False

        deadline = time.time() + timeout
        offset = start_offset if start_offset is not None else CS2Console.log_offset()
        buffer = ""
        while time.time() < deadline:
            if stop_event is not None and stop_event.is_set():
                return False
            try:
                # Reopened every pass: CS2 rewrites the log when it restarts.
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    handle.seek(0, os.SEEK_END)
                    size = handle.tell()
                    if size < offset:  # log was truncated by a fresh CS2
                        offset = 0
                    handle.seek(offset)
                    chunk = handle.read()
                    offset = handle.tell()
            except OSError:
                time.sleep(poll_interval)
                continue

            if chunk:
                buffer += chunk
                lines = buffer.split("\n")
                buffer = lines.pop()  # keep the partial trailing line
                for line in lines:
                    line = line.rstrip()
                    if not line:
                        continue
                    if on_line:
                        on_line(line)
                    if sentinel and sentinel in line:
                        return True
            else:
                time.sleep(poll_interval)
        return False

    @staticmethod
    def log_offset() -> int:
        """Current end of the console log, to listen from after sending."""
        path = CS2Console.log_path()
        try:
            return path.stat().st_size if path else 0
        except OSError:
            return 0

    @staticmethod
    def send_and_listen(command: str,
                        sentinel: str,
                        on_line: Optional[Callable[[str], None]] = None,
                        timeout: float = 300.0,
                        poll_interval: float = 0.1,
                        stop_event: Optional[threading.Event] = None) -> bool:
        """Send *command* and tail the log until *sentinel* appears.

        Returns:
            True if the sentinel was seen, False otherwise.
        """
        offset = CS2Console.log_offset()
        if not CS2Console.send(command):
            return False
        return CS2Console.listen(on_line=on_line, sentinel=sentinel, timeout=timeout,
                                 poll_interval=poll_interval, stop_event=stop_event,
                                 start_offset=offset)

    # ----------------------------------------------------------- cvar query

    @staticmethod
    def query(cvar: str, timeout: float = 3.0) -> Optional[str]:
        """Read a cvar's current value, or None if it cannot be read.

        This is the one thing the pipe cannot do: cvar replies are console
        output, and the engine does not route the output of queued (piped)
        commands to the pipe's write side, nor into the console log. So the
        value comes from the VConsole socket, which is only readable while
        vconsole2.exe is not attached. Callers must handle None.
        """
        if not cvar:
            return None
        response = CS2Console._vconsole_exchange(cvar.strip(), timeout)
        if not response:
            return None
        # Unanchored on purpose: replies arrive inside VConsole's binary framing,
        # which butts a 4-character channel tag right against the text
        # ("...queusv_gravity = 800"), so neither a line start nor a word
        # boundary is available. Requiring "= <value>" right after the name is
        # what keeps a longer cvar (mp_sv_gravity_scale) from matching.
        match = re.search(re.escape(cvar) + r"\s*=\s*(\S+)", response, re.IGNORECASE)
        return match.group(1).strip(" \"'") if match else None

    @staticmethod
    def _vconsole_exchange(command: str, timeout: float) -> str:
        """Run one command on the VConsole socket and return the output text.

        Returns an empty string when the socket is unreachable or another
        client (the user's vconsole2.exe) already holds the single slot.
        """
        try:
            with closing(socket.create_connection(
                    (CS2Console.VCONSOLE_HOST, CS2Console.VCONSOLE_PORT), timeout)) as sock:
                sock.settimeout(timeout)
                greeting = CS2Console._drain(sock, timeout)
                if len(greeting) < CS2Console._VCONSOLE_GREETING_MIN:
                    return ""  # someone else owns the console socket
                payload = command.encode("utf-8") + b"\x00"
                # VConsole frame: tag, protocol 0x00D4, total length.
                sock.sendall(b"CMND" + struct.pack(">HHHH", 0x00D4, 0,
                                                   12 + len(payload), 0) + payload)
                return CS2Console._drain(sock, timeout).decode("utf-8", errors="replace")
        except OSError:
            return ""

    @staticmethod
    def _drain(sock: socket.socket, timeout: float) -> bytes:
        data = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                chunk = sock.recv(65536)
            except (TimeoutError, socket.timeout):
                break
            except OSError:
                break
            if not chunk:
                break
            data += chunk
        return data


# The class was called CS2Netcon while the transport was the netconsole; the
# name is kept so existing call sites keep working.
CS2Netcon = CS2Console
