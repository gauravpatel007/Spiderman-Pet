"""Unit and regression tests for backend audit findings (October 2026)."""
import json
import urllib.request
import urllib.error
import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QApplication

from ui.web_server import WebServer
from ui.web_window import WebMainWindow
from core.character_manager import CharacterManager
from overlay.window_detector import WindowDetector, WindowInfo
from overlay.overlay_manager import OverlayManager
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


def test_character_image_path_traversal_protection(web_win):
    """Verify that path traversal in character ID is blocked with HTTP 400/404."""
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"

    # 1. Valid character returns 200
    with urllib.request.urlopen(f"{base_url}/api/character_image/miles_morales.png") as resp:
        assert resp.status == 200
        data = resp.read()
        assert len(data) > 0

    # 2. Path traversal attack via URL path should be rejected
    for attack in ["..%2F..%2Fmain", "../main", "..\\main", "characters/miles_morales"]:
        url = f"{base_url}/api/character_image/{attack}.png"
        try:
            req = urllib.request.Request(url)
            urllib.request.urlopen(req)
            pytest.fail(f"Request {url} should have raised HTTPError")
        except urllib.error.HTTPError as e:
            assert e.code in (400, 404)


def test_activity_icon_sanitization(web_win):
    """Verify that invalid activity names are rejected."""
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"

    # Valid activity icon
    with urllib.request.urlopen(f"{base_url}/api/activity_icon/dance.png") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/png"

    # Traversal / invalid characters
    for bad_name in ["..%2F..%2Fetc", "dance/hack", "dance&hack", ""]:
        url = f"{base_url}/api/activity_icon/{bad_name}.png"
        try:
            req = urllib.request.Request(url)
            urllib.request.urlopen(req)
            pytest.fail(f"Request {url} should have failed")
        except urllib.error.HTTPError as e:
            assert e.code in (400, 404)


def test_web_server_cors_and_unauthorized_post(web_win):
    """Verify that cross-origin POST requests from untrusted origins are blocked with 403."""
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"

    # 1. Authorized local POST succeeds
    req_local = urllib.request.Request(
        f"{base_url}/api/action",
        data=json.dumps({"action": "test_local"}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"}
    )
    with urllib.request.urlopen(req_local) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("status") == "ok"
        # Access-Control-Allow-Origin should match the local origin
        assert resp.headers.get("Access-Control-Allow-Origin") == f"http://127.0.0.1:{port}"

    # 2. Untrusted external origin is rejected with 403 Forbidden
    req_evil = urllib.request.Request(
        f"{base_url}/api/action",
        data=json.dumps({"action": "malicious_hack"}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Origin": "https://malicious-website.com"}
    )
    try:
        urllib.request.urlopen(req_evil)
        pytest.fail("Cross-origin request from malicious origin should have been blocked with 403")
    except urllib.error.HTTPError as e:
        assert e.code == 403


def test_always_on_top_window_flag(web_win):
    """Verify that toggle_always_on_top properly sets/clears Qt.WindowStaysOnTopHint."""
    # Test method directly
    web_win.set_always_on_top(True)
    assert bool(web_win.windowFlags() & Qt.WindowStaysOnTopHint) is True

    web_win.set_always_on_top(False)
    assert bool(web_win.windowFlags() & Qt.WindowStaysOnTopHint) is False

    # Test via action handler
    web_win._on_web_action({"action": "toggle_always_on_top", "enabled": True})
    assert bool(web_win.windowFlags() & Qt.WindowStaysOnTopHint) is True
    assert web_win.settings.get("system.always_on_top") is True

    web_win._on_web_action({"action": "toggle_always_on_top", "enabled": False})
    assert bool(web_win.windowFlags() & Qt.WindowStaysOnTopHint) is False
    assert web_win.settings.get("system.always_on_top") is False


def test_audio_meter_and_music_state_callbacks(web_win):
    """Verify that update_audio_meter and update_music_state store active state."""
    web_win.update_audio_meter(0.72, 0.45)
    assert web_win._audio_peak == pytest.approx(0.72)
    assert web_win._audio_smoothed == pytest.approx(0.45)

    web_win.update_music_state(True, 0.88)
    assert web_win._music_playing is True
    assert web_win._music_volume == pytest.approx(0.88)

    web_win.update_music_state(False, 0.0)
    assert web_win._music_playing is False


def test_focus_timer_countdown_status(web_win):
    """Verify that focus status is 'Focusing' while counting down even under 5 minutes."""
    # When active with 3 minutes (180s) remaining
    web_win.update_eye_break_status(120.0, 180.0, True)
    assert getattr(web_win, "_last_eye_break_state")[1] == "Focusing"

    # When active with 20 seconds remaining
    web_win.update_eye_break_status(200.0, 20.0, True)
    assert getattr(web_win, "_last_eye_break_state")[1] == "Focusing"

    # When timer reaches 0
    web_win.update_eye_break_status(220.0, 0.0, True)
    assert getattr(web_win, "_last_eye_break_state")[1] == "Break"

    # When inactive
    web_win.update_eye_break_status(0.0, 0.0, False)
    assert getattr(web_win, "_last_eye_break_state")[1] == "Ready"


def test_window_detector_include_self(qapp):
    """Verify that include_self flag on get_visible_windows works as expected."""
    # include_self=False (default) should not crash and returns a list
    windows_external = WindowDetector.get_visible_windows(include_self=False)
    assert isinstance(windows_external, list)

    windows_all = WindowDetector.get_visible_windows(include_self=True)
    assert isinstance(windows_all, list)
    assert len(windows_all) >= len(windows_external)
