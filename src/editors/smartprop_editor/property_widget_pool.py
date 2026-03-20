"""
PropertyWidgetPool: caches PropertyFrame instances by prop_class for modifier reuse.

Usage:
    pool = PropertyWidgetPool.instance()
    frame = pool.acquire(
        prop_class, value, variables_scrollArea,
        element_id_generator, widget_list, tree_hierarchy,
        precomputed=optional_batch_dict,
    )
    pool.release(prop_class, frame)
"""

from collections import defaultdict

from PySide6.QtCore import QObject

from src.editors.smartprop_editor.property.base_pooled import PooledPropertyMixin


PREWARMED_CLASSES = [
    # Elements
    "Model",
    "Group",
    "SmartProp",
    "PlaceMultiple",
    "PlaceInSphere",
    "PlaceOnPath",
    "FitOnLine",
    "PickOne",
    "ModelEntity",
    "PropPhysics",
    "PropDynamic",
    "BendDeformer",
    "MidpointDeformer",
    "Layout2DGrid",
    # Operators
    "RandomRotation",
    "RandomRotationSnapped",
    "RandomScale",
    "RandomOffset",
    "Scale",
    "Translate",
    "Rotate",
    "SetTintColor",
    "MaterialOverride",
    "SetVariable",
    "SaveState",
    "RestoreState",
    "CreateLocator",
    "CreateRotator",
    "CreateSizer",
    "ModifyState",
    # Filters
    "Probability",
    "Expression",
    "SurfaceProperties",
    "SurfaceAngle",
    "VariableValue",
    # Selection criteria
    "PathPosition",
    "EndCap",
    "LinearLength",
    "ChoiceWeight",
    "TraceInDirection",
    # Comment
    "Comment",
]
POOL_SIZE_PER_CLASS = 4
TOTAL_POOL_CAP = 512


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
        self._total = 0

    def acquire(
        self,
        prop_class,
        value,
        variables_scrollArea,
        element_id_generator,
        widget_list,
        tree_hierarchy,
        precomputed=None,
    ):
        """
        Return a configured PropertyFrame. Uses pool if available (fast path),
        otherwise constructs a new one (slow path).
        """
        from src.editors.smartprop_editor.property_frame import PropertyFrame

        use_pc = PropertyFrame._is_complete_precomputed_payload(precomputed)
        holder = PooledPropertyMixin._get_holder()

        if self._pool[prop_class]:
            frame = self._pool[prop_class].pop()
            self._total -= 1
            frame._reconfigure(
                value,
                variables_scrollArea,
                element_id_generator,
                widget_list,
                tree_hierarchy,
                precomputed=precomputed if use_pc else None,
            )
            return frame

        if use_pc:
            return PropertyFrame(
                value=precomputed["value"],
                widget_list=widget_list,
                variables_scrollArea=variables_scrollArea,
                element_id_generator=element_id_generator,
                tree_hierarchy=tree_hierarchy,
                precomputed=precomputed,
                parent=holder,
            )

        return PropertyFrame(
            value=value,
            widget_list=widget_list,
            variables_scrollArea=variables_scrollArea,
            element_id_generator=element_id_generator,
            tree_hierarchy=tree_hierarchy,
            parent=holder,
        )

    def release(self, prop_class, frame):
        """
        Return a frame to the pool or destroy if caps exceeded.
        """
        if prop_class is None:
            try:
                frame.cancel_worker()
            except Exception:
                pass
            frame.deleteLater()
            return

        if self._total >= TOTAL_POOL_CAP:
            try:
                frame.cancel_worker()
            except Exception:
                pass
            frame.deleteLater()
            return

        per_key = self._pool[prop_class]
        if len(per_key) >= POOL_SIZE_PER_CLASS:
            try:
                frame.cancel_worker()
            except Exception:
                pass
            frame.deleteLater()
            return

        try:
            frame.cancel_worker()
        except Exception:
            pass
        frame._clear_widgets()
        frame.hide()
        try:
            frame.setParent(PooledPropertyMixin._get_holder())
        except Exception:
            pass
        per_key.append(frame)
        self._total += 1

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
        """
        from src.editors.smartprop_editor.property_frame import PropertyFrame

        from PySide6.QtCore import QTimer

        holder = PooledPropertyMixin._get_holder()

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
                    parent=holder,
                )
                frame.hide()

                QTimer.singleShot(
                    100, lambda f=frame, c=cls_name: self._store_prewarmed(c, f)
                )

    def _store_prewarmed(self, cls_name, frame):
        """Called 100ms after prewarm frame construction — safe to clear now."""
        if self._total >= TOTAL_POOL_CAP:
            frame.deleteLater()
            return
        per_key = self._pool[cls_name]
        if len(per_key) >= POOL_SIZE_PER_CLASS:
            frame.deleteLater()
            return
        frame._clear_widgets()
        frame.hide()
        try:
            frame.setParent(PooledPropertyMixin._get_holder())
        except Exception:
            pass
        per_key.append(frame)
        self._total += 1
