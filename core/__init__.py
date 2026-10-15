"""Core logic, character handling, and state machine package for Spider-Buddy."""
from .state_machine import StateMachine, CharacterState
from .character_manager import CharacterManager
from .animation_engine import AnimationEngine
from .movement_controller import MovementController
from .behavior_controller import BehaviorController
from .interaction_manager import InteractionManager

__all__ = [
    "StateMachine",
    "CharacterState",
    "CharacterManager",
    "AnimationEngine",
    "MovementController",
    "BehaviorController",
    "InteractionManager",
]
