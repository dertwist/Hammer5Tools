"""
PropertyWidgetPool: pre-builds and caches PropertyFrame instances for the most
frequently-used SmartProp element classes.

Usage:
    pool = PropertyWidgetPool.instance()
    frame = pool.acquire(
        prop_class, value, variables_scrollArea,
        element_id_generator, widget_list, tree_hierarchy
    )
    # ... use frame ...
    pool.release(prop_class, frame)
"""

from collections import defaultdict

from PySide6.QtCore import QObject


PREWARMED_CLASSES = [
    "Model",
    "Group",
    "RandomRotation",
    "RandomScale",
    "RandomOffset",
    "Scale",
]
POOL_SIZE_PER_CLASS = 2


class PropertyWidgetPool(QObject):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._pool = defaultdict(list)

    def acquire(
        self,
        prop_class,
        value,
        variables_scrollArea,
        element_id_generator,
        widget_list,
        tree_hierarchy,
    ):
        """
        Return a configured PropertyFrame. Uses pool if available (fast path),
        otherwise constructs a new one (slow path).
        """
        from src.editors.smartprop_editor.property_frame import PropertyFrame

        if self._pool[prop_class]:
            frame = self._pool[prop_class].pop()
            frame._reconfigure(
                value,
                variables_scrollArea,
                element_id_generator,
                widget_list,
                tree_hierarchy,
            )
            return frame

        return PropertyFrame(
            value=value,
            widget_list=widget_list,
            variables_scrollArea=variables_scrollArea,
            element_id_generator=element_id_generator,
            tree_hierarchy=tree_hierarchy,
        )

    def release(self, prop_class, frame):
        """
        Return a frame to the pool. Clears its child widgets first.
        Only stores up to POOL_SIZE_PER_CLASS frames per class.
        Excess frames are destroyed via deleteLater().
        """
        if len(self._pool[prop_class]) < POOL_SIZE_PER_CLASS:
            frame._clear_widgets()
            frame.hide()
            self._pool[prop_class].append(frame)
        else:
            frame.deleteLater()

    def prewarm(
        self,
        dummy_value_factory,
        variables_scrollArea,
        element_id_generator,
        widget_list,
        tree_hierarchy,
    ):
        """
        Pre-build POOL_SIZE_PER_CLASS instances of each PREWARMED_CLASSES.
        Call this via QTimer.singleShot(500, ...) AFTER the main window is shown.

        dummy_value_factory(class_name: str) -> dict | None
        Must return a minimal valid value dict for the given class name, e.g.:
            {'_class': 'SmartProp_Group', 'm_bEnabled': True}
        Return None to skip pre-warming that class.
        """
        from src.editors.smartprop_editor.property_frame import PropertyFrame

        from PySide6.QtCore import QTimer

        for cls_name in PREWARMED_CLASSES:
            for _ in range(POOL_SIZE_PER_CLASS):
                val = dummy_value_factory(cls_name)
                if val is None:
                    continue

                frame = PropertyFrame(
                    value=val,
                    widget_list=widget_list,
                    variables_scrollArea=variables_scrollArea,
                    element_id_generator=element_id_generator,
                    tree_hierarchy=tree_hierarchy,
                )
                frame.hide()

                # _clear_widgets is called after _finish_init completes.
                # Use a short delay to ensure QTimer.singleShot(0, ...) in
                # PropertyFrame.__init__ has fired before we clear.
                QTimer.singleShot(
                    100, lambda f=frame, c=cls_name: self._store_prewarmed(c, f)
                )

    def _store_prewarmed(self, cls_name, frame):
        """Called 100ms after prewarm frame construction — safe to clear now."""
        if len(self._pool[cls_name]) < POOL_SIZE_PER_CLASS:
            frame._clear_widgets()
            frame.hide()
            self._pool[cls_name].append(frame)
        else:
            frame.deleteLater()

