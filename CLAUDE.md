# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Prism Pipeline is a VFX/Animation pipeline automation framework (v2.1.2, LGPL-3.0). It manages assets, shots, versions, and products across projects and integrates with major DCCs (Blender, Maya, Houdini, Cinema4D, After Effects, Nuke, Photoshop, 3ds Max, PureRef).

## Running the Application

```bat
# Launch the main application (Windows)
Prism/prism.bat

# Launch the setup/installer wizard
Prism/setup.bat

# Console and debug variants
Prism/Tools/prism_console.bat
Prism/Tools/prism_gui_with_console.bat
```

Both bat files invoke the bundled Python 3.11 interpreter at `Prism/Python311/`:
- `prism.bat` → `pythonw.exe Scripts/PrismCore.py`
- `setup.bat` → `python.exe Scripts/PrismInstaller.py`

There is no automated test suite. Validation is done by running the application and exercising the UI.

## Manual Installation (from source)

1. Clone the repo.
2. Download [Prism dependencies](https://www.dropbox.com/scl/fi/bmgsht89nb9u04sqprzrp/Prism_dependencies_v2.0.5.zip) and extract into the `Prism/` folder (provides `Python311/`, `Python313/`, `PythonLibs/`, etc.).
3. Run `setup.bat`.

## Architecture

### Entry Point & Core

`Prism/Scripts/PrismCore.py` (~7,170 lines) is the central hub. It instantiates all manager classes from `PrismUtils/` and acts as the shared context passed through the entire application.

### Manager Modules (`Prism/Scripts/PrismUtils/`)

| Module | Responsibility |
|---|---|
| `PluginManager` | Discovers and loads DCC/custom plugins; handles lifecycle and startup callbacks |
| `ConfigManager` | Reads/writes YAML, JSON, and INI configs; caches them; supports lockfiles for concurrent access |
| `PathManager` | Generates all file paths for scenes, renders, caches, and products; manages version numbering and storage locations |
| `Projects` | Create/load/switch projects; manages project structure (shots, assets, categories) |
| `ProjectEntities` | Asset, shot, and sequence entity CRUD |
| `MediaManager` | Image-sequence detection, video file handling, format conversion, thumbnail generation |
| `Products` / `MediaProducts` | Product versioning, master version promotion, export cache management |
| `Callbacks` | Event-driven hook system; plugins register callbacks by name and priority |
| `Users` | User detection, environment setup, user preferences |
| `Decorators` | `@err_catcher` decorator used throughout for exception handling |

### Plugin System (`Prism/Plugins/Apps/`)

Each DCC plugin lives under `Apps/<DCC>/Scripts/` and follows a consistent naming convention:

```
Prism_<DCC>_init.py              # Main plugin class (loaded first)
Prism_<DCC>_Variables.py         # Plugin constants and version info
Prism_<DCC>_Functions.py         # Core pipeline functions
Prism_<DCC>_Integration.py       # DCC startup/environment integration
Prism_<DCC>_externalAccess_Functions.py  # External API surface
Prism_<DCC>_init_unloaded.py     # Fallback when DCC is absent
```

Plugins are loaded by `PluginManager` from:
1. Default path (`Prism/Plugins/`)
2. Additional paths from `PRISM_PLUGIN_PATHS` env var
3. Search paths from `PRISM_PLUGIN_SEARCH_PATHS`

### UI Components (`Prism/Scripts/ProjectScripts/`)

- **ProjectBrowser** – Main window; tabs into SceneBrowser, ProductBrowser, MediaBrowser
- **StateManager** – Render/export job graph; state node types live in `StateManagerNodes/`
- **EditShot**, **DependencyViewer** – Additional pipeline tools

GUI is built with Qt abstracted through `qtpy` (supports PyQt5 and PySide6).

### Configuration

- **User prefs**: `%APPDATA%/Prism2/` (Windows) or platform equivalent
- **Project config**: `<ProjectRoot>/00_Pipeline/pipeline.yml` (or `.json`)
- **Format**: controlled by `PRISM_CONFIG_EXTENSION` env var (`.yml` default)

### Key Environment Variables

| Variable | Purpose |
|---|---|
| `PRISM_LIBS` | Path to dependencies directory |
| `PRISM_NO_LIBS` | Skip library version check |
| `PRISM_CONFIG_EXTENSION` | Preferred config format (`.json` or `.yml`) |
| `PRISM_PYTHON_VERSION` | Select Python version to use |
| `PRISM_PLUGIN_PATHS` | Colon/semicolon-separated additional plugin load paths |
| `PRISM_PLUGIN_SEARCH_PATHS` | Directories to search for plugins |
| `PRISM_DEBUG` | Enable debug logging |
| `PRISM_USER_PREFS` | Override user preferences directory |
| `PRISM_IGNORE_AUTOLOAD_PLUGINS` | Comma-separated plugin names to skip |

### Error Handling Pattern

The `@err_catcher(name=__name__)` decorator (from `PrismUtils/Decorators.py`) wraps most methods and provides standardized exception catching and logging. Apply it to any new method added to core or plugin classes.

### Callback/Hook System

Callbacks are named string events (e.g., `"projectChanged"`, `"sceneSaved"`). Plugins and external scripts register handlers via `core.callbacks.registerCallback(name, func, args)`. Custom hook scripts are discovered from `<ProjectRoot>/00_Pipeline/Hooks/` and the user prefs hooks directory.
