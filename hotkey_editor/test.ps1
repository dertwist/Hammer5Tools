function New-InputBinding_t() {
    param (
        [Parameter(Mandatory = $true)]
        [string]$m_Context,
        [Parameter(Mandatory = $true)]
        [string]$m_Command,
        [Parameter(Mandatory = $true)]
        [string]$m_Input
    )

    return [PSCustomObject]@{
        m_Context = $m_Context
        m_Command = $m_Command
        m_Input   = $m_Input
        type      = "InputBinding_t"
    }
}

function New-InputMacro_t() {
    param (
        [Parameter(Mandatory = $true)]
        [string]$m_Name,
        [Parameter(Mandatory = $true)]
        [string]$m_Input
    )

    return [PSCustomObject]@{
        m_Name  = $m_Name
        m_Input = $m_Input
        type    = "InputMacro_t"
    }
}

function ParseLine() {
    <#
    .SYNOPSIS
    Parses a line that would be inside the KV3. Then returns the relevant InputBinding_t or InputMacro_t object
    #>
    param (
        [Parameter(Mandatory = $true)]
        [string]$line
    )
    [regex]$pattern = '"(.*?)"'
    
    $lineMatches = $pattern.Matches($line)

    if ($lineMatches.count -eq 3) {
        #m_bindings
        return New-InputBinding_t $lineMatches[0].Value.replace('"', '') $lineMatches[1].Value.replace('"', '') $lineMatches[2].Value.replace('"', '')
    }
    elseif ($lineMatches.count -eq 2) {
        #m_InputMacros
        return New-InputMacro_t $lineMatches[0].Value.replace('"', '') $lineMatches[1].Value.replace('"', '')
    }
}
function Convertfrom-KV3() {
    <#
    .SYNOPSIS
    Hardly a real KV3 Parser. This literally only parses the hotkey KV3 files.
    #>
    param (
        [Parameter(Mandatory = $true)]
        [Object[]]$kv3Content
    )

    $m_InputMacros = @()
    $m_Bindings = @()
    
    foreach ($line in $kv3Content) {

        $line = $line.Trim()
        if($line.StartsWith("//")) {continue}

        if ($null -eq $line -or $line.Length -eq 0) { continue }

        $parsed = ParseLine $line

        if ($parsed.type -eq "InputBinding_t") {
            $m_Bindings += $parsed
        }
        elseif ($parsed.type -eq "InputMacro_t") {
            $m_InputMacros += $parsed
        }
    }

    return @{
        InputBindingList_t = @{
            m_InputMacros = $m_InputMacros
            m_Bindings    = $m_Bindings
        }
    }
}

function ConvertTo-KV3() {
    <#
    .SYNOPSIS
    Also not a real KV3 converted. Only exports to the hotkey KV3 format
    #>
    param (
        [Parameter(Mandatory = $true)]
        [Hashtable]$kv3
    )
    $output = "<!-- schema text {2CC83121-F14F-4A36-ABB8-62F4C2799689} generic {198980D8-3A93-4919-B4C6-DD1FB07A3A4B} -->`nInputBindingList_t`n{`n"

    #Handle the m_InputMacros
    if ($kv3.InputBindingList_t.m_InputMacros.count -gt 0) {
        $output += "`tm_InputMacros =`n`t[`n"

        foreach ($i in $kv3.InputBindingList_t.m_InputMacros) {
            $output += "`t`tInputMacro_t { m_Name = `"$($i.m_Name)`"    m_Input = `"$($i.m_Input)`"},`n"
        }
        $output += "`t]`n"
    }

    $output += "`tm_Bindings =`n`t[`n"
    foreach ($i in $kv3.InputBindingList_t.m_Bindings) {

        if($null -eq $i.m_Input -or $i.m_Input -eq ""){continue} #Skip empty binds

        $output += "`t`tInputBinding_t { m_Context = `"$($i.m_Context)`"  m_Command = `"$($i.m_Command)`"    m_Input = `"$($i.m_Input)`"},`n"
    }
    $output += "`t]`n}"

    return $output
}

Function Merge-UnboundKeys()
{
    <#
    .SYNOPSIS
    After reading in the hotkeys from the txt file, this will merge all known unbound actions
    #>

    #Already merged, don't waste time
    if($Global:mergeCompleted){return}

    $merged = @()
    $hammer5AllCommands = ConvertFrom-Csv @'
"m_Context","m_Command"
"ToolSelection","BakeTransform"
"ToolSelection","MergeMeshesByEdge"
"ToolSelection","ReplaceSelectionWithInstance"
"ToolSelection","RandomizeConfiguration"
"ToolSelection","BakeTransform"
"ToolSelection","BakeTransform"
'@

    $allKnownCommands = $null

    #TODO: Get addational Hammer5 tool hotkeys. Such as ModelDoc.
    if($Global:filePath.Contains("hammer_key_bindings"))
    {
        $allKnownCommands = $hammer5AllCommands
    }
    else {
        return #Bail, don't have merge data.
    }

    foreach ($knownCommand in $allKnownCommands)
    {
        $add = $true
        foreach ($bind in $Global:allBinds.InputBindingList_t.m_Bindings)
        {
            if($knownCommand.m_Command -eq $bind.m_Command -and $knownCommand.m_Context -eq $bind.m_Context)
            {
                $add = $false
                break
            }
        }
        if($add)
        {
            $knownCommand | Add-Member -NotePropertyName m_Input -NotePropertyValue ""
            $merged += $knownCommand
        }
    }

    $Global:allBinds.InputBindingList_t.m_Bindings += $merged
    $Global:mergeCompleted = $true
}

Function Update-Tables() {
    <#
    .SYNOPSIS
    Refreshes the table data and displays all binds or searched for binds
    #>
    $Global:dataTable = New-Object System.Data.DataTable 'm_Bindings'
    $newcol = New-Object system.Data.DataColumn m_Context, ([string]); ($Global:dataTable.columns.add($newcol))
    $newcol = New-Object system.Data.DataColumn m_Command, ([string]); ($Global:dataTable.columns.add($newcol))
    $newcol = New-Object system.Data.DataColumn m_Input, ([string]); ($Global:dataTable.columns.add($newcol))

    Merge-UnboundKeys

    $count = 0
    foreach ($bind in $Global:allBinds.InputBindingList_t.m_Bindings) {
        if ($null -ne $m_ContextSearch.Text -and $m_ContextSearch.Text.Length -ne 0 -and !$bind.m_Context.toLower().contains($m_ContextSearch.Text.ToLower())) {
            continue
        }

        if ($null -ne $m_CommandSearch.Text -and $m_CommandSearch.Text.Length -ne 0 -and !$bind.m_Command.toLower().contains($m_CommandSearch.Text.ToLower())) {
            continue
        }

        if ($null -ne $bind.m_Input -and $null -ne $m_InputSearch.Text -and $m_InputSearch.Text.Length -ne 0 -and !$bind.m_Input.toLower().contains($m_InputSearch.Text.ToLower())) {
            continue
        }

        $row = $Global:dataTable.NewRow()
        $row.m_Context = $bind.m_Context
        $row.m_Command = $bind.m_Command
        $row.m_Input = $bind.m_Input
        $Global:dataTable.Rows.Add($row)
        $count++
    }
    $dataGrid.DataSource = $Global:dataTable
    $mainForm.Text = "CS2 Hammer Hotkey Editor. Showing: $count of $($Global:allBinds.InputBindingList_t.m_Bindings.count)"
}

Function DisplayDuplicates() {
    <#
    .SYNOPSIS
    Updates the display to only show binds that are duplicates and are searched for
    #>
    $allBinds = $Global:allBinds.InputBindingList_t.m_Bindings
    $dupeBinds = @()

    foreach ($b in $allBinds) {
        $dupeResult = Search-DuplicateBinds $b.m_Input

        if ($dupeResult -and $dupeResult.GetType().Name -eq "Object[]") {
            foreach ($d in $dupeResult) {
                #Only add if we aren't already in the list.
                if (!$dupeBinds.Contains($d)) {
                    $dupeBinds += $d
                }
            }
        }
    }

    $Global:dataTable = New-Object System.Data.DataTable 'm_Bindings'
    $newcol = New-Object system.Data.DataColumn m_Context, ([string]); ($Global:dataTable.columns.add($newcol))
    $newcol = New-Object system.Data.DataColumn m_Command, ([string]); ($Global:dataTable.columns.add($newcol))
    $newcol = New-Object system.Data.DataColumn m_Input, ([string]); ($Global:dataTable.columns.add($newcol))

    $count = 0
    #Only read in the binds with known dupe inputs, then search on them
    foreach ($bind in $dupeBinds) {
        if ($null -ne $m_ContextSearch.Text -and $m_ContextSearch.Text.Length -ne 0 -and !$bind.m_Context.toLower().contains($m_ContextSearch.Text.ToLower())) {
            continue
        }

        if ($null -ne $m_CommandSearch.Text -and $m_CommandSearch.Text.Length -ne 0 -and !$bind.m_Command.toLower().contains($m_CommandSearch.Text.ToLower())) {
            continue
        }

        if ($null -ne $m_InputSearch.Text -and $m_InputSearch.Text.Length -ne 0 -and !$bind.m_Input.toLower().contains($m_InputSearch.Text.ToLower())) {
            continue
        }

        $row = $Global:dataTable.NewRow()
        $row.m_Context = $bind.m_Context
        $row.m_Command = $bind.m_Command
        $row.m_Input = $bind.m_Input
        $Global:dataTable.Rows.Add($row)
        $count++
    }
    $dataGrid.DataSource = $Global:dataTable
    $mainForm.Text = "CS2 Hammer Hotkey Editor. DUPES ONLY Showing: $count of $($Global:allBinds.InputBindingList_t.m_Bindings.count)"
}

Function Update-KeypressValue() {
    <#
    .SYNOPSIS
    Valve uses different key identifiers than what .net captures - here we convert the ones we need
    Also have some handing for reserved and escaped characters
    #>
    param (
        [Parameter()]
        [string]$value
    )

    if ($value.StartsWith("NumPad")) { $value = $value.Replace("NumPad", "Num") }
    elseif ($value -eq "Decimal") { $value = "NumDec" }
    elseif ($value -eq "Add") { $value = "NumAdd" }
    elseif ($value -eq "Subtract") { $value = "NumSub" }
    elseif ($value -eq "Back") { $value = "Backspace" }
    elseif ($value -eq "OemMinus") { $value = "-" }
    elseif ($value -eq "Oemplus") { $value = "=" }
    elseif ($value -eq "OemOpenBrackets") { $value = "[" }
    elseif ($value -eq "Oem6") { $value = "]" }
    elseif ($value -eq "Oem1") { $value = ";" }
    elseif ($value -eq "Oem7") { $value = "\`"" }
    elseif ($value -eq "Oemcomma") { $value = "," }
    elseif ($value -eq "OemPeriod") { $value = "," }
    elseif ($value -eq "OemQuestion") { $value = "\/" } #Unsure if this works...
    elseif ($value -eq "Oem5") { $value = "\\" } #Escape char!
    elseif ($value -eq "Oemtilde") { $value = "`` RESERVED" } 
    elseif ($value -eq "F1") { $value = "F1 RESERVED" } 

    #Don't allow binds to reserved keys
    if ($value.Contains("RESERVED")) {
        $bindAcceptButton.Enabled = $false
    }
    else {
        $bindAcceptButton.Enabled = $true
    }

    return $value
}

Function Open-File() {
    <#
    .SYNOPSIS
    Opens the specified file and then updates the table
    #>
    param (
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $Global:mergeCompleted = $false

    $content = Get-Content $Path 
    $Global:allBinds = Convertfrom-KV3 $content

    Update-Tables
}

Function Search-DuplicateBinds() {
    <#
    .SYNOPSIS
    Reports all existing binds with the same m_Input
    
    .PARAMETER newbind
    string of the m_Input to check for dupes, such as "Ctrl+Shift+D"
    #>
    param (
        [Parameter()]
        [string]$newbind
    )

    $dupes = @()
    
    foreach ($bind in $global:allBinds.InputBindingList_t.m_bindings) {
        if($null -eq $bind.m_Input -or $bind.m_Input.length -eq 0) {continue}

        if ($bind.m_Input.ToLower() -eq $newbind.ToLower()) { $dupes += $bind }
    }

    return @($dupes)
}

#Globals
$Global:ConsumeKeyPress = $true #Should we consume the keypress in the bind collection form?
$Global:gridSelection = $null #What did we last select?
$Global:lastKey = $null #What was the last key we pressed in the bind collection from?
$Global:filePath = "c:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\core\tools\keybindings\hammer_key_bindings.txt"
$Global:showingDupes = $false
$Global:mergeCompleted = $false

#Setup main form
Add-Type -Assembly System.Windows.Forms
$mainForm = New-Object System.Windows.Forms.Form
$mainForm.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
$mainForm.AutoSize = $true

#File Menu setup
$menuMain = New-Object System.Windows.Forms.MenuStrip
$menuFile = New-Object System.Windows.Forms.ToolStripMenuItem
$mainForm.MainMenuStrip = $menuMain
[void]$mainForm.Controls.Add($mainToolStrip)
[void]$mainForm.Controls.Add($menuMain)
$menuFile.Text = "File"
[void]$menuMain.Items.Add($menuFile)

#File > Open
$menuOpen = New-Object System.Windows.Forms.ToolStripMenuItem
$menuOpen.ShortcutKeys = "Control, O"
$menuOpen.Text = "Open Keybind File"
[void]$menuFile.DropDownItems.Add($menuOpen)
$menuOpen.Add_Click({
        $selectOpenForm = New-Object System.Windows.Forms.OpenFileDialog
        $selectOpenForm.Filter = "Hammer 5 Keybinds|*.txt"

        $dir = "c:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\core\tools\keybindings"
        if (!(Test-Path $dir)) { $dir = "C:\" }
        $selectOpenForm.InitialDirectory = $dir
        $selectOpenForm.Title = "Select a File to Open"
        $getKey = $selectOpenForm.ShowDialog()
        If ($getKey -eq "OK") {
            $inputFileName = $selectOpenForm.FileName
        }
        Open-File $inputFileName
        $Global:filePath = $inputFileName
    })

#File > SaveAs
$menuSaveAs = New-Object System.Windows.Forms.ToolStripMenuItem
$menuSaveAs.ShortcutKeys = "Control, S"
$menuSaveAs.Text = "Save As"
[void]$menuFile.DropDownItems.Add($menuSaveAs)
$menuSaveAs.Add_Click({
        $selectSaveAsForm = New-Object System.Windows.Forms.SaveFileDialog
        $selectSaveAsForm.Filter = "Hammer 5 Keybinds|*.txt"
        $selectSaveAsForm.InitialDirectory = Split-Path -Path $Global:filePath
        $selectSaveAsForm.Title = "Select a File to Save"
        $selectSaveAsForm.FileName = Split-Path -Leaf $Global:filePath
        $getKey = $selectSaveAsForm.ShowDialog()
        If ($getKey -eq "OK") {
            $outputFileName = $selectSaveAsForm.FileName
            $result = ConvertTo-KV3 $Global:allBinds

            $path = Split-Path -path $outputFileName
            $file = ([io.fileinfo]$outputFileName).basename

            # $result | Out-File $outputFileName
            # $result | Out-File "$path\$file$(get-date -Format "MMddyyyy_HHmm").txt"

            $backupPath = "$path\$file$(get-date -Format "MMddyyyy_HHmm").txt"

            $Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
            [System.IO.File]::WriteAllLines($outputFileName, $result, $Utf8NoBomEncoding)
            [System.IO.File]::WriteAllLines($backupPath, $result, $Utf8NoBomEncoding)
        }
    })

#File > Toggle Show Duplicates
$menuShowDupes = New-Object System.Windows.Forms.ToolStripMenuItem
$menuShowDupes.Text = "Toggle Show Duplicates"
$menuShowDupes.ShortcutKeys = "Control, D"
[void]$menuFile.DropDownItems.Add($menuShowDupes)
$menuShowDupes.Add_Click({
        if (!$Global:showingDupes) {
            $Global:showingDupes = $true
            DisplayDuplicates
        }
        else {
            $Global:showingDupes = $false
            Update-Tables
        }
    })

#File > Restore Defauts
$restoreDefaultMenu = New-Object System.Windows.Forms.ToolStripMenuItem
$restoreDefaultMenu.Text = "Restore Default Binds"
[void]$menuFile.DropDownItems.Add($restoreDefaultMenu)
$restoreDefaultMenu.Add_Click({
    #Defaults as of Aug 14th 2023
    $defaultBinds = @'
    <!-- schema text {2CC83121-F14F-4A36-ABB8-62F4C2799689} generic {198980D8-3A93-4919-B4C6-DD1FB07A3A4B} -->
    InputBindingList_t
    {
        m_InputMacros =
        [
            InputMacro_t { m_Name = "SELECTION_ADD_KEY"				m_Input = "Shift"	},
            InputMacro_t { m_Name = "SELECTION_REMOVE_KEY"			m_Input = "Ctrl"	},
            InputMacro_t { m_Name = "TOGGLE_SNAPPING_KEY"			m_Input = "Ctrl"	},
        ]

        m_Bindings =
        [
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "FileOpen"						m_Input = "Ctrl+O"			},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "FileSave"						m_Input = "Ctrl+S"			},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "FileSaveAs"					m_Input = "Ctrl+Shift+S"	},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "SaveActivePrefab"				m_Input = "Shift+Alt+S"		},		
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "FileReload"					m_Input = "Ctrl+Shift+F12"	},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "FileNew"						m_Input = "Ctrl+N"			},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "NextSession"					m_Input = "Ctrl+Tab"		},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "PreviousSession"				m_Input = "Ctrl+Shift+Tab"	},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "BuildMap"						m_Input = "F9"				},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "ToggleShowHelpers"				m_Input = "Ctrl+Shift+H"	},
            InputBinding_t { m_Context = "HammerApp" 		m_Command = "ToggleTextureLockScale"		m_Input = "Ctrl+Shift+Y"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "TogglePropertiesPopup"			m_Input = "Alt+Enter"		},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "TogglePropertiesPopup"			m_Input = "Alt+NumEnter"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ShowMapVariablesPopup"			m_Input = "Ctrl+Shift+M"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ShowMapPropertiesPopup"		m_Input = "Ctrl+Shift+P"	},		
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleShowGameObjectsOnly"		m_Input = "Shift+O"			},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleSelectThrough"			m_Input = "Ctrl+Shift+L"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ViewDistanceNext"				m_Input = "Alt+MWheelUp"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ViewDistancePrev"				m_Input = "Alt+MWheelDn"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ShowMapManifestWidget"			m_Input = "Ctrl+Alt+M"		},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleGridNav"					m_Input = "Ctrl+Q"			},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleToolsMaterials"			m_Input = "Ctrl+Shift+F2"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleSelectionOverlay"		m_Input = "Ctrl+Shift+F4"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleInstanceOverlay"			m_Input = "Ctrl+Shift+F5"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleMeshSubdivision"			m_Input = "Ctrl+Shift+F6"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleMeshTiles3D"				m_Input = "Ctrl+Shift+F7"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleMeshTiles2D"				m_Input = "Ctrl+Shift+F8"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleSelectBackfacing"		m_Input = "Ctrl+Shift+F9"	},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ToggleFullscreenLayout"		m_Input = "Shift+Alt+Z"		},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "ShowEntityReport"				m_Input = "Ctrl+Alt+R"		},
            InputBinding_t { m_Context = "HammerApp"		m_Command = "CycleEditUVSet"				m_Input = "Alt+Y"			},
        ]
    }
'@
    $defaultBinds = $defaultBinds.Split("`n")
    
    $Global:allBinds = Convertfrom-KV3 $defaultBinds
    $Global:mergeCompleted = $false
    Update-Tables
    })

#File > About info
$aboutMenu = New-Object System.Windows.Forms.ToolStripMenuItem
$aboutMenu.Text = "By TopHATTwaffle"
[void]$menuFile.DropDownItems.Add($aboutMenu)
$aboutMenu.Add_Click({
        Start-Process "https://github.com/tophattwaffle"
    })

#Populate the datagrid
$dataGrid = New-Object System.Windows.Forms.DataGridView
$dataGrid.ScrollBars = [System.Windows.Forms.ScrollBars]::Vertical
$dataGrid.Size = New-Object System.Drawing.Size(600, 900)
$dataGrid.Location = New-Object System.Drawing.Point(0, 20)
$dataGrid.AutoSizeColumnsMode = [System.Windows.Forms.DataGridViewAutoSizeColumnMode]::Fill
$dataGrid.SelectionMode = [System.Windows.Forms.DataGridViewSelectionMode]::FullRowSelect
$dataGrid.MultiSelect = $false
$dataGrid.ReadOnly = $true
$mainForm.Controls.Add($dataGrid)

#Event for changing selection
$dataGrid.add_SelectionChanged({
        $Global:gridSelection = $dataGrid.SelectedCells
        if ($Global:gridSelection.count -eq 0) {
            $changeButton.Enabled = $false
        }
        else {
            $changeButton.Enabled = $true
        }
    })

#Now that the data grid exists, set the main window size since we can just use that
$mainForm.Width = $dataGrid.Width + 20
$mainForm.Height = $dataGrid.Height + 90

#Try opening the default file, if it exists
if (Test-Path $Global:filePath) {
    Open-File $Global:filePath
}

$changeButton = New-Object System.Windows.Forms.Button
$changeButton.Location = New-Object System.Drawing.Point(10, ($mainForm.Height - 65))
$changeButton.AutoSize = $true
$changeButton.Text = 'Change Hotkey'
$mainForm.Controls.Add($changeButton)

$m_ContextSearch = New-Object System.Windows.Forms.TextBox
$m_ContextSearch.Location = New-Object System.Drawing.Point(150, ($mainForm.Height - 65))
$m_ContextSearch.Size = New-Object System.Drawing.Size(100, 20)
$mainForm.Controls.Add($m_ContextSearch)
$m_ContextSearch.Add_KeyUp({
        Update-Tables
    })

$m_CommandSearch = New-Object System.Windows.Forms.TextBox
$m_CommandSearch.Location = New-Object System.Drawing.Point(300, ($mainForm.Height - 65))
$m_CommandSearch.Size = New-Object System.Drawing.Size(100, 20)
$mainForm.Controls.Add($m_CommandSearch)
$m_CommandSearch.Add_KeyUp({
        Update-Tables
    })

$m_InputSearch = New-Object System.Windows.Forms.TextBox
$m_InputSearch.Location = New-Object System.Drawing.Point(450, ($mainForm.Height - 65))
$m_InputSearch.Size = New-Object System.Drawing.Size(100, 20)
$mainForm.Controls.Add($m_InputSearch)
$m_InputSearch.Add_KeyUp({
        Update-Tables
    })

$keyBindForm = New-Object System.Windows.Forms.Form
$keyBindForm.Text = 'New Hotkey'
$keyBindForm.Size = New-Object System.Drawing.Size(300, 175)
$keyBindForm.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
$keyBindForm.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterParent
$keyBindForm.TopMost = $true
$keyBindForm.KeyPreview = $true
$keyBindForm.Add_KeyDown({

        #Bail if we are using the dropdown selection
        if (!$Global:ConsumeKeyPress) { return }

        if ($_.KeyCode -eq "LWin" -or $_.KeyCode -eq "RWin" -or $_.KeyCode -eq "ControlKey" -or $_.KeyCode -eq "Menu" -or $_.KeyCode -eq "ShiftKey") {
            return
        }

        #The built in converted handles some basic key conversions for us
        $converter = New-Object System.Windows.Forms.KeysConverter
        $key = $converter.ConvertToString($_.KeyCode)

        #Re-map the remaining keys that the built in converted can't do
        $key = Update-KeypressValue $key

        $Global:lastKey = $key
        $keyBindLabel.Text = "Key: $Global:lastKey"
    })

$specialKeys = New-Object System.Windows.Forms.ComboBox
$specialKeys.Location = New-Object System.Drawing.Point(125, 17)
$specialKeys.Size = New-Object System.Drawing.Size(150, 20)
$specialKeys.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList
$specialKeys.Enabled = $false
#Special keys / binds that we can't capture easily
#Marked as VOID to not display output on add
[void] $specialKeys.Items.Add("")
[void] $specialKeys.Items.Add("NumEnter")
[void] $specialKeys.Items.Add("Enter")
[void] $specialKeys.Items.Add("Esc")
[void] $specialKeys.Items.Add("Space")
[void] $specialKeys.Items.Add("LMouse")
[void] $specialKeys.Items.Add("RMouse")
[void] $specialKeys.Items.Add("MMouse")
[void] $specialKeys.Items.Add("MWheelUp")
[void] $specialKeys.Items.Add("MWheelDn")
[void] $specialKeys.Items.Add("LMouseDoubleClick")
[void] $specialKeys.Items.Add("Up")
[void] $specialKeys.Items.Add("Down")
[void] $specialKeys.Items.Add("Left")
[void] $specialKeys.Items.Add("Right")
[void] $specialKeys.Items.Add("SELECTION_ADD_KEY")
[void] $specialKeys.Items.Add("SELECTION_REMOVE_KEY")
[void] $specialKeys.Items.Add("TOGGLE_SNAPPING_KEY")
$keyBindForm.Controls.Add($specialKeys)

$specialKeysCheckbox = New-Object System.Windows.Forms.CheckBox
$specialKeysCheckbox.Location = New-Object System.Drawing.Point(100, 17)
$specialKeys.AutoSize = $true
$keyBindForm.Controls.Add($specialKeysCheckbox)
$specialKeysCheckbox.Add_CheckedChanged({
        if ($specialKeysCheckbox.Checked) {
            $bindAcceptButton.Enabled = $true #Enable the accept button incase it was disabled
            $specialKeys.Enabled = $true
            $Global:ConsumeKeyPress = $false
            $keyBindLabel.Text = "Select from list..."
        }
        else {
            $specialKeys.Enabled = $false
            $Global:ConsumeKeyPress = $true
            $specialKeys.SelectedIndex = 0
            $keyBindLabel.Text = "Press a key..."
        }
    })

$keyBindLabel = New-Object System.Windows.Forms.Label
$keyBindLabel.Location = New-Object System.Drawing.Point(10, 20)
$keyBindLabel.Size = New-Object System.Drawing.Size(280, 20)
$keyBindForm.Controls.Add($keyBindLabel)

$checkBox1 = New-Object System.Windows.Forms.CheckBox
$checkBox1.Location = New-Object System.Drawing.Point(20, 50)
$checkBox1.Size = New-Object System.Drawing.Size(90, 20)
$checkBox1.Text = 'CTRL'
$keyBindForm.Controls.Add($checkBox1)

$checkBox2 = New-Object System.Windows.Forms.CheckBox
$checkBox2.Location = New-Object System.Drawing.Point(110, 50)
$checkBox2.Size = New-Object System.Drawing.Size(90, 20)
$checkBox2.Text = 'SHIFT'
$keyBindForm.Controls.Add($checkBox2)

$checkBox3 = New-Object System.Windows.Forms.CheckBox
$checkBox3.Location = New-Object System.Drawing.Point(210, 50)
$checkBox3.Size = New-Object System.Drawing.Size(90, 20)
$checkBox3.Text = 'ALT'
$keyBindForm.Controls.Add($checkBox3)

$bindAcceptButton = New-Object System.Windows.Forms.Button
$bindAcceptButton.Location = New-Object System.Drawing.Point(150, 90)
$bindAcceptButton.AutoSize = $true
$bindAcceptButton.Text = 'Accept'
$bindAcceptButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
$keyBindForm.AcceptButton = $bindAcceptButton
$keyBindForm.Controls.Add($bindAcceptButton)

$bindCancelButton = New-Object System.Windows.Forms.Button
$bindCancelButton.Location = New-Object System.Drawing.Point(50, 90)
$bindCancelButton.AutoSize = $true
$bindCancelButton.Text = 'Cancel'
$bindCancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$keyBindForm.CancelButton = $bindCancelButton
$keyBindForm.Controls.Add($bindCancelButton)

#Changed Press event
$changeButton.add_Click({
        $keyBindForm.Text = "Editing: $($Global:gridSelection[1].value)"
        $Global:lastKey = $null
        $checkBox1.Checked = $false
        $checkBox2.Checked = $false
        $checkBox3.Checked = $false
        $specialKeysCheckbox.Checked = $false
        $specialKeys.Enabled = $false
        $specialKeys.SelectedIndex = 0
        $keyBindLabel.Text = "Press a key..."
        $result = $keyBindForm.ShowDialog()
        if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
            $result = ""
            $ctrl = $checkBox1.Checked
            $shift = $checkBox2.Checked
            $alt = $checkBox3.Checked

            if ($ctrl) { $result += "Ctrl+" }
            if ($shift) { $result += "Shift+" }
            if ($alt) { $result += "Alt+" }

            if ($Global:ConsumeKeyPress) {
                $result += $Global:lastKey
            }
            else {
                if ($specialKeys.SelectedItem -eq "") { #Handle unbinding a key
                    $result = ""
                }
                else {
                    $result += $specialKeys.SelectedItem
                }
            }

            $dupes = Search-DuplicateBinds $result

            if ($dupes) {
                $dupeStr = "Note: Duplicate binds in different Contexts are typically fine.`n`n"

                foreach ($d in $dupes) {
                    $dupeStr += "$($d.m_Context) | $($d.m_Command) | $($d.m_Input)`n"
                }

                $dupeForm = New-Object System.Windows.Forms.Form
                $dupeForm.Text = 'Duplicate Binds Found'
                
                $dupeForm.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
                $dupeForm.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterParent
                $dupeFormText = New-Object System.Windows.Forms.Label
                $dupeFormText.Text = $dupeStr
                $dupeFormText.Location = New-Object System.Drawing.Point(20, 20)
                $dupeFormText.AutoSize = $true

                $dupeAcceptButton = New-Object System.Windows.Forms.Button
                $dupeAcceptButton.Location = New-Object System.Drawing.Point(50, ($dupeForm.Height - 20))
                $dupeAcceptButton.AutoSize = $true
                $dupeAcceptButton.Text = 'Accept Dupes'
                $dupeAcceptButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
                $dupeCancelButton = New-Object System.Windows.Forms.Button
                $dupeCancelButton.Location = New-Object System.Drawing.Point(150, ($dupeForm.Height - 20))
                $dupeCancelButton.AutoSize = $true
                $dupeCancelButton.Text = "Do not Accept"
                $dupeCancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel

                $dupeForm.Controls.Add($dupeFormText)
                $dupeForm.CancelButton = $dupeCancelButton
                $dupeForm.Controls.Add($dupeCancelButton)
                $dupeForm.AcceptButton = $dupeAcceptButton
                $dupeForm.Controls.Add($dupeAcceptButton)
                $dupeForm.AutoSize = $True

                $dupeResult = $dupeForm.ShowDialog()

                if ($dupeResult -eq [System.Windows.Forms.DialogResult]::Cancel) { return }
            }

            $result = $result.TrimEnd("+")

            foreach($bind in $global:allBinds.InputBindingList_t.m_bindings)
            {
                if($bind.m_Context -eq $Global:gridSelection[0].Value -and $bind.m_Command -eq $Global:gridSelection[1].Value)
                {
                    $bind.m_Input = $result
                    break
                }
            }

            Update-Tables
        }
        $Global:dataGrid.ClearSelection()
    })

[void]$mainForm.ShowDialog()