"""Spider-Man personality profiles and behavioral differentiation.

Provides unique movement styles, action frequencies, and cooldown profiles
for built-in and imported characters.
"""
from dataclasses import dataclass, field
from typing import Dict
from .state_machine import CharacterState


@dataclass
class PersonalityProfile:
    """Configures character-specific behavior frequencies and movement styles."""

    character_id: str
    display_name: str
    # Behavioral state weights (relative likelihood of being chosen)
    action_weights: Dict[CharacterState, float] = field(default_factory=dict)
    # Action cooldowns in seconds to prevent repetitive animations
    cooldowns: Dict[str, float] = field(default_factory=dict)
    # Idle & activity duration multipliers
    duration_factor: float = 1.0
    description: str = ""
    dance_caption: str = "Time to find my rhythm!"

    def get_weight(self, state: CharacterState, base_weight: float = 1.0) -> float:
        """Return the personality-adjusted weight for a given character state."""
        return self.action_weights.get(state, base_weight)

    def get_cooldown(self, action: str, default_cooldown: float = 15.0) -> float:
        """Return the minimum interval before an action can be repeated."""
        return self.cooldowns.get(action, default_cooldown)


# 🕷️ Miles Morales:
# Relaxed, playful, hip-hop rhythm, more dancing, casual sitting & relaxed sleeping poses.
MILES_MORALES_PERSONALITY = PersonalityProfile(
    character_id="miles_morales",
    display_name="Miles Morales",
    dance_caption="Sunflower vibes!",
    description="Playful and stylish with casual swagger, frequent dancing, and relaxed poses.",
    action_weights={
        CharacterState.IDLE: 5.0,
        CharacterState.WALK: 5.0,
        CharacterState.RUN: 2.5,
        CharacterState.DANCE: 4.5,       # Miles loves to dance and vibe
        CharacterState.SIT: 4.0,         # Chill sitting
        CharacterState.SLEEP: 3.0,       # Relaxed sleep
        CharacterState.JUMP: 2.0,        # Smooth energetic jumps
        CharacterState.SWING: 1.5,       # Smooth swinging
        CharacterState.CLIMB_UP: 2.5,
        CharacterState.WAVE: 2.5,
        CharacterState.CELEBRATE: 3.5,
    },
    cooldowns={
        "dance": 15.0,        # Shorter dance cooldown for Miles
        "swing": 22.0,
        "jump": 7.0,
        "celebrate": 12.0,
        "climb": 14.0,
        "wave": 10.0,
    },
    duration_factor=1.1,
)

# 🕸️ Tom Holland's Spider-Man:
# Acrobatic, energetic, enthusiastic, frequent wall-crawling, heroic landings, web swinging, waving.
TOM_HOLLAND_PERSONALITY = PersonalityProfile(
    character_id="tom_holland",
    display_name="Tom Holland Spider-Man",
    dance_caption="Even heroes need a dance break!",
    description="Acrobatic, enthusiastic, frequent wall-climbing, hero landings, and web swinging.",
    action_weights={
        CharacterState.IDLE: 4.0,
        CharacterState.WALK: 4.0,
        CharacterState.RUN: 4.0,
        CharacterState.JUMP: 4.5,        # Very energetic jumping
        CharacterState.SWING: 3.5,       # More frequent web swinging
        CharacterState.CLIMB_UP: 5.0,    # Frequent wall crawling
        CharacterState.CLIMB_DOWN: 3.5,
        CharacterState.WALL_SLIDE: 3.0,
        CharacterState.WAVE: 4.0,        # Friendly neighborhood wave
        CharacterState.CELEBRATE: 3.0,
        CharacterState.DANCE: 1.0,       # Less frequent dancing
        CharacterState.SIT: 2.0,
        CharacterState.SLEEP: 1.5,
    },
    cooldowns={
        "swing": 12.0,        # Tom swings more frequently
        "jump": 4.5,         # Fast acrobatic jumps
        "climb": 8.0,         # Frequent wall scaling
        "wave": 8.0,          # Frequent friendly waving
        "dance": 40.0,
        "celebrate": 10.0,
    },
    duration_factor=0.9,
)

GWEN_STACY_PERSONALITY = PersonalityProfile(
    character_id="gwen_stacy",
    display_name="Gwen Stacy",
    dance_caption="Keeping time with the band!",
    description="Light, rhythmic movement, graceful swings, and quiet window perching.",
    action_weights={
        CharacterState.IDLE: 3.0, CharacterState.WALK: 4.0,
        CharacterState.RUN: 2.5, CharacterState.JUMP: 3.5,
        CharacterState.SWING: 4.0, CharacterState.CLIMB_UP: 3.0,
        CharacterState.CLIMB_DOWN: 3.0, CharacterState.DANCE: 3.0,
        CharacterState.WAVE: 2.0, CharacterState.CELEBRATE: 2.0,
        CharacterState.SIT: 3.0, CharacterState.SLEEP: 2.0,
        CharacterState.TITLE_PERCH: 3.0, CharacterState.TITLE_HANG: 2.0,
    },
    cooldowns={"swing": 16.0, "jump": 6.0, "dance": 24.0,
               "wave": 14.0, "celebrate": 18.0, "climb": 11.0,
               "title_perch": 24.0, "title_hang": 28.0},
    duration_factor=1.0,
)

_PERSONALITIES: Dict[str, PersonalityProfile] = {
    "miles_morales": MILES_MORALES_PERSONALITY,
    "tom_holland": TOM_HOLLAND_PERSONALITY,
    "gwen_stacy": GWEN_STACY_PERSONALITY,
}


def get_personality(character_id: str) -> PersonalityProfile:
    """Return the personality profile for the specified character ID."""
    return _PERSONALITIES.get(character_id, MILES_MORALES_PERSONALITY)
