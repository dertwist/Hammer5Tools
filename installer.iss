[Setup]
AppName=Hammer5Tools
AppVersion=5.0.0
DefaultGroupName=Hammer 5Tools

; Install to a portable folder by default
DefaultDirName=C:\Portable\Hammer5Tools

; Do not generate an uninstaller
Uninstallable=no

OutputDir=dist
OutputBaseFilename=hammer5tools_setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "Hammer5Tools\Hammer5Tools.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Hammer5Tools\hotkeys\*"; DestDir: "{app}\hotkeys"; Flags: recursesubdirs ignoreversion
Source: "Hammer5Tools\presets\*"; DestDir: "{app}\presets"; Flags: recursesubdirs ignoreversion
Source: "Hammer5Tools\SmartPropEditor\*"; DestDir: "{app}\SmartPropEditor"; Flags: recursesubdirs ignoreversion
Source: "Hammer5Tools\SoundEventEditor\Presets\*"; DestDir: "{app}\SoundEventEditor\Presets"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{commondesktop}\Hammer5Tools"; Filename: "{app}\Hammer5Tools.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"