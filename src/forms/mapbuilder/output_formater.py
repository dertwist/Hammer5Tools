import re
import html
from typing import Tuple
from enum import Enum


class OutputFormatter:
    """
    Enhanced output formatter for CS2 resource compiler logs
    Handles mixed plain text, HTML tags, HTML entities, and color codes
    Designed for QTextEdit display with HTML support
    """

    # Enhanced color palette for better visibility
    COLOR_MAP = {
        "error": "#FF5555",      # Bright red
        "warning": "#FFD700",    # Gold/yellow
        "success": "#50FA7B",    # Bright green
        "info": "#8BE9FD",       # Cyan
        "path": "#F8F8F2",       # Off-white (file paths)
        "progress": "#BD93F9",   # Purple
        "time": "#6272A4",       # Gray-blue
        "timestamp": "#FFB86C",  # Orange
        "normal": "#F8F8F2",     # Default text
    }

    @staticmethod
    def parse_output_line(line: str) -> str:
        """
        Parse and enhance a single output line
        Handles: HTML tags, HTML entities, color codes, progress indicators, timestamps
        Returns HTML-formatted string ready for QTextEdit
        """
        if not line:
            return ""

        # First, decode HTML entities (e.g., &#39; becomes ')
        line = html.unescape(line)

        # Check if line already contains HTML from compiler (with <br/> or <font> tags)
        if '<br' in line.lower() or '<font' in line.lower():
            return OutputFormatter._process_compiler_html(line)

        # For plain text lines, detect log level and format accordingly
        line_type = OutputFormatter._classify_line(line)

        # Apply appropriate formatting based on type
        if line_type == "error":
            return f'<span style="color:{OutputFormatter.COLOR_MAP["error"]};font-weight:bold;">✗ {html.escape(line)}</span>'
        elif line_type == "warning":
            return f'<span style="color:{OutputFormatter.COLOR_MAP["warning"]};font-weight:500;">⚠ {html.escape(line)}</span>'
        elif line_type == "success":
            return f'<span style="color:{OutputFormatter.COLOR_MAP["success"]};font-weight:bold;">✓ {html.escape(line)}</span>'
        elif line_type == "progress":
            return OutputFormatter._format_progress(line)
        elif line_type == "time":
            return OutputFormatter._format_timing(line)
        elif line_type == "timestamp":
            return OutputFormatter._format_timestamp(line)

        # Check for file paths
        if OutputFormatter._is_file_path(line):
            return OutputFormatter._format_file_path(line)

        return f'<span style="color:{OutputFormatter.COLOR_MAP["normal"]}">{html.escape(line)}</span>'

    @staticmethod
    def _process_compiler_html(line: str) -> str:
        """
        Process lines with existing HTML from the compiler
        These lines contain <br/> tags and <font color> tags that need to be converted
        """
        # Split by <br/> or <br> to process each segment
        segments = re.split(r'<br\s*/?>', line)
        
        processed_segments = []
        for segment in segments:
            if not segment.strip():
                continue
                
            # Process font color tags
            segment = OutputFormatter._convert_font_tags(segment)
            processed_segments.append(segment)
        
        # Join with actual line breaks for QTextEdit
        return '<br/>'.join(processed_segments)

    @staticmethod
    def _convert_font_tags(text: str) -> str:
        """
        Convert <font color="#XXX"> tags to styled spans with appropriate icons
        """
        def replace_font_tag(match):
            color = match.group(1)
            content = match.group(2)
            
            # Add icons based on content
            icon = ""
            weight = "normal"
            
            if 'Failed' in content or 'ERROR' in content:
                icon = "✗ "
                weight = "bold"
            elif 'Missing' in content or 'Bad' in content:
                icon = "⚠ "
                weight = "500"
            elif 'Initialized' in content:
                icon = "✓ "
                weight = "500"
            
            return f'<span style="color:{color};font-weight:{weight};">{icon}{html.escape(content)}</span>'
        
        # Match font tags with color attribute
        text = re.sub(r'<font color="([^"]+)">([^<]*)</font>', replace_font_tag, text)
        
        # If no font tags but text exists, escape and return with default color
        if '<span' not in text and text.strip():
            return f'<span style="color:{OutputFormatter.COLOR_MAP["normal"]}">{html.escape(text)}</span>'
        
        return text

    @staticmethod
    def _classify_line(line: str) -> str:
        """
        Classify line type for appropriate coloring and icons
        """
        line_upper = line.upper()

        # Timestamp pattern (e.g., [12:39:05])
        if re.match(r'^\[\d{2}:\d{2}:\d{2}\]', line):
            return "timestamp"

        if any(keyword in line_upper for keyword in ["ERROR", "FAILED", "FATAL"]):
            return "error"
        elif any(keyword in line_upper for keyword in ["WARNING", "WARN", "MISSING", "BAD"]):
            return "warning"
        elif any(keyword in line_upper for keyword in ["SUCCESS", "COMPLETED SUCCESSFULLY", "✓"]):
            return "success"
        elif re.search(r'\[(\d+)\.+\]', line) or "Done (" in line:
            return "progress"
        elif re.search(r'\d+\.\d+\s*seconds', line, re.IGNORECASE):
            return "time"

        return "info"

    @staticmethod
    def _is_file_path(line: str) -> bool:
        """
        Detect if line contains a file path
        """
        # Look for common path patterns
        patterns = [
            r'\+\-\s+\S+\\',  # +- csgo_addons\...
            r'[A-Z]:\\',  # Windows paths
            r'\w+/\w+',  # Unix-style paths
        ]
        return any(re.search(pattern, line) for pattern in patterns)

    @staticmethod
    def _format_file_path(line: str) -> str:
        """
        Format file path lines with appropriate styling
        """
        # Extract the tree character and file path
        match = re.match(r'(\s*\+\-\s+)(.+)', line)
        if match:
            prefix = match.group(1)
            path = match.group(2)
            return (f'<span style="color:#6272A4">{html.escape(prefix)}</span>'
                   f'<span style="color:{OutputFormatter.COLOR_MAP["path"]};font-weight:500;">{html.escape(path)}</span>')
        
        return f'<span style="color:{OutputFormatter.COLOR_MAP["path"]}">{html.escape(line)}</span>'

    @staticmethod
    def _format_timestamp(line: str) -> str:
        """
        Format timestamp lines (e.g., [12:39:05] message)
        """
        match = re.match(r'^(\[\d{2}:\d{2}:\d{2}\])\s*(.*)$', line)
        if match:
            timestamp = match.group(1)
            message = match.group(2)
            
            # Classify the message part
            icon = ""
            color = OutputFormatter.COLOR_MAP["normal"]
            weight = "normal"
            
            if "✓" in message or "Compilation completed successfully" in message:
                icon = "✓ "
                color = OutputFormatter.COLOR_MAP["success"]
                weight = "bold"
            elif "Starting" in message:
                icon = "▶ "
                color = OutputFormatter.COLOR_MAP["info"]
                weight = "500"
            
            return (f'<span style="color:{OutputFormatter.COLOR_MAP["timestamp"]};font-weight:bold;">{html.escape(timestamp)}</span> '
                   f'<span style="color:{color};font-weight:{weight};">{icon}{html.escape(message)}</span>')
        
        return html.escape(line)

    @staticmethod
    def _format_progress(line: str) -> str:
        """
        Format progress indicators with visual styling
        """
        # Highlight progress bars [0....1....2....3....4....5....6....7....8....9....]
        progress_match = re.search(r'\[(\d+)\.+([\d\.]*)]', line)
        if progress_match:
            before = line[:progress_match.start()]
            progress_bar = progress_match.group(0)
            after = line[progress_match.end():]

            return (f'<span style="color:{OutputFormatter.COLOR_MAP["normal"]}">{html.escape(before)}</span>'
                   f'<span style="background-color:#44475A;color:{OutputFormatter.COLOR_MAP["progress"]};'
                   f'padding:2px 6px;border-radius:3px;font-family:monospace;font-weight:bold;">{html.escape(progress_bar)}</span>'
                   f'<span style="color:{OutputFormatter.COLOR_MAP["normal"]}">{html.escape(after)}</span>')

        # Handle "Done (X.XX seconds)" format
        if "Done (" in line:
            done_match = re.search(r'(Done \()([^)]+)(\))', line)
            if done_match:
                before = line[:done_match.start()]
                after = line[done_match.end():]
                timing = done_match.group(2)
                
                return (f'<span style="color:{OutputFormatter.COLOR_MAP["normal"]}">{html.escape(before)}</span>'
                       f'<span style="color:#50FA7B;font-weight:bold;">Done</span> '
                       f'<span style="color:#6272A4">(</span>'
                       f'<span style="color:#FFB86C;font-weight:bold;">{html.escape(timing)}</span>'
                       f'<span style="color:#6272A4">)</span>'
                       f'<span style="color:{OutputFormatter.COLOR_MAP["normal"]}">{html.escape(after)}</span>')

        return f'<span style="color:{OutputFormatter.COLOR_MAP["normal"]}">{html.escape(line)}</span>'

    @staticmethod
    def _format_timing(line: str) -> str:
        """
        Format timing information with emphasis
        """
        # Find timing patterns like "Done (12.34 seconds)"
        timing_pattern = r'(\d+\.?\d*)\s*seconds?'
        match = re.search(timing_pattern, line, re.IGNORECASE)

        if match:
            timing_value = match.group(1)
            before = line[:match.start()]
            after = line[match.end():]

            return (f'<span style="color:{OutputFormatter.COLOR_MAP["normal"]}">{html.escape(before)}</span>'
                   f'<span style="color:{OutputFormatter.COLOR_MAP["time"]};font-weight:bold;">{timing_value} seconds</span>'
                   f'<span style="color:{OutputFormatter.COLOR_MAP["normal"]}">{html.escape(after)}</span>')

        return f'<span style="color:{OutputFormatter.COLOR_MAP["normal"]}">{html.escape(line)}</span>'

    @staticmethod
    def sanitize_html(html_content: str) -> str:
        """
        Sanitize HTML to prevent injection and fix common issues
        """
        # Remove potentially dangerous tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<iframe[^>]*>.*?</iframe>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'on\w+="[^"]*"', '', html_content)  # Remove event handlers

        return html_content

    @staticmethod
    def format_summary_line(compiled: int, failed: int, skipped: int, time_str: str) -> str:
        """
        Format the compilation summary line with enhanced styling
        """
        parts = []
        
        if compiled > 0:
            parts.append(f'<span style="color:#50FA7B;font-weight:bold;">✓ {compiled} compiled</span>')
        
        if failed > 0:
            parts.append(f'<span style="color:#FF5555;font-weight:bold;">✗ {failed} failed</span>')
        
        if skipped > 0:
            parts.append(f'<span style="color:#FFB86C;font-weight:500;">{skipped} skipped</span>')
        
        parts.append(f'<span style="color:#6272A4;font-weight:bold;">{time_str}</span>')
        
        return ' | '.join(parts)
