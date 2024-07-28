import sys
import keyvalues3 as kv3
# file = kv3.write({"generic_data_type": ["CSmartPropRoot"], "m_Variables": [{"_class": "CSmartPropVariable_Float"}], "m_Children": [{"model": [5]}], "test": [1,2,3]}, sys.stdout)
#
# kvfg = {"generic_data_type": "CSmartPropRoot", "m_Variables": [{"_class": "CSmartPropVariable_Float", "m_VariableName": "length", "m_nElementID": 61}], "m_Children": [{"_class": "CSmartPropElement_Model", "m_sModelName": "models/props/de_nuke/hr_nuke/airduct_hvac_001/airduct_hvac_001_endcap.vmdl", "m_nElementID": 2}]}
# print(kv3.write(kvfg, sys.stdout))
#
# orig_stdout = sys.stdout
# f = open(r'E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_ankhor\smartprops\out.vsmart', 'w')
# sys.stdout = f
#
# for i in range(1):
#     print(kv3.write(kvfg, sys.stdout))
# sys.stdout = orig_stdout
# f.close()
#
#
# file_path = r'E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_ankhor\smartprops\out.vsmart'
#
# # Read the file
# with open(file_path, 'r') as file:
#     content = file.read()
#
# # Replace 'NONE' with an empty string (or any other specified replacement)
# new_content = content.replace('None', '')
#
# # Write the modified content back to the file
# with open(file_path, 'w') as file:
#     file.write(new_content)





# read kv3
bt_config = kv3.read(r'E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\content\csgo_addons\de_ankhor\smartprops\out.vsmart')

print(bt_config.value)
# print(bt_config.__getitem__('m_Variables'))
# print(bt_config["m_Children"],["m_sModelName"])


