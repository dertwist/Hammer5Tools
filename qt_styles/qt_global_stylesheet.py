QT_Stylesheet_global = """
/* # background_neutral 151515
# background_Primary 1C1C1C
# background_Secondaty 1d1d1f
# text_primary E3E3E3
# stroke 363639
# SelectedFill 414956
# text_Neutral 9D9D9D
# pressed 606C77 */


QLabel {
    font: 700 10pt "Segoe UI";
    padding-top: 2px;
    padding-bottom:2px;
    padding-left: 4px;
    padding-right: 4px;
    color: #E3E3E3;
}

/* QPushButton default and hover styles */
QPushButton {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding-top: 2px;
    padding-bottom:2px;
    padding-left: 4px;
    padding-right: 4px;
    color: #E3E3E3;
    background-color: #1C1C1C;
}
QPushButton:hover {
    background-color: #414956;
    color: white;
}
QPushButton:pressed {
    background-color: red;
    background-color: #1C1C1C;
    margin: 1 px;
    margin-left: 2px;
    margin-right: 2px;
}
/* -------------------------- */


QToolTip {
    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding-top: 2px;
    padding-bottom:2px;
    padding-left: 4px;
    padding-right: 4px;
    color: #E3E3E3;
    background-color: #1C1C1C;
    }
/* -------------------------- */



QToolButton {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #E3E3E3;
    background-color: #1C1C1C;
}
QToolButton:hover {
    background-color: #414956;
    color: white;
}
QToolButton:pressed {
    background-color: red;
    background-color: #1C1C1C;
    margin: 1 px;
    margin-left: 2px;
    margin-right: 2px;
    font: 580 9pt "Segoe UI";

}



/* -------------------------- */
QTabWidget::pane {
    background-color: solid red;
    border-radius: 0px;
    border: 2px solid gray;
    border-color: #363639;
    background-color: #1d1d1f;
}

QTabBar::tab {
    background-color: #323232;
    color: #9A9F91;
    border-radius: 0px;
    border-top-right-radius: 0px;
    border-top-left-radius: 0px;
    padding: 4px;
    padding-left:48px;
    padding-right: 48px;

    border-top: 2px solid gray;
    border-bottom: 0px solid black;

    font: 700 10pt "Segoe UI";
    border-left: 2px solid darkgray;
    border-top: 0px solid darkgray;
    border-color: #151515;
    border-right: 2px solid rgba(80, 80, 80, 80);



    color: #E3E3E3;
    background-color: #151515;

}
QTabBar::tab:selected {
    border-radius: 0px;
    border-top-right-radius: 7px;
    border-top-left-radius: 7px;

    border-top: 2px solid gray;
    border-left: 2px solid gray;
    border-right: 2px solid gray;
    border-bottom: 0px solid black;

    font: 700 10pt "Segoe UI";
    border-color: rgba(80, 80, 80, 180);
    height:20px;
    color: #E3E3E3;
    background-color: #1d1d1f;
}


/* -------------------------- */

QComboBox {
    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    height: 18px;
    padding-top: 5px;
    padding-bottom: 5px;
    color: #E3E3E3;
    background-color: #1C1C1C;
    padding-left: 5px;
}

QComboBox:hover {
    background-color: #414956;
    color: white;
}

QComboBox:pressed {
    background-color: #2E2F30;
    color: white;
}

QComboBox:item {
    font: 600 12pt "Segoe UI";
    color: #E3E3E3;
    padding-left: 5px;
    background-color: #1C1C1C;
    border-style: none;
}

QComboBox::drop-down {
    color: #E3E3E3;
    padding: 2px;
    background: url(://icons/arrow_drop_down_16dp.svg) no-repeat center;
    border-bottom: 0px solid black;
    border-top: 0px solid black;
    border-right: 0px;
    border-left: 2px solid;
    margin-left: 5px;
    padding: 5px;
    width: 7px;
    border-color: rgba(80, 80, 80, 255);
    background-color: #1C1C1C;
}

/* Style the drop-down list view */
QComboBox QAbstractItemView {
    border: 2px solid gray;
    border-color: rgba(80, 80, 80, 255);
    selection-background-color: #414956;
    background-color: #1C1C1C;
}

/* Style individual items in the drop-down list */
QComboBox QAbstractItemView::item {
    height: 16px; /* Set the height of each item */
    padding: 4px; /* Add padding to each item */
    padding-left: 5px;
    padding-right: 5px;
    color: #ff8a8a8a;
    border-style: none;
    border-bottom: 0.5px solid black;
    border-color: rgba(255, 255, 255, 10);
}

/* Style the selected item in the drop-down list */
QComboBox QAbstractItemView::item:selected {
    height: 16px; /* Set the height of each item */
    padding: 4px; /* Add padding to each item */
    padding-left: 5px;
    padding-right: 5px;
    background-color: #414956;
    color: white;
    border: none; /* Remove border */
    outline: none; /* Remove outline */
}

/* -------------------------- */





QPlainTextEdit {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #E3E3E3;
    background-color: #1C1C1C;
}



QPlainTextEdit:focus {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #E3E3E3;
    background-color: #1C1C1C;
}
QPlainTextEdit:hover {
    background-color: #414956;
    color: white;
}
QPlainTextEdit:pressed {
    background-color: red;
    background-color: #1C1C1C;
    margin: 1 px;
    margin-left: 2px;
    margin-right: 2px;

}


    /* -------------------------- */



/* QProgressBar - General Style */
QProgressBar {
    border: 2px solid #4CAF50; /* Border color */
    border-radius: 5px;        /* Rounded corners */
    text-align: center;        /* Center the text */
    color: #E3E3E3;            /* Text color */
    background-color: #1C1C1C; /* Background color */
    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
}

/* QProgressBar - Chunk Style */
QProgressBar::chunk {
    background-color: #414956; /* Chunk color */
    width: 20px;               /* Chunk width */
    margin: 1px;               /* Space between chunks */
    border-radius: 2px;        /* Rounded corners */
}




    /* -------------------------- */




QTextBrowser {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #E3E3E3;
    background-color: #1C1C1C;
}



QTextBrowser:focus {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #E3E3E3;
    background-color: #1C1C1C;
}
QTextBrowser:hover {
    background-color: #414956;
    color: white;
}
QTextBrowser:pressed {
    background-color: red;
    background-color: #1C1C1C;
    margin: 1 px;
    margin-left: 2px;
    margin-right: 2px;

}

/* -------------------------- */

QCheckBox {
    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    height:14px;
    padding-top: 2px;
    padding-bottom:2px;
    color: #E3E3E3;
    background-color: #1C1C1C;
    padding-left: 4px;
}

QCheckBox::indicator:unchecked {
    image: url(://icons/check_box_outline_blank_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);
}

QCheckBox::indicator:checked {
    image: url(://icons/select_check_box_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);
}

/* -------------------------- */


QCheckBox:hover {
    background-color: #414956;
    color: white;
}


QListView {
    background-color: #1d1d1f;
    border: 0px;
    border-radius: 4px;
    font: 600 12pt "Segoe UI";
    color: #9A9F91;
    padding: 2px;
}


    /* -------------------------- */





QPlainTextEdit {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #E3E3E3;
    background-color: #1C1C1C;
}



QPlainTextEdit{

    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #E3E3E3;
    background-color: #1C1C1C;
}
QPlainTextEdit:hover {
    background-color: #414956;
    color: white;
}
QPlainTextEdit:pressed {
    background-color: red;
    background-color: #1C1C1C;
    margin: 1 px;
    margin-left: 2px;
    margin-right: 2px;

}




QLineEdit {
    border: 2px solid #CCCCCC;
    border-color: rgba(80, 80, 80, 255);
    border-radius: 2px;
    padding: 2px;
    color: #E3E3E3;
}
QLineEdit:focus {
    border: 2px solid #008CBA;
    border-color: rgba(80, 80, 80, 255);
}
QLineEdit::selection {
    background-color: #414956;
    color: white;
}




QTextEdit {
    border: 2px solid #CCCCCC;
    border-radius: 2px;
    border-color: rgba(80, 80, 80, 255);
    padding: 2px;
    color: #E3E3E3;
}
QTextEdit:focus {
    border: 2px solid #008CBA;
    background-color: #E3E3E3;
}
QTextEdit::selection {
    background-color: #414956;
    color: white;
}



/* QListWidget item and selection styles */
QScrollArea {
    border: 2px solid #CCCCCC;
    border-color: rgba(80, 80, 80, 255);
    border-radius: 2px;
    color: #E3E3E3;
}
/* QListWidget item and selection styles */
QListWidget {
    border: 2px solid #CCCCCC;
    border-color: rgba(80, 80, 80, 255);
    border-radius: 2px;
    padding: 2px;
    color: #E3E3E3;
}
QListWidget::item {
    padding: 0px;
}
QListWidget::item:selected {
    background-color: #414956;
    color:white;
}

QListWidget::item:hover {
    background-color: #414956;
}

/* QListView item and selection styles */

QListView {
    border: 2px solid #CCCCCC;
    border-color: rgba(80, 80, 80, 255);
    border-radius: 2px;
    padding: 2px;
    color: #E3E3E3;
}
QListView::item {
    padding: 0px;
}
QListView::item:selected {
    background-color: #414956;
    color:white;
}

QListView::item:hover {
    background-color: #414956;
}

/* QTableWidget header and cell styles */
QHeaderView::section {
    background-color: #D0D0D0;
    padding: 5px;
    border: 1px solid #CCCCCC;
}
QTableWidget {
    border: 1px solid #CCCCCC;
    border-radius: 5px;
    background-color: #FFFFFF;
}
QTableWidget::item {
    padding: 5px;
    border-bottom: 1px solid #E0E0E0;
}
QTableWidget::item:selected {
    background-color: #414956;
    color: white;
}



QMenu {
background-color: red;
 }

QMenu::item {
    padding: 5px 10px;
    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    color: #E3E3E3;
}
QMenu::item:selected {
    background-color: #414956;
    color: white;
}
QWidget {
    background-color: #151515;
    outline: none;
        /* icon-size: 20px 20px; */
}

QWidget:item:checked {
    background-color: #151515;
    color: white;
}

QWidget:item:selected {
    background-color: #414956;
    color: white;
    border: 0px;
}



QMenu {
    background-color: #1d1d1f;
    color: #FFFFFF;
    border: 1px solid #555555;
    /* padding-top: 5px; */
    /* padding-bottom: 5px; */
    border: 2px solid black;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
}

QMenu::item {
    font: 700 10pt "Segoe UI";
    border-top: 2px solid black;
    border: 0px;
    border-radius: 4px;
    border-color: rgba(80, 80, 80, 255);
    padding-left: 12px;
    padding-right: 12px;
    color: #E3E3E3;
}

QMenu::item:selected {
    background-color: #666666;
    color: #FFFFFF;
}

QMenu::separator {
    height: 1px;
    background: #AAAAAA;
    margin: 5px 0;
}

QMenu::indicator {
    width: 13px;
    height: 13px;
}

QMenu::indicator:checked {
    image: url(:/images/checkmark.png);
}

QMenu::indicator:unchecked {
    image: url(:/images/empty.png);
}






/* --------------------------------------------------- */



QScrollBar:horizontal
{
    height: 15px;
    margin: 3px 15px 3px 15px;
    border: 1px transparent #2A2929;
    border-radius: 4px;
    background-color: #2A2929;
}

QScrollBar::handle:horizontal
{
    background-color: #414956;
    min-width: 5px;
    border-radius: 4px;
}

QScrollBar::add-line:horizontal
{
    margin: 0px 3px 0px 3px;
    border-image: url(:/qss_icons/rc/right_arrow_disabled.png);
    width: 10px;
    height: 10px;
    subcontrol-position: right;
    subcontrol-origin: margin;
}

QScrollBar::sub-line:horizontal
{
    margin: 0px 3px 0px 3px;
    border-image: url(:/qss_icons/rc/left_arrow_disabled.png);
    height: 10px;
    width: 10px;
    subcontrol-position: left;
    subcontrol-origin: margin;
}

QScrollBar::add-line:horizontal:hover,QScrollBar::add-line:horizontal:on
{
    border-image: url(:/qss_icons/rc/right_arrow.png);
    height: 10px;
    width: 10px;
    subcontrol-position: right;
    subcontrol-origin: margin;
}


QScrollBar::sub-line:horizontal:hover, QScrollBar::sub-line:horizontal:on
{
    border-image: url(:/qss_icons/rc/left_arrow.png);
    height: 10px;
    width: 10px;
    subcontrol-position: left;
    subcontrol-origin: margin;
}

QScrollBar::up-arrow:horizontal, QScrollBar::down-arrow:horizontal
{
    background: none;
}


QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal
{
    background: none;
}

QScrollBar:vertical
{
    background-color: #2A2929;
    width: 15px;
    margin: 15px 3px 15px 3px;
    border: 1px transparent #2A2929;
    border-radius: 4px;
}

QScrollBar::handle:vertical
{
    background-color: #414956;         /* #605F5F; */
    min-height: 5px;
    border-radius: 4px;
}
    /* Vertical */
QScrollBar::sub-line:vertical
{
    margin: 3px 0px 3px 0px;
    border-image: url(:/qss_icons/rc/up_arrow_disabled.png);
    height: 10px;
    width: 10px;
    subcontrol-position: top;
    subcontrol-origin: margin;
}

QScrollBar::add-line:vertical
{
    margin: 3px 0px 3px 0px;
    border-image: url(:/qss_icons/rc/down_arrow_disabled.png);
    height: 10px;
    width: 10px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
}

QScrollBar::sub-line:vertical:hover,QScrollBar::sub-line:vertical:on
{
    border-image: url(:/qss_icons/rc/up_arrow.png);
    height: 10px;
    width: 10px;
    subcontrol-position: top;
    subcontrol-origin: margin;
}

QScrollBar::add-line:vertical:hover, QScrollBar::add-line:vertical:on
{
    border-image: url(:/qss_icons/rc/down_arrow.png);
    height: 10px;
    width: 10px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
}

QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical
{
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical
{
    background: none;
}

/* -------------------------- */







/* tree */

/* styles/treeview.qss */

/* General application background */
/* TreeView specific styles */
QTreeView {
    color: #E3E3E3;
    border: 1px solid black;
    border-radius: 2px;
    border-color: rgba(80, 80, 80, 255);
    font: 580 10pt "Segoe UI";
}

QTreeView::item {
    height: 20px;
}

QTreeView::item:selected {
    background-color: #272729;
    color: #E3E3E3;
}

QTreeView::item:hover {
    background-color: #272729;
    color: #E3E3E3;
}

/* Branch icons */
QTreeView::branch:closed:has-children {
    /* Ensure this path is correct and the image exists */
    image: url(:/icons/arrow_drop_down_16dp.svg);
}

QTreeView::branch:open:has-children {
    /* Ensure this path is correct and the image exists */
    image: url(:/icons/arrow_right_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);
}

/* Header styles */
QHeaderView::section {
    background-color: #1d1d1f;
    color: #E3E3E3;
    font: 600 10pt "Segoe UI";
    height: 16px;
    border: 0px;
    border-bottom: 2px solid black;
    border-radius: 2px;
    border-color: rgba(80, 80, 80, 255);
}

/* QHeaderView::section:hover {
    background-color: #565656;
}

QHeaderView::section:pressed {
    background-color: #444444;
} */




/* --------------------------------------------------------------------------------------------- Menubar ---------------------------------------------------------------------------------------------*/


QMenuBar {
    background-color: #333;
    color: white;
}

QMenuBar::item {
    background-color: #333;
    color: white;
    padding-left: 12px;
    padding-right: 12px; /* Added padding-right to make items wider */
    padding-bottom: 12px;
    padding-top: 6px;
}

QMenuBar::item:selected {
    background-color: #555;
}

QMenuBar::item:pressed {
    background-color: #777;
}

QMenu::item:selected {
    background-color: #555;
}
/* --------------------------------------------------------------------------------------------- Statusbar ---------------------------------------------------------------------------------------------*/


QStatusBar {
    background-color: #1C1C1C;
    color: #E3E3E3;
    font: 600 10pt "Segoe UI";
    border-top: 1px solid #4A4A4A;
}
QStatusBar::item {
    border: none;
}


"""