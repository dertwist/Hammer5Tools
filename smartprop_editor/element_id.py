import ast
from multiprocessing.util import debug
from plistlib import dumps

from smartprop_editor.objects import elements_list
from preferences import debug

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
            set_ElementID()
        debug(f"not dict{type(id)}, {id}")
        if not isinstance(id, int):
            id = set_ElementID()
    elif isinstance(value, dict):
        id = value.get('m_nElementID',  None)
        if id is None:
            set_ElementID()
        debug(f"dict{type(id)}, {id}")
        if not isinstance(id, int):
            id = set_ElementID()
    else:
        id = set_ElementID()
    add_ElementID(id)
    debug(f'get_ElementID {id}')
    return id

def update_value_ElementID(value, force=False):
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
def get_ElementID_key(value):
    """Get m_nElementID key from dict"""
    debug(f'get_ElementID_key {value.get('m_nElementID')}')
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
    print(value)
    if isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = update_child_ElementID_value(item)
    elif isinstance(value, dict):
        if '_class' in value:
            updated_value = update_value_ElementID(value, force=force)
            for key in updated_value:
                updated_value[key] = update_child_ElementID_value(updated_value[key])
            return updated_value
    return value

value = {'_class': 'CSmartPropElement_SmartProp', 'm_sSmartProp': 'smartprops/sp_stairs_line.vsmart', 'm_Modifiers': [], 'm_SelectionCriteria': [{'_class': 'CSmartPropSelectionCriteria_LinearLength', 'm_flLength': 8, 'm_bAllowScale': False, 'm_flMinLength': 8, 'm_flMaxLength': 8, 'm_sLabel': '', 'm_nElementID': 20}], 'm_sLabel': 'SmartProp_01', 'm_nElementID': 19}
update_child_ElementID_value(value, force=True)
print(value)