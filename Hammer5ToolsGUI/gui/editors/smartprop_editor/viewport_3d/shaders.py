"""
Loads the GLSL shader source files in ``glsl/`` for the 3D viewport.
All shaders target OpenGL 4.3 core profile.
"""
from pathlib import Path

_GLSL_DIR = Path(__file__).parent / 'glsl'


def _load(name: str) -> str:
    return (_GLSL_DIR / name).read_text(encoding='utf-8')


MODEL_VERTEX_SHADER = _load('model.vert')
MODEL_FRAGMENT_SHADER = _load('model.frag')
PICKING_VERTEX_SHADER = _load('picking.vert')
PICKING_FRAGMENT_SHADER = _load('picking.frag')
GRID_VERTEX_SHADER = _load('grid.vert')
GRID_FRAGMENT_SHADER = _load('grid.frag')
GIZMO_VERTEX_SHADER = _load('gizmo.vert')
GIZMO_FRAGMENT_SHADER = _load('gizmo.frag')
WIREFRAME_VERTEX_SHADER = _load('wireframe.vert')
WIREFRAME_FRAGMENT_SHADER = _load('wireframe.frag')
OUTLINE_VERTEX_SHADER = _load('outline.vert')
OUTLINE_FRAGMENT_SHADER = _load('outline.frag')
LOCATOR_VERTEX_SHADER = _load('locator.vert')
LOCATOR_FRAGMENT_SHADER = _load('locator.frag')
GROUP_BILLBOARD_VERTEX_SHADER = _load('group_billboard.vert')
GROUP_BILLBOARD_FRAGMENT_SHADER = _load('group_billboard.frag')
