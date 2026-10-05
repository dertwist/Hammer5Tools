"""Material batching in the 3D viewport draw loop.

Binding a material is ~50 GL calls, and a loaded map is mostly repeats of a few
models, so the draw loop must not re-upload material state it already holds.
These drive the real ``_draw_material_submesh`` against a stub GL module and count
what it would have sent.
"""

import sys
import types

import numpy as np
import pytest

from gui.editors.smartprop_editor.viewport_3d.mesh_cache import GPUMaterial, GPUSubMesh


class _FakeGL:
    """Records every call the draw path makes, and answers the few queries it asks."""

    GL_FALSE = 0
    GL_TRIANGLES = 4
    GL_UNSIGNED_INT = 5
    GL_TEXTURE0 = 33984
    GL_TEXTURE_2D = 3553

    def __init__(self):
        self.calls = []
        self.ctypes = types.SimpleNamespace(c_void_p=lambda value: value)

    def __getattr__(self, name):
        if name.startswith("GL_"):
            return 0

        def record(*args):
            self.calls.append(name)
            if name == "glGetUniformLocation":
                return 1
            if name == "glIsTexture":
                return True
            return 0

        return record

    def count(self, name):
        return self.calls.count(name)


class _StubRenderArea:
    """Just the parts of SmartProp3DRenderArea the draw call touches."""

    from gui.editors.smartprop_editor.viewport_3d.render_area import (
        SmartProp3DRenderArea as _real)

    _ALPHA_MODE_CODE = _real._ALPHA_MODE_CODE
    _draw_material_submesh = _real._draw_material_submesh
    _bind_material = _real._bind_material
    _is_live_texture = _real._is_live_texture

    def __init__(self):
        self._model_program = 1
        self._bound_material_state = None
        self._bound_vao = None
        self._live_textures = {}
        self.frame_stats = {"drawn": 0, "culled": 0, "materials": 0, "vaos": 0, "ms": 0.0}


@pytest.fixture
def gl(monkeypatch):
    fake = _FakeGL()
    module = types.ModuleType("OpenGL")
    module.GL = fake
    monkeypatch.setitem(sys.modules, "OpenGL", module)
    monkeypatch.setitem(sys.modules, "OpenGL.GL", fake)
    return fake


def _mesh(material, vao=1):
    return types.SimpleNamespace(vao=vao, submeshes=[GPUSubMesh(0, 3, material)])


def _draw(area, gl, material, tint=None, vao=1):
    area._draw_material_submesh(
        _mesh(material, vao), GPUSubMesh(0, 3, material),
        np.eye(4, dtype=np.float32), np.eye(3, dtype=np.float32),
        False, True, material=material, tint=tint)


def test_repeating_one_model_binds_its_vao_once(gl):
    area = _StubRenderArea()
    material = GPUMaterial(name="a.vmat", base_tex=1)

    for _ in range(10):
        _draw(area, gl, material, vao=7)

    # VRF's batch renderer tracks the bound VAO and rebinds only on change; a run of
    # instances of one model is exactly the case that pays for.
    assert gl.count("glBindVertexArray") == 1
    assert gl.count("glDrawElements") == 10


def test_switching_models_rebinds_the_vao(gl):
    area = _StubRenderArea()
    material = GPUMaterial(name="a.vmat", base_tex=1)

    for vao in (1, 1, 2, 2, 1):
        _draw(area, gl, material, vao=vao)

    assert gl.count("glBindVertexArray") == 3


def test_frame_stats_count_what_the_batching_saved(gl):
    area = _StubRenderArea()
    one = GPUMaterial(name="a.vmat", base_tex=1)
    two = GPUMaterial(name="b.vmat", base_tex=2)

    for _ in range(5):
        _draw(area, gl, one, vao=1)
    for _ in range(5):
        _draw(area, gl, two, vao=2)

    # Ten draws that only ever needed two material binds and two VAO binds.
    assert gl.count("glBindVertexArray") == 2
    assert gl.count("glDrawElements") == 10


def test_repeating_one_material_binds_it_once(gl):
    area = _StubRenderArea()
    material = GPUMaterial(name="materials/dev/grid.vmat", base_tex=7)

    _draw(area, gl, material)
    after_first = len(gl.calls)
    for _ in range(9):
        _draw(area, gl, material)

    per_repeat = (len(gl.calls) - after_first) / 9
    # A repeat costs only the model/normal matrices, the VAO bind pair and the draw.
    assert per_repeat <= 7, f"{per_repeat} calls per repeated instance"
    # The expensive part happened exactly once.
    assert gl.count("glBindTexture") == 5
    assert gl.count("glDrawElements") == 10


def test_alternating_materials_rebinds_each_time(gl):
    area = _StubRenderArea()
    one = GPUMaterial(name="a.vmat", base_tex=1)
    two = GPUMaterial(name="b.vmat", base_tex=2)

    for _ in range(5):
        _draw(area, gl, one)
        _draw(area, gl, two)

    # Ten draws, ten distinct materials in sequence, ten binds: no state is skipped
    # when it actually changed.
    assert gl.count("glBindTexture") == 5 * 2 * 5


def test_a_changed_tint_rebinds_the_same_material(gl):
    area = _StubRenderArea()
    material = GPUMaterial(name="a.vmat", base_tex=1)

    _draw(area, gl, material, tint=(1.0, 1.0, 1.0, 1.0))
    binds_after_first = gl.count("glBindTexture")
    _draw(area, gl, material, tint=(1.0, 0.0, 0.0, 1.0))

    # Tint multiplies the albedo inside the material uniforms, so it is part of the
    # bound state, not something the shader picks up per draw.
    assert gl.count("glBindTexture") > binds_after_first


def test_clearing_the_bound_state_forces_a_rebind(gl):
    area = _StubRenderArea()
    material = GPUMaterial(name="a.vmat", base_tex=1)

    _draw(area, gl, material)
    binds = gl.count("glBindTexture")
    # What the marker/billboard pass does after leaving its icon on unit 0.
    area._bound_material_state = None
    _draw(area, gl, material)

    assert gl.count("glBindTexture") == binds * 2


def test_texture_validity_is_queried_once_per_frame(gl):
    area = _StubRenderArea()
    one = GPUMaterial(name="a.vmat", base_tex=1)
    two = GPUMaterial(name="b.vmat", base_tex=2)

    for _ in range(20):
        _draw(area, gl, one)
        _draw(area, gl, two)

    # glIsTexture is a driver round trip; two distinct texture ids, asked once each
    # until paintGL clears the memo for the next frame.
    assert gl.count("glIsTexture") == 2
