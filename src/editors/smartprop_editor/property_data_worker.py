"""
PropertyDataWorker: runs non-UI property data preparation on a QThreadPool worker.
Emits finished(dict) on the main thread when complete; emits error(str) on failure.

Thread safety:
  - Requires ElementIDGenerator._lock (RLock) to be present.
Widget construction must NEVER happen inside run() — only on the main thread.
"""

import ast
import threading

from PySide6.QtCore import QRunnable, QObject, Signal, Slot


class PropertyDataSignals(QObject):
    """Signals for PropertyDataWorker. Must be a QObject to use Qt signals."""

    finished = Signal(dict)
    error = Signal(str)


class PropertyDataWorker(QRunnable):
    """
    Prepares property frame data off the main thread.

    Output dict (emitted via signals.finished):
        value:         dict  — normalized value dict (without _class key)
        name_prefix:   str
        name:          str
        element_id:    int
        prop_class:    str
        ordered_pairs: list of (value_class, val) tuples in insertion order
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
            # Step 1: parse value
            value = self.raw_value
            if not isinstance(value, dict):
                value = ast.literal_eval(value)
            else:
                value = dict(value)  # shallow copy — do not mutate caller's dict

            # Step 2: extract and remove _class key
            name_prefix, name = value["_class"].split("_", 1)
            del value["_class"]

            normalized = {"m_bEnabled": True}
            normalized.update(value)

            # Step 3: element ID — protected by RLock inside ElementIDGenerator
            self.element_id_generator.update_value(normalized)
            element_id = self.element_id_generator.get_key(normalized)

            prop_class = name

            # Step 4: build ordered_pairs (pure data, no Qt calls)
            skeleton = self.ordered_pairs_cache.get(prop_class)
            if skeleton is not None:
                ordered_pairs = [(k, normalized.get(k)) for k, _ in skeleton]
            elif prop_class in self.prop_classes_map_cache:
                classes = self.prop_classes_map_cache[prop_class]
                ordered_pairs = [
                    (item, normalized.get(item)) for item in reversed(classes)
                ]
            else:
                ordered_pairs = list(reversed(list(normalized.items())))

            if self._cancelled.is_set():
                return

            self.signals.finished.emit(
                {
                    "value": normalized,
                    "name_prefix": name_prefix,
                    "name": name,
                    "element_id": element_id,
                    "prop_class": prop_class,
                    "ordered_pairs": ordered_pairs,
                }
            )

        except Exception as e:
            if not self._cancelled.is_set():
                self.signals.error.emit(str(e))
