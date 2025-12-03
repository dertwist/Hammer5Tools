"""
Progress tracking for map compilation.
Tracks compilation phases and provides progress updates.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CompilationPhase(Enum):
    """Compilation phases"""
    IDLE = "Idle"
    INITIALIZING = "Initializing"
    LOADING_MAP = "Loading Map"
    PARSING_ENTITIES = "Parsing Entities"
    BUILDING_WORLD = "Building World"
    BUILDING_PHYSICS = "Building Physics"
    BUILDING_VISIBILITY = "Building Visibility"
    BUILDING_NAVIGATION = "Building Navigation"
    BAKING_LIGHTING = "Baking Lighting"
    BUILDING_AUDIO = "Building Audio"
    FINALIZING = "Finalizing"
    COMPLETE = "Complete"
    FAILED = "Failed"


@dataclass
class ProgressUpdate:
    """Progress update information"""
    phase: CompilationPhase
    phase_progress: float  # 0.0 to 1.0
    global_progress: float  # 0.0 to 1.0
    current_operation: str
    details: Optional[str] = None


class ProgressTracker:
    """Tracks compilation progress"""

    def __init__(self):
        self.current_phase = CompilationPhase.IDLE
        self.phase_progress = 0.0
        self.global_progress = 0.0
        self.current_operation = ""
        self.details = None

    def update(
        self,
        phase: CompilationPhase,
        phase_progress: float,
        global_progress: float,
        operation: str,
        details: Optional[str] = None,
    ) -> ProgressUpdate:
        """Update progress"""
        self.current_phase = phase
        self.phase_progress = max(0.0, min(1.0, phase_progress))
        self.global_progress = max(0.0, min(1.0, global_progress))
        self.current_operation = operation
        self.details = details

        return ProgressUpdate(
            phase=phase,
            phase_progress=self.phase_progress,
            global_progress=self.global_progress,
            current_operation=operation,
            details=details,
        )

    def get_phase_name(self) -> str:
        """Get current phase name"""
        return self.current_phase.value

    def get_progress_percentage(self) -> tuple:
        """Get progress as percentages"""
        return (
            int(self.phase_progress * 100),
            int(self.global_progress * 100),
        )

    def reset(self):
        """Reset tracker"""
        self.current_phase = CompilationPhase.IDLE
        self.phase_progress = 0.0
        self.global_progress = 0.0
        self.current_operation = ""
        self.details = None
