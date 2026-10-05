from gui.editors.hotkey_editor.document_model import HotkeyDocument


def test_hotkey_document_tracks_bindings_without_widgets():
    document = HotkeyDocument.from_mapping({
        "editor_info": {"name": "Hammer 5 Tools"},
        "m_Bindings": [{"m_Context": "Camera", "m_Command": "Move", "m_Input": "W"}],
    })
    document.find("Camera", "Move").input = "Up"
    document.ensure("Camera", "Look").input = "Mouse1"

    value = document.to_mapping()
    assert value["m_Bindings"] == [
        {"m_Context": "Camera", "m_Command": "Move", "m_Input": "Up"},
        {"m_Context": "Camera", "m_Command": "Look", "m_Input": "Mouse1"},
    ]


def test_empty_hotkey_bindings_are_not_serialized():
    document = HotkeyDocument()
    document.ensure("Camera", "Move")
    assert document.to_mapping()["m_Bindings"] == []


def test_valve_context_typo_is_normalized_and_extra_fields_survive():
    document = HotkeyDocument.from_mapping({
        "m_Bindings": [{
            "m_COntext": "HammerEditorSession",
            "m_Command": "ReorientCameraToWorkplane",
            "m_Input": "Shift+Alt+W",
            "m_CustomField": 7,
        }],
    })

    assert document.to_mapping()["m_Bindings"] == [{
        "m_CustomField": 7,
        "m_Context": "HammerEditorSession",
        "m_Command": "ReorientCameraToWorkplane",
        "m_Input": "Shift+Alt+W",
    }]


SAMPLE = '''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
\tm_InputMacros =
\t[
\t\t{ m_Name = "SELECTION_ADD_KEY"\t\tm_Input = "Shift"\t},
\t\t{ m_Name = "SELECTION_ADJUST_KEY"\tm_Input = "Alt"\t\t},
\t]

\tm_Bindings =
\t[
\t\t{ m_Context = "SubrectEditorApp"\t\tm_Command = "FileOpen"\tm_Input = "Ctrl+O"\t\t\t},

\t\t{ m_Context = "SubrectEditorSession"\tm_Command = "Undo"\t\tm_Input = "Ctrl+Z"\t\t\t},
\t\t{ m_Context = "SubrectEditorSession"\tm_Command = "Redo"\t\tm_Input = "Ctrl+Shift+Z"\t},
\t]
}
'''


def test_serialize_matches_valve_layout():
    from gui.editors.hotkey_editor.document_model import serialize

    assert serialize({
        "m_InputMacros": [
            {"m_Name": "SELECTION_ADD_KEY", "m_Input": "Shift"},
            {"m_Name": "SELECTION_ADJUST_KEY", "m_Input": "Alt"},
        ],
        "m_Bindings": [
            {"m_Context": "SubrectEditorApp", "m_Command": "FileOpen", "m_Input": "Ctrl+O"},
            {"m_Context": "SubrectEditorSession", "m_Command": "Undo", "m_Input": "Ctrl+Z"},
            {"m_Context": "SubrectEditorSession", "m_Command": "Redo", "m_Input": "Ctrl+Shift+Z"},
        ],
    }) == SAMPLE


def test_every_editor_default_round_trips_through_kv3(tmp_path):
    import keyvalues3 as kv3
    from gui.editors.hotkey_editor.document_model import serialize
    from gui.editors.hotkey_editor.objects import EDITOR_DEFAULTS, EDITOR_MACROS, EDITOR_STEMS

    for stem in EDITOR_STEMS.values():
        value = {**EDITOR_MACROS.get(stem, {}), **EDITOR_DEFAULTS[stem]}
        path = tmp_path / f"{stem}.keybindings"
        path.write_text(serialize(value), encoding="utf-8", newline="\n")
        assert kv3.read(str(path)).value == value, stem


def test_every_default_binding_is_offered_by_its_catalog():
    from gui.editors.hotkey_editor.objects import EDITOR_CATALOGS, EDITOR_DEFAULTS, EDITOR_STEMS

    for stem in EDITOR_STEMS.values():
        catalog = EDITOR_CATALOGS[stem]
        for binding in EDITOR_DEFAULTS[stem]["m_Bindings"]:
            context, command = binding["m_Context"], binding["m_Command"]
            assert command in catalog.get(context, []), f"{stem}: {context}/{command}"


def test_read_installed_keybindings_returns_empty_for_missing_path():
    from gui.editors.hotkey_editor.objects import read_installed_keybindings

    catalog, defaults = read_installed_keybindings("", "hammer")
    assert catalog == {}
    assert defaults == {}
    catalog, defaults = read_installed_keybindings(r"C:\nonexistent", "hammer")
    assert catalog == {}
    assert defaults == {}


def test_read_installed_keybindings_parses_catalog_and_defaults(tmp_path):
    from gui.editors.hotkey_editor.document_model import serialize
    from gui.editors.hotkey_editor.objects import read_installed_keybindings

    keybindings_dir = tmp_path / "game" / "core" / "tools" / "keybindings"
    keybindings_dir.mkdir(parents=True)
    (keybindings_dir / "hammer_key_bindings.txt").write_text(
        serialize({
            "m_Bindings": [
                {"m_Context": "Camera", "m_Command": "Zoom", "m_Input": "MWheelUp"},
                {"m_Context": "Camera", "m_Command": "Pan", "m_Input": "MMouse"},
                {"m_Context": "HammerEditorSession", "m_Command": "JumpToSavedCamera1", "m_Input": "Shift+F1"},
            ],
        }),
        encoding="utf-8",
        newline="\n",
    )
    catalog, defaults = read_installed_keybindings(str(tmp_path), "hammer")
    assert "Zoom" in catalog["Camera"]
    assert "Pan" in catalog["Camera"]
    assert "JumpToSavedCamera1" in catalog["HammerEditorSession"]
    assert defaults[("Camera", "Zoom")] == "MWheelUp"
    assert defaults[("HammerEditorSession", "JumpToSavedCamera1")] == "Shift+F1"


def test_new_actions_get_default_inputs_from_installed_file(tmp_path):
    from gui.editors.hotkey_editor.document_model import serialize
    from gui.editors.hotkey_editor.objects import EDITOR_CATALOGS, read_installed_keybindings

    keybindings_dir = tmp_path / "game" / "core" / "tools" / "keybindings"
    keybindings_dir.mkdir(parents=True)
    (keybindings_dir / "hammer_key_bindings.txt").write_text(
        serialize({
            "m_Bindings": [
                {"m_Context": "BrandNewCtx", "m_Command": "BrandNewCmd", "m_Input": "Shift+F12"},
            ],
        }),
        encoding="utf-8",
        newline="\n",
    )
    catalog, defaults = read_installed_keybindings(str(tmp_path), "hammer")
    assert "BrandNewCmd" in catalog.get("BrandNewCtx", [])
    assert defaults[("BrandNewCtx", "BrandNewCmd")] == "Shift+F12"
    assert "BrandNewCmd" not in EDITOR_CATALOGS.get("hammer", {}).get("BrandNewCtx", [])

