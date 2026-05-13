# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import sys
import logging
import traceback
import glob
from typing import Any, Optional, List, Dict, Tuple, Callable, Union

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class Callbacks(object):
    """Manages callbacks and hooks for the Prism pipeline system.
    
    This class provides a centralized system for registering, managing, and triggering
    callbacks and hooks throughout the Prism pipeline. Callbacks allow plugins and core
    functionality to respond to events, while hooks enable custom Python scripts to be
    executed at specific points in the workflow.
    
    Attributes:
        core: The Prism core instance
        currentCallback: Dictionary tracking the currently executing callback
        registeredCallbacks: Dictionary of all registered callback functions
        registeredHooks: Dictionary of all registered hook scripts
        availableCallbacks: List of available callback names
        triggeredCallbacks: List of callbacks that have been triggered
        callbackNum: Counter for generating unique callback IDs
        hookNum: Counter for generating unique hook IDs
    """
    
    def __init__(self, core: Any) -> None:
        """Initialize the Callbacks manager.
        
        Args:
            core: The Prism core instance
        """
        self.core = core
        self.currentCallback = {"plugin": "", "function": ""}
        self.registeredCallbacks = {}
        self.registeredHooks = {}
        self.availableCallbacks = []
        self.availableCallbacks += self.getCoreCallbacks() 
        self.triggeredCallbacks = []
        self.callbackNum = 0
        self.hookNum = 0

    @err_catcher(name=__name__)
    def registerCallback(
        self,
        callbackName: str,
        function: Callable,
        priority: int = 50,
        plugin: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Register a callback function to be triggered by specific events.
        
        Callbacks are sorted by priority (higher values are executed first) and
        stored in the registeredCallbacks dictionary. Each callback receives a
        unique ID for later reference.
        
        Args:
            callbackName: Name of the callback event to register for
            function: The callable function to execute when the callback is triggered
            priority: Priority level for callback execution order (higher = earlier). Defaults to 50
            plugin: Optional plugin instance that owns this callback
            
        Returns:
            Dictionary containing callback metadata including function, name, priority, id, and plugin
        """
        if callbackName not in self.registeredCallbacks:
            self.registeredCallbacks[callbackName] = []

        self.callbackNum += 1
        cbDict = {
            "function": function,
            "callbackName": callbackName,
            "priority": priority,
            "id": self.callbackNum,
            "plugin": plugin,
        }
        self.registeredCallbacks[callbackName].append(cbDict)
        self.registeredCallbacks[callbackName] = sorted(
            self.registeredCallbacks[callbackName],
            key=lambda x: int(x["priority"]),
            reverse=True,
        )
        # logger.debug("registered callback: %s" % str(cbDict))
        return cbDict

    @err_catcher(name=__name__)
    def unregisterPluginCallbacks(self, plugin: Any) -> None:
        """Unregister all callbacks belonging to a specific plugin.
        
        Collects all callback IDs associated with the given plugin and removes
        them from the registered callbacks.
        
        Args:
            plugin: The plugin instance whose callbacks should be removed
        """
        cbIds = []
        for callback in self.registeredCallbacks:
            for callbackItem in self.registeredCallbacks[callback]:
                if callbackItem["plugin"] == plugin:
                    cbIds.append(callbackItem["id"])

        for cbId in cbIds:
            self.unregisterCallback(cbId)

    @err_catcher(name=__name__)
    def unregisterCallback(self, callbackId: int) -> bool:
        """Unregister a specific callback by its ID.
        
        Searches through all registered callbacks to find and remove the callback
        with the specified ID.
        
        Args:
            callbackId: The unique ID of the callback to unregister
            
        Returns:
            True if the callback was found and removed, False otherwise
        """
        for cbName in self.registeredCallbacks:
            for cb in self.registeredCallbacks[cbName]:
                if cb["id"] == callbackId:
                    self.registeredCallbacks[cbName].remove(cb)
                    try:
                        logger.debug("unregistered callback: %s" % str(cb))
                    except:
                        pass

                    return True

        logger.debug("couldn't unregister callback with id %s" % callbackId)
        return False

    @err_catcher(name=__name__)
    def registerHook(self, hookName: str, filepath: str) -> Dict[str, Any]:
        """Register a Python script hook to be executed for specific events.
        
        Hooks are Python scripts stored in the project that can be executed at
        specific points in the workflow. Each hook receives a unique ID.
        
        Args:
            hookName: Name of the hook event to register for
            filepath: Path to the Python script file containing the hook code
            
        Returns:
            Dictionary containing hook metadata including name, filepath, and id
        """
        if hookName not in self.registeredHooks:
            self.registeredHooks[hookName] = []

        self.hookNum += 1
        hkDict = {
            "hookName": hookName,
            "filepath": filepath,
            "id": self.hookNum,
        }
        self.registeredHooks[hookName].append(hkDict)
        # logger.debug("registered hook: %s" % str(hkDict))
        return hkDict

    @err_catcher(name=__name__)
    def registerProjectHooks(self) -> None:
        """Register all Python script hooks found in the project's hook folder.
        
        Clears any existing registered hooks and scans the project's hook folder
        for Python files, registering each one as a hook.
        """
        self.registeredHooks = {}
        hooks = self.getProjectHooks()
        for hook in hooks:
            self.registerHook(hook["name"], hook["path"])

    @err_catcher(name=__name__)
    def getProjectHooks(self) -> Optional[List[Dict[str, str]]]:
        """Retrieve all hook scripts from the project's hook folder.
        
        Scans the project hook folder for Python files and returns their metadata.
        
        Returns:
            List of dictionaries containing 'name' and 'path' for each hook,
            or None if no project is loaded
        """
        if not getattr(self.core, "projectPath", None):
            return

        hookPath = os.path.join(self.core.projects.getHookFolder(), "*.py")

        hookPaths = glob.glob(hookPath)
        hooks = []
        for path in hookPaths:
            name = os.path.splitext(os.path.basename(path))[0]
            hookData = {"name": name, "path": path}
            hooks.append(hookData)

        return hooks

    @err_catcher(name=__name__)
    def createProjectHook(self, name: str, content: Optional[str] = None) -> None:
        """Create a new hook script file in the project's hook folder.
        
        Creates a new Python script file that can be used as a hook. If the hook
        already exists, displays an error popup. Automatically adds .py extension
        if not present.
        
        Args:
            name: Name of the hook file to create (will have .py added if missing)
            content: Optional initial content to write to the hook file
        """
        if not name.endswith(".py"):
            name += ".py"

        hookFolder = self.core.projects.getHookFolder()
        hookPath = os.path.join(hookFolder, name)
        if os.path.exists(hookPath):
            msg = "The hook \"%s\" exists already." % name
            self.core.popup(msg)
            return

        if not os.path.exists(hookFolder):
            try:
                os.makedirs(hookFolder)
            except Exception as e:
                self.core.popup("Failed to create folder:\n\n%s\n\n%s" % (hookFolder, e))
                return

        with open(hookPath, "w") as f:
            if content:
                f.write(content)

    @err_catcher(name=__name__)
    def callback(self, name: str = "", *args: Any, **kwargs: Any) -> List[Any]:
        """Trigger all registered callbacks and hooks for the specified event.
        
        Executes all callback functions and hooks registered for the given event name
        in priority order. Results from all callbacks are collected and returned.
        
        Args:
            name: Name of the callback event to trigger
            *args: Positional arguments to pass to callback functions
            **kwargs: Keyword arguments to pass to callback functions. If 'args' key
                     exists in kwargs, those arguments are appended to the positional args
            
        Returns:
            List of results from all executed callbacks and hooks. If a callback
            returns a dict with 'combine': True, its 'results' list is flattened
            into the main result list
        """
        if "args" in kwargs:
            args = list(args)
            args += kwargs["args"]
            del kwargs["args"]

        result = []
        self.core.catchTypeErrors = True
        self.currentCallback["function"] = name

        if name in self.registeredCallbacks:
            for cb in list(self.registeredCallbacks[name]):
                self.currentCallback["plugin"] = getattr(cb["plugin"], "pluginName", "")
                res = cb["function"](*args, **kwargs)
                if isinstance(res, dict) and res.get("combine", False):
                    result += res["results"]
                else:
                    result.append(res)

        if name in self.registeredHooks:
            for cb in self.registeredHooks[name]:
                result.append(self.callHook(name, *args, **kwargs))

        if name not in self.triggeredCallbacks:
            self.triggeredCallbacks.append(name)

        self.core.catchTypeErrors = False
        return result

    @err_catcher(name=__name__)
    def callHook(self, hookName: str, *args: Any, **kwargs: Any) -> Any:
        """Execute a specific hook script by name.
        
        Dynamically imports and executes a Python script hook from the project's
        hook folder. The hook's main() function is called with the provided arguments.
        The core instance is automatically added to kwargs.
        
        Args:
            hookName: Name of the hook to execute (without .py extension)
            *args: Positional arguments to pass to the hook's main function
            **kwargs: Keyword arguments to pass to the hook's main function
            
        Returns:
            The return value from the hook's main() function, or None if the
            hook doesn't exist or if no project is loaded
        """
        if not getattr(self.core, "projectPath", None):
            return

        result = None
        hookPath = os.path.join(self.core.projects.getHookFolder(), hookName + ".py")
        if os.path.exists(os.path.dirname(hookPath)) and os.path.basename(
            hookPath
        ) in os.listdir(os.path.dirname(hookPath)):
            hookDir = os.path.dirname(hookPath)
            if hookDir not in sys.path:
                sys.path.append(os.path.dirname(hookPath))

            if kwargs:
                kwargs["core"] = self.core

            try:
                hook = __import__(hookName)
                result = getattr(hook, "main", lambda *args, **kwargs: None)(*args, **kwargs)
            except:
                msg = "An Error occuredwhile calling the %s hook:\n\n%s" % (
                    hookName,
                    traceback.format_exc(),
                )
                self.core.popup(msg)

            if hookName in sys.modules:
                del sys.modules[hookName]

            if os.path.exists(hookPath + "c"):
                try:
                    os.remove(hookPath + "c")
                except:
                    pass

        return result

    @err_catcher(name=__name__)
    def getCoreCallbacks(self) -> List[str]:
        """Get the list of core callback event names.
        
        Returns the standard set of callback events that are built into the Prism
        core system for import, export, render, playblast, publish, and save operations.
        
        Returns:
            List of core callback event names including prePublish, postExport,
            postImport, postPlayblast, postRender, postSaveScene, preExport,
            preImport, prePlayblast, preRender, preSaveScene, and postPublish
        """
        return [
            "prePublish",
            "postExport",
            "postImport",
            "postPlayblast",
            "postRender",
            "postSaveScene",
            "preExport",
            "preImport",
            "prePlayblast",
            "preRender",
            "preSaveScene",
            "postPublish",
        ]
