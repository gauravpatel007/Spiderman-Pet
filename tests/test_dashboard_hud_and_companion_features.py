"""Unit tests for Dashboard HUD, Spidey-Sense, Action Deck, Pomodoro, Quotes, Stats, and Mood Presets."""
import pytest
from PySide6.QtCore import Qt
from core.character_manager import CharacterManager
from services.settings_service import SettingsService
from services.companion_stats import CompanionStatsService
from ui.main_window import MainWindow, SPIDEY_QUOTES, get_battery_lore, get_spidey_sense_status


@pytest.fixture
def dashboard_app(qapp, tmp_path, monkeypatch):
    settings = SettingsService(config_dir=tmp_path)
    monkeypatch.setattr('ui.main_window.get_settings', lambda: settings)
    manager = CharacterManager()
    manager.set_active_character('tom_holland')
    window = MainWindow(manager)
    window.show()
    yield window, manager, settings
    window.hide()
    window.deleteLater()
    qapp.processEvents()


def test_spidey_quotes_and_comic_speech_bubble(dashboard_app, qapp):
    """Test Requirement 4: Comic speech bubble cycles witty Spidey quotes and emits signal."""
    win, mgr, settings = dashboard_app
    assert hasattr(win, "quote_bubble")
    assert hasattr(win, "quote_text")

    # Capture emitted speech bubble signals
    captured = []
    win.speech_bubble_requested.connect(lambda txt, dur, style: captured.append((txt, dur, style)))

    initial_quote = win.quote_text.text()
    assert any(q in initial_quote for q in SPIDEY_QUOTES)

    # Click quote bubble
    win._cycle_spidey_quote()
    qapp.processEvents()

    new_quote = win.quote_text.text()
    assert len(captured) == 1
    assert captured[0][0] in SPIDEY_QUOTES
    assert captured[0][2] == "comic"
    assert new_quote != initial_quote


def test_system_hud_battery_and_lore(dashboard_app, qapp):
    """Test Requirement 1: Live Battery HUD, animated icon, and lore text for characters."""
    win, mgr, settings = dashboard_app
    assert hasattr(win, "hud_battery_pct")
    assert hasattr(win, "hud_battery_lore")
    assert hasattr(win, "hud_battery_bar")

    # 1. Tom Holland / Stark Suit charging
    win.update_battery_status(85, is_charging=True, is_low=False)
    qapp.processEvents()
    assert "85%" in win.hud_battery_pct.text()
    assert "Charging" in win.hud_battery_pct.text()
    assert "Stark" in win.hud_battery_lore.text()
    assert win.hud_battery_bar.value() == 85

    # 2. Miles Morales bio-electricity lore
    mgr.set_active_character('miles_morales')
    win.update_battery_status(90, is_charging=True, is_low=False)
    qapp.processEvents()
    assert "Miles Bio-Electricity" in win.hud_battery_lore.text()

    # 3. Lore helper functions directly
    miles_lore = get_battery_lore("miles_morales", 100, is_charging=True, is_low=False)
    assert "Fully Charged" in miles_lore or "Venom Surge" in miles_lore
    stark_lore = get_battery_lore("tom_holland", 15, is_charging=False, is_low=True)
    assert "Emergency" in stark_lore or "Low" in stark_lore


def test_spidey_sense_monitor_alerts(dashboard_app, qapp):
    """Test Requirement 1: CPU / RAM Spidey-Sense alerts for quiet vs tingling states."""
    win, mgr, settings = dashboard_app
    assert hasattr(win, "hud_load_metrics")
    assert hasattr(win, "hud_spidey_sense")

    # 1. Quiet state (< 50%)
    win.update_system_load(25.0, 40.0, is_heavy=False)
    qapp.processEvents()
    assert "25%" in win.hud_load_metrics.text()
    assert "Quiet" in win.hud_spidey_sense.text()

    # 2. Tingling state (> 80%)
    win.update_system_load(88.0, 45.0, is_heavy=True)
    qapp.processEvents()
    assert "TINGLING" in win.hud_spidey_sense.text().upper()

    # Helper status tests
    status, col, border = get_spidey_sense_status(10, 20, False)
    assert "Quiet" in status
    status_high, col_h, _ = get_spidey_sense_status(85, 30, False)
    assert "TINGLING" in status_high.upper()


def test_action_deck_instant_triggers(dashboard_app, qapp):
    """Test Requirement 2: 1-Click Action Deck triggers instant Spider-Man tricks."""
    win, mgr, settings = dashboard_app

    actions_emitted = []
    win.activity_requested.connect(actions_emitted.append)

    # Trigger each deck action
    win._trigger_quick_action("swing")
    win._trigger_quick_action("celebrate")
    win._trigger_quick_action("title_perch")
    win._trigger_quick_action("sleep")

    assert actions_emitted == ["swing", "celebrate", "title_perch", "sleep"]


def test_pomodoro_companion_controls(dashboard_app, qapp):
    """Test Requirement 3: 25-Min Focus Mode, 5-Min Break, and Reset."""
    win, mgr, settings = dashboard_app
    assert hasattr(win, "focus_countdown_label")
    assert hasattr(win, "focus_mode_badge")

    focus_started = []
    focus_stopped = []
    activities = []
    win.focus_timer_started.connect(focus_started.append)
    win.focus_timer_stopped.connect(lambda: focus_stopped.append(True))
    win.activity_requested.connect(activities.append)

    # 1. Start 25m Focus
    win._start_pomodoro_focus(25)
    qapp.processEvents()
    assert focus_started == [25]
    assert "focus_read" in activities
    assert "Guardian" in win.focus_mode_badge.text()
    assert settings.get("behavior.focus_mode") is True

    # 2. Start 5m Break
    win._start_pomodoro_break(5)
    qapp.processEvents()
    assert focus_started == [25, 5]
    assert "wave" in activities
    assert "Break" in win.focus_mode_badge.text()

    # 3. Reset
    win._reset_pomodoro()
    qapp.processEvents()
    assert len(focus_stopped) == 1
    assert "Ready" in win.focus_mode_badge.text()


def test_companion_stats_service_and_dashboard(tmp_path, monkeypatch, qapp):
    """Test Requirement 5: Companion daily gameplay stats (distance, webs, active time)."""
    settings = SettingsService(config_dir=tmp_path)
    monkeypatch.setattr('services.companion_stats.get_settings', lambda: settings)

    stats_svc = CompanionStatsService()
    assert stats_svc.get_formatted_stats()["distance_px"] == 0.0
    assert stats_svc.get_formatted_stats()["webs_shot"] == 0

    # Accumulate movement
    stats_svc.record_movement(100, 100)
    stats_svc.record_movement(150, 100)  # +50px
    assert stats_svc.get_formatted_stats()["distance_px"] == 50.0
    assert "50 px" in stats_svc.get_formatted_stats()["distance_text"]

    # Record web swings
    stats_svc.record_web_swing()
    stats_svc.record_web_swing()
    assert stats_svc.get_formatted_stats()["webs_shot"] == 2
    assert "2 swings" in stats_svc.get_formatted_stats()["webs_text"]


def test_quick_mood_presets(dashboard_app, qapp):
    """Test Requirement 6: Quick mood presets (Camo, Hyper, Chill)."""
    win, mgr, settings = dashboard_app
    assert hasattr(win, "btn_mood_chill")
    assert hasattr(win, "btn_mood_hyper")
    assert hasattr(win, "btn_mood_camo")

    modes_emitted = []
    win.mood_preset_changed.connect(modes_emitted.append)

    win._set_mood_preset("camo")
    win._set_mood_preset("hyper")
    win._set_mood_preset("chill")

    assert modes_emitted == ["camo", "hyper", "chill"]
