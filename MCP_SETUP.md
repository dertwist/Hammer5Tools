# Hammer5Tools automation

`Hammer5ToolsGUI.exe` contains the desktop GUI and the headless automation
entry points. Headless dispatch happens before Qt is imported.

## CLI

From a source checkout:

```powershell
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli capabilities
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli core-status
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli vmdl-read C:\addon\models\prop.vmdl
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli call hammer5tools.vmat_edit --args '{"path":"C:/addon/materials/surface.vmat","set_slots":{"TextureColor":"materials/new_color.png"},"dry_run":true}'
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli compile C:\addon\models\prop.vmdl --background
.\.venv\Scripts\python.exe Hammer5ToolsGUI\gui\main.py cli validate --addon example
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

Use `initialize` to read the server version and `tools/list` to inspect the
schema exposed by the executable your client actually launches. Source and
installed builds can differ even when their application version matches. A
client adapter can also rename tools; compare schemas after normalizing those
names before treating an argument as unsupported.

The current single-file `hammer5tools.compile_asset` schema includes `force`
(boolean, default false) and `timeout_seconds` (integer, default 120), plus
optional `cs2_path`, `addon_root`, `background`, and `dry_run`. Force forwards `-f`. The
execution timeout is separate from the client's `tool_timeout_sec` above.

File tools resolve relative names against explicit `addon_root`, otherwise the
configured addon at request time. Absolute workflows remain supported. Relative
paths require an unambiguous root and cannot escape it through junctions.
References default to 50 rows; use filtering and offsets to recover full lists.

`compile_assets` accepts exactly one of paths, pattern, or paths_file (UTF-8 JSON
string array). Background calls return a job_id; use compile_job_status,
compile_job_cancel, and compile_log. Active jobs become interrupted after host
restart; they are never automatically restarted or signalled by a stale PID.
Logs/terminal metadata have seven-day retention with cleanup on later requests.
See the compile-verify guide for timeout/shutdown and aggregate-result semantics.

VMAT/VMDL batch creation/updates, structured VMAP insertion/groups/grid layouts,
compiled render bounds, and explicit 8-bit PNG channel preparation are available
through `cli call` and MCP. Fetch the applicable guide and inspect tools/list.
These features require the updated Python surface **and** NativeAOT library.
An older ABI-2 library still loads existing features; invoking a missing additive
export reports that the updated library must be published. This checkout does
not update an already installed executable or a running adapter automatically.

Reproducible fixture measurements and the inspected local deployment parity
are recorded in [docs/mcp_feedback_progress.md](docs/mcp_feedback_progress.md).
