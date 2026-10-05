"""The addon combo box and the Launch button beside it."""

import logging
import os
import random

from PySide6.QtCore import QPoint, QPropertyAnimation, Qt
from PySide6.QtWidgets import QMessageBox, QWidget

from gui.common import default_commands
from gui.other.addon_functions import launch_addon
from gui.settings.common import (
    get_addon_name,
    cs2_addons_dir,
    get_cs2_path,
    get_settings_value,
    set_addon_name,
)

log = logging.getLogger(__name__)

#: Text the combo box shows when there is nothing real to select.
PLACEHOLDERS = frozenset({"CS2 Path Not Set", "Addons Folder Not Found"})

_EXCLUDED_ADDONS = frozenset({"workshop_items", "addon_template"})

_SWEEP_MS = 1200


def list_addons(cs2_path) -> list[str]:
    """Addon folder names under content/csgo_addons, template folders excluded."""
    addons_folder = cs2_addons_dir(cs2_path=cs2_path)
    if addons_folder is None:
        return []
    if not os.path.exists(addons_folder):
        return []
    return [name for name in os.listdir(addons_folder)
            if name not in _EXCLUDED_ADDONS
            and os.path.isdir(os.path.join(addons_folder, name))]


class AddonSelector:
    """Owns what is in the combo box; the window still owns what a change means."""

    def __init__(self, window):
        self._window = window
        self._create_offered = False

    @property
    def _combo(self):
        return self._window.ui.ComboBoxSelectAddon

    def populate(self):
        cs2_path = get_cs2_path()
        if cs2_path is None:
            self._show_placeholder("CS2 Path Not Set")
            return

        try:
            addons_folder = cs2_addons_dir()
            if addons_folder is None:
                self._show_placeholder("CS2 Path Not Set")
                return
            if not os.path.exists(addons_folder):
                self._show_placeholder("Addons Folder Not Found")
                return

            found_names = self.resolve_saved_addon(list_addons(cs2_path))
            if not found_names:
                self._show_placeholder("")
                return
            for name in found_names:
                self._combo.addItem(name)
        except OSError as error:
            log.error(f"Failed to load addons: {error}")

    def resolve_saved_addon(self, found_names: list[str] | None = None) -> list[str]:
        """Point the addon setting at an addon that exists, and return the addon list.

        Runs before any editor is built. It tests the *stored* value rather than
        get_addon_name(), so "nothing saved yet" stays distinguishable from a real
        selection. With no addons on disk at all it offers to build one from a preset,
        because the alternative -- carrying a placeholder name around -- is what used
        to conjure a csgo_addons/addon folder into existence.
        """
        if found_names is None:
            found_names = list_addons(get_cs2_path())
        if not found_names:
            found_names = self._offer_to_create_addon()
        if found_names and get_settings_value('LAUNCH', 'addon', default='') not in found_names:
            set_addon_name(random.choice(found_names))
        return found_names

    def _offer_to_create_addon(self) -> list[str]:
        """Offer to build a first addon from a preset, returning the addon list after.

        Asked at most once per session: declining leaves no addon selected, which every
        addon path helper reports as None, so the editors simply stay unbuilt.
        """
        if self._create_offered:
            return []
        self._create_offered = True
        response = QMessageBox.question(
            self._window, "No Addon Found",
            "No addons found. Would you like to create one now?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if response != QMessageBox.Yes:
            return []
        from gui.forms.create_addon.main import CreateAddonDialog
        CreateAddonDialog(self._window).exec()
        return list_addons(get_cs2_path())

    def refresh(self):
        """Rebuild the list without the repopulation looking like a user choice."""
        window = self._window
        try:
            self._combo.currentTextChanged.disconnect(window.selected_addon_name)
        except (RuntimeError, TypeError):
            pass

        self._combo.clear()
        self.populate()
        # Read after populate: it may have corrected a stale/default addon name
        # to a real one, and the combo should reflect that correction.
        self._combo.setCurrentText(get_addon_name())
        self._combo.currentTextChanged.connect(window.selected_addon_name)

        if not window._addon_initialised:
            window.selected_addon_name()

    def _show_placeholder(self, text):
        self._combo.addItem(text)
        self._combo.setCurrentIndex(0)

    def launch(self):
        self.animate_launch_button()
        self._window.update_title(text=f"Launched addon: {get_addon_name()}")
        launch_addon()

    def animate_launch_button(self):
        """Sweep a highlight across the button, left to right, then drop it."""
        button = self._window.ui.Launch_Addon_Button
        width, height = button.width(), button.height()

        overlay = QWidget(button)
        overlay.setObjectName("launchOverlay")
        overlay.setAttribute(Qt.WA_StyledBackground, True)
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        overlay.setGeometry(-width, 0, width, height)
        overlay.show()
        overlay.lower()

        animation = QPropertyAnimation(overlay, b"pos", self._window)
        animation.setDuration(_SWEEP_MS)
        animation.setStartValue(QPoint(-width, 0))
        animation.setEndValue(QPoint(width, 0))
        animation.finished.connect(overlay.deleteLater)
        animation.start()

    def update_launch_button_text(self):
        commands = get_settings_value("LAUNCH", "commands", default_commands)
        label = "Edit map" if commands and "-asset" in commands else "Launch Tools"
        self._window.ui.Launch_Addon_Button.setText(label)
