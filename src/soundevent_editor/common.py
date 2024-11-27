import os
from src.preferences import get_cs2_path, get_addon_name

soundevents_source_path_default_cs2_template = os.path.join(get_cs2_path(), 'content', 'csgo_addons', 'addon_template', 'soundevents','soundevents_addon.vsndevts')
sounds_source_path_default_cs2_template = os.path.join(get_cs2_path(), 'content', 'csgo_addons', 'addon_template', 'sounds')
# Destination
addon_vsndevts = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'soundevents','soundevents_addon.vsndevts')
addon_sounds = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'sounds')