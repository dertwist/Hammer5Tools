"""
Integration layer for map builder components.
Coordinates progress tracking, parsing, and UI updates.
"""
from typing import Callable, Optional
from PySide6.QtWidgets import QListWidgetItem, QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon

from .progress_tracker import ProgressTracker, CompilationPhase, ProgressUpdate
from .mapbuilder_parser import MapBuilderParser, MessageSeverity


class MapBuilderIntegration:
    """Integrates progress tracking and parsing with UI"""

    def __init__(self, report_widget, progress_bars: dict):
        """
        Initialize integration
        
        Args:
            report_widget: QListWidget for displaying messages
            progress_bars: Dict with 'phase' and 'global' QProgressBar references
        """
        self.report_widget = report_widget
        self.progress_bars = progress_bars
        self.tracker = ProgressTracker()
        self.parser = MapBuilderParser()

    def process_output_line(self, line: str) -> Optional[ProgressUpdate]:
        """
        Process a single line of compiler output
        
        Args:
            line: Output line from compiler
            
        Returns:
            ProgressUpdate if progress changed, None otherwise
        """
        # Parse the line for messages
        message = self.parser.parse_line(line)

        # Add message to report if found
        if message:
            self._add_report_item(message.message, message.severity)

        return None

    def update_progress(
        self,
        phase: CompilationPhase,
        phase_progress: float,
        global_progress: float,
        operation: str,
        details: Optional[str] = None,
    ) -> ProgressUpdate:
        """
        Update compilation progress
        
        Args:
            phase: Current compilation phase
            phase_progress: Phase progress (0.0-1.0)
            global_progress: Global progress (0.0-1.0)
            operation: Current operation description
            details: Optional additional details
            
        Returns:
            ProgressUpdate object
        """
        update = self.tracker.update(
            phase=phase,
            phase_progress=phase_progress,
            global_progress=global_progress,
            operation=operation,
            details=details,
        )

        # Update UI progress bars
        self._update_progress_bars(update)

        return update

    def _update_progress_bars(self, update: ProgressUpdate):
        """Update progress bar widgets"""
        if "phase" in self.progress_bars:
            phase_pct = int(update.phase_progress * 100)
            self.progress_bars["phase"].setValue(phase_pct)

        if "global" in self.progress_bars:
            global_pct = int(update.global_progress * 100)
            self.progress_bars["global"].setValue(global_pct)

    def _add_report_item(self, message: str, severity: MessageSeverity):
        """
        Add a message to the report widget with copy button
        
        Args:
            message: Message text
            severity: Message severity level
        """
        # Create container widget for message + copy button
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)

        # Create list item
        item = QListWidgetItem()
        item.setText(message)

        # Set color based on severity
        if severity == MessageSeverity.ERROR:
            item.setForeground(QColor(255, 100, 100))
            item.setIcon(QIcon(":/icons/error_24dp_FF6464_FILL0_wght400_GRAD0_opsz24.svg"))
        elif severity == MessageSeverity.WARNING:
            item.setForeground(QColor(255, 200, 100))
            item.setIcon(QIcon(":/icons/warning_24dp_FFC864_FILL0_wght400_GRAD0_opsz24.svg"))
        elif severity == MessageSeverity.SUCCESS:
            item.setForeground(QColor(100, 200, 100))
            item.setIcon(QIcon(":/icons/check_24dp_64C864_FILL0_wght400_GRAD0_opsz24.svg"))
        else:
            item.setForeground(QColor(200, 200, 200))

        # Add copy button
        copy_button = QPushButton("Copy")
        copy_button.setMaximumWidth(50)
        copy_button.setMaximumHeight(24)
        copy_button.clicked.connect(lambda: self._copy_to_clipboard(message))

        layout.addWidget(copy_button)
        layout.addStretch()

        # Add item to report widget
        self.report_widget.addItem(item)
        self.report_widget.setItemWidget(item, container)

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def get_errors(self) -> list:
        """Get all error messages"""
        return self.parser.get_errors()

    def get_warnings(self) -> list:
        """Get all warning messages"""
        return self.parser.get_warnings()

    def get_current_phase(self) -> str:
        """Get current compilation phase name"""
        return self.tracker.get_phase_name()

    def get_progress_percentages(self) -> tuple:
        """Get progress as (phase_pct, global_pct)"""
        return self.tracker.get_progress_percentage()

    def reset(self):
        """Reset all trackers and parsers"""
        self.tracker.reset()
        self.parser.reset()
