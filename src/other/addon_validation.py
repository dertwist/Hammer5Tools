from PySide6.QtWidgets import QMessageBox
from src.settings.main import get_addon_name, get_addon_dir
from src.widgets import ErrorInfo
import os

def validate_addon_structure():
    """
    Validate the structure of the addon.
    The addon should have a valid structure with only one main vmap file that matches the addon name.
    All versions should be stored in a VCS file or used as prefabs.
    """
    try:
        addon_name = get_addon_name()
        addon_dir = get_addon_dir()
    except (ValueError, TypeError) as e:
        # CS2 path not found or addon name not set - skip validation
        print(f"Skipping addon validation: {e}")
        return True

    # Check if the main vmap file exists and matches the addon name
    main_vmap_file = os.path.join(addon_dir, 'maps', f"{addon_name}.vmap")
    if not os.path.isfile(main_vmap_file):
        error_message = "Incorrect Project Structure"
        error_details = (
            "Your current project structure is incorrect.\n\n"
            "The correct structure — as used by Valve — includes only one map file in the addon.\n"
            "Hammer5Tools follows this convention. All tools work based on the main vmap file "
            "which must match the addon name.\n\n"
            "If the addon name and root vmap file don't match, you will see this error repeatedly.\n\n"
            "But what if you want to create different versions of your map?\n"
            "Use a version control system like Git, Perforce, or Diverison. It's highly recommended and not as hard as it might seem.\n\n"
            "If you don't want to use VCS tools, you can work with map versions through prefabs. The recommended structure would be:\n"
            f"  {addon_name}/maps/{addon_name}.vmap\n"
            f"  {addon_name}/maps/versions/version_01.vmap\n"
            f"  {addon_name}/maps/versions/version_02.vmap\n\n"
            f"In this setup, 'version_02.vmap' would be added to '{addon_name}.vmap' as a prefab. "
            "This structure is valid, but version control is still recommended for clean iteration."
        )

        ErrorInfo(text=error_message, details=error_details).exec_()
        return False
    else:
        print(f"Main vmap file '{main_vmap_file}' exists and matches the addon name '{addon_name}'.")
    return True
