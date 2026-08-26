from PySide6.QtWidgets import QWidget
qt_stylesheet_checkbox = """
    QCheckBox {

        font: 580 10pt "Segoe UI";

        border: 2px solid black;
        border-radius: 2px;
        border-color: rgba(94, 94, 94, 255);
        height:22px;
        padding-top: 2px;
        padding-bottom:2px;
        padding-left: 4px;
        padding-right: 4px;
        color: #e5e5e5;
        background-color: #2e2e2e;
    }
    QCheckBox:hover {
        background-color: #515965;
        color: white;
    }
    QCheckBox:pressed {

    }"""
qt_stylesheet_button = """
    /* QPushButton default and hover styles */
    QPushButton {

        font: 580 9pt "Segoe UI";
	

        border: 2px solid black;
        border-radius: 2px;
        border-color: rgba(94, 94, 94, 255);
        height:22px;
        padding-top: 2px;
        padding-bottom:2px;
        padding-left: 4px;
        padding-right: 4px;
        color: #e5e5e5;
        background-color: #2e2e2e;
    }
    QPushButton:hover {
        background-color: #515965;
        color: white;
    }
    QPushButton:pressed {
        background-color: red;
        background-color: #2e2e2e;
        margin: 1 px;
        margin-left: 2px;
        margin-right: 2px;
    }
    QPushButton:disabled {
        background-color: #292929;
        color: #7c7c85;
        border-color: #3f3f42;
    }"""
qt_stylesheet_toolbutton = """
    /* QPushButton default and hover styles */
    QToolButton {

        font: 580 9pt "Segoe UI";


        border: 2px solid black;
        border-radius: 2px;
        border-color: rgba(94, 94, 94, 255);
        height:22px;
        padding-top: 2px;
        padding-bottom:2px;
        padding-left: 4px;
        padding-right: 4px;
        color: #e5e5e5;
        background-color: #2e2e2e;
    }
    QToolButton:hover {
        background-color: #515965;
        color: white;
    }
    QToolButton:pressed {
        background-color: red;
        background-color: #2e2e2e;
        margin: 1 px;
        margin-left: 2px;
        margin-right: 2px;

    }"""
# padding:2px; font: 580 9pt "Segoe UI"; padding-left:4px
qt_stylesheet_combobox = """
    /* QPushButton default and hover styles */
    QComboBox {

        font: 580 9pt "Segoe UI";
        border: 2px solid black;
        border-radius: 2px;
        border-color: rgba(94, 94, 94, 255);
        height:22px;
        padding-top: 2px;
        padding-bottom:2px;
        padding-left: 4px;
        padding-right: 4px;
        color: #e5e5e5;
        background-color: #2e2e2e;
    }
    QComboBox:hover {
        background-color: #515965;
        color: white;
    }
    QComboBox:pressed {

    }
    QComboBox:item {
    font: 600 12pt "Segoe UI";
    color: #e5e5e5;
    padding-left: 5px;
    background-color: #2e2e2e;
    border-style: none;
    }
    
    QComboBox::drop-down {
        color: #e5e5e5;
        padding: 2px;
        background: url(://icons/arrow_drop_down_16dp.svg) no-repeat center;
        border-bottom: 0px solid black;
        border-top: 0px solid black;
        border-right: 0px;
        border-left: 2px solid;
        margin-left: 5px;
        padding: 5px;
        width: 7px;
        border-color: rgba(94, 94, 94, 255);
        background-color: #2e2e2e;
    }
    
    
    QComboBox QAbstractItemView {
        border: 2px solid gray;
        border-color: rgba(94, 94, 94, 255);
        selection-background-color: #515965;
        background-color: #2e2e2e;
    }
    
    
    QComboBox QAbstractItemView::item {
        height: 16px; /* Set the height of each item */
        padding: 4px; /* Add padding to each item */
        padding-left: 5px;
        padding-right: 5px;
        color: #ff939393;
        border-style: none;
        border-bottom: 0.5px solid black;
        border-color: rgba(255, 255, 255, 10);
    }
    
    
    QComboBox QAbstractItemView::item:selected {
        height: 16px; /* Set the height of each item */
        padding: 4px; /* Add padding to each item */
        padding-left: 5px;
        padding-right: 5px;
        background-color: #515965;
        color: white;
        border: none; /* Remove border */
        outline: none; /* Remove outline */
    }
"""

qt_stylesheet_plain_text_batch_inline = """QPlainTextEdit {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
    height:18px;
    padding: 0px;  /* Remove padding */
    padding-left: 0px;  /* Remove left padding */
    padding-right: 0px;  /* Remove right padding */
    color: #e5e5e5;
    background-color: #2e2e2e;
}



QPlainTextEdit{

    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
    height:18px;
    padding: 0px;  /* Remove padding */
    padding-left: 0px;  /* Remove left padding */
    padding-right: 0px;  /* Remove right padding */
    color: #e5e5e5;
    background-color: #2e2e2e;
}

/* QPlainTextEdit:hover {
    background-color: #515965;
    color: white;
} */

QPlainTextEdit:pressed {
    background-color: red;
    background-color: #2e2e2e;
    margin: 0px;  /* Remove margin */
    margin-left: 0px;  /* Remove left margin */
    margin-right: 0px;  /* Remove right margin */
}"""

qt_stylesheet_button_icon = """
    /* QPushButton default and hover styles for icon buttons */
    QPushButton, QToolButton {
        font: 580 9pt "Segoe UI";
        border: 1px solid #464649;
        border-radius: 2px;
        padding: 0px;
        margin: 0px;
        color: #e5e5e5;
        background-color: #2e2e2e;
    }
    QPushButton:hover, QToolButton:hover {
        background-color: #515965;
        border-color: #515965;
        color: white;
    }
    QPushButton:pressed, QToolButton:pressed {
        background-color: #6d7882;
    }
    QPushButton:disabled, QToolButton:disabled {
        background-color: #292929;
        color: #7c7c85;
        border-color: #3f3f42;
    }"""

qt_stylesheet_widgetlist = """
QListWidget, QListView {
    border: 2px solid #d0d0d0;
    border-color: rgba(94, 94, 94, 255);
    border-radius: 2px;
    padding: 2px;
    color: #e5e5e5;
    background-color: #2f2f31;
    alternate-background-color: #363636;
    font: 580 10pt "Segoe UI";
    show-decoration-selected: 1;
}

QListWidget::item, QListView::item {
    padding: 2px;
}

QListWidget::item:selected, QListView::item:selected {
    background-color: #515965;
    color: white;
}

QListWidget::item:hover, QListView::item:hover {
    background-color: #515965;
}
"""

qt_stylesheet_widgetlist2 = """
QListWidget, QListView {
    border: 2px solid #d0d0d0;
    border-color: rgba(94, 94, 94, 255);
    border-radius: 2px;
    padding: 2px;
    color: #e5e5e5;
    background-color: #2f2f31;
    alternate-background-color: #363636;
    font: 580 10pt "Segoe UI";
}

QListWidget::item, QListView::item {
    padding: 0px;
}

QListWidget::item:selected, QListView::item:selected {
    background-color: #515965;
    color: white;
}

QListWidget::item:hover, QListView::item:hover {
    background-color: #515965;
}
QLabel {
background-color: None;
}
"""

qt_stylesheet_tabbar = """
QTabBar {
    background-color: #272727;
    qproperty-drawBase: 0;
    qproperty-elideMode: "ElideNone";
}
QTabBar::tab {
    background-color: #272727;
    color: #a5a5a5;
    border-radius: 0px;
    padding: 4px 10px;
    margin: 0px;
    font: 580 9pt "Segoe UI";
    border: 1px solid transparent;
    border-bottom: 1px solid #464649;
    border-right: 1px solid rgba(94, 94, 94, 80);
}
QTabBar::tab:hover:!selected {
    background-color: #363637;
    color: #FFFFFF;
}
QTabBar::tab:selected {
    border: 1px solid #464649;
    border-top: 2px solid #4a83c9;
    border-bottom: 1px solid #2f2f31;
    border-top-left-radius: 2px;
    border-top-right-radius: 2px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
    color: #FFFFFF;
    background-color: #2f2f31;
    margin-bottom: -1px;
}
QTabBar::close-button {
    image: url(:/icons/valve_style/tab-closebutton.png);
    subcontrol-position: right;
    margin: 1px 1px 1px 4px;
}
QTabBar::close-button:hover {
    image: url(:/icons/valve_style/tab-closebutton-hovered.png);
}
QTabBar::close-button:pressed {
    image: url(:/icons/valve_style/tab-closebutton-selected-hovered.png);
}
"""

qt_stylesheet_lineedit = """
QLineEdit {
    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
    height:22px;
    padding-top: 2px;
    padding-bottom:2px;
    padding-left: 4px;
    padding-right: 4px;
    color: #e5e5e5;
    background-color: #2e2e2e;
}
QLineEdit:hover {
    background-color: #515965;
    color: white;
}
"""

qt_stylesheet_table = """
QTableView {
    color: #e5e5e5;
    border: none;
    background-color: #272727;
    alternate-background-color: #2f2f31;
    gridline-color: #3e3e41;
    selection-background-color: #515965;
    selection-color: white;
    font: 580 10pt "Segoe UI";
}

QHeaderView::section {
    background-color: #2e2e2e;
    color: #a5a5a5;
    padding: 5px;
    border: none;
    font: 600 10pt "Segoe UI";
}

QTableView QTableCornerButton::section {
    background-color: #2e2e2e;
    border: none;
}
"""

qt_stylesheet_viewport_toolbar = """
QWidget#SPE_Viewport3D_Toolbar {
    background-color: #2e2e2e;
    border: none;
}
QWidget#SPE_Viewport3D_Toolbar QLabel {
    font: 580 8pt "Segoe UI";
    color: #a5a5a5;
    background-color: transparent;
    border: none;
    padding: 0px;
}
"""

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