"""Windows user activity and idle detection monitor."""
import ctypes
import logging
import sys
import time
from typing import Optional
from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger("SpiderBuddy.ActivityMonitor")


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


class ActivityMonitor(QObject):
    """Monitors system-wide user activity (keyboard/mouse) using Windows Win32 API."""

    # Signal emitted when user transitions between active and idle states
    user_became_idle = Signal(float)       # idle duration in seconds
    user_became_active = Signal()          # active again
    idle_tick = Signal(float)              # current idle seconds (emitted periodically)

    def __init__(self, check_interval_ms: int = 1000, idle_threshold_sec: float = 30.0, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.check_interval_ms = check_interval_ms
        self.idle_threshold_sec = idle_threshold_sec
        self.is_idle = False
        self._last_active_time = time.time()

        self._timer = QTimer(self)
        self._timer.setInterval(self.check_interval_ms)
        self._timer.timeout.connect(self._check_activity)

        self._has_win32 = sys.platform == "win32"

    def start(self) -> None:
        """Start monitoring user input."""
        self._last_active_time = time.time()
        self._timer.start()
        logger.info("ActivityMonitor started.")

    def stop(self) -> None:
        """Stop monitoring."""
        self._timer.stop()
        logger.info("ActivityMonitor stopped.")

    def get_idle_duration(self) -> float:
        """Returns elapsed seconds since last keyboard or mouse input."""
        if not self._has_win32:
            return 0.0

        try:
            last_input = LASTINPUTINFO()
            last_input.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(last_input)):
                # dwTime is in milliseconds since system boot
                millis = (ctypes.windll.kernel32.GetTickCount() - last_input.dwTime) & 0xFFFFFFFF
                return max(0.0, millis / 1000.0)
        except Exception as e:
            logger.debug(f"Failed to query GetLastInputInfo: {e}")
        return 0.0

    def _check_activity(self) -> None:
        idle_seconds = self.get_idle_duration()
        self.idle_tick.emit(idle_seconds)

        if idle_seconds >= self.idle_threshold_sec and not self.is_idle:
            self.is_idle = True
            logger.debug(f"User is now idle ({idle_seconds:.1f}s)")
            self.user_became_idle.emit(idle_seconds)
        elif idle_seconds < self.idle_threshold_sec and self.is_idle:
            self.is_idle = False
            logger.debug("User is active again")
            self.user_became_active.emit()
