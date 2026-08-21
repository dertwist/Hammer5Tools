# The shared group-box look: a single rule above the title, no box around the
# content. Its own constant because src/styles/common.py also applies it to
# widgets one by one (apply_stylesheets), and the two copies drifted apart once
# — forms using apply_stylesheets drew a full bordered box while everything
# under the global sheet drew the top rule.
QSS_GROUPBOX = """
QGroupBox {
    border: 1px solid #5e5e5e;
    border-bottom: none;
    border-left: none;
    border-right: none;
    margin-top: 8px;
	padding-top: 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6;
    color: white;
}

QGroupBox::indicator {
    width: 13px;
    height: 13px;
}

QGroupBox::indicator:checked {
    image: url(://icons/arrow_drop_down.png);
}

QGroupBox::indicator:unchecked {
    image: url(://icons/arrow_drop_right.png);
}
"""

QT_Stylesheet_global = """
/* # background_neutral 272727
# background_Primary 2E2E2E
# background_Secondaty 2F2F31
# text_primary E5E5E5
# stroke 464649
# SelectedFill 515965
# text_Neutral A5A5A5
# pressed 6D7882 */


QLabel {
    font: 600 10pt "Segoe UI";
    padding-top: 2px;
    padding-bottom:2px;
    padding-left: 4px;
    padding-right: 4px;
    color: #e5e5e5;
}


/* ========================================================== */
""" + QSS_GROUPBOX + """
/* ========================================================== */
    QPushButton {

        font: 580 10pt "Segoe UI";
    

        border: 2px solid black;
        border-radius: 2px;
        border-color: rgba(94, 94, 94, 255);
        height:20px;
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
/* ========================================================== */


QToolTip {
    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(94, 94, 94, 255);
    height:18px;
    padding-top: 2px;
    padding-bottom:2px;
    padding-left: 4px;
    padding-right: 4px;
    color: #e5e5e5;
    background-color: #2e2e2e;
    }
/* ========================================================== */



QToolButton {

    font: 580 10pt "Segoe UI";
    border: 2px solid black;
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

}




/* ========================================================== */
QTabWidget {
    background-color: #272727;
}

QTabWidget::pane {
    border: 1px solid #464649;
    background-color: #2f2f31;
    border-radius: 0px;
    top: -1px;
}

QTabWidget#MainWindowTools_tabs::pane {
    border-bottom: none;
}

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

QToolButton#DocumentNewTabButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 2px;
    padding: 1px;
    margin: 0px;
}

QToolButton#DocumentNewTabButton:hover {
    background-color: #363639;
    border: 1px solid #464649;
}

QToolButton#DocumentNewTabButton:pressed {
    background-color: #464649;
}

/* ========================================================== */
QDockWidget {
    font: 580 9pt "Segoe UI";
    color: #e5e5e5;
    background-color: #3d3d3d;
    border: 2px solid #2e2e2e;
}

QDockWidget::title {
    background-color: #2e2e2e;
    /* padding: 4px; */
    font: 580 10pt "Segoe UI";
    color: #e5e5e5;
}

QDockWidget::slider {
    color: #2e2e2e;
}
QDockWidget::close-button, QDockWidget::float-button {
    border: 1px solid #2e2e2e;
    background: #2e2e2e;
    /* padding: 5px; */
}

QDockWidget::close-button:hover, QDockWidget::float-button:hover {
    background: #515965;
}

QDockWidget::close-button:pressed, QDockWidget::float-button:pressed {
    background: #2e2e2e;
}

QDockWidget DockTitleWidget {
  border-top: 1px solid #c0c0c0;
  border-bottom: 1px solid #c0c0c0;
  background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
    stop: 0.0 #d4d4d4, stop: 0.3 #d0d0d0,
    stop: 0.7 #cfcfcf, stop: 1.0 #c8c8c8);
}
QDockWidget DockTitleWidget QPushButton,
QDockWidget DockTitleWidget QToolButton {
  background: transparent;
  border: 1px solid transparent;
  right: 6px;
  top: 3px;
}
QDockWidget DockTitleWidget QPushButton:hover,
QDockWidget DockTitleWidget QToolButton:hover {
  border-color: #939393;
  border-radius: 2px;
  background: qlineargradient(x1:0, y1 : 0, x2 : 0, y2 : 1,
    stop : 0.0 #a8a8a8, stop : 0.3 #b3b3b3,
    stop : 0.7 #b2b2b2, stop : 1.0 #aaaaaa);
}
QDockWidget DockTitleWidget QPushButton::menu-indicator,
QDockWidget DockTitleWidget QToolButton::menu-indicator {
  image: none;
}


/* ========================================================== */

    QComboBox {

        font: 700 10pt "Segoe UI";
        border: 2px solid black;
        border-radius: 2px;
        border-color: rgba(94, 94, 94, 255);
        height:26px;
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
        alternate-background-color: #37373b;
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

/* ========================================================== */






/* ========================================================== */

QProgressBar {
    border: 2px solid #5ab55e; /* Border color */
    border-radius: 5px;        /* Rounded corners */
    text-align: center;        /* Center the text */
    color: #e5e5e5;            /* Text color */
    background-color: #2e2e2e; /* Background color */
    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(94, 94, 94, 255);
}


QProgressBar::chunk {
    background-color: #515965; /* Chunk color */
    width: 20px;               /* Chunk width */
    margin: 1px;               /* Space between chunks */
    border-radius: 2px;        /* Rounded corners */
}



/* ========================================================== */




QTextBrowser {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(94, 94, 94, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #e5e5e5;
    background-color: #2e2e2e;
}



QTextBrowser:focus {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(94, 94, 94, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #e5e5e5;
    background-color: #2e2e2e;
}
QTextBrowser:hover {
    background-color: #515965;
    color: white;
}
QTextBrowser:pressed {
    background-color: red;
    background-color: #2e2e2e;
    margin: 1 px;
    margin-left: 2px;
    margin-right: 2px;

}

/* ========================================================== */

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

QCheckBox::indicator:unchecked {
    image: url(://icons/check_box_outline_blank_16dp.svg);
}

QCheckBox::indicator:checked {
    image: url(://icons/select_check_box_16dp.svg);
}

/* ========================================================== */


QCheckBox:hover {
    background-color: #515965;
    color: white;
}

QRadioButton {
    font: 580 10pt "Segoe UI";
    color: #e5e5e5;
    padding-left: 2px;
}

QRadioButton::indicator:unchecked {
    image: url(://icons/radio_button_unchecked_24dp.svg);
    width: 16px;
    height: 16px;
}

QRadioButton::indicator:checked {
    image: url(://icons/radio_button_checked_24dp.svg);
    width: 16px;
    height: 16px;
}

QRadioButton:hover {
    background-color: #515965;
    color: white;
    border-radius: 2px;
}


QListView {
    background-color: #2f2f31;
    border: 0px;
    border-radius: 4px;
    font: 600 11pt "Segoe UI";
    color: #a2a79a;
    padding: 2px;
}


/* ========================================================== */





QPlainTextEdit {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #e5e5e5;
    background-color: #2e2e2e;
}



QPlainTextEdit{

    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(94, 94, 94, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
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
    margin: 1 px;
    margin-left: 2px;
    margin-right: 2px;

}



QTextBrowser{

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #e5e5e5;
    background-color: #2e2e2e;
}



QTextBrowser{

    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(94, 94, 94, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #e5e5e5;
    background-color: #2e2e2e;
}

QTextBrowser:hover {
} 

QTextBrowser:pressed {
    background-color: red;
    background-color: #2e2e2e;
    margin: 1 px;
    margin-left: 2px;
    margin-right: 2px;

}


QLineEdit {
    border: 2px solid #d0d0d0;
    border-color: rgba(94, 94, 94, 255);
    border-radius: 2px;
    padding: 2px;
    color: #e5e5e5;
}
QLineEdit:focus {
    border: 2px solid #1495c0;
    border-color: rgba(94, 94, 94, 255);
}
QLineEdit::selection {
    background-color: #515965;
    color: white;
} 




QTextEdit {
    border: 2px solid #d0d0d0;
    border-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
    padding: 2px;
    color: #e5e5e5;
}
QTextEdit:focus {
    border: 2px solid #1495c0;
    background-color: #e5e5e5;
}
QTextEdit::selection {
    background-color: #515965;
    color: white;
}

/* ========================================================== */

QSpinBox {
    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
    padding-left: 2px;
    padding-right: 2px;
    color: #e5e5e5;
    background-color: #2e2e2e;
}

QSpinBox:focus {
}

QSpinBox:hover {
}

QSpinBox:pressed {
	background-color: #252525;
}

QSpinBox::up-button {
    border: 0px solid black;
    subcontrol-origin: border;
    subcontrol-position: top right;
    border-left: 2px solid black;
    border-bottom: 0px solid black;
    border-top-right-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
	width:16px;
    margin:0px;
}

QSpinBox::up-arrow {
    image: url(://icons/arrow_drop_up_24dp.svg);
    width: 20px;
    height: 20px;
}

QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
	border: 0px solid black;
    border-left: 2px solid black;
    border-top: 2px solid black;
border-bottom-right-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
	width:16px;
    margin:0px;
}

QSpinBox::down-arrow {
    image: url(://icons/arrow_drop_down_16dp.svg);
    width: 20px;
    height: 20px;
}

/* ========================================================== */

QDoubleSpinBox {
    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
    padding-left: 2px;
    padding-right: 2px;
    color: #e5e5e5;
    background-color: #2e2e2e;
}

QDoubleSpinBox:focus {
}

QDoubleSpinBox:hover {
}

QDoubleSpinBox:pressed {
	background-color: #252525;
}

QDoubleSpinBox::up-button {
    border: 0px solid black;
    subcontrol-origin: border;
    subcontrol-position: top right;
    border-left: 2px solid black;
    border-bottom: 0px solid black;
    border-top-right-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
	width:16px;
    margin:0px;
}

QDoubleSpinBox::up-arrow {
    image: url(://icons/arrow_drop_up_24dp.svg);
    width: 20px;
    height: 20px;
}

QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
	border: 0px solid black;
    border-left: 2px solid black;
    border-top: 2px solid black;
border-bottom-right-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
	width:16px;
    margin:0px;
}

QDoubleSpinBox::down-arrow {
    image: url(://icons/arrow_drop_down_16dp.svg);
    width: 20px;
    height: 20px;
}


/* ========================================================== */



/* ========================================================== */
QScrollArea {
    border: 2px solid #d0d0d0;
    border-color: rgba(94, 94, 94, 255);
    border-radius: 2px;
    color: #e5e5e5;
}
/* ========================================================== */
QListWidget {
    border: 2px solid #d0d0d0;
    border-color: rgba(94, 94, 94, 255);
    border-radius: 2px;
    padding: 2px;
    color: #e5e5e5;
    background-color: #272727;
    show-decoration-selected: 1;
}
QListWidget::item {
    padding: 2px;
    alternate-background-color: #ff363636;
}
QListWidget::item:selected {
    background-color: #515965;
    color: white;
}

QListWidget::item:hover {
    background-color: #515965;
}

/* ========================================================== */

QListView {
    border: 2px solid #d0d0d0;
    border-color: rgba(94, 94, 94, 255);
    border-radius: 2px;
    padding: 2px;
    color: #e5e5e5;
    background-color: #272727;
    show-decoration-selected: 1;
}
QListView::item {
    padding: 0px;
}
QListView::item:selected {
    background-color: #515965;
    color:white;
}

QListView::item:hover {
    background-color: #515965;
}

/* ========================================================== */
QHeaderView::section {
    background-color: #2e2e2e;
    color: #a5a5a5;
    padding: 5px;
    border: none;
    font: 600 10pt "Segoe UI";
}
QTableWidget, QTableView {
    border: none;
    background-color: #272727;
    color: #e5e5e5;
    gridline-color: #3e3e41;
    outline: none;
}
QTableWidget::item, QTableView::item {
    padding: 5px;
    border-bottom: 1px solid #3e3e41;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: #515965;
    color: white;
}
QTableView QTableCornerButton::section {
    background-color: #2e2e2e;
    border: none;
}


QWidget {
    background-color: #272727;
    outline: none;
}

/* Opt-out for children that must not hide a parent's custom painting.
   The blanket rule above gives every widget in the application an opaque
   background, so a widget that draws in its paintEvent has its work covered up
   by its own children. Those children are marked with
   styles.common.mark_paint_through(). The attribute selector outranks the
   plain type selector above, so this wins without changing anything else. */
QWidget[paintThrough="true"] {
    background: transparent;
}

QWidget:item:checked {
    background-color: #272727;
    color: white;
}

QWidget:item:selected {
    background-color: #515965;
    color: white;
    border: 0px;
}
/* ========================================================== */

QMenu {
    background-color: #2f2f31;
    color: #d0d0d0;
    border: 1px solid #636363;
    border: 2px solid black;
    border-radius: 1px;
    border-color: rgba(94, 94, 94, 255);
}

QMenu::item {
    font: 600 10pt "Segoe UI";
    border: 1px solid transparent; 
    border-radius: 1px;
    border-top: 0px;
    border-bottom: 2px solid transparent;
    border-color: rgba(94, 94, 94, 105);
    padding: 4px 8px 4px 8px;
    padding-right: 20px;
    color: #d0d0d0;
}

QMenu::item:selected {
    background-color: #515965;
    color: #FFFFFF;
    border: 1px solid transparent; 
    border-radius: 1px;
    border-top: 0px;
    border-bottom: 2px solid transparent;
    border-color: rgba(94, 94, 94, 105);
}

QMenu::item:disabled {
    color: #636363;
    background-color: transparent;
}

QMenu::item:selected:disabled {
    color: #636363;
    background-color: transparent;
}

QMenu::separator {
    height: 1px;
    background: #6e727a;
    /* margin: 5px 0; */
}

QMenu::indicator {
    width: 13px;
    height: 13px;
}

QMenu::indicator:checked {
    image: url(:/icons/check_16dp.svg);
}

QMenu::indicator:unchecked {
    image: url(:/icons/check_box_outline_blank_16dp.svg);
}


/* ========================================================== */


QMenuBar {
    color: white;
}

QMenuBar::item {
    background-color: #2e2e2e;
    color: white;
    padding-left: 12px;
    padding-right: 12px; 
    padding-bottom: 2px;
    padding-top: 2px;
    
}

QMenuBar::item:selected {
    background-color: #515965;
}

QMenuBar::item:pressed {
    background-color: #515965;
}

QMenuBar::item:disabled {
    color: #636363;
    background-color: transparent;
}





/* ========================================================== */



QScrollBar:horizontal
{
    height: 15px;
    margin: 3px 3px 3px 3px;
    border: 1px transparent #3b3a3a;
    border-radius: 0px;
    background-color: #3b3a3a;
}

QScrollBar::handle:horizontal
{
    background-color: #515965;
    min-width: 5px;
    border-radius: 0px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal
{
    width: 0px;
    height: 0px;
}

QScrollBar::up-arrow:horizontal, QScrollBar::down-arrow:horizontal
{
    width: 0px;
    height: 0px;
    background: none;
}


QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal
{
    background: none;
}

/* ========================================================== */

QScrollBar:vertical
{
    background-color: #3b3a3a;
    width: 15px;
    margin: 3px 3px 3px 3px;
    border: 1px transparent #3b3a3a;
    border-radius: 0px;
}

QScrollBar::handle:vertical
{
    background-color: #515965;         /* #605F5F; */
    min-height: 5px;
    border-radius: 0px;
}

QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical
{
    height: 0px;
    width: 0px;
}

QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical
{
    height: 0px;
    width: 0px;
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical
{
    background: none;
}

/* ========================================================== */




QSlider::groove:horizontal {
    border: 2px solid black;
    border-color: rgba(94, 94, 94, 0);
    height: 2px;
    margin: 2px 0;
}

QSlider::handle:horizontal {
    background: #515965;
    border: 2px solid black;
    border-color: rgba(94, 94, 94, 255);
    width: 6px;
    height: 36px;  
    margin: -17px 0; 
}

QSlider::handle:horizontal:hover {
}

QSlider::handle:horizontal:pressed {
}

QSlider::sub-page:horizontal {
    background: #35383e;
    border: 2px solid black;
    border-radius: 1px;
    border-color: rgba(94, 94, 94, 255);
    height: 2px;
}

QSlider::add-page:horizontal {
    border: 2px solid black;
    border-radius: 1px;
    border-color: rgba(94, 94, 94, 255);
    height: 2px;
}

/* ========================================================== */


QTreeView {
    color: #e5e5e5;
    border: 2px solid black;
    border-radius: 1px;
    border-color: rgba(94, 94, 94, 255);
    font: 580 10pt "Segoe UI";
    background-color: #272727;
    alternate-background-color: #ff363636;
}

QTreeView::item {
    padding-left: 1px;
    padding-right: 1px;
    padding-top: 2px;
    padding-bottom: 2px;
/*    color: #e5e5e5;*/
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
}



/* Header view styling */
QHeaderView::section {
    background-color: #2f2f31;
    color: #e5e5e5;
    font: 600 10pt "Segoe UI";
    height: 16px;
    border: 0px;
    border-bottom: 2px solid black;
    border-radius: 2px;
    border-color: rgba(94, 94, 94, 255);
}




/* ========================================================== */


QStatusBar {
    background-color: #2e2e2e;
    color: #e5e5e5;
    font: 600 10pt "Segoe UI";
    border-top: 1px solid #585858;
}
QStatusBar::item {
    border: none;
}


/* ========================================================== */



QSplitter {
    border: none;
}
QSplitter::handle {
    background-color: #2e2e2e;
    margin: 1px 1px;
}
QSplitter::handle:hover {
    background-color: #2e2e2e;
}

QSplitterHandle::hover {}

QSplitter::handle:vertical:hover, QSplitter::handle:horizontal:hover {
    background: #5e5e5e;
}
QSplitter::handle:vertical {
/*    image: url(://icons/splitter-vertical.svg);*/
/*    width: 13px;
    height: 16px;
    padding: 0px;*/
    margin: 0px;
}  

QSplitter::handle:horizontal {
/*    image: url(://icons/splitter-horizontal.svg);
    height: 13px;
    width: 16px;*/
    padding: 0px;
    margin: 0px;
}


"""