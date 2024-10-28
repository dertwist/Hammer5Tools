from pywin.scintilla.bindings import next_id

global m_nElementID
m_nElementID = 0
global m_nElementID_list
m_nElementID_list = ()

def set_ElemntID(current_id):
    global m_nElementID
    global m_nElementID_list
    print(f'Global id is {m_nElementID}')
    print(f'Current id is {current_id}')
    if current_id in m_nElementID_list:
        m_nElementID = m_nElementID + 1
    else:
        m_nElementID = current_id
    m_nElementID_list = m_nElementID_list + (m_nElementID,)
    print(f"Ids {m_nElementID_list}")
    return m_nElementID
