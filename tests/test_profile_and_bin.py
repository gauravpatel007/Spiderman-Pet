"""Unit tests for My Profile tab and Character Recycle Bin features."""
import json
import urllib.request
import urllib.error
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from app.bootstrap import ensure_site_packages
ensure_site_packages()

from ui.web_server import WebServer


@pytest.fixture(scope="module")
def web_server_instance(tmp_path_factory):
    server = WebServer()
    port = server.start()
    assert port > 0, "Server port should be greater than 0"
    yield server
    server.stop()


def test_sidebar_profile_markup_and_css():
    """Verify HTML and CSS for My Profile sidebar tile and segmented bar."""
    root = Path(__file__).resolve().parent.parent
    index_html = (root / "Frontend" / "index.html").read_text(encoding="utf-8")

    assert 'id="sidebar-profile-card"' in index_html, "sidebar-profile-card must exist in index.html"
    assert 'data-framer-name="My Profile"' in index_html, "data-framer-name='My Profile' must exist"
    assert '.sidebar-profile-card' in index_html, "CSS rule for .sidebar-profile-card must exist"
    assert '.apple-segmented-bar' in index_html, "CSS rule for .apple-segmented-bar must exist"
    assert '.apple-segmented-item' in index_html, "CSS rule for .apple-segmented-item must exist"


def test_spider_bridge_has_profile_and_bin():
    """Verify spider_bridge.js contains profile view, bin logic, and event hooks."""
    root = Path(__file__).resolve().parent.parent
    bridge_js = (root / "Frontend" / "js" / "spider_bridge.js").read_text(encoding="utf-8")

    assert 'dashboard-profile-view' in bridge_js, "dashboard-profile-view container must exist"
    assert 'bin-characters-grid' in bridge_js, "bin-characters-grid must exist"
    assert 'bin-counter-badge' in bridge_js, "bin-counter-badge must exist"
    assert 'addToBin' in bridge_js, "addToBin function must exist"
    assert 'restoreFromBin' in bridge_js, "restoreFromBin function must exist"
    assert 'loadProfileView' in bridge_js, "loadProfileView function must exist"
    assert 'switchProfileSegment' in bridge_js, "switchProfileSegment function must exist"


def test_spa_deep_link_profile_and_bin(web_server_instance):
    """Verify deep-link routes /profile, /my-profile, and /bin return 200 HTML."""
    port = web_server_instance.port
    for route in ["/profile", "/my-profile", "/bin"]:
        url = f"http://127.0.0.1:{port}{route}"
        req = urllib.request.Request(url, headers={"Origin": f"http://127.0.0.1:{port}"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")
            body = resp.read().decode("utf-8")
            assert "Spider-Buddy" in body


def test_api_user_profile_get_and_post(web_server_instance):
    """Verify GET and POST on /api/user_profile."""
    port = web_server_instance.port
    url = f"http://127.0.0.1:{port}/api/user_profile"

    # GET
    req = urllib.request.Request(url, headers={"Origin": f"http://127.0.0.1:{port}"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert isinstance(data, dict)
        assert "name" in data

    # POST update
    update_payload = json.dumps({
        "name": "Miles Morales",
        "callsign": "Brooklyn Spider-Operative"
    }).encode("utf-8")
    post_req = urllib.request.Request(
        url,
        data=update_payload,
        headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"},
        method="POST"
    )
    with urllib.request.urlopen(post_req) as resp:
        assert resp.status == 200
        res_data = json.loads(resp.read().decode("utf-8"))
        assert res_data["status"] == "ok"
        assert res_data["profile"]["name"] == "Miles Morales"
        assert res_data["profile"]["callsign"] == "Brooklyn Spider-Operative"

    # Restore to Peter Parker
    restore_payload = json.dumps({
        "name": "Peter Parker",
        "callsign": "Spider-Operative"
    }).encode("utf-8")
    restore_req = urllib.request.Request(
        url,
        data=restore_payload,
        headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"},
        method="POST"
    )
    with urllib.request.urlopen(restore_req) as resp:
        assert resp.status == 200


def test_api_bin_endpoints_lifecycle(web_server_instance):
    """Verify full lifecycle of Bin API: get, add, restore, delete, empty."""
    port = web_server_instance.port
    base_url = f"http://127.0.0.1:{port}/api/bin"

    # 1. GET /api/bin/characters
    req = urllib.request.Request(f"{base_url}/characters", headers={"Origin": f"http://127.0.0.1:{port}"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        initial_list = json.loads(resp.read().decode("utf-8"))
        assert isinstance(initial_list, list)

    # 2. POST /api/bin/add
    test_hero = {
        "id": "test_spider_noir",
        "name": "Spider-Man Noir",
        "display_name": "Spider-Man Noir",
        "suit": "1933 Trenchcoat Suit",
        "description": "Hardboiled detective from 1933 Earth-90214."
    }
    add_req = urllib.request.Request(
        f"{base_url}/add",
        data=json.dumps({"character": test_hero}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"},
        method="POST"
    )
    with urllib.request.urlopen(add_req) as resp:
        assert resp.status == 200
        add_res = json.loads(resp.read().decode("utf-8"))
        assert add_res["status"] == "ok"
        assert add_res["added"]["id"] == "test_spider_noir"

    # Verify presence
    req = urllib.request.Request(f"{base_url}/characters", headers={"Origin": f"http://127.0.0.1:{port}"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        ids = [c["id"] for c in data]
        assert "test_spider_noir" in ids

    # 3. POST /api/bin/restore
    restore_req = urllib.request.Request(
        f"{base_url}/restore",
        data=json.dumps({"character_id": "test_spider_noir"}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"},
        method="POST"
    )
    with urllib.request.urlopen(restore_req) as resp:
        assert resp.status == 200
        res_data = json.loads(resp.read().decode("utf-8"))
        assert res_data["status"] == "ok"
        assert res_data["restored"]["id"] == "test_spider_noir"

    # Verify removed from bin
    req = urllib.request.Request(f"{base_url}/characters", headers={"Origin": f"http://127.0.0.1:{port}"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        ids = [c["id"] for c in data]
        assert "test_spider_noir" not in ids

    # 4. POST /api/bin/delete
    # Add again then delete permanently
    urllib.request.urlopen(urllib.request.Request(
        f"{base_url}/add",
        data=json.dumps({"character": test_hero}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"},
        method="POST"
    ))
    del_req = urllib.request.Request(
        f"{base_url}/delete",
        data=json.dumps({"character_id": "test_spider_noir"}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"},
        method="POST"
    )
    with urllib.request.urlopen(del_req) as resp:
        assert resp.status == 200
        del_res = json.loads(resp.read().decode("utf-8"))
        assert del_res["status"] == "ok"
        assert del_res["deleted"] == "test_spider_noir"
