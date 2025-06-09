[Setup]
AppName=Hammer5Tools
AppVersion=5.0.0
DefaultDirName={pf}\Hammer5Tools
OutputDir=Hammer5Tools
OutputBaseFilename=Hammer5ToolsInstaller
Compression=lzma
SolidCompression=yes

[Files]
Source: "Hammer5Tools\Hammer5Tools.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Hammer5Tools\hotkeys\*"; DestDir: "{app}\hotkeys"; Flags: recursesubdirs ignoreversion
Source: "Hammer5Tools\presets\*"; DestDir: "{app}\presets"; Flags: recursesubdirs ignoreversion
Source: "Hammer5Tools\SmartPropEditor\*"; DestDir: "{app}\SmartPropEditor"; Flags: recursesubdirs ignoreversion
Source: "Hammer5Tools\SoundEventEditor\Presets\*"; DestDir: "{app}\SoundEventEditor\Presets"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Hammer5Tools"; Filename: "{app}\Hammer5Tools.exe"
Name: "{commondesktop}\Hammer5Tools"; Filename: "{app}\Hammer5Tools.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

; Modified after archivation process

; Modified after archivation process

; Modified after archivation process
