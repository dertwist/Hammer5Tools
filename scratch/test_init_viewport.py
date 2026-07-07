import sys
import os
sys.path.insert(0, os.path.abspath("src"))

from PySide6.QtWidgets import QApplication
from src.editors.smartprop_editor.viewport_3d import SmartProp3DViewport

app = QApplication(sys.argv)
vp = SmartProp3DViewport()
print("Viewport created successfully!")
