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

        # 7. Main HTML entry point & SPA deep link navigation fallback
        clean_path = self.path.split("?")[0].rstrip("/")
        SPA_ROUTES = {
            "", "/index", "/index.html", "/home", "/characters", "/activities",
            "/desktop", "/desktop-apps", "/desktop_apps", "/focus",
            "/focus-breaks", "/focus_breaks", "/controls", "/settings"
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

    def log_message(self, format, *args):
        # Suppress routine GET logging unless in DEBUG mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"{self.address_string()} - {format % args}")


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


from PySide6.QtCore import QObject, Signal

class WebServer(QObject):
    """Manages the background HTTP server for Framer UI with thread-safe Qt signals."""

    action_received = Signal(dict)

    def __init__(self, directory: Optional[str] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        if directory is None:
            # Default to BIN/Frammer UI in project root or frozen MEIPASS
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                directory = str(Path(sys._MEIPASS) / "BIN" / "Frammer UI")
            else:
                root = Path(__file__).resolve().parent.parent
                directory = str(root / "BIN" / "Frammer UI")

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
