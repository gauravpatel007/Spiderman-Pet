"""Battery monitor service for laptop power detection and low-battery events."""
import ctypes
import logging
from ctypes import wintypes
from typing import Optional, Tuple
from PySide6.QtCore import QObject, Signal, QTimer

logger = logging.getLogger("SpiderBuddy.BatteryService")


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", wintypes.BYTE),
        ("BatteryFlag", wintypes.BYTE),
        ("BatteryLifePercent", wintypes.BYTE),
        ("SystemStatusFlag", wintypes.BYTE),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    ]


class BatteryService(QObject):
    """Monitors system battery level on Windows laptops and triggers low-battery / charging effects."""

    battery_updated = Signal(int, bool, bool)  # percent, is_charging, is_low
    charging_started = Signal(int)  # percent when charging begins
    charging_stopped = Signal()  # when charger is disconnected
    glitch_triggered = Signal()  # periodic flicker impulse

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._percent: int = 100
        self._is_charging: bool = False
        self._was_charging: bool = False
        self._has_battery: bool = True
        self._is_low: bool = False
        self._is_simulated: bool = False
        self._simulated_low: bool = False
        self._simulated_charging: bool = False

        self._check_timer = QTimer(self)
        self._check_timer.setInterval(10000)  # check every 10s
        self._check_timer.timeout.connect(self._check_status)

        self._glitch_timer = QTimer(self)
        self._glitch_timer.setInterval(30000)  # gentle suit flicker impulse (every 30s when low battery)
        self._glitch_timer.timeout.connect(self._on_glitch_tick)

        self._test_glitch_active = False

    @property
    def percent(self) -> int:
        if self._is_simulated and self._simulated_low:
            return 12
        if self._is_simulated and self._simulated_charging:
            return self._percent
        return self._percent

    @property
    def is_charging(self) -> bool:
        if self._is_simulated and self._simulated_low:
            return False
        if self._is_simulated and self._simulated_charging:
            return True
        if not self._has_battery:
            return False
        return self._is_charging

    @property
    def has_battery(self) -> bool:
        return self._has_battery

    @property
    def is_low_battery(self) -> bool:
        if self._is_simulated:
            return self._simulated_low
        return self._is_low

    def start(self):
        """Start polling battery status."""
        self._check_status()
        self._check_timer.start()

    def stop(self):
        """Stop battery polling."""
        self._check_timer.stop()
        self._glitch_timer.stop()

    def simulate_low_battery(self, enabled: bool):
        """Allow users on desktop or full charge to test low battery behavior."""
        self._is_simulated = enabled
        self._simulated_low = enabled
        if enabled:
            self._simulated_charging = False
        self._update_state()

    def simulate_charging(self, enabled: bool, percent: int = 85):
        """Allow users on desktop or test suites to preview charging effects."""
        self._is_simulated = enabled
        self._simulated_charging = enabled
        if enabled:
            self._simulated_low = False
            self._percent = percent
        self._update_state()

    def trigger_test_glitch(self, duration_seconds: float = 2.0):
        """Trigger temporary glitch effect preview for visual testing."""
        self._test_glitch_active = True
        self.glitch_triggered.emit()
        QTimer.singleShot(int(duration_seconds * 1000), self._end_test_glitch)

    def _end_test_glitch(self):
        self._test_glitch_active = False

    def _check_status(self):
        status = SYSTEM_POWER_STATUS()
        try:
            if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                self._has_battery = False
                self._is_charging = False
                return
        except Exception as exc:
            logger.debug(f"Could not read Windows power status: {exc}")
            self._has_battery = False
            self._is_charging = False
            return

        # 255 indicates unknown/no battery (desktop PC)
        if status.BatteryLifePercent == 255 or (status.BatteryFlag & 128):
            self._has_battery = False
            self._percent = 100
            self._is_charging = False  # Desktop PC has no battery to charge
        else:
            self._has_battery = True
            self._percent = int(status.BatteryLifePercent)
            self._is_charging = bool(status.ACLineStatus == 1)

        # Low battery condition: <= 15% and not plugged in
        self._is_low = (self._percent <= 15 and not self._is_charging)
        self._update_state()

    def _update_state(self):
        is_low = self.is_low_battery
        is_charging = self.is_charging
        percent = self.percent

        if is_low and not self._glitch_timer.isActive():
            self._glitch_timer.start()
        elif not is_low and self._glitch_timer.isActive():
            self._glitch_timer.stop()

        # Emit charging transition signals
        if is_charging and not self._was_charging:
            self._was_charging = True
            self.charging_started.emit(percent)
        elif not is_charging and self._was_charging:
            self._was_charging = False
            self.charging_stopped.emit()

        self.battery_updated.emit(percent, is_charging, is_low)

    def _on_glitch_tick(self):
        if self.is_low_battery:
            self.glitch_triggered.emit()
