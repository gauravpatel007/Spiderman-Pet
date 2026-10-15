"""Optional local sound cues; no network or blocking audio playback."""
import logging
import time
from PySide6.QtCore import QObject, QUrl
from .settings_service import get_settings


class SoundService(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = get_settings()
        self.effects = {}
        self._last_play = 0.0
        self.enabled = False
        self.settings.setting_changed.connect(self._setting_changed)

    def start(self):
        self.enabled = True

    def stop(self):
        self.enabled = False
        for effect in self.effects.values():
            effect.stop()

    def _setting_changed(self, key, value):
        if key == 'behavior.sound_enabled' and not value:
            for effect in self.effects.values():
                effect.stop()
        elif key == 'behavior.sound_volume':
            for effect in self.effects.values():
                effect.setVolume(max(0, min(1, float(value))))

    def on_state_changed(self, old, new):
        if not self.enabled or not self.settings.get('behavior.sound_enabled', False):
            return
        cue = {'jump': 'jump', 'swing': 'swing', 'land': 'land', 'sleep': 'sleep',
               'wave': 'reaction', 'celebrate': 'reaction', 'dance': 'reaction'}.get(new.value)
        if cue is None or time.monotonic()-self._last_play < .3:
            return
        if cue not in self.effects:
            try:
                from PySide6.QtMultimedia import QSoundEffect
                path = self.settings.project_root/'assets'/'sounds'/f'{cue}.wav'
                if not path.is_file():
                    return
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setLoopCount(1)
                self.effects[cue] = effect
            except (ImportError, RuntimeError):
                logging.getLogger('SpiderBuddy.Sound').warning('Local audio backend unavailable')
                return
        for effect in self.effects.values():
            effect.stop()
        effect = self.effects[cue]
        effect.setVolume(max(0, min(1, float(self.settings.get('behavior.sound_volume', .25)))))
        effect.play()
        self._last_play = time.monotonic()
