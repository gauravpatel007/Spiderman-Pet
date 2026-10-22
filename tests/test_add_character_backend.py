"""Comprehensive test suite for the 'Add Character' backend and UI flow."""
import json
import shutil
import tempfile
from pathlib import Path
import pytest
from PIL import Image, ImageDraw
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.character_manager import CharacterManager, CharacterProfile
from services.character_import import create_character, build_artwork_clips
from ui.character_selection import AddCharacterDialog, ImportWorker


@pytest.fixture
def tmp_character_roots(tmp_path):
    dest = tmp_path / "characters"
    dest.mkdir(parents=True, exist_ok=True)
    template_dir = dest / "test_template"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "sprites").mkdir()
    (template_dir / "animations").mkdir()
    
    # Create simple dummy preview and sprite
    dummy_img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    dummy_img.save(template_dir / "preview.png")
    dummy_img.save(template_dir / "sprites" / "idle.png")
    
    data = {
        "id": "test_template",
        "name": "Template Spidey",
        "display_name": "Template Spidey",
        "suit": "Classic Red",
        "personality": "Playful",
        "supported_animations": ["idle", "walk", "wave"]
    }
    (template_dir / "character.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return dest, template_dir


def test_create_character_template_copy(tmp_character_roots):
    """Test fast cloning of character without artwork."""
    dest, tpl = tmp_character_roots
    progress_records = []
    
    def on_prog(pct, msg):
        progress_records.append((pct, msg))
        
    target = create_character(
        destination_root=dest,
        template_root=tpl,
        cid="cloned_spidey",
        name="Cloned Spidey",
        suit="Stealth Suit",
        artwork=None,
        progress_callback=on_prog
    )
    
    assert target.exists()
    assert (target / "character.json").exists()
    assert (target / "preview.png").exists()
    assert len(progress_records) > 0
    assert progress_records[-1][0] == 100
    
    char_data = json.loads((target / "character.json").read_text(encoding="utf-8"))
    assert char_data["id"] == "cloned_spidey"
    assert char_data["name"] == "Cloned Spidey"
    assert char_data["suit"] == "Stealth Suit"
    assert char_data["custom_character"] is True
    assert char_data["animation_source"] == "template_copy"


def test_create_character_duplicate_id_raises(tmp_character_roots):
    dest, tpl = tmp_character_roots
    create_character(dest, tpl, "dup_hero", "Duplicate Hero", "Suit A")
    with pytest.raises(ValueError, match="already exists"):
        create_character(dest, tpl, "dup_hero", "Duplicate Hero 2", "Suit B")


def test_create_character_invalid_id_raises(tmp_character_roots):
    dest, tpl = tmp_character_roots
    with pytest.raises(ValueError, match="Choose a valid character identifier"):
        create_character(dest, tpl, "INVALID-ID!", "Hero", "Suit")


def test_create_character_with_custom_artwork(tmp_character_roots):
    """Test character creation with custom artwork and frame generation."""
    dest, tpl = tmp_character_roots
    art_path = dest / "custom_art.png"
    art_img = Image.new("RGBA", (150, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(art_img)
    draw.ellipse((35, 10, 115, 90), fill=(220, 20, 60, 255))
    draw.rectangle((40, 90, 110, 190), fill=(30, 144, 255, 255))
    art_img.save(art_path)
    
    progress_records = []
    def on_prog(pct, msg):
        progress_records.append((pct, msg))
        
    target = create_character(
        destination_root=dest,
        template_root=tpl,
        cid="art_hero",
        name="Artwork Hero",
        suit="Custom Suit",
        artwork=art_path,
        progress_callback=on_prog
    )
    
    assert target.exists()
    assert (target / "preview.png").exists()
    assert (target / "animation_manifest.json").exists()
    assert (target / "generated" / "idle").exists()
    assert len(progress_records) > 0
    assert any("Generating" in msg for _, msg in progress_records)


def test_add_character_dialog_templates_and_ui(qapp, tmp_character_roots):
    """Verify dialog populates all templates dynamically and enforces window flags."""
    dest, tpl = tmp_character_roots
    mgr = CharacterManager(characters_root=dest)
    mgr.discover_characters()
    
    dlg = AddCharacterDialog(character_mgr=mgr)
    
    # Verify WindowStaysOnTopHint is present
    assert bool(dlg.windowFlags() & Qt.WindowStaysOnTopHint) is True
    assert dlg.isModal() is True
    
    # Verify template combo contains our template
    items = [dlg.template_combo.itemData(i) for i in range(dlg.template_combo.count())]
    assert "test_template" in items
    
    # Verify auto-fill id logic
    dlg.name_edit.setText("Amazing Spider-Friend")
    assert dlg.id_edit.text() == "amazing_spider_friend"
    
    # Progress container initially hidden
    assert dlg.progress_container.isVisible() is False
    dlg.close()


def test_import_worker_emits_progress_and_success(qapp, qtbot, tmp_character_roots):
    dest, tpl = tmp_character_roots
    worker = ImportWorker({
        "destination_root": dest,
        "template_root": tpl,
        "cid": "worker_hero",
        "name": "Worker Hero",
        "suit": "Worker Suit",
        "artwork": None
    })
    
    progress_received = []
    worker.progress.connect(lambda p, m: progress_received.append((p, m)))
    
    with qtbot.waitSignal(worker.succeeded, timeout=5000) as blocker:
        worker.start()
        
    assert blocker.args[0] == "worker_hero"
    assert len(progress_received) > 0
    worker.wait()
