from src.editors.soundevent_editor.common import *
elements = []
__sounds_path = os.path.join(os.getcwd(), 'sounds')
print(__sounds_path)
for dirpath, dirnames, filenames in os.walk(__sounds_path):
    for filename in filenames:
        __filepath = os.path.join(dirpath, filename)
        __filepath = vsnd_case_convert(os.path.relpath(__filepath, os.getcwd()))
        __element = {filename: __filepath}
        elements.append(__element)
        print(__element)
print(elements)
