"""Unit tests verifying character deletion permissions and default character protection."""
import json
import shutil
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.bootstrap import ensure_site_packages
ensure_site_packages()

from core.character_manager import CharacterManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_protected_characters_cannot_be_deleted(qapp):
    char_mgr = CharacterManager()
    protected = ["tom_holland", "miles_morales", "gwen_stacy_1", "spider_2"]

    for cid in protected:
        if cid in char_mgr.available_characters:
            char_folder = char_mgr.available_characters[cid].root_path
            assert char_folder.exists(), f"Protected character {cid} folder should exist"

            # Deletion attempt must fail
            res = char_mgr.delete_character(cid)
            assert res is False, f"CharacterManager.delete_character({cid}) must return False"
            assert char_folder.exists(), f"Protected character {cid} folder must still exist"


def test_custom_character_deletion_and_fallback(qapp, tmp_path):
    # Setup a mock characters root with 1 protected and 1 custom character
    chars_root = tmp_path / "characters"
    chars_root.mkdir()

    # Protected default character
    tom_dir = chars_root / "tom_holland"
    tom_dir.mkdir()
    (tom_dir / "character.json").write_text(json.dumps({
        "id": "tom_holland",
        "name": "Tom Holland",
        "suit": "Stark Suit",
        "description": "Default Spidey"
    }), encoding="utf-8")

    # Custom character
    custom_dir = chars_root / "test_custom_hero"
    custom_dir.mkdir()
    (custom_dir / "character.json").write_text(json.dumps({
        "id": "test_custom_hero",
        "name": "Custom Spidey",
        "suit": "Homemade Suit",
        "description": "Custom Hero"
    }), encoding="utf-8")

    mgr = CharacterManager(characters_root=chars_root)
    assert "tom_holland" in mgr.available_characters
    assert "test_custom_hero" in mgr.available_characters

    # Set custom character as active
    mgr.set_active_character("test_custom_hero")
    assert mgr.active_character.id == "test_custom_hero"

    # Attempt to delete protected character
    assert mgr.delete_character("tom_holland") is False
    assert (chars_root / "tom_holland").exists()

    # Delete custom character
    res = mgr.delete_character("test_custom_hero")
    assert res is True
    assert not (chars_root / "test_custom_hero").exists()
    assert "test_custom_hero" not in mgr.available_characters
    # Active character must have fallen back to tom_holland
    assert mgr.active_character is not None
    assert mgr.active_character.id == "tom_holland"


def test_web_window_can_delete_metadata(qapp):
    from ui.web_window import WebMainWindow
    from unittest.mock import MagicMock

    char_mgr = CharacterManager()
    win = WebMainWindow(character_mgr=char_mgr)

    chars_list = win._get_characters_list()
    assert len(chars_list) > 0

    for item in chars_list:
        cid = item["id"]
        if cid in ("tom_holland", "miles_morales", "gwen_stacy_1", "spider_2"):
            assert item["can_delete"] is False, f"{cid} must have can_delete=False"
        elif cid == "a":
            assert item["can_delete"] is True, f"{cid} (A!) must have can_delete=True"

    # Test web action refusal for protected characters
    original_delete = char_mgr.delete_character
    char_mgr.delete_character = MagicMock(return_value=True)

    win._on_web_action({"action": "delete_character", "character_id": "tom_holland"})
    char_mgr.delete_character.assert_not_called()

    char_mgr.delete_character = original_delete
    win.close()
