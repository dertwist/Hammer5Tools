from PySide6.QtWidgets import QWidget


class PooledPropertyMixin:
    """
    Mixin for property widgets that participate in a recycling pool.

    Subclasses must implement:
      - _pool_key_from_kwargs(**kwargs) -> hashable key
      - _current_pool_key(self) -> key used for release
      - reconfigure(self, **kwargs) -> update instance without reconstruction
    """

    _pools: dict = {}  # {subclass -> {key -> list[instance]}}
    _POOL_MAX_PER_KEY = 5
    _holder: QWidget | None = None

    @classmethod
    def _get_holder(cls) -> QWidget:
        # A single hidden holding-pen for all pooled widgets.
        if PooledPropertyMixin._holder is None:
            holder = QWidget()
            holder.setObjectName("_PoolHolder")
            holder.setVisible(False)
            # Never show; we only parent pooled instances to keep them alive.
            PooledPropertyMixin._holder = holder
        return PooledPropertyMixin._holder

    @classmethod
    def acquire(cls, *args, **kwargs):
        key = cls._pool_key_from_kwargs(**kwargs)
        pool = cls._pools.setdefault(cls, {}).setdefault(key, [])
        if pool:
            inst = pool.pop()
            inst.reconfigure(*args, **kwargs)
            inst.show()
            return inst
        return cls(*args, **kwargs)

    @classmethod
    def release(cls, inst):
        key = inst._current_pool_key()
        pool = cls._pools.setdefault(type(inst), {}).setdefault(key, [])

        # Always detach pooled instances from layouts before re-parenting/hiding.
        # (PropertyFrame._clear_widgets already removes from the layout.)
        if len(pool) >= cls._POOL_MAX_PER_KEY:
            try:
                inst.deleteLater()
            except Exception:
                pass
            return

        # Important: disconnect outbound signals to prevent duplicate slot invocations
        # when the instance is re-acquired by a different PropertyFrame.
        for sig_name in ("edited", "slider_pressed", "committed"):
            sig = getattr(inst, sig_name, None)
            if sig is None:
                continue
            try:
                sig.disconnect()
            except Exception:
                # Some signals might not have any connections yet.
                pass

        inst.hide()
        try:
            inst.setParent(cls._get_holder())
        except Exception:
            pass
        pool.append(inst)

    @classmethod
    def _pool_key_from_kwargs(cls, **kwargs):
        raise NotImplementedError

    def _current_pool_key(self):
        raise NotImplementedError

    def reconfigure(self, *args, **kwargs):
        raise NotImplementedError

