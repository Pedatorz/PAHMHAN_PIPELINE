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
from typing import Any, Optional, Dict

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher

logger = logging.getLogger(__name__)


class MetaDataWidget(QGroupBox):
    """Widget for editing metadata associated with project entities.
    
    Provides an interface for viewing and editing key-value metadata pairs
    that can be attached to entities like assets, shots, or versions. Each
    metadata item consists of a key, value, and visibility flag.
    
    Attributes:
        core: The Prism core instance
        entityData: Dictionary containing entity information
        w_add: Container widget for the add button
        b_add: Button to add new metadata items
        lo_add: Layout for the add button container
        lo_main: Main vertical layout for the widget
    """
    
    def __init__(self, core: Any, entityData: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the metadata widget.
        
        Args:
            core: The Prism core instance
            entityData: Entity data dictionary containing entity information
        """
        QGroupBox.__init__(self)

        self.core = core
        self.core.parentWindow(self)
        self.entityData = entityData

        self.loadLayout()
        self.connectEvents()
        self.loadMetaData(entityData)

    @err_catcher(name=__name__)
    def loadLayout(self) -> None:
        """Create and configure the widget layout.
        
        Sets up the main layout with an add button at the top for creating
        new metadata items.
        """
        self.w_add = QWidget()
        self.b_add = QToolButton()
        self.lo_add = QHBoxLayout()
        self.w_add.setLayout(self.lo_add)
        self.lo_add.addStretch()
        self.lo_add.addWidget(self.b_add)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_add.setIcon(icon)
        self.b_add.setIconSize(QSize(20, 20))
        self.b_add.setToolTip("Add Item")
        if self.core.appPlugin.pluginName != "Standalone":
            self.b_add.setStyleSheet(
                "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 1px; }"
            )

        self.lo_main = QVBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.w_add)
        self.setTitle("Meta Data")

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect widget signals to their handler methods."""
        self.b_add.clicked.connect(self.addItem)

    @err_catcher(name=__name__)
    def loadMetaData(self, entityData: Optional[Dict[str, Any]]) -> None:
        """Load metadata from entity data and populate the widget.
        
        Args:
            entityData: Entity data dictionary containing metadata
        """
        metaData = self.core.entities.getMetaData(entityData)
        for key in sorted(metaData):
            self.addItem(key, metaData[key]["value"], metaData[key]["show"])

    @err_catcher(name=__name__)
    def addItem(self, key: Optional[str] = None, value: Optional[Any] = None, 
                show: bool = False) -> Any:
        """Add a new metadata item to the widget.
        
        Args:
            key: The metadata key name
            value: The metadata value
            show: Whether to show the item in preview
            
        Returns:
            The created MetaDataItem widget
        """
        item = MetaDataItem(self.core)
        item.removed.connect(self.removeItem)
        if key:
            item.setKey(key)

        if value:
            item.setValue(value)

        item.setShow(show)

        self.lo_main.insertWidget(self.lo_main.count() - 1, item)
        return item

    @err_catcher(name=__name__)
    def removeItem(self, item: Any) -> None:
        """Remove a metadata item from the widget.
        
        Args:
            item: The MetaDataItem widget to remove
        """
        idx = self.lo_main.indexOf(item)
        if idx != -1:
            w = self.lo_main.takeAt(idx)
            if w.widget():
                w.widget().deleteLater()

    @err_catcher(name=__name__)
    def getMetaData(self) -> Dict[str, Dict[str, Any]]:
        """Get all metadata from the widget items.
        
        Returns:
            Dictionary mapping metadata keys to dictionaries containing
            'value' and 'show' keys
        """
        data = {}
        for idx in reversed(range(self.lo_main.count())):
            w = self.lo_main.itemAt(idx)
            widget = w.widget()
            if widget:
                if isinstance(widget, MetaDataItem):
                    if not widget.key():
                        continue

                    data[widget.key()] = {
                        "value": widget.value(),
                        "show": widget.show(),
                    }

        return data

    @err_catcher(name=__name__)
    def save(self, entityData: Optional[Dict[str, Any]] = None) -> None:
        """Save metadata to the entity.
        
        Args:
            entityData: Entity data dictionary, or None to use the widget's entityData
        """
        if not entityData:
            entityData = self.entityData

        data = self.getMetaData()
        self.core.entities.setMetaData(entityData, data)


class MetaDataItem(QWidget):
    """Individual metadata key-value pair editor widget.
    
    Provides input fields for editing a single metadata entry with key,
    value, and visibility flag. Emits a signal when the item should be removed.
    
    Attributes:
        core: The Prism core instance
        e_key: Line edit for the metadata key
        e_value: Line edit for the metadata value
        chb_show: Checkbox for visibility in preview
        b_remove: Button to remove this item
        removed: Signal emitted when item should be removed
    """

    removed = Signal(object)

    def __init__(self, core: Any) -> None:
        """Initialize the metadata item widget.
        
        Args:
            core: The Prism core instance
        """
        super(MetaDataItem, self).__init__()
        self.core = core
        self.loadLayout()

    @err_catcher(name=__name__)
    def loadLayout(self) -> None:
        """Create and configure the item layout with input fields and remove button."""
        self.e_key = QLineEdit()
        self.e_key.setPlaceholderText("Key")
        self.e_value = QLineEdit()
        self.e_value.setPlaceholderText("Value")
        self.chb_show = QCheckBox("show")
        self.chb_show.setToolTip("Show item in preview")
        self.b_remove = QToolButton()
        self.b_remove.clicked.connect(lambda: self.removed.emit(self))

        self.lo_main = QHBoxLayout()
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.lo_main)
        self.lo_main.addWidget(self.e_key)
        self.lo_main.addWidget(self.e_value)
        self.lo_main.addWidget(self.chb_show)
        self.lo_main.addWidget(self.b_remove)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_remove.setIcon(icon)
        self.b_remove.setIconSize(QSize(20, 20))
        self.b_remove.setToolTip("Delete")
        if self.core.appPlugin.pluginName != "Standalone":
            self.b_remove.setStyleSheet(
                "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 1px; }"
            )

    @err_catcher(name=__name__)
    def key(self) -> str:
        """Get the metadata key.
        
        Returns:
            The current key text
        """
        return self.e_key.text()

    @err_catcher(name=__name__)
    def value(self) -> str:
        """Get the metadata value.
        
        Returns:
            The current value text
        """
        return self.e_value.text()

    @err_catcher(name=__name__)
    def show(self) -> bool:
        """Get the visibility flag.
        
        Returns:
            True if the item should be shown in preview, False otherwise
        """
        return self.chb_show.isChecked()

    @err_catcher(name=__name__)
    def setKey(self, key: str) -> None:
        """Set the metadata key.
        
        Args:
            key: The key text to set
        """
        return self.e_key.setText(key)

    @err_catcher(name=__name__)
    def setValue(self, value: Any) -> None:
        """Set the metadata value.
        
        Args:
            value: The value to set (converted to string)
        """
        return self.e_value.setText(str(value))

    @err_catcher(name=__name__)
    def setShow(self, show: bool) -> None:
        """Set the visibility flag.
        
        Args:
            show: True to show the item in preview, False to hide it
        """
        return self.chb_show.setChecked(show)
