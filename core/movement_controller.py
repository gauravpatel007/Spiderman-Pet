"""Movement physics and coordinate controller."""
import logging
import math
import time
from typing import Optional, Tuple
from PySide6.QtCore import QObject, QTimer, Signal, QRect
from PySide6.QtGui import QRegion

logger = logging.getLogger("SpiderBuddy.MovementController")


class MovementController(QObject):
    """
    Manages 2D physics, velocity, collisions, and spatial coordinates.
    Keeps movement logic independent from animation rendering.
    """

    position_changed = Signal(int, int)       # (x, y)
    direction_changed = Signal(bool)          # True if facing left, False if facing right
    boundary_hit = Signal(str)                # 'floor', 'left_wall', 'right_wall', 'ceiling'

    airborne = Signal()
    apex_reached = Signal()
    swing_released = Signal()
    motion_changed = Signal(float)
    orientation_changed = Signal(float)
    web_changed = Signal(object)
    trampoline_bounced = Signal(float, float)  # (rebound_vx, rebound_vy)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.x: float = 300.0
        self.y: float = 300.0
        self.vx: float = 0.0
        self.vy: float = 0.0

        self.width: int = 128
        self.height: int = 128

        self.bounds: QRect = QRect(0, 0, 1920, 1080)
        self.regions = [QRect(self.bounds)]
        self.allow_monitor_transitions = False
        self.gravity: float = 2160.0
        self.friction: float = 0.85
        self.max_speed: float = 720.0
        self.is_grounded: bool = False
        self.is_facing_left: bool = False
        self.is_dragging: bool = False
        self.active_trampoline = None

        self.mode = 'ground'
        self.target_vx = 0.0
        self.acceleration = 900.0
        self._swing = None
        self._last_tick = time.monotonic()
        self._contacts = set()
        # Physics tick timer (60 Hz)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._update_physics)

    def set_active_trampoline(self, trampoline) -> None:
        """Assign or update active web trampoline for bounce physics."""
        self.active_trampoline = trampoline

    def clear_trampoline(self) -> None:
        """Clear active web trampoline."""
        self.active_trampoline = None

    def set_display_fps(self, fps):
        self._timer.setInterval(33 if int(fps) == 30 else 16)

    def set_bounds(self, rect: QRect) -> None:
        """Update containment bounds (desktop screen or application window)."""
        self.set_regions([rect])

    def set_size(self, width: int, height: int) -> None:
        if (width, height) != (self.width, self.height) and self._swing:
            self.release_swing()
        self.width = width
        self.height = height

    def start(self) -> None:
        self._last_tick = time.monotonic()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.set_motion("ground")
        self.vx = 0.0
        self.vy = 0.0

    def set_position(self, x: float, y: float) -> None:
        if self._swing:
            self.release_swing()
        self.x = x
        self.y = y
        self.clamp_to_bounds()
        self.is_grounded = self._project_position(self.x, self.y+1)[1] < self.y+0.5
        rx, ry = round(self.x), round(self.y)
        if getattr(self, '_last_emitted_pos', None) != (rx, ry):
            self._last_emitted_pos = (rx, ry)
            self.position_changed.emit(rx, ry)

    def move_to(self, x: float, y: float) -> None:
        self.set_position(x, y)

    def set_regions(self, regions) -> None:
        updated = [QRect(r) for r in regions if not r.isEmpty()]
        if updated != self.regions and self._swing:
            self.release_swing()
        self.regions = updated
        self.bounds = QRect()
        for region in self.regions:
            self.bounds = self.bounds.united(region)
        self.clamp_to_bounds()

    def _project_position(self, x, y):
        allowed = QRegion()
        for area in self.regions:
            allowed |= QRegion(area)
        # Cover fractional edges conservatively: rounding allowed up to half a
        # pixel below the floor, followed by a snap back on the next substep.
        left, top = math.floor(x), math.floor(y)
        footprint = QRegion(QRect(left, top, math.ceil(x + self.width) - left,
                                 math.ceil(y + self.height) - top))
        if footprint.subtracted(allowed).isEmpty():
            return x, y
        candidates = []
        for area in self.regions:
            if area.width() < self.width or area.height() < self.height:
                continue
            px = max(area.x(), min(x, area.x()+area.width()-self.width))
            py = max(area.y(), min(y, area.y()+area.height()-self.height))
            candidates.append(((px-x)**2+(py-y)**2, px, py))
        if not candidates:
            return self.x, self.y
        _, px, py = min(candidates)
        return px, py

    def clamp_to_bounds(self) -> None:
        if self.regions:
            self.x, self.y = self._project_position(self.x, self.y)
            rx, ry = round(self.x), round(self.y)
            if getattr(self, '_last_emitted_pos', None) != (rx, ry):
                self._last_emitted_pos = (rx, ry)
                self.position_changed.emit(rx, ry)

    def _monitor_transition(self, x, y):
        if not self.allow_monitor_transitions or self.is_dragging:
            return x, y
        current = next((r for r in self.regions if r.contains(round(self.x+self.width/2), round(self.y+self.height/2))), None)
        if current is None:
            return x, y
        side = 1 if self.vx > 0 and x+self.width > current.x()+current.width() else -1 if self.vx < 0 and x < current.x() else 0
        if not side:
            vertical = 1 if self.vy > 0 and y+self.height > current.y()+current.height() else -1 if self.vy < 0 and y < current.y() else 0
            targets = [r for r in self.regions if r.width() >= self.width and r.height() >= self.height
                       and vertical and (r.center().y()-current.center().y())*vertical > 0]
            if targets:
                target = min(targets, key=lambda r: (r.center().x()-current.center().x())**2+(r.center().y()-current.center().y())**2)
                fraction = max(0, min(1, (self.x-current.x())/max(1,current.width()-self.width)))
                return (target.x()+fraction*(target.width()-self.width),
                        target.y() if vertical > 0 else target.y()+target.height()-self.height)
            return x, y
        choices = [r for r in self.regions if r.width() >= self.width and r.height() >= self.height
                   and (r.center().x()-current.center().x())*side > 0]
        if not choices:
            return x, y
        target = min(choices, key=lambda r: (r.center().x()-current.center().x())**2+(r.center().y()-current.center().y())**2)
        fraction = max(0, min(1, (self.y-current.y())/max(1,current.height()-self.height)))
        return (target.x() if side > 0 else target.x()+target.width()-self.width,
                target.y()+fraction*(target.height()-self.height))

    def set_motion(self, mode, horizontal=0.0, vertical=0.0):
        self._swing = None
        self.web_changed.emit(None)
        self.orientation_changed.emit(0.0)
        self.mode = mode
        self.target_vx = horizontal
        self._contacts.clear()
        if mode in ('hold', 'climb', 'drag'):
            self.vx, self.vy = horizontal, vertical
        elif mode == 'jump':
            self.mode = 'air'
            self.vy = vertical
            self.is_grounded = False
        elif mode == 'air':
            self.target_vx = self.vx
        if mode == 'climb':
            area = self.active_region()
            if area:
                left = abs(self.x-area.left()) <= abs(self.x+self.width-area.x()-area.width())
                self.x = area.left() if left else area.x()+area.width()-self.width
                self.orientation_changed.emit(-90.0 if left else 90.0)

    def active_region(self):
        return next((r for r in self.regions if r.contains(
            round(self.x+self.width/2), round(self.y+self.height/2))
            and r.width() >= self.width and r.height() >= self.height), None)

    def begin_swing(self):
        area = self.active_region()
        if area is None:
            return False
        cx, cy = self.x+self.width/2, self.y+self.height/2
        length = min(cy-area.top()-12, area.height()*0.65, area.width()*0.4)
        if length < self.height*0.6:
            return False
        self.set_motion('swing')
        self._swing = [cx, cy-length, length, 0.0,
                       -1.15 if self.is_facing_left else 1.15, 0.0]
        self.is_grounded = False
        return True

    def release_swing(self):
        if self._swing is None:
            return
        self._swing = None
        self.mode = 'air'
        self.target_vx = self.vx
        self.web_changed.emit(None)
        self.orientation_changed.emit(0.0)
        self.swing_released.emit()

    def _update_physics(self):
        now = time.monotonic()
        elapsed = min(0.08, max(0.0, now-self._last_tick))
        self._last_tick = now
        if self.is_dragging or not self.regions:
            return
        # Small bounded substeps preserve collision behavior after a late callback.
        while elapsed > 0:
            dt = min(elapsed, 1/120)
            elapsed -= dt
            self._step(dt)
        self.motion_changed.emit(abs(self.vx))

    def _step(self, dt):
        previous_vy = self.vy
        if self._swing:
            ax, ay, length, angle, omega, age = self._swing
            omega += (-self.gravity/length*math.sin(angle)-0.12*omega)*dt
            angle += omega*dt
            self._swing = [ax, ay, length, angle, omega, age+dt]
            nx = ax+length*math.sin(angle)-self.width/2
            ny = ay+length*math.cos(angle)-self.height/2
            self.vx = length*math.cos(angle)*omega
            self.vy = -length*math.sin(angle)*omega
        else:
            delta = self.target_vx-self.vx
            self.vx += max(-self.acceleration*dt, min(delta, self.acceleration*dt))
            if self.mode not in ('hold', 'climb', 'drag'):
                self.vy = min(1000.0, self.vy+self.gravity*dt)
            nx, ny = self.x+self.vx*dt, self.y+self.vy*dt
            if self.mode == 'ground':
                nx, ny = self._monitor_transition(nx, ny)

        # Check interactive web trampoline bounce
        if (
            self.active_trampoline
            and getattr(self.active_trampoline, "is_active", lambda: False)()
            and self.mode not in ('hold', 'climb', 'drag')
            and self.vy > 0
        ):
            p1, p2 = self.active_trampoline.get_endpoints()
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            seg_len = math.hypot(dx, dy)
            if seg_len >= 15.0:
                prev_feet_y = self.y + self.height
                curr_feet_x = nx + self.width * 0.5
                curr_feet_y = ny + self.height

                # Project feet onto trampoline line segment
                t = ((curr_feet_x - p1.x()) * dx + (curr_feet_y - p1.y()) * dy) / (seg_len * seg_len)
                if 0.0 <= t <= 1.0:
                    qx = p1.x() + t * dx
                    qy = p1.y() + t * dy

                    # Contact when moving down and feet reach or pass through the web
                    if (prev_feet_y <= qy + 12.0 and curr_feet_y >= qy - 12.0) or abs(curr_feet_y - qy) < 18.0:
                        # 2D Spring Rebound Formula: upward normal and elastic bounce
                        nx_u = -dy / seg_len
                        ny_u = dx / seg_len
                        if ny_u > 0:
                            nx_u, ny_u = -nx_u, -ny_u

                        impact_speed = math.hypot(self.vx, self.vy)
                        spring_rebound_vy = -max(780.0, min(1180.0, abs(self.vy) * 1.35 + 320.0))
                        spring_rebound_vx = self.vx * 0.85 + nx_u * 220.0

                        self.vx = spring_rebound_vx
                        self.vy = spring_rebound_vy
                        self.mode = 'air'
                        self.target_vx = self.vx
                        self.is_grounded = False

                        ny = qy - self.height - 2.0  # place right above web

                        # Trigger visual spring oscillation on the trampoline
                        self.active_trampoline.trigger_bounce(impact_speed=impact_speed)
                        self.trampoline_bounced.emit(self.vx, self.vy)

        px, py = self._project_position(nx, ny)
        contacts = set()
        if abs(px-nx) > 0.001:
            contacts.add('right_wall' if nx > px else 'left_wall')
        if abs(py-ny) > 0.001:
            contacts.add('floor' if ny > py else 'ceiling')
        self.x, self.y = px, py
        self.is_grounded = 'floor' in contacts or self._project_position(px, py+1)[1] < py+0.5
        if any(c.endswith('wall') for c in contacts):
            self.vx = 0.0
        if 'floor' in contacts or 'ceiling' in contacts:
            self.vy = 0.0
        if abs(self.vx) > 1:
            facing = self.vx < 0
            if facing != self.is_facing_left:
                self.is_facing_left = facing
                self.direction_changed.emit(facing)
        rx, ry = round(self.x), round(self.y)
        if getattr(self, '_last_emitted_pos', None) != (rx, ry):
            self._last_emitted_pos = (rx, ry)
            self.position_changed.emit(rx, ry)
        fresh = contacts-self._contacts
        self._contacts = contacts
        if self._swing:
            ax, ay, length, angle, omega, age = self._swing
            if contacts or age >= 3.5:
                self.release_swing()
            else:
                self.orientation_changed.emit(math.degrees(-angle)*0.65)
                self.web_changed.emit(((ax, ay), (self.x+self.width/2, self.y+self.height*0.25)))
        if previous_vy < 0 <= self.vy and self.mode == 'air':
            self.apex_reached.emit()
        if self.mode == 'ground' and not self.is_grounded and self.vy > 40:
            self.mode = 'air'
            self.airborne.emit()
        for contact in sorted(fresh):
            self.boundary_hit.emit(contact)
