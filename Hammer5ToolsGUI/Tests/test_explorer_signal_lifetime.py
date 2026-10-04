"""Model updates must not access explorer widgets after teardown."""

import sys

import pytest
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from gui.widgets.explorer.main import Explorer


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("signal_name", ["directoryLoaded", "rowsInserted"])
@pytest.mark.parametrize("state", ["filtered", "blank", "frame_deleted", "explorer_deleted"])
def test_model_update_lifetime(qapp, tmp_path, monkeypatch, signal_name, state):
    explorer = Explorer(tree_directory=str(tmp_path), addon="", editor_name="test")
    model = explorer.model
    proxy = explorer.filter_proxy_model
    errors = []
    monkeypatch.setattr(sys, "excepthook", lambda *error: errors.append(error))
    try:
        explorer.filter_editline.setText("match" if state != "blank" else "   ")
        explorer._filter_timer.stop()
        explorer._expand_timer.stop()
        if state == "frame_deleted":
            # Editors embed the frame, reparenting it independently of Explorer.
            explorer.frame.setParent(None)
            delete(explorer.frame)
        elif state == "explorer_deleted":
            # Retain the senders to reproduce late model notifications.
            model.setParent(None)
            proxy.setParent(None)
            delete(explorer)

        if signal_name == "directoryLoaded":
            model.directoryLoaded.emit(str(tmp_path))
        else:
            proxy.rowsInserted.emit(QModelIndex(), 0, 0)

        assert not errors
        if state != "explorer_deleted":
            assert explorer._expand_timer.isActive() == (state == "filtered")
        if state == "frame_deleted":
            explorer._expand_all_filtered()
    finally:
        if state == "explorer_deleted":
            delete(proxy)
            delete(model)
        else:
            delete(explorer)
