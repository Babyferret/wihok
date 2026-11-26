"""Runs the update check and download off the window's thread and reports back with signals."""
import http.client
import subprocess
import sys
import tempfile
import threading
import urllib.error
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core.updater import (
    BadChecksum, Release, UpdateCancelled, UpdateCheckFailed, download_installer, find_update, installer_command,
    prune_downloads,
)

UPDATES_FOLDER = Path(tempfile.gettempdir()) / "Wihok-update"


class UpdateController(QObject):
    found = Signal(object)          # a Release
    up_to_date = Signal()
    check_failed = Signal(str)      # offline | rate_limited | unverifiable | other
    progress = Signal(int)          # percent
    downloaded = Signal(object)     # Path of the verified installer
    download_failed = Signal(str)   # offline | bad_checksum | other
    cancelled = Signal()

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self._current = current_version
        self._cancel = threading.Event()

    def check(self):
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self):
        try:
            release = find_update(self._current)
        except UpdateCheckFailed as error:
            self.check_failed.emit(error.kind)
        except Exception:
            self.check_failed.emit("other")
        else:
            self.found.emit(release) if release else self.up_to_date.emit()

    def download(self, release: Release):
        self._cancel = threading.Event()
        threading.Thread(target=self._download, args=(release, self._cancel), daemon=True).start()

    def _download(self, release: Release, cancel: threading.Event):
        last = [-1]

        def on_progress(done: int, total: int):
            percent = min(100, int(done * 100 / total)) if total else 0
            if percent != last[0]:  # a signal per megabyte is plenty; per percent is smoother than needed
                last[0] = percent
                self.progress.emit(percent)

        try:
            prune_downloads(UPDATES_FOLDER)
            path = download_installer(release, UPDATES_FOLDER, on_progress=on_progress, cancel=cancel)
        except UpdateCancelled:
            self.cancelled.emit()
        except BadChecksum:
            self.download_failed.emit("bad_checksum")
        except (urllib.error.URLError, OSError, http.client.HTTPException):
            self.download_failed.emit("offline")
        except Exception:
            self.download_failed.emit("other")
        else:
            self.downloaded.emit(path)

    def cancel(self):
        self._cancel.set()

    @staticmethod
    def install(installer: Path, language: str):
        """Start the installer over the folder Wihok runs from. The caller then closes the program, so that the
        installer can replace its files (the installer would also ask Windows to close it)."""
        app_dir = Path(sys.executable).parent
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(installer_command(installer, app_dir, language), creationflags=flags, close_fds=True)
