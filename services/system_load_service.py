"""System hardware load monitoring service (CPU & RAM) for Spider-Buddy."""
import ctypes
from ctypes import wintypes
import logging
import sys
import time
from typing import Any, Optional, Tuple
from PySide6.QtCore import QObject, QTimer, Signal
from .settings_service import get_settings

logger = logging.getLogger("SpiderBuddy.SystemLoadService")


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", ctypes.c_ulong),
        ("dwHighDateTime", ctypes.c_ulong),
    ]


def _filetime_to_int(ft: FILETIME) -> int:
    return (ft.dwHighDateTime << 32) + ft.dwLowDateTime


class SystemLoadService(QObject):
    """
    Monitors CPU and RAM utilization using native Windows Win32 APIs.
    When either CPU or RAM exceeds 85% (heavy compilation, game, or rendering),
    emits signals for Spider-Man to sweat, pant, or lift a collapsing steel beam.
    """

    # Emits (cpu_percent: float, ram_percent: float, is_heavy_load: bool)
    load_updated = Signal(float, float, bool)

    # Emits when entering or exiting heavy load mode: (is_heavy: bool, cpu: float, ram: float)
    heavy_load_changed = Signal(bool, float, float)

    def __init__(self, check_interval_ms: int = 1500, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.settings = get_settings()
        self.check_interval_ms = check_interval_ms

        self._has_win32 = sys.platform == "win32"
        self._last_cpu_times: Optional[Tuple[int, int, int]] = None

        self._current_cpu: float = 0.0
        self._current_ram: float = 0.0
        self._is_heavy_load: bool = False
        self._simulated_heavy_load: bool = False

        # Hysteresis thresholds: Enter at 85%, exit below 75%
        self._threshold_enter: float = 85.0
        self._threshold_exit: float = 75.0

        self._timer = QTimer(self)
        self._timer.setInterval(self.check_interval_ms)
        self._timer.timeout.connect(self._check_load)

        self.settings.setting_changed.connect(self._on_setting_changed)

    def start(self) -> None:
        """Start monitoring system resource utilization."""
        self._sample_cpu_times()
        self._timer.start()
        logger.info("SystemLoadService started (polling every %dms).", self.check_interval_ms)

    def stop(self) -> None:
        """Stop monitoring."""
        self._timer.stop()
        logger.info("SystemLoadService stopped.")

    def get_cpu_percent(self) -> float:
        return self._current_cpu

    def get_ram_percent(self) -> float:
        return self._current_ram

    def is_heavy_load(self) -> bool:
        return self._is_heavy_load

    def sample_metrics(self) -> Tuple[float, float]:
        """Sample and return immediate (cpu_percent, ram_percent) tuple."""
        cpu = self._calculate_cpu_percent()
        ram = self._calculate_ram_percent()
        return cpu, ram

    def simulate_heavy_load(self, simulate: bool) -> None:
        """Manually force heavy load state for testing and animation preview."""
        self._simulated_heavy_load = bool(simulate)
        logger.info("Heavy load simulation set to: %s", self._simulated_heavy_load)
        if not self._simulated_heavy_load and self._is_heavy_load:
            self._is_heavy_load = False
            self.heavy_load_changed.emit(False, 0.0, 0.0)
        else:
            self._check_load()

    def _on_setting_changed(self, key: str, value: Any) -> None:
        if key in ("behavior.enable_heavy_load_scene", "behavior.enable_heavy_load_reaction") and not value:
            if self._is_heavy_load:
                self._is_heavy_load = False
                logger.info("Heavy load feature disabled by user; clearing active heavy load scene.")
                self.heavy_load_changed.emit(False, self._current_cpu, self._current_ram)

    def _sample_cpu_times(self) -> Optional[Tuple[int, int, int]]:
        if not self._has_win32:
            return None
        try:
            idle = FILETIME()
            kernel = FILETIME()
            user = FILETIME()
            if ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
            ):
                self._last_cpu_times = (
                    _filetime_to_int(idle),
                    _filetime_to_int(kernel),
                    _filetime_to_int(user),
                )
                return self._last_cpu_times
        except Exception as exc:
            logger.debug("Failed GetSystemTimes: %s", exc)
        return None

    def _calculate_cpu_percent(self) -> float:
        if not self._has_win32 or not self._last_cpu_times:
            self._sample_cpu_times()
            return 0.0

        prev_idle, prev_kernel, prev_user = self._last_cpu_times
        current_times = self._sample_cpu_times()
        if not current_times:
            return 0.0

        curr_idle, curr_kernel, curr_user = current_times
        idle_diff = curr_idle - prev_idle
        kernel_diff = curr_kernel - prev_kernel
        user_diff = curr_user - prev_user
        total = kernel_diff + user_diff

        if total <= 0:
            return 0.0

        cpu = (1.0 - (idle_diff / float(total))) * 100.0
        return max(0.0, min(100.0, cpu))

    def _calculate_ram_percent(self) -> float:
        if not self._has_win32:
            return 0.0
        try:
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
                return float(mem.dwMemoryLoad)
        except Exception as exc:
            logger.debug("Failed GlobalMemoryStatusEx: %s", exc)
        return 0.0

    def _check_load(self) -> None:
        if self._simulated_heavy_load:
            self._current_cpu = 92.0
            self._current_ram = 89.0
        else:
            self._current_cpu = self._calculate_cpu_percent()
            self._current_ram = self._calculate_ram_percent()

        threshold = float(self.settings.get("behavior.heavy_load_threshold", self._threshold_enter))
        enabled = self.settings.get("behavior.enable_heavy_load_scene", self.settings.get("behavior.enable_heavy_load_reaction", True))

        max_metric = max(self._current_cpu, self._current_ram)
        metric_name = "CPU" if self._current_cpu >= self._current_ram else "RAM"

        was_heavy = self._is_heavy_load
        if enabled:
            if not was_heavy and (max_metric >= threshold):
                self._is_heavy_load = True
                logger.info(
                    "System heavy load entered! %s at %.1f%% (CPU: %.1f%%, RAM: %.1f%%)",
                    metric_name, max_metric, self._current_cpu, self._current_ram,
                )
                self.heavy_load_changed.emit(True, self._current_cpu, self._current_ram)
            elif was_heavy and (max_metric < self._threshold_exit):
                self._is_heavy_load = False
                logger.info(
                    "System heavy load cleared. (CPU: %.1f%%, RAM: %.1f%%)",
                    self._current_cpu, self._current_ram,
                )
                self.heavy_load_changed.emit(False, self._current_cpu, self._current_ram)
        else:
            if was_heavy:
                self._is_heavy_load = False
                self.heavy_load_changed.emit(False, self._current_cpu, self._current_ram)

        self.load_updated.emit(self._current_cpu, self._current_ram, self._is_heavy_load)
