# AGENTS.md

Hammer 5 Tools is a PySide6-based modular desktop toolkit designed to streamline level design, SmartProp editing, sound event management, map compilation, and addon packaging for Counter-Strike 2. It integrates custom Qt UI controls, KeyValues3 (KV3) parser utilities, C# .NET interop bindings, and automated build and release workflows.

## AI Agent Guidelines

Before making any changes to this repository, AI coding agents and contributors MUST review the following documentation:
- Read [ARCHITECTURE.md](ARCHITECTURE.md) for a concise index of project modules, core classes, functions, and key methods.
- Read [STYLESHEET.md](STYLESHEET.md) for UI/UX design rules, global Qt stylesheets, color palettes, and component patterns.
- Read [ConventionalCommits.md](ConventionalCommits.md) for git branch naming and commit message format specifications.

## Project Structure Overview

```
Hammer5Tools/
├── CLAUDE.md                 # Entry document for AI agents (redirects to AGENTS.md)
├── AGENTS.md                 # Main agent guidelines and project structure overview
├── ARCHITECTURE.md           # Module indexation, class maps, functions, and data flows
├── STYLESHEET.md             # UI/UX guidelines, dark mode QSS, color tokens, and widgets
├── ConventionalCommits.md    # Git commit conventions and RFC 2119 contribution rules
├── compile_ui.py             # Script to compile Qt .ui files into Python UI modules
├── makefile.py               # Build and packaging automation script (dev/stable releases)
├── requirements.txt          # Python dependencies (PySide6, pythonnet, etc.)
├── settings.ini              # Application configuration defaults
├── Hotkeys/                  # Application hotkey profiles and user bindings
├── Presets/                  # Preset definitions for tools and editors
├── SmartPropEditor/          # SmartProp editor presets and schema definitions
├── SoundEventEditor/         # SoundEvent editor configuration and templates
├── docs/                     # Additional project design and rewrite specifications
└── src/                      # Main Python source directory
    ├── main.py               # Application launcher, argument parser, and Velopack hook handler
    ├── app_core.py           # Central application controller and state orchestrator
    ├── ui_main.py            # Primary window layout initialization and tab manager
    ├── common.py             # Shared helper functions, file paths, and environment settings
    ├── dotnet.py             # pythonnet / .NET CLR interop interface layer
    ├── gitvmapmerge.py       # Git merge driver for Valve VMAP binary/text files
    ├── editors/              # Standalone & integrated editor modules
    │   ├── smartprop_editor/ # Visual editor for Valve .vsmart files
    │   ├── soundevent_editor/# Visual editor for soundevents_addon.vsndevts files
    │   ├── assetgroup_maker/ # Tool for creating and grouping game asset collections
    │   ├── hotkey_editor/    # Manager for shortcut keys and input actions
    │   └── loading_editor/   # Loading screen and map metadata builder
    ├── widgets/              # Reusable PySide6 UI widgets and tree controls
    │   ├── tree.py           # Custom tree widgets and drag-drop handlers
    │   ├── commands.py       # Context menu and command registry handlers
    │   ├── console.py        # Embedded output console widget
    │   ├── element_id.py     # Unique identifier generators for UI nodes
    │   ├── widgets.py        # Styled buttons, inputs, and input dialogs
    │   ├── completer/        # Auto-complete widgets and popup models
    │   ├── explorer/         # File explorer and asset browser controls
    │   ├── model_browser/    # 3D model viewer and asset selector
    │   ├── popup_menu/       # Contextual popup menu components
    │   └── property/         # Custom property editor fields and inspectors
    ├── property/             # Generic property inspector and value binding logic
    ├── smartprop/            # SmartProp element hierarchy, variable models, and parser
    ├── styles/               # Design system, themes, and global stylesheets
    │   ├── qt_global_stylesheet.py # Primary QSS dark mode stylesheet string
    │   ├── common.py         # Dynamic styling utilities and palette helpers
    │   ├── property_icons.py # Dynamic property icon map generators
    │   └── widgets.py        # Custom widget styling rules
    ├── forms/                # Compiled Qt form classes and modal dialogs
    ├── settings/             # Settings storage and preference management logic
    ├── git_sync/             # Git synchronization tools and vmap conflict resolution
    ├── ipc/                  # Inter-Process Communication channels and socket servers
    ├── external/             # C# .NET helper DLLs and external binary assets
    ├── updater/              # Velopack auto-updater integration client
    ├── icons/                # Image icons and vector graphics resources
    ├── images/               # Application image assets and splash graphics
    └── fonts/                # Custom bundled typography files
```

## Core Agent Instructions

1. **Keep Files Short and Modular**: Avoid creating monolithic code files; break complexity down into lightweight, single-responsibility modules.
2. **Consult ARCHITECTURE.md**: Always verify existing function signatures and module layout before adding new code.
3. **Follow UI/UX Standards**: All UI additions MUST follow [STYLESHEET.md](STYLESHEET.md).
4. **Adhere to Commit Format**: Commits MUST strictly comply with [ConventionalCommits.md](ConventionalCommits.md).
5. **No AI Agent Attribution**: Do not include AI agent names in branch names, commit messages, or contribution records.
