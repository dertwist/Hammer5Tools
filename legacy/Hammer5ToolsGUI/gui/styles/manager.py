"""Apply the compiled application stylesheet.

See the styling-refactor plan (gui/styles/theme.py docstring / project plan
history) for why this split exists: qss_compiler produces text, this module
is the only thing that hands that text to Qt.
"""

import os
import time

from PySide6.QtWidgets import (
    QAbstractItemDelegate, QApplication, QComboBox, QProxyStyle, QStyle,
    QStyledItemDelegate,
)

from gui.styles.qss_compiler import compile_stylesheet
from gui.styles.theme import Theme

_TIMING = os.environ.get("H5T_STYLE_TIMING") == "1"
#: Keeps the Python half of the installed proxy style alive; app.style() hands
#: back a plain QCommonStyle wrapper once Qt owns it.
_PROXY_STYLE = None


#: Ceiling for a popup widened to fit its items, so one pathological entry
#: cannot open a popup across the whole screen.
_MAX_POPUP_WIDTH = 600


def _fit_popup_to_items(combo: QComboBox) -> None:
    """Widen a combobox popup so its items are not elided.

    Without SH_ComboBox_Popup, Qt sizes the drop-down list to the *combobox*.
    That is unreadable for the narrow ones -- the 70px value-mode switch showed
    "D...t" / "V...e" / "V...d" -- and clips long enum names elsewhere
    ("LESS_...EQUAL"). The view's own minimum width is what Qt honours here.
    """
    view = combo.view()
    if view is None:
        return
    content = view.sizeHintForColumn(0)
    if content <= 0:
        return
    # Frame plus room for the scrollbar the popup grows when the list is long.
    padding = 2 * view.frameWidth() + view.style().pixelMetric(
        QStyle.PM_ScrollBarExtent, None, view
    )
    view.setMinimumWidth(min(content + padding, _MAX_POPUP_WIDTH))


class _ComboBoxStyle(QProxyStyle):
    """Fix the three things Fusion does to QComboBox popups.

    ``polish``: the built-in popup delegate paints rows itself and ignores the
    stylesheet's ``QComboBox QAbstractItemView::item`` rules, so alternating
    rows and the menu-matching item padding never show. QStyledItemDelegate
    honours them. Delegates set by our own code (always QStyledItemDelegate
    subclasses) are left alone.

    ``polish`` also lifts the default 10-item popup cap to 20: the menu-mode
    popup used to size itself to the whole list, so keeping the cap low would
    read as a regression on the addon and map lists. Qt still clamps the popup
    to the screen and adds a scrollbar when it has to.

    ``styleHint``: Fusion answers SH_ComboBox_Popup with true, which pops the
    list as a menu centred on the current item -- clipped to a couple of rows
    with scroll arrows when the combo sits near a screen edge. Off means a
    plain drop-down list under the combo, sized to its items.
    """

    def polish(self, target):
        if isinstance(target, QComboBox):
            delegate = target.itemDelegate()
            if delegate is not None and (
                type(delegate) is QAbstractItemDelegate
                or delegate.metaObject().className() == "QComboBoxDelegate"
            ):
                target.setItemDelegate(QStyledItemDelegate(target))
            if target.maxVisibleItems() == 10:  # Qt's default, i.e. unset
                target.setMaxVisibleItems(20)
            # Re-measure on every repopulation, not just here: the variable
            # pickers refill themselves from showPopup(), so a width measured
            # at polish time would be stale by the time the list is shown.
            model = target.model()
            model.rowsInserted.connect(lambda *_: _fit_popup_to_items(target))
            model.modelReset.connect(lambda *_: _fit_popup_to_items(target))
            _fit_popup_to_items(target)
        super().polish(target)

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_ComboBox_Popup:
            return 0
        return super().styleHint(hint, option, widget, returnData)


def apply(app: QApplication, theme: Theme) -> None:
    """Compile and set the application-wide stylesheet for ``theme``."""
    global _PROXY_STYLE
    if _PROXY_STYLE is None:
        # By name: QProxyStyle takes ownership of a style object, and the one
        # app.style() returns is still owned by the application.
        _PROXY_STYLE = _ComboBoxStyle(app.style().objectName() or "Fusion")
        app.setStyle(_PROXY_STYLE)
    app.setStyleSheet(compile_stylesheet(theme))


def reapply(theme: Theme) -> None:
    """Recompile the one global stylesheet for a live theme switch.

    Expensive, and not because of anything on this side: compiling the sheet
    is ~0.02 ms, while Qt's repolish of every live widget measured ~5 s for a
    ~5000-widget tree, growing faster than linearly with widget count. Content
    of the sheet barely matters -- an empty stylesheet still costs ~25% of the
    full one. Callers should therefore fire this only on a real user-initiated
    change, never speculatively. Set H5T_STYLE_TIMING=1 to print the split.
    """
    app = QApplication.instance()
    if app is None:
        return

    start = time.perf_counter()
    qss = compile_stylesheet(theme)
    compiled = time.perf_counter()
    app.setStyleSheet(qss)

    if _TIMING:
        done = time.perf_counter()
        print(
            f"[style] compile {(compiled - start) * 1000:.1f} ms, "
            f"repolish {(done - compiled) * 1000:.1f} ms, "
            f"{len(app.allWidgets())} widgets",
            flush=True,
        )
