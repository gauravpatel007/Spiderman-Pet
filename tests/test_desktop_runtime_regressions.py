"""Regression coverage for preferences, input latency, and airborne poses."""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap, QColor

from core.behavior_controller import BehaviorController
from core.movement_controller import MovementController
from core.state_machine import StateMachine, CharacterState as C
from services.settings_service import SettingsService
from ui.web_window import WebMainWindow


@pytest.fixture
def behavior(qapp, tmp_path):
    movement = MovementController()
    movement.set_bounds(QRect(0, 0, 1000, 800))
    movement.set_position(400, 200)
    animation = MagicMock()
    animation.physics_profile = {}
    animation.play.return_value = True
    controller = BehaviorController(StateMachine(), movement, animation)
    controller.settings = SettingsService(config_dir=tmp_path)
    controller.settings.set('behavior.focus_mode', False)
    controller._is_active = True
    yield controller
    controller.stop()


@pytest.mark.parametrize('pose', [C.PERCH, C.HANG])
def test_unsupported_pose_falls_and_lands(behavior, pose):
    behavior.state_machine.transition_to(pose, force=True)
    assert behavior.state_machine.current_state == C.FALL
    for _ in range(240):
        behavior.movement._step(1 / 120)
    assert behavior.movement.is_grounded
    assert behavior.state_machine.current_state == C.LAND


def test_supported_hang_and_explicit_pin_remain_supported(behavior):
    behavior.movement.set_position(0, 0)
    behavior.state_machine.transition_to(C.HANG, force=True)
    assert behavior.movement.mode == 'hold'
    behavior.movement.set_position(400, 200)
    behavior.set_pinned(True)
    behavior.movement._step(.1)
    assert behavior.movement.y == 200
    behavior.drop_to_ground()
    assert behavior.movement.mode == 'air'


def test_focus_without_reading_does_not_suspend_gravity(behavior):
    behavior.settings.set('animations.enabled.focus_read', False)
    behavior._enter_focus()
    behavior.movement._step(.02)
    assert behavior.movement.y > 200
    assert behavior.movement.mode != 'hold'


@pytest.fixture
def dashboard(qapp, qtbot):
    win = WebMainWindow()
    win.resize(1380, 840)
    win.show()
    yield win
    win.stop()
    win.close()
    win.deleteLater()
    qapp.processEvents()


def evaluate(win, qtbot, script):
    result = []
    win.web_view.page().runJavaScript(script, result.append)
    qtbot.waitUntil(lambda: bool(result), timeout=10000)
    return result[0]


def test_settings_and_search_in_embedded_browser(dashboard, qtbot):
    win = dashboard
    qtbot.waitUntil(lambda: evaluate(win, qtbot,
        "Boolean(window.SpiderBuddy && document.getElementById('dashboard-settings-view'))"), timeout=15000)
    assert evaluate(win, qtbot, "typeof SpiderBuddy.loadAppSettings") == 'function'
    # Navigation must finish in the click dispatch, not a background task.
    assert evaluate(win, qtbot, """(() => {
        document.querySelector('[data-framer-name="Settings"]').click();
        return getComputedStyle(document.getElementById('dashboard-settings-view')).display;
    })()""") == 'flex'
    assert evaluate(win, qtbot, """(() => {
        const input = document.getElementById('spider-search-input');
        input.value = 'theme'; input.dispatchEvent(new Event('input'));
        return document.querySelectorAll('.spider-search-result-item').length;
    })()""") > 0
    # Observe actual frontend dispatches without changing Windows startup settings.
    payloads = evaluate(win, qtbot, """(() => {
        window.testActions = [];
        window.qtBridge = {handleAction: data => testActions.push(JSON.parse(data))};
        const toggle = document.getElementById('toggle-start-minimized');
        toggle.checked = false; toggle.dispatchEvent(new Event('change'));
        document.querySelector('.theme-select-btn[data-theme="light"]').click();
        return JSON.stringify(testActions);
    })()""")
    assert [p['action'] for p in json.loads(payloads)] == ['toggle_start_minimized', 'set_theme']
    assert evaluate(win, qtbot, 'document.documentElement.dataset.theme') == 'light'
    assert evaluate(win, qtbot, "getComputedStyle(document.body).backgroundColor") == 'rgb(238, 241, 247)'
    assert evaluate(win, qtbot, "getComputedStyle(document.querySelector('[data-framer-name=Home] p')).color") == 'rgb(67, 81, 106)'
    qtbot.wait(800)
    output = Path('build/runtime-review')
    output.mkdir(parents=True, exist_ok=True)
    win.grab().save(str(output / 'settings-light.png'))
    evaluate(win, qtbot, "document.querySelector('.theme-select-btn[data-theme=dark]').click()")
    qtbot.wait(800)
    win.grab().save(str(output / 'settings-dark.png'))


def test_hidden_dashboard_skips_repeated_frame_encoding(dashboard, monkeypatch):
    frame = QPixmap(32, 32)
    frame.fill(QColor('red'))
    dashboard.update_preview(frame)
    previous = dashboard._last_preview_bytes
    dashboard.hide()
    frame.fill(QColor('blue'))
    dashboard.update_preview(frame)
    assert dashboard._last_preview_bytes == previous


def test_test_sound_dispatches_backend_signal(dashboard):
    calls = []
    dashboard.test_sound_requested.connect(lambda: calls.append(True))
    dashboard._on_web_action({'action': 'play_test_sound'})
    assert calls == [True]


def test_reset_notifies_runtime_and_persists_defaults(qapp, tmp_path):
    settings = SettingsService(config_dir=tmp_path)
    settings.set('general.animation_speed', 2.0)
    changes = []
    settings.setting_changed.connect(lambda key, value: changes.append((key, value)))
    settings.reset_to_defaults()
    assert ('general.animation_speed', 1.0) in changes
    assert SettingsService(config_dir=tmp_path).get('general.animation_speed') == 1.0


def test_suit_glitch_toggle_does_not_disable_battery_reactions(dashboard):
    dashboard.settings.set('behavior.enable_low_battery_reaction', True)
    dashboard._on_web_action({'action': 'toggle_suit_glitch', 'enabled': False})
    assert dashboard._get_app_settings()['enable_suit_glitch'] is False
    assert dashboard.settings.get('behavior.enable_low_battery_reaction') is True


def test_title_activity_requires_a_real_visible_window(behavior, monkeypatch):
    from types import SimpleNamespace
    from overlay.overlay_manager import OverlayManager
    from overlay.window_detector import WindowDetector
    monkeypatch.setattr(WindowDetector, 'get_foreground_window', lambda: None)
    monkeypatch.setattr(WindowDetector, 'get_visible_windows', lambda: [])
    manager = SimpleNamespace(_display_mode='desktop', movement=behavior.movement)
    assert OverlayManager.position_activity(manager, 'title_hang') is False


def test_audio_preview_plays_at_configured_volume(qapp, tmp_path):
    from services.sound_service import SoundService
    sound = SoundService()
    sound.settings = SettingsService(config_dir=tmp_path)
    sound.settings.set('behavior.sound_volume', .4)
    effect = MagicMock()
    sound.effects['reaction'] = effect
    sound.play_test_sound()
    effect.setVolume.assert_called_with(.4)
    effect.play.assert_called_once()


def test_dashboard_typing_does_not_trigger_global_pet_controls(qapp, monkeypatch):
    from services.hotkey_service import HotkeyService
    service = HotkeyService()
    service.input_blocked = lambda: True
    service._wasd_active = True
    movements = []
    service.wasd_input.connect(lambda h, v, shift: movements.append((h, v, shift)))
    keys = MagicMock(side_effect=AssertionError('Blocked input must not poll global keys'))
    monkeypatch.setattr('services.hotkey_service.ctypes.windll.user32.GetAsyncKeyState', keys)
    service._poll_keys()
    service._poll_keys()
    assert movements == [(0.0, 0.0, False)]
    keys.assert_not_called()


def test_movement_stats_publish_once_per_tick_without_losing_distance(qapp):
    from services.companion_stats import CompanionStatsService
    stats = CompanionStatsService()
    stats.reset_stats()
    emitted = []
    stats.stats_updated.connect(emitted.append)
    for x in range(241):
        stats.record_movement(x, 0)
    assert stats.get_formatted_stats()['distance_px'] == 240
    assert emitted == []
    stats._on_second_tick()
    assert len(emitted) == 1 and emitted[0]['distance_px'] == 240


def test_missing_windows_product_metadata_does_not_break_app_list():
    from types import SimpleNamespace
    from overlay.window_detector import WindowDetector
    window = SimpleNamespace(process_name='example.exe', executable_path=None, application_name=None)
    assert WindowDetector.matches(window, 'example')
    assert not WindowDetector.matches(window, 'other')


def test_non_home_tab_skips_thumbnail_encoding(dashboard):
    frame = QPixmap(1000, 1000)
    frame.fill(QColor('red'))
    dashboard.update_preview(frame)
    decoded = QPixmap()
    decoded.loadFromData(dashboard._last_preview_bytes)
    assert decoded.width() <= 350 and decoded.height() <= 330
    previous = dashboard._last_preview_bytes
    dashboard._on_web_action({'action': 'dashboard_tab', 'tab': 'Settings'})
    dashboard._last_preview_at = 0
    frame.fill(QColor('blue'))
    dashboard.update_preview(frame)
    assert dashboard._last_preview_bytes == previous
