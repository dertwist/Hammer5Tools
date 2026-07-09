"""
Shared OpenGL surface-format helpers for the 3D viewports.

Centralises how the SmartProp and Path 3D render areas request a multisampled
(anti-aliased) framebuffer so both widgets stay in sync and honour the same
user preference.
"""
from PySide6.QtGui import QSurfaceFormat


# Allowed MSAA sample counts exposed in the settings UI.  0 == antialiasing off.
MSAA_SAMPLE_CHOICES = (0, 2, 4, 8)
DEFAULT_MSAA_SAMPLES = 4


def get_viewport_msaa_samples() -> int:
    """Return the configured MSAA sample count for the 3D viewports.

    Reads ``SmartPropEditor/viewport_msaa`` from the app settings, clamped to a
    supported value.  Falls back to :data:`DEFAULT_MSAA_SAMPLES` when unset or
    invalid so a fresh install still gets smooth edges.
    """
    try:
        from src.settings.common import get_settings_value
        raw = get_settings_value('SmartPropEditor', 'viewport_msaa', DEFAULT_MSAA_SAMPLES)
        samples = int(raw)
    except Exception:
        return DEFAULT_MSAA_SAMPLES
    if samples in MSAA_SAMPLE_CHOICES:
        return samples
    # Snap arbitrary values down to the nearest supported count.
    supported = [s for s in MSAA_SAMPLE_CHOICES if s <= samples]
    return max(supported) if supported else 0


def make_viewport_surface_format(samples: int = None) -> QSurfaceFormat:
    """Build a QSurfaceFormat for a 3D viewport widget.

    Requests an OpenGL 3.3 core context with a depth buffer and the given number
    of MSAA samples (defaults to the user's setting).  Apply it to a
    ``QOpenGLWidget`` via ``setFormat`` *before* the widget is first shown.
    """
    if samples is None:
        samples = get_viewport_msaa_samples()

    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    if samples and samples > 1:
        fmt.setSamples(int(samples))
    else:
        fmt.setSamples(0)
    return fmt
