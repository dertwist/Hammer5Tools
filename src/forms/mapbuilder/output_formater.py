import re
import html
from typing import Tuple
from enum import Enum


class OutputFormatter:
    """
    Enhanced output formatter for CS2 resource compiler logs
    Handles mixed plain text, HTML tags, and color codes
    """

    # Color palette for common log messages
    COLOR_MAP = {
        "error": "#FF5A5A",  # Red
        "warning": "#FFFF5A",  # Yellow
        "success": "#5AFF5A",  # Green
        "info": "#5AABFF",  # Blue
        "path": "#FFFFFF",  # White (file paths)
        "progress": "#00FFFF",  # Cyan
        "time": "#B8B8B8",  # Gray
    }

    @staticmethod
    def parse_output_line(line: str) -> str:
        """
        Parse and enhance a single output line
        Handles: HTML tags, color codes, progress indicators, timestamps
        """
        if not line:
            return ""

        # Already contains HTML tags - clean and enhance
        if "<" in line and ">" in line:
            return OutputFormatter._enhance_html(line)

        # Detect log level from content
        line_type = OutputFormatter._classify_line(line)

        # Apply appropriate formatting based on type
        if line_type == "error":
            return f'<span style="color:{OutputFormatter.COLOR_MAP["error"]}"><strong> {html.escape(line)}</strong></span>'
        elif line_type == "warning":
            return f'<span style="color:{OutputFormatter.COLOR_MAP["warning"]}">{html.escape(line)}</span>'
        elif line_type == "success":
            return f'<span style="color:{OutputFormatter.COLOR_MAP["success"]}"><strong>{html.escape(line)}</strong></span>'
        elif line_type == "progress":
            return OutputFormatter._format_progress(line)
        elif line_type == "time":
            return OutputFormatter._format_timing(line)

        return html.escape(line)

    @staticmethod
    def _enhance_html(line: str) -> str:
        """Enhance and clean existing HTML tags"""
        # Fix common issues
        line = line.replace("<br/>", "<br />")
        line = line.replace("<br>", "<br />")

        # Ensure font tags are properly formatted
        line = re.sub(r'<font\s+color="([^"]+)">([^<]*)</font>',
                      r'<span style="color:\1">\2</span>', line)

        # Add line height for better spacing
        return f'<div style="line-height: 1.4; font-family: monospace;">{line}</div>'

    @staticmethod
    def _classify_line(line: str) -> str:
        """Classify line type for appropriate coloring"""
        line_upper = line.upper()

        if any(keyword in line_upper for keyword in ["ERROR", "FAILED", "FATAL"]):
            return "error"
        elif any(keyword in line_upper for keyword in ["WARNING", "WARN"]):
            return "warning"
        elif any(keyword in line_upper for keyword in ["SUCCESS", "COMPLETE", "DONE"]):
            return "success"
        elif re.search(r'\[(\d+)\.+\]', line) or "Done (" in line:
            return "progress"
        elif re.search(r'\d+\.\d+\s*seconds', line, re.IGNORECASE):
            return "time"

        return "info"

    @staticmethod
    def _format_progress(line: str) -> str:
        """Format progress indicators with visual styling"""
        # Highlight progress bars
        progress_match = re.search(r'\[(\d+)\.+(\d*)\]', line)
        if progress_match:
            before = line[:progress_match.start()]
            progress_bar = progress_match.group(0)
            after = line[progress_match.end():]

            return (f'{html.escape(before)}'
                    f'<span style="background-color: #333333; color: {OutputFormatter.COLOR_MAP["progress"]}; '
                    f'padding: 2px 4px; border-radius: 3px; font-family: monospace;">{progress_bar}</span>'
                    f'{html.escape(after)}')

        return html.escape(line)

    @staticmethod
    def _format_timing(line: str) -> str:
        """Format timing information with emphasis"""
        # Find timing patterns like "Done (12.34 seconds)"
        timing_pattern = r'(\d+\.?\d*)\s*seconds'
        match = re.search(timing_pattern, line, re.IGNORECASE)

        if match:
            timing_value = match.group(1)
            before = line[:match.start()]
            after = line[match.end():]

            return (f'{html.escape(before)}'
                    f'<span style="color: {OutputFormatter.COLOR_MAP["time"]}; '
                    f'font-weight: bold;">{timing_value} seconds</span>'
                    f'{html.escape(after)}')

        return html.escape(line)

    @staticmethod
    def sanitize_html(html_content: str) -> str:
        """Sanitize HTML to prevent injection and fix common issues"""
        # Remove potentially dangerous tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html_content, flags=re.DOTALL)

        return html_content
