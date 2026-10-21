"""Test all WebServer HTTP routes and endpoints."""
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from app.bootstrap import bootstrap_environment
bootstrap_environment()

import urllib.request
import urllib.parse
import json
from PySide6.QtWidgets import QApplication
from ui.web_window import WebMainWindow
from core.character_manager import CharacterManager

app = QApplication.instance()
if not app:
    app = QApplication([])

char_mgr = CharacterManager()
win = WebMainWindow(character_mgr=char_mgr)
port = win.web_port
base_url = f"http://127.0.0.1:{port}"

routes = [
    ("/api/status", "application/json"),
    ("/api/characters", "application/json"),
    ("/api/character_image?id=tom_holland", "image/png"),
    ("/api/activities", "application/json"),
    ("/api/timing_settings", "application/json"),
    ("/api/display_settings", "application/json"),
    ("/api/running_applications", "application/json"),
    ("/api/focus_settings", "application/json"),
    ("/api/control_settings", "application/json"),
    ("/api/app_settings", "application/json"),
    ("/api/character_preview", "image/png"),
    ("/api/activity_icon?name=walk", "image/png"),
    ("/", "text/html"),
]

print("=== TESTING HTTP ROUTES ===")
failed = []
for r, expected_type in routes:
    url = f"{base_url}{r}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()
            if status == 200 and expected_type in content_type:
                print(f"[OK] {r} -> {status} ({len(data)} bytes, {content_type})")
            else:
                print(f"[FAIL] {r} -> {status} (content-type: {content_type})")
                failed.append(r)
    except Exception as e:
        print(f"[ERR] {r} -> {e}")
        failed.append(r)

print("\n=== TESTING POST /api/action ===")
test_actions = [
    {"action": "set_opacity", "opacity": 90},
    {"action": "set_size", "size": 180},
    {"action": "toggle_sound", "enabled": False},
    {"action": "set_theme", "theme": "dark"},
]

for act in test_actions:
    try:
        data = json.dumps(act).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/action", data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            if resp.status == 200 and res_json.get("status") == "ok":
                print(f"[OK] POST /api/action ({act['action']}) -> {res_json}")
            else:
                print(f"[FAIL] POST /api/action ({act['action']}) -> {resp.status} {res_json}")
                failed.append(act["action"])
    except Exception as e:
        print(f"[ERR] POST /api/action ({act['action']}) -> {e}")
        failed.append(act["action"])

win.stop()
if failed:
    print(f"\nFAILED ENDPOINTS: {failed}")
    sys.exit(1)
else:
    print("\nALL HTTP ROUTES AND API ACTIONS VERIFIED SUCCESSFULLY (100% PASS)!")
    sys.exit(0)
