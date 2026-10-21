"""Unit tests using Python standard library unittest."""
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
    from PySide6.QtCore import QPoint, QRect
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False


class TestInteractiveFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HAS_PYSIDE6:
            cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        if HAS_PYSIDE6:
            from services.settings_service import get_settings
            get_settings().set("behavior.enable_comic_bubbles", True)
            get_settings().set("behavior.enable_spider_sense_dodging", True)

    def test_double_click_opens_app_window(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in sandboxed path")
        from core.state_machine import StateMachine, CharacterState
        from core.movement_controller import MovementController
        from core.character_manager import CharacterManager
        from core.interaction_manager import InteractionManager
        from overlay.transparent_overlay import TransparentOverlay

        sm = StateMachine(initial_state=CharacterState.IDLE)
        movement = MovementController()
        char_mgr = CharacterManager()
        interaction_mgr = InteractionManager(sm, movement, char_mgr)
        overlay = TransparentOverlay()
        interaction_mgr.overlay = overlay

        opened = []
        interaction_mgr.open_dashboard_requested.connect(lambda: opened.append(True))
        interaction_mgr.handle_double_click()

        self.assertEqual(len(opened), 1, "Double click must emit open_dashboard_requested to open app window")

    def test_spider_sense_trigger_and_bolts(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in sandboxed path")
        from core.movement_controller import MovementController
        from overlay.transparent_overlay import TransparentOverlay
        from overlay.comic_effects_overlay import ComicEffectsOverlay

        movement = MovementController()
        overlay = TransparentOverlay()
        comic_effects = ComicEffectsOverlay(overlay, movement)
        overlay.set_comic_effects(comic_effects)

        overlay.trigger_spider_sense(750)
        self.assertTrue(overlay._spider_sense_active)
        self.assertTrue(comic_effects._spider_sense_active)
        self.assertGreater(len(comic_effects._spider_bolts), 0)

        overlay._stop_spider_sense()
        self.assertFalse(overlay._spider_sense_active)

    def test_suit_glitch_effect(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in sandboxed path")
        from overlay.transparent_overlay import TransparentOverlay

        overlay = TransparentOverlay()
        self.assertFalse(overlay._glitch_active)

        overlay.trigger_suit_glitch(500)
        self.assertTrue(overlay._glitch_active)
        self.assertTrue(overlay._glitch_timer.isActive())

        overlay._stop_glitch()
        self.assertFalse(overlay._glitch_active)

    def test_comic_speech_bubbles(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in sandboxed path")
        from core.movement_controller import MovementController
        from overlay.transparent_overlay import TransparentOverlay
        from overlay.comic_effects_overlay import ComicEffectsOverlay

        movement = MovementController()
        overlay = TransparentOverlay()
        comic_effects = ComicEffectsOverlay(overlay, movement)
        overlay.set_comic_effects(comic_effects)

        overlay.show_speech_bubble("THWIP!", duration_ms=2000, style="action")
        self.assertTrue(comic_effects._bubble_active)
        self.assertEqual(comic_effects._bubble_text, "THWIP!")
        self.assertEqual(comic_effects._bubble_style, "action")

        overlay.show_speech_bubble("Nice code!", duration_ms=1800, style="comic")
        self.assertTrue(comic_effects._bubble_active)
        self.assertEqual(comic_effects._bubble_text, "Nice code!")

        comic_effects.hide_bubble()
        self.assertFalse(comic_effects._bubble_active)

    def test_disable_spider_sense_and_comic_bubbles(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in sandboxed path")
        from services.settings_service import get_settings
        from core.movement_controller import MovementController
        from overlay.transparent_overlay import TransparentOverlay
        from overlay.comic_effects_overlay import ComicEffectsOverlay

        settings = get_settings()
        settings.set("behavior.enable_comic_bubbles", False)
        settings.set("behavior.enable_spider_sense_dodging", False)

        movement = MovementController()
        overlay = TransparentOverlay()
        comic_effects = ComicEffectsOverlay(overlay, movement)
        overlay.set_comic_effects(comic_effects)

        # Attempt to show bubble when disabled
        overlay.show_speech_bubble("Should not show", duration_ms=2000)
        self.assertFalse(comic_effects._bubble_active)

        # Attempt to trigger spider sense when disabled
        overlay.trigger_spider_sense(750)
        self.assertFalse(overlay._spider_sense_active)
        self.assertFalse(comic_effects._spider_sense_active)

        # Restore defaults
        settings.set("behavior.enable_comic_bubbles", True)
        settings.set("behavior.enable_spider_sense_dodging", True)

    def test_shift_drag_pinning_and_no_activities(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in sandboxed path")
        from unittest.mock import patch
        from core.state_machine import StateMachine, CharacterState as C
        from core.movement_controller import MovementController
        from core.character_manager import CharacterManager
        from core.behavior_controller import BehaviorController
        from core.animation_engine import AnimationEngine
        from core.interaction_manager import InteractionManager
        from PySide6.QtCore import Qt

        sm = StateMachine(initial_state=C.IDLE)
        movement = MovementController()
        movement.set_position(300, 300)
        char_mgr = CharacterManager()
        anim = AnimationEngine()
        behavior = BehaviorController(sm, movement, anim)
        interaction_mgr = InteractionManager(sm, movement, char_mgr, animation=anim, behavior=behavior)

        # 1. Simulate Shift+Drag with is_shift_pressed returning True
        with patch("core.interaction_manager.is_shift_pressed", return_value=True):
            interaction_mgr.handle_mouse_press(QPoint(300, 300), QPoint(20, 20), Qt.LeftButton)
            interaction_mgr.handle_mouse_move(QPoint(450, 450))
            interaction_mgr.handle_mouse_release(Qt.LeftButton)

        # Verify companion is pinned
        self.assertTrue(behavior._is_pinned, "Companion must be pinned after Shift-drag")
        self.assertEqual(movement.mode, "hold", "Movement mode must be 'hold'")
        self.assertEqual(movement.vx, 0.0)
        self.assertEqual(movement.vy, 0.0)
        self.assertFalse(behavior._brain_timer.isActive(), "Brain timer must be halted when pinned")

        # 2. Verify no autonomous activities run while pinned
        old_state = sm.current_state
        behavior._decide_next_action()
        self.assertEqual(sm.current_state, old_state, "No activities should run while pinned")

        # 3. Verify airborne or boundary hit do not disrupt pinned state
        behavior._on_airborne()
        self.assertEqual(sm.current_state, C.IDLE, "Airborne signal must not disrupt pinned state")
        self.assertEqual(movement.mode, "hold")

        behavior._on_boundary_hit("floor")
        self.assertEqual(sm.current_state, C.IDLE, "Boundary hit must not disrupt pinned state")

        # 4. Single click while pinned must NOT unpin companion
        interaction_mgr.handle_click()
        self.assertTrue(behavior._is_pinned, "Single click must NOT unpin companion")
        self.assertEqual(movement.mode, "hold")

        # 5. Double click opens app window but companion remains pinned
        opened = []
        interaction_mgr.open_dashboard_requested.connect(lambda: opened.append(True))
        interaction_mgr.handle_double_click()
        self.assertEqual(len(opened), 1, "Double click must request opening dashboard")
        self.assertTrue(behavior._is_pinned, "Double click must not unpin companion")

        # 6. Now simulate moving without Shift -> unpins!
        with patch("core.interaction_manager.is_shift_pressed", return_value=False):
            interaction_mgr.handle_mouse_press(QPoint(450, 450), QPoint(20, 20), Qt.LeftButton)
            self.assertFalse(behavior._is_pinned, "Moving without Shift must unpin the companion")

    def test_keyboard_animation_hotkeys_all_ten_animations(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in sandboxed path")
        from services.hotkey_service import HotkeyService, HOTKEY_MAPPINGS
        from unittest.mock import patch

        service = HotkeyService()

        # 1. Verify exact 10 animations requested
        expected = {
            "1": "swing",
            "2": "jump",
            "3": "walk",
            "4": "run",
            "5": "focus_read",
            "6": "title_hang",
            "7": "title_perch",
            "8": "dance",
            "9": "sleep",
            "0": "wave",
        }
        for k, expected_action in expected.items():
            self.assertIn(k, HOTKEY_MAPPINGS, f"Key {k} must exist in HOTKEY_MAPPINGS")
            action, title, quote = HOTKEY_MAPPINGS[k]
            self.assertEqual(action, expected_action, f"Key {k} should trigger {expected_action}, got {action}")
            self.assertGreater(len(title), 0)
            self.assertGreater(len(quote), 0)

        # 2. Test trigger_key emits activity_triggered signal
        triggered = []
        service.activity_triggered.connect(lambda act, title, quote: triggered.append((act, title, quote)))

        for k in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
            res = service.trigger_key(k, bypass_cooldown=True)
            self.assertTrue(res)

        self.assertEqual(len(triggered), 10)
        self.assertEqual(triggered[0][0], "swing")
        self.assertEqual(triggered[1][0], "jump")
        self.assertEqual(triggered[2][0], "walk")
        self.assertEqual(triggered[3][0], "run")
        self.assertEqual(triggered[4][0], "focus_read")
        self.assertEqual(triggered[5][0], "title_hang")
        self.assertEqual(triggered[6][0], "title_perch")
        self.assertEqual(triggered[7][0], "dance")
        self.assertEqual(triggered[8][0], "sleep")
        self.assertEqual(triggered[9][0], "wave")

        # 3. Test poll_keys with simulated direct '1' press (no modifier required by default!)
        triggered.clear()
        service._key_down_states[0x31] = False
        service._last_trigger_time = 0.0
        with patch("ctypes.windll.user32.GetAsyncKeyState") as mock_get_async:
            def fake_async(vk):
                if vk == 0x31:  # VK_1 (top row)
                    return 0x8000
                return 0

            mock_get_async.side_effect = fake_async
            service._poll_keys()

        self.assertEqual(len(triggered), 1, "Direct key 1 press without modifier must trigger swing")
        self.assertEqual(triggered[0][0], "swing")

        # 4. Test poll_keys with simulated Win+1 press (both ways work)
        triggered.clear()
        service._key_down_states[0x31] = False
        service._last_trigger_time = 0.0
        with patch("ctypes.windll.user32.GetAsyncKeyState") as mock_get_async:
            def fake_async(vk):
                if vk == 0x5B:  # VK_LWIN
                    return 0x8000
                if vk == 0x31:  # VK_1
                    return 0x8000
                return 0

            mock_get_async.side_effect = fake_async
            service._poll_keys()

        self.assertEqual(len(triggered), 1, "Win+1 press must trigger swing")
        self.assertEqual(triggered[0][0], "swing")

        # 5. When require_modifier is set to True, plain '1' is ignored
        service.set_require_modifier(True)
        triggered.clear()
        service._key_down_states[0x31] = False
        service._last_trigger_time = 0.0
        with patch("ctypes.windll.user32.GetAsyncKeyState") as mock_get_async:
            mock_get_async.side_effect = lambda vk: 0x8000 if vk == 0x31 else 0
            service._poll_keys()

        self.assertEqual(len(triggered), 0, "Plain key 1 should be ignored when require_modifier is True")

    def test_title_hang_horizontal_drag_stays_hanging(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in sandboxed path")
        from core.state_machine import StateMachine, CharacterState as C
        from core.movement_controller import MovementController
        from core.character_manager import CharacterManager
        from core.interaction_manager import InteractionManager
        from overlay.transparent_overlay import TransparentOverlay
        from PySide6.QtCore import Qt, QRect

        sm = StateMachine(initial_state=C.IDLE)
        movement = MovementController()
        movement.set_regions([QRect(0, 0, 1920, 1080)])
        movement.set_position(500, 128)
        char_mgr = CharacterManager()
        interaction_mgr = InteractionManager(sm, movement, char_mgr)
        overlay = TransparentOverlay()
        interaction_mgr.overlay = overlay

        class MockOverlayMgr:
            def __init__(self):
                self._dock_area = QRect(200, 100, 800, 600)
                self._dock_state = "title_hang"
                self._dock_relative_x = 0.5
                self.dragged_positions = []
            def update_dock_drag_position(self, x):
                self.dragged_positions.append(x)

        mock_mgr = MockOverlayMgr()
        interaction_mgr.overlay_mgr = mock_mgr

        sm.transition_to(C.TITLE_HANG, force=True)
        self.assertEqual(sm.current_state, C.TITLE_HANG)

        pressed = interaction_mgr.handle_mouse_press(QPoint(500, 128), QPoint(20, 20), Qt.LeftButton)
        self.assertTrue(pressed)
        self.assertTrue(interaction_mgr._is_title_hang_drag)
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must stay in TITLE_HANG when drag starts")

        # Drag horizontally along top bar (dy = 0)
        interaction_mgr.handle_mouse_move(QPoint(620, 128))
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must stay in TITLE_HANG while dragging horizontally")
        self.assertEqual(movement.x, 600)
        self.assertIn(600, mock_mgr.dragged_positions)

        # Release mouse along top bar
        interaction_mgr.handle_mouse_release(Qt.LeftButton)
        self.assertFalse(interaction_mgr._is_title_hang_drag)
        self.assertFalse(interaction_mgr._is_dragging)
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must NOT fall when released on top bar!")
        self.assertEqual(movement.x, 600)

    def test_title_hang_downward_drag_detaches_and_falls(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in sandboxed path")
        from core.state_machine import StateMachine, CharacterState as C
        from core.movement_controller import MovementController
        from core.character_manager import CharacterManager
        from core.interaction_manager import InteractionManager
        from overlay.transparent_overlay import TransparentOverlay
        from PySide6.QtCore import Qt, QRect

        sm = StateMachine(initial_state=C.IDLE)
        movement = MovementController()
        movement.set_regions([QRect(0, 0, 1920, 1080)])
        movement.set_position(500, 128)
        char_mgr = CharacterManager()
        interaction_mgr = InteractionManager(sm, movement, char_mgr)
        overlay = TransparentOverlay()
        interaction_mgr.overlay = overlay

        sm.transition_to(C.TITLE_HANG, force=True)
        interaction_mgr.handle_mouse_press(QPoint(500, 128), QPoint(20, 20), Qt.LeftButton)
        self.assertTrue(interaction_mgr._is_title_hang_drag)

        # Drag downward past threshold (dy = 72 > 55)
        interaction_mgr.handle_mouse_move(QPoint(500, 200))
        self.assertFalse(interaction_mgr._is_title_hang_drag, "Must detach when dragged downward")
        self.assertEqual(sm.current_state, C.FALL, "Must transition to FALL when dragged downward away from top bar")


if __name__ == "__main__":
    unittest.main()
