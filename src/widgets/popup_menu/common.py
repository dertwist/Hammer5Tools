def _bookmark_bottom_style():
    """
    Special style for the last bookmarked item.
    """
    return """
        QLabel {
            font: 580 10pt "Segoe UI";
            border-bottom: 0px solid black;
            border-radius: 0px;
            border-color: rgba(40, 40, 40, 255);
            padding-top: 8px;
            padding-bottom: 8px;
        }
        QLabel:hover {
            background-color: #414956;
        }
        QLabel[selected="true"] {
            background-color: #2A2E38;
        }
    """

def _label_stylesheet():
    return """
        QLabel {
            font: 580 10pt "Segoe UI";
            border-bottom: 0.5px solid black;
            border-radius: 0px;
            border-color: rgba(40, 40, 40, 255);
            padding-top: 8px;
            padding-bottom: 8px;
        }
        QLabel:hover {
            background-color: #414956;
        }
        QLabel[selected="true"] {
            background-color: #2A2E38;
        }
    """