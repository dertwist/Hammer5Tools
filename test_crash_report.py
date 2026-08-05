"""Self-check for the desktop crash report in src/main.py. Run: python test_crash_report.py"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.main import write_crash_report, _desktop_dir


def test():
    assert os.path.isdir(_desktop_dir()), f"desktop not found: {_desktop_dir()}"
    try:
        raise ValueError("synthetic crash for the self-check")
    except ValueError:
        path = write_crash_report(*sys.exc_info())
    assert path, "no crash report written"
    text = open(path, encoding='utf-8').read()
    os.remove(path)
    for expected in ("crash report", "ValueError", "synthetic crash for the self-check", "All threads"):
        assert expected in text, f"missing {expected!r} in report"
    print(f"OK - report written to {path} and removed")


if __name__ == "__main__":
    test()
