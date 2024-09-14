import json
import re

from PySide6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem

class KeyBindingsTree(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

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
        self.setColumnCount(3)
        self.setHeaderLabels(["Context", "Command", "Input"])
        self.populate_tree(json.loads(re.sub(r'(\w+)\s*=', r'"\1":', data)))

    def populate_tree(self, bindings):
        for binding in bindings:
            context = binding.get('m_Context', '')
            command = binding.get('m_Command', '')
            input_key = binding.get('m_Input', '')

            item = QTreeWidgetItem(self)
            item.setText(0, context)
            item.setText(1, command)
            item.setText(2, input_key)

            self.addTopLevelItem(item)

# Assuming `data` is the parsed dictionary from the provided raw_data
app = QApplication([])
window = QMainWindow()
tree = KeyBindingsTree()
window.setCentralWidget(tree)
window.show()
app.exec()