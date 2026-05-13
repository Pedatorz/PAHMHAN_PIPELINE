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
import platform
from typing import Any, List, Optional, Tuple

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_AfterEffects_externalAccess_Functions(object):
    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize external access functions component.
        
        Registers stylesheet and preset scene callback for AfterEffects plugin.
        
        Args:
            core: Prism core instance
            plugin: Plugin instance
        """
        self.core = core
        self.plugin = plugin
        ssheetPath = os.path.join(
            self.pluginDirectory,
            "UserInterfaces",
            "AfterEffectsStyleSheet"
        )
        self.core.registerStyleSheet(ssheetPath)
        self.core.registerCallback("getPresetScenes", self.getPresetScenes, plugin=self.plugin)

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin: Any) -> Tuple[str, str]:
        """Get autobackup path and file filter string for After Effects.
        
        Args:
            origin: Calling origin object
            
        Returns:
            Tuple of (autobackup directory path, file filter string for dialogs)
        """
        autobackpath = ""
        if platform.system() == "Windows":
            autobackpath = os.path.join(
                self.core.getWindowsDocumentsPath(), "Adobe", "After Effects"
            )

        fileStr = "AfterEffects Scene File ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def copySceneFile(self, origin: Any, origFile: str, targetPath: str, mode: str = "copy") -> None:
        """Copy scene file to target location.
        
        Currently not implemented for After Effects plugin.
        
        Args:
            origin: Calling origin object
            origFile: Source file path
            targetPath: Destination file path
            mode: Copy mode ("copy" or other)
        """
        pass

    @err_catcher(name=__name__)
    def getPresetScenes(self, presetScenes: List[Any]) -> None:
        """Add plugin preset scenes to the preset scenes list.
        
        Loads preset .aep files from plugin Presets directory and adds them to
        the provided list if PRISM_SHOW_DEFAULT_SCENEFILE_PRESETS is enabled.
        
        Args:
            presetScenes: List to append preset scene dictionaries to
        """
        if os.getenv("PRISM_SHOW_DEFAULT_SCENEFILE_PRESETS", "1") != "1":
            return
        
        presetDir = os.path.join(self.pluginDirectory, "Presets")
        scenes = self.core.entities.getPresetScenesFromFolder(presetDir)
        presetScenes += scenes
