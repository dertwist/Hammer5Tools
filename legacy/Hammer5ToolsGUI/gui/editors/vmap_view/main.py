"""Vmap reading experiments: load an uncompiled .vmap and draw it in the SmartProp 3D viewport.

Experimental project, disabled in dev and stable releases. A test/inspection editor,
not a map editor: nothing here writes. It reuses the SmartProp viewport wholesale
and only swaps where the scene comes from — a Core VMAP projection instead of a
SmartProp document.
"""

from __future__ import annotations

import logging
import os

import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMenu,
    QMenuBar,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from core.bridge import CoreBridge
from gui.editors.smartprop_editor.viewport_3d.gizmo import GizmoMode
from gui.editors.smartprop_editor.viewport_3d.render_area import SmartProp3DRenderArea
from gui.editors.smartprop_editor.viewport_3d.viewport import SmartProp3DViewport
from gui.editors.vmap_view.scene import (
    apply_variable_overrides,
    build_scene,
    resolve_content_path,
)

log = logging.getLogger(__name__)


class VmapRenderArea(SmartProp3DRenderArea):
    """A render area whose scene is set directly instead of evaluated from a document."""

    def __init__(self, parent=None):
        super().__init__(document=None, parent=parent)
        self.scene_instances = []
        self.gizmo.set_mode(GizmoMode.NONE)

    def set_scene(self, instances):
        self.scene_instances = list(instances)
        self._selected_id = 0
        # Drop the previous map's meshes, brush geometry included; the new map's
        # were already handed to the cache before this call.
        self.mesh_cache.prune({info["path"] for info in self.scene_instances if info.get("path")})
        self.update_viewport()

    def update_viewport(self):
        # The base class rebuilds from the SmartProp document; here the scene is
        # the authority, and every toolbar toggle that calls this must keep it.
        self._model_instances = list(self.scene_instances)
        self._model_infos = {info["id"]: info for info in self.scene_instances if info.get("id")}
        self._widget_infos = []
        self._path_infos = []
        self.gizmo.hide()
        self.update()


class VmapViewport(SmartProp3DViewport):
    """The SmartProp viewport without the transform tools a viewer cannot use."""

    def make_render_area(self, document):
        return VmapRenderArea(parent=self)

    def __init__(self, parent=None):
        super().__init__(document=None, parent=parent)
        for button in (self.btn_translate, self.btn_rotate, self.btn_scale):
            button.hide()
        self.btn_select.setChecked(True)
        self.isolate_check.hide()


class _SceneLoader(QThread):
    """Reads the map, evaluates its SmartProps, and builds draw data off the UI thread."""

    loaded = Signal(object, object, object)  # draw infos, {key: MeshData}, messages
    failed = Signal(str)

    def __init__(self, path: str, addon: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.addon = addon

    def run(self):
        try:
            document = CoreBridge.instance().read_valve_map_scene(self.path)
            messages = list(document.diagnostics)
            models = self._evaluate_smart_props(document, messages)
            if self.isInterruptionRequested():
                return
            infos, meshes = build_scene(document, models, lambda _path: None)
        except Exception as error:
            log.error("Failed to load %s", self.path, exc_info=True)
            self.failed.emit(str(error))
            return
        self.loaded.emit(infos, meshes, messages)

    def _evaluate_smart_props(self, document, messages: list[str]):
        """(placement index, model path, world matrix) for every SmartProp instance.

        Each placement carries its own parameter overrides, so its .vsmart is
        evaluated once per placement rather than once per file.
        """
        # ponytail: parameter overrides only. Hammer also stores per-placement
        # widget state (m_LocatorConfig: sizer bounds, locator points), so a
        # sizer-driven SmartProp draws at its authored default size rather than
        # the size it was given in the map. Read nodeData/configuration too if
        # that matters.
        from gui.editors.smartprop_editor.document_model import (
            collect_nested_smartprops, parse_smartprop,
        )
        from gui.settings.common import addon_content_dir

        placements = []
        for index, placement in enumerate(document.smart_props):
            if self.isInterruptionRequested():
                break
            source = resolve_content_path(placement.resource, addon_content_dir, self.addon)
            if source is None:
                messages.append(f"SmartProp not found: {placement.resource}")
                continue
            try:
                with open(source, "r", encoding="utf-8") as smart_prop_file:
                    smart_prop = apply_variable_overrides(
                        parse_smartprop(smart_prop_file.read()), placement.variables)
                result = CoreBridge.instance().evaluate_smartprop(
                    smart_prop, nested_documents=collect_nested_smartprops(smart_prop))
            except Exception as error:
                messages.append(f"{placement.resource}: {error}")
                continue
            messages.extend(result.diagnostics)
            transform = np.asarray(placement.transform, dtype=np.float32).reshape((4, 4))
            for model in result.models:
                placements.append((
                    index, model.model_name,
                    np.asarray(model.transform, dtype=np.float32).reshape((4, 4)) @ transform,
                ))
        return placements


class VmapViewMainWindow(QWidget):
    """Loads a .vmap and previews its meshes, props, and SmartProps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.opened_file: str | None = None
        self._loader: _SceneLoader | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.menu_bar = QMenuBar(self)
        self.menu_bar.setNativeMenuBar(False)
        file_menu = QMenu("File", self.menu_bar)
        self.menu_bar.addMenu(file_menu)
        file_menu.addAction(QAction("Open VMAP…", self, triggered=self.open_file_dialog))
        file_menu.addAction(QAction("Reload", self, triggered=self.reload))
        file_menu.addSeparator()
        file_menu.addAction(QAction("Close Map", self, triggered=self.close_map))
        view_menu = QMenu("View", self.menu_bar)
        self.menu_bar.addMenu(view_menu)
        view_menu.addAction(QAction("Frame All", self, triggered=lambda: self.viewport.fit_view()))
        layout.setMenuBar(self.menu_bar)

        self.viewport = VmapViewport(self)
        self.viewport.elementClicked.connect(self._on_element_clicked)
        layout.addWidget(self.viewport)

        self.status_label = QLabel("No map loaded.")
        self.status_label.setProperty("h5Component", "vmapViewStatus")
        layout.addWidget(self.status_label)

    def open_file_dialog(self):
        from gui.settings.common import addon_content_dir, get_addon_name

        addon = get_addon_name()
        start_directory = str(addon_content_dir(addon) / "maps") if addon else ""
        if not os.path.isdir(start_directory):
            start_directory = ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open VMAP", start_directory, "Valve Map (*.vmap)")
        if path:
            self.open_file(path)

    def open_file(self, path: str):
        """Load ``path`` in the background and show it once it is ready."""
        if self._loader is not None and self._loader.isRunning():
            self._loader.requestInterruption()
            self._loader.wait()

        from gui.settings.common import get_addon_name

        self.opened_file = os.path.normpath(path)
        self.status_label.setText(f"Loading {os.path.basename(self.opened_file)}…")
        self._loader = _SceneLoader(self.opened_file, get_addon_name() or "", self)
        self._loader.loaded.connect(self._on_loaded)
        self._loader.failed.connect(self._on_failed)
        self._loader.start()

    def reload(self):
        if self.opened_file:
            self.open_file(self.opened_file)

    def close_map(self):
        self.opened_file = None
        self.viewport.render_area.set_scene([])
        self.status_label.setText("No map loaded.")

    def _on_loaded(self, infos, meshes, messages):
        render_area = self.viewport.render_area
        for key, mesh in meshes.items():
            render_area.mesh_cache.put_mesh(key, mesh)
        render_area.set_scene(infos)
        # Upload now rather than on the next paint: fit_view frames loaded meshes by
        # their real bounds and everything else by a placeholder box at its origin, and
        # brush geometry is baked into world space — so its box would sit at the origin
        # and a brush-only map would open framed on nothing.
        try:
            render_area.makeCurrent()
            render_area.mesh_cache.upload_pending()
        except Exception:
            log.warning("Could not pre-upload map geometry", exc_info=True)
        finally:
            render_area.doneCurrent()
        render_area.fit_view()

        brushes = len(meshes)
        summary = (f"{os.path.basename(self.opened_file or '')}: "
                   f"{brushes} meshes, {len(infos) - brushes} placements")
        if messages:
            summary += f" — {len(messages)} message(s): {messages[0]}"
            log.info("VMAP load messages for %s: %s", self.opened_file, "; ".join(messages))
        self.status_label.setText(summary)

    def _on_failed(self, message: str):
        self.status_label.setText(f"Failed to load: {message}")
        QMessageBox.critical(self, "Vmap View", f"Could not load the map:\n{message}")

    def _on_element_clicked(self, element_id: int):
        info = next((item for item in self.viewport.render_area.scene_instances
                     if item.get("id") == element_id), None)
        if info:
            self.status_label.setText(info.get("label") or info.get("path", ""))

    def closeEvent(self, event):
        if self._loader is not None and self._loader.isRunning():
            self._loader.requestInterruption()
            self._loader.wait()
        super().closeEvent(event)
