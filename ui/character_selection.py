"""Character selection card widgets with '+' option to add new characters."""
import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QPixmap, QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QDialog,
    QLineEdit,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QMessageBox,
    QSizePolicy,
    QScrollArea,
    QProgressBar,
)

from core.character_manager import CharacterManager, CharacterProfile

logger = logging.getLogger("SpiderBuddy.UI.CharacterSelection")


from services.character_import import create_character


class ImportWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)
    progress = Signal(int, str)

    def __init__(self, arguments, parent=None):
        super().__init__(parent)
        self.arguments = arguments

    def run(self):
        try:
            self.arguments["progress_callback"] = lambda pct, msg: self.progress.emit(pct, msg)
            result = create_character(**self.arguments)
            self.succeeded.emit(result.name)
        except Exception as exc:
            logger.exception('Character import failed')
            self.failed.emit(str(exc))


class CharacterCard(QFrame):
    """Interactive card displaying a Spider-Man character in a uniform 3x3 grid."""

    selected = Signal(str)

    def __init__(self, profile: CharacterProfile, is_selected: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.profile = profile
        self.is_selected = is_selected

        self.setMinimumSize(160, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("CharacterCard")
        self.init_ui()
        self.update_style()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)

        # Character Image Preview Container
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(100, 120)
        self.preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setObjectName('characterPreview')

        preview_path = self.profile.root_path / "preview.png"
        if not preview_path.exists():
            preview_path = self.profile.sprites_path / "idle.png"

        if preview_path.exists():
            self._preview_source = QPixmap(str(preview_path))
            self.preview_label.setPixmap(self._preview_source.scaled(124,120,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        else:
            self.preview_label.setText("🕷️\nNo Preview")
            self.preview_label.setStyleSheet("color: #888888; font-size: 14px;")

        layout.addWidget(self.preview_label, 1)

        # Character Name
        self.name_label = QLabel(self.profile.display_name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)

        # Suit Description
        self.suit_label = QLabel(self.profile.suit)
        self.suit_label.setAlignment(Qt.AlignCenter)
        self.suit_label.setWordWrap(True)
        self.suit_label.setMinimumHeight(32)
        self.suit_label.setObjectName("muted")
        layout.addWidget(self.suit_label)

        # Select Button
        self.select_btn = QPushButton("SELECT")
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.clicked.connect(self._on_clicked)
        layout.addWidget(self.select_btn)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        self.update_style()

    def update_style(self) -> None:
        self.setProperty('selected', self.is_selected)
        self.select_btn.setText('Selected' if self.is_selected else 'Select')
        self.select_btn.setProperty('primary', self.is_selected)
        self.select_btn.style().unpolish(self.select_btn)
        self.select_btn.style().polish(self.select_btn)
        self.style().unpolish(self)
        self.style().polish(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_preview_source'):
            size = self.preview_label.size()
            self.preview_label.setPixmap(self._preview_source.scaled(
                max(80,size.width()-16), max(90,size.height()-16), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._on_clicked()
        super().mousePressEvent(event)

    def _on_clicked(self) -> None:
        self.selected.emit(self.profile.id)


class AddCharacterCard(QFrame):
    """Card with a '+' option to import or create a new Spider-Man character in the 3x3 grid."""

    add_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(160, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("AddCharacterCard")
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)

        # Big stylized '+' icon
        self.icon_label = QLabel("+")
        self.icon_label.setFixedSize(140, 130)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet(
            "font-size: 58px; font-weight: 300; color: #E50914; "
            "border: 2px dashed #3D4457; border-radius: 10px; background: rgba(229, 9, 20, 0.05);"
        )
        layout.addWidget(self.icon_label, 0, Qt.AlignCenter)

        # Title
        self.title_label = QLabel("Add Character")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(self.title_label)

        # Description
        self.desc_label = QLabel("Import or create custom companion")
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setMinimumHeight(32)
        self.desc_label.setObjectName("muted")
        layout.addWidget(self.desc_label)

        # Add Button
        self.add_btn = QPushButton("+ CREATE")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setStyleSheet(
            "background: rgba(229, 9, 20, 0.15); color: #E50914; font-weight: bold; border: 1px solid #E50914; border-radius: 6px; padding: 7px 14px;"
        )
        self.add_btn.clicked.connect(self.add_requested.emit)
        layout.addWidget(self.add_btn)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.add_requested.emit()
        super().mousePressEvent(event)


class AddCharacterDialog(QDialog):
    """Modal dialog allowing users to create or import a new character with Apple design system."""

    def __init__(self, character_mgr: Optional[CharacterManager] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.character_mgr = character_mgr or CharacterManager()
        self.setWindowTitle("Add New Companion — Spider-Buddy")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.init_ui()
        self.apply_apple_theme()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Add New Companion")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        subtitle = QLabel("Create a new Spider-Man companion by cloning an existing template or importing custom artwork.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("dialogSubtitle")
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(12)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Spider-Gwen")
        form.addRow("Character Name:", self.name_edit)

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("e.g. spider_gwen (letters, numbers, underscores)")
        form.addRow("Identifier (ID):", self.id_edit)

        self.suit_edit = QLineEdit()
        self.suit_edit.setPlaceholderText("e.g. Ghost-Spider Hooded Suit")
        form.addRow("Suit Description:", self.suit_edit)

        # Dynamic template selector from available characters
        self.template_combo = QComboBox()
        avail = getattr(self.character_mgr, "available_characters", {})
        if avail:
            for cid, prof in avail.items():
                self.template_combo.addItem(f"{prof.display_name} ({prof.suit})", cid)
        else:
            self.template_combo.addItem("Miles Morales (Classic Black & Red)", "miles_morales")
            self.template_combo.addItem("Tom Holland (Integrated Stark Suit)", "tom_holland")
        form.addRow("Base Template:", self.template_combo)

        # Optional artwork
        img_row = QHBoxLayout()
        self.img_edit = QLineEdit()
        self.img_edit.setPlaceholderText("Optional full-body artwork (.png/.webp)")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_image)
        img_row.addWidget(self.img_edit)
        img_row.addWidget(browse_btn)
        form.addRow("Custom Artwork:", img_row)

        layout.addLayout(form)

        note = QLabel("Tip: If artwork is left empty, the base template character is cloned instantly.")
        note.setStyleSheet("font-size: 11px; color: #71717a; margin-top: 2px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        # Progress bar container (active during generation)
        self.progress_container = QWidget()
        prog_layout = QVBoxLayout(self.progress_container)
        prog_layout.setContentsMargins(0, 4, 0, 0)
        self.progress_label = QLabel("Building companion animations...")
        self.progress_label.setStyleSheet("font-size: 11.5px; color: #a1a1aa;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        prog_layout.addWidget(self.progress_label)
        prog_layout.addWidget(self.progress_bar)
        self.progress_container.setVisible(False)
        layout.addWidget(self.progress_container)

        self.name_edit.textChanged.connect(self._auto_fill_id)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.create_btn = QPushButton("Create Character")
        self.create_btn.setObjectName("createBtn")
        self.create_btn.setDefault(True)
        self.create_btn.clicked.connect(self._create_character)
        btn_row.addWidget(self.create_btn)

        layout.addLayout(btn_row)

    def apply_apple_theme(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #f1f5f9;
                font-family: -apple-system, "SF Pro Display", "Segoe UI", sans-serif;
            }
            QLabel#dialogTitle {
                font-size: 19px;
                font-weight: 700;
                color: #FF2D55;
            }
            QLabel#dialogSubtitle {
                font-size: 12px;
                color: #94a3b8;
                margin-bottom: 4px;
            }
            QLabel {
                font-size: 12.5px;
                color: #e2e8f0;
                font-weight: 500;
            }
            QLineEdit, QComboBox {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 8px;
                padding: 7px 12px;
                color: #ffffff;
                font-size: 12.5px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #FF2D55;
                background: rgba(255, 45, 85, 0.05);
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #121727;
                border: 1px solid rgba(255, 255, 255, 0.15);
                color: #ffffff;
                selection-background-color: #FF2D55;
            }
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                color: #f1f5f9;
                padding: 8px 18px;
                border-radius: 9999px;
                font-weight: 600;
                font-size: 12.5px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.14);
            }
            QPushButton#createBtn {
                background: #FF2D55;
                border: none;
                color: #ffffff;
            }
            QPushButton#createBtn:hover {
                background: #ff4569;
            }
            QProgressBar {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                height: 14px;
                text-align: center;
                color: #ffffff;
                font-size: 10px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF2D55, stop:1 #ff6482);
                border-radius: 5px;
            }
        """)

    def _auto_fill_id(self, text: str) -> None:
        if not self.id_edit.isModified():
            clean_id = re.sub(r"[^a-zA-Z0-9_]", "", text.strip().lower().replace(" ", "_").replace("-", "_"))
            self.id_edit.setText(clean_id)
            self.id_edit.setModified(False)

    def _browse_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Character Preview Image", "", "Image Files (*.png *.webp *.jpg)"
        )
        if file_path:
            self.img_edit.setText(file_path)

    def _create_character(self) -> None:
        name = self.name_edit.text().strip()
        cid = self.id_edit.text().strip().lower()
        suit = self.suit_edit.text().strip() or f"{name} Suit"
        template_id = self.template_combo.currentData()
        custom_img = self.img_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a character name.")
            return

        if not cid or not re.match(r"^[a-z0-9_]+$", cid):
            QMessageBox.warning(self, "Invalid ID", "Identifier must only contain lowercase letters, numbers, and underscores.")
            return

        avail = getattr(self.character_mgr, "available_characters", {})
        if cid in avail:
            QMessageBox.warning(self, "Character Exists", f"A character with ID '{cid}' already exists.")
            return

        if custom_img and not Path(custom_img).is_file():
            QMessageBox.warning(self, 'Artwork not found', 'Select an existing image file.')
            return

        template_profile = avail.get(template_id)
        if not template_profile:
            for prof in avail.values():
                template_profile = prof
                break

        if not template_profile or not hasattr(template_profile, 'root_path') or not template_profile.root_path.exists():
            QMessageBox.warning(self, "Template Error", "No valid base template character could be found.")
            return

        self.create_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_container.setVisible(True)
        self.progress_bar.setValue(5)
        self.progress_label.setText("Starting character creation...")

        dest_root = getattr(self.character_mgr, 'characters_root', Path('characters'))
        self.worker = ImportWorker(dict(
            destination_root=dest_root,
            template_root=template_profile.root_path,
            cid=cid, name=name, suit=suit, artwork=custom_img or None
        ), self)
        self.worker.progress.connect(self._on_progress)
        self.worker.succeeded.connect(self._import_succeeded)
        self.worker.failed.connect(self._import_failed)
        self.worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.progress_label.setText(msg)

    def _import_succeeded(self, cid):
        self.worker.wait()
        self.created_character_id = cid
        self.accept()

    def _import_failed(self, message):
        self.worker.wait()
        self.create_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.progress_container.setVisible(False)
        QMessageBox.warning(self, 'Could not import character', message)

    def reject(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            return
        super().reject()

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            event.ignore()
        else:
            super().closeEvent(event)


class CharacterSelectionWidget(QWidget):
    """Container managing Spider-Man character cards in a uniform 3-column / 3x3 grid."""

    character_selected = Signal(str)

    def __init__(self, character_mgr: CharacterManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.character_mgr = character_mgr
        self.cards: dict[str, CharacterCard] = {}
        self.add_card: Optional[AddCharacterCard] = None

        self.card_grid = QGridLayout(self)
        self.card_grid.setContentsMargins(4, 4, 4, 16)
        self.card_grid.setHorizontalSpacing(16)
        self.card_grid.setVerticalSpacing(18)
        self.card_grid.setAlignment(Qt.AlignTop)

        self.refresh_cards()
        self.character_mgr.character_changed.connect(self._on_active_character_changed)

    def refresh_cards(self) -> None:
        """Clear and rebuild all character cards in a uniform 3-column grid (3x3 layout)."""
        # Remove existing widgets
        while self.card_grid.count():
            item = self.card_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.cards.clear()
        active_id = self.character_mgr.active_character.id if self.character_mgr.active_character else ""

        # Populate cards for all discovered characters in 3 columns
        COLS = 3
        slot = 0
        for char_id, profile in self.character_mgr.available_characters.items():
            card = CharacterCard(profile, is_selected=(char_id == active_id))
            card.selected.connect(self._select_character)
            self.cards[char_id] = card
            row = slot // COLS
            col = slot % COLS
            self.card_grid.addWidget(card, row, col)
            slot += 1

        # Add the '+' Add Character card at the next slot
        self.add_card = AddCharacterCard(self)
        self.add_card.add_requested.connect(self._open_add_dialog)
        row = slot // COLS
        col = slot % COLS
        self.card_grid.addWidget(self.add_card, row, col)
        self._reflow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self):
        cards = list(self.cards.values()) + ([self.add_card] if self.add_card else [])
        w = self.width()
        win = self.window()
        if win and hasattr(win, "pages") and win.pages:
            pw = win.pages.width() - 32
            if pw > 100:
                w = pw
        columns = min(3, max(1, (max(1, w) - 8 + 16) // 196))
        if w > 0:
            self.setFixedWidth(w)
        for card in cards:
            self.card_grid.removeWidget(card)
        for column in range(3):
            self.card_grid.setColumnStretch(column, 1 if column < columns else 0)
            self.card_grid.setColumnMinimumWidth(column, 0)
        width = max(160, (w - 8 - 16 * (columns - 1)) // columns)
        ancestor = self.parentWidget()
        while ancestor is not None and not isinstance(ancestor, QScrollArea):
            ancestor = ancestor.parentWidget()
        rows = max(1, (len(cards) + columns - 1) // columns)
        fit_height = ((ancestor.viewport().height() - 140 - 18 * (rows - 1)) // rows) if ancestor else 380
        for index, card in enumerate(cards):
            card_h = max(260, min(380, round(width * 1.25), fit_height))
            card.setFixedHeight(card_h)
            col = index % columns
            row = index // columns
            card.setGeometry(4 + col * (width + 16), 4 + row * (card_h + 16), width, card_h)
            self.card_grid.addWidget(card, row, col)

    def _select_character(self, char_id: str) -> None:
        self.character_mgr.set_active_character(char_id)
        self.character_selected.emit(char_id)

    def _on_active_character_changed(self, profile: CharacterProfile) -> None:
        for cid, card in self.cards.items():
            card.set_selected(cid == profile.id)

    def _open_add_dialog(self) -> None:
        dialog = AddCharacterDialog(self.character_mgr, self)
        if dialog.exec() == QDialog.Accepted and hasattr(dialog, "created_character_id"):
            cid = dialog.created_character_id
            self.character_mgr.discover_characters()
            self.refresh_cards()
            self._select_character(cid)
