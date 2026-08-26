"""Test bootstrap for the Hammer5ToolsGUI Python source root."""

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "Hammer5ToolsGUI"

source = str(SOURCE_ROOT)
if source not in sys.path:
    sys.path.insert(0, source)
