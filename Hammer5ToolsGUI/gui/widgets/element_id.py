import ast

global m_nElementID
m_nElementID = 0
global m_nElementID_list
m_nElementID_list = [0]

def element_id():
    global m_nElementID
    return int(m_nElementID)


def add_element_id(new_id):
    global m_nElementID_list
    if new_id not in m_nElementID_list:
        m_nElementID_list.append(new_id)


def set_element_id(force=False):
    """Set unique ID if found current ID in the list"""
    global m_nElementID
    global m_nElementID_list
    if force or m_nElementID in m_nElementID_list:
        m_nElementID = get_element_id_last() + 1
        return m_nElementID
    return m_nElementID


def reset_element_id(id=0, id_list=None):
    if id_list is None:
        id_list = [0]
    global m_nElementID_list
    global m_nElementID
    m_nElementID_list = id_list
    m_nElementID = id


def get_element_id(value):
    """Setting m_nElementID for each element in the vsmart file. It's necessary for keeping user inputs in the map editor """
    global m_nElementID
    global m_nElementID_list

    if not isinstance(value, dict):
        value = ast.literal_eval(value)
        eid = value.get('m_nElementID', None)
        if eid is None or not isinstance(eid, int):
            eid = set_element_id(force=True)
    elif isinstance(value, dict):
        eid = value.get('m_nElementID', None)
        if eid is None or not isinstance(eid, int):
            eid = set_element_id(force=True)
    else:
        eid = set_element_id()
    add_element_id(eid)
    return eid


def update_value_element_id(value: dict, force=False):
    """Sets unique id for whole element. Input dict and output dict as well. Important for updating the value you don't need to assign new one"""
    global m_nElementID
    global m_nElementID_list

    if force:
        eid = set_element_id(force=True)
        m_nElementID_list.append(eid)
    else:
        eid = get_element_id(value)

    value.update({'m_nElementID': eid})
    return value


def get_element_id_key(value: dict):
    """Get m_nElementID key from dict"""
    return value.get('m_nElementID', set_element_id(force=True))


def get_element_id_last():
    """Get last ElementID"""
    global m_nElementID
    global m_nElementID_list
    last_id = 0
    for eid in m_nElementID_list:
        if eid > last_id:
            last_id = eid
    return last_id


def update_child_element_id_value(value, force=False):
    if isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = update_child_element_id_value(item, force=force)
    elif isinstance(value, dict):
        if '_class' in value:
            updated_value = update_value_element_id(value, force=force)
            for key in value:
                updated_value[key] = update_child_element_id_value(updated_value[key], force=force)
            return updated_value
    return value


ElementId = element_id
add_ElementID = add_element_id
set_ElementID = set_element_id
reset_ElementID = reset_element_id
get_ElementID = get_element_id
update_value_ElementID = update_value_element_id
get_ElementID_key = get_element_id_key
get_ElementID_last = get_element_id_last
update_child_ElementID_value = update_child_element_id_value


class ElementIDGenerator:
    """
    This class encapsulates element ID management.
    Each document should create its own instance to maintain its own state.
    """
    def __init__(self):
        # initial id and list of assigned ids
        import threading
        self._current_id = 0
        self._id_list = [0]
        # Thread-safety: worker threads may call update_value/get_key concurrently.
        # RLock is used to allow re-entrant locking within the same thread.
        self._lock = threading.RLock()

    def current_id(self):
        """Return the current element ID."""
        return int(self._current_id)

    def add_id(self, new_id):
        """Add a new id to the list if it is not already present."""
        if new_id not in self._id_list:
            self._id_list.append(new_id)

    def set_id(self, force=False):
        """
        Generate a new unique id.
        If force is True or if the current id already exists,
        assign the next available id.
        """
        if force or (self._current_id in self._id_list):
            self._current_id = self.get_last_id() + 1
        return self._current_id

    def reset(self, new_id=0, new_list=None):
        """
        Reset the generator with a new starting id and id list.
        """
        if new_list is None:
            new_list = [0]
        self._id_list = new_list
        self._current_id = new_id

    def get_element_id(self, value):
        """
        Ensures that the given value (a dict or string of dict)
        contains a valid element ID. If not, forces generation.
        """
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
        """
        Update the passed dict with a unique element ID.
        When force is True, a new ID will be generated even if one exists.
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
        """
        Retrieve the element ID from the dict; if missing, force its creation.
        """
        with self._lock:
            element_id = value.get('m_nElementID', None)
            if element_id is None:
                element_id = self.set_id(force=True)
            return element_id

    def get_last_id(self):
        """Return the highest id in the list."""
        return max(self._id_list) if self._id_list else 0

    def update_child_value(self, value, force=False):
        """
        Recursively update child element IDs in value.
        If value is a list, update each element;
        for dicts with a '_class' key, update the value and then update each child field.
        """
        if isinstance(value, list):
            for index, item in enumerate(value):
                value[index] = self.update_child_value(item, force=force)
        elif isinstance(value, dict):
            if '_class' in value:
                value = self.update_value(value, force=force)
                # Then recursively update each key/value
                for key in value:
                    value[key] = self.update_child_value(value[key], force=force)
                return value
            else:
                # For other dictionaries update each key
                for key in value:
                    value[key] = self.update_child_value(value[key], force=force)
        return value
