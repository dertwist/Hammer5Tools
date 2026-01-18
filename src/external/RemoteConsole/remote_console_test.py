# pip install pywinpty
from winpty import PTY
import threading
import sys
import time

EXE = r"D:\CG\Projects\Other\Hammer5Tools\src\external\RemoteConsole\CS2RemoteConsole-client.exe"

def pty_reader(pty: PTY):
    """Continuously forward child output to our stdout."""
    while True:
        try:
            data = pty.read(4096)  # bytes
        except Exception:
            return
        if not data:
            return
        sys.stdout.write(data.decode("utf-8", errors="replace"))
        sys.stdout.flush()

def pty_writer_from_keyboard(pty: PTY):
    """Optional: let user type into the child after auto command."""
    # Read raw lines and forward; good enough for basic typing.
    for line in sys.stdin:
        try:
            pty.write(line)
        except Exception:
            return

def send_command(pty: PTY, cmd: str, delay_s: float = 2.0):
    """
    Send a command into the client's TUI input line and press Enter.
    Uses CRLF because that's typically what Windows console apps expect.
    """
    time.sleep(delay_s)
    payload = cmd + "\r\n"
    pty.write(payload)

def main():
    pty = PTY(160, 40)
    pty.spawn(EXE)

    # Start reading output
    threading.Thread(target=pty_reader, args=(pty,), daemon=True).start()

    # Auto-send the command after the client boots
    threading.Thread(
        target=send_command,
        args=(pty, "say hello world", 2.5),
        daemon=True
    ).start()

    # Optional: allow manual interaction too
    threading.Thread(target=pty_writer_from_keyboard, args=(pty,), daemon=True).start()

    # Keep the main thread alive
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
