# Hammer5Tools automation

`Hammer5ToolsGUI.exe` contains the desktop GUI and the headless automation
entry points. Headless dispatch happens before Qt is imported.

## CLI

From a source checkout:

```powershell
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli capabilities
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli core-status
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli read-vmdl C:\addon\models\prop.vmdl
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli edit-vmat C:\addon\materials\surface.vmat --slots '{"TextureColor": "materials/new_color.png"}' --dry-run
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli compile-asset C:\addon\models\prop.vmdl
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli validate-addon C:\addon
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli vmap-references C:\addon\maps\example.vmap
```

In an installed build, replace the Python invocation with the path to
`app\Hammer5ToolsGUI.exe`.

Run `cli capabilities` to discover all operations implemented by the installed
version. Modifying commands support `--dry-run` to preview changes safely without
writing to disk.

## MCP

Hammer5Tools provides a local MCP stdio server:

```powershell
Hammer5ToolsGUI.exe mcp serve
```

The agent launches this command and communicates with it over stdin/stdout; it
is not a network listener. For example, a Codex configuration can contain:

```toml
[mcp_servers.hammer5tools]
command = "C:\\Users\\me\\AppData\\Local\\Hammer5Tools\\current\\app\\Hammer5ToolsGUI.exe"
args = ["mcp", "serve"]
default_tools_approval_mode = "writes"
startup_timeout_sec = 20
tool_timeout_sec = 600
```

Server-wide agent guidance is maintained in
`Hammer5ToolsGUI/automation/mcp/instructions.md`. Tool descriptions, JSON
schemas, annotations, and implementations are registered in
`Hammer5ToolsGUI/automation/tools.py`.
