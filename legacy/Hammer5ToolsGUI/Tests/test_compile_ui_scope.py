from pathlib import Path

from compile_ui import find_ui_files, strip_designer_stylesheets


def test_source_scope_excludes_packaged_application_tree(tmp_path):
    source = tmp_path / "Hammer5ToolsGUI" / "gui"
    packaged = tmp_path / "Hammer5Tools" / "app" / "runtime" / "gui"
    source.mkdir(parents=True)
    packaged.mkdir(parents=True)
    (source / "source.ui").write_text("", encoding="utf-8")
    (packaged / "packaged.ui").write_text("", encoding="utf-8")

    found = [Path(path).name for path in find_ui_files(str(source))]

    assert found == ["source.ui"]


def test_generated_stylesheets_are_removed():
    generated = """from PySide6.QtCore import Qt

class Ui_Form(object):
    def setupUi(self, Form):
        self.frame.setStyleSheet(\"background: #272727;\")
        Form.setStyleSheet(\"color: #e5e5e5;\")
"""

    stripped = strip_designer_stylesheets(generated)

    assert "background: #272727" not in stripped
    assert "color: #e5e5e5" not in stripped
    assert ".setStyleSheet(" not in stripped


def test_temporary_manager_calls_are_removed():
    generated = """from gui.styles.manager import apply_widget_stylesheet

class Ui_Form(object):
    def setupUi(self, Form):
        apply_widget_stylesheet(self.frame, (
            "background: #272727;"
            "color: #e5e5e5;"
        ))
"""

    stripped = strip_designer_stylesheets(generated)

    assert "apply_widget_stylesheet" not in stripped
    assert "background: #272727" not in stripped
