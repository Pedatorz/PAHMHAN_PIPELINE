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

"""Houdini 3Delight renderer implementation for Prism.

Provides renderer-specific functionality for 3Delight ROP nodes
including AOV management, NSI export, deep EXR support, and parameter configuration.
"""

import os
import time
from typing import Any, List, Optional, Union

import hou

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


label = "3Delight"
ropNames = ["3Delight"]


def isActive() -> bool:
    """Check if 3Delight renderer is available.
    
    Returns:
        True if 3Delight node type exists.
    """
    return hou.nodeType(hou.ropNodeTypeCategory(), ropNames[0]) is not None


def activated(origin: Any) -> None:
    """Called when 3Delight renderer is activated.
    
    Adds deep EXR format options to format dropdown.
    
    Args:
        origin: State manager origin object.
    """
    deep = ".exr (deep)"
    idx = origin.cb_format.findText(deep)
    if idx == -1:
        origin.cb_format.addItem(deep)

    deep = ".exr (deep alpha only)"
    idx = origin.cb_format.findText(deep)
    if idx == -1:
        origin.cb_format.addItem(deep)


def deactivated(origin: Any) -> None:
    """Called when 3Delight renderer is deactivated.
    
    Removes deep EXR format options from format dropdown.
    
    Args:
        origin: State manager origin object.
    """
    deep = ".exr (deep)"
    idx = origin.cb_format.findText(deep)
    if idx != -1:
        origin.cb_format.removeItem(idx)

    deep = ".exr (deep alpha only)"
    idx = origin.cb_format.findText(deep)
    if idx != -1:
        origin.cb_format.removeItem(idx)


def getCam(node: Any) -> Any:
    """Get camera node from renderer ROP.
    
    Args:
        node: 3Delight ROP node.
    
    Returns:
        Camera node object.
    """
    return hou.node(node.parm("camera").eval())


def getFormatFromNode(node: Any) -> str:
    """Get output format from renderer node.
    
    Converts 3Delight format tokens to file extensions.
    
    Args:
        node: 3Delight ROP node.
    
    Returns:
        File extension string.
    """
    fmt = node.parm("default_image_format").eval()
    if fmt == "deepexr":
        fmt = ".exr (deep)"
    elif fmt == "deepalphaexr":
        fmt = ".exr (deep alpha only)"
    else:
        fmt = "." + fmt

    return fmt


def createROP(origin: Any) -> None:
    """Create 3Delight ROP node.
    
    Args:
        origin: State manager origin object.
    """
    origin.node = origin.core.appPlugin.createRop(ropNames[0])


def setAOVData(origin: Any, node: Any, aovNum: str, item: Any) -> None:
    """Set AOV data on node from table widget item.
    
    Args:
        origin: State manager origin object.
        node: 3Delight ROP node.
        aovNum: AOV number string.
        item: Table widget item with AOV data.
    """
    origin.core.appPlugin.setNodeParm(node, "aov_name_" + aovNum, val=item.text())


def getDefaultPasses(origin: Any) -> List:
    """Get default render passes for 3Delight.
    
    Retrieves from config or plugin defaults.
    
    Args:
        origin: State manager origin object.
    
    Returns:
        List of default AOV configurations.
    """
    aovs = origin.core.getConfig(
        "defaultpasses", "houdini_3delight", configPath=origin.core.prismIni
    )
    if aovs is None:
        aovs = origin.core.appPlugin.renderPasses["houdini_3delight"]

    return aovs


def addAOV(origin: Any, aovData: List) -> None:
    """Add AOV to 3Delight renderer.
    
    Creates new AOV with name.
    
    Args:
        origin: State manager origin object.
        aovData: List containing [aov_name].
    """
    passNum = origin.node.parm("aov").evalAsInt() + 1
    origin.core.appPlugin.setNodeParm(origin.node, "aov", val=passNum)
    origin.core.appPlugin.setNodeParm(
        origin.node, "aov_name_" + str(passNum), val=aovData[0]
    )


def refreshAOVs(origin: Any) -> None:
    """Refresh AOV list in UI table.
    
    Reads AOVs from node and populates table widget.
    
    Args:
        origin: State manager origin object.
    """
    origin.tw_passes.horizontalHeaderItem(0).setText("Name")
    origin.tw_passes.setColumnHidden(1, True)

    passNum = 0

    if origin.node is None:
        return

    for i in range(origin.node.parm("aov").eval()):
        if origin.node.parm("active_layer_" + str(i + 1)).eval() == 0:
            continue

        labelParm = origin.node.parm("aov_name_" + str(i + 1))
        passTypeToken = labelParm.eval()
        passTypeName = QTableWidgetItem(passTypeToken)
        passNItem = QTableWidgetItem(str(i))
        origin.tw_passes.insertRow(passNum)
        origin.tw_passes.setItem(passNum, 0, passTypeName)
        origin.tw_passes.setItem(passNum, 2, passNItem)
        passNum += 1


def deleteAOV(origin: Any, row: int) -> None:
    """Delete AOV from renderer.
    
    Removes AOV multiparm instance.
    
    Args:
        origin: State manager origin object.
        row: Row index in table widget.
    """
    pid = int(origin.tw_passes.item(row, 2).text())
    origin.node.parm("aov").removeMultiParmInstance(pid)


def aovDbClick(origin: Any, event: Any) -> None:
    """Handle AOV double-click event.
    
    Args:
        origin: State manager origin object.
        event: Mouse event.
    """
    if origin.node is None or event.button() != Qt.LeftButton:
        origin.tw_passes.mouseDbcEvent(event)
        return

    curItem = origin.tw_passes.itemFromIndex(origin.tw_passes.indexAt(event.pos()))
    if curItem is not None and curItem.column() == 0:
        typeMenu = QMenu()

        aovNames = getDefaultPasses(origin)
        for idx, aovName in enumerate(aovNames):
            tAct = QAction(aovName, origin)
            tAct.triggered.connect(lambda z=None, x=curItem, y=aovName: x.setText(y))
            tAct.triggered.connect(lambda z=None, x=curItem: origin.setPassData(x))
            typeMenu.addAction(tAct)

        typeMenu.setStyleSheet(origin.stateManager.parent().styleSheet())
        typeMenu.exec_(QCursor.pos())
    else:
        origin.tw_passes.mouseDbcEvent(event)


def setCam(origin: Any, node: Any, val: str) -> bool:
    """Set camera on renderer node.
    
    Args:
        origin: State manager origin object.
        node: 3Delight ROP node.
        val: Camera path string.
    
    Returns:
        True if successful.
    """
    return origin.core.appPlugin.setNodeParm(node, "camera", val=val)


def executeAOVs(origin: Any, outputName: str) -> Union[bool, List[str]]:
    """Execute AOV setup and configure output paths.
    
    Handles NSI export, deep EXR setup, and AOV output paths.
    
    Args:
        origin: State manager origin object.
        outputName: Primary render output file path.
    
    Returns:
        True if successful, list of error messages otherwise.
    """
    if (
        not origin.gb_submit.isHidden()
        and origin.gb_submit.isChecked()
        and origin.cb_manager.currentText() == "Deadline"
        and origin.chb_rjNSIs.isChecked()
    ):
        nsi = True

        nsiOutput = getNsiOutputPath(origin, outputName)
        parmPath = origin.core.appPlugin.getPathRelativeToProject(nsiOutput) if origin.core.appPlugin.getUseRelativePath() else nsiOutput
        if not origin.core.appPlugin.setNodeParm(
            origin.node, "default_export_nsi_filename", val=parmPath
        ):
            return [
                origin.state.text(0)
                + ": error - could not set filename. Publish canceled"
            ]

    else:
        nsi = False

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "display_rendered_images", val=False
    ):
        return [
            origin.state.text(0)
            + ": error - could not set display images. Publish canceled"
        ]

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "save_rendered_images", val=False
    ):
        return [
            origin.state.text(0)
            + ": error - could not set save images. Publish canceled"
        ]

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "display_and_save_rendered_images", val=not nsi
    ):
        return [
            origin.state.text(0)
            + ": error - could not set display and save images. Publish canceled"
        ]

    if not origin.core.appPlugin.setNodeParm(origin.node, "output_nsi_files", val=nsi):
        return [
            origin.state.text(0)
            + ": error - could not set nsi export. Publish canceled"
        ]

    parmPath = origin.core.appPlugin.getPathRelativeToProject(outputName) if origin.core.appPlugin.getUseRelativePath() else outputName
    if not origin.core.appPlugin.setNodeParm(
        origin.node, "default_image_filename", val=parmPath
    ):
        return [
            origin.state.text(0) + ": error - could not set filename. Publish canceled"
        ]

    base, ext = os.path.splitext(outputName)
    if ext == ".exr":
        if origin.cb_format.currentText() == ".exr (deep)":
            formatVal = "deepexr"
        elif origin.cb_format.currentText() == ".exr (deep alpha only)":
            formatVal = "deepalphaexr"
        else:
            formatVal = "exr"
    elif ext == ".png":
        formatVal = "png"
    else:
        return [
            origin.state.text(0) + ": error - invalid image format. Publish canceled"
        ]

    if not origin.core.appPlugin.setNodeParm(
        origin.node, "default_image_format", val=formatVal
    ):
        return [
            origin.state.text(0) + ": error - could not set format. Publish canceled"
        ]

    return True


def setResolution(origin: Any) -> Union[bool, List[str]]:
    """Set render resolution on node.
    
    Args:
        origin: State manager origin object.
    
    Returns:
        True if successful, list of error messages otherwise.
    """
    cam = getCam(origin.node)
    width = origin.sp_resWidth.value()
    height = origin.sp_resHeight.value()
    if not origin.core.appPlugin.setNodeParm(cam, "resx", val=width):
        return [origin.state.text(0) + ": error - Publish canceled"]

    if not origin.core.appPlugin.setNodeParm(cam, "resy", val=height):
        return [origin.state.text(0) + ": error - Publish canceled"]

    return True


def executeRender(origin: Any) -> Union[bool, str]:
    """Execute the render.
    
    Runs render or generates NSI archive based on configuration.
    
    Args:
        origin: State manager origin object.
    
    Returns:
        True if successful, error message string otherwise.
    """
    if origin.node.parm("sequence_render"):
        origin.node.parm("sequence_render").pressButton()
    else:
        origin.node.parm("execute").pressButton()

    while origin.node.parm("rendering").eval() or (
        origin.node.parm("sequence_rendering")
        and origin.node.parm("sequence_rendering").eval()
    ):
        time.sleep(1)

    return True


def postExecute(origin: Any) -> bool:
    """Post-execution cleanup.
    
    Args:
        origin: State manager origin object.
    
    Returns:
        True if successful.
    """
    return True


def getNsiRenderScript() -> str:
    """Get NSI render script for command-line rendering.
    
    Returns:
        Python script string for NSI rendering.
    """
    script = """

import os
import sys
import subprocess

imgOutput = sys.argv[-1]
nsiOutput = sys.argv[-2]
endFrame = int(sys.argv[-3])
startFrame = int(sys.argv[-4])

dlbase = os.getenv("DELIGHT")
dlpath = os.path.join(dlbase, "bin", "renderdl")

for frame in range(startFrame, (endFrame+1)):
    nsi = nsiOutput.replace("####", "%04d" % (frame))
    output = imgOutput.replace("####", "%04d" % (frame))
    args = [dlpath, nsi]
    print("command args: %s" % (args))
    p = subprocess.Popen(args)
    p.communicate()
    if p.returncode:
        raise RuntimeError("renderer exited with code %s" % p.returncode)
    elif not os.path.exists(output) and "<aov>" not in output:
        raise RuntimeError("expected output doesn't exist %s" % (output))
    else:
        print("successfully rendered frame %s" % (frame))

print("task completed successfully")

"""
    return script


def getCleanupScript() -> str:
    """Get cleanup script for NSI file removal.
    
    Returns:
        Python script string for post-render NSI cleanup.
    """
    script = """

import os
import sys
import shutil

nsiOutput = sys.argv[-1]

delDir = os.path.dirname(nsiOutput)
if os.path.basename(delDir) != "_nsi":
    raise RuntimeError("invalid nsi directory: %s" % (delDir))

if os.path.exists(delDir):
    shutil.rmtree(delDir)
    print("task completed successfully")
else:
    print("directory doesn't exist")

"""
    return script


def getNsiOutputPath(origin: Any, renderOutputPath: str) -> str:
    """Get NSI output path for scene export.
    
    Args:
        origin: State manager origin object.
        renderOutputPath: Primary render output path.
    
    Returns:
        NSI file output path string.
    """
    jobOutputFile = os.path.join(
        os.path.dirname(renderOutputPath), "_nsi", os.path.basename(renderOutputPath)
    )
    jobOutputFile = os.path.splitext(jobOutputFile)[0] + ".nsi"
    return jobOutputFile
