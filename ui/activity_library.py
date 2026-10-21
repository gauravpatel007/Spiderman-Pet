"""Activity catalog and isolated dashboard playback; no desktop engine is reused."""
import math
from PySide6.QtCore import QObject, Signal, Slot, Property, QEvent
from PySide6.QtGui import QImage, QPixmap
from core.activity_policy import ACTIVITIES, PHYSICAL_STATES, enabled
from core.animation_engine import AnimationEngine

GROUPS = {
    'Movement': 'walk run jump climb_up climb_down wall_slide swing',
    'Rest & Poses': 'idle sit sleep wake_up stand_up perch hang focus_read',
    'Expressions': 'wave dance celebrate interact',
    'Window Activities': 'title_perch title_hang',
    'Advanced Transitions': 'fall land dragged',
}
# Effect previews are explicitly labeled; full OS/window scenes need desktop context.
EFFECTS = {
    'music': ('Headphones & beat response', 'Music & Sound', 'behavior.enable_audio_beat_bobbing', 'dance'),
    'sound': ('Sound effects', 'Music & Sound', 'behavior.sound_enabled', ''),
    'bubbles': ('Comic speech bubbles', 'Effects & Toys', 'behavior.enable_comic_bubbles', ''),
    'trampoline': ('Web trampoline', 'Effects & Toys', 'behavior.enable_web_trampoline', ''),
    'glitch': ('Suit glitch', 'Effects & Toys', 'behavior.enable_suit_glitch', ''),
    'battery': ('Low-battery reaction', 'System Reactions', 'behavior.enable_low_battery_reaction', ''),
    'charging': ('Charging indicator', 'System Reactions', 'behavior.enable_battery_charging_reaction', ''),
    'load': ('Heavy-load reaction', 'System Reactions', 'behavior.enable_heavy_load_scene', ''),
}
DESCRIPTIONS = {
    'title_perch': 'Rest at the top-right edge of an eligible application window.',
    'title_hang': 'Hang from an eligible window title bar. Alignment lives in Desktop & Apps.',
    'focus_read': 'Read quietly while focus mode is active.',
    'music': 'React to detected system audio with headphones and beat movement.',
    'sound': 'Play existing companion sounds. Adjust volume in the options below.',
    'bubbles': 'Show comic dialogue during interactions.',
    'trampoline': 'Create an elastic web with Ctrl + drag or the desktop action below.',
    'glitch': 'Allow the temporary suit distortion effect.',
    'battery': 'Allow tired behavior and suit effects when the real battery is low.',
    'charging': 'Show the charging indicator while connected to power.',
    'load': 'React to high CPU or memory use with the existing load scene.',
}


class ActivityLibrary(QObject):
    changed = Signal()
    previewChanged = Signal()
    messageChanged = Signal()

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.settings = window.settings
        self.bridge = window.qml_bridge
        self.engine = AnimationEngine(self)
        self.engine.set_display_fps(30)
        self.provider = None
        self._revision = 0
        self._preview = ''
        self._message = ''
        self._supported = set()
        self._simulation = ''
        self._reconciling = False
        self._thumbnails = {}
        self._options = self._collect_options()
        self.engine.frame_updated.connect(self._frame)
        self.engine.animation_completed.connect(lambda _: self.stopPreview())
        self.settings.setting_changed.connect(self._setting_changed)
        self.settings.settings_reloaded.connect(self._refresh)
        window.character_mgr.character_changed.connect(self._character_changed)
        if hasattr(window.character_mgr, 'characters_discovered'):
            window.character_mgr.characters_discovered.connect(self._character_changed)
        self.bridge.routeChanged.connect(self._route_changed)
        if hasattr(self.bridge, 'statusChanged'):
            self.bridge.statusChanged.connect(self._refresh)
        window.installEventFilter(self)
        self._character_changed()

    def _collect_options(self):
        """Temporary metadata adapter, removed with native pages in Step 7."""
        options = {}
        body = self.window._page_scroll_areas[2][1]
        for key, (widget, kind, factor, extra) in self.window._bindings.items():
            if not body.isAncestorOf(widget):
                continue
            label = widget.property('searchLabel') or (widget.text() if kind == 'check' else key)
            category = 'Timing'
            for group, layout in self.window._activity_groups.items():
                if layout.parentWidget().isAncestorOf(widget):
                    category = {'Effects': 'Effects & Toys', 'System': 'System Reactions', 'Windows': 'Window Activities'}.get(group, group)
                    break
            row = dict(id=key, label=label, kind=kind, factor=factor, category=category)
            if kind == 'slider':
                row.update(low=widget.minimum(), high=widget.maximum(), suffix=extra[1])
            if kind == 'combo':
                row['choices'] = [{'label': widget.itemText(i), 'value': widget.itemData(i)} for i in range(widget.count())]
            options[key] = row
        # These have runtime consumers but no previous generic control.
        for key, label, low, high, default in (
            ('behavior.special_cooldown_seconds', 'Special activity cooldown', 1, 120, 20),
            ('behavior.idle_timeout_seconds', 'Idle timeout', 1, 120, 15),
            ('behavior.sleep_after_minutes', 'Sleep after inactivity (minutes)', 1, 60, 5)
        ):
            options[key] = dict(id=key, label=label, kind='slider', factor=1, category='Timing', low=low, high=high, suffix='', default=default)
        options['animations.enable_window_perching'] = dict(
            id='animations.enable_window_perching', label='Allow window activities', kind='check', factor=1, category='Window Activities', default=True
        )
        for _, (label, category, key, _) in EFFECTS.items():
            options.setdefault(key, dict(id=key, label=label, kind='check', factor=1, category=category, default=key != 'behavior.sound_enabled'))
        return options

    def get_thumbnail(self, name):
        """Return a cached static QImage thumbnail for the given activity or effect."""
        if name in self._thumbnails:
            return self._thumbnails[name]
        clip_name = EFFECTS[name][3] if name in EFFECTS else name
        source_name = {'title_perch': 'perch', 'title_hang': 'hang', 'focus_read': 'sit'}.get(clip_name, clip_name)
        profile = getattr(self.window.character_mgr, 'active_character', None)
        image = QImage()
        if profile and hasattr(profile, 'animations_path'):
            folder = profile.animations_path / source_name
            if folder.is_dir():
                files = sorted([*folder.glob('*.png'), *folder.glob('*.webp')])
                if files:
                    image = QImage(str(files[0]))
        if image.isNull():
            pix = getattr(self.window, '_last_preview', None)
            if pix is not None and not pix.isNull():
                image = pix.toImage()
        if not image.isNull() and name == 'music':
            try:
                from overlay.headphones import with_headphones
                pixmap = with_headphones(QPixmap.fromImage(image))
                image = pixmap.toImage()
            except Exception:
                pass
        self._thumbnails[name] = image
        return image

    @Property('QVariantList', notify=changed)
    def rows(self):
        rows = []
        running = bool(self.bridge.running and not self.bridge.hidden)
        focus = bool(self.bridge.focusMode)
        validator = getattr(self.window, 'activity_context_validator', None)
        window_reason = validator('title_perch') if validator else ''

        for name, label in ACTIVITIES.items():
            available = name in self._supported
            is_enabled = enabled(self.settings, name)
            category = next((g for g, names in GROUPS.items() if name in names.split()), 'Expressions')
            is_trans = name in PHYSICAL_STATES

            if not available:
                can_play = False
                desktop_reason = 'This character does not include this animation.'
            elif not is_enabled:
                can_play = False
                desktop_reason = 'Activity is disabled. Allow it before playing.'
            elif not running:
                can_play = False
                desktop_reason = 'Companion is paused or hidden. Resume and show from Home first.'
            elif focus and name not in ('idle', 'sit', 'sleep', 'focus_read'):
                can_play = False
                desktop_reason = 'Turn off focus mode before playing this activity.'
            elif name in ('title_perch', 'title_hang') and window_reason:
                can_play = False
                desktop_reason = window_reason
            else:
                can_play = True
                desktop_reason = ''

            prereqs = ''
            if name in ('title_perch', 'title_hang'):
                prereqs = 'Eligible window required.'
            elif name == 'focus_read':
                prereqs = 'Plays during focus mode.'

            rel = []
            if name in ('title_perch', 'title_hang'):
                rel.append('animations.enable_window_perching')
            if name == 'focus_read':
                rel.append('behavior.focus_mode')
            if 'climb' in name:
                rel.append('behavior.enable_climbing')
            if name == 'swing':
                rel.append('behavior.enable_swinging')
            if name == 'jump':
                rel.append('behavior.enable_jumping')

            rows.append(dict(
                id=name, label=label, category=category,
                description=DESCRIPTIONS.get(name, 'Character animation: ' + label.lower() + '.'),
                available=available, supported=available, enabled=is_enabled,
                preview=available,
                canPlayDesktop=can_play, desktopReason=desktop_reason,
                prerequisites=prereqs, relatedSettings=','.join(rel),
                reason='' if available else 'This character does not include this animation.',
                recovery=is_trans, isTransition=is_trans
            ))

        for name, (label, category, key, clip) in EFFECTS.items():
            is_enabled = bool(self.settings.get(key, key != 'behavior.sound_enabled'))
            can_preview = bool(clip and clip in self._supported)
            can_play = is_enabled and running and not focus
            desktop_reason = ''
            if not is_enabled:
                desktop_reason = 'Enable this effect before testing it.'
            elif not running or focus:
                desktop_reason = 'Show and resume companion, and leave focus mode, to test.'

            prereqs = ''
            if name == 'music':
                prereqs = 'Requires system audio or music playing.'
            elif name == 'battery':
                prereqs = 'Requires low battery (<15%).'
            elif name == 'charging':
                prereqs = 'Requires AC power connected.'
            elif name == 'load':
                prereqs = 'Requires high CPU or RAM load (>85%).'

            rows.append(dict(
                id=name, label=label, category=category,
                description=DESCRIPTIONS.get(name, label),
                available=True, supported=True, enabled=is_enabled,
                preview=can_preview,
                canPlayDesktop=can_play, desktopReason=desktop_reason,
                prerequisites=prereqs, relatedSettings=key,
                reason='' if can_preview else 'Desktop effect requires system or desktop context.',
                recovery=False, isTransition=False
            ))
        return rows

    @Property('QVariantList', notify=changed)
    def options(self):
        return [dict(row, value=self.settings.get(key, row.get('default', True if row['kind'] == 'check' else 1))) for key, row in self._options.items()]

    @Property(bool, notify=changed)
    def automatic(self):
        return bool(self.settings.get('behavior.automatic_animations', True))

    @Property(str, notify=changed)
    def locked(self):
        return self.settings.get('behavior.locked_activity', 'dance')

    @Property(str, notify=previewChanged)
    def previewId(self):
        return self._preview

    @Property(int, notify=previewChanged)
    def revision(self):
        return self._revision

    @Property(str, notify=messageChanged)
    def message(self):
        return self._message

    @Property(str, notify=previewChanged)
    def simulationId(self):
        return self._simulation

    @Property(bool, notify=previewChanged)
    def isSimulating(self):
        return bool(self._simulation)

    def _tell(self, text):
        self._message = text
        self.messageChanged.emit()
        return False

    def _frame(self, pixmap):
        if self.provider is None or not self._preview:
            return
        if self._preview == 'music':
            from overlay.headphones import with_headphones
            pixmap = with_headphones(pixmap)
        self.provider.frame = pixmap.toImage()
        self._revision += 1
        self.previewChanged.emit()

    @Slot(str, result=bool)
    def preview(self, name):
        self.stopPreview()
        row = next((r for r in self.rows if r['id'] == name), None)
        if not row or not row['preview']:
            return self._tell('No isolated preview is available for this effect. Its real scene needs desktop context.')
        if self.bridge.currentRoute != 2 or not self.window.isVisible():
            return False
        self._preview = name
        clip = EFFECTS[name][3] if name in EFFECTS else name
        if not self.engine.play(clip, force_restart=True):
            self.stopPreview()
            return self._tell('The animation could not be loaded.')
        self._tell(
            'Dashboard preview only. Window positioning and system-triggered scenes are not simulated.'
            if name != 'music' else
            'Headphone animation preview. Live audio detection and beat timing are not simulated.'
        )
        self.previewChanged.emit()
        return True

    @Slot()
    def stopPreview(self):
        self.engine.stop()
        self._preview = ''
        self.previewChanged.emit()

    @Slot(str, bool, result=bool)
    def toggle(self, name, value):
        if name in ACTIVITIES:
            self.window._on_activity_toggled(name, value)
        elif name in EFFECTS:
            self.settings.set(EFFECTS[name][2], value)
        else:
            return False
        return True

    @Slot(str, 'QVariant', result=bool)
    def setOption(self, key, value):
        row = self._options.get(key)
        if not row:
            return False
        if row['kind'] == 'check':
            if not isinstance(value, bool):
                return False
        elif row['kind'] == 'combo':
            if value not in [x['value'] for x in row['choices']]:
                return False
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                return False
            if not row['low'] <= value * row['factor'] <= row['high']:
                return False
        self.settings.set(key, value)
        return True

    @Slot(bool, str, result=bool)
    def setPlayback(self, automatic, name):
        if not automatic and (name not in self._supported or not enabled(self.settings, name)):
            return self._tell('Choose a supported, enabled activity before repeating it.')
        if not automatic:
            self.settings.set('behavior.locked_activity', name)
        self.settings.set('behavior.automatic_animations', automatic)
        self._tell('Automatic playback enabled.' if automatic else 'Repeating ' + ACTIVITIES.get(name, name) + '.')
        return True

    @Slot(str, result=bool)
    def playDesktop(self, name):
        if name not in self._supported:
            return self._tell('This character does not include this animation.')
        if not enabled(self.settings, name):
            return self._tell('Enable a supported activity before playing it on the desktop.')
        if not self.bridge.running or self.bridge.hidden:
            return self._tell('Resume and show the companion from Home first.')
        if self.bridge.focusMode and name not in ('idle', 'sit', 'sleep', 'focus_read'):
            return self._tell('Turn off focus mode before playing this activity.')
        validator = getattr(self.window, 'activity_context_validator', None)
        reason = validator(name) if validator else ('Window context is not connected.' if name.startswith('title_') else '')
        if reason:
            return self._tell(reason)
        self.window.activity_requested.emit(name)
        self._tell('Requested ' + ACTIVITIES.get(name, name) + ' on the desktop.')
        return True

    @Slot(str)
    def bulk(self, mode):
        if mode not in ('enable', 'disable', 'reset'):
            return
        for name in ACTIVITIES:
            if mode == 'enable' and name not in self._supported:
                continue
            self.toggle(name, mode != 'disable' or name in PHYSICAL_STATES)
        if mode in ('enable', 'reset'):
            self.settings.set('animations.enable_window_perching', True)
        self._tell('Animation permissions updated. Effects, timing and unrelated preferences were preserved.')

    def _refresh(self, *args):
        if hasattr(self, "window"):
            try:
                from shiboken6 import isValid
                if not isValid(self.window):
                    return
            except Exception:
                pass
        if not self._reconciling and not self.automatic and (self.locked not in self._supported or not enabled(self.settings, self.locked)):
            self._reconciling = True
            self.settings.set('behavior.automatic_animations', True)
            self._reconciling = False
            self._tell('Repeat-one selection is unavailable; returned to automatic playback.')
        self.changed.emit()

    def _setting_changed(self, key, value):
        if self._simulation in EFFECTS and key == EFFECTS[self._simulation][2] and not value:
            self.stopDesktopTest()
        if key.startswith(('behavior.', 'animations.', 'general.')):
            self._refresh()

    def _character_changed(self, *args):
        self.stopPreview()
        self.stopDesktopTest()
        self._thumbnails.clear()
        profile = self.window.character_mgr.active_character
        self._supported = set()
        if profile:
            self.engine.set_character(profile)
            self.engine.stop()
            self._supported = {name for name in ACTIVITIES if self.engine.has_animation(name)}
        self._revision += 1
        self._refresh()

    def _route_changed(self):
        if self.bridge.currentRoute != 2:
            self.stopPreview()
            self.stopDesktopTest()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Hide, QEvent.Close):
            self.stopPreview()
            self.stopDesktopTest()
        return False

    @Slot(str, result=bool)
    def testDesktop(self, name):
        self.stopDesktopTest()
        if name not in EFFECTS or not self.settings.get(EFFECTS[name][2], name != 'sound'):
            return self._tell('Enable this effect before testing it.')
        if not self.bridge.running or self.bridge.hidden or self.bridge.focusMode:
            return self._tell('Show and resume the companion, and leave focus mode, before a desktop test.')
        mapping = {
            'music': 'simulate_music_toggled', 'battery': 'simulate_low_battery_toggled',
            'charging': 'simulate_charging_toggled', 'load': 'simulate_heavy_load_toggled'
        }
        if name in mapping:
            self._simulation = name
            getattr(self.window, mapping[name]).emit(True)
        elif name == 'glitch':
            self.window.test_glitch_requested.emit()
        elif name == 'trampoline':
            self.window.spawn_trampoline_requested.emit()
        else:
            return self._tell('This effect runs during normal companion interactions.')
        self.previewChanged.emit()
        self.changed.emit()
        self._tell('Temporary desktop test started. Stop it here; leaving Activities also ends simulated system inputs.')
        return True

    @Slot()
    def stopDesktopTest(self):
        name = self._simulation
        self._simulation = ''
        mapping = {
            'music': 'simulate_music_toggled', 'battery': 'simulate_low_battery_toggled',
            'charging': 'simulate_charging_toggled', 'load': 'simulate_heavy_load_toggled'
        }
        if name in mapping and hasattr(self.window, mapping[name]):
            getattr(self.window, mapping[name]).emit(False)
        self.previewChanged.emit()
        self.changed.emit()
