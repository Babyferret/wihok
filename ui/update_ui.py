"""The update feature as the person sees it: the version in the title bar, a small menu behind the arrow button,
and the slim bar that appears only when there is something to say. MainWindow owns one of these."""
import sys
import time

from PySide6.QtCore import QObject, QPoint, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMenu

from core.updater import Release, should_check
from core.version import __version__
from ui.strings import tr
from ui.updates import UpdateController

ERROR_KEYS = {
    "offline": "update_offline",
    "rate_limited": "update_rate_limited",
    "unverifiable": "update_unverifiable",
    "bad_checksum": "update_bad_checksum",
    "other": "update_failed",
}
AUTO_CHECK_DELAY_MS = 4000  # let the window appear and settle first
MESSAGE_SECONDS = 5


def format_size(size: int) -> str:
    return f"{size / 1_000_000:.0f} MB"


class UpdateUi(QObject):
    def __init__(self, window, auto_check: bool = True):
        super().__init__(window)
        self.window = window
        self.bar = window.update_bar
        self.button = window.title_bar.update_button
        self.controller = UpdateController(__version__, self)
        self.release: Release | None = None
        self.state = None  # what the bar is showing now: (kind, ...)
        self._accent = "#D9708F"

        window.title_bar.version_label.setText(f"v{__version__}")
        self.button.clicked.connect(self._show_menu)
        self.bar.update_clicked.connect(self._update)
        self.bar.later_clicked.connect(self._later)
        self.bar.cancel_clicked.connect(self.controller.cancel)
        self.bar.dismissed.connect(self._hide)
        self.bar.notes_clicked.connect(self._open_notes)
        c = self.controller
        c.found.connect(self._on_found)
        c.up_to_date.connect(self._on_up_to_date)
        c.check_failed.connect(lambda kind: self._on_check_failed(kind))
        c.progress.connect(lambda percent: self._set_state(("downloading", percent)))
        c.downloaded.connect(self._on_downloaded)
        c.download_failed.connect(lambda kind: self._set_state(("message", ERROR_KEYS[kind], True)))
        c.cancelled.connect(lambda: self._set_state(("message", "update_cancelled", False)))
        self._manual = False
        if auto_check:
            QTimer.singleShot(AUTO_CHECK_DELAY_MS, self._auto_check)

    # ---- settings -----------------------------------------------------

    @property
    def _settings(self):
        return self.window._settings

    def _auto_enabled(self) -> bool:
        return self._settings.value("auto_update_check", True, type=bool)

    def _last_check(self):
        return self._settings.value("last_update_check", type=float) if self._settings.contains("last_update_check") else None

    def _auto_check(self):
        if should_check(self._last_check(), time.time(), self._auto_enabled()):
            self.check(manual=False)

    # ---- the menu and the checks -------------------------------------------

    def _t(self, key: str, **values) -> str:
        return tr(self.window.language, key, **values)

    def build_menu(self) -> QMenu:
        menu = QMenu(self.window)
        header = menu.addAction(self._t("update_version", version=__version__))
        header.setEnabled(False)
        menu.addSeparator()
        menu.addAction(self._t("update_check")).triggered.connect(lambda: self.check(manual=True))
        auto = menu.addAction(self._t("update_auto"))
        auto.setCheckable(True)
        auto.setChecked(self._auto_enabled())
        auto.toggled.connect(lambda on: self._settings.setValue("auto_update_check", on))
        return menu

    def _show_menu(self):
        self.build_menu().exec(self.button.mapToGlobal(QPoint(0, self.button.height())))

    def _busy_with_update(self) -> bool:
        """A download or an install is under way: a check must neither start nor repaint the bar over it."""
        return bool(self.state) and self.state[0] in ("downloading", "installing")

    def check(self, manual: bool):
        if self._busy_with_update():
            return
        self._manual = manual
        if manual:
            self._set_state(("checking",))
        self.controller.check()

    def _on_found(self, release):
        self._settings.setValue("last_update_check", time.time())
        if self._busy_with_update():  # a late answer must not swap the release being downloaded
            return
        self.release = release
        self.button.set_badge(True)
        self._set_state(("available",))

    def _on_up_to_date(self):
        self._settings.setValue("last_update_check", time.time())
        if self._manual and not self._busy_with_update():
            self._set_state(("message", "update_current", False), timeout=True)

    def _on_check_failed(self, kind: str):
        if self._manual and not self._busy_with_update():
            self._set_state(("message", ERROR_KEYS[kind], True))

    # ---- the bar ------------------------------------------------------

    def _set_state(self, state, timeout: bool = False):
        self.state = state
        self.render()
        if timeout:
            QTimer.singleShot(MESSAGE_SECONDS * 1000, lambda: self._hide() if self.state == state else None)

    def _hide(self):
        self.state = None
        self.bar.hide()

    def render(self):
        """Draw the bar for the current state, in the current language."""
        t = self._t
        self.bar.update_button.setText(t("update_button"))
        self.bar.later_button.setText(t("update_later"))
        self.bar.cancel_button.setText(t("cancel"))
        self.bar.ok_button.setText(t("update_dismiss"))
        state = self.state
        if state is None:
            self.bar.hide()
            return
        kind = state[0]
        if kind == "checking":
            self.bar.installing(t("update_checking"))
        elif kind == "available" and self.release:
            # the style sheet overrides the palette, so the link takes its colour from the markup itself
            notes = f' &nbsp;<a href="notes" style="color:{self._accent}">{t("update_notes")}</a>'
            self.bar.available(t("update_available", version=self.release.version, size=format_size(self.release.size)) + notes)
        elif kind == "downloading":
            self.bar.downloading(t("update_downloading", version=self.release.version, percent=state[1]), state[1])
        elif kind == "installing":
            self.bar.installing(t("update_installing"))
        elif kind == "message":
            values = {"version": __version__} if state[1] == "update_current" else {}
            self.bar.message(t(state[1], **values), error=state[2])

    def retranslate(self):
        self.button.setToolTip(self._t("update_menu"))
        self.render()

    def apply_palette(self, palette):
        self._accent = palette.accent
        self.render()

    # ---- the actions --------------------------------------------------

    def _later(self):
        self._hide()  # the dot on the arrow stays, so the update is still one click away

    def _open_notes(self):
        if self.release and self.release.page_url:
            QDesktopServices.openUrl(QUrl(self.release.page_url))

    def _update(self):
        if self.window.busy:
            self._set_state(("message", "busy", True))
            return
        if not getattr(sys, "frozen", False):
            self._open_notes()  # running from source: there is no installed program to replace
            return
        self._set_state(("downloading", 0))
        self.controller.download(self.release)

    def _on_downloaded(self, installer):
        if self.window.busy:  # a song was started while the download ran: do not pull the program away from it
            self._set_state(("message", "busy", True))
            return
        self._set_state(("installing",))
        QTimer.singleShot(700, lambda: self._launch(installer))

    def _launch(self, installer):
        self.controller.install(installer, self.window.language)
        QApplication.quit()

    def cancel(self):
        self.controller.cancel()
