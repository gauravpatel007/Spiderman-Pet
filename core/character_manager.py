"""Character loading and management system."""
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("SpiderBuddy.CharacterManager")


@dataclass
class CharacterProfile:
    """Represents a loaded Spider-Man character profile."""
    id: str
    name: str
    display_name: str
    suit: str
    description: str
    base_size: tuple[int, int]
    scale_factor: float
    theme_colors: Dict[str, str]
    physics: Dict[str, float]
    supported_animations: List[str]
    root_path: Path
    sprites_path: Path
    animations_path: Path
    personality: str = "miles_morales"

    @classmethod
    def from_json(cls, json_path: Path) -> "CharacterProfile":
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        root = json_path.parent
        return cls(
            id=data.get("id", root.name),
            name=data.get("name", "Unknown Spider-Man"),
            display_name=data.get("display_name", data.get("name", "Spider-Man")),
            suit=data.get("suit", "Classic Suit"),
            description=data.get("description", ""),
            base_size=tuple(data.get("base_size", [128, 128])),
            scale_factor=data.get("scale_factor", 1.0),
            theme_colors=data.get("theme_colors", {"primary": "#E50914", "secondary": "#111111"}),
            physics=data.get("physics", {}),
            supported_animations=data.get("supported_animations", []),
            root_path=root,
            sprites_path=root / "sprites",
            animations_path=root / "animations",
            personality=data.get("personality", data.get("id", "miles_morales")),
        )


class CharacterManager(QObject):
    """Manages discoverability, loading, and runtime switching of Spider-Man characters."""

    character_changed = Signal(CharacterProfile)
    characters_discovered = Signal()

    def __init__(self, characters_root: Optional[Path] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        if characters_root:
            self.characters_root = characters_root
        elif getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
            self.characters_root = base / "characters"
        else:
            self.characters_root = Path(__file__).resolve().parent.parent / "characters"
        self._search_roots = [self.characters_root]
        if characters_root is None and getattr(sys, 'frozen', False):
            from services.settings_service import get_settings
            self.characters_root = get_settings().user_dir/'characters'
            self._search_roots.append(self.characters_root)
        self._characters: Dict[str, CharacterProfile] = {}
        self._active_character: Optional[CharacterProfile] = None

        self.discover_characters()

    @property
    def available_characters(self) -> Dict[str, CharacterProfile]:
        return self._characters

    @property
    def active_character(self) -> Optional[CharacterProfile]:
        return self._active_character

    def discover_characters(self) -> None:
        """Scan the characters directory for valid character.json configurations."""
        self._characters.clear()
        for root in self._search_roots:
            if not root.exists():
                continue
            for child in sorted(root.iterdir()):
                if not child.is_dir() or child.name.startswith('.'):
                    continue
                char_json = child/'character.json'
                if char_json.exists():
                    try:
                        profile = CharacterProfile.from_json(char_json)
                        self._characters[profile.id] = profile
                    except Exception:
                        logger.exception('Failed to load character from %s', char_json)
        self.characters_discovered.emit()

    def set_active_character(self, character_id: str) -> bool:
        """Set the currently active Spider-Man character."""
        if character_id not in self._characters:
            logger.warning(f"Character {character_id} not found in available characters.")
            return False

        if self._active_character and self._active_character.id == character_id:
            return True

        self._active_character = self._characters[character_id]
        logger.info(f"Active character switched to: {self._active_character.display_name}")
        self.character_changed.emit(self._active_character)
        return True

    DEFAULT_CHARACTER_IDS = frozenset({
        "tom_holland", "miles_morales", "gwen_stacy_1", "gwen_stacy", "spider_2"
    })

    def delete_character(self, character_id: str) -> bool:
        """Permanently delete a custom character.

        The 4 default built-in characters (Tom Holland, Miles Morales, Gwen Stacy, Spider 2)
        cannot be deleted.
        """
        if character_id in self.DEFAULT_CHARACTER_IDS:
            logger.warning("Refused to delete protected default character: %s", character_id)
            return False

        profile = self._characters.get(character_id)
        if not profile:
            logger.warning("Character not found for deletion: %s", character_id)
            return False

        was_active = bool(self._active_character and self._active_character.id == character_id)

        import shutil
        char_path = Path(profile.root_path)
        if char_path.exists() and char_path.is_dir():
            shutil.rmtree(char_path, ignore_errors=True)
            logger.info("Successfully deleted character folder: %s", char_path)

        self.discover_characters()

        if was_active:
            fallback = "tom_holland" if "tom_holland" in self._characters else next(iter(self._characters.keys()), "")
            if fallback:
                self.set_active_character(fallback)

        return True
