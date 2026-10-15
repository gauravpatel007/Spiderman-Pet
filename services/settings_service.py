"""Centralized settings management for Spider-Buddy."""
import json
import logging
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("SpiderBuddy.SettingsService")


class SettingsService(QObject):
    """Manages application settings with persistent JSON storage and reactive notifications."""

    # Signal emitted when any setting changes: (key_path, new_value)
    setting_changed = Signal(str, object)
    settings_reloaded = Signal()

    _instance: Optional["SettingsService"] = None

    def __init__(self, config_dir: Optional[Path] = None):
        super().__init__()
        import sys
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
            self.project_root = base
        else:
            self.project_root = Path(__file__).resolve().parent.parent
        self.default_config_path = self.project_root / "config" / "default_settings.json"

        # Dedicated user storage directory in %APPDATA%/SpiderBuddy or local fallback
        if config_dir:
            self.user_dir = config_dir
        else:
            appdata = os.getenv("APPDATA")
            if appdata:
                self.user_dir = Path(appdata) / "SpiderBuddy"
            else:
                self.user_dir = Path.home() / ".spider-buddy"
        
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.user_dir / "settings.json"

        self._settings: Dict[str, Any] = {}
        self.load()

    @classmethod
    def get_instance(cls) -> "SettingsService":
        if cls._instance is None:
            cls._instance = SettingsService()
        return cls._instance

    def _load_defaults(self) -> Dict[str, Any]:
        """Load default configuration from config/default_settings.json."""
        if self.default_config_path.exists():
            try:
                with open(self.default_config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read default_settings.json: {e}")
        return {
            "general": {
                "character": "miles_morales",
                "display_mode": "desktop",
                "target_applications": ["Antigravity", "Visual Studio Code", "Google Chrome", "ChatGPT"],
                "scale": 1.0,
                "opacity": 1.0,
                "animation_speed": 1.0
            },
            "behavior": {
                "movement_speed": 3.0,
                "idle_timeout_seconds": 15,
                "sleep_after_minutes": 5,
                "enable_climbing": True,
                "enable_swinging": True,
                "enable_spider_sense_dodging": True,
                "enable_comic_bubbles": True,
                "sound_enabled": True
            },
            "animations": {
                "enable_window_perching": True,
                "title_bar_offset": 28,
                "enabled": {
                    "idle": True, "walk": True, "run": True, "jump": True, "fall": True,
                    "land": True, "climb_up": True, "climb_down": True, "wall_slide": True,
                    "perch": True, "swing": True, "hang": True, "sleep": True, "wake_up": True,
                    "sit": True, "stand_up": True, "wave": True, "dance": True,
                    "celebrate": True, "interact": True, "dragged": True,
                    "title_perch": True, "title_hang": True, "focus_read": True
                }
            },
            "system": {
                "run_on_startup": False,
                "start_minimized": True,
                "always_on_top": True,
                "click_through": False
            }
        }

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge override dictionary into base dictionary."""
        result = deepcopy(base)
        for key, value in override.items():
            if key in result and not self._valid_type(result[key], value):
                logger.warning("Ignoring invalid type for setting %s", key)
                continue
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _valid_type(default, value):
        if isinstance(default, bool):
            return isinstance(value, bool)
        if isinstance(default, (int, float)):
            import math
            return type(value) in (int, float) and math.isfinite(value)
        return isinstance(value, type(default))

    def load(self) -> None:
        """Load settings from disk, applying defaults for missing entries."""
        defaults = self._load_defaults()
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                    if not isinstance(user_data, dict):
                        raise ValueError("Settings must be a JSON object")
                    self._settings = self._deep_merge(defaults, user_data)
                    logger.info(f"Settings loaded successfully from {self.settings_file}")
            except Exception as e:
                logger.warning(f"Could not parse user settings, using defaults. Error: {e}")
                self._settings = defaults
        else:
            logger.info("User settings file not found. Initializing with defaults.")
            self._settings = defaults
            self.save()

        self.settings_reloaded.emit()

    def save(self) -> bool:
        """Replace settings atomically so interruption cannot truncate them."""
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.user_dir,
                                             prefix="settings-", suffix=".tmp", delete=False) as f:
                temp_path = Path(f.name)
                json.dump(self._settings, f, indent=2, allow_nan=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.settings_file)
            logger.debug(f"Settings saved to {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings to {self.settings_file}: {e}")
            return False
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Retrieve a setting value using a dot-separated key (e.g. 'general.character').
        """
        keys = key_path.split(".")
        current = self._settings
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return deepcopy(current)

    def set(self, key_path: str, value: Any, auto_save: bool = True) -> None:
        """
        Update a setting value using a dot-separated key and notify observers.
        """
        keys = key_path.split(".")
        current = self._settings
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        old_value = current.get(keys[-1])
        if old_value != value:
            current[keys[-1]] = deepcopy(value)
            if auto_save:
                self.save()
            self.setting_changed.emit(key_path, value)
            logger.info(f"Setting updated: {key_path} = {value}")

    def reset_to_defaults(self) -> None:
        """Reset all configuration values to factory defaults."""
        self._settings = self._load_defaults()
        self.save()
        self.settings_reloaded.emit()
        logger.info("Settings reset to defaults.")


def get_settings() -> SettingsService:
    """Convenience accessor for global SettingsService instance."""
    return SettingsService.get_instance()
