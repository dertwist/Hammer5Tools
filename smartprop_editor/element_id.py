global m_nElementID
m_nElementID = 0
global m_nElementID_list
m_nElementID_list = []

def set_ElementId(current_id):
    global m_nElementID
    global m_nElementID_list
    if current_id in m_nElementID_list:
        m_nElementID = m_nElementID + 1
    else:
        m_nElementID = current_id
    m_nElementID_list.append(m_nElementID)
    return m_nElementID