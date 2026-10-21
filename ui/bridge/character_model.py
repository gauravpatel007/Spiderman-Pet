"""Character model providing reactive QAbstractListModel to Qt Quick / QML."""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, QByteArray, Slot, Property, Signal, QObject
from services.settings_service import get_settings

logger = logging.getLogger("SpiderBuddy.Bridge.Character")


class CharacterModel(QAbstractListModel):
    """QAbstractListModel exposing discovered Spider-Man characters to QML."""

    IdRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    DisplayNameRole = Qt.UserRole + 3
    SuitRole = Qt.UserRole + 4
    DescriptionRole = Qt.UserRole + 5
    ScaleRole = Qt.UserRole + 6
    PreviewRole = Qt.UserRole + 7
    IsActiveRole = Qt.UserRole + 8

    activeCharacterChanged = Signal(str)
    scaleChanged = Signal(float)
    opacityChanged = Signal(float)
    importProgress = Signal(int, str)
    importFinished = Signal(bool, str)

    def __init__(self, character_manager: Optional[Any] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._mgr = character_manager
        self._settings = get_settings()
        self._characters: List[Dict[str, Any]] = []
        self._active_id = str(self._settings.get("general.character", "miles_morales"))

        if self._mgr:
            self._mgr.character_changed.connect(self._on_mgr_character_changed)

        self.reloadCharacters()

    def roleNames(self) -> Dict[int, QByteArray]:
        return {
            self.IdRole: QByteArray(b"charId"),
            self.NameRole: QByteArray(b"name"),
            self.DisplayNameRole: QByteArray(b"displayName"),
            self.SuitRole: QByteArray(b"suit"),
            self.DescriptionRole: QByteArray(b"description"),
            self.ScaleRole: QByteArray(b"scaleFactor"),
            self.PreviewRole: QByteArray(b"previewUrl"),
            self.IsActiveRole: QByteArray(b"isActive")
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._characters)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._characters)):
            return None

        char = self._characters[index.row()]
        if role == self.IdRole:
            return char["id"]
        elif role == self.NameRole:
            return char["name"]
        elif role == self.DisplayNameRole:
            return char["display_name"]
        elif role == self.SuitRole:
            return char["suit"]
        elif role == self.DescriptionRole:
            return char["description"]
        elif role == self.ScaleRole:
            return char["scale"]
        elif role == self.PreviewRole:
            return char["preview_url"]
        elif role == self.IsActiveRole:
            return char["id"] == self._active_id
        return None

    def _on_mgr_character_changed(self, profile: Any):
        if hasattr(profile, "id"):
            self.setActiveCharacter(profile.id)

    @Slot()
    def reloadCharacters(self):
        """Scans characters directory to populate available companions."""
        self.beginResetModel()
        self._characters.clear()

        # Discover root path
        from core.character_manager import CharacterManager
        mgr = self._mgr or CharacterManager()
        if hasattr(mgr, "available_characters") and isinstance(mgr.available_characters, dict):
            profiles = list(mgr.available_characters.values())
        elif hasattr(mgr, "get_available_characters"):
            profiles = mgr.get_available_characters()
        else:
            profiles = []

        for p in profiles:
            preview_file = p.root_path / "preview.png"
            if not preview_file.exists():
                preview_file = p.root_path / "animations" / "idle" / "frame_00.png"
            if not preview_file.exists():
                preview_file = p.root_path / "animations" / "perch" / "frame_00.png"

            preview_url = preview_file.as_uri() if preview_file.exists() else ""
            self._characters.append({
                "id": p.id,
                "name": p.name,
                "display_name": p.display_name,
                "suit": p.suit,
                "description": p.description,
                "scale": p.scale_factor,
                "preview_url": preview_url,
                "profile": p
            })

        self.endResetModel()

    # --- Properties ---

    def _get_active_id(self) -> str:
        return self._active_id

    @Slot(str)
    def setActiveCharacter(self, char_id: str):
        if self._active_id != char_id:
            self._active_id = char_id
            self._settings.set("general.character", char_id)
            if self._mgr and hasattr(self._mgr, "set_active_character"):
                self._mgr.set_active_character(char_id)
            self.activeCharacterChanged.emit(char_id)
            # Notify data changed for all items so isActive updates
            if self._characters:
                top_left = self.index(0, 0)
                bottom_right = self.index(len(self._characters) - 1, 0)
                self.dataChanged.emit(top_left, bottom_right, [self.IsActiveRole])

    activeCharacterId = Property(str, _get_active_id, setActiveCharacter, notify=activeCharacterChanged)

    def _get_scale(self) -> float:
        return float(self._settings.get("general.scale", 1.0))

    def _set_scale(self, val: float):
        clamped = max(0.5, min(2.5, round(float(val), 2)))
        self._settings.set("general.scale", clamped)
        self.scaleChanged.emit(clamped)

    scale = Property(float, _get_scale, _set_scale, notify=scaleChanged)

    def _get_opacity(self) -> float:
        return float(self._settings.get("general.opacity", 1.0))

    def _set_opacity(self, val: float):
        clamped = max(0.2, min(1.0, round(float(val), 2)))
        self._settings.set("general.opacity", clamped)
        self.opacityChanged.emit(clamped)

    opacity = Property(float, _get_opacity, _set_opacity, notify=opacityChanged)

    @Slot(str, str, str, str)
    def importCharacter(self, cid: str, name: str, suit: str, artwork_path: str):
        """Asynchronously imports custom artwork and creates an articulated companion."""
        try:
            from services.character_import import create_character
            from core.character_manager import CharacterManager
            mgr = self._mgr or CharacterManager()
            dest_root = mgr.characters_root
            template_root = dest_root / "miles_morales"
            if not template_root.exists():
                for p in mgr.available_characters.values():
                    template_root = p.root_path
                    break

            art = Path(artwork_path) if artwork_path and Path(artwork_path).exists() else None
            create_character(destination_root=dest_root, template_root=template_root, cid=cid, name=name, suit=suit, artwork=art)
            if hasattr(mgr, "discover_characters"):
                mgr.discover_characters()
            self.reloadCharacters()
            self.setActiveCharacter(cid)
            self.importFinished.emit(True, f"Successfully created {name}!")
        except Exception as e:
            logger.exception("Failed to import character")
            self.importFinished.emit(False, str(e))

