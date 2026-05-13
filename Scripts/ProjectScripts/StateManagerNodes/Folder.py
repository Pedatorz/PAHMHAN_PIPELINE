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

from typing import Any, Optional, Dict, List

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


class FolderClass(object):
    """State Manager node for organizing states into folders.
    
    Provides a hierarchical folder structure within the State Manager to organize
    import and export states. Folders can be nested and can contain any state type.
    
    Attributes:
        className (str): Node type identifier
        core (Any): Reference to PrismCore instance
        state (Any): Reference to QTreeWidgetItem representing this folder
        stateManager (Any): Reference to StateManager instance
        canSetVersion (bool): Whether this state supports version control
        listType (str): Type of states this folder contains ("Import" or "Export")
    """
    className = "Folder"

    def setup(
        self, 
        state: Any, 
        core: Any, 
        stateManager: Any, 
        stateData: Optional[Dict[str, Any]] = None, 
        listType: Optional[str] = None
    ) -> None:
        """Initialize the folder state.
        
        Sets up the folder node with core references, determines list type,
        and loads saved state data if provided.
        
        Args:
            state (Any): QTreeWidgetItem representing this folder in the state tree
            core (Any): PrismCore instance for accessing Prism functionality
            stateManager (Any): StateManager instance managing this state
            stateData (Dict[str, Any], optional): Saved state configuration to restore.
                Defaults to None.
            listType (str, optional): Type of states ("Import" or "Export"). If None,
                determined from active list. Defaults to None.
        """
        self.core = core
        self.state = state
        self.stateManager = stateManager
        self.canSetVersion = True
        self.e_name.setText(state.text(0))

        if listType is None:
            if stateManager.activeList == stateManager.tw_import:
                listType = "Import"
            else:
                listType = "Export"

        self.listType = listType
        self.connectEvents()
        self.core.callback("onStateStartup", self)

        if stateData is not None:
            self.loadData(stateData)

    def loadData(self, data: Dict[str, Any]) -> None:
        """Load saved state settings from data dictionary.
        
        Restores folder settings including name, list type, enable state,
        and expansion state from previously saved data.
        
        Args:
            data (Dict[str, Any]): Dictionary containing saved state settings with keys:
                - statename (str, optional): Name of the folder
                - listtype (str, optional): Type of states ("Import" or "Export")
                - stateenabled (int, optional): Check state for export folders
                - stateexpanded (bool, optional): Whether folder is expanded
        """
        if "statename" in data:
            self.e_name.setText(data["statename"])
        if "listtype" in data:
            self.listType = data["listtype"]
        if "stateenabled" in data and self.listType == "Export":
            if type(data["stateenabled"]) == int:
                self.state.setCheckState(
                    0, Qt.CheckState(data["stateenabled"]),
                )
        if "stateexpanded" in data:
            if not data["stateexpanded"]:
                self.stateManager.collapsedFolders.append(self.state)

        self.core.callback("onStateSettingsLoaded", self, data)

    def connectEvents(self) -> None:
        """Connect UI widget signals to handler methods.
        
        Sets up connections between the folder name input field and
        the handlers for name changes and scene saving.
        """
        self.e_name.textChanged.connect(self.nameChanged)
        self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)

    def nameChanged(self, text: str) -> None:
        """Handle folder name changes.
        
        Updates the tree widget item text when the folder name is changed.
        
        Args:
            text (str): New folder name
        """
        self.state.setText(0, text)

    def updateUi(self) -> bool:
        """Update the UI state.
        
        Called when the UI needs to be refreshed. For folders, no
        action is needed.
        
        Returns:
            bool: Always returns True indicating success
        """
        return True

    def preExecuteState(self, states: Optional[List[Any]] = None) -> List[List[Any]]:
        """Check for warnings before executing child states.
        
        Recursively collects warnings from all checked child states,
        including nested folders.
        
        Args:
            states (List[Any], optional): List of specific states to check.
                If None, checks all checked states. Defaults to None.
        
        Returns:
            List[List[Any]]: List of warning entries, where each entry is
                [state_name, [warning1, warning2, ...]]
        """
        warnings = [[self.state.text(0), []]]

        for i in range(self.state.childCount()):
            curState = self.state.child(i)
            if (states is None or id(curState) in [id(s) for s in states] or curState.ui.className == "Folder") and curState.checkState(0) == Qt.Checked:
                if curState.ui.className == "Folder":
                    warnings += curState.ui.preExecuteState(states=states)
                else:
                    warnings.append(curState.ui.preExecuteState())

        return warnings

    def executeState(self, parent: Any, useVersion: str = "next") -> List[Dict[str, Any]]:
        """Execute all checked child states recursively.
        
        Executes all checked child states in order, handling both regular
        states and nested folders. Tracks dependencies and submitted jobs
        for renderfarm submission.
        
        Args:
            parent (Any): Parent state or folder for dependency tracking
            useVersion (str, optional): Version strategy ("next" or specific version).
                Defaults to "next".
        
        Returns:
            List[Dict[str, Any]]: List of execution results, where each result
                contains {"state": state_object, "result": [status_message]}
        """
        result = []
        self.osSubmittedJobs = {}
        self.osDependencies = []
        self.dependencies = (parent.dependencies if parent else None) or []

        for i in range(self.state.childCount()):
            curState = self.state.child(i)
            if (self.stateManager.publishType == "execute" or curState.checkState(0) == Qt.Checked) and (curState.ui.className == "Folder" or curState in set(
                self.stateManager.execStates
            )):
                self.stateManager.curExecutedState = curState.ui
                if getattr(curState.ui, "canSetVersion", False):
                    exResult = curState.ui.executeState(
                        parent=self, useVersion=useVersion
                    )
                else:
                    exResult = curState.ui.executeState(parent=self)

                if curState.ui.className == "Folder":
                    result += exResult

                    for k in exResult:
                        if "publish paused" in k["result"][0]:
                            return result
                else:
                    result.append({"state": curState.ui, "result": exResult})

                    if exResult and "publish paused" in exResult[0]:
                        return result

        self.osSubmittedJobs = {}
        self.osDependencies = []
        self.dependencies = []
        return result

    def getStateProps(self) -> Dict[str, Any]:
        """Get current state settings for saving.
        
        Collects all folder settings including name, type, enable state,
        and expansion state into a dictionary for serialization.
        
        Returns:
            Dict[str, Any]: Dictionary containing state settings with keys:
                - statename (str): Name of the folder
                - listtype (str): Type of states ("Import" or "Export")
                - stateenabled (int): Check state value
                - stateexpanded (bool): Whether folder is expanded
        """
        stateProps = {
            "statename": self.e_name.text(),
            "listtype": self.listType,
            "stateenabled": self.core.getCheckStateValue(self.state.checkState(0)),
            "stateexpanded": self.state.isExpanded(),
        }
        self.core.callback("onStateGetSettings", self, stateProps)
        return stateProps
