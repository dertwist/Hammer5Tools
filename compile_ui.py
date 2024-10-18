import os
import subprocess

# Search for UI files in the project directory and compile them using PySide6
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.ui') and file != 'ui_input.ui':
            filename = os.path.basename(file)
            filename = os.path.splitext(filename)[0]
            # output_file = os.path.join(root, file.replace('.ui', '.py'))
            output_file = os.path.join(root, f'ui_{filename}.py')
            subprocess.run(['pyside6-uic', os.path.join(root, file), '-o', output_file])

# Compile the specific UI file 'ui_input.ui'
subprocess.run(['pyside6-uic', 'ui_input.ui', '-o', 'ui_input.py'])