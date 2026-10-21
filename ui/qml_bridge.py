"""Typed, observable dashboard API backed by the existing Python services.

No QML component owns a second settings store or starts backend timers.
"""
from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, QTimer
from core.activity_policy import ACTIVITIES, enabled
from .dashboard_design import DESTINATIONS


class DashboardBridge(QObject):
    routeChanged = Signal()
    settingsChanged = Signal()
    charactersChanged = Signal()
    activitiesChanged = Signal()
    statusChanged = Signal()
    navigateRequested = Signal(int)
    characterRequested = Signal(str)
    activityToggleRequested = Signal(str, bool)
    pauseRequested = Signal()
    searchRequested = Signal()
    importRequested = Signal()
    homeActionRequested = Signal(str)
    homeChanged = Signal()
    frameChanged = Signal()
    revealRequested = Signal(str)

    def __init__(self, settings, character_manager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.manager = character_manager
        self._route = 0
        self._running = True
        self._activity = 'Idle'
        self._battery = 'Reading battery…'
        self._battery_pct = 100
        self._battery_charging = False
        self._cpu = 0.0
        self._ram = 0.0
        self._frame_revision = 0
        self._home_pending = False
        self.home_source = None
        from pathlib import Path as _P
        self._bg_path = str((_P(__file__).resolve().parent.parent / 'assets' / 'backgrounds' / 'home_bg.png').as_posix())
        settings.setting_changed.connect(self._setting_changed)
        settings.settings_reloaded.connect(self._settings_reloaded)
        character_manager.character_changed.connect(self._characters_changed)
        character_manager.characters_discovered.connect(self._characters_changed)

    @Property('QVariantList', constant=True)
    def destinations(self):
        return [{'index': i, 'label': item[0]} for i, item in enumerate(DESTINATIONS)]

    @Property(int, notify=routeChanged)
    def currentRoute(self):
        return self._route

    @Slot(int)
    def navigate(self, index):
        if 0 <= index < len(DESTINATIONS):
            self.navigateRequested.emit(index)

    @Slot(int)
    def sync_route(self, index):
        if 0 <= index < len(DESTINATIONS) and self._route != index:
            self._route = index
            self.routeChanged.emit()

    @Property(bool, notify=settingsChanged)
    def darkTheme(self):
        return self.settings.get('general.theme', 'dark') != 'light'

    @Property(bool, notify=settingsChanged)
    def focusMode(self):
        return bool(self.settings.get('behavior.focus_mode', False))

    @Property(bool, notify=settingsChanged)
    def hidden(self):
        return bool(self.settings.get('general.hidden', False))

    @Property('QVariantMap', notify=settingsChanged)
    def settingsValues(self):
        # SettingsService.get returns copies, so QML cannot mutate saved data implicitly.
        return {section: self.settings.get(section, {}) for section in
                ('general', 'behavior', 'animations', 'system')}

    @Slot(str, result=bool)
    def setTheme(self, theme):
        if theme not in ('dark', 'light'):
            return False
        self.settings.set('general.theme', theme)
        return True

    @Slot(bool)
    def setFocus(self, active):
        self.settings.set('behavior.focus_mode', active)

    @Slot(bool)
    def setHidden(self, hidden):
        self.settings.set('general.hidden', hidden)

    @Property('QVariantList', notify=charactersChanged)
    def characters(self):
        current = self.manager.active_character
        result = []
        for profile in self.manager.available_characters.values():
            preview = profile.root_path / 'preview.png'
            if not preview.exists():
                preview = profile.sprites_path / 'idle.png'
            result.append({'id': profile.id, 'name': profile.name, 'suit': profile.suit,
                           'personality': profile.personality,
                           'preview': QUrl.fromLocalFile(str(preview.resolve())).toString(),
                           'selected': bool(current and current.id == profile.id)})
        return result

    @Property(str, notify=charactersChanged)
    def characterName(self):
        profile = self.manager.active_character
        return profile.name if profile else 'Choose a companion'

    @Property(str, notify=charactersChanged)
    def characterPreview(self):
        return next((row['preview'] for row in self.characters if row['selected']), '')

    @Property(str, notify=charactersChanged)
    def personalityDescription(self):
        from core.personality import get_personality
        profile = self.manager.active_character
        return get_personality(profile.personality).description if profile else ''

    @Property(int, notify=frameChanged)
    def frameRevision(self):
        return self._frame_revision

    def frame_updated(self):
        self._frame_revision += 1
        self.frameChanged.emit()

    @Property('QVariantMap', notify=homeChanged)
    def homeData(self):
        # Transitional adapter: existing handlers still own timer, HUD and quote state.
        names = {'quote':'quote_text', 'owner':'overlay_owner_label',
                 'timer':'focus_countdown_label', 'timerState':'focus_mode_badge',
                 'load':'hud_load_metrics', 'loadState':'hud_spidey_sense',
                 'batteryLore':'hud_battery_lore', 'distance':'stat_distance_val',
                 'webs':'stat_webs_val', 'focus':'stat_active_val'}
        result = {key: getattr(self.home_source, attr).text() if hasattr(self.home_source, attr) else ''
                  for key, attr in names.items()}
        result['mood'] = getattr(self.home_source, '_active_mood', '')
        return result

    def refresh_home(self):
        if not self._home_pending:
            self._home_pending = True
            QTimer.singleShot(0, self, self._publish_home)

    def _publish_home(self):
        self._home_pending = False
        self.homeChanged.emit()

    @Slot()
    def importCharacter(self):
        self.importRequested.emit()

    @Slot(str, result=bool)
    def homeAction(self, action):
        if action not in ('quote', 'chill', 'hyper', 'camo', 'focus25', 'break5', 'resetTimer',
                           'swing', 'celebrate', 'title_perch', 'sleep'):
            return False
        if action in ACTIVITIES and not enabled(self.settings, action):
            return False
        self.homeActionRequested.emit(action)
        self.refresh_home()
        return True

    @Slot(float, result=bool)
    def setCharacterSize(self, pixels):
        import math
        if not math.isfinite(pixels) or not 100 <= pixels <= 400:
            return False
        self.settings.set('general.scale', round(pixels) / 200)
        return True

    @Slot(float, result=bool)
    def setCharacterOpacity(self, percent):
        import math
        if not math.isfinite(percent) or not 50 <= percent <= 100:
            return False
        self.settings.set('general.opacity', round(percent) / 100)
        return True

    @Property('QVariantList', notify=activitiesChanged)
    def activities(self):
        profile = self.manager.active_character
        supported = set(profile.supported_animations) if profile else set()
        aliases = {'title_perch': 'perch', 'title_hang': 'hang', 'focus_read': 'sit'}
        return [{'id': name, 'label': label, 'enabled': enabled(self.settings, name),
                 'available': name in supported or aliases.get(name) in supported}
                for name, label in ACTIVITIES.items()]

    @Slot(str, result=bool)
    def selectCharacter(self, character_id):
        if character_id not in self.manager.available_characters:
            return False
        self.characterRequested.emit(character_id)
        return True

    @Slot(str, bool, result=bool)
    def setActivityEnabled(self, name, active):
        if name not in ACTIVITIES:
            return False
        # Existing controller owns legacy-flag synchronization during migration.
        self.activityToggleRequested.emit(name, active)
        return True

    @Property(bool, notify=statusChanged)
    def running(self):
        return self._running

    @Property(str, notify=statusChanged)
    def activity(self):
        return self._activity if self._running else 'Paused'

    @Property(str, notify=statusChanged)
    def battery(self):
        return self._battery

    @Property(int, notify=statusChanged)
    def batteryPercent(self):
        return self._battery_pct

    @Property(bool, notify=statusChanged)
    def batteryCharging(self):
        return self._battery_charging

    @Property(float, notify=homeChanged)
    def cpuPercent(self):
        return self._cpu

    @Property(float, notify=homeChanged)
    def ramPercent(self):
        return self._ram

    @Property(str, constant=True)
    def bgImagePath(self):
        return 'file:///' + self._bg_path

    @Slot()
    def togglePause(self):
        self.pauseRequested.emit()

    @Slot()
    def requestSearch(self):
        self.searchRequested.emit()

    def set_status(self, running, activity):
        activity = str(activity).removeprefix('Status: ')
        if (self._running, self._activity) != (running, activity):
            self._running, self._activity = bool(running), activity
            self.statusChanged.emit()

    def set_battery(self, percent, charging):
        text = f'{percent}% · ' + ('Charging' if charging else 'On battery')
        changed = text != self._battery
        self._battery_pct = int(percent)
        self._battery_charging = bool(charging)
        if changed:
            self._battery = text
            self.statusChanged.emit()

    def set_load(self, cpu, ram):
        self._cpu = float(cpu)
        self._ram = float(ram)
        self.refresh_home()

    def _setting_changed(self, key, value):
        self.settingsChanged.emit()
        if key.startswith(('animations.', 'behavior.')):
            self.activitiesChanged.emit()

    def _settings_reloaded(self):
        self.settingsChanged.emit()
        self.activitiesChanged.emit()

    def _characters_changed(self, *args):
        self.charactersChanged.emit()
        self.activitiesChanged.emit()
