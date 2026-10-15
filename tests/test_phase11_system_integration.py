"""Comprehensive system integration and edge case tests for Phase 11."""
import os
import sys
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication

from core.character_manager import CharacterManager
from core.state_machine import StateMachine, CharacterState
from services.settings_service import get_settings
from overlay.overlay_manager import OverlayManager
from core.movement_controller import MovementController
from ui.main_window import MainWindow


def test_character_switching_runtime(qapp):
    """Verify runtime character switching between Miles Morales and Tom Holland."""
    char_mgr = CharacterManager()
    available = char_mgr.available_characters
    assert "miles_morales" in available
    assert "tom_holland" in available

    # Switch to Miles
    assert char_mgr.set_active_character("miles_morales")
    assert char_mgr.active_character.id == "miles_morales"

    # Switch to Tom
    assert char_mgr.set_active_character("tom_holland")
    assert char_mgr.active_character.id == "tom_holland"

    # Switch back to Miles
    assert char_mgr.set_active_character("miles_morales")
    assert char_mgr.active_character.id == "miles_morales"


def test_display_mode_switching(qapp):
    """Verify switching between Desktop and Application display modes."""
    mov = MovementController()
    mgr = OverlayManager(mov)

    # Start in desktop mode
    mgr.set_display_mode("desktop")
    assert mgr._display_mode == "desktop"

    # Switch to application mode
    mgr.set_display_mode("application")
    assert mgr._display_mode == "application"

    # Switch back to desktop mode
    mgr.set_display_mode("desktop")
    assert mgr._display_mode == "desktop"

    mgr.stop()


def test_settings_persistence(qapp):
    """Verify settings modifications persist and emit notifications."""
    settings = get_settings()

    original_scale = settings.get("general.scale", 1.0)
    changed_events = []
    settings.setting_changed.connect(lambda k, v: changed_events.append((k, v)))

    # Modify setting
    settings.set("general.scale", 1.25)
    assert settings.get("general.scale") == 1.25
    assert any(k == "general.scale" and v == 1.25 for k, v in changed_events)

    # Restore original setting
    settings.set("general.scale", original_scale)
    assert settings.get("general.scale") == original_scale


def test_main_window_tabs_and_controls(qapp):
    """Verify MainWindow initializes all tabs, controls, and responds to state changes."""
    char_mgr = CharacterManager()
    win = MainWindow(char_mgr)

    # Navigation pages count
    assert win.navigation.count() >= 7
    page_names = [win.navigation.item(i).text() for i in range(win.navigation.count())]
    assert "Dashboard" in page_names
    assert "Characters" in page_names
    assert "Display Mode" in page_names
    assert "Applications" in page_names
    assert "Animations" in page_names
    assert "Behavior" in page_names
    assert "Appearance" in page_names
    assert "Settings" in page_names

    # Check status updates
    win.set_status(CharacterState.IDLE, CharacterState.WALK)
    assert "Walk" in win.status_label.text()

    win.set_running(False)
    assert "Paused" in win.status_label.text()

    win.set_running(True)
    assert "Walk" in win.status_label.text()

    win.close()
