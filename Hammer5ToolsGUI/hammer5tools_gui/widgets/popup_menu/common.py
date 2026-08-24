def _bookmark_bottom_style():
    """
    Special style for the last bookmarked item.
    """
    return """
        QLabel {
            font: 580 10pt "Segoe UI";
            border-bottom: 0px solid black;
            border-radius: 0px;
            border-color: rgba(57, 57, 57, 255);
            padding-top: 8px;
            padding-bottom: 8px;
        }
        QLabel:hover {
            background-color: #515965;
        }
        QLabel[selected="true"] {
            background-color: #3b3f48;
        }
    """

def _label_stylesheet():
    return """
        QLabel {
            font: 580 10pt "Segoe UI";
            border-bottom: 0.5px solid black;
            border-radius: 0px;
            border-color: rgba(57, 57, 57, 255);
            padding-top: 8px;
            padding-bottom: 8px;
        }
        QLabel:hover {
            background-color: #515965;
        }
        QLabel[selected="true"] {
            background-color: #3b3f48;
        }
    """