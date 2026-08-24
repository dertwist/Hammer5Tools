from pathlib import Path

from compile_ui import find_ui_files


def test_source_scope_excludes_packaged_application_tree(tmp_path):
    source = tmp_path / "Hammer5ToolsGUI" / "hammer5tools_gui"
    packaged = tmp_path / "Hammer5Tools" / "app" / "runtime" / "hammer5tools_gui"
    source.mkdir(parents=True)
    packaged.mkdir(parents=True)
    (source / "source.ui").write_text("", encoding="utf-8")
    (packaged / "packaged.ui").write_text("", encoding="utf-8")

    found = [Path(path).name for path in find_ui_files(str(source))]

    assert found == ["source.ui"]
