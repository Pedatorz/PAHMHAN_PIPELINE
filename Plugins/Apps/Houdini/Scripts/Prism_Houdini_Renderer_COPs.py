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


"""Houdini COPs (Compositing) renderer implementation for Prism.

Provides renderer-specific functionality for COPs ROP nodes
including node creation and parameter configuration.
"""

import os
from typing import Any, List, Union

import hou

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


label = "COPs"
ropNames = ["rop_image"]
hasCamera = False
hasResolution = False


def isActive() -> bool:
    """Check if COPs renderer is available.
    
    Returns:
        True if renderer is active.
    """
    return True


def getFormatFromNode(node: Any) -> str:
    """Get output format from renderer node.
    
    Args:
        node: COPs ROP node.
    
    Returns:
        File extension string.
    """
    ext = os.path.splitext(node.parm("copoutput").eval())[1]
    return ext


def createROP(origin: Any) -> None:
    """Create COPs ROP node in compositing context.
    
    Args:
        origin: State manager origin object.
    """
    nwPane = origin.core.appPlugin.getNetworkPane()
    if not nwPane:
        origin.node = None
        return

    parent = nwPane.pwd()
    if parent.type().childTypeCategory().name() != "Cop":
        origin.node = None
        return

    origin.node = origin.core.appPlugin.createRop("rop_image", parent=parent)


def refreshAOVs(origin: Any) -> None:
    """Refresh AOV list (not supported for COPs).
    
    Hides the passes group box.
    
    Args:
        origin: State manager origin object.
    """
    origin.gb_passes.setVisible(False)
    return


def deleteAOV(origin: Any, row: int) -> None:
    """Delete AOV (not supported for COPs).
    
    Args:
        origin: State manager origin object.
        row: Row index.
    """
    pass


def aovDbClick(origin: Any, event: Any) -> None:
    """Handle AOV double-click (not supported for COPs).
    
    Args:
        origin: State manager origin object.
        event: Mouse event.
    """
    pass


def executeAOVs(origin: Any, outputName: str) -> Union[bool, List[str]]:
    """Execute AOV setup and set output path.
    
    Args:
        origin: State manager origin object.
        outputName: Output file path.
    
    Returns:
        True if successful, list of error messages otherwise.
    """
    parmPath = origin.core.appPlugin.getPathRelativeToProject(outputName) if origin.core.appPlugin.getUseRelativePath() else outputName
    if not origin.core.appPlugin.setNodeParm(origin.node, "copoutput", val=parmPath):
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
        origin.node, "setres", val=True
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "res1", val=origin.sp_resWidth.value()
    ):
        return [origin.state.text(0) + ": error - Publish canceled"]
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "res2", val=origin.sp_resHeight.value()
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
