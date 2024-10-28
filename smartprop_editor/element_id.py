import ast
from multiprocessing.util import debug
from plistlib import dumps

from smartprop_editor.objects import elements_list
from preferences import debug

global m_nElementID
m_nElementID = -1
global m_nElementID_list
m_nElementID_list = [0]

def add_ElementID(new_id):
    global m_nElementID_list
    if new_id in m_nElementID_list:
        pass
    else:
        m_nElementID_list.append(new_id)
def set_ElementID():
    """Set unique ID"""
    global m_nElementID
    global m_nElementID_list
    for id in m_nElementID_list:
        if id in m_nElementID_list:
            new_id = id + 1
            while new_id in m_nElementID_list:
                new_id += 1

            debug(f"New Id for element {new_id}")
            m_nElementID_list.append(new_id)
            return new_id

        else:
            debug(f"There is {id} id in the list")
            return id

def reset_ElementID():
    global m_nElementID_list
    global m_nElementID
    m_nElementID_list = [0]
    m_nElementID = -1

def get_ElementID(value):
    """Setting m_nElementID for each element in the vsmart file. It's necessary for keeping user inputs in the map editor """
    global m_nElementID
    global m_nElementID_list

    if not isinstance(value, dict):
        value = ast.literal_eval(value)
        id = value.get('m_nElementID',  set_ElementID())
        debug(f"not dict{type(id)}, {id}")
        if not isinstance(id, int):
            id = set_ElementID()
    elif isinstance(value, dict):
        id = value.get('m_nElementID', set_ElementID())
        debug(f"dict{type(id)}, {id}")
        if not isinstance(id, int):
            id = set_ElementID()
    else:
        id = set_ElementID()
    m_nElementID = id
    add_ElementID(m_nElementID)
    debug(f'get_ElementID {m_nElementID}')
    return m_nElementID

def update_value_ElementID(value):
    """Sets unique id for whole element. Input dict and output dict as well. Important for updating the value you don't need to assign new one"""
    global m_nElementID
    global m_nElementID_list

    id = get_ElementID(value)

    value.update({'m_nElementID': id})

    # Debug
    debug(f'update_value_ElementID value {value}')
    debug(f'update_value_ElementID id {id}, type of the value {type(id)}')
    return value
def get_ElementID_key(value):
    """Get m_nElementID key from dict"""
    debug(f'get_ElementID_key {m_nElementID}')
    return value.get('m_nElementID')
