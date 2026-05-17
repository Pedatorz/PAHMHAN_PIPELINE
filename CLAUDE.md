# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Prism Pipeline v2.1.2** — an open-source pipeline automation framework for animation and VFX projects. It integrates with 11 DCC (Digital Content Creation) applications (Maya, Houdini, Blender, Nuke, 3dsMax, Cinema4D, etc.) via a plugin system.

## Running the Application

```bat
prism.bat                          # Launch main GUI (uses Python311/Prism.exe)
setup.bat                          # Run installer (PrismInstaller.py)
uninstall.bat                      # Uninstall Prism
Tools\prism_gui_with_console.bat   # Launch with console output (uses python.exe, blocks)
Tools\prism_console.bat            # Launch console only
```

Python is sourced from `Python311/` (bundled). `prism.bat` uses `Prism.exe` (no console window); the Tools variants use `python.exe` directly. Supported bundled Python versions: 3.7, 3.9, 3.10, 3.11, 3.13 — each has a corresponding `PythonLibs/Python3xx/` folder.

There is no test suite. Documentation is auto-generated via Sphinx through `.github/workflows/documentation.yml`.

## Useful Environment Variables

| Variable | Effect |
|---|---|
| `PRISM_DEBUG=True` | Enable debug logging; also clears cached UI module imports for hot-reload |
| `PRISM_LIBS` | Override path to `PythonLibs/` (default: repo root) |
| `PRISM_NO_LIBS=1` | Skip library path check |
| `PRISM_CONFIG_EXTENSION` | Config file format: `.json` (default) or `.yaml` |
| `PRISM_PYTHON_VERSION` | Override Python version string for lib lookup |
| `PRISM_IGNORE_AUTOLOAD_PLUGINS` | Comma-separated plugin names to skip on startup |

## Architecture

### Core Hub: `Scripts/PrismCore.py`

`PrismCore` is the central singleton. It owns all subsystems and is passed as `core` throughout the codebase. Startup sequence:
1. `ConfigManager` loads user/project config
2. `PluginManager` discovers and loads app plugins
3. UI starts — either `PrismTray` (background tray icon) or `ProjectBrowser` (foreground)
4. Project loads → DCC environment is configured

### Subsystems (`Scripts/PrismUtils/`)

Accessed via `core.<attribute>`:

| Module | `core` attribute | Responsibility |
|---|---|---|
| `ConfigManager` | `core.configs` | Read/write YAML/JSON/INI configs with caching |
| `PluginManager` | `core.plugins` | Plugin lifecycle and dispatch |
| `Projects` | `core.projects` | Project create/load/structure |
| `ProjectEntities` | `core.entities` | Shots, assets, sequences |
| `PathManager` | `core.paths` | File path conventions and resolution |
| `MediaManager` | `core.media` | Image/video sequences, thumbnail generation, format conversion |
| `MediaProducts` | `core.mediaProducts` | Render output product versioning |
| `Products` | `core.products` | Output product versioning |
| `Callbacks` | `core.callbacks` | Event callback registration and dispatch |
| `Users` | `core.users` | Username/abbreviation, user prefs |
| `Integration` | `core.integration` | DCC startup script injection |
| `SanityChecks` | `core.sanityChecks` | Pre-publish validation |

Other utility modules in `Scripts/PrismUtils/`: `PrismWidgets.py` (reusable Qt widgets), `ProjectWidgets.py` (project creation dialog), `Lockfile.py` (cross-process file locking), `ScreenShot.py` (viewport capture).

### Plugin Architecture (`Plugins/Apps/`)

Each DCC plugin lives in `Plugins/Apps/<AppName>/` with these files under `Scripts/`:

- `Prism_<App>_Variables.py` — constants: `pluginName`, `version`, `sceneFormats`, `platforms`
- `Prism_<App>_Functions.py` — DCC-specific implementations of Prism hooks
- `Prism_<App>_externalAccess_Functions.py` — functions callable when DCC is not running (e.g., path queries from tray)
- `Prism_<App>_Integration.py` — installs/removes startup scripts from the DCC app
- `Prism_<App>_init.py` — assembles the plugin class via multiple inheritance from all four above
- `Prism_<App>_init_unloaded.py` — lightweight stub loaded when the plugin is present but not the active app

The plugin class uses multiple inheritance:
```python
class Prism_Plugin_MyApp(
    Prism_MyApp_Variables,
    Prism_MyApp_externalAccess_Functions,
    Prism_MyApp_Functions,
    Prism_MyApp_Integration,
): ...
```

`Plugins/Apps/PluginEmpty/` is the canonical template for new app plugins. Non-app plugins (renderfarm, custom tools) go in `Plugins/Custom/`.

### Project Browser & State Manager

`Scripts/ProjectScripts/ProjectBrowser.py` — main window (`QMainWindow`) with three tabs:
- `SceneBrowser` — browse and open scene files
- `ProductBrowser` — browse exported products/caches
- `MediaBrowser` — browse renders and playblasts

`Scripts/ProjectScripts/StateManager.py` — manages the export/render state graph inside a DCC session. States are nodes that represent pipeline operations; built-in node types live in `Scripts/ProjectScripts/StateManagerNodes/`:

| Node file | Purpose |
|---|---|
| `default_Export.py` | Geometry/cache export |
| `default_ImageRender.py` | Image sequence render |
| `default_Playblast.py` | Viewport preview |
| `default_Code.py` | Custom Python execution |
| `default_ImportFile.py` | Import files into scene |
| `default_RenderSettings.py` | Renderer configuration |
| `Folder.py` | Organize states into groups |

### Callback / Hook System

Two mechanisms for extending behavior:

**In-process callbacks** — registered by plugins or core at runtime:
```python
core.callbacks.registerCallback(name, func)
core.callback(name="onProjectBrowserStartup", args=[self])
```

**File-based hooks** — Python files in `<project_root>/00_Pipeline/Hooks/`. Each hook must define `def main(**kwargs)` or `def main(core, ...)`. Hook names map to events (e.g., `postSaveScene.py`, `preExport.py`). Prism loads and calls them automatically.

### Qt Abstraction

All UI code imports from `qtpy` (not directly from `PySide2`/`PySide6`) to maintain compatibility across Qt versions:

```python
from qtpy.QtWidgets import QDialog, QWidget
from qtpy.QtCore import Qt, Signal
```

`.ui` files live alongside their `_ui.py` counterparts (generated by `uic`). Stylesheets live in `Scripts/UserInterfacesPrism/stylesheets/` — two available: `blue_moon` (default) and `qdarkstyle`.

### Error Handling Pattern

Use `@err_catcher` on any method that could raise. It catches, logs, and surfaces exceptions as non-fatal dialogs. For plugin methods, use `@err_catcher_plugin`. For scripts without `core`, use `@err_catcher_standalone`.

```python
from PrismUtils.Decorators import err_catcher

@err_catcher(name=__name__)
def myMethod(self, origin):
    ...
```

`err_catcher` requires `self.core` to exist on the first argument. The decorator suppresses duplicate error dialogs within a 1-second window.

### Configuration Files

- User preferences: `~/.prism/prism.json`
- Project config: `<project_root>/project.json`
- All configs accessed through `ConfigManager` — never read/write these files directly.
- Config format is controlled by `PRISM_CONFIG_EXTENSION`; both `.json` and `.yaml` are supported.

### Project Folder Template

New projects are stamped from `Presets/Projects/Default/`:
- `00_Pipeline/` — hooks, custom plugins, fallbacks, preset scenes
- `01_Management/`, `02_Designs/`, `03_Production/`, `04_Resources/` — production folders

`Presets/Deadline/` provides render farm integration presets for Thinkbox Deadline.

### IPC

`PrismTray` and launched DCC sessions communicate via `multiprocessing.connection.Listener`/`Client`. The tray runs a background listener thread; DCCs connect as clients to request operations (e.g., opening the Project Browser).

## PAHMHAN Customizations

This is a PAHMHAN-branded fork of upstream Prism Pipeline. The changes are intentionally narrow — branding and UI skin only. Upstream logic is preserved.

### Branding Assets (`Scripts/UserInterfacesPrism/`)

| File | Replaces | Used in |
|---|---|---|
| `PAHMHAN Logo.ico` | `p_tray.ico` + `p_tray.png` (both deleted) | Tray icon, window icon, Windows shell icon, installer, project settings |
| `PAHMHAN Logo.png` | *(companion PNG)* | Future use / alternate format of the logo |
| `LODER.png` | `prism_title.png` (still on disk, unused) | Splash screen header image |
| `HOME.png` | *(new)* | ProjectBrowser fullscreen background |
| `newproject.png` | `background.png` (still on disk, unused) | CreateProject dialog background (opacity 0.85 vs 0.3) |

When replacing any icon/logo, update all six occurrences across five files:
- `PrismTray.py` — two places (tray icon init and tray icon refresh)
- `PrismCore.py` — two places (shell icon registration and `create()` window icon)
- `PrismInstaller.py` — shortcut icon
- `ProjectSettings.py` — dialog window icon

`PAHMHAN.ico` also exists in `Scripts/UserInterfacesPrism/` but is not referenced by any script — it is a spare copy.

### Gold Theme (`#FFD700`)

`ProjectBrowser.__init__` applies a global stylesheet on `self` setting all text to `#FFD700`. Child dialogs (`CreateProject`, etc.) apply the same color individually on their labels/combos. Do not hardcode other text colors inside these files; extend the stylesheet instead.

### ProjectBrowser Background

`_setupBackground()` creates a `QLabel` on the scroll area viewport, lowered beneath all content widgets. `_updateBackground()` rescales `HOME.png` to fill the viewport — it is called from both `showEvent` and `resizeEvent`. Both methods are guarded by `@err_catcher` and no-op if the asset is missing.

### Back Button

`b_back` (corner widget of `tbw_project`) calls `_onBackClicked()`. The method closes the browser, calls `setProject(startup=True)` (which internally calls `refreshProjects()`, which shows `w_scrollParent` because existing projects are present), then *overrides* that result by explicitly forcing `w_newProjectV` visible and `w_scrollParent` hidden before recentering the dialog on screen. This double-step is intentional: `setProject` ensures the dialog exists; the manual override returns it to the New/Load landing page.

### SetProjectClass Panel Logic

`SetProjectClass.refreshProjects()` (in `ProjectWidgets.py`) mutually toggles two panels:
- **`w_scrollParent`** (project list scroll area) — shown when projects exist, hidden otherwise
- **`w_newProjectV`** (New / Load buttons overlay) — shown when no projects exist, hidden otherwise

On first-ever launch with no recent projects, `w_newProjectV` is shown. On all subsequent launches, `w_scrollParent` is shown. `_onBackClicked` manually reverses this to force the `w_newProjectV` state even though projects exist.

### CreateProject Dialog Layout

The background image (`newproject.png`) is painted at 0.85 opacity. To ensure form fields don't obscure the top portion of the image, `gridLayout.setContentsMargins(9, 140, 9, 9)` pushes them down 140 px. Font size is reduced by 1pt to keep the dialog compact.

### Windows Taskbar Grouping

`PrismCore.create()` calls `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PAHMHAN.PrismPipeline")` before creating the Qt window icon. This keeps all PAHMHAN windows grouped in the taskbar under one button. The call is wrapped in `try/except` so it is a no-op on non-Windows platforms.

### Intro Screen Behavior

`Projects.setProject()` now only shows the `IntroScreen` when no recent projects exist (first-ever launch). On subsequent launches with existing projects it skips the intro and logs a traceback-level warning — this is intentional for debugging unexpected `setProject` calls, not an error condition.

## Key Conventions

- **Python version target:** 3.7–3.13 (avoid syntax or stdlib features unavailable in 3.7).
- **Bundled libraries** (NumPy, Pillow, PyYAML, psutil, etc.) are in `PythonLibs/` — do not add pip dependencies without bundling them there.
- **Bundled FFmpeg** lives in `Tools/FFmpeg/` — used by `MediaManager` for video conversion and thumbnails.
- **Version string format:** `v{major}.{minor}.{patch}` (e.g., `v2.1.2`), defined in `Prism_<App>_Variables.py` per plugin and in `PrismCore`.
- **Thread safety:** `MediaManager` uses `_FFMPEG_LOCK` to serialize all ffmpeg operations — do not bypass this lock when adding thumbnail or conversion code. The lock guards against a crash in `imageio-ffmpeg` and `subprocess._wait` when called concurrently from multiple threads.
