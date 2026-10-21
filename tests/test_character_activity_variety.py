"""Exercise repertoire parity, opt-outs and repetition for every installed character."""
import pytest
from PySide6.QtCore import QRect
from core.character_manager import CharacterManager
from core.animation_engine import AnimationEngine
from core.behavior_controller import BehaviorController
from core.movement_controller import MovementController
from core.state_machine import StateMachine, CharacterState as C
from core.personality import get_personality
from services.settings_service import SettingsService


@pytest.fixture
def controller(qapp, tmp_path, monkeypatch):
    settings = SettingsService(config_dir=tmp_path)
    monkeypatch.setattr('core.behavior_controller.get_settings', lambda: settings)
    movement = MovementController()
    movement.set_regions([QRect(0, 0, 1920, 1080)])
    movement.is_grounded = True
    controller = BehaviorController(StateMachine(), movement, AnimationEngine())
    controller._is_active = True
    yield controller
    controller.stop()
    controller.animation.stop()


@pytest.mark.parametrize('character', ['miles_morales', 'tom_holland', 'gwen_stacy_1', 'spider_2'])
def test_all_characters_offer_expressive_activities(controller, monkeypatch, character):
    profile = CharacterManager().available_characters[character]
    controller.set_personality(profile.personality)
    controller.animation.set_character(profile)
    offered = []
    monkeypatch.setattr(controller, '_choose', lambda choices: offered.extend(s for s, _ in choices))
    controller._decide_next_action()
    assert {C.DANCE, C.WAVE, C.CELEBRATE} <= set(offered)
    for state in (C.DANCE, C.WAVE, C.CELEBRATE, C.TITLE_PERCH, C.TITLE_HANG, C.FOCUS_READ):
        assert controller.animation.play(state.value, force_restart=True), (character, state)


def test_switches_cooldowns_and_recent_history_filter_choices(controller, monkeypatch):
    monkeypatch.setattr(controller.animation, 'has_animation', lambda name: True)
    controller.settings.set('animations.enabled.dance', False)
    controller.record_action('wave')
    observed = []
    def select(states, weights):
        observed.extend(zip(states, weights))
        return [C.IDLE]
    monkeypatch.setattr('core.behavior_controller.random.choices', select)
    controller.record_action('sit')
    controller._choose([(C.DANCE, 1), (C.WAVE, 1), (C.SIT, 1), (C.WALK, 1)])
    weights = dict(observed)
    assert C.DANCE not in weights and C.WAVE not in weights
    assert weights[C.SIT] < controller.personality.get_weight(C.SIT)
    assert weights[C.WALK] == controller.personality.get_weight(C.WALK)


def test_disabled_reading_rests_with_gravity(controller):
    controller.settings.set('animations.enabled.focus_read', False)
    controller._enter_focus()
    assert controller.state_machine.current_state == C.IDLE
    assert controller.movement.mode == 'ground'


def test_switching_character_starts_fresh_and_gwen_is_distinct(controller):
    controller.record_action('dance')
    controller.set_personality('gwen_stacy')
    assert not controller._recent_actions and controller.can_perform_action('dance')
    assert controller.personality != get_personality('miles_morales')
    assert len({get_personality(name).dance_caption for name in
                ('gwen_stacy', 'miles_morales', 'tom_holland')}) == 3


def test_paused_controller_cannot_choose_locked_activity(controller):
    controller._is_active = False
    controller.settings.set('behavior.automatic_animations', False)
    controller.settings.set('behavior.locked_activity', 'dance')
    controller._decide_next_action()
    assert controller.state_machine.current_state == C.IDLE
