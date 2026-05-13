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


"""Houdini ImportFile node implementation for Prism.

Provides Prism::ImportFile HDA functionality for importing cached files
into Houdini scenes with path resolution and version management.
"""

import os
import logging
from typing import Any, Optional, Dict

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher as err_catcher

import hou

logger = logging.getLogger(__name__)


class Prism_Houdini_ImportFile(object):
    """Prism ImportFile HDA node manager.
    
    Manages Prism::ImportFile nodes for importing product caches
    with automatic path resolution and version tracking.
    
    Attributes:
        plugin: Houdini plugin instance.
        core: PrismCore instance.
        stateType: State type identifier.
        listType: List type for state manager.
    """
    
    def __init__(self, plugin: Any) -> None:
        """Initialize ImportFile node manager.
        
        Args:
            plugin: Houdini plugin instance.
        """
        self.plugin = plugin
        self.core = self.plugin.core
        self.stateType = "ImportFile"
        self.listType = "Import"

    @err_catcher(name=__name__)
    def getTypeName(self) -> str:
        """Get node type name.
        
        Returns:
            Node type name string.
        """
        return "prism::ImportFile"

    @err_catcher(name=__name__)
    def onNodeCreated(self, kwargs: Dict) -> None:
        """Handle node creation event.
        
        Sets node color to purple and creates initial state.
        Optionally enables selectable parameters based on environment variable.
        
        Args:
            kwargs: Houdini callback dict with 'node' key
        """
        self.plugin.onNodeCreated(kwargs)
        kwargs["node"].setColor(hou.Color(0.451, 0.369, 0.796))
        if os.getenv("PRISM_HOUDINI_IMPORT_SELECTABLE_PARMS") == "1":
            self.plugin.setNodeParm(kwargs["node"], "selectableInfo", 1)

        self.getStateFromNode(kwargs)

    @err_catcher(name=__name__)
    def onNodeDeleted(self, kwargs: Dict) -> None:
        """Handle node deletion event.
        
        Delegates to plugin to remove associated Prism state.
        
        Args:
            kwargs: Houdini callback dict with 'node' key
        """
        self.plugin.onNodeDeleted(kwargs)

    @err_catcher(name=__name__)
    def getStateFromNode(self, kwargs: Dict) -> Optional[Any]:
        """Get Prism state associated with node.
        
        Args:
            kwargs: Houdini callback dict with 'node' key
            
        Returns:
            ImportFile state instance or None
        """
        return self.plugin.getStateFromNode(kwargs)

    @err_catcher(name=__name__)
    def showInStateManagerFromNode(self, kwargs: Dict) -> None:
        """Show node's state in State Manager.
        
        Opens State Manager and navigates to this node's state.
        
        Args:
            kwargs: Houdini callback dict with 'node' key
        """
        self.plugin.showInStateManagerFromNode(kwargs)

    @err_catcher(name=__name__)
    def openInExplorerFromNode(self, kwargs: Dict) -> None:
        """Open file explorer to node's import path.
        
        Args:
            kwargs: Houdini callback dict with 'node' key
        """
        self.plugin.openInExplorerFromNode(kwargs)

    @err_catcher(name=__name__)
    def openProductBrowserFromNode(self, kwargs: Dict) -> None:
        """Open Product Browser to select import file.
        
        Opens browser, updates UI with selected path, and reorganizes
        state into appropriate folder hierarchy.
        
        Args:
            kwargs: Houdini callback dict with 'node' key
        """
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        state.ui.browse()
        self.refreshUiFromNode(kwargs, state)
        if state.parent() and state.parent().text(0) == "ImportNodes":
            self.updateStateParent(kwargs["node"], state)

    @err_catcher(name=__name__)
    def refreshUiFromNode(self, kwargs: Dict, state: Optional[Any] = None) -> None:
        """Refresh node parameters from import state.
        
        Updates node parameters (filepath, entity, product, version, comment,
        user, date) to match current state values. Handles both asset and shot
        entities with proper path resolution.
        
        Args:
            kwargs: Houdini callback dict with 'node' key
            state: Optional state instance (retrieved if not provided)
        """
        state = state or self.getStateFromNode(kwargs)
        path = state.ui.getImportPath(expand=False)
        parmPath = self.core.appPlugin.getPathRelativeToProject(path) if self.core.appPlugin.getUseRelativePath() else path

        if not self.core.appPlugin.isNodeValid(None, kwargs["node"]):
            return

        if parmPath != kwargs["node"].parm("filepath").eval():
            try:
                kwargs["node"].parm("filepath").set(parmPath)
            except:
                logger.debug(
                    'failed to set parm "filepath" on node %s' % kwargs["node"].path()
                )

        data = self.core.paths.getCachePathData(path)
        if data.get("type"):
            date = self.core.getFileModificationDate(
                os.path.dirname(path), validate=True
            )
            product = data.get("product", "")
            comment = data.get("comment", "")
            user = data.get("user", "")
        else:
            try:
                expandedPath = hou.text.expandString(path) or ""
            except:
                expandedPath = path or ""

            if os.path.exists(expandedPath):
                date = self.core.getFileModificationDate(expandedPath, validate=True)
            else:
                date = ""
            product = ""
            comment = ""
            user = ""

        versionLabel = data.get("version", "")
        if versionLabel == "master":
            versionLabel = self.core.products.getMasterVersionLabel(path)

        if data.get("type") == "asset":
            name = data.get("asset_path", "")
        elif data.get("type") == "shot":
            name = self.core.entities.getShotName(data)

        try:
            kwargs["node"].parm("entity").set(name)
        except:
            logger.debug(
                'failed to set parm "entity" on node %s' % kwargs["node"].path()
            )

        try:
            kwargs["node"].parm("product").set(product)
        except:
            logger.debug('failed to set parm "product" on node %s' % kwargs["node"].path())

        try:
            kwargs["node"].parm("version").set(versionLabel)
        except:
            logger.debug(
                'failed to set parm "version" on node %s' % kwargs["node"].path()
            )

        try:
            kwargs["node"].parm("comment").set(comment)
        except:
            logger.debug(
                'failed to set parm "comment" on node %s' % kwargs["node"].path()
            )

        try:
            kwargs["node"].parm("user").set(user)
        except:
            logger.debug('failed to set parm "user" on node %s' % kwargs["node"].path())

        try:
            kwargs["node"].parm("date").set(date)
        except:
            logger.debug('failed to set parm "date" on node %s' % kwargs["node"].path())

    @err_catcher(name=__name__)
    def setPathFromNode(self, kwargs: Dict) -> None:
        """Set import path from node parameter change.
        
        Updates state's import path, triggers import, and refreshes UI.
        
        Args:
            kwargs: Houdini callback dict with 'node' and 'script_value' keys
        """
        state = self.getStateFromNode(kwargs)
        state.ui.setImportPath(kwargs["script_value"])
        state.ui.importObject()
        state.ui.updateUi()
        self.refreshUiFromNode(kwargs)

    @err_catcher(name=__name__)
    def getParentFolder(self, create: bool = True, node: Optional[Any] = None) -> Optional[Any]:
        """Get or create parent folder state for node.
        
        Determines folder hierarchy from cache path data. For assets, uses
        asset path hierarchy. For shots, uses sequence/shot structure.
        Creates nested folder states as needed.
        
        Args:
            create: Create folders if they don't exist
            node: Node to get path from (determines hierarchy)
            
        Returns:
            Parent folder state or None
        """
        parents = ["ImportNodes"]
        if node:
            cachePath = node.parm("filepath").eval()
            data = self.core.paths.getCachePathData(cachePath)
            if data.get("type") == "asset":
                parents = (
                    os.path.dirname(data.get("asset_path", "")).replace("\\", "/").split("/")
                )
            elif data.get("type") == "shot":
                parents = [data["sequence"], data["shot"]]

        sm = self.core.getStateManager()
        if not sm:
            return

        state = None
        states = sm.states
        createdStates = []
        for parent in parents:
            cstate = self.findFolderState(states, parent)
            if cstate:
                state = cstate
            else:
                if not create:
                    return state

                stateData = {
                    "statename": parent,
                    "listtype": "Import",
                    "stateexpanded": True,
                }
                state = sm.createState("Folder", stateData=stateData, parent=state)
                createdStates.append(state)

            states = [state.child(idx) for idx in range(state.childCount())]

        for cs in createdStates:
            cs.setExpanded(True)

        return state

    @err_catcher(name=__name__)
    def updateStateParent(self, node: Any, state: Any) -> None:
        """Update state's parent folder based on import path.
        
        Moves state to appropriate folder hierarchy based on cache path.
        Removes empty parent folders after move.
        
        Args:
            node: Houdini node
            state: Import state to reparent
        """
        parent = self.getParentFolder(node=node)
        if parent is not state.parent():
            prevParent = state.parent()
            s = prevParent.takeChild(prevParent.indexOfChild(state))
            parent.addChild(s)
            sm = self.core.getStateManager()
            if prevParent:
                while True:
                    nextParent = prevParent.parent()
                    if prevParent.childCount() == 0:
                        sm.deleteState(prevParent)

                    if nextParent:
                        prevParent = nextParent
                    else:
                        return

    @err_catcher(name=__name__)
    def findFolderState(self, states: list, name: str) -> Optional[Any]:
        """Find folder state by name in state list.
        
        Args:
            states: List of states to search
            name: Folder name to find
            
        Returns:
            Folder state or None
        """
        for state in states:
            if state.ui.listType != "Import" or state.ui.className != "Folder":
                continue

            if state.ui.e_name.text() == name:
                return state

    @err_catcher(name=__name__)
    def getNodeDescription(self) -> str:
        """Get node description for network editor display.
        
        Returns product name and version on separate lines.
        
        Returns:
            Description string with product and version
        """
        node = hou.pwd()
        product = node.parm("product").eval()
        version = node.parm("version").eval()

        descr = product + "\n" + version
        return descr

    @err_catcher(name=__name__)
    def abcGroupsToggled(self, kwargs: Dict) -> None:
        """Handle Alembic groups parameter toggle.
        
        Updates Alembic import node's groupnames parameter based on
        the groupsAbc toggle state.
        
        Args:
            kwargs: Houdini callback dict with 'node' key
        """
        state = self.getStateFromNode(kwargs)
        if not state:
            return

        abcNode = state.ui.fileNode
        if not abcNode:
            return

        if abcNode.type().name() != "alembic":
            return

        if kwargs["node"].parm("groupsAbc").eval():
            abcNode.parm("groupnames").set(4)
        else:
            abcNode.parm("groupnames").set(0)
