"""Windows Core Audio (WASAPI) audio output meter and beat detection service."""
import ctypes
from ctypes import wintypes
import logging
import math
import sys
import time
from typing import Any, Optional
from PySide6.QtCore import QObject, QTimer, Signal
from .settings_service import get_settings

logger = logging.getLogger("SpiderBuddy.AudioSyncService")


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]

    def __init__(self, l, w1, w2, b):
        super().__init__(l, w1, w2, (wintypes.BYTE * 8)(*b))


CLSID_MMDeviceEnumerator = GUID(
    0xBCDE0395, 0xE52F, 0x467C, [0x8E, 0x3D, 0xC4, 0x57, 0x92, 0x91, 0x69, 0x2E]
)
IID_IMMDeviceEnumerator = GUID(
    0xA95664D2, 0x9614, 0x4F35, [0xA7, 0x46, 0xDE, 0x8D, 0xB6, 0x36, 0x17, 0xE6]
)
IID_IAudioMeterInformation = GUID(
    0xC02216F6, 0x8C67, 0x4B5B, [0x9D, 0x00, 0xD0, 0x08, 0xE7, 0x3E, 0x00, 0x64]
)


def _vcall(ptr, index, restype, argtypes, *args):
    """Invoke COM vtable method by zero-based index."""
    vtable = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    func_ptr = vtable[index]
    proto = ctypes.WINFUNCTYPE(restype, *argtypes)
    func = proto(func_ptr)
    return func(ptr, *args)


class AudioSyncService(QObject):
    """
    Detects real-time system audio playback (Spotify, YouTube, games, media)
    using the Windows Core Audio API (WASAPI IAudioMeterInformation).
    Detects musical tempo/beats for Spider-Man to wear headphones and bob his head in rhythm.
    """

    # Emits live peak volume [0.0..1.0] and smoothed baseline
    audio_meter_updated = Signal(float, float)

    # Emitted on musical beats with beat intensity [0.0..1.0]
    beat_detected = Signal(float)

    # Emitted when music starts or stops: (is_playing: bool, volume: float)
    music_state_changed = Signal(bool, float)

    def __init__(self, check_interval_ms: int = 30, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.settings = get_settings()
        self.check_interval_ms = check_interval_ms

        self._has_win32 = sys.platform == "win32"
        self._p_meter = None
        self._is_initialized = False

        self._current_peak: float = 0.0
        self._smoothed_volume: float = 0.0
        self._is_music_playing: bool = False
        self._last_sound_time: float = 0.0
        self._last_beat_time: float = 0.0
        self._simulated_music: bool = False

        # Polling timer (33 Hz)
        self._timer = QTimer(self)
        self._timer.setInterval(self.check_interval_ms)
        self._timer.timeout.connect(self._poll_audio)

        self.settings.setting_changed.connect(self._on_setting_changed)

    def _on_setting_changed(self, key: str, value: Any) -> None:
        if key in ("behavior.enable_audio_beat_bobbing", "behavior.enable_music_sync") and not value:
            if self._is_music_playing:
                self._is_music_playing = False
                logger.info("Audio beat-bobbing disabled by user; stopping music sync state.")
                self.music_state_changed.emit(False, 0.0)

    def start(self) -> None:
        """Start monitoring system audio output."""
        self._init_wasapi()
        self._timer.start()
        logger.info("AudioSyncService started (WASAPI polling at %dms).", self.check_interval_ms)

    def stop(self) -> None:
        """Stop monitoring."""
        self._timer.stop()
        self._release_wasapi()
        self._is_music_playing = False
        logger.info("AudioSyncService stopped.")

    def is_music_playing(self) -> bool:
        return self._is_music_playing

    def get_current_volume(self) -> float:
        return self._current_peak

    def sample_peak(self) -> float:
        """Sample and return immediate audio peak volume [0.0..1.0]."""
        if not self._is_initialized:
            self._init_wasapi()
        if self._p_meter:
            try:
                raw_peak = ctypes.c_float()
                hr = _vcall(self._p_meter, 3, ctypes.c_long, [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)], ctypes.byref(raw_peak))
                if hr == 0:
                    return max(0.0, min(1.0, float(raw_peak.value)))
            except Exception:
                pass
        return 0.0

    def simulate_music(self, simulate: bool) -> None:
        """Simulate music playback for testing head-bobbing animations without audio."""
        self._simulated_music = bool(simulate)
        logger.info("Simulate music set to: %s", self._simulated_music)
        if not self._simulated_music:
            self._last_sound_time = 0.0
            self._smoothed_volume = 0.0
            self._current_peak = 0.0
            if self._is_music_playing:
                self._is_music_playing = False
                self.music_state_changed.emit(False, 0.0)
        else:
            self._poll_audio()

    def _init_wasapi(self) -> bool:
        if not self._has_win32:
            return False
        try:
            ctypes.windll.ole32.CoInitialize(None)
            p_enum = ctypes.c_void_p()
            hr = ctypes.windll.ole32.CoCreateInstance(
                ctypes.byref(CLSID_MMDeviceEnumerator),
                None,
                1,  # CLSCTX_INPROC_SERVER
                ctypes.byref(IID_IMMDeviceEnumerator),
                ctypes.byref(p_enum),
            )
            if hr != 0:
                logger.debug("CoCreateInstance MMDeviceEnumerator failed: 0x%08X", hr & 0xFFFFFFFF)
                return False

            # GetDefaultAudioEndpoint(0 /*eRender*/, 0 /*eConsole*/, &pDevice) -> vtable index 4
            p_device = ctypes.c_void_p()
            hr = _vcall(
                p_enum,
                4,
                ctypes.c_long,
                [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)],
                0,
                0,
                ctypes.byref(p_device),
            )
            if hr != 0:
                logger.debug("GetDefaultAudioEndpoint failed: 0x%08X", hr & 0xFFFFFFFF)
                return False

            # IMMDevice::Activate(&IID_IAudioMeterInformation, CLSCTX_ALL, NULL, &pMeter) -> vtable index 3
            p_meter = ctypes.c_void_p()
            hr = _vcall(
                p_device,
                3,
                ctypes.c_long,
                [ctypes.c_void_p, ctypes.POINTER(GUID), wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)],
                ctypes.byref(IID_IAudioMeterInformation),
                1,
                None,
                ctypes.byref(p_meter),
            )
            if hr != 0:
                logger.debug("Activate IAudioMeterInformation failed: 0x%08X", hr & 0xFFFFFFFF)
                return False

            self._p_meter = p_meter
            self._is_initialized = True
            return True
        except Exception as exc:
            logger.debug("Failed initializing WASAPI: %s", exc)
            return False

    def _release_wasapi(self) -> None:
        self._p_meter = None
        self._is_initialized = False

    def _poll_audio(self) -> None:
        now = time.monotonic()
        peak_val = 0.0

        if self._simulated_music:
            # 128 BPM simulation wave with periodic kick beats
            phase = (now * 2.13) % 1.0  # 128 BPM
            beat_pulse = math.exp(-phase * 5.0)
            peak_val = 0.25 + 0.65 * beat_pulse
        elif self._is_initialized and self._p_meter:
            try:
                raw_peak = ctypes.c_float()
                # IAudioMeterInformation::GetPeakValue(&raw_peak) -> vtable index 3
                hr = _vcall(
                    self._p_meter,
                    3,
                    ctypes.c_long,
                    [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)],
                    ctypes.byref(raw_peak),
                )
                if hr == 0:
                    peak_val = max(0.0, min(1.0, float(raw_peak.value)))
            except Exception as exc:
                logger.debug("Error querying audio meter: %s", exc)
                self._is_initialized = False

        self._current_peak = peak_val
        self._smoothed_volume = self._smoothed_volume * 0.78 + peak_val * 0.22

        enabled = self.settings.get("behavior.enable_audio_beat_bobbing", self.settings.get("behavior.enable_music_sync", True))
        is_active_audio = (peak_val > 0.02) or (self._smoothed_volume > 0.012)

        if is_active_audio:
            self._last_sound_time = now

        # Music is considered active if audio detected within last 1.8 seconds (bridges track pauses)
        music_playing_now = enabled and (
            self._simulated_music or ((now - self._last_sound_time) < 1.8 and self._smoothed_volume > 0.008)
        )

        if music_playing_now != self._is_music_playing:
            self._is_music_playing = music_playing_now
            logger.info("Music playback state changed: is_playing=%s", self._is_music_playing)
            self.music_state_changed.emit(self._is_music_playing, self._current_peak)

        # Beat detection: peak spike exceeding smoothed baseline by 30% with cooldown
        if self._is_music_playing and (now - self._last_beat_time >= 0.28):
            if peak_val > (self._smoothed_volume * 1.25) and peak_val > 0.06:
                self._last_beat_time = now
                self.beat_detected.emit(peak_val)

        self.audio_meter_updated.emit(self._current_peak, self._smoothed_volume)
