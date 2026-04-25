import ast
from multiprocessing.util import debug

from src.settings.main import debug

global m_nElementID
m_nElementID = 0
global m_nElementID_list
m_nElementID_list = [0]

def ElementId():
    global m_nElementID
    return int(m_nElementID)
def add_ElementID(new_id):
    global m_nElementID_list
    if new_id in m_nElementID_list:
        pass
    else:
        m_nElementID_list.append(new_id)
def set_ElementID(force=False):
    """Set unique ID if found current ID in the list"""
    global m_nElementID
    global m_nElementID_list
    if force:
        m_nElementID = get_ElementID_last() + 1
        debug(f"New Id for element {m_nElementID}")

        return m_nElementID
    else:
        if m_nElementID in m_nElementID_list:
            m_nElementID = get_ElementID_last() + 1
            debug(f"New Id for element {m_nElementID}")
            return m_nElementID

        else:
            debug(f"There is {m_nElementID} next id")
            return m_nElementID

def reset_ElementID(id=0, list=None):
    if list is None:
        list = [0]
    global m_nElementID_list
    global m_nElementID
    m_nElementID_list = list
    m_nElementID = id

def get_ElementID(value):
    """Setting m_nElementID for each element in the vsmart file. It's necessary for keeping user inputs in the map editor """
    global m_nElementID
    global m_nElementID_list

    if not isinstance(value, dict):
        value = ast.literal_eval(value)
        id = value.get('m_nElementID',  None)
        if id is None:
            id = set_ElementID(force=True)
        debug(f"not dict{type(id)}, {id}")
        if not isinstance(id, int):
            id = set_ElementID(force=True)
    elif isinstance(value, dict):
        id = value.get('m_nElementID',  None)
        if id is None:
            id = set_ElementID(force=True)
        debug(f"dict{type(id)}, {id}")
        if not isinstance(id, int):
            id = set_ElementID(force=True)
    else:
        id = set_ElementID()
    add_ElementID(id)
    debug(f'get_ElementID {id}')
    return id

def update_value_ElementID(value:dict, force=False):
    """Sets unique id for whole element. Input dict and output dict as well. Important for updating the value you don't need to assign new one"""
    global m_nElementID
    global m_nElementID_list

    if force:
        id = set_ElementID(force=True)
        m_nElementID_list.append(id)

    else:
        id = get_ElementID(value)

    value.update({'m_nElementID': id})

    # Debug
    # debug(f'update_value_ElementID value {value}')
    debug(f'update_value_ElementID id {id}, type of the value {type(id)}')
    return value
def get_ElementID_key(value:dict):
    """Get m_nElementID key from dict"""
    debug(f'get_ElementID_key {value.get("m_nElementID")}')
    return value.get('m_nElementID', set_ElementID(force=True))
def get_ElementID_last():
    """Get last ElementID"""
    global m_nElementID
    global m_nElementID_list
    debug(f'm_nElementID_list {m_nElementID_list}')
    last_id = 0
    for id in m_nElementID_list:
        if id > last_id:
            last_id = id
    return last_id


def update_child_ElementID_value(value, force=False):
    if isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = update_child_ElementID_value(item, force=force)
    elif isinstance(value, dict):
        if '_class' in value:
            updated_value = update_value_ElementID(value, force=force)
            for key in value:
                updated_value[key] = update_child_ElementID_value(updated_value[key], force=force)
            return updated_value
    return value

class ElementIDGenerator:
    """
    This class encapsulates element ID management.
    Each document should create its own instance to maintain its own state.
    """
    def __init__(self):
        # initial id and list of assigned ids
        self._current_id = 0
        self._id_list = [0]

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
            debug(f"New ID generated: {self._current_id}")
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
        debug(f"Obtained element ID: {element_id}")
        return element_id

    def update_value(self, value: dict, force=False):
        """
        Update the passed dict with a unique element ID.
        When force is True, a new ID will be generated even if one exists.
        """
        if force:
            element_id = self.set_id(force=True)
            self.add_id(element_id)
        else:
            element_id = self.get_element_id(value)
        value.update({'m_nElementID': element_id})
        debug(f"Updated value with element ID: {element_id}")
        return value

    def get_key(self, value: dict):
        """
        Retrieve the element ID from the dict; if missing, force its creation.
        """
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
                # Update main dict first
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