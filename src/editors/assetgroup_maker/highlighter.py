from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtCore import QRegularExpression

class CustomHighlighter(QSyntaxHighlighter):
    """
    A custom syntax highlighter for highlighting specific patterns in text.

    Attributes:
        highlighting_rules (list): A list of tuples containing regex patterns and their corresponding text formats.
    """

    def __init__(self, parent=None) -> None:
        """
        Initialize the CustomHighlighter with specific highlighting rules.

        Args:
            parent: The parent widget for the highlighter.
        """
        super().__init__(parent)
        self.highlighting_rules = []

        # Define text formats
        custom_format = QTextCharFormat()
        custom_format.setForeground(QColor("#C78662"))

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#FF5733"))

        quoted_text_format = QTextCharFormat()
        quoted_text_format.setForeground(QColor("#6bc7c4"))

        folder_path_format = QTextCharFormat()
        folder_path_format.setForeground(QColor("#C78662"))

        asset_name_format = QTextCharFormat()
        asset_name_format.setForeground(QColor("#C78662"))

        # Define keyword patterns
        keyword_patterns = [
            r"\bTextureAmbientOcclusion\b",
            r"\bTextureColor1\b",
            r"\bTextureRoughness1\b",
            r"\bTextureMetalness1\b",
            r"\bTextureNormal\b"
        ]

        for pattern in keyword_patterns:
            regex = QRegularExpression(pattern)
            self.highlighting_rules.append((regex, keyword_format))

        # Define quoted text pattern
        quoted_text_pattern = QRegularExpression(r'"\s*[^"]+\s*"')
        self.highlighting_rules.append((quoted_text_pattern, quoted_text_format))

        # Define other patterns
        patterns = [
            (r"#\$FOLDER_PATH\$#", folder_path_format),
            (r"#\$ASSET_NAME\$#", asset_name_format)
        ]

        for pattern, format in patterns:
            regex = QRegularExpression(pattern)
            self.highlighting_rules.append((regex, format))

    def highlightBlock(self, text: str) -> None:
        """
        Apply syntax highlighting to a block of text.

        Args:
            text: The text block to be highlighted.
        """
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)