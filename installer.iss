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
Source: "hammer5tools\Hammer5ToolsLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "hammer5tools\Hammer5ToolsUpdater.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "hammer5tools\app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{commondesktop}\Hammer5Tools"; Filename: "{app}\Hammer5ToolsLauncher.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"