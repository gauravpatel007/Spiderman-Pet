"""🕷️ Spider-Buddy Full Activity Automation Script.

Automates and choreographs the complete suite of all activities that Spider-Man performs:
- Phase 1: Waking up & Greeting (wake_up, idle, wave)
- Phase 2: Ground Traversal & Swagger (walk, run, dance, celebrate)
- Phase 3: Aerial Acrobatics & Physics (jump, fall, land, swing)
- Phase 4: Wall & Ceiling Mastery (climb_up, perch, hang, climb_down, wall_slide, land)
- Phase 5: Interactive Responses & Web Shooting (interact, shoot_web, dragged)
- Phase 6: Rest & Sleep (sit, stand_up, sleep)

Usage:
    python scripts/automate_all_activities.py [--character miles_morales|tom_holland] [--speed 1.0] [--loop] [--headless]
"""
import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bootstrap import bootstrap_environment
bootstrap_environment()

from PySide6.QtCore import Qt, QTimer, QPoint, QRect
from PySide6.QtGui import QColor, QFont, QPainter, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout

from core.state_machine import StateMachine, CharacterState as C
from core.character_manager import CharacterManager
from core.animation_engine import AnimationEngine
from core.movement_controller import MovementController
from core.behavior_controller import BehaviorController
from core.interaction_manager import InteractionManager
from overlay.overlay_manager import OverlayManager
from services.settings_service import get_settings


ACTIVITIES = [
    # 1. Waking up & greetings
    ("wake_up", "Awakens, stretches, and rubs eyes", 2.5),
    ("idle", "Stands naturally with subtle breathing rhythm", 2.0),
    ("wave", "Friendly Spider-Man greeting wave", 2.5),

    # 2. Ground mobility & expression
    ("walk", "Walks across the surface in facing direction", 3.0),
    ("run", "Sprints with athletic Spider-Man momentum", 2.5),
    ("dance", "Vibrant hip-hop dance routine", 3.5),
    ("celebrate", "Victory fist-pump celebration", 2.5),

    # 3. Aerial acrobatics & physics
    ("jump", "Launches vertically into an acrobatic leap", 2.2),
    ("fall", "Airborne drop under gravity", 1.8),
    ("land", "Low-crouch hero landing pose", 2.0),
    ("swing", "Fires web strand and swings in a pendulum arc", 3.5),

    # 4. Wall & Ceiling Mastery
    ("climb_up", "Scales window boundary vertically upward", 2.8),
    ("perch", "Crouches atop upper window ledge", 2.0),
    ("hang", "Hangs upside-down from ceiling web", 3.0),
    ("climb_down", "Descends boundary surface", 2.2),
    ("wall_slide", "Slides down wall with friction contact", 1.8),
    ("land", "Smooth recovery landing on ground", 1.8),

    # 5. Interactive Responses
    ("interact", "Looks toward user attention / cursor", 2.2),
    ("shoot_web", "Fires dynamic web line directly toward cursor", 2.2),
    ("dragged", "Elevated drag pose following cursor", 2.2),

    # 6. Rest & Sleep
    ("sit", "Sits casually along the surface edge", 3.0),
    ("stand_up", "Stands back up onto feet", 2.0),
    ("sleep", "Lies down sleeping with soft breathing rhythm", 3.5),
    ("wake_up", "Awakens refreshed and ready for action", 2.2),
    ("idle", "Returns to relaxed companion idle state", 2.0),
]


class AutomationHUD(QWidget):
    """Floating transparent HUD displaying live activity progress, stats, and description."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(460, 100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        self.title_label = QLabel("🕷️ SPIDER-BUDDY AUTOMATED SHOWCASE")
        self.title_label.setStyleSheet("font-size: 11px; font-weight: 800; color: #E50914; letter-spacing: 1px;")
        layout.addWidget(self.title_label)

        self.step_label = QLabel("Activity: Initializing...")
        self.step_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(self.step_label)

        self.desc_label = QLabel("Description...")
        self.desc_label.setStyleSheet("font-size: 12px; color: #B0B8C8;")
        layout.addWidget(self.desc_label)

        self.stats_label = QLabel("Stats: --")
        self.stats_label.setStyleSheet("font-size: 11px; color: #00F0FF; font-family: Consolas, monospace;")
        layout.addWidget(self.stats_label)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(18, 20, 28, 220))
        painter.setPen(QColor(229, 9, 20, 200))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)

    def update_info(self, step_idx: int, total: int, act_name: str, desc: str, stats: str):
        self.step_label.setText(f"[{step_idx + 1}/{total}] {act_name.upper().replace('_', ' ')}")
        self.desc_label.setText(desc)
        self.stats_label.setText(stats)
        self.update()


class ActivityAutomator:
    """Orchestrates sequential execution of all Spider-Buddy activities."""

    def __init__(self, character_id="miles_morales", speed=1.0, loop=False, headless=False):
        self.character_id = character_id
        self.speed = max(0.2, float(speed))
        self.loop = loop
        self.headless = headless

        self.current_index = 0
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._step)

        self._setup_engine()

    def _setup_engine(self):
        self.settings = get_settings()
        self.char_mgr = CharacterManager()
        self.char_mgr.set_active_character(self.character_id)

        self.sm = StateMachine(initial_state=C.IDLE)
        self.anim = AnimationEngine()
        self.mov = MovementController()
        self.bc = BehaviorController(self.sm, self.mov, self.anim)
        self.im = InteractionManager(self.sm, self.mov, self.char_mgr, self.anim, self.bc)

        profile = self.char_mgr.active_character
        self.anim.set_character(profile)
        self.bc.set_personality(profile.id)

        if not self.headless:
            self.overlay_mgr = OverlayManager(self.mov)
            self.overlay_mgr.start()
            self.anim.frame_updated.connect(self.overlay_mgr.overlay.set_frame)
            self.im.overlay = self.overlay_mgr.overlay

            # Create HUD
            self.hud = AutomationHUD()
            self._position_hud()
            self.hud.show()
        else:
            self.overlay_mgr = None
            self.hud = None

    def _position_hud(self):
        if self.hud:
            screen = QApplication.primaryScreen().geometry()
            self.hud.move(screen.width() - self.hud.width() - 30, 40)

    def start(self):
        print("==================================================")
        print(f"🕷️ SPIDER-BUDDY AUTOMATION: {self.char_mgr.active_character.display_name}")
        print(f"[*] Total activities: {len(ACTIVITIES)}")
        print(f"[*] Speed factor: {self.speed}x")
        print(f"[*] Continuous loop: {self.loop}")
        print("==================================================")
        self.current_index = 0
        self._step()

    def _step(self):
        if self.current_index >= len(ACTIVITIES):
            if self.loop:
                print("\n[🔄] Looping choreography from the beginning...\n")
                self.current_index = 0
            else:
                print("\n==================================================")
                print("✅ ALL ACTIVITIES SUCCESSFULLY AUTOMATED!")
                print("==================================================")
                if not self.headless:
                    QTimer.singleShot(2000, QApplication.instance().quit)
                return

        name, desc, duration = ACTIVITIES[self.current_index]
        adjusted_duration = max(0.5, duration / self.speed)

        # Execute activity actions
        self._execute_activity(name)

        # Update stats
        pos_x = int(self.mov.x)
        pos_y = int(self.mov.y)
        facing = "Left" if self.mov.is_facing_left else "Right"
        grounded = "Yes" if self.mov.is_grounded else "No"
        stats_str = f"Pos: ({pos_x}, {pos_y}) | Grounded: {grounded} | Facing: {facing} | Dur: {adjusted_duration:.1f}s"

        print(f"[{self.current_index + 1:02d}/{len(ACTIVITIES):02d}] {name.upper():<14} | {desc}")

        if self.hud:
            self.hud.update_info(self.current_index, len(ACTIVITIES), name, desc, stats_str)

        self.current_index += 1
        self.timer.start(int(adjusted_duration * 1000))

    def _execute_activity(self, name: str):
        if name == "shoot_web":
            # Fire visible web strand toward top right
            target = QPoint(int(self.mov.x + 240), int(self.mov.y - 180))
            self.im.shoot_web_at(target)
            return

        try:
            state = C(name)
        except ValueError:
            return

        # Special physical setup for specific actions
        if state == C.WALK:
            self.mov.is_facing_left = False
            self.anim.set_facing_left(False)
            self.sm.transition_to(C.WALK, force=True)
            self.bc._on_state_changed(C.WALK, C.WALK)
        elif state == C.RUN:
            self.mov.is_facing_left = True
            self.anim.set_facing_left(True)
            self.sm.transition_to(C.RUN, force=True)
            self.bc._on_state_changed(C.RUN, C.RUN)
        elif state == C.JUMP:
            self.sm.transition_to(C.JUMP, force=True)
            self.bc._on_state_changed(C.JUMP, C.JUMP)
        elif state == C.SWING:
            self.sm.transition_to(C.SWING, force=True)
            self.bc._on_state_changed(C.SWING, C.SWING)
        elif state == C.CLIMB_UP:
            self.sm.transition_to(C.CLIMB_UP, force=True)
            self.bc._on_state_changed(C.CLIMB_UP, C.CLIMB_UP)
        elif state == C.CLIMB_DOWN:
            self.sm.transition_to(C.CLIMB_DOWN, force=True)
            self.bc._on_state_changed(C.CLIMB_DOWN, C.CLIMB_DOWN)
        elif state == C.DRAGGED:
            self.sm.transition_to(C.DRAGGED, force=True)
            self.bc._on_state_changed(C.DRAGGED, C.DRAGGED)
        else:
            self.sm.transition_to(state, force=True)
            self.bc._on_state_changed(state, state)


def main():
    parser = argparse.ArgumentParser(description="Automate all Spider-Buddy character activities.")
    parser.add_argument("--character", choices=["miles_morales", "tom_holland"], default="miles_morales",
                        help="Character to automate (default: miles_morales)")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier (e.g. 1.0, 1.5, 2.0)")
    parser.add_argument("--loop", action="store_true", help="Loop activities continuously")
    parser.add_argument("--headless", action="store_true", help="Run without showing GUI overlays")
    args = parser.parse_args()

    qapp = QApplication.instance() or QApplication(sys.argv)
    qapp.setApplicationName("SpiderBuddy_Automator")

    automator = ActivityAutomator(
        character_id=args.character,
        speed=args.speed,
        loop=args.loop,
        headless=args.headless
    )

    QTimer.singleShot(100, automator.start)

    if args.headless:
        # Run event loop until all steps finish
        total_time = sum(act[2] for act in ACTIVITIES) / args.speed + 2.0
        QTimer.singleShot(int(total_time * 1000), qapp.quit)

    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
