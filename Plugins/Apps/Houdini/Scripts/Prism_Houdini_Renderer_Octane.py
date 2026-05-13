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


"""Houdini Octane renderer implementation for Prism.

Provides renderer-specific functionality for Octane ROP nodes
including node creation, camera setup, and parameter configuration.
"""

import os
from typing import Any, List, Optional, Union

import hou

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

label = "Octane"
ropNames = ["Octane_ROP"]


def isActive() -> bool:
    """Check if Octane renderer is available.
    
    Returns:
        True if Octane ROP node type exists.
    """
    return hou.nodeType(hou.ropNodeTypeCategory(), "Octane_ROP") is not None


def getCam(node: Any) -> Any:
    """Get camera node from renderer ROP.
    
    Args:
        node: Octane ROP node.
    
    Returns:
        Camera node object.
    """
    return hou.node(node.parm("HO_renderCamera").eval())


def getFormatFromNode(node: Any) -> str:
    """Get output format from renderer node.
    
    Args:
        node: Octane ROP node.
    
    Returns:
        File extension string.
    """
    ext = os.path.splitext(node.parm("HO_img_fileName").eval())[1]
    return ext


def createROP(origin: Any) -> None:
    """Create Octane ROP node.
    
    Args:
        origin: State manager origin object.
    """
    origin.node = origin.core.appPlugin.createRop("Octane_ROP")


def setAOVData(origin: Any, node: Any, aovNum: str, item: Any) -> None:
    """Set AOV data on node (not supported for Octane).
    
    Args:
        origin: State manager origin object.
        node: Octane ROP node.
        aovNum: AOV number string.
        item: Table widget item.
    """
    pass


def getDefaultPasses(origin: Any) -> None:
    """Get default render passes (not supported for Octane).
    
    Args:
        origin: State manager origin object.
    """
    pass


def addAOV(origin: Any, aovData: List) -> None:
    """Add AOV to renderer (not supported for Octane).
    
    Args:
        origin: State manager origin object.
        aovData: AOV data list.
    """
    pass


def refreshAOVs(origin: Any) -> None:
    """Refresh AOV list (not supported for Octane).
    
    Hides the passes group box.
    
    Args:
        origin: State manager origin object.
    """
    origin.gb_passes.setVisible(False)
    return


def deleteAOV(origin: Any, row: int) -> None:
    """Delete AOV (not supported for Octane).
    
    Args:
        origin: State manager origin object.
        row: Row index.
    """
    pass


def aovDbClick(origin: Any, event: Any) -> None:
    """Handle AOV double-click (not supported for Octane).
    
    Args:
        origin: State manager origin object.
        event: Mouse event.
    """
    pass


def setCam(origin: Any, node: Any, val: str) -> bool:
    """Set camera on renderer node.
    
    Args:
        origin: State manager origin object.
        node: Octane ROP node.
        val: Camera path string.
    
    Returns:
        True if successful.
    """
    return origin.core.appPlugin.setNodeParm(node, "HO_renderCamera", val=val)


def executeAOVs(origin: Any, outputName: str) -> Union[bool, List[str]]:
    """Execute AOV setup and set output path.
    
    Args:
        origin: State manager origin object.
        outputName: Output file path.
    
    Returns:
        True if successful, list of error messages otherwise.
    """
    if not origin.core.appPlugin.setNodeParm(origin.node, "HO_img_enable", val=True):
        return [origin.state.text(0) + ": error - Publish canceled"]

    parmPath = origin.core.appPlugin.getPathRelativeToProject(outputName) if origin.core.appPlugin.getUseRelativePath() else outputName
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "HO_img_fileName", val=parmPath
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]

    return True


def setResolution(origin: Any) -> Union[bool, List[str]]:
    """Set render resolution on node.
    
    Args:
        origin: State manager origin object.
    
    Returns:
        True if successful, list of error messages otherwise.
    """
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "HO_overrideCameraRes", val=True
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "HO_overrideResScale", val="user"
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "HO_overrideRes1", val=origin.sp_resWidth.value()
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "HO_overrideRes2", val=origin.sp_resHeight.value()
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]

    return True


def executeRender(origin: Any) -> bool:
    """Execute the render.
    
    Args:
        origin: State manager origin object.
    
    Returns:
        True if successful.
    """
    origin.node.parm("execute").pressButton()
    return True


def postExecute(origin: Any) -> bool:
    """Post-execution cleanup.
    
    Args:
        origin: State manager origin object.
    
    Returns:
        True if successful.
    """
    return True
