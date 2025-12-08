import re
import html


class OutputFormatter:
    """
    Simple output formatter for CS2 resource compiler logs
    Passes through HTML output from resourcecompiler without modification
    """

    @staticmethod
    def parse_output_line(line: str) -> str:
        """
        Parse output line - decode HTML entities and pass through
        """
        if not line:
            return ""

        # Decode HTML entities (e.g., &#39; becomes ', &#46; becomes .)
        line = html.unescape(line)
        
        return line

    @staticmethod
    def sanitize_html(html_content: str) -> str:
        """
        Sanitize HTML to prevent injection
        """
        # Remove potentially dangerous tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'on\w+="[^"]*"', '', html_content)  # Remove event handlers

        return html_content
