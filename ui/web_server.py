"""Embedded local HTTP server for Spider-Buddy HTML/CSS/JS frontend."""
import http.server
import json
import logging
import mimetypes
import os
import re
import socketserver
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("SpiderBuddy.UI.WebServer")

# Ensure proper MIME types for modern ES modules and web assets
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("image/png", ".png")


class SpiderWebHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler serving Framer UI files and REST API endpoints."""

    def __init__(self, *args, **kwargs):
        self.server_instance = kwargs.pop("server_instance", None)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        # 1. API: Character Preview Image
        if self.path.startswith("/api/character_preview"):
            self._handle_character_preview()
            return

        # 2. API: Specific Character Image by ID
        if self.path.startswith("/api/character_image"):
            self._handle_character_image()
            return

        # 3. API: Available Characters List
        if self.path.startswith("/api/characters"):
            self._handle_characters_list()
            return

        # 4. API: Current Status JSON
        if self.path.startswith("/api/status"):
            self._handle_api_status()
            return

        # 5. API: Available Activities List
        if self.path.startswith("/api/activities"):
            self._handle_activities_list()
            return

        # 6. API: Timing Settings JSON
        if self.path.startswith("/api/timing_settings"):
            self._handle_timing_settings()
            return

        # 7. API: Activity Icon Image
        if self.path.startswith("/api/activity_icon"):
            self._handle_activity_icon()
            return

        # 8. API: Display & Apps Settings JSON
        if self.path.startswith("/api/display_settings"):
            self._handle_display_settings()
            return

        # 9. API: Running Applications List
        if self.path.startswith("/api/running_applications"):
            self._handle_running_applications()
            return

        # 10. API: Focus & Breaks Settings JSON
        if self.path.startswith("/api/focus_settings"):
            self._handle_focus_settings()
            return

        # 11. API: Controls & Shortcuts Settings JSON
        if self.path.startswith("/api/control_settings"):
            self._handle_control_settings()
            return

        # 12. API: General Application Settings JSON
        if self.path.startswith("/api/app_settings"):
            self._handle_app_settings()
            return

        # 13. API: User Profile JSON
        if self.path.startswith("/api/user_profile"):
            self._handle_user_profile_get()
            return

        # 14. API: Bin (Removed Characters) JSON
        if self.path.startswith("/api/bin/characters"):
            self._handle_bin_characters_list()
            return

        # 15. API: Custom Profile Avatars list
        if self.path.startswith("/api/custom_avatars"):
            self._handle_custom_avatars_get()
            return

        # 16. API: Sticky Notes list
        if self.path.startswith("/api/sticky_notes"):
            self._handle_sticky_notes_get()
            return

        # 7. Main HTML entry point & SPA deep link navigation fallback
        clean_path = self.path.split("?")[0].rstrip("/")
        SPA_ROUTES = {
            "", "/index", "/index.html", "/home", "/characters", "/activities",
            "/desktop", "/desktop-apps", "/desktop_apps", "/focus",
            "/focus-breaks", "/focus_breaks", "/controls", "/settings",
            "/profile", "/my-profile", "/bin", "/notes", "/sticky-notes", "/sticky_notes"
        }
        target_file = Path(self.directory) / clean_path.lstrip("/")
        if clean_path in SPA_ROUTES or (not clean_path.startswith("/api/") and "." not in clean_path.split("/")[-1] and not target_file.exists()):
            index_path = Path(self.directory) / "index.html"
            if not index_path.exists():
                index_path = Path(self.directory) / "index"
            if index_path.exists():
                try:
                    data = index_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    logger.error(f"Error serving index: {e}")

        super().do_GET()

    def _is_request_authorized(self) -> bool:
        """Validate that incoming requests originate from local application context."""
        origin = self.headers.get("Origin")
        if origin:
            parsed = urllib.parse.urlparse(origin)
            hostname = (parsed.hostname or "").lower()
            if hostname not in ("127.0.0.1", "localhost", "null", ""):
                return False
        host = self.headers.get("Host", "")
        if host:
            hostname = host.split(":")[0].lower()
            if hostname not in ("127.0.0.1", "localhost", ""):
                return False
        return True

    def do_POST(self):
        if not self._is_request_authorized():
            self.send_error(403, "Forbidden: Untrusted cross-origin request")
            return
        if self.path.startswith("/api/action"):
            self._handle_api_action()
            return
        if self.path.startswith("/api/user_profile"):
            self._handle_user_profile_post()
            return
        if self.path.startswith("/api/bin/"):
            self._handle_bin_post()
            return
        if self.path.startswith("/api/upload_profile_avatar"):
            self._handle_upload_profile_avatar()
            return
        if self.path.startswith("/api/delete_profile_avatar"):
            self._handle_delete_profile_avatar()
            return
        if self.path.startswith("/api/sticky_notes"):
            self._handle_sticky_notes_post()
            return
        self.send_error(404, "Endpoint not found")

    def _handle_character_preview(self):
        """Serve the current active character preview image."""
        preview_bytes = None
        if self.server_instance and self.server_instance.get_preview_bytes:
            preview_bytes = self.server_instance.get_preview_bytes()

        if not preview_bytes:
            # Fallback to tom_holland preview.png
            root = Path(__file__).resolve().parent.parent
            default_preview = root / "characters" / "tom_holland" / "preview.png"
            if default_preview.exists():
                preview_bytes = default_preview.read_bytes()

        if preview_bytes:
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Content-Length", str(len(preview_bytes)))
            self.end_headers()
            self.wfile.write(preview_bytes)
        else:
            self.send_error(404, "Preview image not found")

    def _handle_character_image(self):
        """Serve character preview image by path /api/character_image/<id>.png or query ?id=..."""
        char_id = ""
        if "/api/character_image/" in self.path:
            raw_id = self.path.split("/api/character_image/")[1].split("?")[0]
            char_id = raw_id.replace(".png", "").strip()
        else:
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            char_id = qs.get("id", [""])[0].strip()

        if not char_id or not re.fullmatch(r"[a-zA-Z0-9_-]+", char_id):
            self.send_error(400, f"Invalid character identifier: {char_id}")
            return

        img_bytes = None
        if self.server_instance and self.server_instance.get_character_image:
            img_bytes = self.server_instance.get_character_image(char_id)

        if not img_bytes and char_id:
            root = Path(__file__).resolve().parent.parent
            characters_dir = (root / "characters").resolve()
            target_file = (characters_dir / char_id / "preview.png").resolve()
            if target_file.is_file() and target_file.is_relative_to(characters_dir):
                img_bytes = target_file.read_bytes()

        if img_bytes:
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(img_bytes)))
            self.end_headers()
            self.wfile.write(img_bytes)
        else:
            self.send_error(404, f"Character image not found for id: {char_id}")

    def _handle_characters_list(self):
        """Return list of all discovered Spider-Man characters as JSON."""
        characters = []
        if self.server_instance and self.server_instance.get_characters_list:
            characters = self.server_instance.get_characters_list()

        payload = json.dumps(characters).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_api_status(self):
        """Return current companion status as JSON."""
        status_data = {}
        if self.server_instance and self.server_instance.get_status_data:
            status_data = self.server_instance.get_status_data()

        payload = json.dumps(status_data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_activities_list(self):
        """Return list of all companion activities as JSON."""
        activities = []
        if self.server_instance and self.server_instance.get_activities_list:
            activities = self.server_instance.get_activities_list()

        payload = json.dumps(activities).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_timing_settings(self):
        """Return behavior timing settings as JSON."""
        timing_data = {}
        if self.server_instance and self.server_instance.get_timing_settings:
            timing_data = self.server_instance.get_timing_settings()

        payload = json.dumps(timing_data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_activity_icon(self):
        """Serve first frame thumbnail for an activity: /api/activity_icon/<name>.png or ?name=... / ?activity=..."""
        raw_name = ""
        if "/api/activity_icon/" in self.path:
            raw_name = self.path.split("/api/activity_icon/")[1].split("?")[0]
        else:
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            raw_name = qs.get("name", [""])[0] or qs.get("activity", [""])[0]

        act_name = raw_name.replace(".png", "").strip()

        if not act_name or not re.fullmatch(r"[a-zA-Z0-9_-]+", act_name):
            self.send_error(400, f"Invalid activity identifier: {act_name}")
            return

        img_bytes = None
        if self.server_instance and self.server_instance.get_activity_icon:
            img_bytes = self.server_instance.get_activity_icon(act_name)

        if not img_bytes:
            # Fallback to preview image
            if self.server_instance and self.server_instance.get_preview_bytes:
                img_bytes = self.server_instance.get_preview_bytes()

        if img_bytes:
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(img_bytes)))
            self.end_headers()
            self.wfile.write(img_bytes)
        else:
            self.send_error(404, f"Icon not found for activity: {act_name}")

    def _handle_display_settings(self):
        """Return display mode, monitor bounds, and window perching settings as JSON."""
        data = {}
        if self.server_instance and self.server_instance.get_display_settings:
            data = self.server_instance.get_display_settings()

        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_running_applications(self):
        """Return list of running visible windows / apps as JSON."""
        apps = []
        if self.server_instance and self.server_instance.get_running_applications:
            apps = self.server_instance.get_running_applications()

        payload = json.dumps(apps).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_focus_settings(self):
        """Return focus mode, pomodoro, eye break, and inactivity settings as JSON."""
        data = {}
        if self.server_instance and self.server_instance.get_focus_settings:
            data = self.server_instance.get_focus_settings()

        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_control_settings(self):
        """Return keyboard shortcuts, WASD, mouse tracking, and reaction settings as JSON."""
        data = {}
        if self.server_instance and self.server_instance.get_control_settings:
            data = self.server_instance.get_control_settings()

        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_app_settings(self):
        """Return general application settings, system startup, and preferences as JSON."""
        data = {}
        if self.server_instance and self.server_instance.get_app_settings:
            data = self.server_instance.get_app_settings()

        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_api_action(self):
        """Handle incoming actions from JavaScript buttons and controls."""
        try:
            try:
                content_length = int(self.headers.get("Content-Length", 0))
            except (ValueError, TypeError):
                self.send_error(400, "Invalid Content-Length header")
                return

            if content_length < 0:
                self.send_error(400, "Negative Content-Length header")
                return

            body = self.rfile.read(content_length) if content_length > 0 else b""
            if not body:
                data = {}
            else:
                try:
                    data = json.loads(body.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as err:
                    self.send_error(400, f"Malformed JSON payload: {err}")
                    return

            if not isinstance(data, dict):
                self.send_error(400, "Action payload must be a JSON object")
                return

            action_val = data.get("action")
            if action_val is not None and not isinstance(action_val, str):
                self.send_error(400, "Field 'action' must be a string")
                return

            if self.server_instance:
                if hasattr(self.server_instance, "action_received"):
                    self.server_instance.action_received.emit(data)
                elif self.server_instance.action_callback:
                    self.server_instance.action_callback(data)

            response = json.dumps({"status": "ok", "received": data}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        except Exception as e:
            logger.error(f"Error handling action: {e}", exc_info=True)
            self.send_error(500, str(e))

    def end_headers(self):
        origin = self.headers.get("Origin")
        if origin and self._is_request_authorized():
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            port = self.server_instance.port if self.server_instance else 0
            self.send_header("Access-Control-Allow-Origin", f"http://127.0.0.1:{port}" if port else "http://127.0.0.1")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        if not self._is_request_authorized():
            self.send_error(403, "Forbidden")
            return
        self.send_response(200)
        self.end_headers()

    def _get_bin_file(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        config_dir = root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "bin_characters.json"

    def _get_profile_file(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        config_dir = root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "user_profile.json"

    def _load_bin_characters(self) -> list:
        bin_file = self._get_bin_file()
        if bin_file.exists():
            try:
                data = json.loads(bin_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception as e:
                logger.warning(f"Error reading bin characters: {e}")
        # Default seed
        default_seed = [
            {
                "id": "spider_2099",
                "name": "Spider-Man 2099",
                "display_name": "Spider-Man 2099 (Miguel O'Hara)",
                "suit": "Nueva York 2099 Suit",
                "description": "Earth-928 high-tech nano-weave suit with talons and accelerated vision.",
                "avatar": "images/spiderman_brand_icon.png",
                "preview_url": "images/spiderman_brand_icon.png",
                "removed_at": "2026-10-21T16:45:00Z",
                "removed_date_str": "Oct 21, 2026 • 04:45 PM"
            },
            {
                "id": "symbiote_classic",
                "name": "Symbiote Spider-Man",
                "display_name": "Symbiote Peter Parker",
                "suit": "Alien Symbiote Black Suit",
                "description": "Alien symbiote suit with liquid web shooters and shapeshifting tendrils.",
                "avatar": "images/spiderman_avatar_brand.png",
                "preview_url": "images/spiderman_avatar_brand.png",
                "removed_at": "2026-10-21T17:15:00Z",
                "removed_date_str": "Oct 21, 2026 • 05:15 PM"
            }
        ]
        try:
            bin_file.write_text(json.dumps(default_seed, indent=2), encoding="utf-8")
        except Exception:
            pass
        return default_seed

    def _save_bin_characters(self, data: list):
        bin_file = self._get_bin_file()
        bin_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _handle_bin_characters_list(self):
        """Return list of removed characters stored in Bin."""
        data = self._load_bin_characters()
        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_bin_post(self):
        """Handle Bin actions: add, restore, delete, empty."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            data = {}

        path = self.path.rstrip("/")
        bin_list = self._load_bin_characters()

        if path.endswith("/restore"):
            cid = data.get("character_id")
            restored = None
            if cid:
                for idx, c in enumerate(bin_list):
                    if c.get("id") == cid:
                        restored = bin_list.pop(idx)
                        break
                self._save_bin_characters(bin_list)
            resp = {"status": "ok", "restored": restored}
        elif path.endswith("/delete"):
            cid = data.get("character_id")
            if cid:
                bin_list = [c for c in bin_list if c.get("id") != cid]
                self._save_bin_characters(bin_list)
            resp = {"status": "ok", "deleted": cid}
        elif path.endswith("/empty"):
            self._save_bin_characters([])
            resp = {"status": "ok", "cleared": True}
        elif path.endswith("/add"):
            char = data.get("character", data)
            if isinstance(char, dict) and char.get("id"):
                bin_list = [c for c in bin_list if c.get("id") != char.get("id")]
                bin_list.insert(0, char)
                self._save_bin_characters(bin_list)
            resp = {"status": "ok", "added": char}
        else:
            self.send_error(404, "Unknown bin endpoint")
            return

        payload = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_user_profile_get(self):
        """Return user profile data as JSON."""
        prof_file = self._get_profile_file()
        data = {
            "name": "Peter Parker",
            "callsign": "Spider-Operative",
            "rank": "Level 7 Companion Master",
            "bio": "With great power comes great responsibility. Balancing desktop productivity with web-slinging acrobatics.",
            "avatar": "images/spiderman_brand_icon.png",
            "custom_avatars": []
        }
        if prof_file.exists():
            try:
                data = json.loads(prof_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Error reading user profile: {e}")

        if "custom_avatars" not in data or not isinstance(data["custom_avatars"], list):
            data["custom_avatars"] = []

        # Scan custom_avatars directory to include all persisted image files
        root = Path(__file__).resolve().parent.parent
        custom_dir = root / "Frontend" / "images" / "custom_avatars"
        if custom_dir.is_dir():
            for f in sorted(custom_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                    rel = f"images/custom_avatars/{f.name}"
                    if rel not in data["custom_avatars"]:
                        data["custom_avatars"].append(rel)

        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_custom_avatars_get(self):
        """Return list of all custom uploaded profile avatars."""
        prof_file = self._get_profile_file()
        custom_list = []
        if prof_file.exists():
            try:
                curr = json.loads(prof_file.read_text(encoding="utf-8"))
                custom_list = curr.get("custom_avatars", [])
            except Exception:
                pass

        root = Path(__file__).resolve().parent.parent
        custom_dir = root / "Frontend" / "images" / "custom_avatars"
        if custom_dir.is_dir():
            for f in sorted(custom_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                    rel = f"images/custom_avatars/{f.name}"
                    if rel not in custom_list:
                        custom_list.append(rel)

        payload = json.dumps({"status": "ok", "custom_avatars": custom_list}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_upload_profile_avatar(self):
        """Upload and save a custom profile avatar image."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self.send_error(400, f"Malformed upload payload: {e}")
            return

        image_data = data.get("image_data", "")
        filename = data.get("filename", "")
        if not image_data:
            self.send_error(400, "Missing image_data")
            return

        import base64
        import time
        if "," in image_data:
            header, b64_data = image_data.split(",", 1)
        else:
            b64_data = image_data

        try:
            raw_bytes = base64.b64decode(b64_data)
        except Exception as e:
            self.send_error(400, f"Invalid base64 encoding: {e}")
            return

        ext = ".png"
        if filename:
            _, orig_ext = os.path.splitext(filename)
            if orig_ext.lower() in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                ext = orig_ext.lower()

        root = Path(__file__).resolve().parent.parent
        custom_dir = root / "Frontend" / "images" / "custom_avatars"
        custom_dir.mkdir(parents=True, exist_ok=True)

        unique_id = f"custom_dp_{int(time.time()*1000)}"
        save_filename = f"{unique_id}{ext}"
        target_path = custom_dir / save_filename

        try:
            target_path.write_bytes(raw_bytes)
        except Exception as e:
            logger.error(f"Failed to write custom avatar: {e}")
            self.send_error(500, f"Failed to save image file: {e}")
            return

        rel_url = f"images/custom_avatars/{save_filename}"

        prof_file = self._get_profile_file()
        curr = {}
        if prof_file.exists():
            try:
                curr = json.loads(prof_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        custom_list = curr.get("custom_avatars", [])
        if rel_url not in custom_list:
            custom_list.append(rel_url)
        curr["custom_avatars"] = custom_list
        curr["avatar"] = rel_url
        prof_file.write_text(json.dumps(curr, indent=2), encoding="utf-8")

        payload = json.dumps({
            "status": "ok",
            "url": rel_url,
            "id": unique_id,
            "custom_avatars": custom_list,
            "avatar": rel_url
        }).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_delete_profile_avatar(self):
        """Delete an uploaded custom profile avatar (default presets cannot be deleted)."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self.send_error(400, f"Malformed delete payload: {e}")
            return

        target_url = (data.get("url") or "").strip()
        if not target_url:
            self.send_error(400, "Missing url to delete")
            return

        DEFAULT_PRESETS = [
            "images/spiderman_brand_icon.png",
            "images/miles_brand_avatar.jpg",
            "images/amazing_spiderman_face.jpg",
            "images/spiderman_avatar_brand.png"
        ]
        if target_url in DEFAULT_PRESETS:
            self.send_error(403, "Default preset avatars cannot be deleted.")
            return

        root = Path(__file__).resolve().parent.parent
        custom_dir = (root / "Frontend" / "images" / "custom_avatars").resolve()

        file_name = Path(target_url).name
        target_file = (custom_dir / file_name).resolve()
        if target_file.is_file() and target_file.is_relative_to(custom_dir):
            try:
                target_file.unlink()
            except Exception as e:
                logger.warning(f"Could not delete avatar file {target_file}: {e}")

        prof_file = self._get_profile_file()
        curr = {}
        if prof_file.exists():
            try:
                curr = json.loads(prof_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        custom_list = curr.get("custom_avatars", [])
        custom_list = [u for u in custom_list if u != target_url and Path(u).name != file_name]
        curr["custom_avatars"] = custom_list

        if curr.get("avatar") == target_url or Path(curr.get("avatar", "")).name == file_name:
            curr["avatar"] = "images/spiderman_brand_icon.png"

        prof_file.write_text(json.dumps(curr, indent=2), encoding="utf-8")

        payload = json.dumps({
            "status": "ok",
            "custom_avatars": custom_list,
            "avatar": curr.get("avatar")
        }).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_user_profile_post(self):
        """Update user profile preferences and data."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self.send_error(400, f"Malformed profile payload: {e}")
            return

        prof_file = self._get_profile_file()
        curr = {}
        if prof_file.exists():
            try:
                curr = json.loads(prof_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        curr.update(data)
        prof_file.write_text(json.dumps(curr, indent=2), encoding="utf-8")

        payload = json.dumps({"status": "ok", "profile": curr}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _get_sticky_notes_file(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        config_dir = root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "sticky_notes.json"

    def _load_sticky_notes(self) -> list:
        notes_file = self._get_sticky_notes_file()
        if notes_file.exists():
            try:
                data = json.loads(notes_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception as e:
                logger.warning(f"Error loading sticky notes: {e}")
        return []

    def _save_sticky_notes(self, data: list):
        notes_file = self._get_sticky_notes_file()
        notes_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _handle_sticky_notes_get(self):
        notes = self._load_sticky_notes()
        payload = json.dumps({"status": "ok", "notes": notes}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_sticky_notes_post(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b""
            req = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self.send_error(400, f"Malformed JSON: {e}")
            return

        action = req.get("action", "save")
        notes = self._load_sticky_notes()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if action in ("create", "add"):
            note_data = req.get("note") or req
            new_id = note_data.get("id") or f"note_{int(time.time()*1000)}"
            raw_color = note_data.get("color") or note_data.get("color_theme") or "spidey_red"
            raw_pinned = note_data.get("pinned") if "pinned" in note_data else note_data.get("is_pinned", True)
            raw_items = note_data.get("items") or note_data.get("tasks") or []
            normalized_items = []
            for it in raw_items:
                if isinstance(it, dict):
                    normalized_items.append({
                        "id": it.get("id") or f"item_{int(time.time()*1000)}_{len(normalized_items)}",
                        "text": it.get("text") or "",
                        "done": bool(it.get("done") or it.get("completed", False))
                    })
                elif isinstance(it, str):
                    normalized_items.append({
                        "id": f"item_{int(time.time()*1000)}_{len(normalized_items)}",
                        "text": it,
                        "done": False
                    })

            new_note = {
                "id": new_id,
                "title": note_data.get("title") or "Spider Mission Note",
                "color": raw_color,
                "content": note_data.get("content") or "",
                "items": normalized_items,
                "pinned": bool(raw_pinned),
                "desktop_visible": bool(note_data.get("desktop_visible", True)),
                "pos_x": int(note_data.get("pos_x", note_data.get("x", 320 + (len(notes) % 4) * 40))),
                "pos_y": int(note_data.get("pos_y", note_data.get("y", 80 + (len(notes) % 3) * 30))),
                "width": int(note_data.get("width", 280)),
                "height": int(note_data.get("height", 320)),
                "minimized": bool(note_data.get("minimized", False)),
                "created_at": now_iso,
                "updated_at": now_iso
            }
            notes.insert(0, new_note)
            self._save_sticky_notes(notes)
            resp = {"status": "ok", "action": "created", "note": new_note, "notes": notes}

            if self.server_instance and self.server_instance.action_callback:
                self.server_instance.action_callback({"action": "sticky_note_sync", "subaction": "create", "note": new_note})

        elif action == "update":
            note_id = req.get("id") or (req.get("note") and req["note"].get("id"))
            updated_note = None
            if note_id:
                for idx, n in enumerate(notes):
                    if n.get("id") == note_id:
                        patch = req.get("note", req)
                        for k, v in patch.items():
                            if k not in ("id", "created_at", "action"):
                                if k == "color_theme":
                                    n["color"] = v
                                elif k == "is_pinned":
                                    n["pinned"] = bool(v)
                                elif k == "tasks":
                                    norm = []
                                    for t in v:
                                        if isinstance(t, dict):
                                            norm.append({
                                                "id": t.get("id") or f"item_{len(norm)}",
                                                "text": t.get("text", ""),
                                                "done": bool(t.get("done") or t.get("completed", False))
                                            })
                                    n["items"] = norm
                                elif k == "x":
                                    n["pos_x"] = int(v)
                                elif k == "y":
                                    n["pos_y"] = int(v)
                                else:
                                    n[k] = v
                        n["updated_at"] = now_iso
                        updated_note = n
                        break
                self._save_sticky_notes(notes)
            resp = {"status": "ok", "action": "updated", "note": updated_note, "notes": notes}

            if self.server_instance and self.server_instance.action_callback:
                self.server_instance.action_callback({"action": "sticky_note_sync", "subaction": "update", "note": updated_note})

        elif action == "delete":
            note_id = req.get("id")
            if note_id:
                notes = [n for n in notes if n.get("id") != note_id]
                self._save_sticky_notes(notes)
            resp = {"status": "ok", "action": "deleted", "id": note_id, "notes": notes}

            if self.server_instance and self.server_instance.action_callback:
                self.server_instance.action_callback({"action": "sticky_note_sync", "subaction": "delete", "id": note_id})

        elif action == "toggle_item":
            note_id = req.get("id") or req.get("note_id")
            item_id = req.get("item_id")
            item_index = req.get("item_index")
            if note_id:
                for n in notes:
                    if n.get("id") == note_id:
                        items = n.get("items", [])
                        if item_id:
                            for it in items:
                                if it.get("id") == item_id:
                                    it["done"] = not it.get("done", False)
                                    break
                        elif item_index is not None and 0 <= int(item_index) < len(items):
                            items[int(item_index)]["done"] = not items[int(item_index)].get("done", False)
                        n["updated_at"] = now_iso
                        break
                self._save_sticky_notes(notes)
            resp = {"status": "ok", "action": "toggle_item", "notes": notes}

            if self.server_instance and self.server_instance.action_callback:
                self.server_instance.action_callback({"action": "sticky_note_sync", "subaction": "update_item", "note_id": note_id, "item_id": item_id})

        elif action == "save_all":
            all_notes = req.get("notes")
            if isinstance(all_notes, list):
                notes = all_notes
                self._save_sticky_notes(notes)
            resp = {"status": "ok", "action": "saved_all", "notes": notes}

            if self.server_instance and self.server_instance.action_callback:
                self.server_instance.action_callback({"action": "sticky_note_sync", "subaction": "reload"})

        elif action in ("spawn_desktop", "toggle_desktop"):
            note_id = req.get("id")
            target_note = None
            for n in notes:
                if n.get("id") == note_id:
                    if action == "toggle_desktop":
                        n["desktop_visible"] = not n.get("desktop_visible", False)
                    else:
                        n["desktop_visible"] = True
                    n["updated_at"] = now_iso
                    target_note = n
                    break
            self._save_sticky_notes(notes)
            resp = {"status": "ok", "action": action, "note": target_note, "notes": notes}

            if self.server_instance and self.server_instance.action_callback:
                self.server_instance.action_callback({"action": "sticky_note_sync", "subaction": "toggle_desktop", "note": target_note})
        else:
            resp = {"status": "error", "message": f"Unknown action: {action}"}

        payload = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        # Suppress routine GET logging unless in DEBUG mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"{self.address_string()} - {format % args}")


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


try:
    from PySide6.QtCore import QObject, Signal
except ImportError:
    class QObject:
        def __init__(self, parent=None):
            pass
    def Signal(*args, **kwargs):
        class _MockSignal:
            def emit(self, *a, **kw):
                pass
            def connect(self, *a, **kw):
                pass
        return _MockSignal()

class WebServer(QObject):
    """Manages the background HTTP server for Framer UI with thread-safe Qt signals."""

    action_received = Signal(dict)

    def __init__(self, directory: Optional[str] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        if directory is None:
            # Default to Frontend in project root or frozen MEIPASS (fallback to legacy BIN/Frammer UI)
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                base_dir = Path(sys._MEIPASS)
            else:
                base_dir = Path(__file__).resolve().parent.parent

            frontend_dir = base_dir / "Frontend"
            bin_dir = base_dir / "BIN" / "Frammer UI"
            if frontend_dir.exists():
                directory = str(frontend_dir)
            elif bin_dir.exists():
                directory = str(bin_dir)
            else:
                directory = str(frontend_dir)

        self.directory = os.path.abspath(directory)
        self.port: int = 0
        self.server: Optional[ThreadedTCPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.action_callback: Optional[Callable[[dict], None]] = None
        self.get_preview_bytes: Optional[Callable[[], Optional[bytes]]] = None
        self.get_status_data: Optional[Callable[[], dict]] = None
        self.get_characters_list: Optional[Callable[[], list]] = None
        self.get_character_image: Optional[Callable[[str], Optional[bytes]]] = None
        self.get_activities_list: Optional[Callable[[], list]] = None
        self.get_timing_settings: Optional[Callable[[], dict]] = None
        self.get_activity_icon: Optional[Callable[[str], Optional[bytes]]] = None
        self.get_display_settings: Optional[Callable[[], dict]] = None
        self.get_running_applications: Optional[Callable[[], list]] = None
        self.get_focus_settings: Optional[Callable[[], dict]] = None
        self.get_control_settings: Optional[Callable[[], dict]] = None
        self.get_app_settings: Optional[Callable[[], dict]] = None

    def start(self, port: int = 0) -> int:
        """Start local web server on specified or ephemeral port."""
        if self.server is not None:
            return self.port

        handler_factory = lambda *args, **kwargs: SpiderWebHandler(
            *args, directory=self.directory, server_instance=self, **kwargs
        )

        self.server = ThreadedTCPServer(("127.0.0.1", port), handler_factory)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="SpiderBuddyWebServer")
        self.thread.start()
        logger.info(f"Spider-Buddy Web UI server started at http://127.0.0.1:{self.port}/ (serving {self.directory})")
        return self.port

    def get_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def stop(self) -> None:
        """Stop local web server."""
        if self.server is not None:
            logger.info("Stopping Web UI server...")
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception as e:
                logger.warning(f"Error shutting down web server: {e}")
            finally:
                self.server = None
                self.thread = None
