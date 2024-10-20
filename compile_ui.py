import os
import subprocess
import threading

def compile_ui(file, output_file):
    subprocess.run(['pyside6-uic', file, '-o', output_file])
    print(file,output_file)

# Function to compile UI files with progress report
def compile_with_progress(file, output_file):
    print(f'Compiling {file}...')
    compile_ui(file, output_file)
    print(f'{file} compiled successfully.')

# Search for UI files in the project directory and compile them using PySide6
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.ui') and file != 'ui_input.ui':
            filename = os.path.basename(file)
            filename = os.path.splitext(filename)[0]
            output_file = os.path.join(root, f'ui_{filename}.py')

            # Create a thread for each UI file compilation
            thread = threading.Thread(target=compile_with_progress, args=(os.path.join(root, file), output_file))
            thread.start()

# Compile the specific UI file 'ui_input.ui'
subprocess.run(['pyside6-uic', 'ui_input.ui', '-o', 'ui_input.py'])

subprocess.run(['pyside6-rcc', '.\\resources.qrc', '-o', '.\\resources_rc.py'])