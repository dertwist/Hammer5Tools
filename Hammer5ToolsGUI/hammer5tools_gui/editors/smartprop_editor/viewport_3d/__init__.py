"""3D viewport package for the SmartProp Editor."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hammer5tools_gui.editors.smartprop_editor.viewport_3d.viewport import SmartProp3DViewport


def __getattr__(name):
    if name != "SmartProp3DViewport":
        raise AttributeError(name)

    from hammer5tools_gui.editors.smartprop_editor.viewport_3d.viewport import SmartProp3DViewport
    return SmartProp3DViewport

__all__ = ["SmartProp3DViewport"]
