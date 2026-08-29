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


def test_serialized_document_round_trips_through_kv3(tmp_path):
    import keyvalues3 as kv3
    from gui.editors.hotkey_editor.document_model import serialize
    from gui.editors.hotkey_editor.objects import hammer_default, hammer_macros

    value = {**hammer_macros, **hammer_default}
    path = tmp_path / "round_trip.keybindings"
    path.write_text(serialize(value), encoding="utf-8", newline="\n")
    assert kv3.read(str(path)).value == value
