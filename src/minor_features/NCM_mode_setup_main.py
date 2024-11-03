import re, shutil

def NCM_mode_setup(cs2_path):
    shutil.copyfile((cs2_path + r"\game\bin\assettypes_common.txt"), (cs2_path + r"\game\bin\assettypes_internal.txt"))
    shutil.copyfile((cs2_path + r"\game\bin\sdkenginetools.txt"), (cs2_path + r"\game\bin\enginetools.txt"))