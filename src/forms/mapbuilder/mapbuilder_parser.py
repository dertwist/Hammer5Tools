"""
Parser for map builder output.
Extracts compilation information, warnings, and errors.
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class MessageSeverity(Enum):
    """Message severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class CompilationMessage:
    """Compilation message"""
    severity: MessageSeverity
    message: str
    line_number: Optional[int] = None
    file_path: Optional[str] = None


class MapBuilderParser:
    """Parses map builder output"""

    # Regex patterns for different message types
    ERROR_PATTERNS = [
        r"(?i)error[:\s]+(.+)",
        r"(?i)fatal[:\s]+(.+)",
        r"(?i)failed[:\s]+(.+)",
        r"(?i)exception[:\s]+(.+)",
    ]

    WARNING_PATTERNS = [
        r"(?i)warning[:\s]+(.+)",
        r"(?i)warn[:\s]+(.+)",
    ]

    SUCCESS_PATTERNS = [
        r"(?i)success",
        r"(?i)completed successfully",
        r"(?i)finished",
    ]

    PHASE_PATTERNS = {
        "Loading": r"(?i)loading|reading",
        "Parsing": r"(?i)parsing|analyzing",
        "Building": r"(?i)building|compiling|processing",
        "Baking": r"(?i)baking|rendering",
        "Finalizing": r"(?i)finalizing|writing|saving",
    }

    def __init__(self):
        self.messages: List[CompilationMessage] = []
        self.current_phase = "Initializing"

    def parse_line(self, line: str) -> Optional[CompilationMessage]:
        """Parse a single line of output"""
        if not line.strip():
            return None

        # Check for errors
        for pattern in self.ERROR_PATTERNS:
            match = re.search(pattern, line)
            if match:
                message = CompilationMessage(
                    severity=MessageSeverity.ERROR,
                    message=line.strip(),
                )
                self.messages.append(message)
                return message

        # Check for warnings
        for pattern in self.WARNING_PATTERNS:
            match = re.search(pattern, line)
            if match:
                message = CompilationMessage(
                    severity=MessageSeverity.WARNING,
                    message=line.strip(),
                )
                self.messages.append(message)
                return message

        # Check for success
        for pattern in self.SUCCESS_PATTERNS:
            match = re.search(pattern, line)
            if match:
                message = CompilationMessage(
                    severity=MessageSeverity.SUCCESS,
                    message=line.strip(),
                )
                self.messages.append(message)
                return message

        # Update phase if detected
        for phase_name, pattern in self.PHASE_PATTERNS.items():
            if re.search(pattern, line):
                self.current_phase = phase_name
                break

        return None

    def get_errors(self) -> List[CompilationMessage]:
        """Get all error messages"""
        return [m for m in self.messages if m.severity == MessageSeverity.ERROR]

    def get_warnings(self) -> List[CompilationMessage]:
        """Get all warning messages"""
        return [m for m in self.messages if m.severity == MessageSeverity.WARNING]

    def get_all_messages(self) -> List[CompilationMessage]:
        """Get all messages"""
        return self.messages

    def reset(self):
        """Reset parser"""
        self.messages = []
        self.current_phase = "Initializing"
