"""
Anti-crash guard for the SmartProp 3D OpenGL viewports.

``QOpenGLWidget`` invokes ``initializeGL`` / ``resizeGL`` / ``paintGL`` as
callbacks from Qt's C++ paint machinery.  If a Python exception propagates out of
one of those callbacks it unwinds back into C++ with the GL context current and
the paint event half-finished — PySide6 prints the traceback but the process
state is undefined and typically aborts, taking the whole editor down with it.
The mouse / wheel / key handlers and the externally-driven scene-update methods
(called from selection signals and debounce timers) have the same failure mode.

``gl_guard`` wraps those methods so an exception can never escape into Qt:

  * the traceback is logged once per unique call site (not once per frame, which
    would flood the console at 60 fps),
  * a consecutive-failure counter is kept, and after :data:`_GL_CRASH_LIMIT`
    straight failures the render area is disabled — ``paintGL`` switches to a
    flat clear plus a short "viewport disabled" message and stops touching the
    scene, so the rest of the editor keeps working instead of crashing.

A single successful paint resets the counter, so transient hiccups (a model
still streaming in, a one-off bad matrix) recover on their own.
"""
import functools
import traceback

# Consecutive failed frames tolerated before the render area gives up.  Kept
# above 1 so a single bad frame while a model is still streaming in doesn't
# permanently kill the preview.
_GL_CRASH_LIMIT = 8

# Deduplicates the console spam: one traceback per (call-site, error) signature.
_logged_signatures = set()


def _log_once(where, exc):
    sig = (where, type(exc).__name__, str(exc))
    if sig in _logged_signatures:
        return
    _logged_signatures.add(sig)
    print(f"[SmartProp3D] Exception in {where}: {exc!r}")
    traceback.print_exc()


def _handle_failure(self, where, role):
    """Record a guarded-method failure and disable the viewport if it persists."""
    if role == "init":
        # A failed GL init leaves nothing usable to render; disable immediately.
        self._gl_disabled = True
        print("[SmartProp3D] 3D viewport disabled: OpenGL initialization failed.")
        return
    count = getattr(self, "_gl_crash_count", 0) + 1
    self._gl_crash_count = count
    if count >= _GL_CRASH_LIMIT and not getattr(self, "_gl_disabled", False):
        self._gl_disabled = True
        print(f"[SmartProp3D] 3D viewport disabled after {count} consecutive "
              f"render failures (last in {where}).")


def _draw_disabled_frame(widget):
    """Best-effort flat clear + message once the viewport is disabled.

    Must itself never raise: the GL context or the widget may already be in a
    bad state, so every step is individually guarded.
    """
    try:
        from OpenGL import GL
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glClearColor(0.11, 0.11, 0.11, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
    except Exception:
        pass
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPainter, QColor, QFont
        painter = QPainter(widget)
        painter.setPen(QColor(170, 170, 170))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(
            widget.rect(),
            Qt.AlignCenter | Qt.TextWordWrap,
            "3D preview disabled after a rendering error.\n"
            "The rest of the editor is unaffected.",
        )
        painter.end()
    except Exception:
        pass


def gl_guard(role="event"):
    """Wrap a viewport method so exceptions can't crash the host application.

    ``role`` selects the failure behaviour:

      * ``"init"``  — ``initializeGL``; any failure disables the viewport.
      * ``"paint"`` — ``paintGL``; failures accumulate toward the crash limit and
        a fallback frame is drawn instead of leaving a garbled buffer.
      * ``"event"`` — resize / mouse / wheel / key / scene-update methods; the
        exception is swallowed and counted, and once the viewport is disabled the
        method becomes a no-op.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if getattr(self, "_gl_disabled", False):
                # Already given up — keep the widget alive but inert.  paintGL
                # still needs to fill the framebuffer so Qt doesn't show garbage.
                if role == "paint":
                    _draw_disabled_frame(self)
                return None
            where = f"{type(self).__name__}.{func.__name__}"
            try:
                result = func(self, *args, **kwargs)
            except Exception as exc:
                _log_once(where, exc)
                _handle_failure(self, where, role)
                if role == "paint":
                    _draw_disabled_frame(self)
                return None
            if role == "paint":
                # A clean frame clears the transient-failure streak.
                self._gl_crash_count = 0
            return result
        return wrapper
    return decorator
