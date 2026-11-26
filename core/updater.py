"""Finds a newer Wihok release on GitHub and downloads its installer, checking it against the published SHA-256."""
import hashlib
import http.client
import json
import re
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

REPO = "Babyferret/wihok"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_PREFIX = f"https://github.com/{REPO}/releases/download/"
INSTALLER_NAME = re.compile(r"^Wihok-Setup-\d+\.\d+\.\d+\.exe$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CHUNK = 1024 * 1024
TIMEOUT_SECONDS = 20


class UpdateCheckFailed(Exception):
    """kind: offline | rate_limited | unverifiable | other"""

    def __init__(self, kind: str, message: str = ""):
        super().__init__(message or kind)
        self.kind = kind


class BadChecksum(Exception):
    pass


class UpdateCancelled(Exception):
    pass


@dataclass(frozen=True)
class Release:
    version: str
    page_url: str
    asset_name: str
    asset_url: str
    sha256: str
    size: int


def _parse(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.lstrip("vV").split("."))


def is_newer(candidate: str, current: str) -> bool:
    a, b = _parse(candidate), _parse(current)
    width = max(len(a), len(b))  # "1.1" and "1.1.0" are the same version
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "Wihok"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def _open_url(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "Wihok"})
    return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS)


def _unverifiable(reason: str) -> UpdateCheckFailed:
    return UpdateCheckFailed("unverifiable", reason)


def _installer_asset(data: dict) -> Release:
    version = str(data.get("tag_name", "")).lstrip("vV")
    try:
        _parse(version)
    except ValueError:
        raise _unverifiable(f"release tag {data.get('tag_name')!r} is not a version") from None
    for asset in data.get("assets", []):
        name = str(asset.get("name", ""))
        if not INSTALLER_NAME.match(name):
            continue
        url = str(asset.get("browser_download_url", ""))
        if not url.startswith(DOWNLOAD_PREFIX):
            raise _unverifiable("the installer is not hosted on the project's GitHub releases")
        digest = str(asset.get("digest") or "")
        sha = digest.removeprefix("sha256:").lower()
        if not digest.startswith("sha256:") or not SHA256.match(sha):
            raise _unverifiable("the release publishes no SHA-256 for its installer")
        return Release(version, str(data.get("html_url", "")), name, url, sha, int(asset.get("size") or 0))
    raise _unverifiable("the release has no installer")


def find_update(current: str, fetch_json: Callable[[str], dict] = _get_json) -> Optional[Release]:
    try:
        data = fetch_json(LATEST_URL)
    except urllib.error.HTTPError as error:
        kind = "rate_limited" if error.code in (403, 429) else "other"
        raise UpdateCheckFailed(kind, f"GitHub answered {error.code}") from error
    except (urllib.error.URLError, OSError, http.client.HTTPException) as error:  # TimeoutError is an OSError;
        raise UpdateCheckFailed("offline", str(error)) from error                # IncompleteRead is not
    except ValueError as error:
        raise UpdateCheckFailed("other", "GitHub's answer was not understood") from error
    release = _installer_asset(data)
    return release if is_newer(release.version, current) else None


CHECK_INTERVAL_SECONDS = 24 * 3600


def should_check(last_checked: Optional[float], now: float, enabled: bool) -> bool:
    """The automatic check: on, and not more than once a day. A clock that went backwards counts as "due"."""
    if not enabled:
        return False
    return last_checked is None or now < last_checked or now - last_checked >= CHECK_INTERVAL_SECONDS


def installer_command(installer: Path, app_dir: Path, language: str) -> list[str]:
    """The new installer, run over the folder Wihok is in now. No /TASKS: the choices made at the first install
    (a desktop shortcut) are remembered by the installer itself, and GPU support is decided by it too."""
    return [str(installer), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", f"/DIR={app_dir}",
            f"/LANG={language}", "/RELAUNCH=1"]


def prune_downloads(folder: Path) -> None:
    """Remove installers left from earlier updates (and half-finished downloads) in the updates folder."""
    if not Path(folder).is_dir():
        return
    for path in Path(folder).iterdir():
        if path.is_file() and (INSTALLER_NAME.match(path.name) or (path.name.endswith(".part") and INSTALLER_NAME.match(path.stem))):
            try:
                path.unlink()
            except OSError:
                pass  # still running or locked: the next start tries again


def download_installer(
    release: Release,
    dest_dir: Path,
    open_url: Callable[[str], object] = _open_url,
    on_progress: Callable[[int, int], None] = lambda done, total: None,
    cancel: Optional[threading.Event] = None,
) -> Path:
    """Saves the installer in dest_dir. On any failure nothing is left behind; a checksum mismatch raises BadChecksum."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    final = dest_dir / release.asset_name
    part = dest_dir / (release.asset_name + ".part")
    digest = hashlib.sha256()
    done = 0
    try:
        with open_url(release.asset_url) as source, open(part, "wb") as out:
            while chunk := source.read(CHUNK):
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                on_progress(done, release.size)
                if cancel is not None and cancel.is_set():
                    raise UpdateCancelled()
        if digest.hexdigest() != release.sha256:
            raise BadChecksum(f"{release.asset_name} does not match its published SHA-256")
        part.replace(final)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    return final
