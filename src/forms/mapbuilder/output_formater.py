import html


class OutputFormatter:
    """
    Simple output formatter for CS2 resource compiler logs
    Decodes HTML entities while preserving HTML tags
    """

    @staticmethod
    def parse_output_line(line: str) -> str:
        """
        Decode HTML entities (&#39; -> ', &#46; -> ., etc.)
        but preserve HTML tags like <font color> and <br/>
        """
        if not line:
            return ""

        # Decode HTML entities (e.g., &#39; becomes ', &#46; becomes .)
        line = html.unescape(line)

        return line
