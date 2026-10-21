"""Unit tests for WASD manual movement and settings persistence."""
import json
import os
import tempfile
from pathlib import Path
import pytest
from PySide6.QtCore import QPointF, QRect
from PySide6.QtWidgets import QApplication

from app.application import SpiderBuddyApp
from core.behavior_controller import BehaviorController, CharacterState
from core.movement_controller import MovementController
from core.state_machine import StateMachine
from services.hotkey_service import HotkeyService
from services.settings_service import SettingsService


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_settings_dir(tmp_path):
    user_dir = tmp_path / "SpiderBuddy"
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def test_wasd_movement_directions_and_states(qapp, temp_settings_dir):
    """Test that W moves up, A moves left, S moves down, D moves right."""
    settings = SettingsService(config_dir=temp_settings_dir)
    settings.set("behavior.wasd_movement_enabled", True)
    settings.set("behavior.movement_speed", 3.0)

    movement = MovementController()
    movement.set_bounds(QRect(0, 0, 1920, 1080))
    movement.set_position(500, 500)
    movement.is_grounded = False

    from PySide6.QtCore import Signal, QObject

    class DummyAnim(QObject):
        animation_completed = Signal(str)

        def __init__(self):
            super().__init__()
            self.facing_left = False
            self.speed_mult = 1.0
            self.resumed = False
        def set_facing_left(self, val):
            self.facing_left = val
        def set_speed_multiplier(self, val):
            self.speed_mult = val
        def resume(self):
            self.resumed = True
        def pause(self):
            pass
        def play(self, name):
            return True

        @property
        def physics_profile(self):
            return {}

    anim = DummyAnim()
    state_machine = StateMachine(initial_state=CharacterState.IDLE)
    behavior = BehaviorController(
        state_machine=state_machine,
        movement=movement,
        animation=anim
    )
    behavior.settings = settings
    behavior._is_active = True

    # 1. Test W (Up) -> vertical = -1.0, horizontal = 0.0: preserves state, moves upward
    behavior.handle_wasd(0.0, -1.0, False)
    assert movement.mode == "hold"
    assert movement.vy < 0, f"Expected upward velocity, got vy={movement.vy}"
    assert state_machine.current_state == CharacterState.IDLE
    assert behavior._is_pinned is True

    # 2. Test A (Left) -> horizontal = -1.0, vertical = 0.0
    behavior.handle_wasd(-1.0, 0.0, False)
    assert movement.is_facing_left is True
    assert anim.facing_left is True
    assert movement.vx < 0, f"Expected leftward velocity, got vx={movement.vx}"
    assert state_machine.current_state == CharacterState.IDLE

    # 3. Test D (Right) -> horizontal = 1.0, vertical = 0.0
    behavior.handle_wasd(1.0, 0.0, False)
    assert movement.is_facing_left is False
    assert anim.facing_left is False
    assert movement.vx > 0, f"Expected rightward velocity, got vx={movement.vx}"
    assert state_machine.current_state == CharacterState.IDLE

    # 4. Test S (Down) with specific state (SIT) -> preserves SIT state while moving down
    state_machine.transition_to(CharacterState.SIT, force=True)
    behavior.handle_wasd(0.0, 1.0, False)
    assert movement.mode == "hold"
    assert movement.vy > 0, f"Expected downward velocity, got vy={movement.vy}"
    assert state_machine.current_state == CharacterState.SIT

    # 5. Test Key Release (horizontal=0, vertical=0) -> statically pinned in place like Shift key
    behavior.handle_wasd(0.0, 0.0, False)
    assert movement.mode == "hold"
    assert movement.vx == 0.0
    assert movement.vy == 0.0
    assert behavior._is_pinned is True
    assert state_machine.current_state == CharacterState.SIT
    last_pos = settings.get("general.last_position")
    assert last_pos is not None
    assert len(last_pos) == 2


def test_wasd_disabled_toggle(qapp, temp_settings_dir):
    """Test that when behavior.wasd_movement_enabled is False, WASD input is ignored."""
    settings = SettingsService(config_dir=temp_settings_dir)
    settings.set("behavior.wasd_movement_enabled", False)

    movement = MovementController()
    movement.set_bounds(QRect(0, 0, 1920, 1080))
    movement.set_position(500, 500)

    from PySide6.QtCore import Signal, QObject

    class DummyAnim(QObject):
        animation_completed = Signal(str)
        def set_facing_left(self, val): pass
        def set_speed_multiplier(self, val): pass
        def resume(self): pass
        def pause(self): pass
        def play(self, name): pass

    anim = DummyAnim()
    state_machine = StateMachine(initial_state=CharacterState.IDLE)
    behavior = BehaviorController(
        state_machine=state_machine,
        movement=movement,
        animation=anim
    )
    behavior.settings = settings
    behavior._is_active = True

    # Try moving with W (Up)
    behavior.handle_wasd(0.0, -1.0, False)
    assert state_machine.current_state == CharacterState.IDLE
    assert movement.vy == 0.0


def test_hotkey_service_wasd_signal(qapp, temp_settings_dir):
    """Test HotkeyService wasd_enabled property and wasd_input signal."""
    hotkey = HotkeyService()
    hotkey.set_wasd_enabled(True)
    assert hotkey.is_wasd_enabled() is True

    received_inputs = []
    hotkey.wasd_input.connect(lambda h, v, shift: received_inputs.append((h, v, shift)))

    hotkey.wasd_input.emit(1.0, -1.0, True)
    assert len(received_inputs) == 1
    assert received_inputs[0] == (1.0, -1.0, True)

    # Disable WASD and verify emit of 0,0,False on active
    hotkey._wasd_active = True
    hotkey.set_wasd_enabled(False)
    assert hotkey.is_wasd_enabled() is False
    assert len(received_inputs) == 2
    assert received_inputs[1] == (0.0, 0.0, False)


def test_settings_persistence_across_instances(temp_settings_dir):
    """Test that settings saved to disk persist and are loaded cleanly on restart."""
    # Instance 1: write custom settings
    s1 = SettingsService(config_dir=temp_settings_dir)
    s1.set("general.character", "tom_holland")
    s1.set("general.scale", 1.25)
    s1.set("general.last_position", [450.0, 720.0])
    s1.set("behavior.wasd_movement_enabled", True)
    s1.set("system.run_on_startup", True)
    s1.save()

    # Verify settings file exists and matches on disk
    settings_file = temp_settings_dir / "settings.json"
    assert settings_file.exists()
    with open(settings_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["general"]["character"] == "tom_holland"
    assert data["general"]["scale"] == 1.25
    assert data["general"]["last_position"] == [450.0, 720.0]
    assert data["behavior"]["wasd_movement_enabled"] is True
    assert data["system"]["run_on_startup"] is True

    # Instance 2: reload from disk
    s2 = SettingsService(config_dir=temp_settings_dir)
    assert s2.get("general.character") == "tom_holland"
    assert s2.get("general.scale") == 1.25
    assert s2.get("general.last_position") == [450.0, 720.0]
    assert s2.get("behavior.wasd_movement_enabled") is True
    assert s2.get("system.run_on_startup") is True


def test_overlay_manager_restores_last_position(qapp, temp_settings_dir):
    """Test that OverlayManager.start() restores saved last_position."""
    from overlay.overlay_manager import OverlayManager

    settings = SettingsService(config_dir=temp_settings_dir)
    settings.set("general.last_position", [350.0, 600.0])
    settings.set("general.display_mode", "desktop")

    movement = MovementController()
    movement.set_bounds(QRect(0, 0, 1920, 1080))

    overlay_mgr = OverlayManager(movement=movement)
    overlay_mgr.settings = settings
    overlay_mgr.start()

    assert movement.x == 350.0
    assert movement.y == 600.0
    overlay_mgr.stop()


def test_wasd_static_pin_toggle(qapp, temp_settings_dir):
    """Test behavior.wasd_static_pin toggle controls static pinning vs falling to ground."""
    settings = SettingsService(config_dir=temp_settings_dir)
    settings.set("behavior.wasd_movement_enabled", True)
    settings.set("behavior.wasd_static_pin", False)

    movement = MovementController()
    movement.set_bounds(QRect(0, 0, 1920, 1080))
    movement.set_position(500, 500)
    movement.is_grounded = False

    from PySide6.QtCore import Signal, QObject

    class DummyAnim(QObject):
        animation_completed = Signal(str)
        def set_facing_left(self, val): pass
        def set_speed_multiplier(self, val): pass
        def resume(self): pass
        def pause(self): pass
        def play(self, name): return True
        @property
        def physics_profile(self): return {}

    anim = DummyAnim()
    state_machine = StateMachine(initial_state=CharacterState.IDLE)
    behavior = BehaviorController(state_machine=state_machine, movement=movement, animation=anim)
    behavior.settings = settings
    behavior._is_active = True

    # Move with WASD
    behavior.handle_wasd(1.0, 0.0, False)
    assert behavior._is_pinned is True

    # Key release when wasd_static_pin is False -> unpins and drops (FALL)
    behavior.handle_wasd(0.0, 0.0, False)
    assert behavior._is_pinned is False
    assert state_machine.current_state == CharacterState.FALL
    assert movement.mode == "air"


def test_spacebar_drops_to_ground(qapp, temp_settings_dir):
    """Test that drop_to_ground() unpins companion and transitions to FALL so gravity drops him."""
    settings = SettingsService(config_dir=temp_settings_dir)
    settings.set("behavior.wasd_movement_enabled", True)
    settings.set("behavior.wasd_static_pin", True)

    movement = MovementController()
    movement.set_bounds(QRect(0, 0, 1920, 1080))
    movement.set_position(500, 300)
    movement.is_grounded = False

    from PySide6.QtCore import Signal, QObject

    class DummyAnim(QObject):
        animation_completed = Signal(str)
        def set_facing_left(self, val): pass
        def set_speed_multiplier(self, val): pass
        def resume(self): pass
        def pause(self): pass
        def play(self, name): return True
        @property
        def physics_profile(self): return {}

    anim = DummyAnim()
    state_machine = StateMachine(initial_state=CharacterState.SIT)
    behavior = BehaviorController(state_machine=state_machine, movement=movement, animation=anim)
    behavior.settings = settings
    behavior._is_active = True

    # Companion stopped in air: static pinned in SIT state
    behavior.handle_wasd(0.0, 0.0, False)
    assert behavior._is_pinned is True
    assert movement.mode == "hold"

    # User presses Spacebar -> drop_to_ground()
    behavior.drop_to_ground()
    assert behavior._is_pinned is False
    assert movement.mode == "air"
    assert state_machine.current_state == CharacterState.FALL
