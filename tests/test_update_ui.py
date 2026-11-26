import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication

from core.updater import Release
from core.version import __version__
from ui.main_window import MainWindow

RELEASE = Release(
    version="9.9.9",
    page_url="https://github.com/Babyferret/wihok/releases/tag/v9.9.9",
    asset_name="Wihok-Setup-9.9.9.exe",
    asset_url="https://github.com/Babyferret/wihok/releases/download/v9.9.9/Wihok-Setup-9.9.9.exe",
    sha256="a" * 64,
    size=201_790_432,
)


@pytest.fixture(scope="module")
def app():
    QCoreApplication.setOrganizationName("WihokTests")
    QCoreApplication.setApplicationName("UpdateUi")
    application = QApplication.instance() or QApplication([])
    yield application
    QSettings().clear()


@pytest.fixture
def window(app):
    QSettings().clear()
    w = MainWindow(device="cpu", check_updates=False)
    w.show()
    yield w
    w.close()


def shown(w) -> bool:
    return not w.update_bar.isHidden()


def test_the_title_bar_says_which_version_is_running(window):
    assert window.title_bar.version_label.text() == f"v{__version__}"


def test_the_bar_is_hidden_until_there_is_something_to_say(window):
    assert not shown(window)


def test_a_new_version_shows_its_number_and_size_and_marks_the_arrow(window):
    window.update_ui.controller.found.emit(RELEASE)

    assert shown(window)
    assert "9.9.9" in window.update_bar.label.text() and "202 MB" in window.update_bar.label.text()
    assert window.title_bar.update_button._badge is True


def test_later_hides_the_bar_but_keeps_the_dot_so_the_update_stays_one_click_away(window):
    window.update_ui.controller.found.emit(RELEASE)

    window.update_bar.later_button.click()

    assert not shown(window)
    assert window.title_bar.update_button._badge is True


def test_a_check_cannot_replace_a_download_that_is_running(window, monkeypatch):
    c = window.update_ui.controller
    c.found.emit(RELEASE)
    window.update_ui._set_state(("downloading", 40))
    asked = []
    monkeypatch.setattr(c, "check", lambda: asked.append(1))

    window.update_ui.check(manual=True)          # the menu entry pressed during the download
    window.update_ui._manual = True
    c.found.emit(RELEASE)                        # or a result that arrives late
    c.up_to_date.emit()
    c.check_failed.emit("offline")

    assert asked == []
    assert window.update_ui.state == ("downloading", 40)


def test_an_automatic_check_that_fails_says_nothing(window):
    window.update_ui._manual = False

    window.update_ui.controller.check_failed.emit("offline")

    assert not shown(window)


def test_a_check_the_person_asked_for_says_why_it_failed(window):
    window.update_ui._manual = True

    window.update_ui.controller.check_failed.emit("rate_limited")

    assert shown(window)
    assert "busy" in window.update_bar.label.text().lower()
    assert window.update_bar.label.property("kind") == "error"


def test_up_to_date_is_only_announced_when_the_person_asked(window):
    window.update_ui._manual = False
    window.update_ui.controller.up_to_date.emit()
    assert not shown(window)

    window.update_ui._manual = True
    window.update_ui.controller.up_to_date.emit()
    assert shown(window) and __version__ in window.update_bar.label.text()


def test_an_update_is_refused_while_a_song_is_being_processed(window, monkeypatch):
    window.update_ui.controller.found.emit(RELEASE)
    started = []
    monkeypatch.setattr(window.update_ui.controller, "download", lambda release: started.append(release))
    monkeypatch.setattr(MainWindow, "busy", property(lambda self: True))
    monkeypatch.setattr("ui.update_ui.sys.frozen", True, raising=False)

    window.update_bar.update_button.click()

    assert started == []
    assert "song" in window.update_bar.label.text().lower()


def test_pressing_update_in_the_installed_program_starts_the_download(window, monkeypatch):
    window.update_ui.controller.found.emit(RELEASE)
    started = []
    monkeypatch.setattr(window.update_ui.controller, "download", lambda release: started.append(release))
    monkeypatch.setattr("ui.update_ui.sys.frozen", True, raising=False)

    window.update_bar.update_button.click()

    assert started == [RELEASE]
    assert window.update_bar.progress.isVisible() and window.update_bar.cancel_button.isVisible()


def test_the_bar_follows_a_change_of_language(window):
    window.update_ui.controller.found.emit(RELEASE)
    window.language_box.setCurrentIndex(window.language_box.findData("th"))

    assert "9.9.9" in window.update_bar.label.text()
    assert "Update" not in window.update_bar.update_button.text()
    assert window.update_bar.update_button.text() != ""
