"""Services package for Spider-Buddy."""
from .settings_service import SettingsService, get_settings
from .startup_service import StartupService
from .activity_monitor import ActivityMonitor
from .session_manager import SessionManager
from .battery_service import BatteryService
from .hotkey_service import HotkeyService, HOTKEY_MAPPINGS
from .eye_break_service import EyeBreakService
from .system_load_service import SystemLoadService
from .audio_sync_service import AudioSyncService
from .companion_stats import CompanionStatsService

__all__ = [
    "SettingsService",
    "get_settings",
    "StartupService",
    "ActivityMonitor",
    "SessionManager",
    "BatteryService",
    "HotkeyService",
    "HOTKEY_MAPPINGS",
    "EyeBreakService",
    "SystemLoadService",
    "AudioSyncService",
    "CompanionStatsService",
]
