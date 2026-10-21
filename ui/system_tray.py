"""System tray integration for background execution and quick controls."""
import logging
from typing import Optional
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from core.character_manager import CharacterManager
from services.settings_service import get_settings

logger = logging.getLogger("SpiderBuddy.UI.SystemTray")


class SystemTrayIcon(QSystemTrayIcon):
    """System tray icon allowing Spider-Buddy to run persistently in the background."""

    show_main_window_requested = Signal()
    toggle_companion_requested = Signal()
    toggle_visibility_requested = Signal()
    quit_requested = Signal()

    def __init__(self, character_mgr: CharacterManager, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.character_mgr = character_mgr
        self.settings = get_settings()
        self._is_running = True

        self._setup_icon()
        self._setup_menu()

        self.activated.connect(self._on_activated)
        self.character_mgr.characters_discovered.connect(self._refresh_characters)
        self.character_mgr.character_changed.connect(lambda _: self._update_menu_state())
        self.settings.setting_changed.connect(lambda *_: self._update_menu_state())

    def _create_fallback_icon(self) -> QIcon:
        pix = QPixmap(32, 32)
        pix.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#E50914"))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawEllipse(2, 2, 28, 28)
        painter.end()
        return QIcon(pix)

    def _setup_icon(self) -> None:
        import sys
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
            icon_path = base / "assets" / "icons" / "tray.png"
        else:
            icon_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "tray.png"
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
        elif self.character_mgr.active_character and (self.character_mgr.active_character.root_path / "preview.png").exists():
            preview_file = str(self.character_mgr.active_character.root_path / "preview.png")
            self.setIcon(QIcon(preview_file))
        else:
            self.setIcon(self._create_fallback_icon())

        self.setToolTip("Spider-Buddy — Interactive Desktop Companion")

    def _setup_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #12121C;
                color: #FFFFFF;
                border: 1px solid #E50914;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 22px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #E50914;
                color: #FFFFFF;
            }
        """)

        # 1. Open Dashboard
        open_act = QAction("🕷️ Open Dashboard", self)
        open_act.triggered.connect(self.show_main_window_requested.emit)
        menu.addAction(open_act)

        menu.addSeparator()

        # 2. Show / Hide Character
        is_hidden = bool(self.settings.get("general.hidden", False))
        self.toggle_hide_act = QAction("👁️ Show Character" if is_hidden else "🙈 Hide Character", self)
        self.toggle_hide_act.triggered.connect(self._toggle_visibility)
        menu.addAction(self.toggle_hide_act)

        # 3. Pause / Resume Companion
        self.toggle_pause_act = QAction("⏸️ Pause Companion" if self._is_running else "▶️ Resume Companion", self)
        self.toggle_pause_act.triggered.connect(self.toggle_companion_requested.emit)
        menu.addAction(self.toggle_pause_act)

        # 4. Focus Mode (Quiet Reading in Corner)
        self.focus_mode_act = QAction("🎯 Focus Mode", self)
        self.focus_mode_act.setCheckable(True)
        self.focus_mode_act.setChecked(bool(self.settings.get("behavior.focus_mode", False)))
        self.focus_mode_act.triggered.connect(lambda checked: self.settings.set("behavior.focus_mode", checked))
        menu.addAction(self.focus_mode_act)

        menu.addSeparator()

        # 4. Display Mode Submenu
        mode_menu = menu.addMenu("🖥️ Display Mode")
        self.mode_app_act = QAction("Selected Applications", self)
        self.mode_app_act.setCheckable(True)
        self.mode_desk_act = QAction("Entire Desktop", self)
        self.mode_desk_act.setCheckable(True)

        curr_mode = self.settings.get("general.display_mode", "desktop")
        self.mode_app_act.setChecked(curr_mode == "application")
        self.mode_desk_act.setChecked(curr_mode == "desktop")

        self.mode_app_act.triggered.connect(lambda: self.settings.set("general.display_mode", "application"))
        self.mode_desk_act.triggered.connect(lambda: self.settings.set("general.display_mode", "desktop"))

        mode_menu.addAction(self.mode_app_act)
        mode_menu.addAction(self.mode_desk_act)

        # 5. Switch Character Submenu
        char_menu = menu.addMenu("🔄 Switch Character")
        self.character_menu = char_menu
        self.char_actions = {}
        for cid, profile in self.character_mgr.available_characters.items():
            act = QAction(profile.display_name, self)
            act.setCheckable(True)
            act.triggered.connect(lambda checked=False, char_id=cid: self.character_mgr.set_active_character(char_id))
            char_menu.addAction(act)
            self.char_actions[cid] = act

        # 6. Interactive FX Submenu
        fx_menu = menu.addMenu("⚡ Interactive FX")
        self.fx_dodge_act = QAction("⚡ Spider-Sense Dodging", self)
        self.fx_dodge_act.setCheckable(True)
        self.fx_dodge_act.setChecked(bool(self.settings.get("behavior.enable_spider_sense_dodging", True)))
        self.fx_dodge_act.triggered.connect(lambda checked: self.settings.set("behavior.enable_spider_sense_dodging", checked))
        fx_menu.addAction(self.fx_dodge_act)

        self.fx_bubble_act = QAction("💬 Comic Speech Bubbles", self)
        self.fx_bubble_act.setCheckable(True)
        self.fx_bubble_act.setChecked(bool(self.settings.get("behavior.enable_comic_bubbles", True)))
        self.fx_bubble_act.triggered.connect(lambda checked: self.settings.set("behavior.enable_comic_bubbles", checked))
        fx_menu.addAction(self.fx_bubble_act)

        self.fx_hotkey_act = QAction("⌨️ Quick Animation Number Keys (1..0)", self)
        self.fx_hotkey_act.setCheckable(True)
        self.fx_hotkey_act.setChecked(bool(self.settings.get("behavior.enable_animation_hotkeys", True)))
        self.fx_hotkey_act.triggered.connect(lambda checked: self.settings.set("behavior.enable_animation_hotkeys", checked))
        fx_menu.addAction(self.fx_hotkey_act)

        self.fx_eye_break_act = QAction("💧 60-Min Eye Break Web Alert", self)
        self.fx_eye_break_act.setCheckable(True)
        self.fx_eye_break_act.setChecked(bool(self.settings.get("behavior.enable_eye_break_alert", True)))
        self.fx_eye_break_act.triggered.connect(lambda checked: self.settings.set("behavior.enable_eye_break_alert", checked))
        fx_menu.addAction(self.fx_eye_break_act)

        self.fx_heavy_load_act = QAction("🏗️ Heavy Load Collapsing Beam (>85%)", self)
        self.fx_heavy_load_act.setCheckable(True)
        self.fx_heavy_load_act.setChecked(bool(self.settings.get("behavior.enable_heavy_load_scene", True)))
        self.fx_heavy_load_act.triggered.connect(lambda checked: self.settings.set("behavior.enable_heavy_load_scene", checked))
        fx_menu.addAction(self.fx_heavy_load_act)

        self.fx_audio_sync_act = QAction("🎧 Headphone Beat-Bobbing (Music / Audio)", self)
        self.fx_audio_sync_act.setCheckable(True)
        self.fx_audio_sync_act.setChecked(bool(self.settings.get("behavior.enable_audio_beat_bobbing", True)))
        self.fx_audio_sync_act.triggered.connect(lambda checked: self.settings.set("behavior.enable_audio_beat_bobbing", checked))
        fx_menu.addAction(self.fx_audio_sync_act)

        self._update_menu_state()

        menu.addSeparator()

        # 6. Exit Action
        quit_act = QAction("❌ Exit Spider-Buddy", self)
        quit_act.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_act)

        self.setContextMenu(menu)
        self._menu = menu

    def _toggle_visibility(self) -> None:
        curr = bool(self.settings.get("general.hidden", False))
        self.settings.set("general.hidden", not curr)
        self.toggle_visibility_requested.emit()

    def set_running_state(self, running: bool) -> None:
        self._is_running = running
        if hasattr(self, "toggle_pause_act"):
            self.toggle_pause_act.setText("⏸️ Pause Companion" if running else "▶️ Resume Companion")

    def _refresh_characters(self):
        self.character_menu.clear()
        self.char_actions = {}
        for cid, profile in self.character_mgr.available_characters.items():
            action = self.character_menu.addAction(profile.display_name)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, cid=cid: self.character_mgr.set_active_character(cid))
            self.char_actions[cid] = action
        self._update_menu_state()

    def _update_menu_state(self) -> None:
        curr_mode = self.settings.get("general.display_mode", "desktop")
        if hasattr(self, "mode_app_act"):
            self.mode_app_act.setChecked(curr_mode == "application")
            self.mode_desk_act.setChecked(curr_mode == "desktop")

        if hasattr(self, "char_actions") and self.character_mgr.active_character:
            active_id = self.character_mgr.active_character.id
            for cid, act in self.char_actions.items():
                act.setChecked(cid == active_id)

        if hasattr(self, "toggle_hide_act"):
            is_hidden = bool(self.settings.get("general.hidden", False))
            self.toggle_hide_act.setText("👁️ Show Character" if is_hidden else "🙈 Hide Character")

        if hasattr(self, "toggle_pause_act"):
            self.toggle_pause_act.setText("⏸️ Pause Companion" if self._is_running else "▶️ Resume Companion")

        if hasattr(self, "focus_mode_act"):
            self.focus_mode_act.setChecked(bool(self.settings.get("behavior.focus_mode", False)))

        if hasattr(self, "fx_dodge_act"):
            self.fx_dodge_act.setChecked(bool(self.settings.get("behavior.enable_spider_sense_dodging", True)))

        if hasattr(self, "fx_bubble_act"):
            self.fx_bubble_act.setChecked(bool(self.settings.get("behavior.enable_comic_bubbles", True)))

        if hasattr(self, "fx_hotkey_act"):
            self.fx_hotkey_act.setChecked(bool(self.settings.get("behavior.enable_animation_hotkeys", True)))

        if hasattr(self, "fx_eye_break_act"):
            self.fx_eye_break_act.setChecked(bool(self.settings.get("behavior.enable_eye_break_alert", True)))

        if hasattr(self, "fx_heavy_load_act"):
            self.fx_heavy_load_act.setChecked(bool(self.settings.get("behavior.enable_heavy_load_scene", True)))

        if hasattr(self, "fx_audio_sync_act"):
            self.fx_audio_sync_act.setChecked(bool(self.settings.get("behavior.enable_audio_beat_bobbing", True)))

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in [QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick]:
            self.show_main_window_requested.emit()
