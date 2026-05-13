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
from typing import Any, Optional, List, Dict, Tuple

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import MetaDataWidget
from PrismUtils.Decorators import err_catcher
from UserInterfaces import EditShot_ui


class EditShot(QDialog, EditShot_ui.Ui_dlg_EditShot):
    """Dialog for creating and editing shots in the project.
    
    This class provides a comprehensive interface for:
    - Creating new shots with episode, sequence, and shot names
    - Editing existing shot properties (name, frame range, preview)
    - Setting shot metadata and frame ranges
    - Managing shot thumbnails/previews
    - Creating task presets for new shots
    
    Signals:
        shotCreated: Emitted when a new shot is created (passes shot data dict)
        shotSaved: Emitted when shot information is saved
        nextClicked: Emitted when Next button is clicked after creation
    
    Attributes:
        core: The Prism core instance
        shotData: Dictionary containing shot information (episode, sequence, shot)
        sequences: List of available sequence names
        episodes: List of available episode names
        useEpisodes: Whether the project uses episodes
        shotPrvXres: Preview image width (250px)
        shotPrvYres: Preview image height (141px)
        pmap: Current preview pixmap
    """
    
    shotCreated = Signal(object)
    shotSaved = Signal()
    nextClicked = Signal()

    def __init__(self, core: Any, shotData: Optional[Dict[str, Any]], sequences: List[str], parent: Optional[Any] = None, episodes: Optional[List[str]] = None, editEpisode: bool = False) -> None:
        """Initialize the EditShot dialog.
        
        Args:
            core: The Prism core instance providing access to pipeline functionality
            shotData: Dictionary with shot information, or None for creating new shot
            sequences: List of available sequence names for selection
            parent: Parent widget for this dialog
            episodes: List of available episode names for selection
            editEpisode: Whether the dialog is in episode edit mode
        """
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.shotData = shotData or {}
        self.sequences = sequences
        self.episodes = episodes or []
        self.core.parentWindow(self, parent=parent)
        self.shotPrvXres = 250
        self.shotPrvYres = 141
        self.useEpisodes = self.core.getConfig(
            "globals",
            "useEpisodes",
            config="project",
        ) or False

        self.loadLayout()

        self.imgPath = ""
        self.btext = "Next"

        self.core.callback(
            name="onShotDlgOpen", args=[self, shotData]
        )

        self.loadData()
        self.connectEvents()

    @err_catcher(name=__name__)
    def connectEvents(self) -> None:
        """Connect UI signals to their respective slot methods.
        
        Connects button clicks, text changes, and mouse events to their
        corresponding handler methods.
        """
        self.b_showEpisodes.clicked.connect(self.showEpisodes)
        self.b_showSeq.clicked.connect(self.showSequences)
        self.buttonBox.clicked.connect(self.buttonboxClicked)
        self.e_shotName.textEdited.connect(lambda x: self.validate(self.e_shotName))
        self.e_sequence.textEdited.connect(lambda x: self.validate(self.e_sequence))
        self.e_episode.textEdited.connect(lambda x: self.validate(self.e_episode))
        self.l_shotPreview.mouseReleaseEvent = self.previewMouseReleaseEvent
        self.l_shotPreview.customContextMenuRequested.connect(self.rclShotPreview)
        self.b_deleteShot.clicked.connect(self.deleteShot)

    @err_catcher(name=__name__)
    def loadLayout(self) -> None:
        """Setup and configure the dialog layout based on project settings.
        
        Adjusts visibility of episode and sequence controls based on availability,
        and adds the metadata widget to the layout.
        """
        if self.useEpisodes and len(self.episodes) == 0:
            self.b_showEpisodes.setVisible(False)

        if len(self.sequences) == 0:
            self.b_showSeq.setVisible(False)

        self.b_deleteShot.setVisible(False)
        self.metaWidget = MetaDataWidget.MetaDataWidget(self.core, self.shotData)
        self.layout().insertWidget(self.layout().count() - 2, self.metaWidget)

    @err_catcher(name=__name__)
    def showEpisodes(self) -> None:
        """Display a context menu with available episode names.
        
        Creates and shows a popup menu containing all episodes,
        allowing the user to select an episode for the shot.
        """
        smenu = QMenu(self)

        for i in self.episodes:
            sAct = QAction(i, self)
            sAct.triggered.connect(lambda x=None, t=i: self.episodeClicked(t))
            smenu.addAction(sAct)

        smenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def episodeClicked(self, ep: str) -> None:
        """Handle episode selection from the menu.
        
        Args:
            ep: The episode name that was clicked
        """
        self.e_episode.setText(ep)

    @err_catcher(name=__name__)
    def showSequences(self) -> None:
        """Display a context menu with available sequence names.
        
        Creates and shows a popup menu containing all sequences,
        allowing the user to select a sequence for the shot.
        """
        smenu = QMenu(self)

        for i in self.sequences:
            sAct = QAction(i, self)
            sAct.triggered.connect(lambda x=None, t=i: self.seqClicked(t))
            smenu.addAction(sAct)

        smenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def seqClicked(self, seq: str) -> None:
        """Handle sequence selection from the menu.
        
        Args:
            seq: The sequence name that was clicked
        """
        self.e_sequence.setText(seq)

    @err_catcher(name=__name__)
    def previewMouseReleaseEvent(self, event: Any) -> None:
        """Handle mouse release events on the preview label.
        
        Args:
            event: The mouse event object
            
        Opens the preview context menu when the preview is left-clicked.
        """
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                self.rclShotPreview()

    @err_catcher(name=__name__)
    def rclShotPreview(self, pos: Optional[Any] = None) -> None:
        """Display context menu for the shot preview.
        
        Args:
            pos: Position where the context menu should appear (unused, uses cursor pos)
            
        Provides options to:
        - Capture thumbnail from screen
        - Browse for thumbnail file
        - Paste thumbnail from clipboard
        """
        rcmenu = QMenu(self)

        copAct = QAction("Capture thumbnail", self)
        copAct.triggered.connect(self.capturePreview)
        rcmenu.addAction(copAct)

        copAct = QAction("Browse thumbnail...", self)
        copAct.triggered.connect(self.browsePreview)
        rcmenu.addAction(copAct)

        clipAct = QAction("Paste thumbnail from clipboard", self)
        clipAct.triggered.connect(self.pastePreviewFromClipboard)
        rcmenu.addAction(clipAct)

        rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def capturePreview(self) -> None:
        """Capture a screen area as the shot preview thumbnail.
        
        Opens a screen area selection tool and sets the captured image
        as the shot preview, scaled to the preview dimensions.
        """
        from PrismUtils import ScreenShot

        previewImg = ScreenShot.grabScreenArea(self.core)

        if previewImg:
            previewImg = self.core.media.scalePixmap(
                previewImg,
                self.shotPrvXres,
                self.shotPrvYres,
            )
            self.setPixmap(previewImg)

    @err_catcher(name=__name__)
    def pastePreviewFromClipboard(self) -> None:
        """Set the shot preview from an image in the clipboard.
        
        Retrieves an image from the clipboard and sets it as the shot preview,
        scaled to the preview dimensions. Shows a popup if no image is found.
        """
        pmap = self.core.media.getPixmapFromClipboard()
        if not pmap:
            self.core.popup("No image in clipboard.", parent=self)
            return

        pmap = self.core.media.scalePixmap(
            pmap,
            self.shotPrvXres,
            self.shotPrvYres,
        )
        self.setPixmap(pmap)

    @err_catcher(name=__name__)
    def browsePreview(self) -> None:
        """Open file browser to select a shot preview image.
        
        Displays a file dialog to select an image file (JPG, PNG, EXR) and
        sets it as the shot preview, scaled to the preview dimensions.
        Supports EXR files with special handling.
        """
        formats = "Image File (*.jpg *.png *.exr)"

        imgPath = QFileDialog.getOpenFileName(
            self, "Select thumbnail-image", self.imgPath, formats
        )[0]

        if not imgPath:
            return

        if os.path.splitext(imgPath)[1] == ".exr":
            pmsmall = self.core.media.getPixmapFromExrPath(
                imgPath,
                width=self.shotPrvXres,
                height=self.shotPrvYres,
            )
        else:
            pm = self.core.media.getPixmapFromPath(imgPath)
            if pm.width() == 0:
                warnStr = "Cannot read image: %s" % imgPath
                self.core.popup(warnStr, parent=self)
                return

            pmsmall = self.core.media.scalePixmap(
                pm,
                self.shotPrvXres,
                self.shotPrvYres,
            )

        self.setPixmap(pmsmall)

    @err_catcher(name=__name__)
    def setPixmap(self, pmsmall: QPixmap) -> None:
        """Set the preview pixmap and update the preview label.
        
        Args:
            pmsmall: Pixmap to display as the shot preview
        """
        self.pmap = pmsmall
        self.l_shotPreview.setMinimumSize(self.pmap.width(), self.pmap.height())
        self.l_shotPreview.setPixmap(self.pmap)

    @err_catcher(name=__name__)
    def validate(self, editField: Any) -> None:
        """Validate a line edit field.
        
        Args:
            editField: The line edit widget to validate
            
        Applies Prism's standard line edit validation rules.
        """
        self.core.validateLineEdit(editField)

    @err_catcher(name=__name__)
    def deleteShot(self) -> None:
        """Delete the current shot and all its associated files.
        
        Prompts the user for confirmation before deleting the shot, including
        all scene files and renderings. Closes the dialog if confirmed.
        """
        shotName = self.core.entities.getShotName(self.shotData)
        msgText = (
            'Are you sure you want to delete shot "%s"?\n\nThis will delete all scenefiles and renderings, which exist in this shot.'
            % (shotName)
        )

        result = self.core.popupQuestion(msgText, parent=self)
        if result == "Yes":
            self.core.createCmd(["deleteShot", shotName])
            self.accept(True)

    @err_catcher(name=__name__)
    def createEntities(self) -> Optional[Dict[str, Any]]:
        """Create shot entities based on current dialog values.
        
        Returns:
            Result dictionary from the last entity creation, or None
            
        This method handles:
        - Creating shots from comma-separated lists of episodes, sequences, and shots
        - Setting frame ranges for each shot
        - Applying preview thumbnails
        - Creating task presets if selected
        - Emitting shotCreated signal for each created shot
        """
        result = None
        if self.useEpisodes:
            epName = self.shotData["episode"].replace(os.pathsep, ",")
            eps = [ep.strip() for ep in epName.split(",") if ep.strip()]
        else:
            eps = [None]

        seqName = self.shotData["sequence"].replace(os.pathsep, ",")
        shotName = self.shotData["shot"].replace(os.pathsep, ",")
        seqs = [seq.strip() for seq in seqName.split(",") if seq.strip()]
        for ep in eps:
            for seq in seqs:
                shots = [shot.strip() for shot in shotName.split(",") if shot.strip()]
                for shot in shots:
                    shotData = self.shotData.copy()
                    shotData["sequence"] = seq
                    shotData["shot"] = shot
                    if self.useEpisodes:
                        shotData["episode"] = ep

                    result = self.core.entities.createEntity(shotData, frameRange=[self.sp_startFrame.value(), self.sp_endFrame.value()], preview=getattr(self, "pmap", None))
                    if self.chb_taskPreset.isChecked():
                        self.core.entities.createTasksFromPreset(shotData, self.cb_taskPreset.currentData())

                    self.shotCreated.emit(shotData)

        return result

    @err_catcher(name=__name__)
    def buttonboxClicked(self, button: Any) -> None:
        """Handle button box button clicks.
        
        Args:
            button: The button that was clicked
            
        Processes clicks on:
        - Add: Create shot and keep dialog open for more
        - Create: Create shot and close dialog
        - Save: Save shot information and close
        - Next: Save and trigger next step workflow
        - Cancel: Close dialog without saving
        """
        if button.text() == "Add":
            result = self.validateInput()
            if result:
                self.shotData = self.getShotData()
                self.createEntities()

            self.shotData = {}
            self.onShotIncrementClicked()
        elif button.text() == "Create":
            result = self.validateInput()
            if result:
                self.shotData = self.getShotData()
                self.createEntities()
                self.accept(True)

        elif button.text() == "Save":
            result = self.saveInfo()
            if result:
                self.shotSaved.emit()
                self.accept(True)
        elif button.text() == self.btext:
            result = self.saveInfo()
            if result:
                result = self.createEntities()
                if result and not result.get("existed", True):
                    self.accept(True)
                    self.nextClicked.emit()
                else:
                    self.shotData = {}

        elif button.text() == "Cancel":
            self.reject()

    @err_catcher(name=__name__)
    def accept(self, force: bool = False) -> None:
        """Accept and close the dialog.
        
        Args:
            force: If True, actually close the dialog. If False, do nothing.
            
        This override prevents accidental dialog closure without explicitly
        using a button.
        """
        if force:
            QDialog.accept(self)

        return

    @err_catcher(name=__name__)
    def getShotData(self) -> Dict[str, str]:
        """Get shot data dictionary from current dialog values.
        
        Returns:
            Dictionary containing type, episode (if used), sequence, and shot names
        """
        data = {
            "type": "shot",
            "sequence": self.e_sequence.text(),
            "shot": self.e_shotName.text() or "_sequence",
        }
        if self.useEpisodes:
            data["episode"] = self.e_episode.text()
            if not data["sequence"]:
                data["sequence"] = "_episode"

        return data

    @err_catcher(name=__name__)
    def validateInput(self, newShotData: Optional[Dict[str, str]] = None) -> bool:
        """Validate shot input fields.
        
        Args:
            newShotData: Shot data dictionary to validate, or None to get current values
            
        Returns:
            True if validation passes, False otherwise
            
        Validates that episode, sequence, and shot names are not empty and
        don't start with underscore (except for special cases like "_episode", "_sequence").
        """
        if newShotData is None:
            newShotData = self.getShotData()

        if self.useEpisodes and (not newShotData["episode"] or newShotData["episode"].startswith("_")):
            self.core.popup("Invalid episodename", parent=self)
            return False

        if not newShotData["sequence"] or (newShotData["sequence"].startswith("_") and newShotData["sequence"] != "_episode"):
            self.core.popup("Invalid sequencename", parent=self)
            return False

        if not newShotData["shot"] or (newShotData["shot"].startswith("_") and newShotData["shot"] != "_sequence"):
            self.core.popup("Invalid shotname", parent=self)
            return False

        return True

    @err_catcher(name=__name__)
    def saveInfo(self) -> bool:
        """Save shot information and handle renames if necessary.
        
        Returns:
            True if save was successful, False if user cancelled or validation failed
            
        This method:
        1. Validates new shot data
        2. Prompts for confirmation if episode/sequence/shot is being renamed
        3. Performs the rename operation if confirmed
        4. Updates frame range and preview
        5. Saves metadata
        6. Triggers callback
        """
        newShotData = self.getShotData()
        result = self.validateInput(newShotData)
        if not result:
            return result

        if self.useEpisodes and self.shotData.get("episode") and newShotData["episode"] != self.shotData["episode"]:
            msgText = (
                'Are you sure you want to rename this episode from "%s" to "%s"?\n\nThis will rename all files in the subfolders of the episode, which may cause errors, if these files are referenced somewhere else.'
                % (self.shotData["episode"], newShotData["episode"])
            )

            result = self.core.popupQuestion(msgText, parent=self)
            if result == "No":
                return False

            self.core.entities.renameEpisode(self.shotData["episode"], newShotData["episode"])
            if self.core.useLocalFiles:
                self.core.createCmd(["renameLocalSequence", self.shotData["episode"], newShotData["episode"]])
            self.shotData = newShotData
            if self.core.pb:
                self.core.pb.refreshUI()
                curw = self.core.pb.tbw_project.currentWidget()
                if hasattr(curw, "w_entities"):
                    curw.w_entities.navigate(newShotData)

        elif self.shotData.get("sequence") and newShotData["sequence"] != self.shotData["sequence"]:
            msgText = (
                'Are you sure you want to rename this sequence from "%s" to "%s"?\n\nThis will rename all files in the subfolders of the sequence, which may cause errors, if these files are referenced somewhere else.'
                % (self.shotData["sequence"], newShotData["sequence"])
            )

            result = self.core.popupQuestion(msgText, parent=self)
            if result == "No":
                return False

            self.core.entities.renameSequence(self.shotData["sequence"], newShotData["sequence"])
            if self.core.useLocalFiles:
                self.core.createCmd(["renameLocalSequence", self.shotData["sequence"], newShotData["sequence"]])
            self.shotData = newShotData
            if self.core.pb:
                self.core.pb.refreshUI()
                curw = self.core.pb.tbw_project.currentWidget()
                if hasattr(curw, "w_entities"):
                    curw.w_entities.navigate(newShotData)

        elif self.shotData.get("shot") and newShotData["shot"] != self.shotData["shot"]:
            msgText = (
                'Are you sure you want to rename this shot from "%s" to "%s"?\n\nThis will rename all files in the subfolders of the shot, which may cause errors, if these files are referenced somewhere else.'
                % (self.shotData["shot"], newShotData["shot"])
            )

            result = self.core.popupQuestion(msgText, parent=self)
            if result == "No":
                return False

            self.core.entities.renameShot(self.shotData, newShotData)
            if self.core.useLocalFiles:
                self.core.createCmd(["renameLocalShot", self.shotData, newShotData])
            self.shotData = newShotData
            if self.core.pb:
                self.core.pb.refreshUI()
                curw = self.core.pb.tbw_project.currentWidget()
                if hasattr(curw, "w_entities"):
                    curw.w_entities.navigate(newShotData)
        else:
            self.shotData = newShotData

        if self.shotData.get("shot", "") != "_sequence":
            self.core.entities.setShotRange(
                self.shotData, self.sp_startFrame.value(), self.sp_endFrame.value()
            )

        if hasattr(self, "pmap"):
            self.core.entities.setEntityPreview(self.shotData, self.pmap)

        self.metaWidget.save(self.shotData)
        self.core.callback(name="onEditShotDlgSaved", args=[self])
        return True

    @err_catcher(name=__name__)
    def loadData(self) -> None:
        """Load shot data and configure the dialog UI.
        
        This method:
        - Sets up episode/sequence/shot fields
        - Configures appropriate buttons for edit vs create mode
        - Loads preview image for existing shots
        - Loads frame range for existing shots
        - Sets up increment buttons for create mode
        - Configures task preset options
        """
        shotName = self.shotData.get("shot")
        seqName = self.shotData.get("sequence")
        if seqName:
            self.e_sequence.setText(self.shotData["sequence"])

        if self.useEpisodes:
            epName = self.shotData.get("episode")
            if epName:
                self.e_episode.setText(self.shotData["episode"])

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "sequence.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.l_seqIcon.setPixmap(icon.pixmap(15, 15))

        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "shot.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        self.l_shotIcon.setPixmap(icon.pixmap(15, 15))
        self.w_shotName.layout().addWidget(self.e_shotName, 2, 2, 1, 2)

        self.l_episodeIcon.setHidden(not self.useEpisodes)
        self.l_episode.setHidden(not self.useEpisodes)
        self.e_episode.setHidden(not self.useEpisodes)
        self.b_showEpisodes.setHidden(not self.useEpisodes)
        if self.useEpisodes:
            epName = self.shotData.get("episode")
            if epName:
                self.e_episode.setText(self.shotData["episode"])

            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "episode.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            self.l_episodeIcon.setPixmap(icon.pixmap(15, 15))

        pmap = None
        if shotName:
            b_save = self.buttonBox.addButton("Save", QDialogButtonBox.AcceptRole)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "check.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_save.setIcon(icon)
            b_cancel = self.buttonBox.addButton("Cancel", QDialogButtonBox.AcceptRole)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_cancel.setIcon(icon)
            self.e_shotName.setText(shotName)

            shotRange = self.core.entities.getShotRange(self.shotData)
            if shotRange:
                if shotRange[0] is not None:
                    self.sp_startFrame.setValue(shotRange[0])

                if shotRange[1] is not None:
                    self.sp_endFrame.setValue(shotRange[1])

            width = self.shotPrvXres
            height = self.shotPrvYres
            pmap = self.core.entities.getEntityPreview(self.shotData, width, height)
        else:
            self.setWindowTitle("Create Shot")
            self.b_deleteShot.setVisible(False)
            b_create = self.buttonBox.addButton("Create", QDialogButtonBox.AcceptRole)
            b_create.setToolTip("Create shot and close dialog")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "create.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_create.setIcon(icon)
            b_add = self.buttonBox.addButton("Add", QDialogButtonBox.AcceptRole)
            b_add.setToolTip("Create shot and keep dialog open")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_add.setIcon(icon)
            b_next = self.buttonBox.addButton(self.btext, QDialogButtonBox.AcceptRole)
            b_next.setToolTip("Create shot and open department dialog")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "arrow_right.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_next.setIcon(icon)
            b_cancel = self.buttonBox.addButton("Cancel", QDialogButtonBox.AcceptRole)
            b_cancel.setToolTip("Close dialog without creating shot")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "delete.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            b_cancel.setIcon(icon)
            if self.useEpisodes and self.e_episode.text():
                self.e_sequence.setFocus()

            if self.e_sequence.text():
                self.e_shotName.setFocus()

            self.buttonBox.setStyleSheet("* { button-layout: 2}")

            self.b_incrementEpisode = QToolButton()
            self.b_incrementEpisode.setToolTip("Increment episode name.\nHold CTRL to append incremented name.")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            self.b_incrementEpisode.setIcon(icon)
            self.b_incrementEpisode.clicked.connect(self.onEpisodeIncrementClicked)

            self.b_incrementSeq = QToolButton()
            self.b_incrementSeq.setToolTip("Increment sequence name.\nHold CTRL to append incremented name.")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            self.b_incrementSeq.setIcon(icon)
            self.b_incrementSeq.clicked.connect(self.onSeqIncrementClicked)

            self.b_incrementShot = QToolButton()
            self.b_incrementShot.setToolTip("Increment shot name.\nHold CTRL to append incremented name.")
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "add.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            self.b_incrementShot.setIcon(icon)
            self.b_incrementShot.clicked.connect(self.onShotIncrementClicked)

            if self.useEpisodes:
                self.w_shotName.layout().addWidget(self.b_incrementEpisode, 0, 4)

            self.w_shotName.layout().addWidget(self.b_incrementSeq, 1, 4)
            self.w_shotName.layout().addWidget(self.b_incrementShot, 2, 4)

            self.l_episode.setText("Episode(s):")
            self.e_episode.setToolTip("Episode name or comma separated list of episode names")
            self.l_seq.setText("Sequence(s):")
            self.e_sequence.setToolTip("Sequence name or comma separated list of sequence names")
            self.l_shot.setText("Shot(s):")
            self.e_shotName.setToolTip("Shot name or comma separated list of shot names")

            self.w_taskPreset = QWidget()
            self.lo_taskPreset = QHBoxLayout(self.w_taskPreset)
            self.lo_taskPreset.setContentsMargins(9, 0, 9, 0)
            self.l_taskPreset = QLabel("Task Preset:")
            self.chb_taskPreset = QCheckBox()
            self.cb_taskPreset = QComboBox()
            self.cb_taskPreset.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            self.lo_taskPreset.addWidget(self.l_taskPreset)
            self.lo_taskPreset.addStretch()
            self.lo_taskPreset.addWidget(self.chb_taskPreset)
            self.lo_taskPreset.addWidget(self.cb_taskPreset)
            self.cb_taskPreset.setEnabled(self.chb_taskPreset.isChecked())
            self.chb_taskPreset.toggled.connect(self.cb_taskPreset.setEnabled)
            presets = self.core.projects.getShotTaskPresets()
            if presets:
                for preset in presets:
                    self.cb_taskPreset.addItem(preset.get("name", ""), preset)

                if "Default" in [p.get("name") for p in presets]:
                    self.cb_taskPreset.setCurrentText("Default")

                self.layout().insertWidget(self.layout().indexOf(self.w_buttons)-2, self.w_taskPreset)

        if not pmap:
            imgFile = os.path.join(
                self.core.projects.getFallbackFolder(), "noFileSmall.jpg"
            )
            pmap = self.core.media.getPixmapFromPath(imgFile)

        if pmap:
            self.l_shotPreview.setMinimumSize(pmap.width(), pmap.height())
            self.l_shotPreview.setPixmap(pmap)

        self.core.callback(name="onEditShotDlgLoaded", args=[self])

    @err_catcher(name=__name__)
    def keyPressEvent(self, event: Any) -> None:
        """Handle key press events.
        
        Args:
            event: The key event object
            
        Processes Enter/Return to trigger the first button action,
        and Escape to reject the dialog.
        """
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            self.buttonboxClicked(self.buttonBox.buttons()[0])
        elif event.key() == Qt.Key_Escape:
            self.reject()

    @err_catcher(name=__name__)
    def onEpisodeIncrementClicked(self) -> None:
        """Increment the episode name by numerical value.
        
        Extracts the trailing number from the current episode name and
        increments it by 1. If no number exists, appends "01".
        If Ctrl is held, appends the incremented name to the existing value.
        """
        origName = self.e_episode.text()
        name = origName.replace(os.pathsep, ",").split(",")[-1]
        num = self.getNumFromStr(name)
        inc = 1
        if num:
            intnum = int(num) + inc
            newNum = str(intnum).zfill(len(num))
            newName = name[:-len(num)] + newNum
        else:
            strNum = str(inc).zfill(2)
            if name:
                newName = name + strNum
            else:
                newName = "ep" + strNum

        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            newName = origName + "," + newName

        self.e_episode.setText(newName.strip(","))

    @err_catcher(name=__name__)
    def onSeqIncrementClicked(self) -> None:
        """Increment the sequence name by numerical value.
        
        Extracts the trailing number from the current sequence name and
        increments it by the value from PRISM_SHOT_INCREMENT env var (default: 10).
        If no number exists, appends a zero-padded number.
        If Ctrl is held, appends the incremented name to the existing value.
        """
        origName = self.e_sequence.text()
        name = origName.replace(os.pathsep, ",").split(",")[-1]
        num = self.getNumFromStr(name)
        inc = int(os.getenv("PRISM_SHOT_INCREMENT", "10"))
        if num:
            intnum = int(num) + inc
            newNum = str(intnum).zfill(len(num))
            newName = name[:-len(num)] + newNum
        else:
            strNum = str(inc).zfill(3)
            if name:
                newName = name + strNum
            else:
                newName = "sq" + strNum

        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            newName = origName + "," + newName

        self.e_sequence.setText(newName.strip(","))

    @err_catcher(name=__name__)
    def onShotIncrementClicked(self) -> None:
        """Increment the shot name by numerical value.
        
        Extracts the trailing number from the current shot name and
        increments it by the value from PRISM_SHOT_INCREMENT env var (default: 10).
        If no number exists, appends a zero-padded number.
        If Ctrl is held, appends the incremented name to the existing value.
        """
        origName = self.e_shotName.text()
        name = origName.replace(os.pathsep, ",").split(",")[-1]
        num = self.getNumFromStr(name)
        inc = int(os.getenv("PRISM_SHOT_INCREMENT", "10"))
        if num:
            intnum = int(num) + inc
            newNum = str(intnum).zfill(len(num))
            newName = name[:-len(num)] + newNum
        else:
            strNum = str(inc).zfill(3)
            if name:
                newName = name + strNum
            else:
                newName = "sh" + strNum

        mods = QApplication.keyboardModifiers()
        if mods == Qt.ControlModifier:
            newName = origName + "," + newName

        self.e_shotName.setText(newName.strip(","))

    @err_catcher(name=__name__)
    def getNumFromStr(self, val: str) -> str:
        """Extract the trailing numeric characters from a string.
        
        Args:
            val: String to extract number from
            
        Returns:
            The trailing numeric characters as a string, or empty string if none found
            
        Example:
            "shot010" -> "010"
            "sequence" -> ""
        """
        numVal = ""
        for c in reversed(val):
            if c.isnumeric():
                numVal = c + numVal
            else:
                break

        return numVal
