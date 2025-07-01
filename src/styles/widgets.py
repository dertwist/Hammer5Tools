qt_stylesheet_checkbox_showchild = """
QCheckBox::indicator:checked {
    
image: url(://icons/arrow_drop_down.png);
	height:14px;
	width:14px;
}

QCheckBox::indicator:unchecked {
    image: url(://icons/arrow_drop_right.png);
	height:14px;
	width:14px;
}
QCheckBox {
    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 0px;
    border-color: rgba(80, 80, 80, 255);
    height:14px;
    padding-top: 2px;
    padding-bottom:4px;
    color: #E3E3E3;
background-color: #242424;
    padding-left: 4px;
}
QCheckBox:hover {
    background-color: #414956;
    color: white;
}
QCheckBox{
	padding-left:5px;
	border-left: 0px solid black;
border-right: 0px solid black;
border-top: 0px solid black;
}"""