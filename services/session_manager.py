"""Windows Session Management Service.

Monitors Windows session events (lock/unlock, sleep/resume, monitor changes)
to suspend rendering and conserve system resources during inactivity.
"""
import ctypes
from ctypes import wintypes
import logging
import sys
from typing import Optional

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

logger = logging.getLogger("SpiderBuddy.SessionManager")

# Windows message constants
WM_WTSSESSION_CHANGE = 0x02B1
WM_POWERBROADCAST = 0x0218
WM_DISPLAYCHANGE = 0x007E

# WTS session change event codes
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
WTS_SESSION_LOGON = 0x5
WTS_SESSION_LOGOFF = 0x6

# Power broadcast event codes
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012

NOTIFY_FOR_THIS_SESSION = 0


class _NativeSessionWidget(QWidget):
    """Hidden window that receives native Windows session & power messages."""

    def __init__(self, manager: "SessionManager"):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint)
        self.manager = manager
        self.setAttribute(Qt.WA_DontShowOnScreen, True)
        self.resize(0, 0)
        self.hide()
        self._registered_wts = False

    def register_wts(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            hwnd = int(self.winId())
            wts = ctypes.windll.wtsapi32
            wts.WTSRegisterSessionNotification.argtypes = [wintypes.HWND, wintypes.DWORD]
            wts.WTSRegisterSessionNotification.restype = wintypes.BOOL
            res = wts.WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_THIS_SESSION)
            self._registered_wts = bool(res)
            logger.info("Registered WTSRegisterSessionNotification: %s", self._registered_wts)
            return self._registered_wts
        except Exception as exc:
            logger.warning("Could not register WTSRegisterSessionNotification: %s", exc)
            return False

    def unregister_wts(self) -> None:
        if self._registered_wts and sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                unregister = ctypes.windll.wtsapi32.WTSUnRegisterSessionNotification
                unregister.argtypes = [wintypes.HWND]
                unregister.restype = wintypes.BOOL
                unregister(hwnd)
            except Exception:
                pass
            self._registered_wts = False

    def nativeEvent(self, event_type, message):
        try:
            if sys.platform == "win32" and event_type == b"windows_generic_MSG":
                msg = wintypes.MSG.from_address(int(message))
                msg_id, wparam = msg.message, msg.wParam

                if msg_id == WM_WTSSESSION_CHANGE:
                    if wparam == WTS_SESSION_LOCK:
                        self.manager.handle_lock()
                    elif wparam in (WTS_SESSION_UNLOCK, WTS_SESSION_LOGON):
                        self.manager.handle_unlock()
                elif msg_id == WM_POWERBROADCAST:
                    if wparam == PBT_APMSUSPEND:
                        self.manager.handle_suspend()
                    elif wparam in (PBT_APMRESUMESUSPEND, PBT_APMRESUMEAUTOMATIC):
                        self.manager.handle_resume()
                elif msg_id == WM_DISPLAYCHANGE:
                    self.manager.handle_display_change()
        except Exception as exc:
            logger.debug("Error processing nativeEvent: %s", exc)

        return super().nativeEvent(event_type, message)


class SessionManager(QObject):
    """Manages Windows session lifecycle and display changes."""

    session_locked = Signal()
    session_unlocked = Signal()
    system_suspended = Signal()
    system_resumed = Signal()
    display_changed = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._is_locked = False
        self._is_suspended = False
        self._native_widget: Optional[_NativeSessionWidget] = None
        self._connected_screens = []

        self._setup_native_listener()
        self._setup_qt_screen_listeners()

    @property
    def is_locked(self) -> bool:
        return self._is_locked

    @property
    def is_suspended(self) -> bool:
        return self._is_suspended

    @property
    def is_session_active(self) -> bool:
        return not self._is_locked and not self._is_suspended

    def _setup_native_listener(self) -> None:
        if sys.platform == "win32":
            try:
                self._native_widget = _NativeSessionWidget(self)
                self._native_widget.register_wts()
            except Exception as exc:
                logger.warning("Could not initialize native session listener: %s", exc)

    def _setup_qt_screen_listeners(self) -> None:
        app = QGuiApplication.instance()
        if not app:
            return

        app.screenAdded.connect(self._on_screen_topology_changed)
        app.screenRemoved.connect(self._on_screen_topology_changed)
        app.primaryScreenChanged.connect(self._on_screen_topology_changed)
        self._bind_screen_geometry_signals()

    def _bind_screen_geometry_signals(self) -> None:
        app = QGuiApplication.instance()
        if not app:
            return
        for screen in app.screens():
            if screen not in self._connected_screens:
                self._connected_screens.append(screen)
                try:
                    screen.geometryChanged.connect(lambda *_: self.handle_display_change())
                    screen.logicalDotsPerInchChanged.connect(lambda *_: self.handle_display_change())
                except Exception:
                    pass

    def _on_screen_topology_changed(self, *args) -> None:
        self._bind_screen_geometry_signals()
        self.handle_display_change()

    def handle_lock(self) -> None:
        if not self._is_locked:
            self._is_locked = True
            logger.info("Windows session locked. Suspending companion rendering and activities.")
            self.session_locked.emit()

    def handle_unlock(self) -> None:
        if self._is_locked:
            self._is_locked = False
            logger.info("Windows session unlocked. Restoring companion rendering and activities.")
            self.session_unlocked.emit()

    def handle_suspend(self) -> None:
        if not self._is_suspended:
            self._is_suspended = True
            logger.info("System entering sleep/suspend. Pausing companion.")
            self.system_suspended.emit()

    def handle_resume(self) -> None:
        if self._is_suspended:
            self._is_suspended = False
            logger.info("System resumed from sleep/suspend. Restoring companion.")
            self.system_resumed.emit()

    def handle_display_change(self) -> None:
        logger.info("Display topology / resolution changed.")
        self.display_changed.emit()

    def stop(self) -> None:
        """Cleanup listener hooks."""
        if self._native_widget is not None:
            self._native_widget.unregister_wts()
            self._native_widget.deleteLater()
            self._native_widget = None
