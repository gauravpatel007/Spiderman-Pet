"""Unit tests for Heavy System Load (>85% collapsing beam) and Audio & Music Synchronization."""
import sys
import os
import unittest
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.bootstrap import ensure_site_packages
ensure_site_packages()

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QPoint
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from services.system_load_service import SystemLoadService
from services.audio_sync_service import AudioSyncService
from services.settings_service import get_settings


class TestSystemLoadAndAudioSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HAS_PYSIDE6:
            cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        settings = get_settings()
        settings.set("behavior.enable_comic_bubbles", True)
        settings.set("behavior.enable_heavy_load_scene", True)
        settings.set("behavior.enable_audio_beat_bobbing", True)

    def test_system_load_service_metrics(self):
        """Test pure ctypes Windows CPU & RAM querying without external packages."""
        service = SystemLoadService()
        cpu, ram = service.sample_metrics()
        self.assertGreaterEqual(cpu, 0.0)
        self.assertLessEqual(cpu, 100.0)
        self.assertGreaterEqual(ram, 0.0)
        self.assertLessEqual(ram, 100.0)

    def test_system_load_service_simulation_and_hysteresis(self):
        """Test heavy load hysteresis and simulation mode."""
        service = SystemLoadService()
        signals_received = []
        service.heavy_load_changed.connect(lambda is_h, c, r: signals_received.append((is_h, c, r)))

        # 1. Enable simulation (>85%)
        service.simulate_heavy_load(True)
        self.assertTrue(service.is_heavy_load())
        self.assertEqual(len(signals_received), 1)
        self.assertTrue(signals_received[-1][0])
        self.assertGreaterEqual(signals_received[-1][1], 85.0)

        # 2. Disable simulation
        service.simulate_heavy_load(False)
        self.assertFalse(service.is_heavy_load())
        self.assertEqual(len(signals_received), 2)
        self.assertFalse(signals_received[-1][0])

    def test_audio_sync_service_wasapi_and_simulation(self):
        """Test WASAPI peak meter and simulation mode."""
        service = AudioSyncService()
        peak = service.sample_peak()
        self.assertGreaterEqual(peak, 0.0)
        self.assertLessEqual(peak, 1.0)

        meter_updates = []
        beat_hits = []
        music_changes = []

        service.audio_meter_updated.connect(lambda p, s: meter_updates.append((p, s)))
        service.beat_detected.connect(lambda i: beat_hits.append(i))
        service.music_state_changed.connect(lambda p, v: music_changes.append((p, v)))

        # Test simulation
        service.simulate_music(True)
        self.assertTrue(service.is_music_playing())
        self.assertGreaterEqual(len(music_changes), 1)
        self.assertTrue(music_changes[-1][0])

        # Advance a tick
        service._poll_audio()
        self.assertGreaterEqual(len(meter_updates), 1)
        self.assertGreater(meter_updates[-1][0], 0.0)

        # Turn off simulation
        service.simulate_music(False)
        self.assertFalse(service.is_music_playing())
        self.assertFalse(music_changes[-1][0])

    def test_comic_effects_collapsing_beam_and_music_notes(self):
        """Test ComicEffectsOverlay rendering and state for collapsing beam and floating notes."""
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in test environment")
        from overlay.transparent_overlay import TransparentOverlay
        from overlay.comic_effects_overlay import ComicEffectsOverlay
        from core.movement_controller import MovementController

        pet = TransparentOverlay()
        movement = MovementController()
        overlay = ComicEffectsOverlay(pet, movement)
        pet.show()  # Effects are owned by a visible companion.

        # 1. Test heavy load
        overlay.set_heavy_load(True, cpu=92.0, ram=88.0)
        self.assertTrue(overlay._heavy_load_active)
        self.assertEqual(overlay._heavy_cpu, 92.0)
        self.assertEqual(overlay._heavy_ram, 88.0)
        self.assertTrue(overlay.isVisible())

        # Advance animation tick to spawn rubble
        overlay._on_anim_frame()
        self.assertTrue(overlay.isVisible())

        # 2. Test audio music notes and beat
        overlay.set_music_playing(True, volume=0.85)
        self.assertTrue(overlay._music_active)
        overlay.trigger_beat(intensity=1.4)
        self.assertGreaterEqual(len(overlay._soundwave_rings), 2)
        self.assertGreaterEqual(len(overlay._music_notes), 1)

        # Advance frame to drift notes
        overlay._on_anim_frame()
        self.assertGreaterEqual(len(overlay._music_notes), 1)

        # Clear states
        overlay.set_heavy_load(False)
        overlay.set_music_playing(False)
        overlay._soundwave_rings.clear()
        overlay._music_notes.clear()
        overlay._rubble_particles.clear()
        overlay._on_anim_frame()
        self.assertTrue(overlay.isHidden())
        pet.close()

    def test_transparent_overlay_headphones_and_strain(self):
        """Test TransparentOverlay state for red-and-black headphones, beat-bobbing, and heavy strain."""
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in test environment")
        from overlay.transparent_overlay import TransparentOverlay

        overlay = TransparentOverlay()

        # 1. Heavy load
        overlay.set_heavy_load(True, cpu=94.0, ram=70.0)
        self.assertTrue(overlay._is_heavy_load)
        self.assertEqual(overlay._heavy_cpu, 94.0)

        # 2. Music beat-bobbing
        overlay.set_music_playing(True, volume=0.75)
        self.assertTrue(overlay._is_music_playing)
        self.assertTrue(overlay._audio_anim_timer.isActive())

        overlay.trigger_beat(intensity=1.2)
        self.assertEqual(overlay._beat_phase, 0.0)
        self.assertEqual(overlay._foot_tap_phase, 1.0)

        # Advance tick
        overlay._on_audio_anim_frame()
        self.assertGreater(overlay._beat_phase, 0.0)

        # Reset
        overlay.set_heavy_load(False)
        overlay.set_music_playing(False)
        self.assertFalse(overlay._is_heavy_load)
        self.assertFalse(overlay._is_music_playing)

    def test_behavior_controller_reactions(self):
        """Test BehaviorController reactions to heavy load and music playback."""
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in test environment")
        from core.state_machine import StateMachine, CharacterState
        from core.movement_controller import MovementController
        from core.animation_engine import AnimationEngine
        from core.behavior_controller import BehaviorController
        from overlay.transparent_overlay import TransparentOverlay
        from overlay.comic_effects_overlay import ComicEffectsOverlay

        state_machine = StateMachine(CharacterState.WALK)
        movement = MovementController()
        animation = AnimationEngine()
        behavior = BehaviorController(state_machine, movement, animation)
        overlay = TransparentOverlay()
        comic = ComicEffectsOverlay(overlay, movement)
        overlay.set_comic_effects(comic)
        behavior.overlay = overlay

        # Enter heavy load
        behavior.set_heavy_load(True, cpu=93.0, ram=86.0)
        self.assertTrue(behavior._is_heavy_load)
        self.assertFalse(behavior._brain_timer.isActive())
        self.assertTrue(comic._bubble_active)
        self.assertIn("CPU at 93%", comic._bubble_text)

        # Exit heavy load
        behavior.set_heavy_load(False)
        self.assertFalse(behavior._is_heavy_load)
        self.assertIn("Phew!", comic._bubble_text)

        # Music playing reaction
        behavior.set_music_playing(True, volume=0.8)
        self.assertTrue(behavior._is_music_playing)
        self.assertTrue(comic._bubble_active)
        self.assertTrue(any(sym in comic._bubble_text for sym in ["🎧", "🎶", "🎵"]))

    def test_main_window_and_system_tray_wiring(self):
        """Test MainWindow and SystemTray controls for system load and audio sync."""
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in test environment")
        from core.character_manager import CharacterManager
        from ui.main_window import MainWindow
        from ui.system_tray import SystemTrayIcon

        char_mgr = CharacterManager()
        char_mgr.discover_characters()
        main_win = MainWindow(char_mgr)
        tray = SystemTrayIcon(char_mgr)

        # Verify signals and widgets
        self.assertTrue(hasattr(main_win, "simulate_heavy_load_toggled"))
        self.assertTrue(hasattr(main_win, "simulate_music_toggled"))
        self.assertTrue(hasattr(main_win, "lbl_system_load"))
        self.assertTrue(hasattr(main_win, "lbl_audio_status"))

        # Update methods
        main_win.update_system_load(91.0, 89.0, is_heavy=True)
        self.assertIn("91%", main_win.lbl_system_load.text())
        self.assertIn("CRITICAL", main_win.lbl_system_load.text())

        main_win.update_music_state(is_playing=True, volume=0.7)
        self.assertIn("Active", main_win.lbl_audio_status.text())

        main_win.update_battery_status(85, is_charging=True, is_low=False)
        self.assertIn("85%", main_win.battery_status_lbl.text())

        # System tray actions
        self.assertTrue(hasattr(tray, "fx_heavy_load_act"))
        self.assertTrue(hasattr(tray, "fx_audio_sync_act"))
        self.assertTrue(tray.fx_heavy_load_act.isCheckable())
        self.assertTrue(tray.fx_audio_sync_act.isCheckable())

    def test_turn_off_heavy_load_and_audio_sync_via_settings(self):
        """Verify unchecking settings immediately dismisses heavy load and audio sync."""
        settings = get_settings()

        # Test heavy load turn off
        load_service = SystemLoadService()
        load_service.simulate_heavy_load(True)
        self.assertTrue(load_service.is_heavy_load())

        # Uncheck setting
        settings.set("behavior.enable_heavy_load_scene", False)
        self.assertFalse(load_service.is_heavy_load())

        # Test audio sync turn off
        audio_service = AudioSyncService()
        audio_service.simulate_music(True)
        self.assertTrue(audio_service.is_music_playing())

        # Uncheck setting
        settings.set("behavior.enable_audio_beat_bobbing", False)
        self.assertFalse(audio_service.is_music_playing())


if __name__ == "__main__":
    unittest.main()
