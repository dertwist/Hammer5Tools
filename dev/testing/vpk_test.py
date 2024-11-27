import vpk
import os
from src.preferences import get_cs2_path
path = os.path.join(get_cs2_path(), 'game', 'csgo', 'pak01_dir.vpk')
pak1 = vpk.open(path)

for filepath in pak1:
    if 'vsnd_c' in filepath:
        print(filepath)
# print(pak1)
# pakfile = pak1.get_file("smartprops/porta_potty/porta_potty.vsmart_c")
# print(pakfile.read())
# pakfile.save('test.vsmart_c')