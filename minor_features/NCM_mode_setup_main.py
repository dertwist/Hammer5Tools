import re, shutil

def NCM_mode_setup(cs2_path):

    # Define the new code block to insert
    new_code_block = """
            vsmart_asset =
            {
                    _class = "CResourceAssetTypeInfo"
                    m_FriendlyName = "Smart Prop"
                    m_Ext = "vsmart"
                    m_IconLg = "game:tools/images/assettypes/vdata_lg.png"
                    m_IconSm = "game:tools/images/assettypes/vdata_sm.png"
                    m_CompilerIdentifier = "CompileSmartProp"
                    m_Blocks =
                    [
                            {
                                    m_BlockID = "DATA"
                                    m_Encoding = "RESOURCE_ENCODING_KV3"
                            },
                    ]
            }
    """

    # Read the existing file conten

    shutil.copyfile((cs2_path + r"\game\bin\assettypes_common.txt"), (cs2_path + r"\game\bin\assettypes_internal.txt"))
    shutil.copyfile((cs2_path + r"\game\bin\sdkenginetools.txt"), (cs2_path + r"\game\bin\enginetools.txt"))
    file_path = cs2_path + "\\game\\bin\\assettypes_internal.txt"
    with open(file_path, 'r', encoding='utf-8') as file:
        file_content = file.read()

    # Check if the new code block already exists
    if new_code_block.strip() in file_content:
        print("The new code block already exists in the file.")
    else:
        # Locate the assettypes section
        match = re.search(r'(assettypes\s*=\s*\{)', file_content)
        if match:
            insertion_point = match.end()  # Position right after the opening brace of assettypes

            # Ensure proper formatting and insertion
            new_file_content = (
                file_content[:insertion_point].rstrip() + '\n' +
                new_code_block.strip() + '\n' +
                file_content[insertion_point:].lstrip()
            )

            # Write the updated content back to the file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(new_file_content)
            print("Code block inserted successfully.")
        else:
            print("Couldn't find assettypes section in the file.")