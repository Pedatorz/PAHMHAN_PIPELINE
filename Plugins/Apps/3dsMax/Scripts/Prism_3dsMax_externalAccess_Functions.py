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
from typing import Any, List, Tuple

from PrismUtils.Decorators import err_catcher_plugin as err_catcher


class Prism_3dsMax_externalAccess_Functions(object):
    """External access functions for 3ds Max plugin.
    
    Provides callbacks and utility functions accessible from outside 3ds Max,
    including autoback path retrieval and preset scene management.
    
    Attributes:
        core: PrismCore instance
        plugin: Plugin instance
    """

    def __init__(self, core: Any, plugin: Any) -> None:
        """Initialize external access functions and register callbacks.
        
        Args:
            core: PrismCore instance.
            plugin: Plugin instance.
        """
        self.core = core
        self.plugin = plugin
        self.core.registerCallback("getPresetScenes", self.getPresetScenes, plugin=self.plugin)

    @err_catcher(name=__name__)
    def getAutobackPath(self, origin: Any) -> Tuple[str, str]:
        """Get the 3ds Max autoback directory path and file filter string.
        
        Args:
            origin: Originating object.
        
        Returns:
            Tuple of (autoback_path, file_filter_string).
        """
        autobackpath = ""
        if self.core.appPlugin.pluginName == "3dsmax":
            autobackpath = self.executeScript(self, "getdir #autoback")
        else:
            if platform.system() == "Windows":
                autobackpath = os.path.join(
                    self.core.getWindowsDocumentsPath(), "3dsMax", "autoback"
                )

        fileStr = "3ds Max Scene File ("
        for i in self.sceneFormats:
            fileStr += "*%s " % i

        fileStr += ")"

        return autobackpath, fileStr

    @err_catcher(name=__name__)
    def getPresetScenes(self, presetScenes: List) -> None:
        """Add 3ds Max preset scenes to the preset scenes list.
        
        Args:
            presetScenes: List to append preset scenes to.
        """
        if os.getenv("PRISM_SHOW_DEFAULT_SCENEFILE_PRESETS", "1") != "1":
            return

        presetDir = os.path.join(self.pluginDirectory, "Presets")
        scenes = self.core.entities.getPresetScenesFromFolder(presetDir)
        presetScenes += scenes
