qt_stylesheet_colors = {
    'background_neutral': '#151515',
    'background_Primary': '#1C1C1C',
    'background_Secondary': '#1d1d1f',
    'text_primary': '#E3E3E3',
    'stroke': '#363639',
    'SelectedFill': '#414956',
    'text_Neutral': '#9D9D9D',
    'text_Neutral_second': '#6D6D6D',
    'pressed': '#606C77'
}
qt_stylesheet_classes = {
    'label':
        """
        QLabel {
        font-size: 8pt;
        font-family: "Segoe UI";
        border-top: 0px;
        border-left: 0px;
        border-right: 0px;
        border-bottom: 2px solid rgba(80, 80, 80, 255);
        border-radius: 0px;
        padding: 2px;
        color: #6D6D6D;
        background-color: #9D9D9D;
        """,
    'label_second':
        """
        QLabel {
        font-size: 8pt;
        font-family: "Segoe UI";
        border-top: 0px;
        border-left: 0px;
        border-right: 0px;
        border-bottom: 2px solid rgba(80, 80, 80, 255);
        border-radius: 0px;
        padding: 2px;
        color: #6D6D6D;
        background-color: #242424;
        """,
    'tree':
        """QTreeView {
        color: #E3E3E3;
        border: 2px solid black;
        border-radius: 1px;
        border-color: rgba(80, 80, 80, 255);
        font: 580 10pt "Segoe UI";
        background-color: #292929; /* Background color for the tree view */
        alternate-background-color: #ff242424;
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
        background-color: #414956; /* Background color for selected item */
        alternate-background-color: #414956; /* Background color for selected item */
        color: white; /* Text color for selected item */
    }
    
    QTreeView::item:hover {
        background-color: #272729; /* Background color for hovered item */
        color: #E3E3E3; /* Text color for hovered item */
    }
    
    QTreeView::branch:has-siblings {
        border-image: url(:/icons/vertical_line.png) 0; /* Set the vertical line for branches with siblings */
    }
    
    QTreeView::branch:has-siblings:adjoins-item {
        border-image: none; /* Remove the line where the branch adjoins an item */
    }
    
    
    QTreeView::branch:closed:has-children {
         image: url(:/icons/arrow_right_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);
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
        background-color: #1C1C1C; /* Match the background color of the tree view */
        color: #E3E3E3; /* Match the text color of the tree view */
    }"""
}
qt_stylesheet_checkbox = """
    QCheckBox {

        font: 580 10pt "Segoe UI";

        border: 2px solid black;
        border-radius: 2px;
        border-color: rgba(80, 80, 80, 255);
        height:22px;
        padding-top: 2px;
        padding-bottom:2px;
        padding-left: 4px;
        padding-right: 4px;
        color: #E3E3E3;
        background-color: #1C1C1C;
    }
    QCheckBox:hover {
        background-color: #414956;
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
        border-color: rgba(80, 80, 80, 255);
        height:22px;
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

    }"""
# padding:2px; font: 580 9pt "Segoe UI"; padding-left:4px
qt_stylesheet_combobox = """
    /* QPushButton default and hover styles */
    QComboBox {

        font: 580 9pt "Segoe UI";
        border: 2px solid black;
        border-radius: 2px;
        border-color: rgba(80, 80, 80, 255);
        height:22px;
        padding-top: 2px;
        padding-bottom:2px;
        padding-left: 4px;
        padding-right: 4px;
        color: #E3E3E3;
        background-color: #1C1C1C;
    }
    QComboBox:hover {
        background-color: #414956;
        color: white;
    }
    QComboBox:pressed {

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
    
    
    QComboBox QAbstractItemView {
        border: 2px solid gray;
        border-color: rgba(80, 80, 80, 255);
        selection-background-color: #414956;
        background-color: #1C1C1C;
    }
    
    
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
"""
qt_stylesheet_smartprop_editor_frame = """.QFrame {
    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 0px;
    border-left: 0px;
    border-right: 0px;
	border-top: 0px;
    border-color: rgba(50, 50, 50, 255);
    color: #E3E3E3;
    background-color: #1C1C1C;
}

.QFrame::hover {
}
.QFrame::selected {
    background-color: #414956;
}"""

qt_stylesheet_plain_text_batch_inline = """QPlainTextEdit {

    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 2px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 0px;  /* Remove padding */
    padding-left: 0px;  /* Remove left padding */
    padding-right: 0px;  /* Remove right padding */
    color: #E3E3E3;
    background-color: #1C1C1C;
}



QPlainTextEdit{

    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 2px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 0px;  /* Remove padding */
    padding-left: 0px;  /* Remove left padding */
    padding-right: 0px;  /* Remove right padding */
    color: #E3E3E3;
    background-color: #1C1C1C;
}

/* QPlainTextEdit:hover {
    background-color: #414956;
    color: white;
} */

QPlainTextEdit:pressed {
    background-color: red;
    background-color: #1C1C1C;
    margin: 0px;  /* Remove margin */
    margin-left: 0px;  /* Remove left margin */
    margin-right: 0px;  /* Remove right margin */
}"""

qt_stylesheet_widgetlist = """
QListWidget, QListView {
    border: 2px solid #CCCCCC;
    border-color: rgba(80, 80, 80, 255);
    border-radius: 2px;
    padding: 2px;
    color: #E3E3E3;
}

QListWidget::item, QListView::item {
    padding: 0px;
}

QListWidget::item:selected, QListView::item:selected {
    background-color: #414956;
    color: white;
}

QListWidget::item:hover, QListView::item:hover {
    background-color: #414956;
}
QLabel {
background-color: None;
}
"""

qt_stylesheet_tabbar = """
QTabBar::tab {
    background-color: #323232;
    color: #9A9F91;
    border-radius: 0px;
    border-top-right-radius: 0px;
    border-top-left-radius: 0px;
    padding: 4px;
    padding-left:8px;
    padding-right: 8px;

    border-top: 2px solid gray;
    border-bottom: 0px solid black;

    font: 580 10pt "Segoe UI";
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

    font: 580 10pt "Segoe UI";
    border-color: rgba(80, 80, 80, 180);
    height:20px;
    color: #E3E3E3;
    background-color: #1d1d1f;

    border: 2px solid black;
    border-radius: 2px;
    border-color: rgba(80, 80, 80, 255);
        border-bottom: 0px solid black;
}
"""