"""Test bootstrap for the separated GUI and Core Python roots."""

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOTS = (
    REPOSITORY_ROOT / "Hammer5ToolsGUI",
    REPOSITORY_ROOT / "Hammer5ToolsCore" / "Python",
)

for source_root in SOURCE_ROOTS:
    source = str(source_root)
    if source not in sys.path:
        sys.path.insert(0, source)
