from PySide6.QtWidgets import QApplication
import pytest
from gui.updater.check import build_update_dialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


RELEASES = [{"tag_name": "v6.0.4", "body": "Fixed things.", "assets": []}]


def test_progress_bar_lives_in_the_release_notes_dialog(qapp):
    dialog = build_update_dialog(None, RELEASES, "dertwist", "Hammer5Tools", None)

    # Progress bar sits in the notes dialog, hidden until an install starts.
    assert not dialog.progress_bar.isVisibleTo(dialog)
    assert not dialog.status_label.isVisibleTo(dialog)

    dialog.begin_download()
    assert dialog.progress_bar.isVisibleTo(dialog)
    assert not dialog.button_container.isVisibleTo(dialog)
    dialog._set_progress(42)
    assert dialog.progress_bar.value() == 42

    # A close attempt mid-download must not tear the window down.
    dialog.reject()
    assert dialog.result() == 0

    dialog.end_download()
    assert not dialog.progress_bar.isVisibleTo(dialog)
    assert dialog.button_container.isVisibleTo(dialog)
    dialog.close()
