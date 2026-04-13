import re

content = '''
    m_refMeshes = [
        "models/my_mesh1.vmdl",
        "models/my_mesh2.vmdl_c"
    ]
    model = "models/player.vmdl"
'''

pattern = r'"([^"]+\.(?:vmdl|vsmart|vmat|vpcf|vsndevts|vtex|vsnd|txt|kv3)(?:_c)?)"'
print(re.findall(pattern, content, re.IGNORECASE))
