"""Check for undefined names using pyflakes.

Fails fast on NameError candidates in the GUI directory while ignoring
unused-import warnings (which pyflakes also emits by default).
"""
import subprocess
import sys


def main() -> int:
    result = subprocess.run(
        [sys.executable, '-m', 'pyflakes', 'Hammer5ToolsGUI/gui'],
        capture_output=True,
        text=True,
    )
    undefined = [
        line for line in result.stdout.splitlines()
        if "undefined name '" in line
    ]
    if undefined:
        print(f"Found {len(undefined)} undefined name(s):", file=sys.stderr)
        for line in undefined:
            print(f"  {line}", file=sys.stderr)
        return 1

    print("OK: No undefined names found in Hammer5ToolsGUI/gui.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
