"""Shell-integration entry points.

Everything here is reached from outside the app -- a double-clicked file, an
Explorer context-menu verb arriving over IPC -- rather than from the UI, which
is why it does not belong to any one tab.
"""

import logging
import os

from PySide6.QtWidgets import QMessageBox

from gui.common import JsonToKv3, compile as run_compile
from gui.other.file_association import setup_associations
from gui.settings.common import cs2_bin_dir, get_addon_dir, get_addon_name, get_settings_bool
from gui.forms.quick_create.main import QuickCreateDialog

log = logging.getLogger(__name__)


class QuickActions:
    """File associations plus the quick vmdl/batch/compile verbs."""

    def __init__(self, window):
        self._window = window

    def setup_file_associations(self):
        """Silently claim our extensions on startup."""
        if get_settings_bool("APP", "check_associations", True):
            setup_associations()

    def confirm_addon_for(self, addon_hint) -> bool:
        """A file may belong to an addon other than the active one. Returns
        False only when the user cancels the whole operation."""
        if not addon_hint:
            return True
        current_addon = get_addon_name()
        if addon_hint.lower() == current_addon.lower():
            return True

        window = self._window
        msg_box = QMessageBox(window)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Addon Mismatch")
        msg_box.setText(
            f"This file belongs to addon '{addon_hint}', but Hammer5Tools is "
            f"currently using '{current_addon}'."
        )
        msg_box.setInformativeText("Would you like to switch to the correct addon before proceeding?")
        switch_button = msg_box.addButton("Switch Addon", QMessageBox.AcceptRole)
        keep_button = msg_box.addButton("Keep Current", QMessageBox.RejectRole)
        msg_box.addButton(QMessageBox.Cancel)
        msg_box.setDefaultButton(switch_button)
        msg_box.exec()

        if msg_box.clickedButton() == switch_button:
            window.ui.ComboBoxSelectAddon.setCurrentText(addon_hint)
            return True
        return msg_box.clickedButton() == keep_button

    def open_quick_create_dialog(self, folder_path, file_type):
        dialog = QuickCreateDialog(folder_path, file_type, self._window)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def create_vmdl(self, path):
        """Write a .vmdl next to a mesh file, or offer the dialog for a folder."""
        if not os.path.isfile(path):
            self.open_quick_create_dialog(path, "vmdl")
            return

        window = self._window
        folder = os.path.dirname(path)
        basename = os.path.splitext(os.path.basename(path))[0]
        vmdl_path = os.path.join(folder, f"{basename}.vmdl")

        try:
            addon_dir = get_addon_dir()
            rel_mesh = os.path.relpath(path, addon_dir).replace("\\", "/") if addon_dir else os.path.basename(path)
        except ValueError:
            # relpath across drives; the filename alone is the best guess left.
            rel_mesh = ""

        content = _vmdl_for_mesh(rel_mesh, basename)
        try:
            with open(vmdl_path, "w") as file:
                file.write(JsonToKv3(content, format="vmdl"))
            window.update_title(text=f"Created VMDL: {os.path.basename(vmdl_path)}")
        except OSError as error:
            QMessageBox.critical(window, "Error", f"Failed to create VMDL: {error}")

    def create_compile_batch(self, path):
        """Write a compile_assets.bat that runs resourcecompiler over a folder."""
        window = self._window
        target_dir = path if os.path.isdir(path) else os.path.dirname(path)
        if not os.path.isdir(target_dir):
            return

        bin_dir = cs2_bin_dir()
        if bin_dir is None:
            QMessageBox.warning(window, "CS2 Not Found", "CS2 installation path not set.")
            return

        rc_exe = bin_dir / "resourcecompiler.exe"
        bat_path = os.path.join(target_dir, "compile_assets.bat")
        try:
            with open(bat_path, "w") as file:
                file.write(f'@echo off\n"{rc_exe}" -i "*.vmdl" "*.vmat"\npause')
            window.update_title(text=f"Created Batch: {os.path.basename(bat_path)}")
        except OSError as error:
            QMessageBox.critical(window, "Error", f"Failed to create Batch file: {error}")

    def compile_folder(self, path):
        if os.path.isdir(path):
            self._window.update_title(text=f"Processing folder: {os.path.basename(path)}...")
            run_compile(os.path.join(path, "*.vmdl"))
            run_compile(os.path.join(path, "*.vmat"))

    def compile_file(self, path):
        if os.path.isfile(path):
            self._window.update_title(text=f"Processing file: {os.path.basename(path)}...")
            run_compile(path)


def _vmdl_for_mesh(rel_mesh: str, basename: str) -> dict:
    """The default vmdl document with its mesh and physics references filled in."""
    from gui.common import fast_deepcopy
    from gui.editors.assetgroup_maker.objects import DEFAULT_VMDL

    content = fast_deepcopy(DEFAULT_VMDL)
    for child in content.get("rootNode", {}).get("children", []):
        if child.get("_class") == "RenderMeshList":
            for mesh_file in child.get("children", []):
                if mesh_file.get("_class") == "RenderMeshFile":
                    mesh_file["filename"] = rel_mesh
        if child.get("_class") == "PhysicsShapeList":
            for phys_file in child.get("children", []):
                if phys_file.get("_class") == "PhysicsHullFile":
                    phys_file["filename"] = rel_mesh
                    phys_file["name"] = basename
    return content
