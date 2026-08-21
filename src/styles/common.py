from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QTreeView,
    QCheckBox,
    QPushButton,
    QToolButton,
    QComboBox,
    QFrame,
    QPlainTextEdit,
    QListWidget,
    QListView,
    QTabBar,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QRadioButton,
    QGroupBox,
    QProgressBar,
    QLineEdit,
    QTableView,
    QHeaderView
)
import sys

qt_stylesheet_colors = {
    'background_neutral': '#272727',
    'background_Primary': '#2e2e2e',
    'background_Secondary': '#2f2f31',
    'text_primary': '#e5e5e5',
    'stroke': '#464649',
    'SelectedFill': '#515965',
    'text_Neutral': '#a5a5a5',
    'text_Neutral_second': '#797979',
    'pressed': '#6d7882'
}
qt_stylesheet_classes = {
    'label':
        """
        QLabel {
        font-size: 8pt;
        font-family: "Segoe UI";
        border: none;
        border-radius: 0px;
        padding: 2px;
        color: #e5e5e5;
        background-color: transparent;
        }
        """,
    'label_second':
        """
        QLabel {
        font-size: 8pt;
        font-family: "Segoe UI";
        border-top: 0px;
        border-left: 0px;
        border-right: 0px;
        border-bottom: 2px solid rgba(94, 94, 94, 255);
        border-radius: 0px;
        padding: 2px;
        color: #797979;
        background-color: #363636;
        }
        """,
    'tree':
        """QTreeView {
        color: #e5e5e5;
        border: 2px solid black;
        border-radius: 1px;
        border-color: rgba(94, 94, 94, 255);
        font: 580 10pt "Segoe UI";
        background-color: #3a3a3a; /* Background color for the tree view */
        alternate-background-color: #ff363636;
    }
    
    QTreeView::item {
        padding-left: 1px;
        padding-right: 1px;
        padding-top: 2px;
        padding-bottom: 2px;
        border-style: none;
        border-bottom: 0.5px solid black;
        border-color: rgba(255, 255, 255, 10);
    }
    
    QTreeView::item:selected {
        background-color: #515965; /* Background color for selected item */
        alternate-background-color: #515965; /* Background color for selected item */
        color: white; /* Text color for selected item */
    }
    
    QTreeView::item:hover {
        background-color: #38383a; /* Background color for hovered item */
        color: #e5e5e5; /* Text color for hovered item */
    }
    
    QTreeView::branch:has-siblings {
        border-image: url(:/icons/vertical_line.png) 0; /* Set the vertical line for branches with siblings */
    }
    
    QTreeView::branch:has-siblings:adjoins-item {
        border-image: none; /* Remove the line where the branch adjoins an item */
    }
    
    
    QTreeView::branch:closed:has-children {
         image: url(:/icons/arrow_right_16dp.svg);
    }
    
    QTreeView::branch:open:has-children {
         /* Icon for open branch */
        image: url(:/icons/arrow_drop_down_16dp.svg);
    }
    
    /* Remove border for edit line in tree */
    QTreeView::item QLineEdit {
        border: none;
        margin: 0px;
        padding: 0px;
        background-color: #2e2e2e; /* Match the background color of the tree view */
        color: #e5e5e5; /* Match the text color of the tree view */
    }"""
}
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
qt_stylesheet_smartprop_editor_frame = """.QFrame {
    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 0px;
    border-left: 0px;
    border-right: 0px;
	border-top: 0px;
    border-color: rgba(66, 66, 66, 255);
    color: #e5e5e5;
    background-color: #2e2e2e;
}

.QFrame::hover {
}
.QFrame::selected {
    background-color: #515965;
}"""

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

qt_stylesheet_widgetlist = """
QListWidget, QListView {
    border: 2px solid #d0d0d0;
    border-color: rgba(94, 94, 94, 255);
    border-radius: 2px;
    padding: 2px;
    color: #e5e5e5;
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

qt_stylesheet_widgetlist2 = """
QListWidget, QListView {
    border: 2px solid #d0d0d0;
    border-color: rgba(94, 94, 94, 255);
    border-radius: 2px;
    padding: 2px;
    color: #e5e5e5;
    background-color: #2f2f31;
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

# One definition, shared with the global sheet — see QSS_GROUPBOX for why.
from src.styles.qt_global_stylesheet import QSS_GROUPBOX as qt_stylesheet_groupbox

qt_stylesheet_radiobutton = """
QRadioButton {
    color: #e5e5e5;
    font: 580 10pt "Segoe UI";
}
QRadioButton::indicator {
    width: 12px;
    height: 12px;
    border-radius: 6px;
}
QRadioButton::indicator::unchecked {
    border: 2px solid rgba(94, 94, 94, 255);
    background-color: #2e2e2e;
}
QRadioButton::indicator:unchecked:hover {
    background-color: #515965;
}
QRadioButton::indicator::checked {
    border: 2px solid #4d92c2;
    background-color: #4d92c2;
}
"""

qt_stylesheet_progressbar = """
QProgressBar {
    border: 2px solid rgba(94, 94, 94, 255);
    border-radius: 2px;
    text-align: center;
    color: #e5e5e5;
    font: 700 10pt "Segoe UI";
    background-color: #2e2e2e;
}
QProgressBar::chunk {
    background-color: #515965;
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
#: qt_global_stylesheet.QT_Stylesheet_global.
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


def apply_stylesheets(parent: QWidget) -> None:
    """
    Applies registered QT stylesheets to all child widgets of the given parent.

    The mapping below associates widget types with the corresponding internal stylesheet.
    """
    widget_styles = {
        QLabel: qt_stylesheet_classes.get('label'),
        QTreeView: qt_stylesheet_classes.get('tree'),
        QCheckBox: qt_stylesheet_checkbox,
        QPushButton: qt_stylesheet_button,
        QToolButton: qt_stylesheet_toolbutton,
        QComboBox: qt_stylesheet_combobox,
        QFrame: qt_stylesheet_smartprop_editor_frame,
        QPlainTextEdit: qt_stylesheet_plain_text_batch_inline,
        QListWidget: qt_stylesheet_widgetlist,
        QListView: qt_stylesheet_widgetlist,
        QTabBar: qt_stylesheet_tabbar,
        QGroupBox: qt_stylesheet_groupbox,
        QRadioButton: qt_stylesheet_radiobutton,
        QProgressBar: qt_stylesheet_progressbar,
        QLineEdit: qt_stylesheet_lineedit,
        QTableView: qt_stylesheet_table
    }
    for widget_type, style in widget_styles.items():
        if style is None: continue
        # Find all children of this widget type and apply the stylesheet.
        for child in parent.findChildren(widget_type):
            # A widget that styled itself keeps its own sheet. findChildren is
            # subclass-inclusive, so QTextEdit/QTextBrowser come back as QFrames
            # and used to be handed a `.QFrame`-only sheet - which matches
            # nothing on them, leaving the widget unstyled and white.
            if child.styleSheet():
                continue
            child.setStyleSheet(style)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QT Stylesheet Application Example")
        main_layout = QVBoxLayout(self)

        # Create examples of various widgets.
        label = QLabel("This is a label", self)
        tree_view = QTreeView(self)
        checkbox = QCheckBox("Check me!", self)
        button = QPushButton("Press me!", self)
        combobox = QComboBox(self)
        combobox.addItems(["Option 1", "Option 2", "Option 3"])
        frame = QFrame(self)
        plain_text = QPlainTextEdit("Editable text", self)
        list_widget = QListWidget(self)
        list_widget.addItems(["List Item 1", "List Item 2"])
        tab_bar = QTabBar(self)
        tab_bar.addTab("Tab 1")
        tab_bar.addTab("Tab 2")

        # Adding widgets to layout. A grid layout to showcase multiple widgets.
        grid_layout = QGridLayout()
        grid_layout.addWidget(label, 0, 0)
        grid_layout.addWidget(tree_view, 0, 1)
        grid_layout.addWidget(checkbox, 1, 0)
        grid_layout.addWidget(button, 1, 1)
        grid_layout.addWidget(combobox, 2, 0)
        grid_layout.addWidget(frame, 2, 1)
        grid_layout.addWidget(plain_text, 3, 0)
        grid_layout.addWidget(list_widget, 3, 1)
        grid_layout.addWidget(tab_bar, 4, 0, 1, 2)

        main_layout.addLayout(grid_layout)

        # Apply the defined stylesheets to all child widgets.
        apply_stylesheets(self)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec_())