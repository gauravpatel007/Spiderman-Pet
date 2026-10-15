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
from core.character_manager import CharacterManager
from core.state_machine import StateMachine, CharacterState
from core.animation_engine import AnimationEngine
from core.movement_controller import MovementController
from core.behavior_controller import BehaviorController
from core.interaction_manager import InteractionManager
from overlay.overlay_manager import OverlayManager
from ui.main_window import MainWindow
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

        # Sync startup registry setting
        reg_enabled = self.startup_service.is_startup_enabled()
        if self.settings.get("system.run_on_startup", False) != reg_enabled:
            self.settings.set("system.run_on_startup", reg_enabled, auto_save=False)

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
        self.behavior_ctrl.overlay = self.overlay_mgr.overlay
        self.behavior_ctrl.position_activity = self.overlay_mgr.position_activity

        # 7. Initialize UI (Main Window + System Tray)
        self.main_window = MainWindow(character_mgr=self.character_mgr)
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
        self.main_window.save_position_requested.connect(self.overlay_mgr.save_custom_position)

        # Overlay mouse interactions route to InteractionManager
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

        # Interaction manager events
        self.interaction_mgr.open_dashboard_requested.connect(self.show_main_window)
        self.interaction_mgr.quit_requested.connect(self.shutdown)

        # System tray events
        self.system_tray.show_main_window_requested.connect(self.show_main_window)
        self.system_tray.toggle_companion_requested.connect(self._toggle_companion)
        self.system_tray.quit_requested.connect(self.shutdown)

        # Character switching
        self.character_mgr.character_changed.connect(self._on_character_changed)
        self.main_window.character_changed.connect(self.character_mgr.set_active_character)

        self.overlay_mgr.owner_changed.connect(self.main_window.overlay_owner_label.setText)

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
        self.battery_service.glitch_triggered.connect(self._on_glitch_triggered)
        self.main_window.test_glitch_requested.connect(self.battery_service.trigger_test_glitch)
        self.main_window.simulate_low_battery_toggled.connect(self.battery_service.simulate_low_battery)

    def _on_battery_updated(self, percent: int, is_charging: bool, is_low: bool) -> None:
        """Handle laptop battery updates and notify UI, overlay, and behavior."""
        self.overlay_mgr.overlay.set_low_battery(is_low, percent)
        self.behavior_ctrl.set_low_battery(is_low)
        self.main_window.update_battery_status(percent, is_charging, is_low)

    def _on_glitch_triggered(self) -> None:
        """Trigger temporary suit glitch impulse when battery is low."""
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

        # 4. Start behavioral autonomy
        self.behavior_ctrl.start()
        self.interaction_mgr.start()
        self.sound_service.start()
        self.main_window.set_running(True)
        self.system_tray.set_running_state(True)
        self._on_overlay_visibility_changed(self.overlay_mgr.overlay.isVisible())

        # 5. Start Windows activity monitor and battery service
        self.activity_monitor.start()
        self.battery_service.start()

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
        self.main_window.set_running(True)
        self.system_tray.set_running_state(True)
        self._on_overlay_visibility_changed(self.overlay_mgr.overlay.isVisible())
        logger.info("Spider-Buddy companion started.")

    def stop_companion(self) -> None:
        """Pause companion overlay and behavior."""
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
        """Bring main window to foreground."""
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        self.main_window.show()
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

        logger.info(f"Loaded character into animation engine: {profile.name}")

    def _on_size_changed(self, height_px: int) -> None:
        self.overlay_mgr.overlay.set_character_height(height_px)
        self.movement_ctrl.set_size(self.overlay_mgr.overlay.width(), self.overlay_mgr.overlay.height())

    def _on_secondary_instance_launched(self) -> None:
        self.show_main_window()

    def _play_activity(self, name):
        try:
            state = CharacterState(name)
        except ValueError:
            return
        if not self.behavior_ctrl._is_active:
            self.start_companion()
        if self.settings.get('general.hidden', False):
            self.settings.set('general.hidden', False)
            self.overlay_mgr._on_visibility_changed(True)
        self.interaction_mgr.play_activity(state)

    def _on_state_sound(self, old, new):
        if self.overlay_mgr.overlay.isVisible():
            self.sound_service.on_state_changed(old, new)

    def _on_setting_changed(self, key, value):
        if key == 'general.display_fps':
            self.animation_engine.set_display_fps(value)
            self.movement_ctrl.set_display_fps(value)
        elif key == 'general.scale':
            self._on_size_changed(round(200*float(value)))
        elif key == 'system.run_on_startup':
            self.startup_service.set_startup_enabled(bool(value))

    def shutdown(self) -> None:
        """Perform orderly cleanup and termination."""
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info("Shutting down Spider-Buddy gracefully...")
        for name, method in (("session_mgr", "stop"), ("activity_monitor", "stop"),
                             ("battery_service", "stop"),
                             ("interaction_mgr", "stop"), ("sound_service", "stop"),
                             ("overlay_mgr", "stop"), ("behavior_ctrl", "stop"),
                             ("animation_engine", "stop"), ("system_tray", "hide"),
                             ("main_window", "hide"), ("instance_lock", "release")):
            component = getattr(self, name, None)
            if component is not None:
                try:
                    getattr(component, method)()
                except Exception:
                    logger.exception("Cleanup failed for %s", name)
        self.qapp.quit()
