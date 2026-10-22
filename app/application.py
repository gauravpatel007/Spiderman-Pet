"""Main application controller orchestrating Spider-Buddy components."""
import logging
import sys
from typing import Optional
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QApplication

from .lifecycle import SingleInstanceLock
from services.settings_service import get_settings
from services.activity_monitor import ActivityMonitor
from services.sound_service import SoundService
from services.startup_service import StartupService
from services.session_manager import SessionManager
from services.battery_service import BatteryService
from services.hotkey_service import HotkeyService
from services.eye_break_service import EyeBreakService
from services.system_load_service import SystemLoadService
from services.audio_sync_service import AudioSyncService
from services.companion_stats import CompanionStatsService
from core.character_manager import CharacterManager
from core.state_machine import StateMachine, CharacterState
from core.animation_engine import AnimationEngine
from core.movement_controller import MovementController
from core.behavior_controller import BehaviorController
from core.interaction_manager import InteractionManager
from overlay.overlay_manager import OverlayManager
from ui.main_window import MainWindow
from ui.web_window import WebMainWindow
from ui.system_tray import SystemTrayIcon

logger = logging.getLogger("SpiderBuddy.Application")


class SpiderBuddyApp(QObject):
    """Orchestrates Spider-Buddy startup sequence, services, and event wiring."""

    def __init__(self, qapp: QApplication, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.qapp = qapp
        self._shutting_down = False
        self.qapp.setQuitOnLastWindowClosed(False)

        # 1. Single Instance Check
        self.instance_lock = SingleInstanceLock(parent=self)
        if not self.instance_lock.check_and_lock():
            logger.info("Exiting because primary instance is already active.")
            sys.exit(0)

        self.instance_lock.secondary_instance_launched.connect(self._on_secondary_instance_launched)

        try:
            self._initialize_components()
        except Exception:
            logger.exception("Application initialization failed")
            self.shutdown()
            raise

    def _initialize_components(self) -> None:
        # 2. Load Saved Settings
        self.settings = get_settings()

        # 3. Initialize Windows Services
        self.activity_monitor = ActivityMonitor(parent=self)
        self.startup_service = StartupService()
        self.session_mgr = SessionManager(parent=self)
        self.sound_service = SoundService(self)
        self.battery_service = BatteryService(parent=self)
        self.hotkey_service = HotkeyService(parent=self)
        self.hotkey_service.set_enabled(bool(self.settings.get("behavior.enable_animation_hotkeys", True)))
        self.hotkey_service.set_require_modifier(bool(self.settings.get("behavior.hotkeys_require_modifier", False)))
        self.hotkey_service.set_wasd_enabled(bool(self.settings.get("behavior.wasd_movement_enabled", True)))
        self.eye_break_service = EyeBreakService(parent=self)
        self.system_load_service = SystemLoadService(parent=self)
        self.audio_sync_service = AudioSyncService(parent=self)
        self.stats_service = CompanionStatsService(parent=self)

        # Sync startup registry setting with saved user preference
        reg_enabled = self.startup_service.is_startup_enabled()
        user_startup = bool(self.settings.get("system.run_on_startup", False))
        if reg_enabled != user_startup:
            self.startup_service.set_startup_enabled(user_startup)

        # 4. Initialize Core State & Character Management
        self.character_mgr = CharacterManager(parent=self)
        self.state_machine = StateMachine(initial_state=CharacterState.IDLE, parent=self)
        self.animation_engine = AnimationEngine(parent=self)
        self.movement_ctrl = MovementController(parent=self)

        # 5. Initialize Behavior and Interactions
        self.behavior_ctrl = BehaviorController(
            state_machine=self.state_machine,
            movement=self.movement_ctrl,
            animation=self.animation_engine,
            parent=self
        )
        self.interaction_mgr = InteractionManager(
            state_machine=self.state_machine,
            movement=self.movement_ctrl,
            character_mgr=self.character_mgr,
            animation=self.animation_engine,
            behavior=self.behavior_ctrl,
            parent=self
        )

        # 6. Initialize Overlay Manager
        self.overlay_mgr = OverlayManager(movement=self.movement_ctrl, parent=self)
        self.interaction_mgr.overlay = self.overlay_mgr.overlay
        self.interaction_mgr.overlay_mgr = self.overlay_mgr
        self.behavior_ctrl.overlay = self.overlay_mgr.overlay
        self.behavior_ctrl.position_activity = self.overlay_mgr.position_activity
        if hasattr(self.overlay_mgr, 'sticky_notes_mgr'):
            self.overlay_mgr.sticky_notes_mgr.set_enabled(
                bool(self.settings.get('behavior.enable_sticky_notes', True))
            )

        # 7. Initialize UI (Main Window + System Tray)
        if self.settings.get("ui.engine", "web") == "legacy":
            self.main_window = MainWindow(character_mgr=self.character_mgr)
        else:
            self.main_window = WebMainWindow(character_mgr=self.character_mgr)
        self.system_tray = SystemTrayIcon(character_mgr=self.character_mgr, parent=self)

        self._wire_components()
        self.qapp.aboutToQuit.connect(self.shutdown)

    def _wire_components(self) -> None:
        """Wire all application signals and handlers together."""
        # Animation frame updates feed the transparent overlay
        self.animation_engine.frame_updated.connect(self.overlay_mgr.overlay.set_frame)
        self.animation_engine.frame_updated.connect(self.main_window.update_preview)
        self.state_machine.state_changed.connect(self.main_window.set_status)
        self.state_machine.state_changed.connect(self.overlay_mgr.on_activity_changed)
        self.main_window.activity_requested.connect(self._play_activity)
        self.main_window.activity_context_validator = self._activity_context_reason
        self.main_window.save_position_requested.connect(self.overlay_mgr.save_custom_position)

        # Overlay mouse and keyboard interactions route to InteractionManager & HotkeyService
        self.overlay_mgr.overlay.drag_started.connect(
            lambda g_pos, l_pos: self.interaction_mgr.handle_mouse_press(g_pos, l_pos, Qt.LeftButton)
        )
        self.overlay_mgr.overlay.drag_moved.connect(self.interaction_mgr.handle_mouse_move)
        self.overlay_mgr.overlay.drag_ended.connect(
            lambda: self.interaction_mgr.handle_mouse_release(Qt.LeftButton)
        )
        self.overlay_mgr.overlay.clicked.connect(self.interaction_mgr.handle_click)
        self.overlay_mgr.overlay.double_clicked.connect(self.interaction_mgr.handle_double_click)
        self.overlay_mgr.overlay.context_menu_requested.connect(self.interaction_mgr.show_context_menu)
        self.overlay_mgr.overlay.key_pressed.connect(self.hotkey_service.trigger_key)

        # Interaction manager events
        self.interaction_mgr.open_dashboard_requested.connect(self.show_main_window)
        self.interaction_mgr.quit_requested.connect(self.shutdown)

        # Global Hotkey Service (Win+1..0 / Alt+1..0), WASD Movement, & Spacebar Drop
        self.hotkey_service.activity_triggered.connect(self._on_hotkey_triggered)
        self.hotkey_service.ctrl_click_triggered.connect(self._on_ctrl_click_web_shoot)
        self.hotkey_service.wasd_input.connect(self.behavior_ctrl.handle_wasd)
        self.hotkey_service.input_blocked = self.main_window.isActiveWindow
        self.hotkey_service.space_pressed.connect(self.behavior_ctrl.drop_to_ground)

        # System tray events
        self.system_tray.show_main_window_requested.connect(self.show_main_window)
        self.system_tray.toggle_companion_requested.connect(self._toggle_companion)
        self.system_tray.quit_requested.connect(self.shutdown)

        # Character switching
        self.character_mgr.character_changed.connect(self._on_character_changed)
        self.main_window.character_changed.connect(self.character_mgr.set_active_character)

        self.overlay_mgr.owner_changed.connect(self.main_window.overlay_owner_label.setText)
        self.overlay_mgr.owner_changed.connect(lambda _: self.main_window.qml_bridge.refresh_home())

        # Display Mode switching
        self.main_window.display_mode_changed.connect(self.overlay_mgr.set_display_mode)

        # Size slider changes
        self.main_window.size_changed.connect(self._on_size_changed)

        # Start / Stop toggle
        self.main_window.start_requested.connect(self.start_companion)
        self.main_window.stop_requested.connect(self.stop_companion)

        # Session management & display changes (Phase 9.3)
        self.session_mgr.session_locked.connect(self._on_session_locked)
        self.session_mgr.session_unlocked.connect(self._on_session_unlocked)
        self.session_mgr.system_suspended.connect(self._on_session_locked)
        self.session_mgr.system_resumed.connect(self._on_session_unlocked)
        self.session_mgr.display_changed.connect(self._on_display_changed)

        # Resource management: suspend animation when overlay is hidden (Phase 9.4)
        self.overlay_mgr.visibility_state_changed.connect(self._on_overlay_visibility_changed)

        # Smart activity reactions (Phase 10.2)
        self.overlay_mgr.application_entered.connect(
            lambda win, is_new: self.behavior_ctrl.on_application_entered(is_new)
        )

        # User activity idle detection
        self.activity_monitor.idle_tick.connect(self.behavior_ctrl.update_idle)
        self.settings.setting_changed.connect(self._on_setting_changed)
        self.state_machine.state_changed.connect(self._on_state_sound)

        # Laptop battery service & glitch reactions
        self.battery_service.battery_updated.connect(self._on_battery_updated)
        self.battery_service.charging_started.connect(self._on_charging_started)
        self.battery_service.charging_stopped.connect(self._on_charging_stopped)
        self.battery_service.glitch_triggered.connect(self._on_glitch_triggered)
        self.main_window.test_glitch_requested.connect(self.battery_service.trigger_test_glitch)
        self.main_window.simulate_low_battery_toggled.connect(self.battery_service.simulate_low_battery)
        self.main_window.simulate_charging_toggled.connect(self.battery_service.simulate_charging)

        # Eye-break health reminders & focus timer
        self.activity_monitor.idle_tick.connect(self.eye_break_service.on_idle_tick)
        self.eye_break_service.alert_triggered.connect(self._on_eye_break_alert)
        self.eye_break_service.status_updated.connect(self.main_window.update_eye_break_status)
        self.main_window.test_eye_break_requested.connect(self.eye_break_service.trigger_test_alert)
        self.main_window.focus_timer_started.connect(self.eye_break_service.start_focus_timer)
        self.main_window.focus_timer_stopped.connect(self.eye_break_service.stop_focus_timer)

        # Interactive Web Trampolines
        self.interaction_mgr.trampoline_created.connect(self.overlay_mgr.trampoline_overlay.set_trampoline)
        self.interaction_mgr.trampoline_created.connect(
            lambda p1, p2: self.movement_ctrl.set_active_trampoline(self.overlay_mgr.trampoline_overlay)
        )
        self.main_window.spawn_trampoline_requested.connect(self.interaction_mgr.spawn_trampoline_below)

        # Heavy system load monitoring (>85% classic collapsing beam lift)
        self.system_load_service.load_updated.connect(self._on_system_load_updated)
        self.system_load_service.heavy_load_changed.connect(self._on_heavy_load_changed)
        self.main_window.simulate_heavy_load_toggled.connect(self.system_load_service.simulate_heavy_load)

        # Audio & music synchronization (WASAPI headphone beat-bobbing)
        self.audio_sync_service.audio_meter_updated.connect(self._on_audio_meter_updated)
        self.audio_sync_service.beat_detected.connect(self._on_beat_detected)
        self.audio_sync_service.music_state_changed.connect(self._on_music_state_changed)
        self.main_window.simulate_music_toggled.connect(self.audio_sync_service.simulate_music)

        # Companion Gameplay Statistics & Interactive Dashboard
        self.movement_ctrl.position_changed.connect(self.stats_service.record_movement)
        self.state_machine.state_changed.connect(self._on_state_changed_stats)
        self.stats_service.stats_updated.connect(self.main_window.update_companion_stats)
        self.main_window.reset_companion_stats_requested.connect(self.stats_service.reset_stats)
        self.main_window.test_sound_requested.connect(self.sound_service.play_test_sound)
        self.main_window.speech_bubble_requested.connect(self.overlay_mgr.overlay.show_speech_bubble)
        self.main_window.mood_preset_changed.connect(self._on_mood_preset_changed)

        # Spider Sticky Notes & Reminders
        if hasattr(self.interaction_mgr, "open_sticky_notes_requested"):
            self.interaction_mgr.open_sticky_notes_requested.connect(self._on_open_sticky_notes_requested)
        if hasattr(self.main_window, "sticky_note_action_received"):
            self.main_window.sticky_note_action_received.connect(self._on_sticky_note_action)

        # Web-Shoot to Cursor from UI action
        if hasattr(self.main_window, "shoot_web_cursor_requested"):
            from PySide6.QtCore import QPoint
            self.main_window.shoot_web_cursor_requested.connect(
                lambda x, y: self.interaction_mgr.shoot_web_at_cursor(QPoint(x, y))
            )

    def _on_state_changed_stats(self, old_state, new_state) -> None:
        """Track web swings and acrobatic actions for gameplay statistics."""
        if new_state == CharacterState.SWING:
            self.stats_service.record_web_swing()

    def _on_mood_preset_changed(self, mode: str) -> None:
        """Activate quick mood preset (chill, hyper, camo)."""
        logger.info("Mood preset changed to: %s", mode)
        if mode == "camo":
            self.settings.set("general.opacity", 0.40)
            self.overlay_mgr.overlay.set_character_opacity(0.40)
            self.overlay_mgr.overlay.show_speech_bubble("👻 Stealth Camo: 40% translucent & quiet.", 2400, "glitch")
        elif mode == "hyper":
            self.settings.set("general.opacity", 1.0)
            self.overlay_mgr.overlay.set_character_opacity(1.0)
            self.settings.set("general.animation_speed", 1.25)
            self.settings.set("behavior.movement_speed", 5.5)
            self.animation_engine.set_speed_multiplier(1.25)
            self.overlay_mgr.overlay.show_speech_bubble("⚡ Hyper Mode: Maximum energy & speed!", 2400, "action")
        elif mode == "chill":
            self.settings.set("general.opacity", 1.0)
            self.overlay_mgr.overlay.set_character_opacity(1.0)
            self.settings.set("general.animation_speed", 0.85)
            self.settings.set("behavior.movement_speed", 2.2)
            self.animation_engine.set_speed_multiplier(0.85)
            self.overlay_mgr.overlay.show_speech_bubble("🧘 Chill Mode: Resting quietly.", 2400, "comic")

    def _is_main_window_valid(self) -> bool:
        mw = getattr(self, "main_window", None)
        if mw is None:
            return False
        try:
            import shiboken6
            return shiboken6.isValid(mw)
        except Exception:
            return True

    def _on_system_load_updated(self, cpu: float, ram: float) -> None:
        """Forward system CPU and RAM usage to dashboard."""
        mw = getattr(self, "main_window", None)
        if mw is not None:
            try:
                import shiboken6
                if not shiboken6.isValid(mw):
                    mw = None
            except Exception:
                pass
        if mw is not None:
            try:
                mw.update_system_load(cpu, ram, self.system_load_service.is_heavy_load())
            except (RuntimeError, AttributeError):
                pass

    def _on_heavy_load_changed(self, is_heavy: bool, cpu: float, ram: float) -> None:
        """Trigger collapsing beam scene when CPU or RAM > 85%."""
        if (self.settings.get("behavior.enable_heavy_load_scene", True)
                and not self.settings.get("behavior.focus_mode", False)):
            self.overlay_mgr.set_heavy_load(is_heavy, cpu, ram)
            self.behavior_ctrl.set_heavy_load(is_heavy, cpu, ram)
        else:
            self.overlay_mgr.set_heavy_load(False, cpu, ram)
            self.behavior_ctrl.set_heavy_load(False, cpu, ram)
        mw = getattr(self, "main_window", None)
        if mw is not None:
            try:
                import shiboken6
                if not shiboken6.isValid(mw):
                    mw = None
            except Exception:
                pass
        if mw is not None:
            try:
                mw.update_system_load(cpu, ram, is_heavy)
            except (RuntimeError, AttributeError):
                pass

    def _on_audio_meter_updated(self, peak: float, smoothed: float) -> None:
        """Forward peak audio meter to dashboard."""
        mw = getattr(self, "main_window", None)
        if mw is not None:
            try:
                import shiboken6
                if not shiboken6.isValid(mw):
                    mw = None
            except Exception:
                pass
        if mw is not None:
            try:
                mw.update_audio_meter(peak, smoothed)
            except (RuntimeError, AttributeError):
                pass

    def _on_beat_detected(self, intensity: float) -> None:
        """Forward beat hit to overlay for head-bob and sneaker tap."""
        if self.settings.get("behavior.enable_audio_beat_bobbing", True):
            self.overlay_mgr.trigger_beat(intensity)

    def _on_music_state_changed(self, is_playing: bool, volume: float) -> None:
        """Handle music playback start/stop for headphone beat-bobbing."""
        if self.settings.get("behavior.enable_audio_beat_bobbing", True):
            self.overlay_mgr.set_music_playing(is_playing, volume)
            self.behavior_ctrl.set_music_playing(is_playing, volume)
        else:
            self.overlay_mgr.set_music_playing(False, volume)
            self.behavior_ctrl.set_music_playing(False, volume)
        mw = getattr(self, "main_window", None)
        if mw is not None:
            try:
                import shiboken6
                if not shiboken6.isValid(mw):
                    mw = None
            except Exception:
                pass
        if mw is not None:
            try:
                mw.update_music_state(is_playing, volume)
            except (RuntimeError, AttributeError):
                pass

    def _on_battery_updated(self, percent: int, is_charging: bool, is_low: bool) -> None:
        """Handle laptop battery updates and notify UI, overlay, and behavior."""
        char_id = getattr(self.character_mgr.active_character, "id", "")
        permitted_charging = is_charging and bool(self.settings.get("behavior.enable_battery_charging_reaction", True))
        self.overlay_mgr.set_battery_charging(permitted_charging, percent, char_id)
        self.behavior_ctrl.set_battery_charging(permitted_charging)
        permitted_low = is_low and bool(self.settings.get("behavior.enable_low_battery_reaction", True))
        self.overlay_mgr.overlay.set_low_battery(permitted_low, percent)
        self.behavior_ctrl.set_low_battery(permitted_low)
        mw = getattr(self, "main_window", None)
        if mw is not None:
            try:
                import shiboken6
                if not shiboken6.isValid(mw):
                    mw = None
            except Exception:
                pass
        if mw is not None:
            try:
                mw.update_battery_status(percent, is_charging, is_low)
            except (RuntimeError, AttributeError):
                pass

    def _on_charging_started(self, percent: int) -> None:
        """Called when AC power is connected (charging starts)."""
        if not bool(self.settings.get("behavior.enable_battery_charging_reaction", True)):
            return
        char_id = getattr(self.character_mgr.active_character, "id", "")
        if char_id == "miles_morales":
            self.overlay_mgr.overlay.show_speech_bubble("⚡ Venom Surge! Absorbing power!", 2500, "glitch")
        else:
            self.overlay_mgr.overlay.show_speech_bubble("⚡ Stark Suit: Power Connected!", 2500, "comic")

    def _on_charging_stopped(self) -> None:
        """Called when AC power is disconnected."""
        char_id = getattr(self.character_mgr.active_character, "id", "")
        if char_id == "miles_morales":
            self.overlay_mgr.overlay.show_speech_bubble("Unplugged! Venom stored and ready!", 2200, "comic")
        else:
            self.overlay_mgr.overlay.show_speech_bubble("On internal battery reserves.", 2200, "comic")

    def _on_glitch_triggered(self) -> None:
        """Trigger temporary suit glitch impulse when battery is low."""
        if self.settings.get("behavior.enable_low_battery_reaction", True):
            self.overlay_mgr.overlay.trigger_suit_glitch(450)

    def startup(self) -> None:
        """Execute Phase 1 complete startup sequence."""
        logger.info("Executing Spider-Buddy startup sequence...")

        # 1. Load active character
        active_char_id = self.settings.get("general.character", "miles_morales")
        if not self.character_mgr.set_active_character(active_char_id):
            available = self.character_mgr.available_characters
            if not available:
                raise RuntimeError("No character artwork profiles are installed.")
            self.character_mgr.set_active_character(next(iter(available)))
        # Bind explicitly when a previously selected profile emits no change signal.
        profile = self.character_mgr.active_character
        if self.animation_engine._character is not profile:
            self._on_character_changed(profile)

        # 2. Configure scale / height
        scale = float(self.settings.get("general.scale", 1.0))
        target_height = int(200 * scale)
        self._on_size_changed(target_height)

        self._on_setting_changed('general.display_fps', self.settings.get('general.display_fps', 0))
        # 3. Apply display mode and start overlay
        self.overlay_mgr.start()
        if hasattr(self.overlay_mgr, "sticky_notes_mgr") and self.overlay_mgr.sticky_notes_mgr:
            self.overlay_mgr.sticky_notes_mgr.set_enabled(bool(self.settings.get("behavior.enable_sticky_notes", True)))

        # 4. Start behavioral autonomy
        self.behavior_ctrl.start()
        self.interaction_mgr.start()
        self.sound_service.start()
        self.hotkey_service.start()
        self.eye_break_service.start()
        self.main_window.set_running(True)
        self.system_tray.set_running_state(True)
        self._on_overlay_visibility_changed(self.overlay_mgr.overlay.isVisible())

        # 5. Start Windows activity monitor and battery service
        self.activity_monitor.start()
        self.battery_service.start()
        self.system_load_service.start()
        self.audio_sync_service.start()
        self.stats_service.start()

        # 6. Show System Tray
        self.system_tray.show()

        # 7. Show Main Window by default on first launch or if not start_minimized
        start_minimized = self.settings.get("system.start_minimized", False)
        if not start_minimized:
            self.show_main_window()
        else:
            self.system_tray.showMessage(
                "Spider-Buddy",
                "Spider-Buddy is active and running in your system tray!",
                self.system_tray.icon(),
                3000
            )

        logger.info("Spider-Buddy launched successfully!")

    def _toggle_companion(self) -> None:
        if self.behavior_ctrl._is_active:
            self.stop_companion()
        else:
            self.start_companion()

    def start_companion(self) -> None:
        """Start or resume companion overlay and behavior."""
        self.overlay_mgr.start()
        self.behavior_ctrl.start()
        self.interaction_mgr.start()
        self.sound_service.start()
        self.hotkey_service.start()
        self.eye_break_service.start()
        self.system_load_service.start()
        self.audio_sync_service.start()
        self.main_window.set_running(True)
        self.system_tray.set_running_state(True)
        self._on_overlay_visibility_changed(self.overlay_mgr.overlay.isVisible())
        logger.info("Spider-Buddy companion started.")

    def stop_companion(self) -> None:
        """Pause companion overlay and behavior."""
        self.audio_sync_service.stop()
        self.system_load_service.stop()
        self.eye_break_service.stop()
        self.hotkey_service.stop()
        self.interaction_mgr.stop()
        self.sound_service.stop()
        self.overlay_mgr.stop()
        self.behavior_ctrl.stop()
        self.animation_engine.stop()
        self.main_window.set_running(False)
        self.system_tray.set_running_state(False)
        logger.info("Spider-Buddy companion stopped.")

    def _on_session_locked(self) -> None:
        """Suspend animation and rendering when Windows is locked or asleep."""
        logger.info("Session locked or sleeping: suspending rendering and animation.")
        self.overlay_mgr.session_active = False
        self.overlay_mgr._on_visibility_changed(False)

    def _on_session_unlocked(self) -> None:
        self.overlay_mgr.session_active = self.session_mgr.is_session_active
        self.overlay_mgr._on_visibility_changed(self.overlay_mgr.boundary_ctrl.is_character_visible)

    def _on_display_changed(self) -> None:
        """Handle screen topology and resolution changes safely."""
        logger.info("Handling display reconfiguration.")
        self.overlay_mgr.monitor_mgr.refresh()
        if self.overlay_mgr._display_mode == 'desktop':
            self.overlay_mgr.apply_default_position()
        elif self.overlay_mgr._running:
            self.overlay_mgr.window_tracker.refresh(force=True)

    def _on_overlay_visibility_changed(self, is_shown: bool) -> None:
        """Suspend animation engine rendering whenever overlay is hidden."""
        active = is_shown and self.session_mgr.is_session_active and self.behavior_ctrl._is_active
        self.animation_engine.set_suspended(not active)
        if active:
            self.movement_ctrl.start()
            if not self.behavior_ctrl._brain_timer.isActive():
                self.behavior_ctrl._brain_timer.start()
            self.interaction_mgr.start()
            self.sound_service.start()
        else:
            self.movement_ctrl._timer.stop()
            self.behavior_ctrl._brain_timer.stop()
            self.interaction_mgr.stop()
            self.sound_service.stop()


    def show_main_window(self) -> None:
        """Bring main window to foreground without unnecessary repainting."""
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        if not self.main_window.isVisible():
            self.main_window.show()
        if not self.main_window.isActiveWindow():
            self.main_window.raise_()
            self.main_window.activateWindow()
            self.main_window.setWindowState(
                (self.main_window.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive
            )
            try:
                import ctypes
                ctypes.windll.user32.SetForegroundWindow(int(self.main_window.winId()))
            except Exception:
                pass
        self.main_window._character_updated(self.character_mgr.active_character)

    def _on_open_sticky_notes_requested(self) -> None:
        """Open or focus dashboard and navigate to the Sticky Notes tab."""
        self.show_main_window()
        if hasattr(self.main_window, "switch_tab"):
            self.main_window.switch_tab("Sticky Notes")

    def _on_sticky_note_action(self, data: dict) -> None:
        """Forward web-originating sticky note changes to the desktop overlay manager."""
        if hasattr(self.overlay_mgr, "sticky_notes_mgr") and self.overlay_mgr.sticky_notes_mgr:
            self.overlay_mgr.sticky_notes_mgr.handle_external_sync(data)

    def _on_character_changed(self, profile) -> None:
        self.animation_engine.set_character(profile)
        self.behavior_ctrl.set_personality(profile.personality)
        self.settings.set("general.character", profile.id)
        if self.behavior_ctrl._is_active:
            current = self.state_machine.current_state
            self.behavior_ctrl._on_state_changed(current, current)
        else:
            self.animation_engine.pause()

        # Multiverse Glitch Effect on Suit / Mode Switch
        self.overlay_mgr.overlay.trigger_suit_glitch(650)
        import random
        if getattr(profile, "id", "") == "miles_morales":
            greetings = ["⚡ MULTIVERSE GLITCH!", "What's up, danger!", "Miles Morales in the house!"]
        else:
            greetings = ["⚡ MULTIVERSE GLITCH!", "Hey everyone! Peter here!", "Queens is in the house!"]
        self.overlay_mgr.overlay.show_speech_bubble(random.choice(greetings), 2200, "glitch")
        char_id = getattr(profile, "id", "")
        self.overlay_mgr.overlay.set_character_id(char_id)
        if hasattr(self, "battery_service"):
            self.overlay_mgr.set_battery_charging(
                self.battery_service.is_charging,
                self.battery_service.percent,
                char_id
            )

        logger.info(f"Loaded character into animation engine: {profile.name}")

    def _on_size_changed(self, height_px: int) -> None:
        self.overlay_mgr.overlay.set_character_height(height_px)
        self.movement_ctrl.set_size(self.overlay_mgr.overlay.width(), self.overlay_mgr.overlay.height())

    def _on_secondary_instance_launched(self) -> None:
        self.show_main_window()

    def _activity_context_reason(self, name):
        if name not in ("title_perch", "title_hang"):
            return ""
        from overlay.window_detector import WindowDetector
        import os
        windows = [w for w in WindowDetector.get_visible_windows() if w.pid != os.getpid() and w.is_visible and not w.is_minimized and w.title not in ("", "Program Manager")]
        if self.settings.get("general.display_mode") == "application":
            active = self.overlay_mgr._active_window
            windows = [active] if active and active.is_visible and not active.is_minimized else []
        return "" if windows else "Open an eligible application window first."

    def _play_activity(self, name, force: bool = True):
        try:
            state = CharacterState(name)
        except ValueError:
            return False
        if not force and not self.behavior_ctrl.activity_enabled(state):
            return False
        if not self.animation_engine.has_animation(name):
            return False
        if not self.behavior_ctrl._is_active:
            self.start_companion()
        if self.settings.get('general.hidden', False):
            self.settings.set('general.hidden', False)
            self.overlay_mgr._on_visibility_changed(True)
        self.interaction_mgr.play_activity(state, force=force)
        return True

    def _on_state_sound(self, old, new):
        if self.overlay_mgr.overlay.isVisible():
            self.sound_service.on_state_changed(old, new)

    def _on_hotkey_triggered(self, action_name: str, display_title: str, quote: str) -> None:
        """Handle global keyboard shortcut animation triggers (Win+1..0, Alt+1..0)."""
        logger.info("Executing hotkey action: %s (%s)", display_title, action_name)
        if hasattr(self.behavior_ctrl, "set_pinned") and getattr(self.behavior_ctrl, "_is_pinned", False):
            self.behavior_ctrl.set_pinned(False)
        if not self._play_activity(action_name):
            return
        if self.overlay_mgr and self.overlay_mgr.overlay and hasattr(self.overlay_mgr.overlay, "show_speech_bubble"):
            self.overlay_mgr.overlay.show_speech_bubble(quote, 2200, "action")

    def _on_ctrl_click_web_shoot(self) -> None:
        """Shoot web directly toward mouse cursor when Ctrl + Left Click is pressed globally on desktop."""
        if (
            self.settings.get("behavior.enable_web_shoot_cursor", True)
            and self.overlay_mgr
            and self.overlay_mgr.overlay
            and self.overlay_mgr.overlay.isVisible()
            and not (self.main_window and self.main_window.isActiveWindow())
        ):
            from PySide6.QtGui import QCursor
            self.interaction_mgr.shoot_web_at_cursor(QCursor.pos())

    def _on_eye_break_alert(self, title: str, message: str, alert_type: str) -> None:
        """Handle 60-min continuous typing or focus timer completion alert."""
        logger.info("Eye break alert fired: %s - %s (%s)", title, message, alert_type)
        # 1. Show corner web alert overlay with spring animation
        if hasattr(self.overlay_mgr, "corner_web_overlay"):
            self.overlay_mgr.corner_web_overlay.show_alert(title, message, 8.0)

        # 2. Spider-Man screen-tapping & hydration speech bubble
        if self.behavior_ctrl and self.behavior_ctrl._is_active:
            if not getattr(self.behavior_ctrl, "_is_pinned", False):
                self.behavior_ctrl.user_override()
                self.state_machine.transition_to(CharacterState.WAVE, force=True)

        if self.overlay_mgr and self.overlay_mgr.overlay and hasattr(self.overlay_mgr.overlay, "show_speech_bubble"):
            bubble_text = "Time to stretch, hydrate, and rest your eyes! 🥤" if alert_type == "break" else "Time for water, man! 💧"
            self.overlay_mgr.overlay.show_speech_bubble(bubble_text, 3800, "comic")

        # 3. Audio cue if enabled
        if self.sound_service and self.settings.get('behavior.sound_enabled', False):
            self.sound_service.on_state_changed(None, CharacterState.WAVE)

    def _on_setting_changed(self, key, value):
        if key == 'behavior.enable_low_battery_reaction':
            low = bool(value) and self.battery_service.is_low_battery
            self.overlay_mgr.overlay.set_low_battery(low, self.battery_service.percent)
            self.behavior_ctrl.set_low_battery(low)
        elif key == 'behavior.enable_suit_glitch' and not value:
            self.overlay_mgr.overlay._stop_glitch()
        elif key == 'general.display_fps':
            self.animation_engine.set_display_fps(value)
            self.movement_ctrl.set_display_fps(value)
        elif key == 'general.scale':
            self._on_size_changed(round(200*float(value)))
        elif key == 'general.opacity':
            self.overlay_mgr.overlay.set_character_opacity(float(value))
        elif key == 'system.run_on_startup':
            self.startup_service.set_startup_enabled(bool(value))
        elif key == 'behavior.enable_animation_hotkeys':
            self.hotkey_service.set_enabled(bool(value))
        elif key == 'behavior.hotkeys_require_modifier':
            self.hotkey_service.set_require_modifier(bool(value))
        elif key == 'behavior.wasd_movement_enabled':
            self.hotkey_service.set_wasd_enabled(bool(value))
        elif key == 'behavior.enable_battery_charging_reaction':
            is_charging = self.battery_service.is_charging if hasattr(self, 'battery_service') else False
            pct = self.battery_service.percent if hasattr(self, 'battery_service') else 100
            char_id = getattr(self.character_mgr.active_character, "id", "")
            self.overlay_mgr.set_battery_charging(is_charging if bool(value) else False, pct, char_id)
        elif key == 'behavior.focus_mode':
            self._on_heavy_load_changed(
                self.system_load_service.is_heavy_load(),
                self.system_load_service.get_cpu_percent(),
                self.system_load_service.get_ram_percent())
        elif key in ('behavior.enable_heavy_load_scene', 'behavior.enable_heavy_load_reaction'):
            if not value:
                self.overlay_mgr.set_heavy_load(False, 0.0, 0.0)
                self.behavior_ctrl.set_heavy_load(False, 0.0, 0.0)
                if hasattr(self, 'system_load_service'):
                    self.system_load_service._is_heavy_load = False
        elif key in ('behavior.enable_audio_beat_bobbing', 'behavior.enable_music_sync'):
            if not value:
                self.overlay_mgr.set_music_playing(False, 0.0)
                self.behavior_ctrl.set_music_playing(False, 0.0)
                if hasattr(self, 'audio_sync_service'):
                    self.audio_sync_service._is_music_playing = False
        elif key == 'behavior.enable_eye_break_alert':
            if not value:
                if hasattr(self.overlay_mgr, 'corner_web_overlay'):
                    self.overlay_mgr.corner_web_overlay.dismiss()
        elif key == 'behavior.enable_sticky_notes':
            if hasattr(self.overlay_mgr, 'sticky_notes_mgr'):
                self.overlay_mgr.sticky_notes_mgr.set_enabled(bool(value))

    def shutdown(self) -> None:
        """Perform orderly cleanup and termination."""
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info("Shutting down Spider-Buddy gracefully...")
        try:
            if hasattr(self, 'movement_ctrl') and self.movement_ctrl:
                self.settings.set('general.last_position', [float(self.movement_ctrl.x), float(self.movement_ctrl.y)], auto_save=False)
            self.settings.save()
        except Exception as e:
            logger.warning(f"Could not persist final settings: {e}")
        for name, method in (("session_mgr", "stop"), ("activity_monitor", "stop"),
                             ("battery_service", "stop"), ("hotkey_service", "stop"),
                             ("eye_break_service", "stop"),
                             ("system_load_service", "stop"), ("audio_sync_service", "stop"),
                             ("stats_service", "stop"),
                             ("interaction_mgr", "stop"), ("sound_service", "stop"),
                             ("overlay_mgr", "stop"), ("behavior_ctrl", "stop"),
                             ("animation_engine", "stop"), ("system_tray", "hide"),
                             ("main_window", "stop"), ("main_window", "hide"), ("instance_lock", "release")):
            component = getattr(self, name, None)
            if component is not None:
                try:
                    getattr(component, method)()
                except Exception:
                    logger.exception("Cleanup failed for %s", name)
        self.qapp.quit()
