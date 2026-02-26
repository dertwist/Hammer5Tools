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
    height:14px;
    width:8x;
    color: #E3E3E3;
}
QCheckBox:hover {
    color: white;
    background-color: #414956;
}"""