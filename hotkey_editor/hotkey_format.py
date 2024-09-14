import ast

data = '''
{
	m_Bindings =
	[
		{	m_Context = "AnimGraphEditor" 					m_Command = "Find"						m_Input = "Ctrl+F"			},
		{	m_Context = "AnimGraphEditor" 					m_Command = "NextFrame"					m_Input = "]"				},
		{	m_Context = "AnimGraphEditor" 					m_Command = "PrevFrame"					m_Input = "["				},
		{	m_Context = "AnimGraphEditor" 					m_Command = "PreviewGraph"				m_Input = "F5"				},
		{	m_Context = "AnimGraph_Preview_WaypointMode"	m_Command = "SelectionAddModifier"		m_Input = "Shift"			},
		{	m_Context = "AnimGraph_Preview_WaypointMode"	m_Command = "PlaceWaypoint"				m_Input = "LMouse"			},
		{	m_Context = "AnimGraph_Preview_PlayerInput"		m_Command = "PlaceMoveTarget"			m_Input = "LMouse"			},
		{	m_Context = "AnimGraph_Preview_WASDInput"		m_Command = "ForwardButton"				m_Input = "W"				},
		{	m_Context = "AnimGraph_Preview_WASDInput"		m_Command = "BackwardButton"			m_Input = "S"				},
		{	m_Context = "AnimGraph_Preview_WASDInput"		m_Command = "LeftButton"				m_Input = "A"				},
		{	m_Context = "AnimGraph_Preview_WASDInput"		m_Command = "RightButton"				m_Input = "D"				},
		{	m_Context = "AnimGraph_Preview_WASDInput"		m_Command = "RotateCameraButton"		m_Input = "LMouse"			},
	]
}
'''
def custom_parser(data):
    bindings = []
    in_bindings = False
    current_binding = {}

    lines = data.split('\n')
    for line in lines:
        if 'm_Bindings =' in line:
            in_bindings = True
            continue
        if in_bindings and line.strip() == '},':
            bindings.append(current_binding)
            current_binding = {}
        if in_bindings and '=' in line:
            key_value = line.strip().split('=')
            key = key_value[0].strip()
            value = key_value[1].strip().strip('"')
            current_binding[key] = value
            print(value)

    # Add the last binding if it exists
    # if current_binding:
    bindings.append(current_binding)

    return bindings
print(custom_parser(data))