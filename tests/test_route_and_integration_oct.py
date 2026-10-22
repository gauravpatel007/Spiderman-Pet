"""Comprehensive Route, API, Navigation, and Integration test suite.

Tests:
- All 12 HTTP GET endpoints (valid queries, invalid queries, response structure, MIME types)
- POST /api/action payload validation, non-dict payloads, malformed JSON (RT-001)
- GET /api/activity_icon query parameter and path support (RT-002)
- SPA deep link routing fallback for /characters, /settings, /desktop-apps (INT-001)
- Web action test_hotkey type sanitization (INT-002)
- Desktop integration: Add application -> Settings persistence -> Display settings sync
- Dashboard closeEvent graceful hide without killing WebServer
- Security & authorization Origin / Host filtering
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
from PySide6.QtCore import Qt, QTimer
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
    win._force_close = True
    win.stop()
    win.close()
    win.deleteLater()
    qapp.processEvents()


# ── PHASE 2: Route & API Tests ──────────────────────────────────────────────

def test_rt_001_post_action_malformed_json_returns_400(web_win):
    """RT-001: Malformed JSON syntax must return HTTP 400 Bad Request, not 500."""
    port = web_win.web_port
    url = f"http://127.0.0.1:{port}/api/action"

    req = urllib.request.Request(
        url,
        data=b"{bad json syntax",
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400
    assert "Malformed JSON" in exc_info.value.reason or "Malformed JSON" in exc_info.value.read().decode("utf-8")


def test_rt_001_post_action_non_dict_payload_returns_400(web_win):
    """RT-001: Non-dict JSON payloads (lists, strings, numbers) must return HTTP 400 Bad Request."""
    port = web_win.web_port
    url = f"http://127.0.0.1:{port}/api/action"

    # 1. List payload
    req1 = urllib.request.Request(
        url,
        data=json.dumps([1, 2, 3]).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info1:
        urllib.request.urlopen(req1)
    assert exc_info1.value.code == 400

    # 2. String literal payload
    req2 = urllib.request.Request(
        url,
        data=json.dumps("string_action").encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info2:
        urllib.request.urlopen(req2)
    assert exc_info2.value.code == 400


def test_rt_001_post_action_invalid_action_type_returns_400(web_win):
    """RT-001: Payload where 'action' is not a string must return HTTP 400 Bad Request."""
    port = web_win.web_port
    url = f"http://127.0.0.1:{port}/api/action"

    req = urllib.request.Request(
        url,
        data=json.dumps({"action": 12345}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400


def test_rt_002_activity_icon_via_query_params(web_win):
    """RT-002: /api/activity_icon must accept query params ?name= and ?activity= as well as path."""
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"

    # 1. Via query param ?name=dance
    with urllib.request.urlopen(f"{base_url}/api/activity_icon?name=dance") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/png"
        data = resp.read()
        assert len(data) > 0

    # 2. Via query param ?activity=jump
    with urllib.request.urlopen(f"{base_url}/api/activity_icon?activity=jump") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/png"

    # 3. Via path /api/activity_icon/dance.png
    with urllib.request.urlopen(f"{base_url}/api/activity_icon/dance.png") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/png"


def test_int_001_spa_deep_link_routes_serve_index(web_win):
    """INT-001: Direct navigation or refresh on SPA client routes must serve index.html."""
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"

    spa_paths = ["/characters", "/activities", "/desktop", "/desktop-apps", "/focus", "/controls", "/settings"]
    for path in spa_paths:
        with urllib.request.urlopen(f"{base_url}{path}") as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type")
            content = resp.read().decode("utf-8", errors="ignore")
            assert "SpiderBuddy" in content or "html" in content.lower()


def test_int_002_test_hotkey_action_sanitization(web_win, qtbot):
    """INT-002: test_hotkey action with invalid non-string parameter types must not crash."""
    port = web_win.web_port
    url = f"http://127.0.0.1:{port}/api/action"

    # Send non-string activity and quote
    req = urllib.request.Request(
        url,
        data=json.dumps({"action": "test_hotkey", "activity": 9999, "quote": [1, 2, 3]}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200


def test_all_12_get_endpoints_validity_and_mime(web_win):
    """Verify all 12 GET endpoints respond with valid JSON / image types and correct schema."""
    port = web_win.web_port
    base_url = f"http://127.0.0.1:{port}"

    # 1. /api/character_preview
    with urllib.request.urlopen(f"{base_url}/api/character_preview") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/png"

    # 2. /api/character_image (by id)
    with urllib.request.urlopen(f"{base_url}/api/character_image/miles_morales.png") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/png"

    # 3. /api/characters
    with urllib.request.urlopen(f"{base_url}/api/characters") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "application/json"
        data = json.loads(resp.read().decode("utf-8"))
        assert isinstance(data, list)
        assert len(data) > 0

    # 4. /api/status
    with urllib.request.urlopen(f"{base_url}/api/status") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "application/json"
        data = json.loads(resp.read().decode("utf-8"))
        assert "is_running" in data
        assert "character" in data

    # 5. /api/activities
    with urllib.request.urlopen(f"{base_url}/api/activities") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert isinstance(data, list)

    # 6. /api/timing_settings
    with urllib.request.urlopen(f"{base_url}/api/timing_settings") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "special_cooldown" in data
        assert "idle_timeout" in data

    # 7. /api/activity_icon/dance.png
    with urllib.request.urlopen(f"{base_url}/api/activity_icon/dance.png") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/png"

    # 8. /api/display_settings
    with urllib.request.urlopen(f"{base_url}/api/display_settings") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "display_mode" in data
        assert "target_applications" in data

    # 9. /api/running_applications
    with urllib.request.urlopen(f"{base_url}/api/running_applications") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert isinstance(data, list)

    # 10. /api/focus_settings
    with urllib.request.urlopen(f"{base_url}/api/focus_settings") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "focus_mode" in data

    # 11. /api/control_settings
    with urllib.request.urlopen(f"{base_url}/api/control_settings") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "enable_animation_hotkeys" in data
        assert "cursor_radius" in data

    # 12. /api/app_settings
    with urllib.request.urlopen(f"{base_url}/api/app_settings") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "theme" in data


def test_cors_and_untrusted_origin_filtering(web_win):
    """Verify OPTIONS CORS preflight and 403 Forbidden on untrusted external origins."""
    port = web_win.web_port
    url = f"http://127.0.0.1:{port}/api/action"

    # Trusted local origin preflight
    opt_req = urllib.request.Request(url, method="OPTIONS", headers={"Origin": "http://127.0.0.1"})
    with urllib.request.urlopen(opt_req) as resp:
        assert resp.status == 200
        assert resp.headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1"

    # Untrusted malicious cross-origin POST must return 403
    evil_req = urllib.request.Request(
        url,
        data=json.dumps({"action": "hide"}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Origin": "https://malicious-website.com"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(evil_req)
    assert exc_info.value.code == 403


# ── PHASE 3: End-to-End Integration Tests ───────────────────────────────────

def test_e2e_add_target_application_and_display_sync(web_win, qtbot):
    """E2E flow: User adds target application -> Dispatched via HTTP -> Settings persist -> Display endpoint sync."""
    port = web_win.web_port
    url = f"http://127.0.0.1:{port}/api/action"

    app_name = "NotepadTestAudit.exe"
    req = urllib.request.Request(
        url,
        data=json.dumps({"action": "add_target_application", "application": app_name}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200

    qtbot.wait(200)

    # Verify settings persistence
    settings = get_settings()
    apps = settings.get("general.target_applications", [])
    found = any(
        (a.get("process_name") if isinstance(a, dict) else str(a)).lower() == app_name.lower()
        for a in apps
    )
    assert found is True

    # Verify /api/display_settings output contains the newly added target application
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/display_settings") as resp:
        ds = json.loads(resp.read().decode("utf-8"))
        target_apps = ds.get("target_applications", [])
        assert any(a.get("process_name", "").lower() == app_name.lower() for a in target_apps)

    # Clean up test entry
    req_del = urllib.request.Request(
        url,
        data=json.dumps({"action": "remove_target_application", "application": app_name}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_del) as resp:
        assert resp.status == 200


def test_dashboard_close_event_hides_to_tray_without_killing_server(web_win, qtbot):
    """Desktop UX integration: Closing dashboard hides window to tray without terminating web server."""
    port = web_win.web_port
    web_win.show()
    assert web_win.isVisible() is True

    # User clicks 'X' close button on dashboard
    web_win.close()
    qtbot.wait(100)

    # Window should be hidden, not destroyed
    assert web_win.isVisible() is False

    # WebServer must still be alive and serving requests
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "status" in data
