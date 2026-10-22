# Full verification test script for Spider Sticky Notes backend and data storage
import json
import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(r"g:\Languages\Projects\Pet\Pet A2 Final")
sys.path.insert(0, str(ROOT))

CONFIG_FILE = ROOT / "config" / "sticky_notes.json"

print("--- 1. Testing config/sticky_notes.json ---")
assert CONFIG_FILE.exists(), f"File {CONFIG_FILE} does not exist!"
notes = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
assert isinstance(notes, list), "sticky_notes.json root should be a list"
print(f"Loaded {len(notes)} notes successfully.")
for n in notes:
    print(f"  Note ID: {n.get('id')}, Title: {n.get('title')}, Color: {n.get('color')}, Desktop: {n.get('desktop_visible')}, Items: {len(n.get('items', []))}")

print("\n--- 2. Testing web_server.py handlers ---")
import importlib.util
spec = importlib.util.spec_from_file_location("web_server", str(ROOT / "ui" / "web_server.py"))
web_server_mod = importlib.util.module_from_spec(spec)
sys.modules["web_server"] = web_server_mod
spec.loader.exec_module(web_server_mod)
WebRequestHandler = web_server_mod.SpiderWebHandler

class MockServerInstance:
    def __init__(self):
        self.port = 8000
        self.action_callback = self._on_action
        self.last_action = None

    def _on_action(self, data):
        self.last_action = data
        print("  [Mock Action Callback Received]:", data)

class MockHandler(WebRequestHandler):
    def __init__(self):
        self.server_instance = MockServerInstance()
        self.headers = {}
        self.response_status = None
        self.response_headers = {}
        self.response_body = b""

    def send_response(self, code):
        self.response_status = code

    def send_header(self, key, value):
        self.response_headers[key] = value

    def end_headers(self):
        pass

    def send_error(self, code, message=""):
        self.response_status = code
        self.response_body = message.encode("utf-8")
        print(f"  [Mock send_error]: {code} - {message}")

    class MockWFile:
        def __init__(self, outer):
            self.outer = outer
        def write(self, data):
            self.outer.response_body = data

    @property
    def wfile(self):
        return self.MockWFile(self)

handler = MockHandler()

# Test GET
print("\n--- Testing _handle_sticky_notes_get ---")
handler._handle_sticky_notes_get()
res_data = json.loads(handler.response_body.decode("utf-8"))
assert res_data.get("status") == "ok"
assert isinstance(res_data.get("notes"), list)
print(f"GET returned status={res_data.get('status')}, count={len(res_data.get('notes'))}")

# Test POST create
print("\n--- Testing POST create ---")
class MockRFile:
    def __init__(self, data_bytes):
        self.data_bytes = data_bytes
    def read(self, length):
        return self.data_bytes[:length]

create_payload = json.dumps({
    "action": "create",
    "title": "Automated Test Mission",
    "color": "miles_black",
    "content": "Automated verification note.",
    "items": [{"text": "Task A", "done": False}, {"text": "Task B", "done": True}],
    "desktop_visible": True
}).encode("utf-8")

handler.headers = {"Content-Length": str(len(create_payload))}
handler.rfile = MockRFile(create_payload)
handler._handle_sticky_notes_post()
res_create = json.loads(handler.response_body.decode("utf-8"))
assert res_create.get("status") == "ok"
created_id = res_create.get("note", {}).get("id")
print(f"Created note id: {created_id}")
assert created_id is not None
assert handler.server_instance.last_action is not None
assert handler.server_instance.last_action.get("subaction") == "create"

# Test POST toggle_item
print("\n--- Testing POST toggle_item ---")
toggle_payload = json.dumps({
    "action": "toggle_item",
    "id": created_id,
    "item_index": 0
}).encode("utf-8")

handler.headers = {"Content-Length": str(len(toggle_payload))}
handler.rfile = MockRFile(toggle_payload)
handler._handle_sticky_notes_post()
res_toggle = json.loads(handler.response_body.decode("utf-8"))
assert res_toggle.get("status") == "ok"
toggled_note = next((n for n in res_toggle.get("notes", []) if n.get("id") == created_id), None)
assert toggled_note is not None
assert toggled_note["items"][0]["done"] == True, "Task A should now be done=True"
print("toggle_item toggled task 0 to done=True successfully!")

# Test POST delete
print("\n--- Testing POST delete ---")
delete_payload = json.dumps({
    "action": "delete",
    "id": created_id
}).encode("utf-8")

handler.headers = {"Content-Length": str(len(delete_payload))}
handler.rfile = MockRFile(delete_payload)
handler._handle_sticky_notes_post()
res_del = json.loads(handler.response_body.decode("utf-8"))
assert res_del.get("status") == "ok"
assert not any(n.get("id") == created_id for n in res_del.get("notes", []))
print("Deleted note successfully!")

print("\nALL BACKEND API AND STORAGE TESTS PASSED 100%!")
