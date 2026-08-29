"""Regenerate the Hotkey Editor catalogs from CS2's shipped key-binding files.

Usage:
    python dev/generate_hotkey_catalogs.py "<cs2>/game/core/tools/keybindings"

Prints the EDITOR_CATALOGS / EDITOR_DEFAULTS / EDITOR_MACROS literals to paste
into Hammer5ToolsGUI/gui/editors/hotkey_editor/objects.py. Hammer is skipped on
purpose: its file in a real install has usually been overwritten by Hammer 5
Tools, so its catalog stays hand-maintained as `hammer_commands`.
"""

import os
import pprint
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Hammer5ToolsGUI"))
import keyvalues3 as kv3

SUFFIX = "_key_bindings.txt"
SKIP = {"hammer"}


def collect(folder):
    catalogs, defaults, macros = {}, {}, {}
    for name in sorted(os.listdir(folder)):
        if not name.endswith(SUFFIX):
            continue
        stem = name[: -len(SUFFIX)]
        if stem in SKIP:
            continue
        value = kv3.read(os.path.join(folder, name)).value
        bindings = [item for item in value.get("m_Bindings", []) if isinstance(item, dict)]
        commands = {}
        for item in bindings:
            commands.setdefault(item.get("m_Context", ""), []).append(item.get("m_Command", ""))
        catalogs[stem] = {context: sorted(set(names)) for context, names in commands.items()}
        defaults[stem] = {"m_Bindings": bindings}
        if value.get("m_InputMacros"):
            macros[stem] = {"m_InputMacros": value["m_InputMacros"]}
    return catalogs, defaults, macros


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    catalogs, defaults, macros = collect(sys.argv[1])
    for name, value in (("EDITOR_CATALOGS", catalogs), ("EDITOR_DEFAULTS", defaults),
                        ("EDITOR_MACROS", macros)):
        print(f"{name} = {pprint.pformat(value, width=110, sort_dicts=False)}\n")


if __name__ == "__main__":
    main()
