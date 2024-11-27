import vpk

pak1 = vpk.open(r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\pak01_dir.vpk")

for filepath in pak1:
    if 'vsnd_c' in filepath:
        print(filepath)
# print(pak1)
# pakfile = pak1.get_file("smartprops/porta_potty/porta_potty.vsmart_c")
# print(pakfile.read())
# pakfile.save('test.vsmart_c')