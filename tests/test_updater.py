import hashlib
import http.client
import io
import threading
import urllib.error
from pathlib import Path

import pytest

from core.updater import (
    BadChecksum, Release, UpdateCancelled, UpdateCheckFailed, download_installer, find_update, installer_command,
    is_newer, prune_downloads, should_check,
)

DOWNLOADS = "https://github.com/Babyferret/wihok/releases/download"
INSTALLER_SHA = "a" * 64


def github_release(version="1.1.0", installer_digest=f"sha256:{INSTALLER_SHA}", installer_url=None):
    """What api.github.com/repos/.../releases/latest returns for a Wihok release (only the fields we read)."""
    base = f"{DOWNLOADS}/v{version}"
    setup = {
        "name": f"Wihok-Setup-{version}.exe",
        "browser_download_url": installer_url or f"{base}/Wihok-Setup-{version}.exe",
        "size": 201_782_080,
    }
    if installer_digest is not None:
        setup["digest"] = installer_digest
    pack = {
        "name": f"Wihok-CUDA-Pack-{version}.exe",
        "browser_download_url": f"{base}/Wihok-CUDA-Pack-{version}.exe",
        "digest": "sha256:" + "b" * 64,
        "size": 1_778_643_485,
    }
    return {
        "tag_name": f"v{version}",
        "html_url": f"https://github.com/Babyferret/wihok/releases/tag/v{version}",
        "assets": [pack, setup],
    }


@pytest.mark.parametrize("candidate,current,expected", [
    ("1.1.0", "1.0.0", True),
    ("v1.1.0", "1.0.0", True),
    ("1.0.0", "1.0.0", False),
    ("1.0.0", "1.1.0", False),
    ("1.0.10", "1.0.9", True),  # numbers, not text: "10" is bigger than "9"
    ("2.0.0", "1.99.99", True),
    ("1.1", "1.1.0", False),   # the same version written with fewer numbers
    ("1.1.0", "1.1", False),
    ("1.1.1", "1.1", True),
])
def test_compares_versions_as_numbers(candidate, current, expected):
    assert is_newer(candidate, current) is expected


def test_finds_a_newer_release_and_picks_the_installer_not_the_gpu_add_on():
    release = find_update("1.0.0", fetch_json=lambda url: github_release("1.1.0"))

    assert isinstance(release, Release)
    assert release.version == "1.1.0"
    assert release.asset_name == "Wihok-Setup-1.1.0.exe"
    assert release.sha256 == INSTALLER_SHA
    assert release.page_url.endswith("/tag/v1.1.0")


def test_finds_nothing_when_already_up_to_date():
    assert find_update("1.1.0", fetch_json=lambda url: github_release("1.1.0")) is None
    assert find_update("1.2.0", fetch_json=lambda url: github_release("1.1.0")) is None


def test_refuses_a_release_whose_installer_has_no_checksum():
    with pytest.raises(UpdateCheckFailed) as caught:
        find_update("1.0.0", fetch_json=lambda url: github_release("1.1.0", installer_digest=None))
    assert caught.value.kind == "unverifiable"


def test_refuses_a_download_address_outside_the_project():
    evil = github_release("1.1.0", installer_url="https://evil.example/Wihok-Setup-1.1.0.exe")
    with pytest.raises(UpdateCheckFailed) as caught:
        find_update("1.0.0", fetch_json=lambda url: evil)
    assert caught.value.kind == "unverifiable"


def test_refuses_a_release_that_has_no_installer():
    only_pack = github_release("1.1.0")
    only_pack["assets"] = [a for a in only_pack["assets"] if "Pack" in a["name"]]
    with pytest.raises(UpdateCheckFailed) as caught:
        find_update("1.0.0", fetch_json=lambda url: only_pack)
    assert caught.value.kind == "unverifiable"


@pytest.mark.parametrize("error,kind", [
    (urllib.error.URLError("no route to host"), "offline"),
    (TimeoutError("timed out"), "offline"),
    (urllib.error.HTTPError("u", 403, "rate limit exceeded", {}, None), "rate_limited"),
    (urllib.error.HTTPError("u", 429, "too many", {}, None), "rate_limited"),
    (urllib.error.HTTPError("u", 500, "server error", {}, None), "other"),
    (http.client.IncompleteRead(b"{"), "offline"),   # the connection dropped halfway through the answer
])
def test_tells_the_failure_kinds_apart(error, kind):
    def broken(url):
        raise error

    with pytest.raises(UpdateCheckFailed) as caught:
        find_update("1.0.0", fetch_json=broken)
    assert caught.value.kind == kind


def _release_for(payload: bytes, sha256: str | None = None) -> Release:
    return Release(
        version="1.1.0",
        page_url="https://github.com/Babyferret/wihok/releases/tag/v1.1.0",
        asset_name="Wihok-Setup-1.1.0.exe",
        asset_url=f"{DOWNLOADS}/v1.1.0/Wihok-Setup-1.1.0.exe",
        sha256=sha256 or hashlib.sha256(payload).hexdigest(),
        size=len(payload),
    )


def test_downloads_the_installer_and_checks_it_against_the_published_checksum(tmp_path):
    payload = b"pretend installer " * 100_000
    progress = []

    path = download_installer(
        _release_for(payload), tmp_path,
        open_url=lambda url: io.BytesIO(payload), on_progress=lambda done, total: progress.append((done, total)),
    )

    assert path == tmp_path / "Wihok-Setup-1.1.0.exe"
    assert path.read_bytes() == payload
    assert progress[-1] == (len(payload), len(payload))
    assert not list(tmp_path.glob("*.part")), "no half-written file is left behind"


def test_a_download_that_does_not_match_its_checksum_is_deleted_and_never_run(tmp_path):
    payload = b"tampered " * 1000

    with pytest.raises(BadChecksum):
        download_installer(
            _release_for(payload, sha256="0" * 64), tmp_path, open_url=lambda url: io.BytesIO(payload)
        )

    assert list(tmp_path.iterdir()) == []


DAY = 24 * 3600


@pytest.mark.parametrize("last,now,enabled,expected", [
    (None, 1_000_000, True, True),                # never checked
    (1_000_000, 1_000_000 + DAY + 1, True, True),  # more than a day ago
    (1_000_000, 1_000_000 + DAY - 1, True, False),  # checked today already
    (None, 1_000_000, False, False),              # the person switched it off
    (2_000_000, 1_000_000, True, True),           # the clock went backwards: check rather than stay silent for good
])
def test_checks_automatically_at_most_once_a_day_and_never_when_switched_off(last, now, enabled, expected):
    assert should_check(last, now, enabled) is expected


def test_the_installer_is_started_over_the_same_folder_with_the_apps_language_and_a_relaunch(tmp_path):
    installer = tmp_path / "Wihok-Setup-1.1.0.exe"
    app_dir = Path(r"C:\Users\Some One\AppData\Local\Programs\Wihok")

    command = installer_command(installer, app_dir, "th")

    assert command[0] == str(installer)
    assert "/SILENT" in command and "/NORESTART" in command and "/SUPPRESSMSGBOXES" in command
    assert f"/DIR={app_dir}" in command
    assert "/LANG=th" in command
    assert "/RELAUNCH=1" in command
    assert not any(part.startswith("/TASKS") for part in command), "the person's earlier choices must be kept"


def test_old_downloads_are_removed_but_nothing_else(tmp_path):
    (tmp_path / "Wihok-Setup-1.0.1.exe").write_bytes(b"x")
    (tmp_path / "Wihok-Setup-1.1.0.exe.part").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("keep me")

    prune_downloads(tmp_path)

    assert sorted(p.name for p in tmp_path.iterdir()) == ["notes.txt"]
    prune_downloads(tmp_path / "does-not-exist")   # a first run has no folder yet: must not raise


def test_cancelling_a_download_removes_what_was_written(tmp_path):
    payload = b"x" * 5_000_000
    cancel = threading.Event()

    with pytest.raises(UpdateCancelled):
        download_installer(
            _release_for(payload), tmp_path, open_url=lambda url: io.BytesIO(payload),
            on_progress=lambda done, total: cancel.set(), cancel=cancel,
        )

    assert list(tmp_path.iterdir()) == []
