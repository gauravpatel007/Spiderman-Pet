"""Status model providing companion live telemetry and quick controls to QML."""
import logging
from typing import Optional, Any
from PySide6.QtCore import QObject, Signal, Slot, Property
from services.settings_service import get_settings

logger = logging.getLogger("SpiderBuddy.Bridge.Status")


class StatusModel(QObject):
    """Exposes live status (paused, target app, focus mode, battery) to QML."""

    pausedChanged = Signal(bool)
    hiddenChanged = Signal(bool)
    focusModeChanged = Signal(bool)
    activeActivityChanged = Signal(str)
    currentTargetChanged = Signal(str)
    batteryPercentChanged = Signal(int)
    isChargingChanged = Signal(bool)
    cpuPercentChanged = Signal(int)

    # Action requests to backend
    pauseToggleRequested = Signal(bool)
    hideToggleRequested = Signal(bool)
    focusToggleRequested = Signal(bool)
    customPositionSaveRequested = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._settings = get_settings()
        self._is_paused = False
        self._is_hidden = False
        self._is_focus = bool(self._settings.get("behavior.focus_mode", False))
        self._active_activity = "Idle & Look Around"
        self._current_target = "Entire Desktop (All Monitors)"
        self._battery_percent = 95
        self._is_charging = False
        self._cpu_percent = 4

    # --- Property Getters / Setters ---

    def _get_paused(self) -> bool:
        return self._is_paused

    @Slot(bool)
    def setPaused(self, val: bool):
        if self._is_paused != val:
            self._is_paused = val
            self.pausedChanged.emit(val)

    isPaused = Property(bool, _get_paused, setPaused, notify=pausedChanged)

    def _get_hidden(self) -> bool:
        return self._is_hidden

    @Slot(bool)
    def setHidden(self, val: bool):
        if self._is_hidden != val:
            self._is_hidden = val
            self.hiddenChanged.emit(val)

    isHidden = Property(bool, _get_hidden, setHidden, notify=hiddenChanged)

    def _get_focus(self) -> bool:
        return self._is_focus

    @Slot(bool)
    def setFocusMode(self, val: bool):
        if self._is_focus != val:
            self._is_focus = val
            self._settings.set("behavior.focus_mode", val)
            self.focusModeChanged.emit(val)

    isFocusMode = Property(bool, _get_focus, setFocusMode, notify=focusModeChanged)

    def _get_activity(self) -> str:
        return self._active_activity

    @Slot(str)
    def setActiveActivity(self, val: str):
        if self._active_activity != val:
            self._active_activity = val
            self.activeActivityChanged.emit(val)

    activeActivity = Property(str, _get_activity, setActiveActivity, notify=activeActivityChanged)

    def _get_target(self) -> str:
        return self._current_target

    @Slot(str)
    def setCurrentTarget(self, val: str):
        if self._current_target != val:
            self._current_target = val
            self.currentTargetChanged.emit(val)

    currentTarget = Property(str, _get_target, setCurrentTarget, notify=currentTargetChanged)

    def _get_battery(self) -> int:
        return self._battery_percent

    @Slot(int)
    def setBatteryPercent(self, val: int):
        if self._battery_percent != val:
            self._battery_percent = val
            self.batteryPercentChanged.emit(val)

    batteryPercent = Property(int, _get_battery, setBatteryPercent, notify=batteryPercentChanged)

    def _get_charging(self) -> bool:
        return self._is_charging

    @Slot(bool)
    def setCharging(self, val: bool):
        if self._is_charging != val:
            self._is_charging = val
            self.isChargingChanged.emit(val)

    isCharging = Property(bool, _get_charging, setCharging, notify=isChargingChanged)

    def _get_cpu(self) -> int:
        return self._cpu_percent

    @Slot(int)
    def setCpuPercent(self, val: int):
        if self._cpu_percent != val:
            self._cpu_percent = val
            self.cpuPercentChanged.emit(val)

    cpuPercent = Property(int, _get_cpu, setCpuPercent, notify=cpuPercentChanged)

    # --- QML Invokable Control Slots ---

    @Slot()
    def togglePause(self):
        self.setPaused(not self._is_paused)
        self.pauseToggleRequested.emit(self._is_paused)

    @Slot()
    def toggleHide(self):
        self.setHidden(not self._is_hidden)
        self.hideToggleRequested.emit(self._is_hidden)

    @Slot()
    def toggleFocus(self):
        self.setFocusMode(not self._is_focus)
        self.focusToggleRequested.emit(self._is_focus)

    @Slot()
    def saveCustomPosition(self):
        self.customPositionSaveRequested.emit()
