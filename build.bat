@echo off


rem pyinstaller --name="Hammer5Tools" --noconfirm --onefile --windowed  --optimize "2" --icon appicon.ico --add-data "appicon.ico:." --add-data "images;images/" --splash splash.png --noupx main.py
pyinstaller --name="Hammer5Tools" --noconfirm --onefile --windowed --optimize "2" --icon appicon.ico --add-data "appicon.ico:." --add-data "images;images/" --noupx --distpath hammer5tools main.py
rem pyinstaller --name="Hammer5Tools" --noconfirm --windowed  --optimize "2" --icon appicon.ico --add-data "appicon.ico:." --add-data "images;images/" --noupx main.py
rem python -m nuitka --onefile --windows-console-mode=disable  --enable-plugin=pyside6 --output-filename="H5T C++" --windows-icon-from-ico=appicon.ico main.py