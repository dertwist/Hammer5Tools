import sys
from typing import List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QScrollArea, QMenu, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPixmap, QUndoCommand, QUndoStack, QKeySequence, QShortcut
from random import random


# -------------------- Undo Command Classes --------------------
class DuplicateCommand(QUndoCommand):
    def __init__(self, window, frames_to_duplicate):
        super().__init__("Duplicate")
        self.window = window
        self.frames_to_duplicate = [f for f in window.frames if f in frames_to_duplicate]
        self.new_frames = []

    def redo(self):
        from src.property.widget import PropertyWidget  # Fix: import here
        for fr in self.frames_to_duplicate:
            new_frame = PropertyWidget(PropertyViewport=self.window)  # Fix: pass correct viewport
            self.window.addFrameSignals(new_frame)
            idx = self.window.framesLayout.indexOf(fr)
            self.window.framesLayout.insertWidget(idx + 1, new_frame)
            self.window.frames.insert(idx + 1, new_frame)
            self.new_frames.append((idx + 1, new_frame))

    def undo(self):
        for idx, new_frame in reversed(self.new_frames):
            self.window.framesLayout.removeWidget(new_frame)
            if new_frame in self.window.frames:
                self.window.frames.remove(new_frame)
            new_frame.deleteLater()
        self.new_frames.clear()

class CutCommand(QUndoCommand):
    def __init__(self, window, frames_to_cut):
        super().__init__("Cut")
        self.window = window
        self.frames_to_cut = [f for f in window.frames if f in frames_to_cut]
        self.cut_indices = []
        self.prev_cut_buffer = window.cut_buffer.copy()

    def redo(self):
        self.window.cut_buffer = self.frames_to_cut.copy()
        self.cut_indices = []
        for fr in self.frames_to_cut:
            idx = self.window.framesLayout.indexOf(fr)
            self.cut_indices.append(idx)
            self.window.framesLayout.removeWidget(fr)
            if fr in self.window.frames:
                self.window.frames.remove(fr)
            fr.hide()
            fr.selected = False
            fr.updateStyle()
        self.window.selected_frames = []
        self.window.last_selected_index = None

    def undo(self):
        for idx, fr in sorted(zip(self.cut_indices, self.frames_to_cut)):
            self.window.framesLayout.insertWidget(idx, fr)
            self.window.frames.insert(idx, fr)
            fr.show()
        self.window.cut_buffer = self.prev_cut_buffer.copy()

class PasteCommand(QUndoCommand):
    def __init__(self, window, buffer, target):
        super().__init__("Paste")
        self.window = window
        self.buffer = buffer.copy()  # can be cut_buffer or copy_buffer
        self.target = target
        self.insert_index = None
        self.pasted_frames = []

    def redo(self):
        from src.property.widget import PropertyWidget
        # Determine insert index
        if self.target is None:
            self.insert_index = self.window.framesLayout.count() - 1  # before spacer
        else:
            self.insert_index = self.window.framesLayout.indexOf(self.target) + 1

        self.pasted_frames.clear()
        # If buffer is from cut_buffer, move the original widgets
        if self.buffer and all(f in self.window.cut_buffer for f in self.buffer):
            for offset, fr in enumerate(self.buffer):
                fr.show()
                self.window.framesLayout.insertWidget(self.insert_index + offset, fr)
                self.window.frames.insert(self.insert_index + offset, fr)
                self.pasted_frames.append(fr)
            self.window.cut_buffer = []
        else:
            # Otherwise, treat as copy_buffer: create new widgets
            for offset, fr in enumerate(self.buffer):
                new_frame = PropertyWidget(PropertyViewport=self.window)
                self.window.addFrameSignals(new_frame)
                self.window.framesLayout.insertWidget(self.insert_index + offset, new_frame)
                self.window.frames.insert(self.insert_index + offset, new_frame)
                self.pasted_frames.append(new_frame)
        # Update selection
        self.window.selected_frames = list(self.pasted_frames)
        self.window.last_selected_index = None

    def undo(self):
        for fr in self.pasted_frames:
            self.window.framesLayout.removeWidget(fr)
            if fr in self.window.frames:
                self.window.frames.remove(fr)
            fr.hide()
        # If these were cut frames, restore them to cut_buffer
        if self.buffer and all(f in self.window.cut_buffer + self.pasted_frames for f in self.buffer):
            self.window.cut_buffer = self.pasted_frames.copy()
        self.window.selected_frames = []
        self.window.last_selected_index = None

class RemoveCommand(QUndoCommand):
    def __init__(self, window, frames_to_remove):
        super().__init__("Remove")
        self.window = window
        self.frames_to_remove = [f for f in window.frames if f in frames_to_remove]
        self.remove_indices = []

    def redo(self):
        self.remove_indices = []
        for fr in self.frames_to_remove:
            idx = self.window.framesLayout.indexOf(fr)
            self.remove_indices.append(idx)
            self.window.framesLayout.removeWidget(fr)
            if fr in self.window.frames:
                self.window.frames.remove(fr)
            fr.hide()
            fr.selected = False
            fr.updateStyle()
        self.window.selected_frames = []
        self.window.last_selected_index = None

    def undo(self):
        # Sort by index to avoid comparing PropertyWidget instances
        for idx, fr in sorted(zip(self.remove_indices, self.frames_to_remove), key=lambda x: x[0]):
            self.window.framesLayout.insertWidget(idx, fr)
            self.window.frames.insert(idx, fr)
            fr.show()

class CopyCommand(QUndoCommand):
    def __init__(self, window, frames_to_copy):
        super().__init__("Copy")
        self.window = window
        self.frames_to_copy = [f for f in window.frames if f in frames_to_copy]
        self.copied_frames = []

    def redo(self):
        # Copy frames (deep copy is not implemented, just reference for now)
        self.window.copy_buffer = self.frames_to_copy.copy()
        self.copied_frames = self.frames_to_copy.copy()

    def undo(self):
        self.window.copy_buffer = []

class AddCommand(QUndoCommand):
    def __init__(self, window, insert_index=None):
        super().__init__("Add")
        self.window = window
        self.insert_index = insert_index
        self.new_frame = None

    def redo(self):
        from src.property.widget import PropertyWidget
        self.new_frame = PropertyWidget(PropertyViewport=self.window.__class__)
        self.window.addFrameSignals(self.new_frame)
        idx = self.insert_index
        if idx is None or idx > self.window.framesLayout.count() - 1:
            idx = self.window.framesLayout.count() - 1
        self.window.framesLayout.insertWidget(idx, self.new_frame)
        self.window.frames.insert(idx, self.new_frame)

    def undo(self):
        if self.new_frame:
            self.window.framesLayout.removeWidget(self.new_frame)
            if self.new_frame in self.window.frames:
                self.window.frames.remove(self.new_frame)
            self.new_frame.deleteLater()