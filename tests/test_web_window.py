"""Unit tests for WebMainWindow and WebServer backend integration."""
import json
import urllib.request
import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import QApplication

from ui.web_server import WebServer
from ui.web_window import WebMainWindow
from core.character_manager import CharacterManager
from services.settings_service import get_settings


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def web_win(qapp):
    char_mgr = CharacterManager()
    win = WebMainWindow(character_mgr=char_mgr)
    win.web_view.stop()
    yield win
    win.stop()
    win.close()
    win.deleteLater()
    qapp.processEvents()


def test_web_server_endpoints(web_win):
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"

    # 1. GET /api/status
    with urllib.request.urlopen(f"{base_url}/api/status") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "is_running" in data
        assert "status" in data
        assert "character" in data

    # 2. GET /api/character_preview
    with urllib.request.urlopen(f"{base_url}/api/character_preview") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/png"
        img_bytes = resp.read()
        assert len(img_bytes) > 0

    # 3. GET /api/characters
    with urllib.request.urlopen(f"{base_url}/api/characters") as resp:
        assert resp.status == 200
        chars = json.loads(resp.read().decode("utf-8"))
        assert isinstance(chars, list)
        assert len(chars) > 0


def test_web_actions_dispatch_qt_signals(web_win, qtbot):
    port = web_win.web_port
    url = f"http://127.0.0.1:{port}/api/action"

    # 1. Test play_activity -> activity_requested signal
    with qtbot.waitSignal(web_win.activity_requested, timeout=2000) as blocker:
        req = urllib.request.Request(
            url,
            data=json.dumps({"action": "play_activity", "activity": "swing"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
    assert blocker.args == ["swing"]

    # 2. Test pause -> stop_requested signal
    with qtbot.waitSignal(web_win.stop_requested, timeout=2000):
        req = urllib.request.Request(
            url,
            data=json.dumps({"action": "pause"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
    assert web_win._is_running is False

    # 3. Test resume -> start_requested signal
    with qtbot.waitSignal(web_win.start_requested, timeout=2000):
        req = urllib.request.Request(
            url,
            data=json.dumps({"action": "resume"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
    assert web_win._is_running is True

    # 4. Test start_focus -> focus_timer_started signal
    with qtbot.waitSignal(web_win.focus_timer_started, timeout=2000) as blocker:
        req = urllib.request.Request(
            url,
            data=json.dumps({"action": "start_focus", "minutes": 25}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
    assert blocker.args == [25.0]

    # 5. Test stop_focus -> focus_timer_stopped signal
    with qtbot.waitSignal(web_win.focus_timer_stopped, timeout=2000):
        req = urllib.request.Request(
            url,
            data=json.dumps({"action": "stop_focus"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200

    # 6. Test mood preset -> mood_preset_changed signal
    with qtbot.waitSignal(web_win.mood_preset_changed, timeout=2000) as blocker:
        req = urllib.request.Request(
            url,
            data=json.dumps({"action": "mood", "mood": "chill"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
    assert blocker.args == ["chill"]

    # 7. Test hide toggle
    init_hidden = web_win.settings.get("general.hidden", False)
    req = urllib.request.Request(
        url,
        data=json.dumps({"action": "hide"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("general.hidden") == (not init_hidden)


def test_update_preview_and_status(web_win):
    # Test pixmap update
    pm = QPixmap(64, 64)
    pm.fill(QColor("red"))
    web_win.update_preview(pm)
    assert web_win._last_preview_bytes is not None
    assert len(web_win._last_preview_bytes) > 0

    # Test status update
    web_win.set_status("old", "swing")
    assert web_win._status_text == "Swing"

    # Test eye break status update with 3 args
    web_win.update_eye_break_status(120.0, 1400.0, True)


def test_activities_endpoints(web_win):
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"

    # 1. GET /api/activities
    with urllib.request.urlopen(f"{base_url}/api/activities") as resp:
        assert resp.status == 200
        acts = json.loads(resp.read().decode("utf-8"))
        assert isinstance(acts, list)
        assert len(acts) > 0
        act_ids = {a["id"] for a in acts}
        assert "idle" in act_ids
        assert "swing" in act_ids
        assert "dance" in act_ids
        assert "music" in act_ids
        # Verify structure
        item = next(a for a in acts if a["id"] == "swing")
        assert "label" in item
        assert "category" in item
        assert "description" in item
        assert "enabled" in item
        assert "supported" in item
        assert "icon_url" in item

    # 2. GET /api/timing_settings
    with urllib.request.urlopen(f"{base_url}/api/timing_settings") as resp:
        assert resp.status == 200
        timing = json.loads(resp.read().decode("utf-8"))
        assert "special_cooldown" in timing
        assert "idle_timeout" in timing
        assert "sleep_after" in timing
        assert "automatic" in timing

    # 3. GET /api/activity_icon
    with urllib.request.urlopen(f"{base_url}/api/activity_icon/swing.png") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/png"
        icon_bytes = resp.read()
        assert len(icon_bytes) > 0


def test_activities_and_character_actions(web_win, qtbot):
    qtbot.wait(600)  # Wait for initial Chromium page load & singleShot sync to settle
    port = web_win.web_port
    url = f"http://127.0.0.1:{port}/api/action"

    # 1. Toggle activity
    req = urllib.request.Request(
        url,
        data=json.dumps({"action": "toggle_activity", "activity": "wave", "enabled": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("animations.enabled.wave") is False

    # 2. Bulk activities - enable
    req = urllib.request.Request(
        url,
        data=json.dumps({"action": "bulk_activities", "mode": "enable"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("animations.enabled.wave") is True

    # 3. Set timing
    req = urllib.request.Request(
        url,
        data=json.dumps({"action": "set_timing", "key": "special_cooldown", "value": 35.0}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert float(web_win.settings.get("behavior.special_cooldown_seconds")) == 35.0

    # 4. Set playback mode
    req = urllib.request.Request(
        url,
        data=json.dumps({"action": "set_playback_mode", "automatic": False, "locked_activity": "celebrate"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.waitUntil(lambda: web_win.settings.get("behavior.automatic_animations") is False, timeout=6000)
    assert web_win.settings.get("behavior.locked_activity") == "celebrate"

    # 5. Select character -> character_changed signal
    with qtbot.waitSignal(web_win.character_changed, timeout=2000) as blocker:
        req = urllib.request.Request(
            url,
            data=json.dumps({"action": "select_character", "character_id": "miles_morales"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
    assert blocker.args == ["miles_morales"]

    # 6. Set size & opacity
    with qtbot.waitSignal(web_win.size_changed, timeout=2000) as blocker:
        req = urllib.request.Request(
            url,
            data=json.dumps({"action": "set_size", "size": 240}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
    assert blocker.args == [240]
    assert float(web_win.settings.get("general.scale")) == 1.2

    req = urllib.request.Request(
        url,
        data=json.dumps({"action": "set_opacity", "opacity": 85}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert float(web_win.settings.get("general.opacity")) == 0.85


def test_desktop_and_apps_endpoints_and_actions(web_win, qtbot):
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"
    url_action = f"{base_url}/api/action"

    # 1. GET /api/display_settings
    with urllib.request.urlopen(f"{base_url}/api/display_settings") as resp:
        assert resp.status == 200
        ds = json.loads(resp.read().decode("utf-8"))
        assert "display_mode" in ds
        assert "monitor" in ds
        assert "default_position" in ds
        assert "title_bar_offset" in ds
        assert "window_perching" in ds
        assert "title_hang" in ds
        assert "target_applications" in ds
        assert isinstance(ds["target_applications"], list)

    # 2. GET /api/running_applications
    with urllib.request.urlopen(f"{base_url}/api/running_applications") as resp:
        assert resp.status == 200
        apps = json.loads(resp.read().decode("utf-8"))
        assert isinstance(apps, list)

    # 3. Action: set_display_mode
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_display_mode", "mode": "application"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("general.display_mode") == "application"

    # 4. Action: set_monitor
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_monitor", "monitor": "all"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("general.monitor") == "all"

    # 5. Action: set_default_position
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_default_position", "position": "bottom_left"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("general.default_position") == "bottom_left"

    # 6. Action: save_current_position -> save_position_requested signal
    spy = qtbot.waitSignal(web_win.save_position_requested, timeout=2000)
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "save_current_position"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    spy.wait()

    # 7. Action: set_title_offset
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_title_offset", "offset": 45}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert int(web_win.settings.get("animations.title_bar_offset")) == 45

    # 8. Action: toggle_window_perch & toggle_title_hang
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_window_perch", "enabled": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("animations.window_perching") is False

    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_title_hang", "enabled": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("animations.enabled.title_hang") is False

    # 9. Action: add_target_application & remove_target_application
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "add_target_application", "application": "test_calc.exe"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    apps_after = web_win.settings.get("general.target_applications", [])
    assert any("test_calc.exe" in (a if isinstance(a, str) else a.get("process_name", "")) for a in apps_after)

    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "remove_target_application", "application": "test_calc.exe"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    apps_after_rem = web_win.settings.get("general.target_applications", [])
    assert not any("test_calc.exe" in (a if isinstance(a, str) else a.get("process_name", "")) for a in apps_after_rem)


def test_focus_and_breaks_endpoints_and_actions(web_win, qtbot):
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"
    url_action = f"{base_url}/api/action"

    # 1. GET /api/focus_settings
    with urllib.request.urlopen(f"{base_url}/api/focus_settings") as resp:
        assert resp.status == 200
        fs = json.loads(resp.read().decode("utf-8"))
        assert "focus_mode" in fs
        assert "focus_timer_active" in fs
        assert "focus_time_remaining" in fs
        assert "continuous_work_seconds" in fs
        assert "enable_eye_break_alert" in fs
        assert "eye_break_minutes" in fs
        assert "inactivity_relax_minutes" in fs
        assert "inactivity_sit_minutes" in fs
        assert "inactivity_sleep_minutes" in fs

    # 2. Action: toggle_focus_mode
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_focus_mode", "enabled": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("behavior.focus_mode") is True

    # 3. Action: start_focus_timer -> focus_timer_started signal
    spy_start = qtbot.waitSignal(web_win.focus_timer_started, timeout=2000)
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "start_focus_timer", "minutes": 45}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    spy_start.wait()
    assert web_win._timer_active is True

    # 4. Action: stop_focus_timer -> focus_timer_stopped signal
    spy_stop = qtbot.waitSignal(web_win.focus_timer_stopped, timeout=2000)
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "stop_focus_timer"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    spy_stop.wait()
    assert web_win._timer_active is False

    # 5. Action: toggle_eye_break
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_eye_break", "enabled": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("behavior.enable_eye_break_alert") is False

    # 6. Action: set_eye_break_interval
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_eye_break_interval", "minutes": 25}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert float(web_win.settings.get("behavior.eye_break_minutes")) == 25.0

    # 7. Action: test_eye_break -> test_eye_break_requested signal
    spy_eye = qtbot.waitSignal(web_win.test_eye_break_requested, timeout=2000)
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "test_eye_break"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    spy_eye.wait()

    # 8. Action: set_inactivity_threshold
    for stage, mins in [("relax", 3), ("sit", 8), ("sleep", 15)]:
        req = urllib.request.Request(
            url_action,
            data=json.dumps({"action": "set_inactivity_threshold", "stage": stage, "minutes": mins}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
        qtbot.wait(100)
        assert float(web_win.settings.get(f"behavior.inactivity.{stage}_seconds")) == mins * 60.0

    # 9. update_eye_break_status integration
    web_win.update_eye_break_status(180.0, 900.0, True)
    assert web_win._continuous_sec == 180.0
    assert web_win._timer_remaining_sec == 900.0
    assert web_win._timer_active is True


def test_controls_endpoints_and_actions(web_win, qtbot):
    """Test full GET /api/control_settings endpoint and all control actions."""
    port = web_win.web_port
    assert port > 0
    url_settings = f"http://127.0.0.1:{port}/api/control_settings"
    url_action = f"http://127.0.0.1:{port}/api/action"

    # 1. GET /api/control_settings
    with urllib.request.urlopen(url_settings) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "enable_animation_hotkeys" in data
        assert "hotkeys_require_modifier" in data
        assert "wasd_movement_enabled" in data
        assert "wasd_static_pin" in data
        assert "enable_mouse_following" in data
        assert "enable_spider_sense_dodging" in data
        assert "cursor_radius" in data
        assert "click_through" in data
        assert "sound_enabled" in data
        assert "sound_volume" in data
        assert "movement_speed" in data
        assert "preset" in data
        assert "enable_comic_bubbles" in data
        assert isinstance(data["hotkeys"], list)
        assert len(data["hotkeys"]) >= 10

    # 2. Action: toggle_animation_hotkeys
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_animation_hotkeys", "enabled": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("behavior.enable_animation_hotkeys") is False

    # 3. Action: toggle_hotkeys_require_modifier
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_hotkeys_require_modifier", "enabled": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("behavior.hotkeys_require_modifier") is True

    # 4. Action: toggle_number_key
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_number_key", "key": "2", "enabled": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("behavior.enabled_number_keys.2") is False

    # 5. Action: set_all_number_keys
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_all_number_keys", "enabled": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("behavior.enabled_number_keys.2") is True

    # 6. Action: test_hotkey -> emits activity_requested and speech_bubble_requested
    spy_act = qtbot.waitSignal(web_win.activity_requested, timeout=2000)
    spy_quote = qtbot.waitSignal(web_win.speech_bubble_requested, timeout=2000)
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "test_hotkey", "activity": "swing", "quote": "WHOOSH!"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    spy_act.wait()
    spy_quote.wait()

    # 7. Action: toggle_wasd & toggle_wasd_static_pin & toggles
    for act_name, key, val in [
        ("toggle_wasd", "behavior.wasd_movement_enabled", False),
        ("toggle_wasd_static_pin", "behavior.wasd_static_pin", False),
        ("toggle_mouse_following", "behavior.enable_mouse_following", False),
        ("toggle_spider_sense_dodging", "behavior.enable_spider_sense_dodging", False),
        ("toggle_click_through", "system.click_through", True),
        ("toggle_sound", "behavior.sound_enabled", True),
        ("toggle_comic_bubbles", "behavior.enable_comic_bubbles", False),
    ]:
        req = urllib.request.Request(
            url_action,
            data=json.dumps({"action": act_name, "enabled": val}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
        qtbot.wait(100)
        assert web_win.settings.get(key) == val

    # 8. Numeric adjustments
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_movement_speed", "speed": 4.5}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert float(web_win.settings.get("behavior.movement_speed")) == 4.5

    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_cursor_radius", "radius": 240}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert int(web_win.settings.get("behavior.cursor_radius")) == 240

    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_sound_volume", "volume": 75}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert float(web_win.settings.get("behavior.sound_volume")) == 0.75

    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_pacing_preset", "preset": "playful"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("behavior.preset") == "playful"


def test_activities_categories_and_bulk_operations(web_win, qtbot):
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"

    # 1. Verify GET /api/activities returns all 32 activities & effects with valid categories
    with urllib.request.urlopen(f"{base_url}/api/activities") as resp:
        assert resp.status == 200
        acts = json.loads(resp.read().decode("utf-8"))
        assert len(acts) == 32  # 24 character animations + 8 effects

        valid_categories = {
            "Movement",
            "Rest & Poses",
            "Expressions",
            "Window Tricks",
            "Advanced Transitions",
            "Effects & Reactions"
        }
        for act in acts:
            assert act["category"] in valid_categories, f"Unknown category: {act['category']} for {act['id']}"
            assert "description" in act
            assert len(act["description"]) > 0

    # 2. Test toggle_activity for animation and effect
    url_action = f"{base_url}/api/action"
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_activity", "activity": "dance", "enabled": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("animations.enabled.dance") is False

    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_activity", "activity": "trampoline", "enabled": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("behavior.enable_web_trampoline") is False

    # 3. Test bulk_activities enable
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "bulk_activities", "mode": "enable"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("animations.enabled.dance") is True
    assert web_win.settings.get("behavior.enable_web_trampoline") is True
    assert web_win.settings.get("animations.enabled.walk") is True

    # 4. Test bulk_activities disable
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "bulk_activities", "mode": "disable"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("animations.enabled.dance") is False
    assert web_win.settings.get("behavior.enable_web_trampoline") is False
    assert web_win.settings.get("animations.enabled.walk") is False
    # Transitions like idle, fall, land remain true
    assert web_win.settings.get("animations.enabled.idle") is True


def test_target_applications_add_remove(web_win, qtbot):
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"
    url_action = f"{base_url}/api/action"

    # Add by executable name without .exe
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "add_target_application", "application": "test_app"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    target_apps = web_win.settings.get("general.target_applications", [])
    assert any((a.get("process_name") if isinstance(a, dict) else str(a)) == "test_app.exe" for a in target_apps)

    # Add by executable name with .exe (deduplication check)
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "add_target_application", "application": "test_app.exe"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    target_apps = web_win.settings.get("general.target_applications", [])
    matching = [a for a in target_apps if (a.get("process_name") if isinstance(a, dict) else str(a)) == "test_app.exe"]
    assert len(matching) == 1

    # Remove target application
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "remove_target_application", "application": "test_app.exe"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    target_apps = web_win.settings.get("general.target_applications", [])
    assert not any((a.get("process_name") if isinstance(a, dict) else str(a)) == "test_app.exe" for a in target_apps)


def test_settings_endpoints_and_actions(web_win, qtbot):
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"
    url_action = f"{base_url}/api/action"

    # 1. GET /api/app_settings
    with urllib.request.urlopen(f"{base_url}/api/app_settings") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "theme" in data
        assert "display_fps" in data
        assert "animation_speed" in data
        assert "start_minimized" in data
        assert "run_on_startup" in data
        assert "always_on_top" in data
        assert "version" in data
        assert data["version"] == "v2.5.0"

    # 2. POST set_theme
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_theme", "theme": "light"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("general.theme") == "light"

    # 3. POST set_display_fps
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_display_fps", "fps": 60}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("general.display_fps") == 60

    # 4. POST set_animation_speed
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "set_animation_speed", "speed": 1.5}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert float(web_win.settings.get("general.animation_speed")) == 1.5

    # 5. POST toggle_start_minimized
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_start_minimized", "enabled": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("system.start_minimized") is False

    # 6. POST toggle_run_on_startup
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_run_on_startup", "enabled": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("system.run_on_startup") is True

    # 7. POST toggle_always_on_top
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "toggle_always_on_top", "enabled": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("system.always_on_top") is False

    # 8. POST reset_companion_stats
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "reset_companion_stats"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("stats.distance_px") == 0

    # 9. POST reset_all_settings
    req = urllib.request.Request(
        url_action,
        data=json.dumps({"action": "reset_all_settings"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
    qtbot.wait(100)
    assert web_win.settings.get("general.theme") == "dark"





