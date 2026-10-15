"""Regression coverage for imported activities, themed lists and resize overflow."""
import json
from pathlib import Path
import pytest
from PIL import Image, ImageDraw
from PySide6.QtGui import QPalette, QFontDatabase
from core.character_manager import CharacterManager, CharacterProfile
from core.animation_engine import AnimationEngine
from services.character_import import create_character, load_artwork
from services.settings_service import get_settings
from ui.main_window import MainWindow


def test_artwork_import_uses_own_pixels_and_template_behavior(tmp_path, qapp):
    template = tmp_path/'template'
    template.mkdir()
    data = json.loads((Path('characters/tom_holland/character.json')).read_text(encoding='utf-8'))
    data['supported_animations'] = ['idle','walk','wave']
    (template/'character.json').write_text(json.dumps(data))
    source = tmp_path/'hero.png'
    artwork = Image.new('RGB',(100,150),'white')
    draw = ImageDraw.Draw(artwork)
    draw.ellipse((25,5,75,65),fill='#00A060')
    draw.ellipse((40,20,60,40),fill='white')
    draw.rectangle((30,60,70,140),fill='#00A060')
    artwork.save(source)
    transparent = load_artwork(source)
    assert transparent.getpixel((0,0))[3] == 0
    assert any(r>245 and g>245 and b>245 and a>240 for r,g,b,a in transparent.getdata())
    target = create_character(tmp_path/'imports',template,'green_hero','Green hero','Test suit',source)
    profile = CharacterProfile.from_json(target/'character.json')
    assert profile.personality == 'tom_holland'
    engine = AnimationEngine()
    engine.set_character(profile)
    for action in data['supported_animations']:
        assert engine.play(action,force_restart=True)
        clip = engine._get_clip(action)
        assert len(clip.frames)>1
        assert all(path.is_file() and path.is_relative_to(target) for path in clip.frames)
        assert len({Image.open(path).tobytes() for path in clip.frames})>1
    engine.stop()
    with pytest.raises(ValueError):
        create_character(tmp_path/'imports',template,'green_hero','Duplicate','Test',source)
    assert not list((tmp_path/'imports').glob('.import-*'))


def test_failed_import_is_not_discoverable(tmp_path):
    with pytest.raises(FileNotFoundError):
        create_character(tmp_path,Path('characters/miles_morales'),'missing_art','Name','Suit',tmp_path/'missing.png')
    assert not (tmp_path/'missing_art').exists()
    assert not list(tmp_path.glob('.import-*'))


@pytest.mark.parametrize('character',['spider_2','gwen_stacy_1','miles_morales','tom_holland'])
def test_every_advertised_activity_is_playable(character,qapp):
    manager = CharacterManager()
    profile = manager.available_characters[character]
    engine = AnimationEngine()
    received = []
    engine.frame_updated.connect(received.append)
    engine.set_character(profile)
    for name in profile.supported_animations:
        assert engine.play(name,force_restart=True), (character,name)
        assert received and not received[-1].isNull()
        for path in engine._get_clip(name).frames:
            with Image.open(path) as image:
                assert image.mode == 'RGBA'
                assert image.size == (512,512)
    engine.stop()


@pytest.mark.parametrize('theme',['dark','light'])
def test_responsive_grid_and_application_contrast(theme,qapp):
    settings = get_settings()
    old_theme = settings.get('general.theme')
    settings.set('general.theme',theme)
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    manager = CharacterManager()
    manager.set_active_character('miles_morales')
    window = MainWindow(manager)
    window.show()
    widths = []
    try:
        window.navigation.setCurrentRow(1)
        for width in (1280,720,940):
            window.resize(width,720)
            for _ in range(4):
                qapp.processEvents()
            page = window.pages.currentWidget()
            assert page.horizontalScrollBar().maximum() == 0
            cards = list(window.char_selection_widget.cards.values())+[window.char_selection_widget.add_card]
            assert all(card.x()+card.width() <= window.char_selection_widget.width() for card in cards)
            columns = len({card.x() for card in cards})
            assert columns == (2 if width == 720 else 3)
            widths.append(cards[0].width())
        assert widths[0] > widths[1]
        window.navigation.setCurrentRow(3)
        qapp.processEvents()
        palette = window.app_list.palette()
        background = palette.color(QPalette.Base)
        text = palette.color(QPalette.Text)
        assert abs(background.lightness()-text.lightness()) > 120
    finally:
        window.hide()
        window.deleteLater()
        settings.set('general.theme',old_theme)


def test_suspension_does_not_advance_clip_time(qapp):
    engine = AnimationEngine()
    manager = CharacterManager()
    engine.set_character(manager.available_characters['miles_morales'])
    engine.set_suspended(True)
    elapsed = engine._position_ms
    engine._last_ns -= 10_000_000_000
    engine.set_speed_multiplier(1.5)
    assert engine._position_ms == elapsed
    engine.stop()
