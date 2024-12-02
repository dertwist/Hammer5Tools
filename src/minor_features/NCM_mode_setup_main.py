import os.path
import re, shutil

def NCM_mode_setup(cs2_path):
    assettypes_internal = cs2_path + r"\game\bin\assettypes_internal.txt"
    if os.path.exists(assettypes_internal):
        pass
    else:
        shutil.copyfile((cs2_path + r"\game\bin\assettypes_common.txt"), assettypes_internal)

    enginetools = (cs2_path + r"\game\bin\enginetools.txt")
    if os.path.exists(enginetools):
        pass
    else:
        shutil.copyfile((cs2_path + r"\game\bin\sdkenginetools.txt"), enginetools)