"""Comprehensive tests for Eye-Break / Screen Tapping and Interactive Web Trampolines."""
import unittest
from unittest.mock import MagicMock, patch

try:
    from PySide6.QtCore import QPointF, QPoint, QRect, Qt
    from PySide6.QtWidgets import QApplication
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

# Ensure QApplication instance exists for GUI tests
if HAS_PYSIDE6:
    app = QApplication.instance() or QApplication([])


class TestEyeBreakService(unittest.TestCase):
    """Test continuous typing detection, threshold alerts, and focus timers."""

    def setUp(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available in sandboxed environment")
        from services.eye_break_service import EyeBreakService
        self.service = EyeBreakService()

    def test_continuous_active_accumulation_and_reset_on_break(self):
        # 1. Idle duration < 120s -> active time increases
        self.service.on_idle_tick(10.0)
        self.service._on_tick()
        self.assertEqual(self.service.get_continuous_active_seconds(), 1.0)

        self.service.on_idle_tick(5.0)
        self.service._on_tick()
        self.assertEqual(self.service.get_continuous_active_seconds(), 2.0)

        # 2. Idle duration >= 120s (user took break) -> active time resets
        self.service.on_idle_tick(150.0)
        self.service._on_tick()
        self.assertEqual(self.service.get_continuous_active_seconds(), 0.0)

    def test_continuous_typing_threshold_triggers_alert(self):
        alerts = []
        self.service.alert_triggered.connect(lambda title, msg, t: alerts.append((title, msg, t)))

        # Simulate 10 minutes threshold
        self.service.settings.set("behavior.eye_break_minutes", 10.0)
        self.service._continuous_active_seconds = 599.0
        self.service.on_idle_tick(2.0)
        self.service._on_tick()

        self.assertEqual(len(alerts), 1)
        self.assertIn("typing", alerts[0][2])
        self.assertIn("10 minutes", alerts[0][1])

    def test_focus_countdown_timer_finishes_and_alerts(self):
        alerts = []
        self.service.alert_triggered.connect(lambda title, msg, t: alerts.append((title, msg, t)))

        self.service.start_focus_timer(minutes=0.05)  # 3 seconds
        self.assertTrue(self.service.is_focus_timer_active())

        # Tick 3 times
        self.service._on_tick()
        self.service._on_tick()
        self.service._on_tick()

        self.assertFalse(self.service.is_focus_timer_active())
        self.assertEqual(len(alerts), 1)
        self.assertIn("FOCUS", alerts[0][0])
        self.assertEqual(alerts[0][2], "timer_ended")

    def test_manual_test_alert(self):
        alerts = []
        self.service.alert_triggered.connect(lambda title, msg, t: alerts.append((title, msg, t)))
        self.service.trigger_test_alert()

        self.assertEqual(len(alerts), 1)
        self.assertIn("TIME FOR WATER, MAN!", alerts[0][0])


class TestCornerWebOverlay(unittest.TestCase):
    """Test corner web graphics and dismiss lifecycle."""

    def setUp(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available")
        from overlay.corner_web_overlay import CornerWebOverlay
        self.overlay = CornerWebOverlay()

    def tearDown(self):
        if HAS_PYSIDE6:
            self.overlay.dismiss()

    def test_show_alert_and_dismiss(self):
        self.overlay.show_alert("Test Alert", "Drink water!", duration_sec=5.0)
        self.assertTrue(self.overlay._active)
        self.assertEqual(self.overlay._title, "Test Alert")

        self.overlay.dismiss()
        self.assertFalse(self.overlay._active)
        self.assertFalse(self.overlay.isVisible())


class TestTrampolineOverlayAndPhysics(unittest.TestCase):
    """Test 2D spring formula trampoline bounce and dissolve lifecycle."""

    def setUp(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available")
        from overlay.trampoline_overlay import TrampolineOverlay
        self.tramp = TrampolineOverlay()

    def tearDown(self):
        if HAS_PYSIDE6:
            self.tramp.remove()

    def test_trampoline_setup_and_dissolve(self):
        p1 = QPointF(100, 500)
        p2 = QPointF(400, 500)
        self.tramp.set_trampoline(p1, p2)

        self.assertTrue(self.tramp.is_active())
        ret_p1, ret_p2 = self.tramp.get_endpoints()
        self.assertEqual(ret_p1, p1)
        self.assertEqual(ret_p2, p2)

        # Trigger dynamic spring oscillation
        self.tramp.trigger_bounce(impact_speed=800.0)
        self.assertTrue(self.tramp._is_bouncing)
        self.assertGreater(self.tramp._bounce_amplitude, 0.0)

        # Start dissolve
        self.tramp.start_dissolve()
        self.assertTrue(self.tramp._is_dissolving)
        self.assertGreater(len(self.tramp._particles), 0)

        # Remove
        dissolved = []
        self.tramp.trampoline_dissolved.connect(lambda: dissolved.append(True))
        self.tramp.remove()
        self.assertFalse(self.tramp.is_active())
        self.assertEqual(len(dissolved), 1)

    def test_movement_controller_trampoline_spring_rebound(self):
        from core.movement_controller import MovementController

        mc = MovementController()
        mc.set_bounds(QRect(0, 0, 1920, 1080))
        mc.set_size(128, 128)

        # Set up trampoline at y=600 spanning x=200 to 600
        p1 = QPointF(200, 600)
        p2 = QPointF(600, 600)
        self.tramp.set_trampoline(p1, p2)
        mc.set_active_trampoline(self.tramp)

        # Position Spider-Man falling directly toward the trampoline
        # Feet are at y = 460 + 128 = 588, moving down at vy = 600 px/s
        mc.set_position(300.0, 460.0)
        mc.mode = 'air'
        mc.vx = 0.0
        mc.vy = 600.0

        bounces = []
        mc.trampoline_bounced.connect(lambda vx, vy: bounces.append((vx, vy)))

        # Step physics by dt = 1/30s
        mc._step(1.0 / 30.0)

        # Must have triggered a 2D spring bounce!
        self.assertEqual(len(bounces), 1, "Trampoline must bounce falling Spider-Man")
        rebound_vx, rebound_vy = bounces[0]

        # Upward spring velocity must be strongly negative
        self.assertLess(rebound_vy, -500.0, "Spring rebound must fling Spider-Man upward")
        self.assertEqual(mc.mode, 'air')
        self.assertTrue(self.tramp._is_bouncing, "Trampoline visual oscillation must be active")


class TestInteractionManagerTrampoline(unittest.TestCase):
    """Test InteractionManager spawn and Ctrl+Drag trampoline features."""

    def setUp(self):
        if not HAS_PYSIDE6:
            self.skipTest("PySide6 not available")
        from core.state_machine import StateMachine, CharacterState
        from core.movement_controller import MovementController
        from core.character_manager import CharacterManager
        from core.interaction_manager import InteractionManager

        self.sm = StateMachine(CharacterState.IDLE)
        self.mc = MovementController()
        self.cm = CharacterManager()
        self.im = InteractionManager(self.sm, self.mc, self.cm)

    def test_spawn_trampoline_below(self):
        created = []
        self.im.trampoline_created.connect(lambda p1, p2: created.append((p1, p2)))

        self.mc.set_position(400.0, 300.0)
        self.im.spawn_trampoline_below(width_px=200.0, offset_y=80.0)

        self.assertEqual(len(created), 1)
        p1, p2 = created[0]
        # Feet are at 300 + 128 = 428, trampoline at 428 + 80 = 508
        self.assertAlmostEqual(p1.y(), 508.0, delta=2.0)
        self.assertAlmostEqual(p2.y(), 508.0, delta=2.0)
        self.assertAlmostEqual(p2.x() - p1.x(), 200.0, delta=1.0)


if __name__ == "__main__":
    unittest.main()
