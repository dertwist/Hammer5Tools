from PySide6.QtWidgets import QWidget

#: Dynamic property paired with the ``QWidget[paintThrough="true"]`` rule in
#: gui/styles/qss/base.qss.
PAINT_THROUGH_PROPERTY = "paintThrough"


def mark_paint_through(widget: QWidget) -> None:
    """Make ``widget`` transparent so whatever is painted behind it shows.

    The global stylesheet gives every widget an opaque background via an
    unqualified ``QWidget { background-color: ... }``. A widget that draws in
    its own paintEvent is fine — Qt draws the styled background first and the
    paintEvent over it — but every opaque *child* then covers that drawing up.

    So this goes on the children that should not obscure their parent, not on
    the parent doing the painting. Marking the painter itself does nothing.

    Call before the widget is first shown: Qt resolves stylesheet rules at
    polish time, so a property set afterwards needs an unpolish/polish cycle.
    """
    widget.setProperty(PAINT_THROUGH_PROPERTY, True)


def set_style_property(widget: QWidget, name: str, value) -> None:
    """Set a dynamic QSS property and refresh an already-polished widget."""
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    QWidget.update(widget)
