"""Modern Web-Based Settings & Dashboard Window for Spider-Buddy.

Hosts the Framer HTML/CSS/JS frontend inside PySide6 QWebEngineView and
exposes full bi-directional communication between JavaScript controls and
the Spider-Buddy backend services.
"""
import base64
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QUrl, QBuffer, QIODevice, QTimer, QObject, QEvent
from PySide6.QtGui import QIcon, QPixmap, QColor, QPalette
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings

from .web_server import WebServer
from services.settings_service import get_settings
from services.hotkey_service import HOTKEY_MAPPINGS
from core.activity_policy import ACTIVITIES, LEGACY_FLAGS, PHYSICAL_STATES, enabled
from ui.activity_library import GROUPS, EFFECTS, DESCRIPTIONS

logger = logging.getLogger("SpiderBuddy.UI.WebWindow")

ACTIVITY_CATEGORIES = {
    # Movement
    "walk": "Movement",
    "run": "Movement",
    "jump": "Movement",
    "climb_up": "Movement",
    "climb_down": "Movement",
    "wall_slide": "Movement",
    "swing": "Movement",
    # Rest & Poses
    "idle": "Rest & Poses",
    "sit": "Rest & Poses",
    "sleep": "Rest & Poses",
    "wake_up": "Rest & Poses",
    "stand_up": "Rest & Poses",
    "perch": "Rest & Poses",
    "hang": "Rest & Poses",
    "focus_read": "Rest & Poses",
    # Expressions
    "wave": "Expressions",
    "dance": "Expressions",
    "celebrate": "Expressions",
    "interact": "Expressions",
    # Window Tricks
    "title_perch": "Window Tricks",
    "title_hang": "Window Tricks",
    # Advanced Transitions
    "fall": "Advanced Transitions",
    "land": "Advanced Transitions",
    "dragged": "Advanced Transitions",
}

ACTIVITY_DESCRIPTIONS = {
    "idle": "Look around, adjust mask, and stay alert on screen.",
    "walk": "Pace casually along window borders and desktop floor.",
    "run": "Sprint quickly across desktop edges and taskbar.",
    "jump": "Leap into the air with acrobatic agility.",
    "fall": "Realistic gravity fall when dropped from above.",
    "land": "Superhero three-point landing upon hitting a surface.",
    "climb_up": "Scale vertical window frames and screen edges.",
    "climb_down": "Descend smoothly down window borders.",
    "wall_slide": "Slide down screen edges with friction.",
    "swing": "Shoot web line and swing across the display.",
    "perch": "Crouch vigilantly atop taskbars or window frames.",
    "hang": "Hang upside-down by a single web strand.",
    "sleep": "Nap quietly after periods of user inactivity.",
    "wake_up": "Stretch and wake up when activity resumes.",
    "sit": "Sit down and relax during short pauses.",
    "stand_up": "Rise back to ready stance from sitting or resting.",
    "wave": "Friendly neighborhood wave to say hello.",
    "dance": "Show off Spidey dance moves and footwork.",
    "celebrate": "Cheer and celebrate completed focus sessions.",
    "interact": "React playfully when hovered or clicked.",
    "dragged": "Caught by the web when user drags companion.",
    "title_perch": "Perch vigilantly at top-right corner of active windows.",
    "title_hang": "Hang upside down from browser and app title bars.",
    "focus_read": "Read a comic quietly while focus mode is active.",
    "music": "Put on headphones and groove to system audio beats.",
    "sound": "Play classic comic sound effects on actions.",
    "bubbles": "Display comic dialogue and reaction bubbles.",
    "trampoline": "Spawn an elastic web trampoline on the desktop.",
    "glitch": "Dimensional suit glitch distortion effect.",
    "battery": "Low battery fatigue and suit power warning.",
    "charging": "Bio-electric surge and charging indicators.",
    "load": "Spider-Sense warning and struggle under high CPU/RAM."
}



class ZoomBlocker(QObject):
    """Event filter that blocks Ctrl +/-/0 and Ctrl + Wheel zooming."""

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Wheel:
            if event.modifiers() & Qt.ControlModifier:
                event.ignore()
                return True
        elif event.type() in (QEvent.KeyPress, QEvent.KeyRelease):
            if event.modifiers() & Qt.ControlModifier:
                if event.key() in (Qt.Key_Plus, Qt.Key_Minus, Qt.Key_Equal, Qt.Key_0, Qt.Key_Underscore):
                    event.ignore()
                    return True
        return super().eventFilter(watched, event)

SPIDEY_QUOTES = [
    "With great power comes great... need to commit to Git.",
    "Spider-Sense detects a bug somewhere in this codebase...",
    "Antigravity looks comfy today.",
    "Queens is quiet... time to write some clean, bug-free code.",
    "Remember to hydrate! Even Spider-Man drinks water.",
    "Tabs or spaces? Don't make me shoot a web at your screen!",
    "Peter Parker: Part-time superhero, full-time bug fixer.",
    "Why do bugs always attack right before deployment?!",
    "Don't worry, I'm watching your terminal for errors.",
    "Spider-Sense tingling! Did someone just push directly to main?!",
    "Stay hydrated and keep that posture straight, web-slinger!",
]


def get_battery_lore(char_id: str, percent: int, is_charging: bool, is_low: bool) -> tuple:
    """Return (suit_name, suit_status) for battery Lore."""
    if "miles" in str(char_id).lower():
        suit_name = "Miles Bio-Electricity"
        if is_charging:
            suit_status = "Venom Surge Charging" if percent < 100 else "Fully Charged!"
        elif is_low:
            suit_status = "Bio-Reserve Depleted"
        else:
            suit_status = f"Stable ({percent}%)"
    elif "gwen" in str(char_id).lower():
        suit_name = "Ghost-Spider Suit"
        if is_charging:
            suit_status = "Kinetic Capacitors Recharging" if percent < 100 else "Fully Energized!"
        elif is_low:
            suit_status = "Low Kinetic Energy"
        else:
            suit_status = f"Systems Operational ({percent}%)"
    else:
        suit_name = "Stark Suit"
        if is_charging:
            suit_status = "Arc Reactor Overcharged" if percent < 100 else "100% Fully Powered!"
        elif is_low:
            suit_status = "Emergency Low Power"
        else:
            suit_status = f"Systems Operational ({percent}%)"
    return suit_name, suit_status


def get_spidey_sense_status(cpu: float, ram: float, is_heavy: bool) -> tuple:
    """Return (sense_text, sense_color)."""
    max_val = max(cpu, ram)
    if is_heavy or max_val >= 80:
        return "SPIDEY-SENSE TINGLING! (Heavy Load)", "#EF4444"
    elif max_val >= 50:
        return "Humming (Active Workload)", "#F59E0B"
    else:
        return "Quiet (Systems Cool)", "#21D9A0"


class DummyLabel:
    """Compatibility placeholder for legacy overlay owner label."""
    def __init__(self):
        self._text = ""

    def setText(self, text: str):
        self._text = str(text)


class DummyBridge:
    """Compatibility placeholder for legacy QML bridge."""
    def refresh_home(self):
        pass


class WebMainWindow(QMainWindow):
    """Native window displaying the Framer HTML/CSS/JS frontend."""

    start_requested = Signal()
    stop_requested = Signal()
    character_changed = Signal(str)
    display_mode_changed = Signal(str)
    size_changed = Signal(int)
    activity_requested = Signal(str)
    save_position_requested = Signal()
    test_glitch_requested = Signal()
    simulate_low_battery_toggled = Signal(bool)
    simulate_charging_toggled = Signal(bool)
    test_eye_break_requested = Signal()
    focus_timer_started = Signal(float)
    focus_timer_stopped = Signal()
    spawn_trampoline_requested = Signal()
    simulate_heavy_load_toggled = Signal(bool)
    simulate_music_toggled = Signal(bool)
    speech_bubble_requested = Signal(str, int, str)
    mood_preset_changed = Signal(str)
    reset_companion_stats_requested = Signal()
    test_sound_requested = Signal()

    def __init__(self, character_mgr=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.character_mgr = character_mgr
        self.settings = get_settings()

        # State tracking
        self._is_running = True
        self._status_text = "Idle"
        self._dashboard_tab = "Home"
        self._last_preview_bytes: Optional[bytes] = None
        self._last_frame_b64: Optional[str] = None
        self.activity_context_validator = None
        self._continuous_sec: float = 0.0
        self._timer_remaining_sec: float = 0.0
        self._timer_active: bool = False

        # Compatibility attributes expected by SpiderBuddyApp
        self.overlay_owner_label = DummyLabel()
        self.qml_bridge = DummyBridge()

        # Window Appearance
        self.setWindowTitle("Spider-Buddy — Desktop Companion")
        self.setMinimumSize(960, 580)

        # Proper Desktop Application Geometry: fit comfortably inside the primary screen work area
        # (availableGeometry automatically excludes the Windows Taskbar so it is NEVER overlapped or covered)
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = max(960, min(1280, int(avail.width() * 0.84)))
            target_h = max(580, min(750, int(avail.height() * 0.85)))
            self.resize(target_w, target_h)
            # Center neatly within the desktop work area above the taskbar
            cx = avail.x() + (avail.width() - target_w) // 2
            cy = avail.y() + (avail.height() - target_h) // 2
            self.move(cx, cy)
        else:
            self.resize(1180, 720)

        # Real desktop application: window must NOT override other apps or the taskbar on startup.
        # WebMainWindow is a standard desktop window that respects system window layering.
        self.setWindowFlag(Qt.WindowStaysOnTopHint, False)

        self._audio_peak: float = 0.0
        self._audio_smoothed: float = 0.0
        self._music_playing: bool = False
        self._music_volume: float = 0.0

        # Set Dark Palette to prevent white flash during initial browser load
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor("#060912"))
        self.setPalette(pal)

        # Top-left application icon
        root_dir = Path(__file__).resolve().parent.parent
        icon_path = root_dir / "assets" / "icons" / "spiderman_face.png"
        if not icon_path.exists():
            icon_path = root_dir / "assets" / "icons" / "spider.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # 1. Initialize embedded web server serving BIN/Frammer UI
        self.web_server = WebServer()
        self.web_server.action_received.connect(self._on_web_action)
        self.web_server.action_callback = self._on_web_action
        self.web_server.get_preview_bytes = self._get_active_preview_bytes
        self.web_server.get_status_data = self._get_status_dict
        self.web_server.get_characters_list = self._get_characters_list
        self.web_server.get_character_image = self._get_character_image
        self.web_server.get_activities_list = self._get_activities_list
        self.web_server.get_timing_settings = self._get_timing_settings
        self.web_server.get_activity_icon = self._get_activity_icon
        self.web_server.get_display_settings = self._get_display_settings
        self.web_server.get_running_applications = self._get_running_applications
        self.web_server.get_focus_settings = self._get_focus_settings
        self.web_server.get_control_settings = self._get_control_settings
        self.web_server.get_app_settings = self._get_app_settings
        self.web_port = self.web_server.start()

        # 2. Initialize QWebEngineView with native opaque paint event (no QWidget stylesheet interference)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.web_view = QWebEngineView(self)
        self.web_view.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.web_view.page().setBackgroundColor(QColor("#06080d"))
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, False)

        # Block Ctrl +/-/0 zooming in Qt
        self._zoom_blocker = ZoomBlocker(self)
        self.web_view.installEventFilter(self._zoom_blocker)
        if self.web_view.focusProxy():
            self.web_view.focusProxy().installEventFilter(self._zoom_blocker)
        self.web_view.setZoomFactor(1.0)

        self.setCentralWidget(self.web_view)

        # Load web dashboard
        url = QUrl(self.web_server.get_url())
        self.web_view.load(url)
        self.web_view.loadFinished.connect(self._on_load_finished)

        # Character manager signals & initial character setup
        if self.character_mgr:
            if hasattr(self.character_mgr, "character_changed"):
                self.character_mgr.character_changed.connect(self._character_updated)
            if hasattr(self.character_mgr, "characters_discovered"):
                self.character_mgr.characters_discovered.connect(self._on_characters_discovered)
            if hasattr(self.character_mgr, "active_character") and self.character_mgr.active_character:
                self._character_updated(self.character_mgr.active_character)

    def _on_load_finished(self, ok: bool):
        logger.info(f"Web UI loaded: ok={ok}")
        if self.web_view.focusProxy():
            self.web_view.focusProxy().installEventFilter(self._zoom_blocker)
        self.web_view.setZoomFactor(1.0)
        if ok:
            # Sync initial state to frontend after load
            QTimer.singleShot(400, self._sync_full_state_to_ui)

    def _sync_full_state_to_ui(self):
        """Push initial backend state values to JavaScript UI elements."""
        char_profile = getattr(self.character_mgr, "active_character", None) if self.character_mgr else None
        char_name = char_profile.display_name if char_profile else "Tom Holland Spider-Man"

        quote = SPIDEY_QUOTES[0]
        self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setCharacter({self._json_str(char_name)}, {self._json_str(quote)})")
        self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setActivity({self._json_str(self._status_text)})")
        self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setRunning({str(self._is_running).lower()})")

        scale = float(self.settings.get("general.scale", 1.0))
        size_px = int(scale * 200)
        opacity_pct = int(float(self.settings.get("general.opacity", 1.0)) * 100)
        self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setTuning && window.SpiderBuddy.setTuning({size_px}, {opacity_pct})")

        # If a frame was already rendered, push it
        if self._last_frame_b64:
            self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setFrame({self._json_str(self._last_frame_b64)})")
        elif char_profile and hasattr(char_profile, "root_path"):
            prev_file = Path(char_profile.root_path) / "preview.png"
            if prev_file.exists():
                b64 = base64.b64encode(prev_file.read_bytes()).decode("ascii")
                self._last_frame_b64 = b64
                self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setFrame({self._json_str(b64)})")

    def _run_js(self, script: str):
        """Execute a JavaScript snippet safely in the web page."""
        try:
            if self.web_view and self.web_view.page():
                self.web_view.page().runJavaScript(script)
        except Exception as e:
            logger.debug(f"runJavaScript error: {e}")

    def _json_str(self, val: str) -> str:
        import json
        return json.dumps(str(val))

    def _get_active_preview_bytes(self) -> Optional[bytes]:
        """Fetch current character preview image bytes."""
        if self._last_preview_bytes:
            return self._last_preview_bytes
        char_profile = getattr(self.character_mgr, "active_character", None) if self.character_mgr else None
        if char_profile and hasattr(char_profile, "root_path"):
            prev_file = Path(char_profile.root_path) / "preview.png"
            if prev_file.exists():
                return prev_file.read_bytes()
        return None

    def _on_characters_discovered(self):
        self._sync_full_state_to_ui()
        self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadCharacters && window.SpiderBuddy.loadCharacters()")

    def _get_status_dict(self) -> dict:
        char_profile = getattr(self.character_mgr, "active_character", None) if self.character_mgr else None
        char_id = char_profile.id if char_profile else "tom_holland"
        char_name = char_profile.display_name if char_profile else "Tom Holland Spider-Man"
        scale = float(self.settings.get("general.scale", 1.0))
        size_px = int(scale * 200)
        opacity_pct = int(float(self.settings.get("general.opacity", 1.0)) * 100)
        return {
            "is_running": self._is_running,
            "status": self._status_text,
            "character": char_id,
            "character_id": char_id,
            "character_name": char_name,
            "is_hidden": bool(self.settings.get("general.hidden", False)),
            "companion_size": size_px,
            "companion_opacity": opacity_pct
        }

    def _get_characters_list(self) -> list:
        result = []
        if not self.character_mgr:
            return result
        active_id = self.character_mgr.active_character.id if self.character_mgr.active_character else ""
        for cid, profile in self.character_mgr.available_characters.items():
            result.append({
                "id": profile.id,
                "name": profile.display_name,
                "suit": profile.suit,
                "description": profile.description,
                "personality": getattr(profile, "personality", "balanced"),
                "selected": (profile.id == active_id),
                "preview_url": f"/api/character_image/{profile.id}.png"
            })
        return result

    def _get_character_image(self, char_id: str) -> Optional[bytes]:
        if not self.character_mgr:
            return None
        profile = self.character_mgr.available_characters.get(char_id)
        if profile and hasattr(profile, "root_path"):
            prev_file = Path(profile.root_path) / "preview.png"
            if prev_file.exists():
                return prev_file.read_bytes()
        return None

    def _get_activities_list(self) -> list:
        """Return full catalog of activities and effects with their current status."""
        rows = []
        profile = getattr(self.character_mgr, "active_character", None) if self.character_mgr else None
        anim_path = getattr(profile, "animations_path", None) if profile else None

        # Determine supported animations for active character
        supported = set()
        if anim_path and anim_path.exists():
            supported = {d.name for d in anim_path.iterdir() if d.is_dir()}
        else:
            # Fallback to tom_holland animations if standalone
            root = Path(__file__).resolve().parent.parent
            def_anim = root / "characters" / "tom_holland" / "animations"
            if def_anim.exists():
                supported = {d.name for d in def_anim.iterdir() if d.is_dir()}

        # 1. Standard Character Activities
        for name, label in ACTIVITIES.items():
            category = ACTIVITY_CATEGORIES.get(name, "Expressions")
            is_supp = (name in supported) or (name in ("title_perch", "title_hang", "focus_read") and any(x in supported for x in ("perch", "hang", "sit")))
            is_en = enabled(self.settings, name)
            is_trans = name in PHYSICAL_STATES
            can_play = bool(is_supp and is_en and self._is_running and not self.settings.get("general.hidden", False))

            rows.append({
                "id": name,
                "label": label,
                "category": category,
                "description": ACTIVITY_DESCRIPTIONS.get(name, DESCRIPTIONS.get(name, f"Companion animation: {label.lower()}.")),
                "enabled": is_en,
                "supported": is_supp,
                "can_play": can_play,
                "is_transition": is_trans,
                "is_effect": False,
                "icon_url": f"/api/activity_icon/{name}.png"
            })

        # 2. Desktop Effects & System Reactions
        for name, (label, _, key, clip) in EFFECTS.items():
            is_en = bool(self.settings.get(key, key != "behavior.sound_enabled"))
            can_play = bool(is_en and self._is_running and not self.settings.get("general.hidden", False))

            rows.append({
                "id": name,
                "label": label,
                "category": "Effects & Reactions",
                "description": ACTIVITY_DESCRIPTIONS.get(name, DESCRIPTIONS.get(name, label)),
                "enabled": is_en,
                "supported": True,
                "can_play": can_play,
                "is_transition": False,
                "is_effect": True,
                "icon_url": f"/api/activity_icon/{name}.png"
            })

        return rows


    def _get_timing_settings(self) -> dict:
        """Return timing and autonomy parameters for the frontend."""
        return {
            "special_cooldown": float(self.settings.get("behavior.special_cooldown_seconds", 20)),
            "idle_timeout": float(self.settings.get("behavior.idle_timeout_seconds", 15)),
            "sleep_after": float(self.settings.get("behavior.sleep_after_minutes", 5)),
            "automatic": bool(self.settings.get("behavior.automatic_animations", True)),
            "locked_activity": str(self.settings.get("behavior.locked_activity", "dance"))
        }

    def _get_activity_icon(self, act_name: str) -> Optional[bytes]:
        """Fetch thumbnail frame for an activity or effect."""
        profile = getattr(self.character_mgr, "active_character", None) if self.character_mgr else None
        root = Path(__file__).resolve().parent.parent
        anim_path = getattr(profile, "animations_path", None) if profile else None
        if not anim_path or not anim_path.exists():
            anim_path = root / "characters" / "tom_holland" / "animations"

        clip_name = EFFECTS[act_name][3] if act_name in EFFECTS else act_name
        source_name = {"title_perch": "perch", "title_hang": "hang", "focus_read": "sit"}.get(clip_name, clip_name)

        if not source_name:
            source_name = "idle"

        folder = anim_path / source_name
        if folder.is_dir():
            files = sorted([*folder.glob("*.png"), *folder.glob("*.webp")])
            if files:
                return files[0].read_bytes()

        # Fallback to preview image
        return self._get_active_preview_bytes()

    def _open_import_dialog(self):
        """Open native character artwork import dialog."""
        try:
            from ui.character_selection import AddCharacterDialog
            dlg = AddCharacterDialog(self.character_mgr, parent=self)
            from PySide6.QtWidgets import QDialog
            if dlg.exec() == QDialog.Accepted:
                new_cid = getattr(dlg, "created_character_id", None)
                if new_cid and self.character_mgr:
                    self.character_mgr.discover_characters()
                    self.character_mgr.set_active_character(new_cid)
                    self.character_changed.emit(new_cid)
                    self._character_updated(new_cid)
                    self._sync_full_state_to_ui()
                    # Trigger web page to reload characters
                    self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadCharacters && window.SpiderBuddy.loadCharacters()")
        except Exception as e:
            logger.exception("Failed to open AddCharacterDialog: %s", e)

    def _get_display_settings(self) -> dict:
        """Return display mode, monitor bounds, and window perching settings."""
        target_apps = self.settings.get("general.target_applications", [])
        clean_target_apps = []
        for app in target_apps:
            if isinstance(app, dict):
                clean_target_apps.append({
                    "executable_path": app.get("executable_path", ""),
                    "process_name": app.get("process_name", ""),
                    "display_name": app.get("display_name", "") or app.get("process_name", "")
                })
            else:
                clean_target_apps.append({
                    "executable_path": "",
                    "process_name": str(app),
                    "display_name": str(app)
                })

        return {
            "display_mode": str(self.settings.get("general.display_mode", "desktop")),
            "monitor": str(self.settings.get("general.monitor", "primary")),
            "default_position": str(self.settings.get("general.default_position", "bottom_right")),
            "title_bar_offset": int(self.settings.get("animations.title_bar_offset", 28)),
            "window_perching": bool(self.settings.get("animations.window_perching", True)),
            "title_hang": bool(self.settings.get("animations.enabled.title_hang", True)),
            "target_applications": clean_target_apps
        }

    def _get_running_applications(self) -> list:
        """Return list of running visible apps detected on user's system."""
        try:
            from overlay.window_detector import WindowDetector
            windows = WindowDetector.get_visible_windows()
            target_apps = self.settings.get("general.target_applications", [])

            results = []
            seen_procs = set()
            for win in windows:
                proc = win.process_name
                if not proc or proc.lower() in seen_procs:
                    continue
                seen_procs.add(proc.lower())

                is_selected = any(WindowDetector.matches(win, s) for s in target_apps)
                results.append({
                    "process_name": proc,
                    "title": win.title or proc,
                    "executable_path": win.executable_path,
                    "display_name": win.application_name or proc,
                    "is_selected": is_selected
                })
            return sorted(results, key=lambda x: (not x["is_selected"], x["display_name"].lower()))
        except Exception as e:
            logger.warning(f"Error getting running applications: {e}")
            return []

    def _browse_and_add_application(self):
        """Open file dialog on Qt thread to select an executable."""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Application Executable", "", "Applications (*.exe);;All Files (*.*)"
        )
        if path:
            exe_path = os.path.normpath(path)
            proc_name = os.path.basename(exe_path)
            record = {
                "process_name": proc_name,
                "executable_path": exe_path,
                "display_name": Path(exe_path).stem
            }
            apps = list(self.settings.get("general.target_applications", []))
            def is_same(a, b):
                p_a = (a.get("process_name") if isinstance(a, dict) else str(a)).casefold()
                p_b = (b.get("process_name") if isinstance(b, dict) else str(b)).casefold()
                e_a = (a.get("executable_path") if isinstance(a, dict) else "").casefold()
                e_b = (b.get("executable_path") if isinstance(b, dict) else "").casefold()
                if e_a and e_b and os.path.normcase(e_a) == os.path.normcase(e_b):
                    return True
                return p_a == p_b or p_a.removesuffix(".exe") == p_b.removesuffix(".exe")

            if not any(is_same(a, record) for a in apps):
                apps.append(record)
                self.settings.set("general.target_applications", apps)
                self.settings.save()
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadDisplaySettings && window.SpiderBuddy.loadDisplaySettings()")


    def _get_focus_settings(self) -> dict:
        """Return focus mode, pomodoro, eye break, and inactivity settings."""
        limit_mins = float(self.settings.get("behavior.eye_break_minutes", 10))
        return {
            "focus_mode": bool(self.settings.get("behavior.focus_mode", False)),
            "focus_timer_active": bool(getattr(self, "_timer_active", False)),
            "focus_time_remaining": float(getattr(self, "_timer_remaining_sec", 0.0)),
            "continuous_work_seconds": float(getattr(self, "_continuous_sec", 0.0)),
            "enable_eye_break_alert": bool(self.settings.get("behavior.enable_eye_break_alert", True)),
            "eye_break_minutes": limit_mins,
            "inactivity_relax_minutes": round(float(self.settings.get("behavior.inactivity.relax_seconds", 120)) / 60.0, 1),
            "inactivity_sit_minutes": round(float(self.settings.get("behavior.inactivity.sit_seconds", 300)) / 60.0, 1),
            "inactivity_sleep_minutes": round(float(self.settings.get("behavior.inactivity.sleep_seconds", 600)) / 60.0, 1)
        }

    def _get_control_settings(self) -> dict:
        """Return keyboard shortcuts, WASD, mouse tracking, and reaction settings."""
        enabled_keys = self.settings.get("behavior.enabled_number_keys", {})
        if not isinstance(enabled_keys, dict):
            enabled_keys = {}

        hotkey_list = []
        for k in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
            if k in HOTKEY_MAPPINGS:
                act_name, act_title, quote = HOTKEY_MAPPINGS[k]
                hotkey_list.append({
                    "key": k,
                    "action": act_name,
                    "title": act_title,
                    "quote": quote,
                    "enabled": bool(enabled_keys.get(k, True))
                })

        return {
            "enable_animation_hotkeys": bool(self.settings.get("behavior.enable_animation_hotkeys", True)),
            "hotkeys_require_modifier": bool(self.settings.get("behavior.hotkeys_require_modifier", False)),
            "wasd_movement_enabled": bool(self.settings.get("behavior.wasd_movement_enabled", True)),
            "wasd_static_pin": bool(self.settings.get("behavior.wasd_static_pin", True)),
            "enable_mouse_following": bool(self.settings.get("behavior.enable_mouse_following", True)),
            "enable_spider_sense_dodging": bool(self.settings.get("behavior.enable_spider_sense_dodging", True)),
            "cursor_radius": int(self.settings.get("behavior.cursor_radius", 180)),
            "click_through": bool(self.settings.get("system.click_through", False)),
            "sound_enabled": bool(self.settings.get("behavior.sound_enabled", False)),
            "sound_volume": int(round(float(self.settings.get("behavior.sound_volume", 0.25)) * 100)),
            "movement_speed": round(float(self.settings.get("behavior.movement_speed", 3.0)), 1),
            "preset": str(self.settings.get("behavior.preset", "normal")),
            "enable_comic_bubbles": bool(self.settings.get("behavior.enable_comic_bubbles", True)),
            "hotkeys": hotkey_list
        }

    def _compute_cache_size(self) -> str:
        """Compute the total disk footprint of user data, logs, and frame buffers."""
        try:
            total_bytes = 0
            from app.bootstrap import get_user_data_dir
            user_dir = get_user_data_dir()
            if user_dir.exists():
                for root, _, files in os.walk(user_dir):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            total_bytes += os.path.getsize(fp)
                        except Exception:
                            pass
            if total_bytes < 1024:
                return f"{total_bytes} B"
            elif total_bytes < 1024 * 1024:
                return f"{total_bytes / 1024:.1f} KB"
            return f"{total_bytes / (1024 * 1024):.1f} MB"
        except Exception:
            return "2.4 MB"

    def _open_config_folder(self):
        """Open Spider-Buddy user configuration folder in Windows File Explorer."""
        try:
            from app.bootstrap import get_user_data_dir
            folder = get_user_data_dir()
            if not folder.exists():
                folder.mkdir(parents=True, exist_ok=True)
            import subprocess
            subprocess.Popen(["explorer.exe", str(folder)])
            self.speech_bubble_requested.emit("📂 Opened settings folder in Explorer!", 2200, "comic")
        except Exception as e:
            logger.warning("Could not open config folder: %s", e)

    def _get_app_settings(self) -> dict:
        """Return comprehensive application preferences, diagnostics, and system settings."""
        cfg_path = str(getattr(self.settings, "settings_file", ""))
        import platform
        scale = float(self.settings.get("general.scale", 1.0))
        size_px = int(round(scale * 200))
        opacity_pct = int(round(float(self.settings.get("general.opacity", 1.0)) * 100))
        return {
            "theme": str(self.settings.get("general.theme", "dark")),
            "display_fps": int(self.settings.get("general.display_fps", 0)),
            "animation_speed": float(self.settings.get("general.animation_speed", 1.0)),
            "start_minimized": bool(self.settings.get("system.start_minimized", True)),
            "run_on_startup": bool(self.settings.get("system.run_on_startup", False)),
            "always_on_top": bool(self.settings.get("system.always_on_top", True)),
            "click_through": bool(self.settings.get("system.click_through", False)),
            "monitor": str(self.settings.get("general.monitor", "primary")),
            "default_position": str(self.settings.get("general.default_position", "bottom_right")),
            "display_mode": str(self.settings.get("general.display_mode", "desktop")),
            "authentic_twos": bool(self.settings.get("animations.authentic_twos", True)),
            "companion_size": size_px,
            "companion_opacity": opacity_pct,
            "automatic_animations": bool(self.settings.get("behavior.automatic_animations", True)),
            "preset": str(self.settings.get("behavior.preset", "normal")),
            "movement_speed": round(float(self.settings.get("behavior.movement_speed", 3.0)), 1),
            "enable_spider_sense_dodging": bool(self.settings.get("behavior.enable_spider_sense_dodging", True)),
            "enable_mouse_following": bool(self.settings.get("behavior.enable_mouse_following", True)),
            "enable_comic_bubbles": bool(self.settings.get("behavior.enable_comic_bubbles", True)),
            "enable_heavy_load_scene": bool(self.settings.get("behavior.enable_heavy_load_scene", True)),
            "enable_audio_beat_bobbing": bool(self.settings.get("behavior.enable_audio_beat_bobbing", True)),
            "enable_battery_charging_reaction": bool(self.settings.get("behavior.enable_battery_charging_reaction", True)),
            "enable_low_battery_reaction": bool(self.settings.get("behavior.enable_low_battery_reaction", True)),
            "enable_suit_glitch": bool(self.settings.get("behavior.enable_suit_glitch", True)),
            "sound_enabled": bool(self.settings.get("behavior.sound_enabled", False)),
            "sound_volume": int(round(float(self.settings.get("behavior.sound_volume", 0.25)) * 100)),
            "enable_eye_break_alert": bool(self.settings.get("behavior.enable_eye_break_alert", True)),
            "eye_break_minutes": float(self.settings.get("behavior.eye_break_minutes", 10.0)),
            "enable_animation_hotkeys": bool(self.settings.get("behavior.enable_animation_hotkeys", True)),
            "hotkeys_require_modifier": bool(self.settings.get("behavior.hotkeys_require_modifier", False)),
            "wasd_movement_enabled": bool(self.settings.get("behavior.wasd_movement_enabled", True)),
            "wasd_static_pin": bool(self.settings.get("behavior.wasd_static_pin", True)),
            "config_path": cfg_path,
            "cache_size": self._compute_cache_size(),
            "version": "v2.5.0",
            "platform": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version(),
            "engine": "PySide6 Qt 6.8 • Chromium WebEngine"
        }

    # ── Signal Handlers from JavaScript ──────────────────────────────────
    def _on_web_action(self, data: dict):
        if not isinstance(data, dict):
            logger.warning(f"Ignored non-dict web action payload: {type(data)}: {data}")
            return
        action = data.get("action")
        logger.info(f"Received web action: {action} ({data})")

        if action == "dashboard_tab":
            self._dashboard_tab = str(data.get("tab", "Home"))
            if self._dashboard_tab == "Home" and self._last_frame_b64:
                self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setFrame && window.SpiderBuddy.setFrame({self._json_str(self._last_frame_b64)})")
        elif action == "play_activity":
            act = data.get("activity", "idle")
            if act in ACTIVITIES:
                self.activity_requested.emit(act)
            elif act == "trampoline":
                self.spawn_trampoline_requested.emit()
            elif act == "glitch":
                self.test_glitch_requested.emit()
            elif act == "battery":
                self.simulate_low_battery_toggled.emit(True)
                QTimer.singleShot(5000, lambda: self.simulate_low_battery_toggled.emit(False))
            elif act == "charging":
                self.simulate_charging_toggled.emit(True)
                QTimer.singleShot(5000, lambda: self.simulate_charging_toggled.emit(False))
            elif act == "load":
                self.simulate_heavy_load_toggled.emit(True)
            elif act == "music":
                self.simulate_music_toggled.emit(True)
            elif act == "bubbles":
                self.speech_bubble_requested.emit("Hey there! Spider-Man at your service! 🕷️", 3000, "comic")
            elif act == "sound":
                self.speech_bubble_requested.emit("Thwip! *Web sound fx*", 2000, "action")
            else:
                self.activity_requested.emit(act)

        elif action == "pause":
            self.set_running(False)
            self.stop_requested.emit()
        elif action == "resume":
            self.set_running(True)
            self.start_requested.emit()
        elif action == "hide":
            is_hidden = not self.settings.get("general.hidden", False)
            self.settings.set("general.hidden", is_hidden)
            self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setHidden && window.SpiderBuddy.setHidden({str(is_hidden).lower()})")
        elif action in ("start_focus", "start_focus_timer"):
            minutes = float(data.get("minutes", 25.0))
            self.focus_timer_started.emit(minutes)
            self.settings.set("behavior.focus_mode", True)
            self.activity_requested.emit("focus_read")
            self._timer_active = True
            self._timer_remaining_sec = minutes * 60.0
            self.speech_bubble_requested.emit(f"🎯 {int(minutes)}-Min Focus Started! I'll watch the perimeter while you work.", 3000, "comic")
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadFocusSettings && window.SpiderBuddy.loadFocusSettings()")
        elif action in ("stop_focus", "stop_focus_timer"):
            self.focus_timer_stopped.emit()
            self.settings.set("behavior.focus_mode", False)
            self.activity_requested.emit("idle")
            self._timer_active = False
            self._timer_remaining_sec = 0.0
            self.speech_bubble_requested.emit("Focus timer stopped. Great effort!", 2000, "comic")
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadFocusSettings && window.SpiderBuddy.loadFocusSettings()")
        elif action == "toggle_focus_mode":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.focus_mode", val)
            if val:
                self.activity_requested.emit("focus_read")
                self.speech_bubble_requested.emit("Focus mode activated! Sshh... let's get to work! 🎯", 2500, "comic")
            else:
                self.activity_requested.emit("idle")
                self.speech_bubble_requested.emit("Focus mode off! Ready to swing!", 2000, "comic")
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadFocusSettings && window.SpiderBuddy.loadFocusSettings()")
        elif action == "toggle_eye_break":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.enable_eye_break_alert", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadFocusSettings && window.SpiderBuddy.loadFocusSettings()")
        elif action == "set_eye_break_interval":
            mins = float(data.get("minutes", 10))
            self.settings.set("behavior.eye_break_minutes", mins)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadFocusSettings && window.SpiderBuddy.loadFocusSettings()")
        elif action == "test_eye_break":
            self.test_eye_break_requested.emit()
            self.speech_bubble_requested.emit("Time for water, man! 💧 Hydrate or diedrate!", 3000, "comic")
        elif action == "set_inactivity_threshold":
            stage = str(data.get("stage", "relax"))
            mins = float(data.get("minutes", 2))
            secs = mins * 60.0
            if stage in ("relax", "sit", "sleep"):
                self.settings.set(f"behavior.inactivity.{stage}_seconds", secs)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadFocusSettings && window.SpiderBuddy.loadFocusSettings()")
        elif action == "mood":
            mood = str(data.get("mood", "normal"))
            self.mood_preset_changed.emit(mood)
            if mood == "camo":
                self.test_glitch_requested.emit()
        elif action == "toggle_camo":
            self.mood_preset_changed.emit("camo")
            self.test_glitch_requested.emit()
        elif action == "select_character":
            cid = data.get("character_id")
            if cid and self.character_mgr:
                self.character_mgr.set_active_character(cid)
                self.character_changed.emit(cid)
                self._character_updated(cid)
                self._sync_full_state_to_ui()
                self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadCharacters && window.SpiderBuddy.loadCharacters()")
                self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadActivities && window.SpiderBuddy.loadActivities()")
        elif action == "set_size":
            size = int(data.get("size", 200))
            self.settings.set("general.scale", size / 200.0)
            self.size_changed.emit(size)
        elif action == "set_opacity":
            opacity = float(data.get("opacity", 100)) / 100.0
            self.settings.set("general.opacity", opacity)
        elif action == "open_import_dialog":
            self._open_import_dialog()
        elif action == "toggle_activity":
            name = data.get("activity", "")
            val = bool(data.get("enabled", True))
            if name in ACTIVITIES:
                self.settings.set(f"animations.enabled.{name}", val)
                if name in LEGACY_FLAGS:
                    leg = LEGACY_FLAGS[name]
                    if leg == "climbing":
                        up = self.settings.get("animations.enabled.climb_up", True)
                        down = self.settings.get("animations.enabled.climb_down", True)
                        self.settings.set("behavior.enable_climbing", up or down)
                    else:
                        self.settings.set(f"behavior.enable_{leg}", val)
                if name in ("title_perch", "title_hang"):
                    tp = self.settings.get("animations.enabled.title_perch", True)
                    th = self.settings.get("animations.enabled.title_hang", True)
                    self.settings.set("animations.enable_window_perching", tp or th)
            elif name in EFFECTS:
                key = EFFECTS[name][2]
                self.settings.set(key, val)
                if name == "sound":
                    self.settings.set("sound.enabled", val)
            self.settings.save()
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadActivities && window.SpiderBuddy.loadActivities()")
        elif action == "bulk_activities":
            mode = data.get("mode", "enable")
            if mode == "enable":
                self.settings.set("animations.enable_window_perching", True, auto_save=False)
                for name in ACTIVITIES:
                    self.settings.set(f"animations.enabled.{name}", True, auto_save=False)
                    if name in LEGACY_FLAGS:
                        self.settings.set(f"behavior.enable_{LEGACY_FLAGS[name]}", True, auto_save=False)
                self.settings.set("behavior.enable_climbing", True, auto_save=False)
                for _, (_, _, key, _) in EFFECTS.items():
                    self.settings.set(key, True, auto_save=False)
                self.settings.set("sound.enabled", True, auto_save=False)
                self.settings.save()
            elif mode == "disable":
                self.settings.set("animations.enable_window_perching", False, auto_save=False)
                for name in ACTIVITIES:
                    val = True if name == "idle" else False
                    self.settings.set(f"animations.enabled.{name}", val, auto_save=False)
                    if name in LEGACY_FLAGS:
                        self.settings.set(f"behavior.enable_{LEGACY_FLAGS[name]}", val, auto_save=False)
                self.settings.set("behavior.enable_climbing", False, auto_save=False)
                for _, (_, _, key, _) in EFFECTS.items():
                    self.settings.set(key, False, auto_save=False)
                self.settings.set("sound.enabled", False, auto_save=False)
                self.settings.save()
            elif mode == "reset":
                self.settings.set("animations.enable_window_perching", True, auto_save=False)
                for name in ACTIVITIES:
                    self.settings.set(f"animations.enabled.{name}", True, auto_save=False)
                    if name in LEGACY_FLAGS:
                        self.settings.set(f"behavior.enable_{LEGACY_FLAGS[name]}", True, auto_save=False)
                self.settings.set("behavior.enable_climbing", True, auto_save=False)
                for _, (_, _, key, _) in EFFECTS.items():
                    self.settings.set(key, key != "behavior.sound_enabled", auto_save=False)
                self.settings.set("sound.enabled", False, auto_save=False)
                self.settings.set("behavior.special_cooldown_seconds", 20, auto_save=False)
                self.settings.set("behavior.idle_timeout_seconds", 15, auto_save=False)
                self.settings.set("behavior.sleep_after_minutes", 5, auto_save=False)
                self.settings.set("behavior.automatic_animations", True, auto_save=False)
                self.settings.save()
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadActivities && window.SpiderBuddy.loadActivities()")
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadTimingSettings && window.SpiderBuddy.loadTimingSettings()")

        elif action == "set_timing":
            key_name = data.get("key", "")
            val = float(data.get("value", 20))
            timing_map = {
                "special_cooldown": "behavior.special_cooldown_seconds",
                "idle_timeout": "behavior.idle_timeout_seconds",
                "sleep_after": "behavior.sleep_after_minutes"
            }
            if key_name in timing_map:
                self.settings.set(timing_map[key_name], val)
        elif action == "set_playback_mode":
            automatic = bool(data.get("automatic", True))
            locked = str(data.get("locked_activity", "dance"))
            self.settings.set("behavior.automatic_animations", automatic)
            self.settings.set("behavior.locked_activity", locked)
        elif action == "set_display_mode":
            mode = str(data.get("mode", "desktop"))
            self.settings.set("general.display_mode", mode)
        elif action == "set_monitor":
            mon = str(data.get("monitor", "primary"))
            self.settings.set("general.monitor", mon)
        elif action == "set_default_position":
            pos = str(data.get("position", "bottom_right"))
            self.settings.set("general.default_position", pos)
        elif action == "save_current_position":
            self.save_position_requested.emit()
            self.speech_bubble_requested.emit("Saved current position as default!", 2000, "comic")
        elif action == "set_title_offset":
            val = int(data.get("offset", 28))
            self.settings.set("animations.title_bar_offset", val)
        elif action == "toggle_window_perch":
            val = bool(data.get("enabled", True))
            self.settings.set("animations.window_perching", val)
            self.settings.set("animations.enabled.perch", val)
        elif action == "toggle_title_hang":
            val = bool(data.get("enabled", True))
            self.settings.set("animations.enabled.title_hang", val)
        elif action == "add_target_application":
            app_spec = data.get("application", "")
            if app_spec:
                apps = list(self.settings.get("general.target_applications", []))
                if isinstance(app_spec, str):
                    app_str = app_spec.strip()
                    if not app_str.lower().endswith(".exe") and not os.path.isabs(app_str):
                        proc_name = app_str + ".exe"
                    else:
                        proc_name = os.path.basename(app_str)
                    record = {
                        "process_name": proc_name,
                        "executable_path": app_str if os.path.isabs(app_str) else "",
                        "display_name": Path(proc_name).stem
                    }
                else:
                    record = app_spec

                def is_same(a, b):
                    p_a = (a.get("process_name") if isinstance(a, dict) else str(a)).casefold()
                    p_b = (b.get("process_name") if isinstance(b, dict) else str(b)).casefold()
                    e_a = (a.get("executable_path") if isinstance(a, dict) else "").casefold()
                    e_b = (b.get("executable_path") if isinstance(b, dict) else "").casefold()
                    if e_a and e_b and os.path.normcase(e_a) == os.path.normcase(e_b):
                        return True
                    return p_a == p_b or p_a.removesuffix(".exe") == p_b.removesuffix(".exe")

                if not any(is_same(a, record) for a in apps):
                    apps.append(record)
                    self.settings.set("general.target_applications", apps)
                    self.settings.save()
                self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadDisplaySettings && window.SpiderBuddy.loadDisplaySettings()")
        elif action == "remove_target_application":
            app_spec = data.get("application", "")
            if app_spec:
                apps = list(self.settings.get("general.target_applications", []))
                def is_same(a, target):
                    p_a = (a.get("process_name") if isinstance(a, dict) else str(a)).casefold()
                    p_t = (target.get("process_name") if isinstance(target, dict) else (target if isinstance(target, str) else "")).casefold()
                    e_a = (a.get("executable_path") if isinstance(a, dict) else "").casefold()
                    e_t = (target.get("executable_path") if isinstance(target, dict) else "").casefold()
                    if e_a and e_t and os.path.normcase(e_a) == os.path.normcase(e_t):
                        return True
                    return p_a == p_t or p_a.removesuffix(".exe") == p_t.removesuffix(".exe")

                apps = [a for a in apps if not is_same(a, app_spec)]
                self.settings.set("general.target_applications", apps)
                self.settings.save()
                self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadDisplaySettings && window.SpiderBuddy.loadDisplaySettings()")
        elif action == "browse_application":
            QTimer.singleShot(0, self._browse_and_add_application)

        elif action == "toggle_animation_hotkeys":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.enable_animation_hotkeys", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "toggle_hotkeys_require_modifier":
            val = bool(data.get("enabled", False))
            self.settings.set("behavior.hotkeys_require_modifier", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "toggle_number_key":
            k = str(data.get("key", "1"))
            val = bool(data.get("enabled", True))
            keys = dict(self.settings.get("behavior.enabled_number_keys", {}))
            keys[k] = val
            self.settings.set("behavior.enabled_number_keys", keys)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "set_all_number_keys":
            val = bool(data.get("enabled", True))
            keys = {k: val for k in HOTKEY_MAPPINGS}
            self.settings.set("behavior.enabled_number_keys", keys)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "test_hotkey":
            act = data.get("activity")
            quote = data.get("quote", "")
            if act and isinstance(act, str):
                self.activity_requested.emit(act.strip())
            if quote and isinstance(quote, str):
                self.speech_bubble_requested.emit(quote.strip(), 3000, "comic")
        elif action == "toggle_wasd":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.wasd_movement_enabled", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "toggle_wasd_static_pin":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.wasd_static_pin", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "toggle_mouse_following":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.enable_mouse_following", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "toggle_spider_sense_dodging":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.enable_spider_sense_dodging", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "set_cursor_radius":
            rad = int(data.get("radius", 180))
            self.settings.set("behavior.cursor_radius", rad)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "toggle_click_through":
            val = bool(data.get("enabled", False))
            self.settings.set("system.click_through", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "toggle_sound":
            val = bool(data.get("enabled", False))
            self.settings.set("behavior.sound_enabled", val)
            self.settings.set("sound.enabled", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "set_sound_volume":
            vol = float(data.get("volume", 25))
            self.settings.set("behavior.sound_volume", vol / 100.0)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "set_movement_speed":
            spd = float(data.get("speed", 3.0))
            self.settings.set("behavior.movement_speed", spd)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "set_pacing_preset":
            preset = str(data.get("preset", "normal"))
            self.settings.set("behavior.preset", preset)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "toggle_comic_bubbles":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.enable_comic_bubbles", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
        elif action == "set_theme":
            theme = str(data.get("theme", "dark"))
            self.settings.set("general.theme", theme)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action == "set_display_fps":
            fps = int(data.get("fps", 0))
            self.settings.set("general.display_fps", fps)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action == "set_animation_speed":
            spd = float(data.get("speed", 1.0))
            self.settings.set("general.animation_speed", spd)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action == "toggle_start_minimized":
            val = bool(data.get("enabled", True))
            self.settings.set("system.start_minimized", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action == "toggle_run_on_startup":
            val = bool(data.get("enabled", False))
            self.settings.set("system.run_on_startup", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action == "toggle_always_on_top":
            val = bool(data.get("enabled", True))
            self.settings.set("system.always_on_top", val)
            self.set_always_on_top(val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action == "reset_all_settings":
            self.settings.reset_to_defaults()
            self._sync_full_state_to_ui()
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadCharacters && window.SpiderBuddy.loadCharacters()")
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadActivities && window.SpiderBuddy.loadActivities()")
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadDisplaySettings && window.SpiderBuddy.loadDisplaySettings()")
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadFocusSettings && window.SpiderBuddy.loadFocusSettings()")
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadControlSettings && window.SpiderBuddy.loadControlSettings()")
            self.speech_bubble_requested.emit("⚙️ Factory settings restored!", 2500, "comic")
        elif action == "reset_companion_stats":
            self.settings.set("stats.distance_px", 0)
            self.settings.set("stats.webs_shot", 0)
            self.settings.set("stats.active_seconds", 0)
            self.settings.save()
            self.reset_companion_stats_requested.emit()
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.setStats && window.SpiderBuddy.setStats('0 px', 0, '0m')")
            self.speech_bubble_requested.emit("📊 Companion stats have been reset!", 2500, "comic")
        elif action == "toggle_authentic_twos":
            val = bool(data.get("enabled", True))
            self.settings.set("animations.authentic_twos", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action == "toggle_heavy_load_scene":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.enable_heavy_load_scene", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action == "toggle_audio_beat_bobbing":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.enable_audio_beat_bobbing", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action == "toggle_battery_charging_reaction":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.enable_battery_charging_reaction", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action == "toggle_suit_glitch":
            self.settings.set("behavior.enable_suit_glitch", bool(data.get("enabled", True)))
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings()")
        elif action == "toggle_low_battery_reaction":
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.enable_low_battery_reaction", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action in ("toggle_automatic_animations", "toggle_automatic_mode"):
            val = bool(data.get("enabled", True))
            self.settings.set("behavior.automatic_animations", val)
            self._run_js("window.SpiderBuddy && window.SpiderBuddy.loadAppSettings && window.SpiderBuddy.loadAppSettings()")
        elif action == "open_config_folder":
            self._open_config_folder()
        elif action == "play_test_sound":
            self.test_sound_requested.emit()
        elif action == "clear_app_cache":
            try:
                if hasattr(self, "web_view") and self.web_view.page():
                    self.web_view.page().profile().clearHttpCache()
                from app.bootstrap import get_user_data_dir
                log_dir = get_user_data_dir() / "logs"
                if log_dir.exists():
                    for f in log_dir.glob("spider_buddy.log.*"):
                        try:
                            f.unlink()
                        except Exception:
                            pass
            except Exception as exc:
                logger.debug("Clear app cache error: %s", exc)
            self.speech_bubble_requested.emit("🧹 App cache and frame buffers cleared!", 2500, "comic")
            new_size = self._compute_cache_size()
            self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setCacheSize && window.SpiderBuddy.setCacheSize({self._json_str(new_size)})")
        elif action == "reload_ui":
            self.web_view.reload()
        elif action == "navigate":
            page = data.get("page", "")
            logger.info(f"Navigate to {page}")
            if page == "Characters":
                self._run_js("window.SpiderBuddy && window.SpiderBuddy.switchTab('Characters')")
            elif page == "Home":
                self._run_js("window.SpiderBuddy && window.SpiderBuddy.switchTab('Home')")
            elif page == "Activities":
                self._run_js("window.SpiderBuddy && window.SpiderBuddy.switchTab('Activities')")
            elif page == "Desktop & Apps":
                self._run_js("window.SpiderBuddy && window.SpiderBuddy.switchTab('Desktop & Apps')")
            elif page in ("Focus & Breaks", "Focus settings"):
                self._run_js("window.SpiderBuddy && window.SpiderBuddy.switchTab('Focus & Breaks')")
            elif page == "Controls":
                self._run_js("window.SpiderBuddy && window.SpiderBuddy.switchTab('Controls')")
            elif page == "Settings":
                self._run_js("window.SpiderBuddy && window.SpiderBuddy.switchTab('Settings')")

    # ── API Methods Expected by SpiderBuddyApp ───────────────────────────
    def update_preview(self, pixmap: QPixmap):
        """Called whenever the animation engine advances a frame."""
        if pixmap.isNull():
            return

        now = time.monotonic()
        if self._last_preview_bytes and (
            not self.isVisible() or self.isMinimized() or self._dashboard_tab != "Home"
            or now - getattr(self, "_last_preview_at", 0.0) < 1.0
        ):
            return
        self._last_preview_at = now

        # Encode live frame as base64 and cache
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        # Encode only the pixels the small dashboard preview can display.
        preview = pixmap.scaled(280, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation) if (
            pixmap.width() > 280 or pixmap.height() > 260) else pixmap
        preview.save(buf, "PNG")
        raw_bytes = bytes(buf.data())
        if raw_bytes == self._last_preview_bytes:
            return
        self._last_preview_bytes = raw_bytes
        b64 = bytes(buf.data().toBase64()).decode("ascii")
        self._last_frame_b64 = b64

        # Push to Web UI only if window is visible and on Home tab
        if self.isVisible() and not self.isMinimized() and self._dashboard_tab == "Home":
            self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setFrame && window.SpiderBuddy.setFrame({self._json_str(b64)})")

    def set_status(self, old, state):
        """Called when state machine changes companion activity."""
        state_str = getattr(state, "value", str(state))
        new_text = state_str.replace("_", " ").title()
        if new_text == self._status_text:
            return
        self._status_text = new_text
        self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setActivity({self._json_str(self._status_text)})")

    def set_running(self, running: bool):
        if self._is_running == running:
            return
        self._is_running = running
        self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setRunning({str(running).lower()})")

    def update_battery_status(self, percent: int, is_charging: bool, is_low: bool):
        try:
            if not self.isVisible() or self.isMinimized():
                return
        except RuntimeError:
            return
        char_profile = getattr(self.character_mgr, "active_character", None) if self.character_mgr else None
        char_id = getattr(char_profile, "id", "tom_holland") if char_profile else "tom_holland"
        suit_name, suit_status = get_battery_lore(char_id, percent, is_charging, is_low)
        state_key = (int(percent), bool(is_charging), bool(is_low), suit_name, suit_status)
        if state_key == getattr(self, "_last_battery_state", None):
            return
        self._last_battery_state = state_key
        self._run_js(
            f"window.SpiderBuddy && window.SpiderBuddy.setBattery("
            f"{int(percent)}, {str(is_charging).lower()}, {str(is_low).lower()}, "
            f"{self._json_str(suit_name)}, {self._json_str(suit_status)})"
        )

    def update_system_load(self, cpu: float, ram: float, is_heavy: bool):
        try:
            if not self.isVisible() or self.isMinimized():
                return
        except RuntimeError:
            return
        cpu_val = round(float(cpu), 1)
        ram_val = round(float(ram), 1)
        state_key = (cpu_val, ram_val, bool(is_heavy))
        if state_key == getattr(self, "_last_system_load", None):
            return
        self._last_system_load = state_key
        sense_text, sense_color = get_spidey_sense_status(cpu, ram, is_heavy)
        self._run_js(
            f"window.SpiderBuddy && window.SpiderBuddy.setHardwareLoad("
            f"{cpu_val}, {ram_val}, {str(is_heavy).lower()}, "
            f"{self._json_str(sense_text)}, {self._json_str(sense_color)})"
        )

    def update_companion_stats(self, stats: dict):
        try:
            if not self.isVisible() or self.isMinimized():
                return
        except RuntimeError:
            return
        dist_px = stats.get("distance_px", 0)
        dist_str = f"{dist_px/1000:.1f}K" if dist_px >= 1000 else f"{int(dist_px)}"
        webs = stats.get("webs_shot", 0)
        secs = stats.get("active_seconds", 0)
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        uptime_str = f"{h}h {m}m" if h > 0 else f"{m}m"
        state_key = (dist_str, int(webs), uptime_str)
        if state_key == getattr(self, "_last_companion_stats", None):
            return
        self._last_companion_stats = state_key
        self._run_js(
            f"window.SpiderBuddy && window.SpiderBuddy.setStats("
            f"{self._json_str(dist_str)}, {int(webs)}, {self._json_str(uptime_str)})"
        )

    def update_eye_break_status(self, *args):
        """Handle status update from EyeBreakService (continuous_sec, timer_remaining_sec, timer_active)."""
        if len(args) == 3:
            continuous_sec, remaining_sec, is_active = args
            self._continuous_sec = float(continuous_sec)
            self._timer_remaining_sec = float(remaining_sec)
            self._timer_active = bool(is_active)
            if is_active:
                mins = int(remaining_sec // 60)
                secs = int(remaining_sec % 60)
                time_str = f"{mins:02d}:{secs:02d}"
                status_str = "Focusing" if remaining_sec > 0 else "Break"
            else:
                time_str = "25:00"
                status_str = "Ready"
            self._focus_status_text = status_str
            self._timer_time_str = time_str
            limit_mins = float(self.settings.get("behavior.eye_break_minutes", 10))
            state_key = (time_str, status_str, round(float(continuous_sec), 0), limit_mins)
            self._last_eye_break_state = state_key
            if not self.isVisible() or self.isMinimized():
                return
            if state_key == getattr(self, "_rendered_eye_break_state", None):
                return
            self._rendered_eye_break_state = state_key
            self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setTimer({self._json_str(time_str)}, {self._json_str(status_str)})")
            self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setEyeBreakProgress && window.SpiderBuddy.setEyeBreakProgress({float(continuous_sec)}, {limit_mins * 60.0})")
        elif len(args) == 1 and isinstance(args[0], str):
            if not self.isVisible() or self.isMinimized():
                return
            self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setTimer(null, {self._json_str(args[0])})")

    def set_always_on_top(self, enabled: bool) -> None:
        """Set whether the main application window stays on top of other windows."""
        self.setWindowFlag(Qt.WindowStaysOnTopHint, bool(enabled))
        if sys.platform == "win32" and self.isVisible():
            try:
                import ctypes
                HWND_TOPMOST = -1
                HWND_NOTOPMOST = -2
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOACTIVATE = 0x0010
                target = HWND_TOPMOST if enabled else HWND_NOTOPMOST
                ctypes.windll.user32.SetWindowPos(
                    int(self.winId()), target, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                )
            except Exception:
                self.show()
        elif self.isVisible():
            self.show()

    def update_audio_meter(self, peak: float, smoothed: float):
        self._audio_peak = float(peak)
        self._audio_smoothed = float(smoothed)
        if not self.isVisible() or self.isMinimized():
            return
        pct = int(peak * 100)
        self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setAudioMeter && window.SpiderBuddy.setAudioMeter({pct})")

    def update_music_state(self, is_playing: bool, volume: float):
        self._music_playing = bool(is_playing)
        self._music_volume = float(volume)
        if not self.isVisible() or self.isMinimized():
            return
        status = "Active! Beat-bobbing engaged" if is_playing else "Inactive"
        self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setMusicStatus && window.SpiderBuddy.setMusicStatus({self._json_str(status)}, {float(volume)})")

    def _character_updated(self, char_id_or_profile):
        """Called when active character profile changes."""
        profile = None
        if hasattr(char_id_or_profile, "root_path"):
            profile = char_id_or_profile
        elif self.character_mgr:
            if hasattr(self.character_mgr, "active_character") and hasattr(self.character_mgr.active_character, "root_path"):
                profile = self.character_mgr.active_character
            elif hasattr(self.character_mgr, "available_characters") and isinstance(char_id_or_profile, str):
                profile = self.character_mgr.available_characters.get(char_id_or_profile)

        if not profile:
            return

        display_name = getattr(profile, "display_name", "Spider-Man")
        prev_file = Path(profile.root_path) / "preview.png"
        if prev_file.exists():
            self._last_preview_bytes = prev_file.read_bytes()
            b64 = base64.b64encode(self._last_preview_bytes).decode("ascii")
            self._last_frame_b64 = b64
            self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setFrame({self._json_str(b64)})")

        import random
        quote = random.choice(SPIDEY_QUOTES)
        self._run_js(f"window.SpiderBuddy && window.SpiderBuddy.setCharacter({self._json_str(display_name)}, {self._json_str(quote)})")

    def stop(self):
        """Orderly shutdown of web server."""
        if hasattr(self, "web_server"):
            self.web_server.stop()

    def nativeEvent(self, event_type, message):
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0014:  # WM_ERASEBKGND: prevent white GDI flash before Chromium paints
                return True, 1
        return super().nativeEvent(event_type, message)

    def closeEvent(self, event):
        """Hide dashboard to system tray instead of destroying web server so companion stays active."""
        if getattr(self, "_force_close", False):
            self.stop()
            super().closeEvent(event)
        else:
            event.ignore()
            self.hide()


def launch_standalone():
    """Standalone launcher to test and inspect the HTML/CSS/JS frontend."""
    logging.basicConfig(level=logging.INFO)
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication(sys.argv)
        owns_app = True

    from core.character_manager import CharacterManager
    char_mgr = CharacterManager()
    win = WebMainWindow(character_mgr=char_mgr)
    win.show()

    if owns_app:
        sys.exit(app.exec())
    return win


if __name__ == "__main__":
    launch_standalone()
