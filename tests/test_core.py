"""Unit tests for Spider-Buddy core components."""
import sys
import os
import pytest
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.bootstrap import ensure_site_packages
ensure_site_packages()

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect, QPoint

# Ensure a single QApplication instance exists for Qt tests
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_character_manager_discovers_both_characters(qapp):
    from core.character_manager import CharacterManager
    char_mgr = CharacterManager()
    
    assert "miles_morales" in char_mgr.available_characters
    assert "tom_holland" in char_mgr.available_characters
    
    miles = char_mgr.available_characters["miles_morales"]
    assert "Miles" in miles.name
    assert miles.root_path.exists()
    assert (miles.root_path / "preview.png").exists()

    tom = char_mgr.available_characters["tom_holland"]
    assert "Tom Holland" in tom.name
    assert tom.root_path.exists()
    assert (tom.root_path / "preview.png").exists()


def test_character_switching(qapp):
    from core.character_manager import CharacterManager
    char_mgr = CharacterManager()
    
    assert char_mgr.set_active_character("miles_morales") is True
    assert char_mgr.active_character.id == "miles_morales"
    
    assert char_mgr.set_active_character("tom_holland") is True
    assert char_mgr.active_character.id == "tom_holland"


def test_state_machine_transitions(qapp):
    from core.state_machine import StateMachine, CharacterState
    sm = StateMachine(initial_state=CharacterState.IDLE)
    
    assert sm.current_state == CharacterState.IDLE
    assert sm.transition_to(CharacterState.WALK) is True
    assert sm.current_state == CharacterState.WALK
    
    # Transition to DRAGGED
    assert sm.transition_to(CharacterState.DRAGGED) is True
    assert sm.current_state == CharacterState.DRAGGED


def test_settings_service():
    from services.settings_service import SettingsService
    test_dir = root_dir / "build" / "test_tmp_settings"
    test_dir.mkdir(parents=True, exist_ok=True)
    settings_file = test_dir / "settings.json"
    if settings_file.exists():
        settings_file.unlink()
    settings = SettingsService(config_dir=test_dir)
    
    # Check default values
    assert settings.get("general.character") == "miles_morales"
    assert settings.get("general.display_mode") == "desktop"
    
    # Modify value
    settings.set("general.display_mode", "application")
    assert settings.get("general.display_mode") == "application"


def test_boundary_controller_display_modes(qapp):
    from overlay.monitor_manager import MonitorManager
    from overlay.boundary_controller import BoundaryController
    
    mon_mgr = MonitorManager()
    b_ctrl = BoundaryController(mon_mgr)
    
    b_ctrl.set_mode("desktop")
    assert b_ctrl.mode == "desktop"
    assert b_ctrl.is_character_visible is True
    
    b_ctrl.set_mode("application")
    assert b_ctrl.mode == "application"
    
    # If app window is active and visible
    target_rect = QRect(100, 100, 800, 600)
    b_ctrl.update_application_bounds(target_rect, is_minimized=False, is_target_active=True)
    assert b_ctrl.is_character_visible is True
    assert b_ctrl.current_bounds == target_rect
    
    # If app window is minimized or target not active
    b_ctrl.update_application_bounds(None, is_minimized=True, is_target_active=False)
    assert b_ctrl.is_character_visible is False


def test_hit_test_manager():
    from overlay.hit_test_manager import HitTestManager
    hit = HitTestManager()
    
    char_rect = QRect(100, 100, 200, 200)
    assert hit.is_point_inside_rect(QPoint(150, 150), char_rect) is True
    assert hit.is_point_inside_rect(QPoint(50, 50), char_rect) is False


def test_animation_engine_flip(qapp):
    from core.character_manager import CharacterManager
    from core.animation_engine import AnimationEngine
    
    char_mgr = CharacterManager()
    anim = AnimationEngine()
    profile = char_mgr.available_characters["miles_morales"]
    anim.set_character(profile)
    
    # Test facing left transformation
    anim.set_facing_left(True)
    assert anim._is_facing_left is True
    
    # Test facing right transformation
    anim.set_facing_left(False)
    assert anim._is_facing_left is False

