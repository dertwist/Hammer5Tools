from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtCore import QRegularExpression

class CustomHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Define the format for the custom text
        custom_format = QTextCharFormat()
        custom_format.setForeground(QColor("#C78662"))

        # Define the format for the new keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#FF5733"))  # Example color, change as needed

        # Define the format for text within quotes
        quoted_text_format = QTextCharFormat()
        quoted_text_format.setForeground(QColor("#6bc7c4"))

        # Define the format for FOLDER_PATH pattern
        folder_path_format = QTextCharFormat()
        folder_path_format.setForeground(QColor("#C78662"))  # Example color, change as needed

        # Define the format for ASSET_NAME pattern
        asset_name_format = QTextCharFormat()
        asset_name_format.setForeground(QColor("#C78662"))  # Example color, change as needed

        # Define the new keyword patterns
        keyword_patterns = [
            r"\bTextureAmbientOcclusion\b",
            r"\bTextureColor1\b",
            r"\bTextureRoughness1\b",
            r"\bTextureMetalness1\b",
            r"\bTextureNormal\b"
        ]

        # Add the keyword patterns and their format to the highlighting rules
        for pattern in keyword_patterns:
            regex = QRegularExpression(pattern)
            self.highlighting_rules.append((regex, keyword_format))

        # Add the pattern for text within quotes
        quoted_text_pattern = QRegularExpression(r'"\s*[^"]+\s*"')
        self.highlighting_rules.append((quoted_text_pattern, quoted_text_format))

        # Define the patterns to be highlighted
        patterns = [
            (r"#\$FOLDER_PATH\$#", folder_path_format),
            (r"#\$ASSET_NAME\$#", asset_name_format)
        ]

        # Add the existing patterns and their format to the highlighting rules
        for pattern, format in patterns:
            regex = QRegularExpression(pattern)
            self.highlighting_rules.append((regex, format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)