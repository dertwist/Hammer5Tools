"""
Icon caching system for better performance
"""
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt
from typing import Dict, Tuple

class IconCache:
    """Singleton icon cache for better performance"""
    _instance = None
    _cache: Dict[str, QIcon] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IconCache, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_node_icon(cls, type_str: str) -> QIcon:
        """Get cached node icon or create if not exists"""
        cache_key = f"node_{type_str}"
        if cache_key not in cls._cache:
            cls._cache[cache_key] = cls._create_node_icon(type_str)
        return cls._cache[cache_key]

    @classmethod
    def get_modifier_icon(cls) -> QIcon:
        """Get cached icon for modifiers from modeldoc_editor icons."""
        cache_key = "node_modifier"
        if cache_key not in cls._cache:
            import os
            path = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "icons",
                    "tools",
                    "modeldoc_editor",
                    "outliner_icon_model_modifier_decaluv.png",
                )
            )
            if os.path.exists(path):
                cls._cache[cache_key] = QIcon(path)
            else:
                cls._cache[cache_key] = cls.get_node_icon("operation")
        return cls._cache[cache_key]

    @classmethod
    def get_selection_criteria_icon(cls) -> QIcon:
        """Get cached icon for selection criteria from modeldoc_editor icons."""
        cache_key = "node_selection_criteria"
        if cache_key not in cls._cache:
            import os
            path = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "icons",
                    "tools",
                    "modeldoc_editor",
                    "outliner_icon_lod_group_list.png",
                )
            )
            if os.path.exists(path):
                cls._cache[cache_key] = QIcon(path)
            else:
                cls._cache[cache_key] = cls.get_node_icon("selection criteria")
        return cls._cache[cache_key]

    @classmethod
    def get_property_icon(cls, type_str: str) -> QIcon:
        """Get cached property icon or create if not exists"""
        cache_key = f"property_{type_str}"
        if cache_key not in cls._cache:
            cls._cache[cache_key] = cls._create_property_icon(type_str)
        return cls._cache[cache_key]

    @classmethod
    def _create_node_icon(cls, type_str: str) -> QIcon:
        """Create a node icon with colored label"""
        type_map = {
            'element': ("E", QColor("#ffc86a")),
            'filter': ("F", QColor("#FF646C")),
            'operation': ("O", QColor("#5387DE")),
            'selection criteria': ("CR", QColor("#FF81ED")),
            'other': ("OT", QColor("#B1DE75")),
        }
        label, color = type_map.get(type_str, ("?", QColor("#CCCCCC")))
        return cls._create_icon(label, color, 24)

    @classmethod
    def _create_property_icon(cls, type_str: str) -> QIcon:
        """Create a property icon with colored label"""
        type_map = {
            'float':  ("fl", QColor("#87FFD0")),
            'number': ("n",  QColor("#5387DE")),
            'string': ("s",  QColor("#FFD186")),
            'bool':   ("b",  QColor("#FFBDBE")),
            'vector': ("v",  QColor("#7A75DE")),
            'materialgroup': ("m", QColor("#1A75DE")),
            'directionspace': ("ds", QColor("#3A75DE")),
            'variablename': ("vn", QColor("#adde75")),
            'displayname': ("dn", QColor("#75de7a")),
            'defaultvalue': ("def", QColor("#de75de")),
            # Control-kind icons (Phase D) — distinct colour + 2-letter tag.
            'color':     ("c",  QColor("#FF6AB0")),
            'combobox':  ("cb", QColor("#56C7C7")),
            'reference': ("rf", QColor("#8FB0FF")),
            'comment':   ("//", QColor("#9AA0AA")),
            'warning':   ("!",  QColor("#FFAA00")),
            'legacy':    ("?",  QColor("#9AA0AA")),
            'comparison':("cp", QColor("#C77FD6")),
            'surface':   ("sf", QColor("#7AC7B0")),
            'colormatch':("cm", QColor("#FF8AB0")),
            'material':  ("mr", QColor("#5AA0DE")),
            'setvariable':("sv", QColor("#B0DE75")),
        }
        label, color = type_map.get(type_str, ("?", QColor("#CCCCCC")))
        return cls._create_icon(label, color, 24)

    @classmethod
    def _create_icon(cls, label: str, color: QColor, size: int = 24) -> QIcon:
        """Create an icon with given label and color"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw colored circle
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # Draw label
        painter.setPen(Qt.black)
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, label)
        painter.end()

        return QIcon(pixmap)

    @classmethod
    def clear_cache(cls):
        """Clear the icon cache"""
        cls._cache.clear()

    @classmethod
    def cache_size(cls) -> int:
        """Get current cache size"""
        return len(cls._cache)
