"""
Fast deep-copy for JSON-safe nested dicts/lists via orjson round-trip.

orjson (Rust extension) is 3-10x faster than copy.deepcopy for the
JSON-compatible data structures used throughout the SmartProp editor
(str, int, float, bool, None, list, dict).

Falls back to copy.deepcopy when orjson is unavailable or when the
data contains non-JSON-serialisable types.
"""

import copy

try:
    import orjson

    def fast_deepcopy(obj):
        try:
            return orjson.loads(orjson.dumps(obj))
        except (TypeError, orjson.JSONEncodeError):
            return copy.deepcopy(obj)

except ImportError:
    def fast_deepcopy(obj):
        return copy.deepcopy(obj)
