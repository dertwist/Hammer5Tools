; Velopack owns installed files and uninstallation. This wizard only selects a mode and destination.
[Setup]
AppId=Hammer5Tools.Managed.Wizard
AppName=Hammer 5 Tools
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Hammer5Tools.Managed
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Uninstallable=no
CreateUninstallRegKey=no
OutputDir={#ReleaseDir}
OutputBaseFilename=Hammer5Tools-Wizard
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "{#SetupFile}"; DestDir: "{tmp}"; DestName: "Hammer5Tools-Velopack-Setup.exe"; Flags: deleteafterinstall; Check: IsInstalled
Source: "{#PortableDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: IsPortable

[Code]
var
  ModePage: TInputOptionWizardPage;

function IsPortable: Boolean;
begin
  Result := ModePage.SelectedValueIndex = 1;
end;

function IsInstalled: Boolean;
begin
  Result := not IsPortable;
end;

procedure InitializeWizard;
begin
  ModePage := CreateInputOptionPage(wpWelcome, 'Installation mode',
    'Choose installed or portable', 'Portable mode extracts the application into the selected folder without registering an uninstaller.', True, False);
  ModePage.Add('Install for the current Windows user');
  ModePage.Add('Portable folder');
  ModePage.SelectedValueIndex := 0;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ModePage.ID then
  begin
    if IsPortable then
      WizardForm.DirEdit.Text := ExpandConstant('{userdesktop}\Hammer5Tools-Portable')
    else
      WizardForm.DirEdit.Text := ExpandConstant('{localappdata}\Hammer5Tools.Managed');
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if (CurStep = ssPostInstall) and IsInstalled then
  begin
    if not Exec(ExpandConstant('{tmp}\Hammer5Tools-Velopack-Setup.exe'),
      '--silent --installto "' + ExpandConstant('{app}') + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      RaiseException('Could not start the Velopack installer.');
    if ResultCode <> 0 then
      RaiseException('Velopack installation failed with exit code ' + IntToStr(ResultCode) + '.');
  end;
end;
