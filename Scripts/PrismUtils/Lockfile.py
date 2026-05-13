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
import time
import errno
import logging
from typing import Any, Optional, List, Dict, Tuple


logger = logging.getLogger(__name__)


class LockfileException(Exception):
    """Custom exception class for lockfile-related errors.
    
    This exception is raised when lockfile operations fail, such as when
    a timeout occurs or permissions are denied.
    """
    pass


class Lockfile(object):
    """Manages file locking for safe concurrent access to shared files.
    
    Implements a simple file-based locking mechanism using lock files to ensure
    that only one process can write to a file at a time. Supports timeout-based
    waiting and can be used as a context manager.
    
    Attributes:
        core: Reference to the Prism core instance.
        _fileLocked (bool): Whether the lock is currently held.
        lockPath (str): Path to the lock file.
        fileName (str): Path to the file being protected.
        timeout (float): Maximum time to wait for lock acquisition in seconds.
        delay (float): Time to wait between lock acquisition attempts in seconds.
    """
    
    def __init__(self, core: Any, fileName: str, timeout: int = 10, delay: float = 0.05) -> None:
        """Initialize the lockfile manager.
        
        Args:
            core: Prism core instance
            fileName: Path to the file to protect with locking
            timeout: Maximum seconds to wait for lock (default: 10)
            delay: Seconds between lock attempts (default: 0.05)
        """
        self.core = core
        self._fileLocked = False
        self.lockPath = fileName + ".lock"
        self.fileName = fileName
        self.timeout = timeout
        self.delay = delay

    def acquire(self, content: Optional[str] = None, force: bool = False) -> None:
        """Acquire the lock file.
        
        Attempts to create a lock file atomically. If the lock already exists,
        waits up to the timeout period for it to be released. Can optionally
        write content to the lock file and force removal of existing locks.
        
        Args:
            content: Optional content to write to the lock file.
            force: If True, removes existing lock files without waiting.
            
        Raises:
            LockfileException: If lock acquisition fails due to timeout or permissions.
        """
        startTime = time.time()
        triedCreate = False
        while True:
            try:
                self.lockFile = os.open(
                    self.lockPath, os.O_CREAT | os.O_EXCL | os.O_RDWR
                )
                self._fileLocked = True
                if content:
                    os.write(self.lockFile, content.encode())

                break
            except OSError as e:
                if e.errno == errno.EACCES:
                    msg = "Permission denied to create file:\n\n%s" % self.lockPath
                    self.core.popup(msg)
                    raise LockfileException(msg)
                elif e.errno == errno.ENOENT: 
                    msg = "The directory doesn't exist or can't be accessed:\n\n%s" % os.path.dirname(self.lockPath)
                    self.core.popup(msg)
                    raise LockfileException(msg)
                elif not os.path.exists(os.path.dirname(self.lockPath)) and not triedCreate:
                    triedCreate = True
                    os.makedirs(os.path.dirname(self.lockPath))
                    continue
                elif e.errno != errno.EEXIST:
                    raise
                elif force:
                    if os.path.exists(self.lockPath):
                        os.remove(self.lockPath)

                elif time.time() - startTime >= self.timeout:
                    msg = (
                        "This file seems to be in use by another process:\n\n%s\n\nForcing to write to this file while another process is writing to it could result in data loss.\n\nDo you want to force writing to this file?"
                        % self.fileName
                    )
                    result = self.core.popupQuestion(msg)
                    if result == "Yes":
                        if os.path.exists(self.lockPath):
                            os.remove(self.lockPath)
                    else:
                        raise LockfileException(
                            "Timeout occurred while writing to file: %s" % self.fileName
                        )

                time.sleep(self.delay)

    def release(self) -> None:
        """Release the lock file.
        
        Closes the file handle and removes the lock file. If removal fails,
        retries up to the timeout period. Shows a popup message if the lock
        cannot be removed.
        """
        if self._fileLocked:
            os.close(self.lockFile)
            startTime = time.time()
            while True:
                try:
                    if os.path.exists(self.lockPath):
                        os.remove(self.lockPath)
                    break
                except:
                    if time.time() - startTime >= self.timeout:
                        self.core.popup(
                            "Couldn't remove lockfile:\n\n%s\n\nIt might be used by another process. Prism won't be able to write to this file as long as it's lockfile exists."
                            % self.lockPath
                        )
                        break

                time.sleep(self.delay)

            self._fileLocked = False

    def forceRelease(self) -> None:
        """Force removal of the lock file without checking lock state.
        
        Removes the lock file if it exists, bypassing normal lock state tracking.
        Use with caution as this can break lock semantics.
        """
        if os.path.exists(self.lockPath):
            os.remove(self.lockPath)

    def waitUntilReady(self, timeout: Optional[float] = None) -> None:
        """Wait until the lock file is released.
        
        Blocks until the lock file is removed or the timeout is reached.
        Used when reading from a file to ensure no other process is writing.
        
        Args:
            timeout: Maximum time in seconds to wait. Uses instance timeout if None.
            
        Raises:
            LockfileException: If timeout is reached before lock is released.
        """
        startTime = time.time()
        timeout = timeout or self.timeout
        while True:
            if not os.path.exists(self.lockPath):
                break

            logger.debug("waiting for config to unlock before reading")

            if time.time() - startTime >= timeout:
                raise LockfileException(
                    "Timeout occurred while reading from file: %s" % self.fileName
                )

            time.sleep(self.delay)

    def isLocked(self) -> bool:
        """Check if the lock file currently exists.
        
        Returns:
            bool: True if the lock file exists, False otherwise.
        """
        return os.path.exists(self.lockPath)

    def __enter__(self) -> 'Lockfile':
        """Enter context manager - acquire the lock.
        
        Returns:
            Lockfile: Self reference for use in with statements.
        """
        if not self._fileLocked:
            self.acquire()
        return self

    def __exit__(self, type: Any, value: Any, traceback: Any) -> None:
        """Exit context manager - release the lock.
        
        Args:
            type: Exception type if an exception occurred.
            value: Exception value if an exception occurred.
            traceback: Exception traceback if an exception occurred.
        """
        if self._fileLocked:
            self.release()

    def __del__(self) -> None:
        """Destructor - ensure lock is released when object is destroyed."""
        self.release()
