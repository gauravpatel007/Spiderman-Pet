"""Global hotkey service for triggering Spider-Man animations via keyboard shortcuts."""
import ctypes
import logging
import sys
import time
from typing import Dict, Optional, Tuple
from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger("SpiderBuddy.HotkeyService")

# Action mappings: key_char -> (action_name, display_title, speech_bubble_quote)
HOTKEY_MAPPINGS: Dict[str, Tuple[str, str, str]] = {
    "1": ("swing", "Web Swing", "🕸️ WHOOSH! Web Swing!"),
    "2": ("jump", "Spider-Sense Dodge / Leap", "⚡ Spider-Sense Leap!"),
    "3": ("walk", "Ground Walk & Patrol", "🐾 On Patrol!"),
    "4": ("run", "Sprint / Dash", "💨 Spider-Sprint!"),
    "5": ("focus_read", "Focus Comic Reading", "📖 Studying the Comics!"),
    "6": ("title_hang", "Window Title Hang", "🕸️ Hanging from window top bar!"),
    "7": ("title_perch", "Window Corner Perch", "👀 Perched & Watching!"),
    "8": ("dance", "Dance / Sunflower Vibe", "🎶 Sunflower Vibe!"),
    "9": ("sleep", "Superhero Power Nap", "😴 Power Nap time..."),
    "0": ("wave", "Friendly Wave", "👋 Hey there, Hero!"),
}

# Windows Virtual Key codes for number row (0-9) and numpad (0-9)
VK_NUM_MAP: Dict[int, str] = {
    0x31: "1", 0x61: "1",
    0x32: "2", 0x62: "2",
    0x33: "3", 0x63: "3",
    0x34: "4", 0x64: "4",
    0x35: "5", 0x65: "5",
    0x36: "6", 0x66: "6",
    0x37: "7", 0x67: "7",
    0x38: "8", 0x68: "8",
    0x39: "9", 0x69: "9",
    0x30: "0", 0x60: "0",
}

VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_ALT = 0x12
VK_CTRL = 0x11
VK_SHIFT = 0x10

# WASD and Arrow keys
VK_W = 0x57
VK_A = 0x41
VK_S = 0x53
VK_D = 0x44
VK_UP = 0x26
VK_LEFT = 0x25
VK_DOWN = 0x28
VK_RIGHT = 0x27
VK_SPACE = 0x20


class HotkeyService(QObject):
    """
    Monitors keyboard shortcuts (Keys 1..0, Numpad 0..9, Win+1..0, Alt+1..0, Ctrl+1..0),
    manual WASD / Arrow keys movement, and Spacebar drop-to-ground.
    """

    # Emits (action_name, display_title, speech_quote)
    activity_triggered = Signal(str, str, str)
    # Emits (horizontal: -1..1, vertical: -1..1, is_shift: bool)
    wasd_input = Signal(float, float, bool)
    # Emits when spacebar is pressed to drop to ground
    space_pressed = Signal()

    def __init__(self, check_interval_ms: int = 25, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.check_interval_ms = check_interval_ms
        self._enabled = True
        self._wasd_enabled = True
        self._wasd_active = False
        self.input_blocked = lambda: False
        self._space_down = False
        self._require_modifier = False  # False: direct 1..0 keys trigger animations!
        self._key_down_states: Dict[int, bool] = {vk: False for vk in VK_NUM_MAP}
        self._last_trigger_time = 0.0
        self._cooldown_seconds = 0.35

        self._timer = QTimer(self)
        self._timer.setInterval(self.check_interval_ms)
        self._timer.timeout.connect(self._poll_keys)

        try:
            from .settings_service import get_settings
            self._wasd_enabled = bool(get_settings().get("behavior.wasd_movement_enabled", True))
        except Exception:
            self._wasd_enabled = True

        self._has_win32 = sys.platform == "win32"

    def start(self) -> None:
        """Start listening for keyboard hotkeys."""
        self._timer.start()
        logger.info(
            "HotkeyService started (polling global keyboard state at %dms, require_modifier=%s).",
            self.check_interval_ms,
            self._require_modifier,
        )

    def stop(self) -> None:
        """Stop listening for keyboard hotkeys."""
        self._timer.stop()
        self._key_down_states = {vk: False for vk in VK_NUM_MAP}
        logger.info("HotkeyService stopped.")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable hotkey detection."""
        self._enabled = bool(enabled)
        if not self._enabled:
            self._key_down_states = {vk: False for vk in VK_NUM_MAP}

    def is_enabled(self) -> bool:
        return self._enabled

    def set_require_modifier(self, require: bool) -> None:
        """Set whether modifier (Win, Alt, or Ctrl) is required when pressing number keys."""
        self._require_modifier = bool(require)

    def is_require_modifier(self) -> bool:
        return self._require_modifier

    def is_key_enabled(self, key_char: str) -> bool:
        """Check whether an individual number key (1..0) is enabled."""
        if not self._enabled:
            return False
        try:
            from .settings_service import get_settings
            settings = get_settings()
            enabled_keys = settings.get("behavior.enabled_number_keys", {})
            return enabled_keys.get(key_char, True)
        except Exception:
            return True

    def set_key_enabled(self, key_char: str, enabled: bool) -> None:
        """Enable or disable a specific number key shortcut."""
        try:
            from .settings_service import get_settings
            settings = get_settings()
            enabled_keys = dict(settings.get("behavior.enabled_number_keys", {}))
            enabled_keys[key_char] = bool(enabled)
            settings.set("behavior.enabled_number_keys", enabled_keys)
        except Exception:
            pass

    def trigger_key(self, key_char: str, bypass_cooldown: bool = False, force: bool = False) -> bool:
        """Programmatically or manually trigger an animation by number key ('1'-'0')."""
        if key_char not in HOTKEY_MAPPINGS:
            return False
        if not force and not self._enabled:
            return False
        if not force and not bypass_cooldown and not self.is_key_enabled(key_char):
            return False
        now = time.monotonic()
        if not bypass_cooldown and (now - self._last_trigger_time) < self._cooldown_seconds:
            return False
        self._last_trigger_time = now
        action_name, title, quote = HOTKEY_MAPPINGS[key_char]
        logger.info("Hotkey triggered: Key %s -> %s (%s)", key_char, title, action_name)
        self.activity_triggered.emit(action_name, title, quote)
        return True

    def set_wasd_enabled(self, enabled: bool) -> None:
        """Enable or disable manual WASD / Arrow keys movement."""
        self._wasd_enabled = bool(enabled)
        if not self._wasd_enabled and self._wasd_active:
            self._wasd_active = False
            self.wasd_input.emit(0.0, 0.0, False)

    def is_wasd_enabled(self) -> bool:
        return self._wasd_enabled

    def _poll_keys(self) -> None:
        # Dashboard typing and arrow-key navigation belong to the focused UI.
        if self.input_blocked():
            if self._wasd_active:
                self._wasd_active = False
                self.wasd_input.emit(0.0, 0.0, False)
            self._space_down = False
            self._key_down_states = {vk: False for vk in VK_NUM_MAP}
            return
        if not self._has_win32 or (not self._enabled and not self._wasd_enabled):
            return

        try:
            user32 = ctypes.windll.user32

            # 1. Number row & numpad hotkeys (Keys 1..0)
            if self._enabled:
                # Check if Windows Key, Alt, or Ctrl modifier is currently held down
                is_win = bool((user32.GetAsyncKeyState(VK_LWIN) & 0x8000) or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000))
                is_alt = bool(user32.GetAsyncKeyState(VK_ALT) & 0x8000)
                is_ctrl = bool(user32.GetAsyncKeyState(VK_CTRL) & 0x8000)

                # Accept Windows key (Win+1..0), Alt (Alt+1..0), or Ctrl (Ctrl+1..0)
                modifier_active = is_win or is_alt or is_ctrl

                now = time.monotonic()
                for vk, key_char in VK_NUM_MAP.items():
                    is_down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
                    was_down = self._key_down_states.get(vk, False)
                    self._key_down_states[vk] = is_down

                    # Edge trigger: key transitioned from UP to DOWN
                    if is_down and not was_down:
                        if not self.is_key_enabled(key_char):
                            continue
                        # If modifier is not required, direct number key press triggers!
                        # If modifier is required, Win/Alt/Ctrl must be active.
                        if (not self._require_modifier) or modifier_active:
                            if (now - self._last_trigger_time) >= self._cooldown_seconds:
                                self._last_trigger_time = now
                                self.trigger_key(key_char, bypass_cooldown=True)
                                break

            # 2. WASD and Arrow Keys Manual Movement
            if self._wasd_enabled:
                is_w = bool(user32.GetAsyncKeyState(VK_W) & 0x8000) or bool(user32.GetAsyncKeyState(VK_UP) & 0x8000)
                is_a = bool(user32.GetAsyncKeyState(VK_A) & 0x8000) or bool(user32.GetAsyncKeyState(VK_LEFT) & 0x8000)
                is_s = bool(user32.GetAsyncKeyState(VK_S) & 0x8000) or bool(user32.GetAsyncKeyState(VK_DOWN) & 0x8000)
                is_d = bool(user32.GetAsyncKeyState(VK_D) & 0x8000) or bool(user32.GetAsyncKeyState(VK_RIGHT) & 0x8000)
                is_shift = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)

                h = (-1.0 if is_a else 0.0) + (1.0 if is_d else 0.0)
                v = (-1.0 if is_w else 0.0) + (1.0 if is_s else 0.0)

                if h != 0.0 or v != 0.0:
                    self._wasd_active = True
                    self.wasd_input.emit(h, v, is_shift)
                elif self._wasd_active:
                    self._wasd_active = False
                    self.wasd_input.emit(0.0, 0.0, False)

            # 3. Spacebar drops companion to ground when suspended/static
            if self._wasd_enabled:
                is_space = bool(user32.GetAsyncKeyState(VK_SPACE) & 0x8000)
                if is_space and not self._space_down:
                    self.space_pressed.emit()
                self._space_down = is_space

        except Exception as exc:
            logger.debug("Error polling hotkey state: %s", exc)

