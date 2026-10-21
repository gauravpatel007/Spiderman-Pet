"""Activity library model providing categorized activities, filtering, and preview controls to QML."""
import logging
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, QByteArray, Slot, Property, Signal, QObject
from services.settings_service import get_settings

logger = logging.getLogger("SpiderBuddy.Bridge.Activity")


class ActivityModel(QAbstractListModel):
    """Categorized activity catalog with search, filter, and state toggles."""

    IdRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    CategoryRole = Qt.UserRole + 3
    DescriptionRole = Qt.UserRole + 4
    EnabledRole = Qt.UserRole + 5
    PreviewRole = Qt.UserRole + 6
    IsAnimatingRole = Qt.UserRole + 7
    HasOptionsRole = Qt.UserRole + 8

    # Activity Catalog
    ACTIVITIES_DEF = [
        # Movement
        {"id": "walk", "name": "Walk & Stroll", "category": "Movement", "desc": "Casual walking along borders and taskbar", "has_options": False},
        {"id": "run", "name": "Run & Sprint", "category": "Movement", "desc": "Energetic dashing across the screen", "has_options": False},
        {"id": "jump", "name": "Jump & Leap", "category": "Movement", "desc": "Acrobatic leaps between window surfaces", "has_options": False},
        {"id": "climb_up", "name": "Climb Up", "category": "Movement", "desc": "Vertical climbing up window sides", "has_options": False},
        {"id": "climb_down", "name": "Climb Down", "category": "Movement", "desc": "Descending window borders smoothly", "has_options": False},
        {"id": "wall_slide", "name": "Wall Slide", "category": "Movement", "desc": "Sliding down side edges", "has_options": False},
        {"id": "swing", "name": "Web Swing", "category": "Movement", "desc": "Dynamic web swinging across the screen", "has_options": True},

        # Rest & Poses
        {"id": "idle", "name": "Idle & Look Around", "category": "Rest & Poses", "desc": "Observant resting posture and glances", "has_options": False},
        {"id": "sit", "name": "Sit & Chill", "category": "Rest & Poses", "desc": "Sitting relaxed on taskbar or windows", "has_options": False},
        {"id": "sleep", "name": "Sleep & Nap", "category": "Rest & Poses", "desc": "Curled up nap after inactivity", "has_options": True},
        {"id": "wake_up", "name": "Wake Up", "category": "Rest & Poses", "desc": "Stretching and awakening from sleep", "has_options": False},
        {"id": "stand_up", "name": "Stand Up", "category": "Rest & Poses", "desc": "Transitioning back to active stance", "has_options": False},
        {"id": "perch", "name": "Squat & Perch", "category": "Rest & Poses", "desc": "Iconic gargoyle crouching pose", "has_options": False},
        {"id": "hang", "name": "Ceiling / Bar Hang", "category": "Rest & Poses", "desc": "Hanging upside down from top edges", "has_options": False},

        # Expressions
        {"id": "wave", "name": "Friendly Wave", "category": "Expressions", "desc": "Greets user with a friendly hand wave", "has_options": False},
        {"id": "dance", "name": "Spider Dance", "category": "Expressions", "desc": "Fun energetic dance celebration", "has_options": False},
        {"id": "celebrate", "name": "Victory Celebration", "category": "Expressions", "desc": "Fist pumps and playful cheers", "has_options": False},
        {"id": "interact", "name": "Click Reaction", "category": "Expressions", "desc": "Responds directly when clicked", "has_options": False},

        # Window Activities
        {"id": "title_perch", "name": "Window Corner Perch", "category": "Window Activities", "desc": "Perches alertly at the top-right corner of active windows", "has_options": True},
        {"id": "title_hang", "name": "Title Bar Hang", "category": "Window Activities", "desc": "Dangles from titlebar or browser tabs", "has_options": True},

        # Music & Sound
        {"id": "music_sync", "name": "Beat Bobbing & Headphones", "category": "Music & Sound", "desc": "Puts on headphones and bobs to playing music", "has_options": True},
        {"id": "sound_effects", "name": "Companion SFX & Chimes", "category": "Music & Sound", "desc": "Plays subtle sound effects during jumps and poses", "has_options": True},

        # Effects & Toys
        {"id": "comic_bubbles", "name": "Comic Speech Bubbles", "category": "Effects & Toys", "desc": "Shows retro comic exclamations (THWIP! POW!)", "has_options": True},
        {"id": "web_trampoline", "name": "Web Trampoline", "category": "Effects & Toys", "desc": "Bounces on an interactive spider-web net", "has_options": False},

        # System Reactions
        {"id": "battery_reaction", "name": "Low Battery Reaction", "category": "System Reactions", "desc": "Looks exhausted or powers down when battery is low", "has_options": True},
        {"id": "system_load_reaction", "name": "Heavy CPU/RAM Reaction", "category": "System Reactions", "desc": "Wipes sweat or dodges frantically under high load", "has_options": True},

        # Transition Poses (Advanced)
        {"id": "fall", "name": "Falling Transition", "category": "Transition Poses", "desc": "Mid-air descent pose (recovery physics always preserved)", "has_options": False},
        {"id": "land", "name": "Landing Recovery", "category": "Transition Poses", "desc": "Dynamic three-point superhero landing", "has_options": False},
        {"id": "dragged", "name": "Cursor Drag Pose", "category": "Transition Poses", "desc": "Dangles by web thread while user drags character", "has_options": False}
    ]

    filterCategoryChanged = Signal(str)
    filterStateChanged = Signal(str)
    searchQueryChanged = Signal(str)
    activePreviewIdChanged = Signal(str)
    modeChanged = Signal(str)
    frequencyChanged = Signal(str)
    timingChanged = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._settings = get_settings()
        self._filter_category = "All"
        self._filter_state = "All"  # All, Enabled, Disabled
        self._search_query = ""
        self._active_preview_id = ""
        self._displayed_items: List[Dict[str, Any]] = []

        self._refresh_list()

    def roleNames(self) -> Dict[int, QByteArray]:
        return {
            self.IdRole: QByteArray(b"activityId"),
            self.NameRole: QByteArray(b"name"),
            self.CategoryRole: QByteArray(b"category"),
            self.DescriptionRole: QByteArray(b"description"),
            self.EnabledRole: QByteArray(b"enabled"),
            self.PreviewRole: QByteArray(b"previewUrl"),
            self.IsAnimatingRole: QByteArray(b"isAnimating"),
            self.HasOptionsRole: QByteArray(b"hasOptions")
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._displayed_items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._displayed_items)):
            return None

        item = self._displayed_items[index.row()]
        act_id = item["id"]

        if role == self.IdRole:
            return act_id
        elif role == self.NameRole:
            return item["name"]
        elif role == self.CategoryRole:
            return item["category"]
        elif role == self.DescriptionRole:
            return item["desc"]
        elif role == self.EnabledRole:
            return self._is_activity_enabled(act_id)
        elif role == self.PreviewRole:
            return f"image://preview/{act_id}"
        elif role == self.IsAnimatingRole:
            return act_id == self._active_preview_id
        elif role == self.HasOptionsRole:
            return item.get("has_options", False)
        return None

    def _is_activity_enabled(self, act_id: str) -> bool:
        # Check specific mapping in settings
        if act_id == "music_sync":
            return bool(self._settings.get("audio.enabled", True))
        elif act_id == "sound_effects":
            return bool(self._settings.get("behavior.sound_enabled", True))
        elif act_id == "comic_bubbles":
            return bool(self._settings.get("behavior.enable_comic_bubbles", True))
        elif act_id == "battery_reaction":
            return bool(self._settings.get("system.enable_battery_reaction", True))
        elif act_id == "system_load_reaction":
            return bool(self._settings.get("system.enable_load_reaction", True))
        
        # General animation enabled dict
        return bool(self._settings.get(f"animations.enabled.{act_id}", True))

    def _refresh_list(self):
        self.beginResetModel()
        filtered = []
        q = self._search_query.strip().lower()

        for item in self.ACTIVITIES_DEF:
            # Category filter
            if self._filter_category != "All" and item["category"] != self._filter_category:
                continue

            # State filter
            is_enabled = self._is_activity_enabled(item["id"])
            if self._filter_state == "Enabled" and not is_enabled:
                continue
            if self._filter_state == "Disabled" and is_enabled:
                continue

            # Text Search
            if q:
                if q not in item["name"].lower() and q not in item["desc"].lower() and q not in item["category"].lower():
                    continue

            filtered.append(item)

        self._displayed_items = filtered
        self.endResetModel()

    # --- QML Slots ---

    @Slot(str, bool)
    def toggleActivity(self, act_id: str, enabled: bool):
        """Update activity toggle and persist."""
        if act_id == "music_sync":
            self._settings.set("audio.enabled", enabled)
        elif act_id == "sound_effects":
            self._settings.set("behavior.sound_enabled", enabled)
        elif act_id == "comic_bubbles":
            self._settings.set("behavior.enable_comic_bubbles", enabled)
        elif act_id == "battery_reaction":
            self._settings.set("system.enable_battery_reaction", enabled)
        elif act_id == "system_load_reaction":
            self._settings.set("system.enable_load_reaction", enabled)
        else:
            self._settings.set(f"animations.enabled.{act_id}", enabled)

        # Re-evaluate displayed list if filtering by Enabled/Disabled
        if self._filter_state in ("Enabled", "Disabled"):
            self._refresh_list()
        else:
            # Emit dataChanged for the row
            for row, itm in enumerate(self._displayed_items):
                if itm["id"] == act_id:
                    idx = self.index(row, 0)
                    self.dataChanged.emit(idx, idx, [self.EnabledRole])
                    break

    @Slot(str)
    def previewActivity(self, act_id: str):
        """Toggle animating preview for one card only (saving CPU)."""
        if self._active_preview_id == act_id:
            self._active_preview_id = ""
        else:
            self._active_preview_id = act_id
        self.activePreviewIdChanged.emit(self._active_preview_id)

        # Notify all rows to update IsAnimatingRole
        if self._displayed_items:
            tl = self.index(0, 0)
            br = self.index(len(self._displayed_items) - 1, 0)
            self.dataChanged.emit(tl, br, [self.IsAnimatingRole])

    @Slot(str)
    def setCategoryFilter(self, cat: str):
        if self._filter_category != cat:
            self._filter_category = cat
            self.filterCategoryChanged.emit(cat)
            self._refresh_list()

    @Slot(str)
    def setStateFilter(self, st: str):
        if self._filter_state != st:
            self._filter_state = st
            self.filterStateChanged.emit(st)
            self._refresh_list()

    @Slot(str)
    def setSearchQuery(self, q: str):
        if self._search_query != q:
            self._search_query = q
            self.searchQueryChanged.emit(q)
            self._refresh_list()

    # --- Properties ---

    def _get_mode(self) -> str:
        return str(self._settings.get("behavior.activity_mode", "auto"))

    def _set_mode(self, val: str):
        self._settings.set("behavior.activity_mode", val)
        self.modeChanged.emit(val)

    mode = Property(str, _get_mode, _set_mode, notify=modeChanged)

    def _get_frequency(self) -> str:
        return str(self._settings.get("behavior.frequency", "normal"))

    def _set_frequency(self, val: str):
        self._settings.set("behavior.frequency", val)
        self.frequencyChanged.emit(val)

    frequency = Property(str, _get_frequency, _set_frequency, notify=frequencyChanged)

    def _get_movement_speed(self) -> float:
        return float(self._settings.get("behavior.movement_speed", 3.0))

    def _set_movement_speed(self, val: float):
        self._settings.set("behavior.movement_speed", round(float(val), 1))
        self.timingChanged.emit()

    movementSpeed = Property(float, _get_movement_speed, _set_movement_speed, notify=timingChanged)

    def _get_animation_speed(self) -> float:
        return float(self._settings.get("general.animation_speed", 1.0))

    def _set_animation_speed(self, val: float):
        self._settings.set("general.animation_speed", round(float(val), 2))
        self.timingChanged.emit()

    animationSpeed = Property(float, _get_animation_speed, _set_animation_speed, notify=timingChanged)
