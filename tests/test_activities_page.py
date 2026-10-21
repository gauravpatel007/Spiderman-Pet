"""Integration tests for Step 5: Activities visual library, permissions, and previews."""
import os
os.environ.setdefault('QT_QUICK_BACKEND', 'software')

import pytest
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QFontDatabase, QImage
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtTest import QTest

from core.character_manager import CharacterManager
from services.settings_service import SettingsService
from ui.main_window import MainWindow
from core.activity_policy import PHYSICAL_STATES, ACTIVITIES


@pytest.fixture
def shell(qapp, tmp_path, monkeypatch):
    settings = SettingsService(config_dir=tmp_path)
    monkeypatch.setattr('ui.main_window.get_settings', lambda: settings)
    manager = CharacterManager()
    manager.set_active_character('tom_holland')
    window = MainWindow(manager)
    window.character_changed.connect(manager.set_active_character)
    window.stop_requested.connect(lambda: window.set_running(False))
    window.start_requested.connect(lambda: window.set_running(True))
    window.show()
    QTest.qWait(60)
    yield window
    window.hide()
    window.deleteLater()
    qapp.processEvents()


def item(quick, name):
    pending = [quick.rootObject()]
    while pending:
        candidate = pending.pop()
        if candidate.objectName() == name:
            return candidate
        pending.extend(candidate.childItems())
    raise AssertionError(f"Item not found: {name}")


def test_activities_page_loads_and_displays_cards(shell, qapp):
    w = shell
    w.navigation.setCurrentRow(2)
    qapp.processEvents()
    quick = w.qml_pages[2]
    assert quick.status() == QQuickWidget.Ready, w.qml_page_errors
    assert w.qml_page_hosts[2].currentWidget() is quick

    lib = w.activity_library
    assert len(lib.rows) >= 32  # 24 activities + 8 effects
    row_ids = [r['id'] for r in lib.rows]
    assert 'walk' in row_ids
    assert 'dance' in row_ids
    assert 'music' in row_ids
    assert 'title_perch' in row_ids

    # Responsive grid adapts to size
    for width, expected_min_cols in ((720, 2), (1100, 3)):
        w.resize(width, 780)
        QTest.qWait(30)
        cols = item(quick, 'activityGallery').property('columns')
        assert cols >= expected_min_cols
        assert w.pages.currentWidget().horizontalScrollBar().maximum() == 0

    # Thumbnail provider returns valid image
    img = lib.get_thumbnail('walk')
    assert isinstance(img, QImage) and not img.isNull()
    thumb_music = lib.get_thumbnail('music')
    assert isinstance(thumb_music, QImage) and not thumb_music.isNull()


def test_activity_permission_toggle_and_sync(shell, qapp):
    w = shell
    w.navigation.setCurrentRow(2)
    qapp.processEvents()
    lib = w.activity_library

    # Disable dance
    assert lib.toggle('dance', False)
    assert not w.settings.get('animations.enabled.dance')
    assert not w._activity_checkboxes['dance'].isChecked()
    dance_row = next(r for r in lib.rows if r['id'] == 'dance')
    assert not dance_row['enabled']

    # Re-enable dance
    assert lib.toggle('dance', True)
    assert w.settings.get('animations.enabled.dance')
    assert w._activity_checkboxes['dance'].isChecked()
    dance_row = next(r for r in lib.rows if r['id'] == 'dance')
    assert dance_row['enabled']

    # Toggle effect
    assert lib.toggle('music', False)
    assert not w.settings.get('behavior.enable_audio_beat_bobbing')
    assert lib.toggle('music', True)
    assert w.settings.get('behavior.enable_audio_beat_bobbing')


def test_isolated_dashboard_preview_lifecycle(shell, qapp):
    w = shell
    w.navigation.setCurrentRow(2)
    qapp.processEvents()
    lib = w.activity_library

    initial_auto = w.settings.get('behavior.automatic_animations')
    initial_enabled = w.settings.get('animations.enabled.dance')

    # Start preview
    assert lib.preview('dance')
    assert lib.previewId == 'dance'
    assert 'Dashboard preview' in lib.message
    # Settings and persistent playback mode were NOT mutated
    assert w.settings.get('behavior.automatic_animations') == initial_auto
    assert w.settings.get('animations.enabled.dance') == initial_enabled

    # Stop preview
    lib.stopPreview()
    assert lib.previewId == ''

    # Navigating away stops active preview
    lib.preview('walk')
    assert lib.previewId == 'walk'
    w.navigation.setCurrentRow(0)
    qapp.processEvents()
    assert lib.previewId == ''


def test_desktop_playback_validation(shell, qapp):
    w = shell
    w.navigation.setCurrentRow(2)
    qapp.processEvents()
    lib = w.activity_library

    # 1. When paused/hidden, desktop playback is blocked
    w.set_running(False)
    qapp.processEvents()
    assert not lib.playDesktop('dance')
    assert 'Resume and show' in lib.message

    # Resume companion
    w.set_running(True)
    qapp.processEvents()

    # 2. When focus mode is active, non-quiet activities are blocked
    w.settings.set('behavior.focus_mode', True)
    qapp.processEvents()
    assert not lib.playDesktop('dance')
    assert 'focus mode' in lib.message.lower()

    # Quiet activity is allowed during focus mode
    requested = []
    w.activity_requested.connect(requested.append)
    assert lib.playDesktop('sit')
    assert requested == ['sit']

    # Turn off focus mode
    w.settings.set('behavior.focus_mode', False)
    qapp.processEvents()

    # 3. Disabled activity cannot be played on desktop
    lib.toggle('celebrate', False)
    qapp.processEvents()
    assert not lib.playDesktop('celebrate')
    assert 'Enable' in lib.message or 'disabled' in lib.message.lower()

    # 4. Window context validation for title_perch
    assert not lib.playDesktop('title_perch')
    assert len(lib.message) > 0


def test_playback_modes_automatic_and_repeat(shell, qapp):
    w = shell
    w.navigation.setCurrentRow(2)
    qapp.processEvents()
    lib = w.activity_library

    # Set repeat-one mode
    assert lib.setPlayback(False, 'walk')
    assert not lib.automatic
    assert lib.locked == 'walk'
    assert 'Repeating' in lib.message

    # Disabling the locked activity reconciles back to automatic playback predictably
    lib.toggle('walk', False)
    qapp.processEvents()
    assert lib.automatic
    assert 'returned to automatic' in lib.message.lower()

    # Restore walk
    lib.toggle('walk', True)
    qapp.processEvents()

    # Return to automatic explicitly
    assert lib.setPlayback(True, 'walk')
    assert lib.automatic
    assert 'Automatic playback enabled' in lib.message


def test_bulk_operations_and_physical_transitions(shell, qapp):
    w = shell
    w.navigation.setCurrentRow(2)
    qapp.processEvents()
    lib = w.activity_library

    # Disable optional activities
    lib.bulk('disable')
    qapp.processEvents()

    # Optional activities are disabled
    assert not w.settings.get('animations.enabled.walk')
    assert not w.settings.get('animations.enabled.jump')
    assert not w.settings.get('animations.enabled.dance')

    # Physical recovery transitions MUST remain enabled
    for state in PHYSICAL_STATES:
        if state in ACTIVITIES:
            assert w.settings.get(f'animations.enabled.{state}'), f"{state} should remain enabled"

    # Reset restores all activity permissions
    lib.bulk('reset')
    qapp.processEvents()
    assert w.settings.get('animations.enabled.walk')
    assert w.settings.get('animations.enabled.jump')
    assert w.settings.get('animations.enabled.dance')
    assert w.settings.get('animations.enable_window_perching')


def test_character_change_updates_availability_and_stops_preview(shell, qapp):
    w = shell
    w.navigation.setCurrentRow(2)
    qapp.processEvents()
    lib = w.activity_library

    lib.preview('walk')
    assert lib.previewId == 'walk'

    # Switch character
    w.character_mgr.set_active_character('miles_morales')
    qapp.processEvents()

    # Preview stops and resources reset
    assert lib.previewId == ''
    assert len(lib._supported) == 24
