"""Companion daily usage and gameplay statistics service for Spider-Buddy."""
from datetime import date
import logging
import math
import time
from typing import Dict, Optional
from PySide6.QtCore import QObject, Signal, QTimer
from .settings_service import get_settings

logger = logging.getLogger("SpiderBuddy.CompanionStats")


class CompanionStatsService(QObject):
    """
    Tracks daily desktop companionship metrics:
    - Distance crawled / traveled across user windows (in pixels)
    - Web lines shot / web swings triggered
    - Active companion interaction time
    """

    # Emits dictionary with formatted metrics on change
    stats_updated = Signal(dict)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.settings = get_settings()
        self._today_str = date.today().isoformat()
        self._stats: Dict[str, object] = {
            "date": self._today_str,
            "distance_px": 0.0,
            "webs_shot": 0,
            "active_seconds": 0,
        }
        self._load_stats()
        self._last_x: Optional[int] = None
        self._last_y: Optional[int] = None

        # 1-second cadence timer for active session duration
        self._active_timer = QTimer(self)
        self._active_timer.setInterval(1000)
        self._active_timer.timeout.connect(self._on_second_tick)

    def _load_stats(self) -> None:
        """Load stored stats from settings or initialize for today."""
        stored = self.settings.get("stats", {})
        if isinstance(stored, dict) and stored.get("date") == self._today_str:
            self._stats["distance_px"] = float(stored.get("distance_px", 0.0))
            self._stats["webs_shot"] = int(stored.get("webs_shot", 0))
            self._stats["active_seconds"] = int(stored.get("active_seconds", 0))
        else:
            self._save_stats()

    def _save_stats(self) -> None:
        """Persist current metrics to settings file."""
        self.settings.set("stats", self._stats)

    def start(self) -> None:
        """Start tracking companion active time."""
        if not self._active_timer.isActive():
            self._active_timer.start()
        self.stats_updated.emit(self.get_formatted_stats())
        logger.info("CompanionStatsService started.")

    def stop(self) -> None:
        """Pause tracking."""
        self._active_timer.stop()
        self._save_stats()
        logger.info("CompanionStatsService stopped.")

    def reset_stats(self) -> None:
        """Reset all tracked gameplay statistics to zero."""
        self._stats = {
            "date": self._today_str,
            "distance_px": 0.0,
            "webs_shot": 0,
            "active_seconds": 0,
        }
        self._last_x = None
        self._last_y = None
        self._save_stats()
        self.stats_updated.emit(self.get_formatted_stats())
        logger.info("CompanionStatsService reset to zero.")

    def record_movement(self, x: int, y: int) -> None:
        """Accumulate distance traveled in pixels."""
        if self._last_x is not None and self._last_y is not None:
            dist = math.hypot(x - self._last_x, y - self._last_y)
            # Filter out instantaneous monitor teleports / resets (> 600px)
            if 0.5 < dist < 600:
                self._stats["distance_px"] = float(self._stats["distance_px"]) + dist
                # Physics can report several substeps per frame. Publish via
                # the existing one-second timer, not hundreds of browser IPCs.
        self._last_x = int(x)
        self._last_y = int(y)

    def record_web_swing(self) -> None:
        """Increment count of webs shot."""
        self._stats["webs_shot"] = int(self._stats["webs_shot"]) + 1
        self.settings.set("stats", self._stats, auto_save=False)
        self.stats_updated.emit(self.get_formatted_stats())

    def _on_second_tick(self) -> None:
        """Tick active companion time every second."""
        today = date.today().isoformat()
        if today != self._today_str:
            # Rollover at midnight
            self._today_str = today
            self._stats = {
                "date": self._today_str,
                "distance_px": 0.0,
                "webs_shot": 0,
                "active_seconds": 0,
            }

        self._stats["active_seconds"] = int(self._stats["active_seconds"]) + 1
        # Periodic persist every 15 seconds
        if int(self._stats["active_seconds"]) % 15 == 0:
            self._save_stats()
        self.stats_updated.emit(self.get_formatted_stats())

    def get_formatted_stats(self) -> dict:
        """Return formatted user-facing metrics."""
        dist = float(self._stats.get("distance_px", 0.0))
        webs = int(self._stats.get("webs_shot", 0))
        secs = int(self._stats.get("active_seconds", 0))

        # Format distance
        if dist >= 1000:
            dist_str = f"{int(dist):,} px"
        else:
            dist_str = f"{int(dist)} px"

        # Format active time
        hours = secs // 3600
        mins = (secs % 3600) // 60
        s = secs % 60
        if hours > 0:
            time_str = f"{hours}h {mins}m"
        elif mins > 0:
            time_str = f"{mins}m {s}s"
        else:
            time_str = f"{s}s"

        return {
            "distance_px": dist,
            "distance_text": dist_str,
            "webs_shot": webs,
            "webs_text": f"{webs} {'swing' if webs == 1 else 'swings'}",
            "active_seconds": secs,
            "active_text": time_str,
        }
