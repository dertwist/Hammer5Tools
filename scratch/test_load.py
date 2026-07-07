import sys
import os
sys.path.insert(0, os.path.abspath("src"))

from PySide6.QtWidgets import QApplication
from src.editors.smartprop_editor.document import SmartPropDocument

app = QApplication(sys.argv)
doc = SmartPropDocument()
try:
    doc.open_file("E:\\SteamLibrary\\steamapps\\common\\Counter-Strike Global Offensive\\content\\csgo_addons\\de_ober\\smartprops\\test.vsmart")
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
