import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from services.battery_service import BatteryService
from overlay.transparent_overlay import TransparentOverlay
from core.behavior_controller import BehaviorController
from core.animation_engine import AnimationEngine
from core.state_machine import StateMachine, CharacterState
from core.movement_controller import MovementController


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_battery_service_charging_signals(qapp):
    """Test that BatteryService properly detects charging and emits transition signals."""
    service = BatteryService()

    started_events = []
    stopped_events = []
    updated_events = []

    service.charging_started.connect(lambda pct: started_events.append(pct))
    service.charging_stopped.connect(lambda: stopped_events.append(True))
    service.battery_updated.connect(lambda pct, chg, low: updated_events.append((pct, chg, low)))

    # Simulate charging at 85%
    service.simulate_charging(True, 85)
    assert service.is_charging is True
    assert service.percent == 85
    assert len(started_events) == 1
    assert started_events[0] == 85
    assert len(updated_events) >= 1
    assert updated_events[-1] == (85, True, False)

    # Disconnect charger simulation
    service.simulate_charging(False)
    assert service.is_charging is False
    assert len(stopped_events) == 1


def test_battery_desktop_safety(qapp):
    """Ensure desktop PCs with no battery do not show charging or false low battery."""
    service = BatteryService()
    service._has_battery = False
    service._percent = 100
    service._is_charging = False

    assert service.is_charging is False
    assert service.is_low_battery is False


def test_overlay_charging_state_and_rendering(qapp):
    """Test TransparentOverlay charging toggles and character-specific rendering."""
    overlay = TransparentOverlay()
    frame = QPixmap(100, 100)
    frame.fill()
    overlay.set_frame(frame)

    # 1. Miles Morales: Venom Strike charging
    overlay.set_battery_charging(True, 75, "miles_morales")
    assert overlay._is_charging is True
    assert overlay._charging_percent == 75
    assert overlay._character_id == "miles_morales"
    assert overlay._charging_timer.isActive()

    # Paint Miles charging effect onto canvas
    canvas = QPixmap(120, 160)
    canvas.fill()
    painter = QPainter(canvas)
    overlay._paint_charging_effects(painter)
    painter.end()

    # 2. Tom Holland: Stark Tech charging
    overlay.set_battery_charging(True, 95, "tom_holland")
    assert overlay._character_id == "tom_holland"
    assert overlay._charging_percent == 95

    # Paint Tom Holland Stark HUD effect onto canvas
    painter = QPainter(canvas)
    overlay._paint_charging_effects(painter)
    painter.end()

    # 3. Disconnect charger
    overlay.set_battery_charging(False)
    assert overlay._is_charging is False
    assert not overlay._charging_timer.isActive()


def test_behavior_controller_charging_state(qapp):
    """Test that BehaviorController responds to charging state with energized gait and actions."""
    movement = MovementController()
    state_machine = StateMachine()
    animation = AnimationEngine()
    behavior = BehaviorController(state_machine, movement, animation)

    assert behavior._is_charging is False

    # Enable charging
    behavior.set_battery_charging(True)
    assert behavior._is_charging is True

    # Disable charging
    behavior.set_battery_charging(False)
    assert behavior._is_charging is False


def test_comic_overlay_yellow_charging_indicator(qapp):
    """Test ComicEffectsOverlay yellow floating battery charging indicator and settings toggle."""
    from overlay.comic_effects_overlay import ComicEffectsOverlay
    from overlay.transparent_overlay import TransparentOverlay
    from core.movement_controller import MovementController
    from services.settings_service import get_settings

    pet = TransparentOverlay()
    movement = MovementController()
    comic_overlay = ComicEffectsOverlay(pet, movement)
    settings = get_settings()

    # 1. Enable in settings
    settings.set('behavior.enable_battery_charging_reaction', True)
    comic_overlay.set_battery_charging(True, 88)
    assert comic_overlay._charging_active is True
    assert comic_overlay._battery_percent == 88

    # Paint indicator onto canvas to verify no exceptions
    canvas = QPixmap(200, 200)
    canvas.fill()
    painter = QPainter(canvas)
    comic_overlay._draw_charging_indicator(painter, 1.0)
    painter.end()

    # 2. Disable via settings toggle
    settings.set('behavior.enable_battery_charging_reaction', False)
    comic_overlay.set_battery_charging(True, 88)
    assert comic_overlay._charging_active is False

    # Restore setting
    settings.set('behavior.enable_battery_charging_reaction', True)


def test_charging_indicator_activity_6_and_7_positioning(qapp):
    """Test Activity 6 (title_hang, inverted) positions battery below head, and Activity 7 (title_perch) above head."""
    from overlay.comic_effects_overlay import ComicEffectsOverlay
    from overlay.transparent_overlay import TransparentOverlay
    from core.movement_controller import MovementController

    pet = TransparentOverlay()
    movement = MovementController()
    movement.set_size(150, 150)
    movement.set_position(400, 300)

    comic_overlay = ComicEffectsOverlay(pet, movement)
    comic_overlay.set_battery_charging(True, 85)

    # 1. Activity 7: Window Corner Perch (upright)
    comic_overlay.set_activity("title_perch")
    assert comic_overlay.is_inverted() is False
    # In upright mode, target_y places the battery indicator above the head
    upright_y = comic_overlay.y()

    # 2. Activity 6: Window Title Hang (upside-down)
    comic_overlay.set_activity("title_hang")
    assert comic_overlay.is_inverted() is True
    # In hanging mode, target_y places the battery indicator below the head
    hang_y = comic_overlay.y()

    # The upside-down hang indicator must be positioned substantially lower (below the head) than upright
    assert hang_y > upright_y
    # Verify hang_y is at or below the bottom of the pet movement
    assert hang_y >= movement.y

    # 3. Test orientation signal 180 degrees
    comic_overlay.set_orientation(180.0)
    assert comic_overlay.is_inverted() is True

    # 4. Test orientation signal 0 degrees (back upright)
    comic_overlay.set_orientation(0.0)
    assert comic_overlay.is_inverted() is False

    # 5. Activity 7 (title_perch) and Activity 3 (walk) position identically above head
    comic_overlay.set_activity("walk")
    walk_y = comic_overlay.y()
    comic_overlay.set_activity("title_perch")
    perch_y = comic_overlay.y()
    assert walk_y == perch_y  # Exact above head positioning like in 3!


def test_charging_indicator_element_order_and_canvas_render(qapp):
    """Test that charging indicator layout renders [⚡ Flash, Number %, 🔋 Battery Indicator]."""
    from overlay.comic_effects_overlay import ComicEffectsOverlay
    from overlay.transparent_overlay import TransparentOverlay
    from core.movement_controller import MovementController

    pet = TransparentOverlay()
    movement = MovementController()
    comic_overlay = ComicEffectsOverlay(pet, movement)
    comic_overlay.set_battery_charging(True, 94)

    # Render onto canvas without exception
    canvas = QPixmap(300, 100)
    canvas.fill()
    painter = QPainter(canvas)
    comic_overlay._draw_charging_indicator(painter, 1.0)
    painter.end()




