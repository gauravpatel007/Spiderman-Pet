"""Bridge exposing application settings and global search to Qt Quick / QML."""
import logging
from typing import Any, Dict, List, Optional
from PySide6.QtCore import QObject, Signal, Slot, Property
from services.settings_service import get_settings, SettingsService

logger = logging.getLogger("SpiderBuddy.Bridge.Settings")


class SettingsBridge(QObject):
    """QObject wrapper around SettingsService for reactive QML bindings."""

    # Navigation signal: (tabIndex, sectionId, controlKey)
    navigationRequested = Signal(int, str, str)
    settingChanged = Signal(str, "QVariant")
    themeChanged = Signal(str)
    reducedMotionChanged = Signal(bool)

    # Search Catalog with everyday aliases mapping to authoritative locations
    SEARCH_INDEX = [
        {
            "id": "music_reaction",
            "title": "Audio Reaction & Beat Bobbing",
            "category": "Activities",
            "path": "Activities > Music & Sound",
            "tabIndex": 2,
            "sectionId": "music_sound",
            "controlKey": "audio_reaction",
            "aliases": ["music", "headphones", "dance to audio", "beat", "bobbing", "audio", "song"]
        },
        {
            "id": "sound_volume",
            "title": "Companion Sound Effects & Volume",
            "category": "Activities",
            "path": "Activities > Music & Sound",
            "tabIndex": 2,
            "sectionId": "music_sound",
            "controlKey": "sound_volume",
            "aliases": ["sound", "volume", "sfx", "audio", "chime", "mute"]
        },
        {
            "id": "battery_charging",
            "title": "Battery Charging Reaction & Visual Effects",
            "category": "Activities",
            "path": "Activities > System Reactions",
            "tabIndex": 2,
            "sectionId": "system_reactions",
            "controlKey": "battery_charging",
            "aliases": ["battery", "charging", "charger", "power", "plugged in", "venom strike", "stark tech", "bio electricity"]
        },
        {
            "id": "target_applications",
            "title": "Selected Applications & Windows",
            "category": "Desktop & Apps",
            "path": "Desktop & Apps > Target Applications",
            "tabIndex": 3,
            "sectionId": "applications",
            "controlKey": "target_apps",
            "aliases": ["chrome", "selected apps", "applications", "vscode", "window", "spotify"]
        },
        {
            "id": "character_size",
            "title": "Character Size & Scale",
            "category": "Characters",
            "path": "Characters > Appearance",
            "tabIndex": 1,
            "sectionId": "appearance",
            "controlKey": "scale",
            "aliases": ["size", "bigger", "smaller", "scale", "zoom", "large"]
        },
        {
            "id": "character_opacity",
            "title": "Character Opacity & Transparency",
            "category": "Characters",
            "path": "Characters > Appearance",
            "tabIndex": 1,
            "sectionId": "appearance",
            "controlKey": "opacity",
            "aliases": ["transparent", "opacity", "see through", "fade", "alpha"]
        },
        {
            "id": "focus_mode",
            "title": "Focus Mode",
            "category": "Focus & Breaks",
            "path": "Focus & Breaks > Focus Mode",
            "tabIndex": 4,
            "sectionId": "focus",
            "controlKey": "focus_mode",
            "aliases": ["stop moving", "study", "focus", "quiet", "do not disturb", "pause movement"]
        },
        {
            "id": "comic_reading",
            "title": "Comic Reading Mode",
            "category": "Focus & Breaks",
            "path": "Focus & Breaks > Quiet Modes",
            "tabIndex": 4,
            "sectionId": "quiet_modes",
            "controlKey": "comic_reading",
            "aliases": ["comic", "book", "reading", "sit and read", "quiet"]
        },
        {
            "id": "eye_break_reminder",
            "title": "Eye-Break & Hydration Reminders",
            "category": "Focus & Breaks",
            "path": "Focus & Breaks > Health & Reminders",
            "tabIndex": 4,
            "sectionId": "reminders",
            "controlKey": "eye_break",
            "aliases": ["break", "water", "hydration", "timer", "health", "rest eyes", "20-20-20"]
        },
        {
            "id": "keyboard_shortcuts",
            "title": "Keyboard Shortcuts & Hotkeys",
            "category": "Controls",
            "path": "Controls > Shortcuts",
            "tabIndex": 5,
            "sectionId": "shortcuts",
            "controlKey": "hotkeys",
            "aliases": ["keyboard", "number keys", "hotkeys", "shortcuts", "win+1", "bindings"]
        },
        {
            "id": "spider_sense_dodge",
            "title": "Spider-Sense Cursor Dodge",
            "category": "Controls",
            "path": "Controls > Spider-Sense",
            "tabIndex": 5,
            "sectionId": "spider_sense",
            "controlKey": "spider_sense_dodge",
            "aliases": ["spider sense", "dodge", "cursor", "evade", "tingle", "reflex"]
        },
        {
            "id": "click_through",
            "title": "Click-Through Mode",
            "category": "Controls",
            "path": "Controls > Mouse Interaction",
            "tabIndex": 5,
            "sectionId": "mouse",
            "controlKey": "click_through",
            "aliases": ["click through", "mouse transparent", "ignore click", "transparent input"]
        },
        {
            "id": "reduced_motion",
            "title": "Reduced UI Motion",
            "category": "Settings",
            "path": "Settings > Performance",
            "tabIndex": 6,
            "sectionId": "performance",
            "controlKey": "reduced_motion",
            "aliases": ["reduced motion", "animations off", "disable animation", "fast ui"]
        },
        {
            "id": "theme_mode",
            "title": "Color Theme (Dark / Light / System)",
            "category": "Settings",
            "path": "Settings > Appearance",
            "tabIndex": 6,
            "sectionId": "appearance",
            "controlKey": "theme",
            "aliases": ["dark mode", "light mode", "theme", "colors", "charcoal", "style"]
        },
        {
            "id": "windows_startup",
            "title": "Launch on Windows Startup",
            "category": "Settings",
            "path": "Settings > System",
            "tabIndex": 6,
            "sectionId": "system",
            "controlKey": "run_on_startup",
            "aliases": ["startup", "boot", "autostart", "windows launch", "start with windows"]
        }
    ]

    def __init__(self, settings_service: Optional[SettingsService] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._settings = settings_service or get_settings()
        self._settings.setting_changed.connect(self._on_service_setting_changed)

    def _on_service_setting_changed(self, key_path: str, new_value: Any):
        self.settingChanged.emit(key_path, new_value)
        if key_path == "ui.theme":
            self.themeChanged.emit(str(new_value))
        elif key_path == "ui.reduced_motion":
            self.reducedMotionChanged.emit(bool(new_value))

    # --- Property Accessors ---

    def _get_theme(self) -> str:
        return str(self._settings.get("ui.theme", "dark"))

    def _set_theme(self, val: str):
        self._settings.set("ui.theme", val)

    theme = Property(str, _get_theme, _set_theme, notify=themeChanged)

    def _get_reduced_motion(self) -> bool:
        return bool(self._settings.get("ui.reduced_motion", False))

    def _set_reduced_motion(self, val: bool):
        self._settings.set("ui.reduced_motion", val)

    reducedMotion = Property(bool, _get_reduced_motion, _set_reduced_motion, notify=reducedMotionChanged)

    # --- QML Invokable Methods ---

    @Slot(str, result="QVariant")
    def get(self, key_path: str) -> Any:
        """Read setting from backend."""
        return self._settings.get(key_path, None)

    @Slot(str, "QVariant", result="QVariant")
    def getWithDefault(self, key_path: str, default_val: Any) -> Any:
        """Read setting with explicit fallback."""
        val = self._settings.get(key_path, default_val)
        return val if val is not None else default_val

    @Slot(str, "QVariant")
    def set(self, key_path: str, value: Any):
        """Write setting and persist."""
        self._settings.set(key_path, value)

    @Slot()
    def resetToDefaults(self):
        """Restore defaults."""
        self._settings.reset_to_defaults()

    @Slot(str, result="QVariantList")
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search settings catalog with aliases and terms."""
        clean_q = query.strip().lower()
        if not clean_q:
            return []

        results = []
        for item in self.SEARCH_INDEX:
            score = 0
            # Title match
            if clean_q in item["title"].lower():
                score += 10
            # Category match
            if clean_q in item["category"].lower():
                score += 5
            # Aliases match
            for alias in item["aliases"]:
                if clean_q == alias:
                    score += 20
                elif clean_q in alias:
                    score += 8

            if score > 0:
                results.append({
                    "id": item["id"],
                    "title": item["title"],
                    "category": item["category"],
                    "path": item["path"],
                    "tabIndex": item["tabIndex"],
                    "sectionId": item["sectionId"],
                    "controlKey": item["controlKey"],
                    "score": score
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    @Slot(int, str, str)
    def requestNavigation(self, tab_index: int, section_id: str, control_key: str):
        """Emit navigation requested to switch tab, scroll and highlight."""
        self.navigationRequested.emit(tab_index, section_id, control_key)
