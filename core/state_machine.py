"""Robust State Machine for Spider-Man behavioral states."""
import logging
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Set
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("SpiderBuddy.StateMachine")


class CharacterState(Enum):
    """Enumeration of possible animation & behavioral states."""
    IDLE = "idle"
    WALK = "walk"
    RUN = "run"
    JUMP = "jump"
    FALL = "fall"
    LAND = "land"
    CLIMB_UP = "climb_up"
    CLIMB_DOWN = "climb_down"
    WALL_SLIDE = "wall_slide"
    PERCH = "perch"
    SWING = "swing"
    HANG = "hang"
    SLEEP = "sleep"
    WAKE_UP = "wake_up"
    SIT = "sit"
    STAND_UP = "stand_up"
    WAVE = "wave"
    DANCE = "dance"
    CELEBRATE = "celebrate"
    INTERACT = "interact"
    DRAGGED = "dragged"
    TITLE_PERCH = "title_perch"
    TITLE_HANG = "title_hang"
    FOCUS_READ = "focus_read"


class StateTransition:
    """Represents an allowed transition between states with optional condition."""
    def __init__(self, from_state: CharacterState, to_state: CharacterState, condition: Optional[Callable[[], bool]] = None):
        self.from_state = from_state
        self.to_state = to_state
        self.condition = condition

    def can_transition(self) -> bool:
        if self.condition is not None:
            return self.condition()
        return True


class StateMachine(QObject):
    """Event-driven hierarchical state machine controlling character state."""

    state_changed = Signal(CharacterState, CharacterState)  # (old_state, new_state)

    def __init__(self, initial_state: CharacterState = CharacterState.IDLE, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._current_state: CharacterState = initial_state
        self._previous_state: Optional[CharacterState] = None
        self._pending_state: Optional[CharacterState] = None
        self._finishing_posture = False
        self._transitions: Dict[CharacterState, List[StateTransition]] = {state: [] for state in CharacterState}
        self._enter_callbacks: Dict[CharacterState, List[Callable[[], None]]] = {state: [] for state in CharacterState}
        self._exit_callbacks: Dict[CharacterState, List[Callable[[], None]]] = {state: [] for state in CharacterState}

        self._setup_default_transitions()

    @property
    def current_state(self) -> CharacterState:
        return self._current_state

    @property
    def previous_state(self) -> Optional[CharacterState]:
        return self._previous_state

    def _setup_default_transitions(self) -> None:
        """Register valid state transitions."""
        # Any state can be dragged
        for state in CharacterState:
            if state != CharacterState.DRAGGED:
                self.add_transition(state, CharacterState.DRAGGED)

        # From DRAGGED, transitions to FALL or LAND
        self.add_transition(CharacterState.DRAGGED, CharacterState.FALL)
        self.add_transition(CharacterState.DRAGGED, CharacterState.LAND)
        self.add_transition(CharacterState.DRAGGED, CharacterState.IDLE)

        # IDLE transitions
        self.add_transition(CharacterState.IDLE, CharacterState.WALK)
        self.add_transition(CharacterState.IDLE, CharacterState.RUN)
        self.add_transition(CharacterState.IDLE, CharacterState.JUMP)
        self.add_transition(CharacterState.IDLE, CharacterState.PERCH)
        self.add_transition(CharacterState.IDLE, CharacterState.SLEEP)
        self.add_transition(CharacterState.IDLE, CharacterState.INTERACT)
        self.add_transition(CharacterState.IDLE, CharacterState.SWING)

        # WALK / RUN transitions
        self.add_transition(CharacterState.WALK, CharacterState.IDLE)
        self.add_transition(CharacterState.WALK, CharacterState.RUN)
        self.add_transition(CharacterState.WALK, CharacterState.JUMP)
        self.add_transition(CharacterState.WALK, CharacterState.CLIMB_UP)
        self.add_transition(CharacterState.WALK, CharacterState.FALL)

        self.add_transition(CharacterState.RUN, CharacterState.WALK)
        self.add_transition(CharacterState.RUN, CharacterState.IDLE)
        self.add_transition(CharacterState.RUN, CharacterState.JUMP)
        self.add_transition(CharacterState.RUN, CharacterState.SWING)

        # JUMP / FALL / LAND transitions
        self.add_transition(CharacterState.JUMP, CharacterState.FALL)
        self.add_transition(CharacterState.JUMP, CharacterState.SWING)
        self.add_transition(CharacterState.JUMP, CharacterState.CLIMB_UP)
        self.add_transition(CharacterState.FALL, CharacterState.LAND)
        self.add_transition(CharacterState.FALL, CharacterState.SWING)
        self.add_transition(CharacterState.FALL, CharacterState.WALL_SLIDE)
        self.add_transition(CharacterState.LAND, CharacterState.IDLE)
        self.add_transition(CharacterState.LAND, CharacterState.WALK)

        # CLIMB / WALL_SLIDE / PERCH / HANG transitions
        self.add_transition(CharacterState.CLIMB_UP, CharacterState.CLIMB_DOWN)
        self.add_transition(CharacterState.CLIMB_UP, CharacterState.PERCH)
        self.add_transition(CharacterState.CLIMB_UP, CharacterState.HANG)
        self.add_transition(CharacterState.CLIMB_UP, CharacterState.JUMP)
        self.add_transition(CharacterState.CLIMB_DOWN, CharacterState.CLIMB_UP)
        self.add_transition(CharacterState.CLIMB_DOWN, CharacterState.IDLE)
        self.add_transition(CharacterState.CLIMB_DOWN, CharacterState.WALL_SLIDE)
        self.add_transition(CharacterState.WALL_SLIDE, CharacterState.LAND)
        self.add_transition(CharacterState.WALL_SLIDE, CharacterState.CLIMB_UP)
        self.add_transition(CharacterState.PERCH, CharacterState.IDLE)
        self.add_transition(CharacterState.PERCH, CharacterState.JUMP)
        self.add_transition(CharacterState.PERCH, CharacterState.SWING)
        self.add_transition(CharacterState.HANG, CharacterState.FALL)
        self.add_transition(CharacterState.HANG, CharacterState.CLIMB_UP)

        # SWING transitions
        self.add_transition(CharacterState.SWING, CharacterState.FALL)
        self.add_transition(CharacterState.SWING, CharacterState.LAND)
        self.add_transition(CharacterState.SWING, CharacterState.CLIMB_UP)
        self.add_transition(CharacterState.SWING, CharacterState.PERCH)

        # SLEEP / INTERACT transitions
        self.add_transition(CharacterState.IDLE, CharacterState.SIT)
        self.add_transition(CharacterState.IDLE, CharacterState.WAVE)
        self.add_transition(CharacterState.IDLE, CharacterState.DANCE)
        self.add_transition(CharacterState.DANCE, CharacterState.IDLE)
        self.add_transition(CharacterState.CELEBRATE, CharacterState.IDLE)
        self.add_transition(CharacterState.SIT, CharacterState.STAND_UP)
        self.add_transition(CharacterState.SIT, CharacterState.SLEEP)
        self.add_transition(CharacterState.STAND_UP, CharacterState.IDLE)
        self.add_transition(CharacterState.SLEEP, CharacterState.WAKE_UP)
        self.add_transition(CharacterState.WAKE_UP, CharacterState.IDLE)
        self.add_transition(CharacterState.WAVE, CharacterState.IDLE)
        self.add_transition(CharacterState.INTERACT, CharacterState.IDLE)

        # Window perching and focus transitions
        self.add_transition(CharacterState.IDLE, CharacterState.TITLE_PERCH)
        self.add_transition(CharacterState.IDLE, CharacterState.TITLE_HANG)
        self.add_transition(CharacterState.IDLE, CharacterState.FOCUS_READ)
        self.add_transition(CharacterState.WALK, CharacterState.TITLE_PERCH)
        self.add_transition(CharacterState.WALK, CharacterState.TITLE_HANG)
        self.add_transition(CharacterState.SWING, CharacterState.TITLE_PERCH)
        self.add_transition(CharacterState.SWING, CharacterState.TITLE_HANG)
        self.add_transition(CharacterState.CLIMB_UP, CharacterState.TITLE_PERCH)
        self.add_transition(CharacterState.CLIMB_UP, CharacterState.TITLE_HANG)
        self.add_transition(CharacterState.PERCH, CharacterState.TITLE_PERCH)
        self.add_transition(CharacterState.TITLE_PERCH, CharacterState.FALL)
        self.add_transition(CharacterState.TITLE_PERCH, CharacterState.SWING)
        self.add_transition(CharacterState.TITLE_PERCH, CharacterState.CLIMB_DOWN)
        self.add_transition(CharacterState.TITLE_PERCH, CharacterState.IDLE)
        self.add_transition(CharacterState.TITLE_HANG, CharacterState.FALL)
        self.add_transition(CharacterState.TITLE_HANG, CharacterState.SWING)
        self.add_transition(CharacterState.TITLE_HANG, CharacterState.CLIMB_DOWN)
        self.add_transition(CharacterState.TITLE_HANG, CharacterState.IDLE)
        self.add_transition(CharacterState.FOCUS_READ, CharacterState.IDLE)

    def add_transition(self, from_state: CharacterState, to_state: CharacterState, condition: Optional[Callable[[], bool]] = None) -> None:
        """Register a valid state transition."""
        self._transitions[from_state].append(StateTransition(from_state, to_state, condition))

    def on_enter(self, state: CharacterState, callback: Callable[[], None]) -> None:
        """Register a callback when entering a specific state."""
        self._enter_callbacks[state].append(callback)

    def on_exit(self, state: CharacterState, callback: Callable[[], None]) -> None:
        """Register a callback when exiting a specific state."""
        self._exit_callbacks[state].append(callback)

    def can_transition_to(self, new_state: CharacterState) -> bool:
        """Check if transition from current state to new_state is allowed."""
        if self._current_state == new_state:
            return True
        for transition in self._transitions.get(self._current_state, []):
            if transition.to_state == new_state:
                return transition.can_transition()
        return False

    def transition_to(self, new_state: CharacterState, force: bool = False) -> bool:
        """Attempt to transition to new_state."""
        # User requests may override normal transitions, but must still play
        # wake/stand clips before locomotion. Physical dragging can interrupt.
        if new_state == CharacterState.DRAGGED:
            self._pending_state = None
        elif (not self._finishing_posture and
              self._current_state in (CharacterState.WAKE_UP, CharacterState.STAND_UP) and
              new_state != self._current_state):
            self._pending_state = new_state
            return True
        elif self._current_state == CharacterState.SLEEP and new_state not in (
                CharacterState.SLEEP, CharacterState.WAKE_UP):
            self._pending_state = new_state
            new_state = CharacterState.WAKE_UP
        elif self._current_state == CharacterState.SIT and new_state not in (
                CharacterState.SIT, CharacterState.SLEEP, CharacterState.STAND_UP):
            self._pending_state = new_state
            new_state = CharacterState.STAND_UP
        if self._current_state == new_state:
            return True

        if not force and not self.can_transition_to(new_state):
            logger.debug(f"Transition rejected: {self._current_state.value} -> {new_state.value}")
            return False

        old_state = self._current_state

        # Fire exit callbacks
        for cb in self._exit_callbacks.get(old_state, []):
            try:
                cb()
            except Exception as e:
                logger.error(f"Error in exit callback for {old_state}: {e}")

        self._previous_state = old_state
        self._current_state = new_state
        logger.debug(f"State transitioned: {old_state.value} -> {new_state.value}")

        # Fire enter callbacks
        for cb in self._enter_callbacks.get(new_state, []):
            try:
                cb()
            except Exception as e:
                logger.error(f"Error in enter callback for {new_state}: {e}")

        self.state_changed.emit(old_state, new_state)
        return True

    def finish_posture_transition(self) -> None:
        """Continue the requested action after wake-up or stand-up completes."""
        if self._current_state not in (CharacterState.WAKE_UP, CharacterState.STAND_UP):
            return
        destination = self._pending_state or CharacterState.IDLE
        self._pending_state = None
        self._finishing_posture = True
        try:
            self.transition_to(destination, force=True)
        finally:
            self._finishing_posture = False
