import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPixmap
from overlay.transparent_overlay import TransparentOverlay
from core.character_manager import CharacterManager
from core.animation_engine import AnimationEngine


@pytest.mark.parametrize('character', ['miles_morales', 'tom_holland', 'spider_2', 'gwen_stacy_1'])
def test_headphones_survive_frames_and_are_in_alpha_mask(qapp, character):
    engine = AnimationEngine()
    engine.set_character(CharacterManager().available_characters[character])
    clip = engine._get_clip('idle')
    overlay = TransparentOverlay()
    overlay.set_character_height(166)
    overlay.set_frame(QPixmap(str(clip.frames[0])))
    original = overlay._rendered.toImage()
    overlay.set_music_playing(True)
    dressed = overlay._rendered.toImage()
    assert original != dressed
    added = [(x, y) for y in range(dressed.height()) for x in range(dressed.width())
             if dressed.pixelColor(x, y).alpha() > 180 and original.pixelColor(x, y).alpha() < 10]
    assert len(added) > 10
    assert any(overlay._input_region.contains(QPoint(x,y)) for x,y in added)
    overlay.set_frame(QPixmap(str(clip.frames[1])))
    music_frame = overlay._rendered.toImage()
    overlay.set_music_playing(False)
    assert overlay._rendered.toImage() != music_frame
    overlay._audio_anim_timer.stop()
    overlay.close()
    engine.stop()
