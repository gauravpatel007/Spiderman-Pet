"""Unit and functional tests for Phase 9: Windows Integration & Background Operation."""
import os
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from core.character_manager import CharacterManager
from core.animation_engine import AnimationEngine
from services.startup_service import StartupService
from services.session_manager import SessionManager
from services.settings_service import get_settings
from ui.system_tray import SystemTrayIcon


def test_system_tray_menu_actions(qapp):
    """Verify system tray includes all required Phase 9.1 controls."""
    char_mgr = CharacterManager()
    tray = SystemTrayIcon(char_mgr)

    menu = tray._menu
    actions = [a.text() for a in menu.actions()]

    # Verify Open Dashboard
    assert any("Open" in text for text in actions)

    # Verify Show/Hide Character
    assert any("Hide Character" in text or "Show Character" in text for text in actions)

    # Verify Pause/Resume
    assert any("Pause" in text or "Resume" in text for text in actions)

    # Verify Display Mode submenu
    assert any("Display Mode" in text for text in actions)

    # Verify Switch Character submenu
    assert any("Switch Character" in text for text in actions)

    # Verify Exit
    assert any("Exit" in text for text in actions)

    # Test toggling running state updates action text
    tray.set_running_state(False)
    assert "Resume" in tray.toggle_pause_act.text()
    tray.set_running_state(True)
    assert "Pause" in tray.toggle_pause_act.text()

    # Test toggling visibility
    settings = get_settings()
    settings.set("general.hidden", True)
    tray._update_menu_state()
    assert "Show Character" in tray.toggle_hide_act.text()
    settings.set("general.hidden", False)
    tray._update_menu_state()
    assert "Hide Character" in tray.toggle_hide_act.text()


def test_startup_service_command():
    """Verify StartupService generates a valid launch command."""
    cmd = StartupService.get_executable_command()
    assert isinstance(cmd, str)
    assert len(cmd) > 0
    assert "python" in cmd.lower() or ".exe" in cmd.lower()


def test_session_manager_lifecycle(qapp):
    """Verify SessionManager handles lock, unlock, sleep, resume, and display changes."""
    session_mgr = SessionManager()
    assert session_mgr.is_session_active
    assert not session_mgr.is_locked
    assert not session_mgr.is_suspended

    locked_events = []
    unlocked_events = []
    suspend_events = []
    resume_events = []
    display_events = []

    session_mgr.session_locked.connect(lambda: locked_events.append(True))
    session_mgr.session_unlocked.connect(lambda: unlocked_events.append(True))
    session_mgr.system_suspended.connect(lambda: suspend_events.append(True))
    session_mgr.system_resumed.connect(lambda: resume_events.append(True))
    session_mgr.display_changed.connect(lambda: display_events.append(True))

    # Test Lock
    session_mgr.handle_lock()
    assert session_mgr.is_locked
    assert not session_mgr.is_session_active
    assert len(locked_events) == 1

    # Redundant lock should not duplicate
    session_mgr.handle_lock()
    assert len(locked_events) == 1

    # Test Unlock
    session_mgr.handle_unlock()
    assert not session_mgr.is_locked
    assert session_mgr.is_session_active
    assert len(unlocked_events) == 1

    # Test Suspend
    session_mgr.handle_suspend()
    assert session_mgr.is_suspended
    assert not session_mgr.is_session_active
    assert len(suspend_events) == 1

    # Test Resume
    session_mgr.handle_resume()
    assert not session_mgr.is_suspended
    assert session_mgr.is_session_active
    assert len(resume_events) == 1

    # Test Display Change
    session_mgr.handle_display_change()
    assert len(display_events) == 1

    session_mgr.stop()


def test_animation_engine_resource_optimizations(qapp):
    """Verify resource optimizations: reduced sleeping FPS and suspension."""
    engine = AnimationEngine()
    char_mgr = CharacterManager()
    if char_mgr.active_character:
        engine.set_character(char_mgr.active_character)

    # Test reduced FPS flag
    engine.set_reduced_fps(True)
    assert engine._reduced_fps is True
    engine.set_reduced_fps(False)
    assert engine._reduced_fps is False

    # Test suspension
    engine.set_suspended(True)
    assert engine._suspended is True
    assert not engine._timer.isActive()

    engine.set_suspended(False)
    assert engine._suspended is False
