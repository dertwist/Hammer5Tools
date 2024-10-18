@echo off

REM Search for UI files in the project directory and compile them using PySide6
for /r %%i in (*.ui) do (
    set OUTPUT_FILE=%%i
    pyside6-uic %%i -o !OUTPUT_FILE:.ui=.py!
)

REM Compile the specific UI file 'ui_input.ui'
pyside6-uic ui_input.ui -o ui_input.py