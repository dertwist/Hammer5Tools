"""
PropertyDataWorker: runs non-UI property data preparation on a QThreadPool worker.
Emits finished(dict) on the main thread when complete; emits error(str) on failure.

BatchPropertyDataWorker: processes many modifier dicts in one runnable (one signal back).

Thread safety:
  - Requires ElementIDGenerator._lock (RLock) to be present.
Widget construction must NEVER happen inside run() — only on the main thread.
"""

from __future__ import annotations

import ast
import threading
from typing import Any

from PySide6.QtCore import QRunnable, QObject, Signal, Slot


def process_property_raw_value(
    raw_value: Any,
    element_id_generator,
    prop_classes_map_cache: dict,
    ordered_pairs_cache: dict,
) -> dict:
    """
    Pure CPU work for one property payload. Returns the same dict shape as
    PropertyDataWorker's finished payload. Raises on parse / data errors.
    """
    value = raw_value
    if not isinstance(value, dict):
        value = ast.literal_eval(value)
    else:
        value = dict(value)

    name_prefix, name = value["_class"].split("_", 1)
    del value["_class"]

    normalized = {"m_bEnabled": True}
    normalized.update(value)

    element_id_generator.update_value(normalized)
    element_id = element_id_generator.get_key(normalized)

    prop_class = name

    skeleton = ordered_pairs_cache.get(prop_class)
    if skeleton is not None:
        ordered_pairs = [(k, normalized.get(k)) for k, _ in skeleton]
    elif prop_class in prop_classes_map_cache:
        classes = prop_classes_map_cache[prop_class]
        ordered_pairs = [
            (item, normalized.get(item)) for item in reversed(classes)
        ]
    else:
        ordered_pairs = list(reversed(list(normalized.items())))

    return {
        "value": normalized,
        "name_prefix": name_prefix,
        "name": name,
        "element_id": element_id,
        "prop_class": prop_class,
        "ordered_pairs": ordered_pairs,
    }


class PropertyDataSignals(QObject):
    """Signals for PropertyDataWorker. Must be a QObject to use Qt signals."""

    finished = Signal(dict)
    error = Signal(str)


class PropertyDataWorker(QRunnable):
    """
    Prepares property frame data off the main thread.

    Output dict (emitted via signals.finished):
        value, name_prefix, name, element_id, prop_class, ordered_pairs
    """

    def __init__(
        self,
        raw_value,
        element_id_generator,
        prop_classes_map_cache,
        only_variable_properties,
        ordered_pairs_cache=None,
    ):
        super().__init__()
        self.raw_value = raw_value
        self.element_id_generator = element_id_generator
        self.prop_classes_map_cache = prop_classes_map_cache
        self.only_variable_properties = only_variable_properties
        self.ordered_pairs_cache = ordered_pairs_cache or {}
        self.signals = PropertyDataSignals()
        self.setAutoDelete(True)
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    @Slot()
    def run(self):
        if self._cancelled.is_set():
            return
        try:
            with self.element_id_generator._lock:
                prepared = process_property_raw_value(
                    self.raw_value,
                    self.element_id_generator,
                    self.prop_classes_map_cache,
                    self.ordered_pairs_cache,
                )
            if self._cancelled.is_set():
                return
            self.signals.finished.emit(prepared)
        except Exception as e:
            if not self._cancelled.is_set():
                self.signals.error.emit(str(e))


class BatchPropertyDataSignals(QObject):
    finished = Signal(list)
    error = Signal(str)


class BatchPropertyDataWorker(QRunnable):
    """
    Processes a list of raw modifier dicts in one pool job.
    Emits finished(list[dict]) in the same order as raw_values.
    """

    def __init__(
        self,
        raw_values: list,
        element_id_generator,
        prop_classes_map_cache: dict,
        ordered_pairs_cache: dict,
    ):
        super().__init__()
        self.raw_values = raw_values
        self.element_id_generator = element_id_generator
        self.prop_classes_map_cache = prop_classes_map_cache
        self.ordered_pairs_cache = ordered_pairs_cache or {}
        self.signals = BatchPropertyDataSignals()
        self.setAutoDelete(True)
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    @Slot()
    def run(self):
        if self._cancelled.is_set():
            return
        results: list[dict] = []
        try:
            for raw_value in self.raw_values:
                if self._cancelled.is_set():
                    return
                with self.element_id_generator._lock:
                    prepared = process_property_raw_value(
                        raw_value,
                        self.element_id_generator,
                        self.prop_classes_map_cache,
                        self.ordered_pairs_cache,
                    )
                results.append(prepared)
            if not self._cancelled.is_set():
                self.signals.finished.emit(results)
        except Exception as e:
            if not self._cancelled.is_set():
                self.signals.error.emit(str(e))
