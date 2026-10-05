<#
.SYNOPSIS
Creates optional Windows shortcuts for the installed toolkit and standalone tools.
#>
[CmdletBinding()]
param(
    [string] $ApplicationPath = (Join-Path $PSScriptRoot 'Hammer5Tools.App.exe'),
    [string] $Destination = (Join-Path ([Environment]::GetFolderPath('Programs')) 'Hammer 5 Tools')
)

$ErrorActionPreference = 'Stop'
$ApplicationPath = (Resolve-Path -LiteralPath $ApplicationPath).Path
$Destination = [System.IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$shortcutShell = New-Object -ComObject WScript.Shell
$tools = [ordered]@{
    'Hammer 5 Tools' = ''
    'SoundEvent Editor' = '--tool soundevents'
    'Map Builder' = '--tool mapbuilder'
    'Workshop Manager' = '--tool workshop'
}
foreach ($tool in $tools.GetEnumerator()) {
    $shortcut = $shortcutShell.CreateShortcut((Join-Path $Destination ($tool.Key + '.lnk')))
    $shortcut.TargetPath = $ApplicationPath
    $shortcut.Arguments = $tool.Value
    $shortcut.WorkingDirectory = Split-Path -Parent $ApplicationPath
    $shortcut.IconLocation = $ApplicationPath + ',0'
    $shortcut.Save()
}
