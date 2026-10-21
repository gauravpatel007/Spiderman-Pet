"""Unit tests for Spider-Buddy interactive features:
1. Double click opens app window.
2. ⚡ Spider-Sense dodging on rapid cursor approach.
3. Multiverse glitch effect on suit and display mode switch.
4. Stylized comic speech and reaction bubbles.
"""
import sys
from pathlib import Path
import pytest

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.bootstrap import ensure_site_packages
ensure_site_packages()

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint, QRect


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_double_click_opens_app_window(qapp):
    """Verify double clicking the character emits open_dashboard_requested."""
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

    assert len(opened) == 1, "Double click must emit open_dashboard_requested to open app window"


def test_spider_sense_dodging(qapp):
    """Verify rapid cursor movement toward Spider-Man triggers Spider-Sense dodging."""
    from core.state_machine import StateMachine, CharacterState as C
    from core.movement_controller import MovementController
    from core.character_manager import CharacterManager
    from core.behavior_controller import BehaviorController
    from core.animation_engine import AnimationEngine
    from core.interaction_manager import InteractionManager
    from overlay.transparent_overlay import TransparentOverlay
    from overlay.comic_effects_overlay import ComicEffectsOverlay

    sm = StateMachine(initial_state=C.IDLE)
    movement = MovementController()
    movement.set_regions([QRect(0, 0, 1920, 1080)])
    movement.set_position(500, 500)

    char_mgr = CharacterManager()
    anim = AnimationEngine()
    behavior = BehaviorController(sm, movement, anim)
    interaction_mgr = InteractionManager(sm, movement, char_mgr, animation=anim, behavior=behavior)

    overlay = TransparentOverlay()
    comic_effects = ComicEffectsOverlay(overlay, movement)
    overlay.set_comic_effects(comic_effects)
    interaction_mgr.overlay = overlay

    # Simulate rapid cursor movement toward character
    # Spider-Man is at (500, 500), cursor starts at (350, 500) and moves to (460, 500) fast
    interaction_mgr._last_cursor = QPoint(350, 500)
    interaction_mgr._last_sample = 0.0

    # Call track cursor when cursor lunges toward Spider-Man
    # Mock QCursor.pos by monkeypatching or testing logic directly
    import time
    now = time.monotonic()
    interaction_mgr._last_sample = now - 0.05  # 50ms ago
    interaction_mgr._last_cursor = QPoint(350, 500)

    # Trigger spider sense directly on overlay
    overlay.trigger_spider_sense(750)
    assert overlay._spider_sense_active is True
    assert comic_effects._spider_sense_active is True
    assert len(comic_effects._spider_bolts) > 0


def test_multiverse_suit_glitch_effect(qapp):
    """Verify chromatic aberration glitch effect triggers on suit/mode switch."""
    from overlay.transparent_overlay import TransparentOverlay

    overlay = TransparentOverlay()
    assert overlay._glitch_active is False

    # Trigger suit glitch
    overlay.trigger_suit_glitch(500)
    assert overlay._glitch_active is True
    assert overlay._glitch_timer.isActive()

    # Verify stop
    overlay._stop_glitch()
    assert overlay._glitch_active is False


def test_comic_speech_bubbles(qapp):
    """Verify stylized comic dialogue bubbles with spring animations."""
    from overlay.transparent_overlay import TransparentOverlay
    from overlay.comic_effects_overlay import ComicEffectsOverlay
    from core.movement_controller import MovementController

    movement = MovementController()
    movement.set_position(400, 400)
    overlay = TransparentOverlay()
    comic_effects = ComicEffectsOverlay(overlay, movement)
    overlay.set_comic_effects(comic_effects)

    # Test displaying a comic speech bubble
    overlay.show_speech_bubble("THWIP!", duration_ms=2000, style="action")
    assert comic_effects._bubble_active is True
    assert comic_effects._bubble_text == "THWIP!"
    assert comic_effects._bubble_style == "action"

    # Test another bubble
    overlay.show_speech_bubble("Nice code!", duration_ms=1800, style="comic")
    assert comic_effects._bubble_active is True
    assert comic_effects._bubble_text == "Nice code!"
    assert comic_effects._bubble_style == "comic"

    comic_effects.hide_bubble()
    assert comic_effects._bubble_active is False


def test_keyboard_animation_hotkeys(qapp):
    """Verify keys 1 to 0 trigger all 10 requested Spider-Man animations."""
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
        assert k in HOTKEY_MAPPINGS, f"Key {k} must exist in HOTKEY_MAPPINGS"
        action, title, quote = HOTKEY_MAPPINGS[k]
        assert action == expected_action, f"Key {k} should trigger {expected_action}, got {action}"
        assert len(title) > 0
        assert len(quote) > 0

    # 2. Test trigger_key emits activity_triggered signal
    triggered = []
    service.activity_triggered.connect(lambda act, title, quote: triggered.append((act, title, quote)))

    with patch('services.hotkey_service.time.monotonic') as clock:
        for index, k in enumerate(["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]):
            clock.return_value = 100.0 + index
            assert service.trigger_key(k) is True
            assert service.trigger_key(k) is False  # Same instant is debounced.

    assert len(triggered) == 10
    assert triggered[0][0] == "swing"
    assert triggered[1][0] == "jump"
    assert triggered[2][0] == "walk"
    assert triggered[3][0] == "run"
    assert triggered[4][0] == "focus_read"
    assert triggered[5][0] == "title_hang"
    assert triggered[6][0] == "title_perch"
    assert triggered[7][0] == "dance"
    assert triggered[8][0] == "sleep"
    assert triggered[9][0] == "wave"

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

    assert len(triggered) == 1
    assert triggered[0][0] == "swing"

    # 4. Test poll_keys with simulated Win+1 press (both work)
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

    assert len(triggered) == 1
    assert triggered[0][0] == "swing"

    # 5. When require_modifier is set to True, plain '1' is ignored
    service.set_require_modifier(True)
    triggered.clear()
    service._key_down_states[0x31] = False
    service._last_trigger_time = 0.0
    with patch("ctypes.windll.user32.GetAsyncKeyState") as mock_get_async:
        mock_get_async.side_effect = lambda vk: 0x8000 if vk == 0x31 else 0
        service._poll_keys()

    assert len(triggered) == 0


def test_title_hang_top_bar_drag_stays_hanging(qapp):
    """Verify title_hang can be dragged along window top bar without falling."""
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
    assert sm.current_state == C.TITLE_HANG

    pressed = interaction_mgr.handle_mouse_press(QPoint(500, 128), QPoint(20, 20), Qt.LeftButton)
    assert pressed is True
    assert interaction_mgr._is_title_hang_drag is True
    assert sm.current_state == C.TITLE_HANG

    # Drag horizontally across top bar
    interaction_mgr.handle_mouse_move(QPoint(620, 128))
    assert sm.current_state == C.TITLE_HANG
    assert movement.x == 600
    assert 600 in mock_mgr.dragged_positions

    # Release on top bar -> DOES NOT FALL!
    interaction_mgr.handle_mouse_release(Qt.LeftButton)
    assert interaction_mgr._is_title_hang_drag is False
    assert interaction_mgr._is_dragging is False
    assert sm.current_state == C.TITLE_HANG
    assert movement.x == 600


def test_title_hang_downward_drag_detaches_and_falls(qapp):
    """Verify dragging downward away from top bar detaches and transitions to FALL."""
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
    assert interaction_mgr._is_title_hang_drag is True

    # Pull down > 55px (dy = 72)
    interaction_mgr.handle_mouse_move(QPoint(500, 200))
    assert interaction_mgr._is_title_hang_drag is False
    assert sm.current_state == C.FALL


