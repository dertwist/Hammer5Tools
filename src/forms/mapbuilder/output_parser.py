"""
Real-time console output parser for resourcecompiler.exe.
Extracts compilation phases, progress, warnings, and errors.
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum


class CompilationPhase(Enum):
    """Compilation phases detected from output"""
    STARTING = "Starting"
    UNPACKING = "Unpacking VPK"
    BUILDING_WORLD = "Building World"
    BUILDING_VIS = "Building Visibility"
    BUILDING_RAY_TRACE = "Building Ray Trace"
    BUILDING_LIGHTMAPS = "Baking Lightmaps"
    PROCESSING_LIGHTING = "Processing Lighting"
    BUILDING_PHYSICS = "Building Physics"
    BUILDING_NAV = "Building Navigation"
    BUILDING_AUDIO = "Building Audio"
    FINALIZING = "Finalizing"
    COMPLETED = "Completed"
    ERROR = "Error"


@dataclass
class CompilationMessage:
    """A message from the compilation process"""
    severity: str  # "info", "warning", "error"
    phase: CompilationPhase
    message: str
    timestamp: Optional[float] = None
    line_number: Optional[int] = None


@dataclass
class CompilationProgress:
    """Current compilation progress"""
    phase: CompilationPhase
    phase_progress: float  # 0.0 to 1.0
    global_progress: float  # 0.0 to 1.0
    estimated_remaining: Optional[float] = None  # seconds
    current_phase_name: str = ""
    current_operation: str = ""


class OutputParser:
    """Parses resourcecompiler.exe output in real-time"""

    # Phase detection patterns
    PHASE_PATTERNS = {
        CompilationPhase.UNPACKING: [
            r"Unzip.*\.vpk",
            r"unpacking.*files",
        ],
        CompilationPhase.BUILDING_WORLD: [
            r"Building world",
            r"Compiling.*\.vmap",
            r"Done \(\d+\.\d+ seconds\)",
        ],
        CompilationPhase.BUILDING_RAY_TRACE: [
            r"Building ray trace environment",
            r"Convert RTE with.*triangles",
            r"Successfully.*ray tracing environment",
        ],
        CompilationPhase.BUILDING_VIS: [
            r"Built.*clusters",
            r"Merge vis clusters",
            r"Merged to.*clusters",
            r"Compute enclosed cluster",
            r"Raytraced sun visibility",
        ],
        CompilationPhase.BUILDING_LIGHTMAPS: [
            r"Pass \d+ of \d+",
            r"Done \(\d+\.\d+ seconds\)",
            r"ProcessReceivedLightingPackets",
            r"DilateToGutters",
        ],
        CompilationPhase.BUILDING_PHYSICS: [
            r"Building physics",
            r"Compiling.*collision",
        ],
        CompilationPhase.BUILDING_NAV: [
            r"Building navigation",
            r"Generating nav mesh",
        ],
        CompilationPhase.BUILDING_AUDIO: [
            r"-sareverb",
            r"-sapaths",
            r"-sacustomdata",
        ],
        CompilationPhase.FINALIZING: [
            r"Exiting \(code \d+\)",
            r"Compilation complete",
        ],
    }

    # Progress extraction patterns
    PROGRESS_PATTERNS = {
        "percentage": r"(\d+)%",
        "pass_progress": r"Pass (\d+) of (\d+)",
        "cluster_progress": r"Merge vis clusters:(\d+)\.+(\d+)",
        "time_elapsed": r"\((\d+\.\d+) seconds\)",
    }

    # Warning/Error patterns
    WARNING_PATTERN = r"(?i)(warning|note):\s*(.+)"
    ERROR_PATTERN = r"(?i)(error|exception|failed|violation):\s*(.+)"

    def __init__(self):
        self.current_phase = CompilationPhase.STARTING
        self.messages: List[CompilationMessage] = []
        self.phase_start_times = {}
        self.total_lines_processed = 0

        # Phase weights for global progress estimation
        self.phase_weights = {
            CompilationPhase.STARTING: 0.01,
            CompilationPhase.UNPACKING: 0.02,
            CompilationPhase.BUILDING_WORLD: 0.10,
            CompilationPhase.BUILDING_RAY_TRACE: 0.05,
            CompilationPhase.BUILDING_VIS: 0.20,
            CompilationPhase.BUILDING_LIGHTMAPS: 0.50,
            CompilationPhase.PROCESSING_LIGHTING: 0.05,
            CompilationPhase.BUILDING_PHYSICS: 0.03,
            CompilationPhase.BUILDING_NAV: 0.02,
            CompilationPhase.BUILDING_AUDIO: 0.01,
            CompilationPhase.FINALIZING: 0.01,
        }

        self.phase_progress = 0.0
        self.global_progress = 0.0

    def parse_line(self, line: str) -> Tuple[Optional[CompilationMessage], Optional[CompilationProgress]]:
        """
        Parse a single line of output.
        Returns (message, progress) tuple where either can be None.
        """
        self.total_lines_processed += 1

        # Detect phase change
        new_phase = self._detect_phase(line)
        if new_phase and new_phase != self.current_phase:
            self.current_phase = new_phase
            self.phase_progress = 0.0

        # Extract progress
        progress = self._extract_progress(line)

        # Detect warnings/errors
        message = self._detect_message(line)

        return message, progress

    def _detect_phase(self, line: str) -> Optional[CompilationPhase]:
        """Detect which compilation phase this line belongs to"""
        for phase, patterns in self.PHASE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return phase
        return None

    def _extract_progress(self, line: str) -> Optional[CompilationProgress]:
        """Extract progress information from line"""

        # Check for pass progress (e.g., "Pass 5 of 9")
        pass_match = re.search(self.PROGRESS_PATTERNS["pass_progress"], line)
        if pass_match:
            current = int(pass_match.group(1))
            total = int(pass_match.group(2))
            self.phase_progress = current / total
            self.global_progress = self._calculate_global_progress()

            return CompilationProgress(
                phase=self.current_phase,
                phase_progress=self.phase_progress,
                global_progress=self.global_progress,
                current_phase_name=self.current_phase.value,
                current_operation=f"Pass {current} of {total}"
            )

        # Check for percentage
        pct_match = re.search(self.PROGRESS_PATTERNS["percentage"], line)
        if pct_match:
            pct = int(pct_match.group(1))
            self.phase_progress = pct / 100.0
            self.global_progress = self._calculate_global_progress()

            return CompilationProgress(
                phase=self.current_phase,
                phase_progress=self.phase_progress,
                global_progress=self.global_progress,
                current_phase_name=self.current_phase.value,
                current_operation=line.strip()[:50]
            )

        # Check for cluster merge progress
        cluster_match = re.search(self.PROGRESS_PATTERNS["cluster_progress"], line)
        if cluster_match:
            # Progress indicated by dots (0...10 means 0-100%)
            progress_str = line[line.find(':') + 1:line.find('...')]
            # Rough estimation
            self.phase_progress = min(0.9, self.phase_progress + 0.1)
            self.global_progress = self._calculate_global_progress()

            return CompilationProgress(
                phase=self.current_phase,
                phase_progress=self.phase_progress,
                global_progress=self.global_progress,
                current_phase_name=self.current_phase.value,
                current_operation="Merging visibility clusters"
            )

        return None

    def _detect_message(self, line: str) -> Optional[CompilationMessage]:
        """Detect warnings and errors"""

        # Check for errors
        error_match = re.search(self.ERROR_PATTERN, line)
        if error_match:
            return CompilationMessage(
                severity="error",
                phase=self.current_phase,
                message=error_match.group(2).strip()
            )

        # Check for warnings
        warning_match = re.search(self.WARNING_PATTERN, line)
        if warning_match:
            return CompilationMessage(
                severity="warning",
                phase=self.current_phase,
                message=warning_match.group(2).strip()
            )

        return None

    def _calculate_global_progress(self) -> float:
        """Calculate overall compilation progress"""
        completed_weight = 0.0

        # Sum weights of completed phases
        for phase, weight in self.phase_weights.items():
            if phase.value < self.current_phase.value:
                completed_weight += weight

        # Add current phase progress
        current_weight = self.phase_weights.get(self.current_phase, 0.0)
        completed_weight += current_weight * self.phase_progress

        return min(1.0, completed_weight)

    def reset(self):
        """Reset parser state for new compilation"""
        self.current_phase = CompilationPhase.STARTING
        self.messages.clear()
        self.phase_start_times.clear()
        self.total_lines_processed = 0
        self.phase_progress = 0.0
        self.global_progress = 0.0