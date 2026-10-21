"""Full end-to-end startup and initialization test."""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap
import pytest

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.bootstrap import bootstrap_environment
bootstrap_environment()

from app.application import SpiderBuddyApp

@pytest.mark.parametrize("character_id", ["miles_morales", "tom_holland", "spider_2", "gwen_stacy_1"])
def test_full_application_lifecycle(character_id, monkeypatch):
    from app.lifecycle import SingleInstanceLock
    from services.settings_service import get_settings
    import uuid
    original_init = SingleInstanceLock.__init__
    def isolated_lock(self, key=None, parent=None):
        original_init(self, "SpiderBuddy_test_" + uuid.uuid4().hex, parent)
    monkeypatch.setattr(SingleInstanceLock, "__init__", isolated_lock)
    qapp = QApplication.instance()
    if qapp is None:
        qapp = QApplication(sys.argv)

    get_settings().set("general.character", character_id)
    app = SpiderBuddyApp(qapp)
    app.startup()
    profile = app.character_mgr.active_character
    assert profile.id == character_id
    assert app.animation_engine._character is profile
    expected = QPixmap(str(app.animation_engine._get_clip("idle").frames[app.animation_engine._current_frame_idx]))
    assert not expected.isNull()
    assert app.overlay_mgr.overlay._current_frame.toImage() == expected.toImage()

    # Assert character is loaded
    assert app.character_mgr.active_character is not None
    assert app.character_mgr.active_character.id in ["miles_morales", "tom_holland", "spider_2", "gwen_stacy_1"]

    # Assert overlay is active
    assert app.overlay_mgr.overlay is not None
    assert app.overlay_mgr._display_mode in ["desktop", "application"]

    # Assert behavior and animation engine are running
    assert app.animation_engine._current_animation in ["idle", "walk"]

    # Test mode switching on the fly
    app.overlay_mgr.set_display_mode("desktop")
    assert app.overlay_mgr._display_mode == "desktop"
    app.overlay_mgr.set_display_mode("application")
    assert app.overlay_mgr._display_mode == "application"

    # Test character switching on the fly
    assert app.character_mgr.set_active_character("tom_holland") is True
    assert app.character_mgr.active_character.id == "tom_holland"
    assert app.animation_engine._character.id == "tom_holland"
    assert app.character_mgr.set_active_character("miles_morales") is True
    assert app.character_mgr.active_character.id == "miles_morales"
    assert app.animation_engine._character.id == "miles_morales"

    # Session resume must not override a pending suspend or a user pause.
    get_settings().set('general.display_mode', 'desktop')
    get_settings().set('general.hidden', False)
    app.overlay_mgr.set_display_mode('desktop')
    app.session_mgr.handle_lock()
    assert not app.movement_ctrl._timer.isActive()
    assert not app.behavior_ctrl._brain_timer.isActive()
    app.session_mgr.handle_suspend()
    app.session_mgr.handle_unlock()
    assert not app.movement_ctrl._timer.isActive()
    app.session_mgr.handle_resume()
    assert app.movement_ctrl._timer.isActive()
    app.stop_companion()
    app.session_mgr.handle_lock()
    app.session_mgr.handle_unlock()
    assert not app.movement_ctrl._timer.isActive()
    assert not app.overlay_mgr.overlay.isVisible()

    # Clean shutdown
    app.shutdown()
    app.shutdown()  # Repeated quit requests must be harmless.
    assert not app.animation_engine._timer.isActive()
    assert not app.movement_ctrl._timer.isActive()
    assert not app.behavior_ctrl._brain_timer.isActive()
    assert not app.activity_monitor._timer.isActive()
    assert not app.overlay_mgr._focus_timer.isActive()
    assert app.instance_lock.server is None
    assert not app.main_window.isVisible()
    print("Full application lifecycle verified successfully!")

def test_focus_charging_navigation_and_pause_stability(qapp, qtbot, monkeypatch):
    """Exercise the recording's conditions with the real app and live renderer."""
    import uuid
    from PySide6.QtCore import QTimer
    from app.lifecycle import SingleInstanceLock
    from core.state_machine import CharacterState
    from services.settings_service import get_settings
    from test_dashboard_interactions import click, ready
    original_init = SingleInstanceLock.__init__
    monkeypatch.setattr(SingleInstanceLock, "__init__",
                        lambda self, key=None, parent=None: original_init(self, uuid.uuid4().hex, parent))
    settings = get_settings()
    settings.set("general.character", "tom_holland")
    settings.set("general.display_mode", "desktop")
    settings.set("general.hidden", False)
    settings.set("behavior.focus_mode", False)
    settings.set("animations.enabled.focus_read", True)
    app = SpiderBuddyApp(qapp)
    timer = QTimer()
    positions = []
    try:
        app.startup()
        app.main_window.show()
        app.main_window.resize(1380, 840)
        ready(app.main_window, qtbot)
        click(app.main_window, qtbot, '[data-framer-name="Focus & Breaks"]')
        qtbot.waitUntil(lambda: app.main_window._dashboard_tab == "Focus & Breaks")
        settings.set("behavior.focus_mode", True)
        app.system_load_service.simulate_heavy_load(True)
        app.overlay_mgr.set_battery_charging(True, 99, "tom_holland")
        assert app.state_machine.current_state == CharacterState.FOCUS_READ
        assert not app.overlay_mgr.overlay._is_heavy_load
        assert not app.overlay_mgr.comic_overlay._heavy_load_active
        timer.timeout.connect(lambda: positions.append((app.movement_ctrl.x, app.movement_ctrl.y)))
        timer.start(16)
        qtbot.wait(2200)  # Longer than one complete 24-frame Focus clip.
        timer.stop()
        assert len(positions) > 30
        assert len(set(positions)) == 1, set(positions)
        assert app.overlay_mgr.comic_overlay.isVisible()
        for tab in ("Home", "Settings", "Focus & Breaks"):
            click(app.main_window, qtbot, f'[data-framer-name="{tab}"]')
            qtbot.waitUntil(lambda: app.main_window._dashboard_tab == tab)
        app.stop_companion()
        assert not app.overlay_mgr.overlay.isVisible()
        app.overlay_mgr.set_battery_charging(True, 99, "tom_holland")
        assert not app.overlay_mgr.comic_overlay.isVisible()
    finally:
        timer.stop()
        app.shutdown()
        app.main_window.deleteLater()
        qapp.processEvents()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
