"""Behavior controller orchestrating state transitions, actions, and autonomy."""
import logging
import random
import time
from collections import deque
from typing import Optional, List, Tuple
from PySide6.QtCore import QObject, QTimer

from .activity_policy import enabled, PHYSICAL_STATES
from .state_machine import StateMachine, CharacterState
from .movement_controller import MovementController
from .animation_engine import AnimationEngine
from .personality import get_personality, PersonalityProfile
from services.settings_service import get_settings

logger = logging.getLogger("SpiderBuddy.BehaviorController")


class BehaviorController(QObject):
    """
    Drives autonomous Spider-Man behavior, linking high-level logic to movement
    and animation playback with character personalities and smart reactions.
    """

    def __init__(
        self,
        state_machine: StateMachine,
        movement: MovementController,
        animation: AnimationEngine,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.state_machine = state_machine
        self.movement = movement
        self.animation = animation
        self.settings = get_settings()
        self.personality: PersonalityProfile = get_personality("miles_morales")

        # Autonomous thinking / decision timer
        self._brain_timer = QTimer(self)
        self._brain_timer.timeout.connect(self._decide_next_action)
        self._brain_timer.setInterval(3000)

        # Wire signals
        self.state_machine.state_changed.connect(self._on_state_changed)
        self.movement.boundary_hit.connect(self._on_boundary_hit)
        self.movement.airborne.connect(self._on_airborne)
        self.movement.apex_reached.connect(self._on_apex)
        self.movement.swing_released.connect(self._on_swing_released)
        self.movement.motion_changed.connect(self._sync_gait)
        self.movement.direction_changed.connect(self.animation.set_facing_left)
        self.movement.trampoline_bounced.connect(self._on_trampoline_bounced)
        self.animation.animation_completed.connect(self._on_animation_completed)
        self.settings.setting_changed.connect(self._on_setting_changed)

        self._is_active = False
        self._last_special = 0.0
        self.cursor_attention = False
        self._idle_stage = 0
        self._idle_seconds = 0.0
        self._continuous_active_seconds = 0.0
        self._override_until = 0.0
        self._is_low_battery = False
        self._is_charging = False
        self._action_timestamps = {}
        self._recent_actions = deque(maxlen=4)
        self.position_activity = lambda name: False
        self.overlay = None
        self._is_pinned = False
        self._is_heavy_load = False
        self._is_music_playing = False

    def set_pinned(self, pinned: bool, keep_state: bool = False) -> None:
        """Lock companion in place with no autonomous activities when Shift-dragged or WASD static."""
        self._is_pinned = bool(pinned)
        if self._is_pinned:
            self._brain_timer.stop()
            self.movement.set_motion('hold', 0.0, 0.0)
            self.movement.vx = 0.0
            self.movement.vy = 0.0
            if not keep_state:
                self.state_machine.transition_to(CharacterState.IDLE, force=True)
                self.animation.play("idle")
                if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                    self.overlay.show_speech_bubble("📌 Pinned in place! (No activities)", 2200, "action")
                logger.info("Spider-Man pinned in place by Shift+Drag. Autonomy paused.")
            else:
                logger.info("Spider-Man statically held in place via WASD. Autonomy paused.")
        else:
            self._is_pinned = False
            self.movement.set_motion('ground' if self.movement.is_grounded else 'air')
            if not self.movement.is_grounded and self.state_machine.current_state not in (CharacterState.TITLE_HANG, CharacterState.TITLE_PERCH, CharacterState.HANG, CharacterState.PERCH):
                self.state_machine.transition_to(CharacterState.FALL, force=True)
            if self._is_active:
                self._brain_timer.start()
                self._schedule_decision()
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                self.overlay.show_speech_bubble("Back in action!", 1800, "comic")
            logger.info("Spider-Man unpinned. Autonomy resumed.")

    def set_heavy_load(self, is_heavy: bool, cpu: float = 0.0, ram: float = 0.0) -> None:
        """When CPU or RAM > 85%, Spider-Man pauses autonomy and holds the collapsing beam."""
        was_heavy = self._is_heavy_load
        self._is_heavy_load = bool(is_heavy) and not self.settings.get('behavior.focus_mode', False)

        # Do not override or disrupt quiet focus mode / reading
        in_focus = (
            bool(self.settings.get('behavior.focus_mode', False))
            or self.state_machine.current_state == CharacterState.FOCUS_READ
        )

        if self._is_heavy_load and not was_heavy:
            if not in_focus:
                self._brain_timer.stop()
                self.movement.set_motion('hold', 0.0, 0.0)
                self.movement.vx = 0.0
                self.movement.vy = 0.0
                self.state_machine.transition_to(CharacterState.IDLE, force=True)
                self.animation.play("idle")
                if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                    quote = (
                        f"HRRRGH! CPU at {int(cpu)}%! I can hold this beam...!"
                        if cpu >= ram
                        else f"HRRRGH! RAM at {int(ram)}%! It's too heavy...!"
                    )
                    self.overlay.show_speech_bubble(quote, 3200, "action")
                logger.info("Heavy system load (>85%%) entered. Lifting collapsing steel beam.")

        elif not self._is_heavy_load and was_heavy:
            if self.settings.get('behavior.focus_mode', False):
                self._enter_focus()
                return
            if not getattr(self, "_is_pinned", False) and not in_focus:
                self.movement.set_motion('ground' if self.movement.is_grounded else 'air')
                if self._is_active:
                    self._brain_timer.start()
                    self._schedule_decision()
                if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                    self.overlay.show_speech_bubble("Phew! Load's back down! Almost dropped that beam!", 2400, "comic")
            logger.info("Heavy system load ended. Beam lifted away.")

    def set_music_playing(self, is_playing: bool, volume: float = 0.0) -> None:
        """React to live music playback detection."""
        was_playing = self._is_music_playing
        self._is_music_playing = bool(is_playing)
        if self._is_music_playing and not was_playing:
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                reaction = random.choice([
                    "🎧 Oh yeah! Love this track!",
                    "🎶 Dropping the beat!",
                    "🎵 Headphone groove time!",
                ])
                self.overlay.show_speech_bubble(reaction, 2200, "comic")

    def set_low_battery(self, is_low: bool) -> None:
        """Apply exhausted behavior modifications when battery drops below 15%."""
        self._is_low_battery = bool(is_low)
        if is_low and self._is_active:
            current = self.state_machine.current_state
            if current in (CharacterState.WALK, CharacterState.RUN):
                self._on_state_changed(current, current)

    def set_battery_charging(self, is_charging: bool) -> None:
        """Apply energized behavior modifications when laptop is plugged in and charging."""
        self._is_charging = bool(is_charging)
        if is_charging and self._is_active:
            current = self.state_machine.current_state
            if current in (CharacterState.WALK, CharacterState.RUN):
                self._on_state_changed(current, current)

    def set_personality(self, character_id: str) -> None:
        """Switch behavior profile to match the active character's personality."""
        self.personality = get_personality(character_id)
        self._action_timestamps.clear()
        self._recent_actions.clear()
        logger.info("Activated personality profile for: %s", self.personality.display_name)

    def can_perform_action(self, action: str) -> bool:
        """Enforce cooldowns on special moves to prevent repetitive animations."""
        last_time = self._action_timestamps.get(action, 0.0)
        cooldown = self.personality.get_cooldown(
            action, float(self.settings.get("behavior.special_cooldown_seconds", 15.0))
        )
        return (time.monotonic() - last_time) >= cooldown

    def record_action(self, action: str) -> None:
        """Record the timestamp of an executed action for cooldown tracking."""
        self._action_timestamps[action] = time.monotonic()
        if not self._recent_actions or self._recent_actions[-1] != action:
            self._recent_actions.append(action)

    def start(self) -> None:
        """Start autonomous behavior loop."""
        self._is_active = True
        self.animation.set_speed_multiplier(float(self.settings.get("general.animation_speed", 1.0)))
        self.movement.start()
        self._brain_timer.start()
        current = self.state_machine.current_state
        self._on_state_changed(current, current)
        logger.info("BehaviorController started.")

    def stop(self) -> None:
        """Pause autonomous behavior."""
        self._is_active = False
        self._brain_timer.stop()
        self.movement.stop()
        self.animation.pause()
        logger.info("BehaviorController stopped.")

    def _on_state_changed(self, old_state: CharacterState, new_state: CharacterState) -> None:
        """Apply physics velocities and play animations matching the new state."""
        if getattr(self, "_is_pinned", False) and new_state != CharacterState.DRAGGED:
            self.movement.set_motion("hold", 0.0, 0.0)
            self.movement.vx = 0.0
            self.movement.vy = 0.0
            clip = new_state.value if new_state in (CharacterState.TITLE_HANG, CharacterState.TITLE_PERCH, CharacterState.SIT) else "idle"
            self.animation.play(clip)
            self._brain_timer.stop()
            return
        is_user_override = time.monotonic() < self._override_until
        if not is_user_override and not self.activity_enabled(new_state) and new_state.value not in PHYSICAL_STATES:
            self.state_machine.transition_to(CharacterState.IDLE, force=True)
            return
        if new_state in (CharacterState.WAKE_UP, CharacterState.STAND_UP) and not self.activity_enabled(new_state) and not is_user_override:
            self.state_machine.finish_posture_transition()
            return
        self.record_action(new_state.value)

        # Resource management: reduce animation frame rate when sleeping to conserve CPU
        if new_state == CharacterState.SLEEP:
            self.animation.set_reduced_fps(True)
        elif old_state == CharacterState.SLEEP:
            self.animation.set_reduced_fps(False)

        clip_name = new_state.value if (self.activity_enabled(new_state) or is_user_override) else 'idle'
        if not self.animation.play(clip_name):
            self.movement.set_motion("ground")
            self.movement.vx = self.movement.vy = 0.0
            if new_state in (CharacterState.WAKE_UP, CharacterState.STAND_UP):
                self.state_machine.finish_posture_transition()
            elif new_state != CharacterState.IDLE:
                self.state_machine.transition_to(CharacterState.IDLE, force=True)
            return

        speed = max(0.0, float(self.settings.get("behavior.movement_speed", 3.0))) * 60
        profile = self.animation.physics_profile
        factor = speed / 180
        walk_speed = float(profile.get("walk_speed", 3)) * 60 * factor
        run_speed = float(profile.get("run_speed", 5.4)) * 60 * factor
        if self._is_low_battery:
            # Exhausted locomotion: reduced speed
            walk_speed *= 0.6
            run_speed *= 0.6
        elif self._is_charging:
            # Energized locomotion: slightly faster movement
            walk_speed *= 1.2
            run_speed *= 1.2
        climb_speed = float(profile.get("climb_speed", 2.4)) * 60 * factor
        self.movement.gravity = max(1, float(profile.get("gravity", 0.6)) * 3600)
        direction = -1 if self.movement.is_facing_left else 1
        self.animation.set_facing_left(direction < 0)
        self.animation.set_speed_multiplier(float(self.settings.get("general.animation_speed", 1)))
        state = new_state
        if state in (CharacterState.WALK, CharacterState.RUN):
            self.movement.set_motion("ground", direction * (run_speed if state == CharacterState.RUN else walk_speed))
        elif state == CharacterState.JUMP:
            self.movement.set_motion("jump", direction * walk_speed, -abs(float(profile.get("jump_force", -11))) * 60)
            self._last_special = time.monotonic()
        elif state in (CharacterState.FALL, CharacterState.WALL_SLIDE):
            self.movement.set_motion("air")
        elif state in (CharacterState.CLIMB_UP, CharacterState.CLIMB_DOWN):
            self.movement.set_motion("climb", 0, climb_speed * (-1 if state == CharacterState.CLIMB_UP else 1))
        elif state == CharacterState.SWING:
            if not self.movement.begin_swing():
                self.state_machine.transition_to(CharacterState.FALL, force=True)
                return
            self._last_special = time.monotonic()
            if self.overlay and hasattr(self.overlay, "show_speech_bubble") and random.random() < 0.6:
                self.overlay.show_speech_bubble("WHOOSH!", 1600, "action")
        elif state == CharacterState.DRAGGED:
            self.movement.set_motion("drag")
        elif state in (CharacterState.TITLE_PERCH, CharacterState.TITLE_HANG, CharacterState.FOCUS_READ):
            self.movement.set_motion('hold')
            if not self.position_activity(state.value):
                self.state_machine.transition_to(CharacterState.IDLE, force=True)
                return
            if state == CharacterState.TITLE_HANG:
                self.movement.orientation_changed.emit(180.0)
            elif state == CharacterState.FOCUS_READ:
                if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                    self.overlay.show_speech_bubble("Studying the comics!", 2000, "comic")
        elif state in (CharacterState.HANG, CharacterState.PERCH):
            area = self.movement.active_region()
            at_ceiling = area is not None and abs(self.movement.y - area.top()) <= 1
            if at_ceiling or (state == CharacterState.PERCH and self.movement.is_grounded):
                self.movement.set_motion("hold")
            else:
                self.state_machine.transition_to(CharacterState.FALL, force=True)
                return
        elif state == CharacterState.DANCE:
            self.movement.set_motion("ground")
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                self.overlay.show_speech_bubble(self.personality.dance_caption, 2000, "action")
        elif state == CharacterState.CELEBRATE:
            self.movement.set_motion("ground")
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                self.overlay.show_speech_bubble("YES! Nailed it!", 2000, "action")
        elif state == CharacterState.SLEEP:
            self.movement.set_motion("ground")
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                self.overlay.show_speech_bubble("Zzz... power nap...", 2000, "comic")
        else:
            self.movement.set_motion("ground")
        if new_state == CharacterState.LAND and not self.activity_enabled(new_state):
            self.state_machine.transition_to(CharacterState.IDLE,force=True)
            return
        self._schedule_decision()
        if not self._is_active or (clip_name == 'idle' and not self.activity_enabled(CharacterState.IDLE)):
            self.animation.pause()

    def _on_airborne(self):
        if getattr(self, "_is_pinned", False):
            return
        if self.state_machine.current_state not in (
            CharacterState.DRAGGED,
            CharacterState.FALL,
            CharacterState.TITLE_PERCH,
            CharacterState.TITLE_HANG,
            CharacterState.HANG,
            CharacterState.PERCH,
            CharacterState.CLIMB_UP,
            CharacterState.CLIMB_DOWN,
            CharacterState.FOCUS_READ,
        ):
            self.state_machine.transition_to(CharacterState.FALL, force=True)

    def _on_apex(self):
        if getattr(self, "_is_pinned", False):
            return
        if self.state_machine.current_state == CharacterState.JUMP:
            self.state_machine.transition_to(CharacterState.FALL, force=True)

    def _on_swing_released(self):
        if getattr(self, "_is_pinned", False):
            return
        if self.state_machine.current_state == CharacterState.SWING:
            self.state_machine.transition_to(CharacterState.FALL, force=True)

    def _on_trampoline_bounced(self, vx: float, vy: float) -> None:
        """Handle 2D spring trampoline bounce reaction with acrobatic jump and speech bubble."""
        if getattr(self, "_is_pinned", False):
            return
        self.user_override()
        self.state_machine.transition_to(CharacterState.JUMP, force=True)
        if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
            quotes = ["BOING! 🕸️", "TRAMPOLINE BOUNCE! 🚀", "WHOOSH! Nice spring!", "SPRING LAUNCH! ⚡"]
            self.overlay.show_speech_bubble(random.choice(quotes), 1800, "action")
        logger.info("Spider-Man bounced on web trampoline! (vx=%.1f, vy=%.1f)", vx, vy)

    def _sync_gait(self, speed):
        if not self._is_active:
            return
        if self.state_machine.current_state in (CharacterState.WALK, CharacterState.RUN):
            if speed < 1:
                self.animation.pause()
            else:
                self.animation.resume()
                nominal = max(1, abs(self.movement.target_vx))
                multiplier = float(self.settings.get("general.animation_speed", 1))
                self.animation.set_speed_multiplier(multiplier * max(0.15, min(1.5, speed / nominal)))

    def activity_enabled(self, state: CharacterState) -> bool:
        return enabled(self.settings, state.value)

    def _choose(self, options: List[Tuple[CharacterState, float]]) -> None:
        if not self.settings.get("behavior.enable_random_animations", True):
            options = [(CharacterState.IDLE, 1.0)]

        # Filter enabled animations, available sprite clips, and cooldown checks
        choices = []
        for state, base_weight in options:
            if not self.activity_enabled(state):
                continue
            if not self.animation.has_animation(state.value):
                continue
            # Apply cooldown for special actions
            if state in (CharacterState.SWING, CharacterState.DANCE, CharacterState.CELEBRATE,
                         CharacterState.JUMP, CharacterState.WAVE, CharacterState.TITLE_PERCH,
                         CharacterState.TITLE_HANG):
                if not self.can_perform_action(state.value):
                    continue
            # Apply character personality weight modifier
            personality_weight = self.personality.get_weight(state, 1.0)
            weight = base_weight * personality_weight
            # Keep a recognizable personality without repeatedly choosing the same pose.
            weight *= 0.55 ** self._recent_actions.count(state.value)
            if state == self.state_machine.current_state:
                weight *= 0.4
            choices.append((state, weight))

        if not choices:
            return

        preset = self.settings.get("behavior.preset", "normal")
        energetic = (CharacterState.RUN, CharacterState.JUMP, CharacterState.SWING, CharacterState.CLIMB_UP, CharacterState.DANCE)
        modulated = []
        for state, weight in choices:
            if preset == "calm" and state in energetic:
                w = weight * 0.3
            elif preset == "playful" and state in energetic:
                w = weight * 2.0
            elif preset == "calm" and state in (CharacterState.IDLE, CharacterState.SIT):
                w = weight * 2.0
            else:
                w = weight
            modulated.append((state, max(0.01, w)))

        states, weights = zip(*modulated)
        chosen = random.choices(states, weights=weights)[0]
        self.state_machine.transition_to(chosen, force=True)

    def _on_boundary_hit(self, boundary: str) -> None:
        if getattr(self, "_is_pinned", False):
            return
        state = self.state_machine.current_state
        C = CharacterState
        if boundary in ("left_wall", "right_wall") and state in (C.WALK, C.RUN, C.JUMP, C.FALL):
            self.movement.is_facing_left = boundary == "right_wall"
            self.animation.set_facing_left(self.movement.is_facing_left)
            choices = [(C.IDLE, 2.0), (C.WALK, 5.0)]
            if self.settings.get("behavior.enable_climbing", True) and self.can_perform_action("climb"):
                choices.append((C.CLIMB_UP, 4.0))
            if self.can_perform_action("jump") and (time.monotonic() - self._last_special > float(self.settings.get("behavior.special_cooldown_seconds", 20))):
                choices.append((C.JUMP, 1.5))
            self._choose(choices)
            if self.state_machine.current_state == state:
                self._on_state_changed(state, state)
        elif boundary == "ceiling" and state == C.CLIMB_UP:
            choices = [(C.HANG, 3.0), (C.PERCH, 2.0), (C.CLIMB_DOWN, 3.0)]
            self._choose(choices)
        elif boundary == "floor" and state in (C.JUMP, C.FALL, C.CLIMB_DOWN, C.SWING, C.WALL_SLIDE):
            self.state_machine.transition_to(C.LAND, force=True)

    def _on_animation_completed(self, anim_name: str) -> None:
        """Handle completion of one-shot animations."""
        if getattr(self, "_is_pinned", False):
            if anim_name != "idle":
                self.animation.play("idle")
            return
        if self.state_machine.current_state.value != anim_name:
            return
        if anim_name in ["wake_up", "stand_up"]:
            self.state_machine.finish_posture_transition()
            # Phase 10.2: After waking up, wave to the user if friendly
            if anim_name == "wake_up" and self.can_perform_action("wave"):
                self.state_machine.transition_to(CharacterState.WAVE)
        elif anim_name in ["land", "interact", "wave", "dance", "celebrate"]:
            if not self.settings.get("behavior.automatic_animations", True):
                locked = self.settings.get("behavior.locked_activity", "idle")
                if anim_name == locked:
                    self.animation.play(locked)
                    return
                try:
                    self.state_machine.transition_to(CharacterState(locked), force=True)
                    return
                except ValueError:
                    pass
            self.state_machine.transition_to(CharacterState.IDLE)

    def _on_setting_changed(self, key, value):
        if not getattr(self, "_is_active", False):
            return
        if key in ('behavior.focus_mode', 'animations.enabled.focus_read'):
            if self._is_active and self.settings.get('behavior.focus_mode', False):
                self._enter_focus()
            elif self.state_machine.current_state == CharacterState.FOCUS_READ:
                self.state_machine.transition_to(CharacterState.IDLE, force=True)
        if key in ('behavior.automatic_animations', 'behavior.locked_activity'):
            is_auto = self.settings.get('behavior.automatic_animations', True)
            if not is_auto:
                locked = self.settings.get('behavior.locked_activity', 'idle')
                try:
                    self.state_machine.transition_to(CharacterState(locked), force=True)
                except ValueError:
                    pass
            else:
                self._schedule_decision()
        if key == 'animations.title_bar_offset' and self.state_machine.current_state in (CharacterState.TITLE_PERCH, CharacterState.TITLE_HANG):
            self.position_activity(self.state_machine.current_state.value)
        if (key.startswith("behavior.enable_") or key.startswith("animations.enabled.") or key == "animations.enable_window_perching") and not value:
            state = self.state_machine.current_state
            if not self.activity_enabled(state):
                destination = CharacterState.IDLE if self.movement.is_grounded else CharacterState.FALL
                self.state_machine.transition_to(destination, force=True)
            elif key == "behavior.enable_random_animations" and state in (CharacterState.WALK, CharacterState.RUN):
                self.state_machine.transition_to(CharacterState.IDLE, force=True)
        if key == "behavior.preset":
            self._schedule_decision()
        if key == "general.animation_speed":
            self.animation.set_speed_multiplier(float(value))
        elif key == "behavior.movement_speed" and self._is_active:
            state = self.state_machine.current_state
            if state in (CharacterState.WALK, CharacterState.RUN, CharacterState.CLIMB_UP, CharacterState.CLIMB_DOWN):
                self._on_state_changed(state, state)
        elif key == "behavior.enable_swinging" and not value:
            self.movement.release_swing()
        elif key == "behavior.enable_climbing" and not value:
            if self.state_machine.current_state in (CharacterState.CLIMB_UP, CharacterState.CLIMB_DOWN):
                self.state_machine.transition_to(CharacterState.FALL, force=True)

    def user_override(self):
        if getattr(self, "_is_pinned", False):
            return
        self._override_until = time.monotonic() + 30
        self.cursor_attention = False
        self._schedule_decision()

    def handle_wasd(self, horizontal: float, vertical: float, is_shift: bool) -> None:
        """Handle direct manual movement from WASD keys without changing character state.

        Preserves the current animation/state and keeps the companion statically pinned
        in place on screen like Shift key when stopped.
        """
        if not self._is_active:
            return
        if not bool(self.settings.get("behavior.wasd_movement_enabled", True)):
            return

        if horizontal == 0.0 and vertical == 0.0:
            static_pin = bool(self.settings.get("behavior.wasd_static_pin", True))
            if static_pin:
                # Stopped with static pin enabled: hold position statically on screen in current state
                self.movement.set_motion("hold", 0.0, 0.0)
                self.movement.vx = 0.0
                self.movement.vy = 0.0
                self._is_pinned = True
                self._brain_timer.stop()
            else:
                # Static pin disabled: unpin, drop to ground if airborne, and resume autonomy
                self._is_pinned = False
                if self.movement.is_grounded:
                    self.movement.set_motion("ground", 0.0)
                    self.state_machine.transition_to(CharacterState.IDLE, force=True)
                else:
                    self.movement.set_motion("air", 0.0, 0.0)
                    self.state_machine.transition_to(CharacterState.FALL, force=True)
                if self._is_active:
                    self._brain_timer.start()
                    self._schedule_decision()

            # Persist last position so companion reopens where left
            try:
                self.settings.set("general.last_position", [float(self.movement.x), float(self.movement.y)], auto_save=False)
            except Exception:
                pass
            return

        # Moving with WASD: pause autonomous timer, remain in current state
        self._is_pinned = True
        self._brain_timer.stop()

        base_speed = max(1.0, float(self.settings.get("behavior.movement_speed", 3.0))) * 75.0
        run_multiplier = 1.6 if is_shift else 1.0
        speed = base_speed * run_multiplier

        # Horizontal direction & steering
        if horizontal < 0:
            self.movement.is_facing_left = True
            self.movement.direction_changed.emit(True)
            self.animation.set_facing_left(True)
        elif horizontal > 0:
            self.movement.is_facing_left = False
            self.movement.direction_changed.emit(False)
            self.animation.set_facing_left(False)

        vx = horizontal * speed
        vy = vertical * speed

        # Direct 2D movement in hold mode preserving current state and animation
        self.movement.set_motion("hold", vx, vy)
        self.animation.resume()

    def drop_to_ground(self) -> None:
        """Release static hold / pin when Spacebar is pressed and let companion fall and land on ground."""
        if not self._is_active:
            return
        if getattr(self, "_is_pinned", False) or self.movement.mode == "hold":
            self.set_pinned(False)
            self.movement.orientation_changed.emit(0.0)
            self.movement.web_changed.emit(None)
            self.state_machine.transition_to(CharacterState.FALL, force=True)
            logger.info("Companion unpinned and dropped to ground via Spacebar.")


    def resume_autonomy(self):
        self.cursor_attention = False
        if getattr(self, "_is_pinned", False):
            return
        if self._is_active:
            self._schedule_decision()

    def update_idle(self, seconds: float) -> None:
        """Handle user inactivity progression and return-to-activity reactions."""
        if getattr(self, "_is_pinned", False) or self.state_machine.current_state in (CharacterState.TITLE_HANG, CharacterState.TITLE_PERCH):
            return
        if self.settings.get('behavior.focus_mode', False):
            if self._is_active:
                self._enter_focus()
            return
        previous_seconds = self._idle_seconds
        self._idle_seconds = seconds

        relax = max(1, float(self.settings.get("behavior.inactivity.relax_seconds", 120)))
        sit = max(relax, float(self.settings.get("behavior.inactivity.sit_seconds", 300)))
        sleep = max(sit, float(self.settings.get("behavior.inactivity.sleep_seconds", 600)))
        stage = 3 if seconds >= sleep else 2 if seconds >= sit else 1 if seconds >= relax else 0
        previous_stage, self._idle_stage = self._idle_stage, stage

        if not self._is_active:
            return

        C = CharacterState

        # Phase 10.2: Smart Activity Reaction: User returns after inactivity
        if (previous_stage > stage and stage == 0) or (seconds < 5.0 and previous_seconds > 60.0):
            current = self.state_machine.current_state
            if current == C.SLEEP:
                # Wake up and wave
                self.state_machine.transition_to(C.WAKE_UP, force=True)
                self.resume_autonomy()
                return
            elif current == C.SIT:
                # Wave to returning user
                self.state_machine.transition_to(C.WAVE, force=True)
                self.resume_autonomy()
                return
            elif self.can_perform_action("wave") and random.random() < 0.5:
                self.state_machine.transition_to(C.WAVE, force=True)
                self.resume_autonomy()
                return

        if time.monotonic() < self._override_until or self.cursor_attention:
            return

        state = self.state_machine.current_state
        if stage >= 2 and state in (C.HANG, C.PERCH, C.CLIMB_UP, C.CLIMB_DOWN):
            self.state_machine.transition_to(C.FALL, force=True)
            return

        safe = state in (C.IDLE, C.WALK, C.RUN, C.SIT, C.SLEEP)
        if not safe or not self.movement.is_grounded:
            return

        if stage >= 2:
            destination = C.SLEEP if stage == 3 and self.activity_enabled(C.SLEEP) else C.SIT
            if not self.activity_enabled(destination):
                destination = C.IDLE
            if state != destination and self.activity_enabled(destination) and self.animation.has_animation(destination.value):
                self.state_machine.transition_to(destination, force=True)
        elif stage == 1 and previous_stage != stage and state in (C.WALK, C.RUN):
            self.state_machine.transition_to(C.IDLE, force=True)

    def on_application_entered(self, is_new_app: bool = True) -> None:
        """Phase 10.2: Smart reaction when a selected application is brought into front."""
        if not self._is_active or getattr(self, "_is_pinned", False) or self.state_machine.current_state in (CharacterState.TITLE_HANG, CharacterState.TITLE_PERCH):
            return
        if is_new_app:
            C = CharacterState
            if self.movement.is_grounded:
                if self.can_perform_action("wave") and random.random() < 0.4:
                    self.state_machine.transition_to(C.WAVE, force=True)
                elif self.animation.has_animation("land"):
                    self.state_machine.transition_to(C.LAND, force=True)

    def _schedule_decision(self):
        if getattr(self, "_is_pinned", False):
            self._brain_timer.stop()
            return
        state = self.state_machine.current_state.value
        defaults = {
            "idle": (4, 9),
            "walk": (6, 12),
            "run": (3, 6),
            "sit": (10, 20),
            "sleep": (25, 50),
            "hang": (3, 6),
            "perch": (4, 8),
            "dance": (4, 8),
            "title_perch": (15, 30),
            "title_hang": (10, 20),
            "focus_read": (30, 60),
        }
        low, high = defaults.get(state, (4, 8))
        low = max(1.0, float(self.settings.get(f"behavior.durations.{state}.min", low)))
        high = max(low, float(self.settings.get(f"behavior.durations.{state}.max", high)))
        preset = self.settings.get("behavior.preset", "normal")
        factor = 1.6 if preset == "calm" else 0.7 if preset == "playful" else 1.0
        # Factor in personality duration factor
        personality_factor = getattr(self.personality, "duration_factor", 1.0)
        total_factor = factor * personality_factor
        self._brain_timer.setInterval(round(random.uniform(low, high) * total_factor * 1000))

    def _enter_focus(self):
        if getattr(self, "_is_pinned", False) or self.state_machine.current_state == CharacterState.DRAGGED:
            return
        destination = (CharacterState.FOCUS_READ if self.activity_enabled(CharacterState.FOCUS_READ)
                       else CharacterState.IDLE)
        if self.state_machine.current_state != destination:
            self.state_machine.transition_to(destination, force=True)
        if destination == CharacterState.IDLE:
            self.movement.set_motion('ground')

    def _decide_next_action(self):
        if not self._is_active:
            return
        if getattr(self, "_is_pinned", False):
            self._brain_timer.stop()
            return
        if not self.settings.get("behavior.automatic_animations", True):
            locked = self.settings.get("behavior.locked_activity", "idle")
            try:
                target_state = CharacterState(locked)
                if self.state_machine.current_state != target_state:
                    self.state_machine.transition_to(target_state, force=True)
                elif not self.animation.is_playing:
                    self.animation.play(locked)
            except ValueError:
                pass
            self._schedule_decision()
            return
        if self.settings.get('behavior.focus_mode', False):
            self._enter_focus()
            return
        if not self._is_active or not self.movement.regions or self.cursor_attention or not self.settings.get("behavior.enable_random_animations", True):
            return
        C = CharacterState
        state = self.state_machine.current_state

        if self._idle_stage >= 2 and time.monotonic() >= self._override_until:
            self.update_idle(self._idle_seconds)
            return

        if state in (C.IDLE, C.WALK, C.RUN):
            if self._is_low_battery:
                # Exhausted: heavily favor sitting or resting quietly
                choices = [(C.SIT, 6.0), (C.IDLE, 5.0), (C.WALK, 1.5)]
            elif self._is_charging:
                # Energized / power surge: high energy, active moves and celebrations
                choices = [(C.RUN, 5.0), (C.WALK, 5.0), (C.CELEBRATE, 3.5), (C.DANCE, 2.5), (C.IDLE, 2.0)]
            elif self._idle_stage:
                choices = [(C.IDLE, 8.0), (C.WALK, 2.0), (C.SIT, 5.0)]
            else:
                choices = [(C.IDLE, 5.0), (C.WALK, 6.0), (C.RUN, 2.0), (C.SIT, 3.0)]
            if not self._idle_stage and self.movement.is_grounded:
                # Check jump and swing with cooldowns
                if self.can_perform_action("jump") and (time.monotonic() - self._last_special > float(self.settings.get("behavior.special_cooldown_seconds", 20))):
                    choices.append((C.JUMP, 2.0))
                if self.settings.get("behavior.enable_swinging", True) and self.can_perform_action("swing"):
                    choices.append((C.SWING, 1.5))
                # Every character shares the repertoire; personality controls frequency.
                choices.extend([(C.DANCE, 1.5), (C.WAVE, 1.5), (C.CELEBRATE, 1.0)])

            if self.settings.get("animations.enable_window_perching", True):
                if self.can_perform_action('title_perch') and self.activity_enabled(C.TITLE_PERCH):
                    choices.append((C.TITLE_PERCH, 2.8))
                if self.can_perform_action('title_hang') and self.activity_enabled(C.TITLE_HANG):
                    choices.append((C.TITLE_HANG, 1.5))
            if random.random() < 0.25:
                self.movement.is_facing_left = not self.movement.is_facing_left

            self._choose(choices)
            if self.state_machine.current_state == state and state in (C.WALK, C.RUN):
                self._on_state_changed(state, state)
        elif state == C.SIT:
            self._choose([(C.IDLE, 1.0)])
        elif state == C.SLEEP:
            self._choose([(C.IDLE, 1.0)])
        elif state in (C.TITLE_PERCH, C.TITLE_HANG):
            # Explicit title-bar docking lasts indefinitely until user triggers another action
            self._brain_timer.stop()
            return
        elif state in (C.PERCH, C.HANG):
            choices = [(C.FALL, 2.0)]
            if self.settings.get("behavior.enable_climbing", True):
                choices.append((C.CLIMB_DOWN, 3.0))
            if self.settings.get("behavior.enable_swinging", True) and self.can_perform_action("swing"):
                choices.append((C.SWING, 1.5))
            self._choose(choices)
        self._schedule_decision()
