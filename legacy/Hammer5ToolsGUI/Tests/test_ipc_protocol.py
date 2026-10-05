from gui.shell.ipc_protocol import IPCCommand, IPCMessage


def test_messages_include_current_protocol_version():
    parsed = IPCMessage.parse(IPCMessage.create_show().encode("utf-8"))
    assert parsed == {"protocol_version": 1, "command": "show"}


def test_legacy_unversioned_messages_remain_accepted():
    assert IPCMessage.parse(b'{"command":"show"}') == {"command": "show"}


def test_future_protocol_messages_are_rejected():
    assert IPCMessage.parse(b'{"protocol_version":2,"command":"show"}') is None


def test_quick_action_uses_typed_command():
    parsed = IPCMessage.parse(IPCMessage.create_quick_action(
        IPCCommand.QUICK_PROCESS_FILE, "C:/maps/test.vmap").encode("utf-8"))
    assert parsed["command"] == "quick_process_file"
