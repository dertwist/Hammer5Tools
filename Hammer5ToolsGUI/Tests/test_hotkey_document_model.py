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
