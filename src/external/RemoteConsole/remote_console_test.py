# pip install pywinpty
from winpty import PTY
import threading
import sys
import time
import queue

EXE = r"D:\CG\Projects\Other\Hammer5Tools\src\external\RemoteConsole\CS2RemoteConsole-client.exe"

def pty_reader(pty: PTY, stop: threading.Event):
    while not stop.is_set():
        try:
            data = pty.read(4096)
        except Exception:
            break
        if not data:
            break
        sys.stdout.write(data.decode("utf-8", errors="replace"))
        sys.stdout.flush()

def pty_writer(pty: PTY, q: "queue.Queue[str]", stop: threading.Event):
    while not stop.is_set():
        try:
            msg = q.get(timeout=0.1)
        except queue.Empty:
            continue
        try:
            pty.write(msg)
        except Exception:
            break

def keyboard_feeder(q: "queue.Queue[str]", stop: threading.Event):
    # Forward lines you type into the child (press Enter).
    # This avoids touching sys.stdin from multiple places.
    while not stop.is_set():
        line = sys.stdin.readline()
        if not line:
            break
        q.put(line)

def send_cmd(q: "queue.Queue[str]", cmd: str):
    # CRLF is typically safest for Windows console apps / PTY usage. [web:9]
    q.put(cmd + "\r\n")

def main():
    stop = threading.Event()
    q: "queue.Queue[str]" = queue.Queue()

    pty = PTY(160, 40)
    pty.spawn(EXE)

    threading.Thread(target=pty_reader, args=(pty, stop), daemon=True).start()
    threading.Thread(target=pty_writer, args=(pty, q, stop), daemon=True).start()
    threading.Thread(target=keyboard_feeder, args=(q, stop), daemon=True).start()

    # Give the TUI a moment to initialize, then send your command
    time.sleep(2.5)
    send_cmd(q, "say hello world")

    # Example: send more commands later
    # time.sleep(1.0)
    # send_cmd(q, "status")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop.set()
        # Best-effort: attempt to tell the app to exit if it supports it.
        # send_cmd(q, "quit")

if __name__ == "__main__":
    main()
