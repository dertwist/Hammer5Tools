"""Opt-in smoke checks against a published NativeAOT DLL and public CS2 assets."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.skipif(not os.environ.get("H5T_SMARTPROP_NATIVE") or not os.environ.get("H5T_AUTOMATION_CS2"),
                    reason="Set H5T_SMARTPROP_NATIVE and H5T_AUTOMATION_CS2 for the native stdio smoke")
def test_native_geometry_and_repeated_failures_leave_stdio_json_only():
    root = Path(__file__).resolve().parents[1]
    requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize"}]
    requests.append({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
        "name": "hammer5tools.model_bounds", "arguments": {
            "path": "models/editor/placeholder_box.vmdl", "game_dir": os.environ["H5T_AUTOMATION_CS2"], "addon": "h5t_native_smoke"}}})
    for identity in range(3, 6):
        requests.append({"jsonrpc": "2.0", "id": identity, "method": "tools/call", "params": {
            "name": "hammer5tools.compile_job_status", "arguments": {"job_id": "invalid"}}})
    requests.append({"jsonrpc": "2.0", "id": 6, "method": "ping"})
    probe = subprocess.run([sys.executable, str(root / "gui/main.py"), "mcp", "serve"],
                           input="".join(json.dumps(request) + "\n" for request in requests),
                           capture_output=True, encoding="utf-8", timeout=30, check=True)
    replies = [json.loads(line) for line in probe.stdout.splitlines() if line.strip()]
    assert [reply["id"] for reply in replies] == list(range(1, 7))
    bounds = replies[1]["result"]["structuredContent"]
    assert bounds["supported"] and bounds["dimensions"] == [10, 10, 10]
    assert all(reply["result"]["isError"] for reply in replies[2:5])
    assert replies[-1]["result"] == {}
