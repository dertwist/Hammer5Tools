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