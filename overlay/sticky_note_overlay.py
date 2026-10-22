"""Spider Sticky Notes & Desktop Reminders Overlay.

Provides interactive, frosted-glass floating sticky notes that hang from a
subtle spider-web strand from the top of the screen. Supports checklists,
editable notes, color themes, dragging, pinning, and persistent storage.
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger("SpiderBuddy.Overlay.StickyNotes")

THEME_PALETTES = {
    "spidey_red": {
        "name": "Classic Spidey",
        "accent": "#FF2D55",
        "border": "rgba(255, 45, 85, 0.55)",
        "bg_top": QColor(24, 10, 16, 235),
        "bg_bottom": QColor(36, 14, 24, 245),
        "text_primary": "#FFFFFF",
        "text_secondary": "rgba(255, 230, 238, 0.75)",
    },
    "miles_black": {
        "name": "Miles Shadow",
        "accent": "#E63946",
        "border": "rgba(230, 57, 70, 0.45)",
        "bg_top": QColor(14, 14, 18, 240),
        "bg_bottom": QColor(22, 16, 22, 248),
        "text_primary": "#FFFFFF",
        "text_secondary": "rgba(235, 225, 230, 0.7)",
    },
    "gwen_cyan": {
        "name": "Ghost Spider",
        "accent": "#00F5D4",
        "border": "rgba(0, 245, 212, 0.5)",
        "bg_top": QColor(10, 20, 26, 235),
        "bg_bottom": QColor(16, 28, 36, 245),
        "text_primary": "#FFFFFF",
        "text_secondary": "rgba(200, 245, 240, 0.75)",
    },
    "symbiote_purple": {
        "name": "Symbiote Pulse",
        "accent": "#A855F7",
        "border": "rgba(168, 85, 247, 0.5)",
        "bg_top": QColor(16, 12, 26, 240),
        "bg_bottom": QColor(26, 18, 42, 248),
        "text_primary": "#FFFFFF",
        "text_secondary": "rgba(230, 215, 255, 0.75)",
    },
    "spider_gold": {
        "name": "Iron Spider Gold",
        "accent": "#FFB703",
        "border": "rgba(255, 183, 3, 0.5)",
        "bg_top": QColor(24, 18, 10, 235),
        "bg_bottom": QColor(36, 26, 14, 245),
        "text_primary": "#FFFFFF",
        "text_secondary": "rgba(255, 240, 215, 0.75)",
    },
}


class SpiderStickyNoteWindow(QWidget):
    """Native floating translucent desktop sticky note window with web string anchor."""

    note_updated = Signal(dict)
    note_deleted = Signal(str)

    def __init__(self, note_data: dict, parent: Optional[QWidget] = None):
        super().__init__(
            parent,
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.SubWindow
            | (Qt.WindowStaysOnTopHint if note_data.get("pinned", True) else Qt.Widget),
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)

        self.note_data = dict(note_data)
        self.note_id = self.note_data.get("id") or f"note_{int(time.time()*1000)}"
        self.note_data["id"] = self.note_id

        self._color_key = self.note_data.get("color", "spidey_red")
        if self._color_key not in THEME_PALETTES:
            self._color_key = "spidey_red"

        self._minimized = bool(self.note_data.get("minimized", False))
        self._dragging = False
        self._drag_start_pos = QPoint()
        self._save_debounce_timer = QTimer(self)
        self._save_debounce_timer.setSingleShot(True)
        self._save_debounce_timer.setInterval(400)
        self._save_debounce_timer.timeout.connect(self._emit_update)

        self._setup_ui()
        self._apply_geometry()

    @property
    def palette(self) -> dict:
        return THEME_PALETTES.get(self._color_key, THEME_PALETTES["spidey_red"])

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 24, 10, 10)  # Top room for web anchor
        self.main_layout.setSpacing(0)

        # Card container
        self.card = QFrame(self)
        self.card.setObjectName("cardFrame")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(14, 12, 14, 14)
        self.card_layout.setSpacing(10)

        # --- Top Header Bar ---
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(6)

        # Spider icon badge
        self.icon_badge = QLabel("🕷️", self.card)
        self.icon_badge.setStyleSheet("font-size: 13px; background: transparent;")
        self.header_layout.addWidget(self.icon_badge)

        # Title Edit
        self.title_edit = QLineEdit(self.note_data.get("title", "Spider Note"), self.card)
        self.title_edit.setStyleSheet(
            f"font-size: 13.5px; font-weight: 700; color: {self.palette['text_primary']}; "
            "background: transparent; border: none; padding: 2px 4px; border-radius: 4px;"
        )
        self.title_edit.textChanged.connect(self._on_title_changed)
        self.header_layout.addWidget(self.title_edit, 1)

        # Color dot cycle button
        self.btn_color = QPushButton(self.card)
        self.btn_color.setFixedSize(16, 16)
        self.btn_color.setCursor(Qt.PointingHandCursor)
        self.btn_color.setToolTip("Change Note Theme")
        self._update_color_button_style()
        self.btn_color.clicked.connect(self._cycle_color)
        self.header_layout.addWidget(self.btn_color)

        # Pin button
        is_pinned = self.note_data.get("pinned", True)
        self.btn_pin = QPushButton("📌" if is_pinned else "📍", self.card)
        self.btn_pin.setFixedSize(22, 22)
        self.btn_pin.setCursor(Qt.PointingHandCursor)
        self.btn_pin.setToolTip("Toggle Always on Top" if is_pinned else "Pin on Top")
        self.btn_pin.setStyleSheet(
            "background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); "
            "border-radius: 6px; font-size: 11px; color: #fff; padding: 0;"
        )
        self.btn_pin.clicked.connect(self._toggle_pin)
        self.header_layout.addWidget(self.btn_pin)

        # Fold / Minimize button
        self.btn_fold = QPushButton("—", self.card)
        self.btn_fold.setFixedSize(22, 22)
        self.btn_fold.setCursor(Qt.PointingHandCursor)
        self.btn_fold.setToolTip("Fold / Minimize Note")
        self.btn_fold.setStyleSheet(
            "background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); "
            "border-radius: 6px; font-size: 12px; font-weight: bold; color: #fff; padding: 0;"
        )
        self.btn_fold.clicked.connect(self._toggle_minimize)
        self.header_layout.addWidget(self.btn_fold)

        # Close button
        self.btn_close = QPushButton("✕", self.card)
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setToolTip("Close / Delete Note")
        self.btn_close.setStyleSheet(
            "background: rgba(255, 45, 85, 0.15); border: 1px solid rgba(255, 45, 85, 0.35); "
            "border-radius: 6px; font-size: 10px; font-weight: bold; color: #FF2D55; padding: 0;"
        )
        self.btn_close.clicked.connect(self._close_note)
        self.header_layout.addWidget(self.btn_close)

        self.card_layout.addLayout(self.header_layout)

        # --- Content Container (Hidden when minimized) ---
        self.body_container = QWidget(self.card)
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(10)

        # To-Do Items Checklist ScrollArea
        self.tasks_scroll = QScrollArea(self.body_container)
        self.tasks_scroll.setWidgetResizable(True)
        self.tasks_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; } "
            "QScrollBar:vertical { width: 4px; background: rgba(0,0,0,0.1); border-radius: 2px; } "
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.25); border-radius: 2px; }"
        )
        self.tasks_widget = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_widget)
        self.tasks_layout.setContentsMargins(0, 2, 0, 2)
        self.tasks_layout.setSpacing(6)
        self.tasks_scroll.setWidget(self.tasks_widget)
        self.body_layout.addWidget(self.tasks_scroll)

        self._populate_tasks()

        # Add Task Input Row
        self.add_task_layout = QHBoxLayout()
        self.add_task_layout.setContentsMargins(0, 0, 0, 0)
        self.add_task_layout.setSpacing(6)

        self.task_input = QLineEdit(self.body_container)
        self.task_input.setPlaceholderText("+ Add task, press Enter...")
        self.task_input.setStyleSheet(
            f"font-size: 12px; color: #ffffff; background: rgba(255, 255, 255, 0.08); "
            f"border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 8px; padding: 5px 10px;"
        )
        self.task_input.returnPressed.connect(self._add_task)
        self.add_task_layout.addWidget(self.task_input)

        self.body_layout.addLayout(self.add_task_layout)

        # Free-form Note Text
        self.content_edit = QTextEdit(self.body_container)
        self.content_edit.setPlaceholderText("Write notes, web formulas, mission briefings...")
        self.content_edit.setPlainText(self.note_data.get("content", ""))
        self.content_edit.setStyleSheet(
            f"font-size: 12.5px; line-height: 1.4; color: {self.palette['text_secondary']}; "
            "background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(255, 255, 255, 0.08); "
            "border-radius: 8px; padding: 6px 8px;"
        )
        self.content_edit.textChanged.connect(self._on_content_changed)
        self.content_edit.setMaximumHeight(90)
        self.body_layout.addWidget(self.content_edit)

        self.card_layout.addWidget(self.body_container)
        self.main_layout.addWidget(self.card)

        self._update_card_style()
        if self._minimized:
            self.body_container.hide()

    def _update_color_button_style(self):
        self.btn_color.setStyleSheet(
            f"background: {self.palette['accent']}; border: 1.5px solid #ffffff; "
            f"border-radius: 8px; box-shadow: 0 0 8px {self.palette['accent']};"
        )

    def _update_card_style(self):
        self.card.setStyleSheet(
            f"#cardFrame {{"
            f"  background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {self.palette['bg_top'].name()}, stop:1 {self.palette['bg_bottom'].name()});"
            f"  border: 1.5px solid {self.palette['border']};"
            f"  border-top: 1.5px solid rgba(255, 255, 255, 0.4);"
            f"  border-radius: 18px;"
            f"}}"
        )

    def _populate_tasks(self):
        # Clear existing
        while self.tasks_layout.count():
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = self.note_data.get("items", [])
        for task in items:
            self._create_task_row(task)

    def _create_task_row(self, task: dict):
        row = QWidget(self.tasks_widget)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        chk = QCheckBox(task.get("text", ""), row)
        chk.setChecked(bool(task.get("done", False)))
        strike = "text-decoration: line-through; color: rgba(255, 255, 255, 0.4);"
        normal = f"color: {self.palette['text_primary']}; font-weight: 500;"
        chk.setStyleSheet(
            f"QCheckBox {{ font-size: 12px; {strike if chk.isChecked() else normal} }} "
            f"QCheckBox::indicator {{ width: 15px; height: 15px; border-radius: 4px; "
            f"border: 1.5px solid {self.palette['accent']}; background: rgba(0,0,0,0.3); }} "
            f"QCheckBox::indicator:checked {{ background: {self.palette['accent']}; image: none; }}"
        )

        def on_toggle(checked):
            task["done"] = bool(checked)
            chk.setStyleSheet(
                f"QCheckBox {{ font-size: 12px; {strike if checked else normal} }} "
                f"QCheckBox::indicator {{ width: 15px; height: 15px; border-radius: 4px; "
                f"border: 1.5px solid {self.palette['accent']}; background: rgba(0,0,0,0.3); }} "
                f"QCheckBox::indicator:checked {{ background: {self.palette['accent']}; }}"
            )
            self._schedule_save()

        chk.toggled.connect(on_toggle)
        row_layout.addWidget(chk, 1)

        # Remove single task button
        btn_del = QPushButton("×", row)
        btn_del.setFixedSize(16, 16)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet(
            "background: transparent; color: rgba(255, 255, 255, 0.35); border: none; font-size: 13px;"
        )

        def del_task():
            items = self.note_data.get("items", [])
            if task in items:
                items.remove(task)
            row.deleteLater()
            self._schedule_save()

        btn_del.clicked.connect(del_task)
        row_layout.addWidget(btn_del)

        self.tasks_layout.addWidget(row)

    def _add_task(self):
        text = self.task_input.text().strip()
        if not text:
            return
        new_task = {"id": f"task_{int(time.time()*1000)}", "text": text, "done": False}
        if "items" not in self.note_data or not isinstance(self.note_data["items"], list):
            self.note_data["items"] = []
        self.note_data["items"].append(new_task)
        self._create_task_row(new_task)
        self.task_input.clear()
        self._schedule_save()

    def _cycle_color(self):
        keys = list(THEME_PALETTES.keys())
        idx = (keys.index(self._color_key) + 1) % len(keys)
        self._color_key = keys[idx]
        self.note_data["color"] = self._color_key
        self._update_card_style()
        self._update_color_button_style()
        self.update()  # Redraw web strand
        self._schedule_save()

    def _toggle_pin(self):
        is_pinned = not bool(self.note_data.get("pinned", True))
        self.note_data["pinned"] = is_pinned
        self.btn_pin.setText("📌" if is_pinned else "📍")
        self.btn_pin.setToolTip("Always on Top: ON" if is_pinned else "Always on Top: OFF")

        # Re-apply window flags
        pos = self.pos()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, is_pinned)
        self.show()
        self.move(pos)
        self._schedule_save()

    def _toggle_minimize(self):
        self._minimized = not self._minimized
        self.note_data["minimized"] = self._minimized
        if self._minimized:
            self.body_container.hide()
            self.btn_fold.setText("+")
            self.btn_fold.setToolTip("Unfold Note")
            self.resize(self.width(), 65)
        else:
            self.body_container.show()
            self.btn_fold.setText("—")
            self.btn_fold.setToolTip("Fold Note")
            self.resize(self.width(), int(self.note_data.get("height", 320)))
        self.update()
        self._schedule_save()

    def _close_note(self):
        self.note_data["desktop_visible"] = False
        self.hide()
        self.note_deleted.emit(self.note_id)

    def _on_title_changed(self, text: str):
        self.note_data["title"] = text
        self._schedule_save()

    def _on_content_changed(self):
        self.note_data["content"] = self.content_edit.toPlainText()
        self._schedule_save()

    def _apply_geometry(self):
        x = int(self.note_data.get("pos_x", 350))
        y = int(self.note_data.get("pos_y", 80))
        w = int(self.note_data.get("width", 280))
        h = int(self.note_data.get("height", 320))
        self.setGeometry(x, y, w, h if not self._minimized else 65)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.LeftButton):
            new_pos = event.globalPosition().toPoint() - self._drag_start_pos
            # Bound Y so note stays below ceiling with room for web strand
            new_pos.setY(max(20, new_pos.y()))
            self.move(new_pos)
            self.note_data["pos_x"] = new_pos.x()
            self.note_data["pos_y"] = new_pos.y()
            self.update()  # Repaint web strand
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._schedule_save()
            event.accept()

    def _schedule_save(self):
        self._save_debounce_timer.start()

    def _emit_update(self):
        self.note_data["pos_x"] = self.x()
        self.note_data["pos_y"] = self.y()
        self.note_data["width"] = self.width()
        if not self._minimized:
            self.note_data["height"] = self.height()
        self.note_updated.emit(self.note_data)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the hanging Spider-Web Strand from ceiling to note top
        # Coordinates relative to this widget
        center_x = self.width() / 2.0
        anchor_y = 24.0  # Center of hanger ring

        # Top web strand
        pen = QPen(QColor(245, 248, 255, 220), 1.6)
        painter.setPen(pen)
        painter.drawLine(QPointF(center_x, 0), QPointF(center_x, anchor_y))

        # Web knot node ring
        painter.setBrush(QBrush(QColor(self.palette["accent"])))
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1.2))
        painter.drawEllipse(QPointF(center_x, anchor_y), 4.5, 4.5)


class StickyNotesManager(QWidget):
    """Manager orchestrating all desktop floating sticky note overlays."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notes_windows: Dict[str, SpiderStickyNoteWindow] = {}
        self._enabled = True
        try:
            from services.settings_service import get_settings
            self._enabled = bool(get_settings().get("behavior.enable_sticky_notes", True))
        except Exception:
            self._enabled = True
        self._sync_debounce = QTimer(self)
        self._sync_debounce.setSingleShot(True)
        self._sync_debounce.setInterval(300)
        self._sync_debounce.timeout.connect(self._save_to_disk)
        self.load_notes()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable desktop sticky notes display."""
        self._enabled = bool(enabled)
        for w in self.notes_windows.values():
            if self._enabled:
                if w.note_data.get("desktop_visible", True):
                    w.show()
            else:
                w.hide()

    def is_enabled(self) -> bool:
        return self._enabled

    def _get_storage_path(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        config_dir = root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "sticky_notes.json"

    def load_notes(self):
        file_path = self._get_storage_path()
        if not file_path.exists():
            return
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for note in data:
                    if note.get("desktop_visible", True):
                        self.show_or_create_window(note)
        except Exception as e:
            logger.warning(f"Error loading sticky notes for overlay: {e}")

    def show_or_create_window(self, note: dict) -> SpiderStickyNoteWindow:
        nid = note.get("id")
        if nid in self.notes_windows:
            w = self.notes_windows[nid]
            w.note_data = dict(note)
            if self._enabled and note.get("desktop_visible", True):
                w.show()
                w.raise_()
            else:
                w.hide()
            return w

        w = SpiderStickyNoteWindow(note)
        w.note_updated.connect(self._on_note_window_updated)
        w.note_deleted.connect(self._on_note_window_deleted)
        self.notes_windows[nid] = w
        if self._enabled and note.get("desktop_visible", True):
            w.show()
        else:
            w.hide()
        return w

    def create_new_note(self, title: str = "Spider Note", color: str = "spidey_red", pos: Optional[QPoint] = None) -> SpiderStickyNoteWindow:
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        nid = f"note_{int(time.time()*1000)}"
        px = pos.x() if pos else 360 + (len(self.notes_windows) % 4) * 40
        py = pos.y() if pos else 80 + (len(self.notes_windows) % 3) * 30
        new_note = {
            "id": nid,
            "title": title,
            "color": color,
            "content": "",
            "items": [],
            "pinned": True,
            "desktop_visible": True,
            "pos_x": max(40, px),
            "pos_y": max(40, py),
            "width": 280,
            "height": 320,
            "minimized": False,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        win = self.show_or_create_window(new_note)
        self._schedule_disk_save()
        return win

    def toggle_all_visibility(self):
        all_visible = any(w.isVisible() for w in self.notes_windows.values())
        for w in self.notes_windows.values():
            if all_visible:
                w.hide()
            else:
                w.show()

    def _on_note_window_updated(self, note_data: dict):
        self._schedule_disk_save()

    def _on_note_window_deleted(self, note_id: str):
        if note_id in self.notes_windows:
            w = self.notes_windows.pop(note_id)
            w.deleteLater()
        self._schedule_disk_save()

    def _schedule_disk_save(self):
        self._sync_debounce.start()

    def _save_to_disk(self):
        file_path = self._get_storage_path()
        notes_list = []
        # Combine existing disk notes with active memory notes
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    notes_list = data
            except Exception:
                pass

        mem_map = {w.note_id: w.note_data for w in self.notes_windows.values()}
        merged = []
        for disk_n in notes_list:
            nid = disk_n.get("id")
            if nid in mem_map:
                merged.append(mem_map.pop(nid))
            else:
                merged.append(disk_n)
        for leftover in mem_map.values():
            merged.append(leftover)

        file_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")

    def handle_external_sync(self, event_data: dict):
        subaction = event_data.get("subaction")
        if subaction == "create":
            note = event_data.get("note")
            if note and note.get("desktop_visible", True):
                self.show_or_create_window(note)
        elif subaction == "update":
            note = event_data.get("note")
            if note:
                nid = note.get("id")
                if nid in self.notes_windows:
                    w = self.notes_windows[nid]
                    w.note_data.update(note)
                    w.title_edit.setText(note.get("title", ""))
                    w.content_edit.setPlainText(note.get("content", ""))
                    w._populate_tasks()
        elif subaction == "delete":
            nid = event_data.get("id")
            if nid in self.notes_windows:
                w = self.notes_windows.pop(nid)
                w.hide()
                w.deleteLater()
        elif subaction == "toggle_desktop":
            note = event_data.get("note")
            if note:
                nid = note.get("id")
                if note.get("desktop_visible", True):
                    self.show_or_create_window(note)
                elif nid in self.notes_windows:
                    w = self.notes_windows.pop(nid)
                    w.hide()
                    w.deleteLater()
        elif subaction == "reload":
            self.load_notes()
