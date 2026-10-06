<#
.SYNOPSIS
Creates optional Windows shortcuts for the installed toolkit and standalone tools.
#>
[CmdletBinding()]
param(
    [string] $ApplicationPath = (Join-Path $PSScriptRoot '../Hammer5Tools.exe'),
    [string] $Destination = (Join-Path ([Environment]::GetFolderPath('Programs')) 'Hammer 5 Tools')
)

$ErrorActionPreference = 'Stop'
$ApplicationPath = (Resolve-Path -LiteralPath $ApplicationPath).Path
$Destination = [System.IO.Path]::GetFullPath($Destination)
$applicationDirectory = Split-Path -Parent $ApplicationPath
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$shortcutShell = New-Object -ComObject WScript.Shell
$tools = [ordered]@{
    'Hammer 5 Tools' = @('', $ApplicationPath)
    'SoundEvent Editor' = @('--tool soundevents', (Join-Path $applicationDirectory 'SoundEventEditor.exe'))
    'Map Builder' = @('--tool mapbuilder', (Join-Path $applicationDirectory 'MapBuilder.exe'))
    'SmartProp Editor' = @('--tool smartprops', (Join-Path $applicationDirectory 'SmartPropEditor.exe'))
    'Workshop Manager' = @('--tool workshop', (Join-Path $applicationDirectory 'WorkshopManager.exe'))
}
foreach ($tool in $tools.GetEnumerator()) {
    $shortcut = $shortcutShell.CreateShortcut((Join-Path $Destination ($tool.Key + '.lnk')))
    $shortcut.TargetPath = (Resolve-Path -LiteralPath $tool.Value[1]).Path
    $shortcut.Arguments = $tool.Value[0]
    $shortcut.WorkingDirectory = Split-Path -Parent $ApplicationPath
    $shortcut.IconLocation = (Resolve-Path -LiteralPath $tool.Value[1]).Path + ',0'
    $shortcut.Save()
}
