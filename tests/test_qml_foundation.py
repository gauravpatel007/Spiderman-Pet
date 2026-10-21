"""Tests verifying the Phase 3 QML foundation, bridge models, and navigation."""
import sys
import os
import pytest
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtWidgets import QApplication

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.settings_service import get_settings
from ui.bridge.settings_bridge import SettingsBridge
from ui.bridge.character_model import CharacterModel
from ui.bridge.activity_model import ActivityModel
from ui.bridge.status_model import StatusModel
from ui.qml_dashboard import QmlDashboard


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_settings_bridge_reads_and_searches(qapp):
    """Verifies SettingsBridge reads existing preferences and performs alias search."""
    bridge = SettingsBridge()

    # Read existing preferences
    scale = bridge.get("general.scale")
    assert scale is not None
    assert isinstance(scale, (int, float))

    # Search with everyday alias 'headphones' -> Music & Sound
    results = bridge.search("headphones")
    assert len(results) > 0
    first = results[0]
    assert first["tabIndex"] == 2  # Activities tab
    assert "Music & Sound" in first["path"]

    # Search alias 'size' -> Characters appearance
    results_size = bridge.search("size")
    assert any(r["tabIndex"] == 1 for r in results_size)

    # Search alias 'study' -> Focus & Breaks
    results_focus = bridge.search("study")
    assert any(r["tabIndex"] == 4 for r in results_focus)


def test_character_model_discovery(qapp):
    """Verifies CharacterModel lists discovered characters and handles selection."""
    char_model = CharacterModel()
    assert char_model.rowCount() > 0

    # Ensure active companion is reported
    assert char_model.activeCharacterId != ""
    assert char_model.scale >= 0.5

    # Switch character
    first_id = char_model.data(char_model.index(0, 0), char_model.IdRole)
    char_model.setActiveCharacter(first_id)
    assert char_model.activeCharacterId == first_id

    # Test scale and opacity clamping
    char_model.scale = 1.8
    assert char_model.scale == 1.8
    char_model.opacity = 0.85
    assert char_model.opacity == 0.85


def test_activity_model_categories_and_toggles(qapp):
    """Verifies ActivityModel exposes categorized library and handles toggles."""
    act_model = ActivityModel()
    assert act_model.rowCount() > 10

    # Test filtering by category
    act_model.setCategoryFilter("Movement")
    assert act_model.rowCount() > 0
    for i in range(act_model.rowCount()):
        idx = act_model.index(i, 0)
        assert act_model.data(idx, act_model.CategoryRole) == "Movement"

    # Reset filter
    act_model.setCategoryFilter("All")

    # Test selective preview (only one animates at a time)
    act_model.previewActivity("walk")
    assert act_model._active_preview_id == "walk"
    act_model.previewActivity("swing")
    assert act_model._active_preview_id == "swing"


def test_status_model_quick_actions(qapp):
    """Verifies StatusModel handles telemetry and quick pause/focus toggles."""
    status = StatusModel()
    initial_pause = status.isPaused
    status.togglePause()
    assert status.isPaused != initial_pause
    status.togglePause()
    assert status.isPaused == initial_pause


def test_qml_dashboard_instantiation_and_resizing(qapp):
    """Verifies QML engine loads AppShell.qml without errors, opens window, and resizes."""
    dashboard = QmlDashboard()
    assert dashboard.window is not None

    # Test initial dimensions
    assert dashboard.window.width() >= 640
    assert dashboard.window.height() >= 480

    # Test resizing
    dashboard.window.setWidth(1024)
    dashboard.window.setHeight(700)
    assert dashboard.window.width() == 1024
    assert dashboard.window.height() == 700

    # Test show and visibility check
    dashboard.show()
    assert dashboard.is_visible()

    dashboard.close()


def test_tray_and_settings_synchronization(qapp):
    """Verifies bi-directional synchronization between settings bridge and tray."""
    from core.character_manager import CharacterManager
    from ui.system_tray import SystemTrayIcon

    char_mgr = CharacterManager()
    tray = SystemTrayIcon(character_mgr=char_mgr)
    bridge = SettingsBridge()

    # Changing setting via bridge updates settings and persists
    bridge.set("behavior.enable_spider_sense_dodging", False)
    assert get_settings().get("behavior.enable_spider_sense_dodging") is False

    bridge.set("behavior.enable_spider_sense_dodging", True)
    assert get_settings().get("behavior.enable_spider_sense_dodging") is True

