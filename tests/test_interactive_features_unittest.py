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


if __name__ == "__main__":
    unittest.main()
