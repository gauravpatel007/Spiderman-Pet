"""Unit and functional tests for Phase 10: Advanced Character Behaviors."""
import time
import pytest
from PySide6.QtCore import QPoint

from core.state_machine import StateMachine, CharacterState
from core.personality import get_personality, MILES_MORALES_PERSONALITY, TOM_HOLLAND_PERSONALITY
from core.animation_engine import AnimationEngine
from core.movement_controller import MovementController
from core.behavior_controller import BehaviorController
from core.character_manager import CharacterManager
from core.interaction_manager import InteractionManager


def test_personality_profiles():
    """Verify Miles Morales and Tom Holland personality differentiation."""
    miles = get_personality("miles_morales")
    tom = get_personality("tom_holland")

    assert miles.character_id == "miles_morales"
    assert tom.character_id == "tom_holland"

    # Miles Morales has higher dance weight than Tom
    assert miles.get_weight(CharacterState.DANCE) > tom.get_weight(CharacterState.DANCE)

    # Tom Holland has higher jump and climb weights
    assert tom.get_weight(CharacterState.JUMP) > miles.get_weight(CharacterState.JUMP)
    assert tom.get_weight(CharacterState.CLIMB_UP) > miles.get_weight(CharacterState.CLIMB_UP)

    # Cooldown differences
    assert tom.get_cooldown("swing") < miles.get_cooldown("swing")
    assert miles.get_cooldown("dance") < tom.get_cooldown("dance")


def test_action_cooldowns(qapp):
    """Verify BehaviorController enforces action cooldowns to prevent repetitive moves."""
    sm = StateMachine()
    anim = AnimationEngine()
    mov = MovementController()
    bc = BehaviorController(sm, mov, anim)

    bc.set_personality("miles_morales")
    action = "swing"
    cooldown = bc.personality.get_cooldown(action)

    # Initially can perform action
    assert bc.can_perform_action(action)

    # After performing action, cooldown is enforced
    bc.record_action(action)
    assert not bc.can_perform_action(action)

    # Fast forward simulated time
    bc._action_timestamps[action] = time.monotonic() - (cooldown + 1.0)
    assert bc.can_perform_action(action)


def test_smart_reactions(qapp):
    """Verify smart reactions: wake up on user return and application entrance."""
    sm = StateMachine()
    anim = AnimationEngine()
    mov = MovementController()
    bc = BehaviorController(sm, mov, anim)

    char_mgr = CharacterManager()
    char_mgr.set_active_character("miles_morales")
    anim.set_character(char_mgr.active_character)

    bc.start()

    # User return after sleeping: wakes up
    sm.transition_to(CharacterState.SLEEP, force=True)
    assert sm.current_state == CharacterState.SLEEP

    # User returns: idle seconds drops from 700 to 1
    bc.update_idle(700)
    bc.update_idle(1)
    # Should transition to WAKE_UP or IDLE
    assert sm.current_state in (CharacterState.WAKE_UP, CharacterState.IDLE, CharacterState.WAVE)

    bc.stop()


def test_interactive_web_shoot(qapp):
    """Verify interactive web shooting toward cursor/target."""
    sm = StateMachine()
    anim = AnimationEngine()
    mov = MovementController()
    char_mgr = CharacterManager()
    bc = BehaviorController(sm, mov, anim)
    im = InteractionManager(sm, mov, char_mgr, anim, bc)

    web_events = []
    mov.web_changed.connect(lambda points: web_events.append(points))

    target = QPoint(300, 100)
    im.shoot_web_at(target)

    assert len(web_events) >= 1
    points = web_events[0]
    assert points is not None
    (p1, p2) = points
    assert p2[0] == float(target.x())
    assert p2[1] == float(target.y())
