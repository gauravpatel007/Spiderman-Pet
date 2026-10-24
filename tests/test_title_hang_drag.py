"""Verification test for Window Title Hang (title_hang) top bar dragging and hotkey 6."""
import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from core.state_machine import StateMachine, CharacterState as C
from services.hotkey_service import HotkeyService, HOTKEY_MAPPINGS


class MockMovement:
    def __init__(self):
        self.x = 400
        self.y = 128
        self.width = 120
        self.height = 120
        self.is_dragging = False
        self.is_grounded = False
        self.mode = "ground"
        self.web_history = []
        self.orientations = []

        class Signal:
            def __init__(self, callback=None):
                self._cbs = [callback] if callback else []
            def connect(self, cb):
                self._cbs.append(cb)
            def emit(self, *args):
                for cb in self._cbs:
                    cb(*args)

        self.web_changed = Signal(lambda s: self.web_history.append(s))
        self.orientation_changed = Signal(lambda o: self.orientations.append(o))
        self.boundary_hit = Signal()

    def set_motion(self, mode, vx=0.0, vy=0.0):
        self.mode = mode

    def set_position(self, x, y):
        self.x = x
        self.y = y

    def active_region(self):
        return None

    @property
    def regions(self):
        return []


class MockBehavior:
    def __init__(self):
        self._override_until = 0.0
        self.cursor_attention = False

    def user_override(self):
        self._override_until = 9999999999.0


class TestTitleHangDragLogic(unittest.TestCase):
    def test_hotkey_6_maps_to_title_hang(self):
        self.assertIn("6", HOTKEY_MAPPINGS)
        action_name, title, quote = HOTKEY_MAPPINGS["6"]
        self.assertEqual(action_name, "title_hang")
        self.assertIn("Title Hang", title)

        service = HotkeyService()
        emitted = []
        service.activity_triggered.connect(lambda a, t, q: emitted.append((a, t, q)))
        res = service.trigger_key("6", bypass_cooldown=True)
        self.assertTrue(res)
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0][0], "title_hang")

    def test_top_bar_drag_horizontal_stays_hanging_without_falling(self):
        sm = StateMachine(initial_state=C.IDLE)
        movement = MockMovement()
        behavior = MockBehavior()

        from core.interaction_manager import InteractionManager
        from PySide6.QtCore import QPoint, QRect, Qt

        im = InteractionManager(sm, movement, None, animation=None, behavior=behavior)

        class MockOverlayMgr:
            def __init__(self):
                self._dock_area = QRect(100, 50, 1000, 700)
                self._dock_state = "title_hang"
                self._dock_relative_x = 0.5
                self.dragged_xs = []

            def update_dock_drag_position(self, x):
                self.dragged_xs.append(x)

        mock_overlay = MockOverlayMgr()
        im.overlay_mgr = mock_overlay

        # Start in TITLE_HANG
        sm.transition_to(C.TITLE_HANG, force=True)
        self.assertEqual(sm.current_state, C.TITLE_HANG)

        # Mouse press on Spider-Man hanging from title bar
        # Global (420, 140), local offset (20, 12)
        res = im.handle_mouse_press(QPoint(420, 140), QPoint(20, 12), Qt.LeftButton)
        self.assertTrue(res)
        self.assertTrue(im._is_title_hang_drag)
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must remain in TITLE_HANG on press")

        # Drag horizontally along the top bar: X moves from 420 to 650, Y stays at 140 (dy = 0)
        im.handle_mouse_move(QPoint(650, 140))
        self.assertTrue(im._is_title_hang_drag)
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must stay in TITLE_HANG while moving horizontally")
        self.assertEqual(movement.x, 630)  # 650 - 20
        self.assertEqual(movement.orientations[-1], 180.0, "Must remain inverted (180.0)")
        self.assertIsNotNone(movement.web_history[-1], "Web line must stay active")
        self.assertIn(630, mock_overlay.dragged_xs)

        # Drag further horizontally left: X moves to 300, Y moves slightly (dy = 8, well under 55)
        im.handle_mouse_move(QPoint(300, 148))
        self.assertEqual(sm.current_state, C.TITLE_HANG)
        self.assertEqual(movement.x, 280)

        # Release mouse along the top bar
        with patch("PySide6.QtGui.QCursor.pos", return_value=QPoint(300, 148)):
            im.handle_mouse_release(Qt.LeftButton)

        self.assertFalse(im._is_title_hang_drag)
        self.assertFalse(im._is_dragging)
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must NOT fall to ground when released on top bar!")
        self.assertEqual(movement.x, 280)
        self.assertEqual(movement.orientations[-1], 180.0)

    def test_downward_drag_past_threshold_detaches_and_falls(self):
        sm = StateMachine(initial_state=C.IDLE)
        movement = MockMovement()
        behavior = MockBehavior()

        from core.interaction_manager import InteractionManager
        from PySide6.QtCore import QPoint, QRect, Qt

        im = InteractionManager(sm, movement, None, animation=None, behavior=behavior)

        class MockOverlayMgr:
            def __init__(self):
                self._dock_area = QRect(100, 50, 1000, 700)
                self._dock_state = "title_hang"
                self._dock_relative_x = 0.5
                self._dock_timer = MagicMock()

            def update_dock_drag_position(self, x):
                pass

        mock_overlay = MockOverlayMgr()
        im.overlay_mgr = mock_overlay

        sm.transition_to(C.TITLE_HANG, force=True)
        im.handle_mouse_press(QPoint(420, 140), QPoint(20, 12), Qt.LeftButton)
        self.assertTrue(im._is_title_hang_drag)

        # Drag downward: Y moves from 140 to 215 (dy = 75, which is > 55px threshold)
        im.handle_mouse_move(QPoint(420, 215))

        self.assertFalse(im._is_title_hang_drag, "Must detach from title bar")
        self.assertTrue(im._title_hang_detached)
        self.assertEqual(sm.current_state, C.FALL, "Must transition to FALL when pulled down!")
        self.assertEqual(movement.orientations[-1], 0.0, "Must reset orientation to upright (0.0)")
        self.assertIsNone(movement.web_history[-1], "Web line must be cleared")
        self.assertIsNone(mock_overlay._dock_state, "Dock state must be cleared")


    def test_drag_to_top_up_left_75_percent_activates_title_hang_key_6(self):
        sm = StateMachine(initial_state=C.IDLE)
        movement = MockMovement()
        behavior = MockBehavior()

        from core.interaction_manager import InteractionManager
        from PySide6.QtCore import QPoint, QRect, Qt

        im = InteractionManager(sm, movement, None, animation=None, behavior=behavior)

        class MockOverlayMgr:
            def __init__(self):
                self._dock_area = None
                self._dock_state = None
                self._dock_relative_x = None

            def update_dock_drag_position(self, x):
                pass

        im.overlay_mgr = MockOverlayMgr()

        # Window top bar from x=100 to 1100, width=1000, pet width=120, avail_w=880
        # Left 75% region is rel_x in [0.0, 0.75), e.g. rel_x = 0.25 -> x = 100 + 0.25 * 880 = 320
        # Place movement at top edge: y = 60 <= 85 (is_topmost is True)
        movement.x = 320
        movement.y = 60

        im._is_dragging = True
        movement.is_dragging = True

        with patch.object(movement, "active_region", return_value=QRect(100, 50, 1000, 700)):
            im.handle_mouse_release(Qt.LeftButton)

        self.assertEqual(sm.current_state, C.TITLE_HANG, "Dropping in left 75% MUST activate Key 6 (title_hang)!")
        self.assertEqual(im.overlay_mgr._dock_state, "title_hang")
        self.assertLess(im.overlay_mgr._dock_relative_x, 0.75)
        self.assertEqual(movement.orientations[-1], 180.0, "Must be inverted in title_hang")
        self.assertIsNotNone(movement.web_history[-1], "Must have web line attached")

    def test_drag_to_top_up_right_25_percent_activates_title_perch_key_7(self):
        sm = StateMachine(initial_state=C.IDLE)
        movement = MockMovement()
        behavior = MockBehavior()

        from core.interaction_manager import InteractionManager
        from PySide6.QtCore import QPoint, QRect, Qt

        im = InteractionManager(sm, movement, None, animation=None, behavior=behavior)

        class MockOverlayMgr:
            def __init__(self):
                self._dock_area = None
                self._dock_state = None
                self._dock_relative_x = None

            def update_dock_drag_position(self, x):
                pass

        im.overlay_mgr = MockOverlayMgr()

        # Window top bar from x=100 to 1100, width=1000, pet width=120, avail_w=880
        # Right 25% region is rel_x in [0.75, 1.0], e.g. rel_x = 0.85 -> x = 100 + 0.85 * 880 = 848
        movement.x = 848
        movement.y = 60

        im._is_dragging = True
        movement.is_dragging = True

        with patch.object(movement, "active_region", return_value=QRect(100, 50, 1000, 700)):
            im.handle_mouse_release(Qt.LeftButton)

        self.assertEqual(sm.current_state, C.TITLE_PERCH, "Dropping in right 25% MUST activate Key 7 (title_perch)!")
        self.assertEqual(im.overlay_mgr._dock_state, "title_perch")
        self.assertGreaterEqual(im.overlay_mgr._dock_relative_x, 0.75)
        self.assertEqual(movement.orientations[-1], 0.0, "Must be upright in title_perch")
        self.assertIsNone(movement.web_history[-1], "No web line in title_perch")

    def test_top_bar_drag_retains_activity_across_full_width(self):
        """Once at top, dragging left or right keeps the exact same activity (no switching)."""
        sm = StateMachine(initial_state=C.IDLE)
        movement = MockMovement()
        behavior = MockBehavior()

        from core.interaction_manager import InteractionManager
        from PySide6.QtCore import QPoint, QRect, Qt

        im = InteractionManager(sm, movement, None, animation=None, behavior=behavior)

        class MockOverlayMgr:
            def __init__(self):
                self._dock_area = QRect(100, 50, 1000, 700)
                self._dock_state = "title_hang"
                self._dock_relative_x = 0.5

            def update_dock_drag_position(self, x):
                pass

        mock_overlay = MockOverlayMgr()
        im.overlay_mgr = mock_overlay

        # Case 1: Start in TITLE_HANG, drag all the way into right 25% area
        sm.transition_to(C.TITLE_HANG, force=True)
        im.handle_mouse_press(QPoint(400, 100), QPoint(20, 12), Qt.LeftButton)

        # Drag right into > 75% region (x = 900)
        im.handle_mouse_move(QPoint(900, 102))
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must RETAIN title_hang even when moved into right 25%!")
        self.assertEqual(mock_overlay._dock_state, "title_hang")
        self.assertEqual(movement.orientations[-1], 180.0)

        im.handle_mouse_release(Qt.LeftButton)
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must stay in title_hang on release!")

        # Case 2: Start in TITLE_PERCH, drag all the way into left 75% area
        sm.transition_to(C.TITLE_PERCH, force=True)
        mock_overlay._dock_state = "title_perch"
        im.handle_mouse_press(QPoint(900, 100), QPoint(20, 12), Qt.LeftButton)

        # Drag left into < 75% region (x = 300)
        im.handle_mouse_move(QPoint(300, 101))
        self.assertEqual(sm.current_state, C.TITLE_PERCH, "Must RETAIN title_perch even when moved into left 75%!")
        self.assertEqual(mock_overlay._dock_state, "title_perch")
        self.assertEqual(movement.orientations[-1], 0.0)

        im.handle_mouse_release(Qt.LeftButton)
        self.assertEqual(sm.current_state, C.TITLE_PERCH, "Must stay in title_perch on release!")

    def test_behavior_controller_keeps_title_docked_without_autonomous_leaving(self):
        """Autonomous decision making must not kick Spider-Man off the title bar."""
        from core.movement_controller import MovementController
        from core.behavior_controller import BehaviorController
        from unittest.mock import MagicMock

        sm = StateMachine(initial_state=C.IDLE)
        movement = MovementController()

        anim = MagicMock()
        anim.has_animation.return_value = True
        bc = BehaviorController(sm, movement, anim)
        bc._is_active = True
        bc.position_activity = lambda name: True
        # This test exercises autonomous docking, independent of saved test settings.
        bc.settings.set("behavior.automatic_animations", True)
        bc.settings.set("behavior.focus_mode", False)

        # When in TITLE_PERCH, decide next action must NOT leave TITLE_PERCH
        sm.transition_to(C.TITLE_PERCH, force=True)
        bc._decide_next_action()
        self.assertEqual(sm.current_state, C.TITLE_PERCH, "Autonomy must keep Spider-Man in TITLE_PERCH!")

        # When in TITLE_HANG, decide next action must NOT leave TITLE_HANG
        sm.transition_to(C.TITLE_HANG, force=True)
        bc._decide_next_action()
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Autonomy must keep Spider-Man in TITLE_HANG!")

    def test_key_6_and_7_pin_state_and_prevent_autonomous_change(self):
        from core.state_machine import StateMachine, CharacterState as C
        from core.movement_controller import MovementController
        from core.behavior_controller import BehaviorController
        from core.interaction_manager import InteractionManager
        from unittest.mock import MagicMock

        sm = StateMachine(initial_state=C.IDLE)
        movement = MovementController()
        anim = MagicMock()
        anim.has_animation.return_value = True

        bc = BehaviorController(sm, movement, anim)
        bc._is_active = True
        bc.position_activity = lambda name: True
        im = InteractionManager(sm, movement, None, animation=anim, behavior=bc)

        # 1. Play Key 6 (title_hang)
        im.play_activity(C.TITLE_HANG)
        self.assertEqual(sm.current_state, C.TITLE_HANG)
        self.assertTrue(bc._is_pinned, "TITLE_HANG must pin the companion in place")
        self.assertFalse(bc._brain_timer.isActive(), "Brain timer must be stopped while in TITLE_HANG")

        # Inactivity update must NOT change activity
        bc.update_idle(999.0)
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Idle inactivity must NOT change TITLE_HANG")

        # App switch reaction must NOT change activity
        bc.on_application_entered(True)
        self.assertEqual(sm.current_state, C.TITLE_HANG, "App enter reaction must NOT change TITLE_HANG")

        # Decision tick must NOT change activity
        bc._decide_next_action()
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Decide next action must NOT change TITLE_HANG")

        # 2. Play Key 7 (title_perch)
        im.play_activity(C.TITLE_PERCH)
        self.assertEqual(sm.current_state, C.TITLE_PERCH)
        self.assertTrue(bc._is_pinned, "TITLE_PERCH must pin the companion in place")
        self.assertFalse(bc._brain_timer.isActive(), "Brain timer must be stopped while in TITLE_PERCH")

        # Inactivity update must NOT change activity
        bc.update_idle(999.0)
        self.assertEqual(sm.current_state, C.TITLE_PERCH, "Idle inactivity must NOT change TITLE_PERCH")

        # App switch reaction must NOT change activity
        bc.on_application_entered(True)
        self.assertEqual(sm.current_state, C.TITLE_PERCH, "App enter reaction must NOT change TITLE_PERCH")

        # Decision tick must NOT change activity
        bc._decide_next_action()
        self.assertEqual(sm.current_state, C.TITLE_PERCH, "Decide next action must NOT change TITLE_PERCH")

        # 3. Switching to another activity unpins cleanly
        im.play_activity(C.SWING)
        self.assertEqual(sm.current_state, C.SWING)
        self.assertFalse(bc._is_pinned, "Switching to another activity must unpin the companion")

        # 4. Dropping to ground unpins cleanly
        im.play_activity(C.TITLE_HANG)
        self.assertTrue(bc._is_pinned)
        bc.drop_to_ground()
        self.assertFalse(bc._is_pinned, "drop_to_ground must unpin the companion")
        self.assertEqual(sm.current_state, C.FALL)

    def test_pinned_title_dock_drag_left_right_retains_pose_and_never_switches(self):
        """User requirement: While pinned at top in 6th or 7th position, dragging left/right

        MUST retain that exact position and pose without changing to DRAGGED, FALL, or switching activities.
        """
        from core.state_machine import StateMachine, CharacterState as C
        from core.movement_controller import MovementController
        from core.behavior_controller import BehaviorController
        from core.interaction_manager import InteractionManager
        from PySide6.QtCore import QPoint, QRect, Qt
        from unittest.mock import MagicMock

        sm = StateMachine(initial_state=C.IDLE)
        movement = MovementController()
        anim = MagicMock()
        anim.has_animation.return_value = True

        bc = BehaviorController(sm, movement, anim)
        bc._is_active = True
        bc.position_activity = lambda name: True
        im = InteractionManager(sm, movement, None, animation=anim, behavior=bc)

        class MockOverlayMgr:
            def __init__(self):
                self._dock_area = QRect(0, 0, 1920, 1080)
                self._dock_state = None
                self._dock_relative_x = 0.5
                self._dock_timer = MagicMock()
            def update_dock_drag_position(self, x, area=None):
                pass

        mock_overlay = MockOverlayMgr()
        im.overlay_mgr = mock_overlay

        # 1. Key 6 (TITLE_HANG): pinned at top
        im.play_activity(C.TITLE_HANG)
        mock_overlay._dock_state = "title_hang"
        self.assertEqual(sm.current_state, C.TITLE_HANG)
        self.assertTrue(bc._is_pinned)

        # Click on Spider-Man to drag him left/right
        im.handle_mouse_press(QPoint(500, 50), QPoint(20, 20), Qt.LeftButton)
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must stay in TITLE_HANG on press, not change to DRAGGED/FALL!")

        # Drag all the way to the right side (where 75% boundary is)
        im.handle_mouse_move(QPoint(1600, 52))
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must stay in TITLE_HANG while dragging to the right side!")
        self.assertEqual(mock_overlay._dock_state, "title_hang")

        # Drag back all the way to the left side
        im.handle_mouse_move(QPoint(100, 51))
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must stay in TITLE_HANG while dragging to the left side!")

        # Release mouse
        im.handle_mouse_release(Qt.LeftButton)
        self.assertEqual(sm.current_state, C.TITLE_HANG, "Must stay in TITLE_HANG upon release!")
        self.assertTrue(bc._is_pinned, "Must remain securely pinned after drag release!")

        # 2. Key 7 (TITLE_PERCH): pinned at top
        im.play_activity(C.TITLE_PERCH)
        mock_overlay._dock_state = "title_perch"
        self.assertEqual(sm.current_state, C.TITLE_PERCH)
        self.assertTrue(bc._is_pinned)

        # Click on Spider-Man to drag him left/right
        im.handle_mouse_press(QPoint(1600, 50), QPoint(20, 20), Qt.LeftButton)
        self.assertEqual(sm.current_state, C.TITLE_PERCH, "Must stay in TITLE_PERCH on press, not change to DRAGGED/FALL!")

        # Drag all the way to the left side (< 75% region)
        im.handle_mouse_move(QPoint(200, 52))
        self.assertEqual(sm.current_state, C.TITLE_PERCH, "Must stay in TITLE_PERCH while dragging across to left side!")
        self.assertEqual(mock_overlay._dock_state, "title_perch")

        # Release mouse
        im.handle_mouse_release(Qt.LeftButton)
        self.assertEqual(sm.current_state, C.TITLE_PERCH, "Must stay in TITLE_PERCH upon release!")
        self.assertTrue(bc._is_pinned, "Must remain securely pinned after drag release!")


if __name__ == "__main__":
    unittest.main()

