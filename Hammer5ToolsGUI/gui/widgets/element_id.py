"""Element ID allocation for SmartProp documents.

``m_nElementID`` keeps user input attached to the right element in the map
editor, so every element in a document needs a stable, unique one.

Each document owns an :class:`ElementIDGenerator`
(``SmartPropDocument.element_id_generator``) and that is what callers should
use. The module-level functions delegate to one shared generator for the few
paths that run without a document in reach; they used to be a second,
unsynchronised copy of this logic.
"""

import ast
import threading


class ElementIDGenerator:
    """Allocates unique element IDs for one document.

    Each document should create its own instance to maintain its own state.
    """

    def __init__(self):
        self._current_id = 0
        self._id_list = [0]
        # Worker threads may call update_value/get_key concurrently. RLock so
        # update_value can call through to get_element_id while holding it.
        self._lock = threading.RLock()

    def current_id(self):
        """Return the current element ID."""
        return int(self._current_id)

    def add_id(self, new_id):
        """Add a new id to the list if it is not already present."""
        if new_id not in self._id_list:
            self._id_list.append(new_id)

    def set_id(self, force=False):
        """Generate a new unique id.

        If force is True or the current id is already taken, move to the next
        available one.
        """
        if force or (self._current_id in self._id_list):
            self._current_id = self.get_last_id() + 1
        return self._current_id

    def reset(self, new_id=0, new_list=None):
        """Reset the generator with a new starting id and id list."""
        if new_list is None:
            new_list = [0]
        self._id_list = new_list
        self._current_id = new_id

    def get_element_id(self, value):
        """Return the value's element ID, allocating one if it lacks a valid ID."""
        if not isinstance(value, dict):
            try:
                value = ast.literal_eval(value)
            except Exception:
                element_id = self.set_id(force=True)
                self.add_id(element_id)
                return element_id

        element_id = value.get('m_nElementID', None)
        if element_id is None or not isinstance(element_id, int):
            element_id = self.set_id(force=True)
        self.add_id(element_id)
        return element_id

    def update_value(self, value: dict, force=False):
        """Write a unique element ID into ``value``.

        With force=True a new ID is generated even if one is already present.
        """
        with self._lock:
            if force:
                element_id = self.set_id(force=True)
                self.add_id(element_id)
            else:
                element_id = self.get_element_id(value)
            value.update({'m_nElementID': element_id})
            return value

    def get_key(self, value: dict):
        """Read the element ID out of ``value``, allocating one only if missing."""
        with self._lock:
            element_id = value.get('m_nElementID', None)
            if element_id is None:
                element_id = self.set_id(force=True)
            return element_id

    def get_last_id(self):
        """Return the highest id in the list."""
        return max(self._id_list) if self._id_list else 0

    def update_child_value(self, value, force=False):
        """Recursively write element IDs through a nested value.

        Lists are walked element-wise; dicts carrying a ``_class`` key get an ID
        of their own before their children are walked.
        """
        if isinstance(value, list):
            for index, item in enumerate(value):
                value[index] = self.update_child_value(item, force=force)
        elif isinstance(value, dict):
            if '_class' in value:
                value = self.update_value(value, force=force)
                for key in value:
                    value[key] = self.update_child_value(value[key], force=force)
                return value
            else:
                for key in value:
                    value[key] = self.update_child_value(value[key], force=force)
        return value


# Shared generator behind the module-level functions below. Prefer a document's
# own generator; this exists for call sites that have no document in reach.
_shared = ElementIDGenerator()


def element_id():
    return _shared.current_id()


def add_element_id(new_id):
    _shared.add_id(new_id)


def set_element_id(force=False):
    return _shared.set_id(force=force)


def reset_element_id(id=0, id_list=None):
    _shared.reset(id, id_list)


def get_element_id(value):
    return _shared.get_element_id(value)


def update_value_element_id(value: dict, force=False):
    return _shared.update_value(value, force=force)


def get_element_id_key(value: dict):
    return _shared.get_key(value)


def get_element_id_last():
    return _shared.get_last_id()


def update_child_element_id_value(value, force=False):
    return _shared.update_child_value(value, force=force)
