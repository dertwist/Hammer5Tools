"""The 'Cleanup _vrad3 cache' utility.

Deleting a lightmap cache forces a full rebuild on the next compile, so the
decision of what to delete is kept separate from the dialogs that confirm it.
"""

import logging
import shutil
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from gui.settings.common import get_cs2_path

log = logging.getLogger(__name__)

_TITLE = "Cleanup _vrad3 cache"


def find_cache_dirs(game_addons_dir: Path) -> list[Path]:
    """Every <addon>/_vrad3 directory that actually exists, in addon order."""
    return [addon / "_vrad3" for addon in sorted(game_addons_dir.iterdir())
            if addon.is_dir() and (addon / "_vrad3").is_dir()]


def remove_cache_dirs(targets) -> tuple[int, list[str]]:
    """Delete each target, returning how many went and what refused."""
    removed, failed = 0, []
    for target in targets:
        try:
            shutil.rmtree(target)
            removed += 1
        except OSError as error:
            failed.append(f"{target.parent.name}: {error}")
    return removed, failed


def cleanup_vrad3_cache(parent) -> None:
    """Ask, then delete the _vrad3 cache from every addon in the game directory."""
    cs2_path = get_cs2_path()
    if not cs2_path:
        QMessageBox.warning(parent, _TITLE, "CS2 path not found. Set it in the settings first.")
        return

    game_addons_dir = Path(cs2_path) / "game" / "csgo_addons"
    if not game_addons_dir.is_dir():
        QMessageBox.warning(parent, _TITLE, f"Addons directory not found:\n{game_addons_dir}")
        return

    targets = find_cache_dirs(game_addons_dir)
    if not targets:
        QMessageBox.information(parent, _TITLE, "No _vrad3 cache folders found.")
        return

    addon_list = "\n".join(f"  • {target.parent.name}" for target in targets)
    reply = QMessageBox.question(
        parent, _TITLE,
        f"Delete the _vrad3 cache from {len(targets)} addon(s)?\n\n{addon_list}\n\n"
        "This forces a full lightmap rebuild on the next compile.",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
    )
    if reply != QMessageBox.Yes:
        return

    removed, failed = remove_cache_dirs(targets)
    if failed:
        QMessageBox.warning(
            parent, _TITLE,
            f"Removed {removed} of {len(targets)} cache folder(s).\n\nFailed:\n" + "\n".join(failed),
        )
    else:
        QMessageBox.information(parent, _TITLE, f"Removed the _vrad3 cache from {removed} addon(s).")
