"""Eye-break health reminder and focus timer service."""
import logging
import time
from typing import Optional
from PySide6.QtCore import QObject, QTimer, Signal
from .settings_service import get_settings

logger = logging.getLogger("SpiderBuddy.EyeBreakService")


class EyeBreakService(QObject):
    """
    Monitors continuous typing and work duration (default 60 minutes) and
    manages optional focus timers. When time is up, emits alerts for Spider-Man
    to web the corner of the screen and tap with a 'Time for water, man!' reminder.
    """

    # Emitted when an alert should be triggered: (title, message, alert_type)
    alert_triggered = Signal(str, str, str)

    # Periodic status update: (continuous_active_sec, timer_remaining_sec, timer_active)
    status_updated = Signal(float, float, bool)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.settings = get_settings()

        self._continuous_active_seconds: float = 0.0
        self._break_idle_threshold_seconds: float = 120.0  # 2 min idle counts as a real break

        # Optional countdown focus/work timer (in seconds)
        self._focus_timer_seconds: float = 0.0
        self._focus_timer_active: bool = False
        self._last_alert_time: float = 0.0
        self._cooldown_seconds: float = 600.0  # strictly at least 10 minutes cooldown between alerts

        # 1-second cadence timer
        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._on_tick)

        self._current_idle_seconds: float = 0.0

    def start(self) -> None:
        """Start tracking continuous typing and focus timer."""
        self._ticker.start()
        logger.info("EyeBreakService started.")

    def stop(self) -> None:
        """Stop tracking."""
        self._ticker.stop()
        logger.info("EyeBreakService stopped.")

    def on_idle_tick(self, idle_seconds: float) -> None:
        """Receive idle duration updates from ActivityMonitor."""
        self._current_idle_seconds = float(idle_seconds)

    def start_focus_timer(self, minutes: float) -> None:
        """Start an explicit focus countdown timer in minutes."""
        self._focus_timer_seconds = max(1.0, float(minutes) * 60.0)
        self._focus_timer_active = True
        logger.info("Focus timer started for %.1f minutes.", minutes)
        self._emit_status()

    def stop_focus_timer(self) -> None:
        """Cancel or reset the focus countdown timer."""
        self._focus_timer_active = False
        self._focus_timer_seconds = 0.0
        logger.info("Focus timer stopped.")
        self._emit_status()

    def is_focus_timer_active(self) -> bool:
        return self._focus_timer_active

    def get_continuous_active_seconds(self) -> float:
        return self._continuous_active_seconds

    def get_focus_timer_remaining_seconds(self) -> float:
        return self._focus_timer_seconds

    def reset_continuous_typing(self) -> None:
        """Reset continuous active typing timer."""
        self._continuous_active_seconds = 0.0
        self._emit_status()

    def trigger_test_alert(self) -> None:
        """Manually trigger an eye-break water alert for preview and testing."""
        logger.info("Triggering test eye-break alert.")
        self._last_alert_time = time.monotonic()
        self.alert_triggered.emit(
            "💧 TIME FOR WATER, MAN!",
            "Take a 20-second eye break & drink some water! Stay hydrated, hero!",
            "test",
        )

    def _on_tick(self) -> None:
        """Handle 1-second timer tick."""
        enabled = self.settings.get("behavior.enable_eye_break_alert", True)

        # 1. Update continuous active typing/work time
        if self._current_idle_seconds < self._break_idle_threshold_seconds:
            # User is actively working
            self._continuous_active_seconds += 1.0
        else:
            # User took a rest break >= 2 mins: reset continuous counter
            if self._continuous_active_seconds > 0.0:
                logger.debug("User took break; resetting continuous active time.")
                self._continuous_active_seconds = 0.0

        now = time.monotonic()

        # 2. Check continuous typing threshold (strictly at least 10 minutes)
        raw_limit = float(self.settings.get("behavior.eye_break_minutes", 10.0))
        limit_minutes = max(10.0, raw_limit)
        limit_seconds = limit_minutes * 60.0

        if enabled and (self._continuous_active_seconds >= limit_seconds):
            if (now - self._last_alert_time) >= self._cooldown_seconds:
                self._last_alert_time = now
                self._continuous_active_seconds = 0.0
                logger.info("Continuous typing threshold reached (%.1f mins). Firing alert.", limit_minutes)
                mins_str = f"{int(limit_minutes)} minutes"
                self.alert_triggered.emit(
                    "💧 TIME FOR WATER, MAN!",
                    f"You've been typing for {mins_str} straight! Rest your eyes & take a water break!",
                    "typing_alert",
                )

        # 3. Check focus countdown timer
        if self._focus_timer_active:
            self._focus_timer_seconds -= 1.0
            if self._focus_timer_seconds <= 0.0:
                self._focus_timer_active = False
                self._focus_timer_seconds = 0.0
                if enabled and (now - self._last_alert_time) >= self._cooldown_seconds:
                    self._last_alert_time = now
                    logger.info("Focus countdown timer finished. Firing alert.")
                    self.alert_triggered.emit(
                        "⏰ FOCUS TIMER FINISHED!",
                        "Time for water, man! Take a stretch and give your eyes a break!",
                        "timer_ended",
                    )

        self._emit_status()

    def _emit_status(self) -> None:
        self.status_updated.emit(
            self._continuous_active_seconds,
            self._focus_timer_seconds,
            self._focus_timer_active,
        )
