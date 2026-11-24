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


def test_stages_automation_docs_beside_launcher(tmp_path):
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Skill\n", encoding="utf-8")
    guide = tmp_path / "AUTOMATION.md"
    guide.write_text("# Automation\n", encoding="utf-8")
    bundle = tmp_path / "bundle"

    stage_automation_documentation([str(skill), str(guide)], str(bundle))

    assert (bundle / "SKILL.md").read_text(encoding="utf-8") == "# Skill\n"
    assert (bundle / "AUTOMATION.md").read_text(encoding="utf-8") == "# Automation\n"
