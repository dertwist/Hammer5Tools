#requires -Version 7.0
<#
.SYNOPSIS
Builds and validates the managed application locally or in GitHub Actions.
.EXAMPLE
./build.ps1 -Task All
.EXAMPLE
./build.ps1 -Task Check -Gpu -GameAssets
#>
[CmdletBinding()]
param(
    [ValidateSet('Build', 'Check', 'Publish', 'Package', 'All')]
    [string] $Task = 'Check',
    [ValidatePattern('^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$')]
    [string] $Version = '7.0.0',
    [ValidateSet('stable', 'dev')]
    [string] $Channel = 'dev',
    [switch] $Gpu,
    [switch] $GameAssets,
    [switch] $Wizard,
    [string] $InnoCompiler = 'C:/Program Files (x86)/Inno Setup 6/ISCC.exe',
    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows) { throw 'This workflow requires Windows and the .NET SDK specified in global.json.' }
if (($Gpu -or $GameAssets) -and $Task -notin @('Check', 'All')) {
    throw '-Gpu and -GameAssets require -Task Check or All.'
}
if ($Wizard -and $Task -notin @('Package', 'All')) { throw '-Wizard requires -Task Package or All.' }
if ($Wizard -and -not $DryRun -and -not (Test-Path -LiteralPath $InnoCompiler)) {
    throw 'Install Inno Setup 6, or supply -InnoCompiler with the path to ISCC.exe.'
}

function Invoke-DotNet {
    param([string[]] $Arguments)
    Write-Host "dotnet $($Arguments -join ' ')"
    if ($DryRun) { return }
    & dotnet @Arguments
    if ($LASTEXITCODE -ne 0) { throw "dotnet failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')" }
}

$checkFailures = [Collections.Generic.List[string]]::new()
function Invoke-Check {
    param([string[]] $Arguments)
    try { Invoke-DotNet $Arguments }
    catch {
        $checkFailures.Add($_.Exception.Message)
        Write-Warning $_.Exception.Message
    }
}

Push-Location $PSScriptRoot
try {
    $solution = 'Hammer5Tools.slnx'
    Invoke-DotNet @('restore', $solution)
    Invoke-DotNet @('build', $solution, '--no-restore', '-c', 'Release', "-p:Version=$Version")

    if ($Task -in @('Check', 'All')) {
        foreach ($suite in @('Hammer5Tools.Core.Tests', 'Hammer5Tools.IntegrationTests', 'Hammer5Tools.App.Tests', 'Hammer5Tools.SmartProp.Tests')) {
            $project = "Tests/$suite/$suite.csproj"
            Invoke-Check @('run', '--project', $project, '--no-build', '--no-restore', '-c', 'Release')
        }
        $smartProp = 'Tests/Hammer5Tools.SmartProp.Tests/Hammer5Tools.SmartProp.Tests.csproj'
        if ($GameAssets) {
            Invoke-Check @('run', '--project', $smartProp, '--no-build', '--no-restore', '-c', 'Release', '--', '--game-assets')
        }
        if ($Gpu) {
            if (-not $DryRun) { New-Item -ItemType Directory -Path '.build/gpu' -Force | Out-Null }
            foreach ($mode in @('--gpu', '--main-gpu')) {
                $capture = Join-Path $PSScriptRoot ".build/gpu/$($mode.TrimStart('-')).png"
                Invoke-Check @('run', '--project', $smartProp, '--no-build', '--no-restore', '-c', 'Release', '--', $mode, $capture)
            }
        }
        Invoke-Check @('format', $solution, '--verify-no-changes', '--no-restore', '--exclude', 'Core/Steamworks', 'Core/CS2WorkshopManager', 'GUI/CS2WorkshopManager')
        if ($checkFailures.Count -gt 0) { throw "Validation failed:`n$($checkFailures -join "`n")" }
    }

    if ($Task -in @('Publish', 'Package', 'All')) {
        $buildId = [Guid]::NewGuid().ToString('N')
        $output = Join-Path $PSScriptRoot ".build/publish/$buildId/win-x64"
        Invoke-DotNet @('publish', 'GUI/Hammer5Tools.csproj', '-c', 'Release', '-r', 'win-x64', '--self-contained', 'true', "-p:Version=$Version", '-o', $output)
        if (-not $DryRun) {
            foreach ($required in @('Hammer5Tools.exe', 'SoundEventEditor.exe', 'MapBuilder.exe', 'SmartPropEditor.exe',
                'WorkshopManager.exe', 'bin/Hammer5Tools.dll', 'bin/ffmpeg/win-x64/avcodec-61.dll', 'bin/ffmpeg/win-x64/avformat-61.dll',
                'bin/ffmpeg/win-x64/avutil-59.dll', 'bin/ffmpeg/win-x64/swscale-8.dll', 'bin/ffmpeg/win-x64/swresample-5.dll',
                'bin/licenses/FFmpeg-LGPL.txt', 'bin/licenses/FFMediaToolkit/LICENSE.txt', 'icons/SoundEventEditor.ico', 'icons/MapBuilder.ico',
                'icons/SmartPropEditor.ico', 'icons/WorkshopManager.ico', 'presets/addons', 'presets/soundeventeditor', 'presets/smartpropeditor')) {
                if (-not (Test-Path -LiteralPath (Join-Path $output $required))) { throw "Published application is missing $required." }
            }
        }
        if ($Task -eq 'Publish') {
            $archive = Join-Path $PSScriptRoot '.build/Hammer5Tools-win-x64.zip'
            Write-Host "Archive: $archive"
            if (-not $DryRun) {
                $stagedArchive = Join-Path $PSScriptRoot ".build/$buildId.zip"
                [IO.Compression.ZipFile]::CreateFromDirectory($output, $stagedArchive)
                [IO.File]::Move($stagedArchive, $archive, $true)
            }
        }
        if ($Task -in @('Package', 'All')) {
            Invoke-DotNet @('tool', 'restore')
            $releaseDir = Join-Path $PSScriptRoot ".build/releases/$Channel/$Version/$buildId"
            Invoke-DotNet @('tool', 'run', 'vpk', '--', 'pack', '--packId', 'Hammer5Tools.Managed', '--packVersion', $Version,
                '--packDir', $output, '--mainExe', 'Hammer5Tools.exe', '--packTitle', 'Hammer5Tools',
                '--channel', $Channel, '--runtime', 'win-x64', '--shortcuts', 'None', '--icon', 'GUI/Assets/Icons/appicon.ico',
                '--outputDir', $releaseDir)
            Write-Host "Installer, portable ZIP and update feed: $releaseDir"
            $portableZip = Join-Path $releaseDir "Hammer5Tools.Managed-$Channel-Portable.zip"
            $setup = Join-Path $releaseDir "Hammer5Tools.Managed-$Channel-Setup.exe"
            if (-not $DryRun) {
                $payload = [IO.Compression.ZipFile]::OpenRead($portableZip)
                try {
                    foreach ($required in @('.portable', 'Hammer5Tools.exe', 'Update.exe', 'current/sq.version',
                        'current/Hammer5Tools.exe', 'current/bin/Hammer5Tools.dll', 'current/bin/ffmpeg/win-x64/avcodec-61.dll',
                        'current/bin/ffmpeg/win-x64/avformat-61.dll', 'current/bin/ffmpeg/win-x64/avutil-59.dll',
                        'current/bin/ffmpeg/win-x64/swscale-8.dll', 'current/bin/ffmpeg/win-x64/swresample-5.dll',
                        'current/bin/licenses/FFmpeg-LGPL.txt', 'current/bin/licenses/FFMediaToolkit/LICENSE.txt', 'current/SoundEventEditor.exe',
                        'current/MapBuilder.exe', 'current/SmartPropEditor.exe', 'current/WorkshopManager.exe',
                        'current/icons/SoundEventEditor.ico', 'current/icons/MapBuilder.ico',
                        'current/icons/SmartPropEditor.ico', 'current/icons/WorkshopManager.ico')) {
                        if ($null -eq $payload.GetEntry($required)) { throw "Portable package is missing $required." }
                    }
                }
                finally { $payload.Dispose() }
                if (-not (Test-Path -LiteralPath $setup)) { throw 'Velopack installer was not generated.' }
            }
            if ($Wizard) {
                $portableDir = Join-Path (Split-Path $output -Parent) 'portable'
                Write-Host "Compile installation wizard: $releaseDir"
                if (-not $DryRun) {
                    Expand-Archive -LiteralPath $portableZip -DestinationPath $portableDir
                    & $InnoCompiler '/Qp' "/DAppVersion=$Version" "/DSetupFile=$setup" "/DPortableDir=$portableDir" "/DReleaseDir=$releaseDir" 'installer/Hammer5Tools.iss'
                    if ($LASTEXITCODE -ne 0) { throw "Installer compiler failed with exit code $LASTEXITCODE." }
                }
            }
        }
    }
}
finally {
    Pop-Location
}
