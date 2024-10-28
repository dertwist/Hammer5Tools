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
            debug(f"There is {id} id in the list")
        else:
            i = 0
            while i > 0:
                m_nElementID = id + 1
                debug(f"Checking id for {m_nElementID}")
                if m_nElementID in m_nElementID_list:
                    debug(f"Found  {m_nElementID} in the list")
                    continue
                else:
                    debug(f"New Id for element {m_nElementID}")
                    m_nElementID_list.append(m_nElementID)
                    return m_nElementID

def reset_ElementID():
    global m_nElementID_list
    global m_nElementID
    m_nElementID_list = [0]
    m_nElementID = -1

def get_ElementID(value):
    """Setting m_nElementID for each element in the vsmart file. It's necessary for keeping user inputs in the map editor """
    global m_nElementID
    global m_nElementID_list
    m_nElementID = value.get('m_nElementID', set_ElementID())
    add_ElementID(m_nElementID)
    print(f'id {m_nElementID}, list {m_nElementID_list}')
    return m_nElementID

def get_ElementID_value(value):
    """Sets unique id for whole element. Input dict and output dict as well"""
    global m_nElementID
    global m_nElementID_list

    if not isinstance(value, dict):
        value = ast.literal_eval(value)
        id = value.get('m_nElementID',  set_ElementID())
        debug(f"not dict{type(id)}, {id}")
        if not isinstance(id, int):
            id = set_ElementID()
    else:
        id = value.get('m_nElementID', set_ElementID())
        debug(f"dict{type(id)}, {id}")
        if not isinstance(id, int):
            id = set_ElementID()
    value.update({'m_nElementID': id})
    # Debug
    debug(f'SetElementID value {value}')
    debug(f'SetElementID id {id}, type of the value {type(id)}')
    return str(value)
