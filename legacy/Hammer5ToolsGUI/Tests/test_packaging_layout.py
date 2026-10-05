from pathlib import Path

from makefile import stage_automation_documentation, stage_three_root_bundle


def test_stages_pyinstaller_payload_under_application_root(tmp_path):
    output = tmp_path / "pyinstaller" / "Hammer5ToolsGUI"
    runtime = output / "runtime"
    runtime.mkdir(parents=True)
    (output / "Hammer5ToolsGUI.exe").write_bytes(b"exe")
    (runtime / "dependency.dll").write_bytes(b"dll")
    bundle = tmp_path / "bundle"

    stage_three_root_bundle(str(output), str(bundle))

    assert (bundle / "app" / "Hammer5ToolsGUI.exe").read_bytes() == b"exe"
    assert (bundle / "app" / "runtime" / "dependency.dll").read_bytes() == b"dll"
    assert not output.exists()


def test_stages_mcp_setup_guide_beside_launcher(tmp_path):
    source = tmp_path / "AUTOMATION.md"
    source.write_text("# MCP setup\n", encoding="utf-8")
    bundle = tmp_path / "bundle"

    stage_automation_documentation(str(source), str(bundle))

    assert (bundle / "MCP_SETUP.md").read_text(encoding="utf-8") == "# MCP setup\n"
