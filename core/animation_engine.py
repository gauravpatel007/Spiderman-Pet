"""Elapsed-time sprite playback with manifest timing, alignment and bounded caching."""
from bisect import bisect_right
from collections import OrderedDict
from dataclasses import dataclass
import json
import logging
import math
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QElapsedTimer, QTimer, Qt, Signal
from PySide6.QtGui import QPainter, QPixmap, QTransform

logger = logging.getLogger('SpiderBuddy.AnimationEngine')


@dataclass
class Clip:
    name: str
    frames: list
    offsets: list
    anchors: list
    deadlines: list
    loop: bool
    mirror: bool
    source_left: bool
    cache_key: tuple
    interpolate_offsets: bool = True

    @property
    def duration(self):
        return self.deadlines[-1]


class AnimationEngine(QObject):
    frame_updated = Signal(QPixmap)
    animation_completed = Signal(str)
    animation_cancelled = Signal(str)
    animation_unavailable = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._character = None
        self._display_fps = 60
        self._current_animation = 'idle'
        self._current_frame_idx = 0
        self._is_facing_left = False
        self._scale = self._opacity = self._speed_multiplier = 1.0
        self._animation_configs = self._load_default_animation_configs()
        self._manifest = {}
        self._clips = {}
        self._frame_cache = OrderedDict()
        self._cache_bytes = 0
        self._cache_limit = 48 * 1024 * 1024
        self._canvas = (512,512)
        self._anchor = (256,488)
        self._clip = None
        self._playing = False
        self._completed = False
        self._position_ms = 0.0
        self._last_ns = 0
        self._generation = 0
        self._emitted_key = None
        self._queue = []
        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._advance_frame)
        self._current_fps = 12
        self._reduced_fps = False
        self._suspended = False

    def _load_default_animation_configs(self):
        import sys
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
            path = base / "config" / "animations.json"
        else:
            path = Path(__file__).resolve().parents[1] / "config" / "animations.json"
        try:
            return json.loads(path.read_text(encoding='utf-8')).get('animations',{})
        except (OSError,ValueError):
            return {'idle':{'fps':12,'loop':True}}

    @property
    def physics_profile(self):
        return dict(self._character.physics) if self._character else {}

    @property
    def is_playing(self) -> bool:
        return bool(self._playing)

    def set_character(self, character):
        self.cancel()
        self._character=character
        self._clips.clear()
        self._frame_cache.clear()
        self._cache_bytes=0
        self._animation_configs=self._load_default_animation_configs()
        try:
            self._manifest=json.loads((character.root_path/'animation_manifest.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):
            self._manifest={}
        canvas=self._manifest.get('canvas',[512,512])
        self._canvas=tuple(max(1,min(2048,int(v))) for v in canvas[:2])
        self._anchor=tuple(self._manifest.get('anchor',[self._canvas[0]/2,self._canvas[1]-24]))
        for name,config in self._manifest.get('animations',{}).items():
            self._animation_configs[name]={**self._animation_configs.get(name,{}),**config}
        desired=self._current_animation
        if not self.play(desired,force_restart=True):
            self.play('idle',force_restart=True)

    def _asset_path(self, relative):
        root=self._character.root_path.resolve()
        path=(root/relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Animation frame path must stay inside its character folder')
        return path

    def _get_clip(self,name):
        direction='left' if self._is_facing_left else 'right'
        key=(name,direction)
        if key in self._clips:
            return self._clips[key]
        if self._character is None:
            return None
        source_name = {'title_perch':'perch','title_hang':'hang','focus_read':'sit'}.get(name,name)
        config=dict(self._animation_configs.get(name,self._animation_configs.get(source_name,{})))
        variant=config.get('directions',{}).get(direction)
        if variant:
            config.update(variant)
            config['direction']=direction
            config['mirror_allowed']=False
        try:
            entries=config.get('frames')
            if entries is None:
                anim_dir = self._character.animations_path / name
                if anim_dir.is_dir() and any(anim_dir.iterdir()):
                    folder = anim_dir
                else:
                    folder = self._character.animations_path / source_name
                entries = [str(p.relative_to(self._character.root_path)) for p in
                           sorted([*folder.glob('*.png'), *folder.glob('*.webp')])]
            if not entries:
                return None
            fps=max(1,min(60,float(config.get('fps',12))))
            frames,offsets,anchors,deadlines=[],[],[],[]
            elapsed=0.0
            for i,entry in enumerate(entries):
                data=entry if isinstance(entry,dict) else {'path':entry}
                path=self._asset_path(data['path'])
                if not path.is_file():
                    raise ValueError(f'Missing animation frame: {path.name}')
                frame_offsets=config.get('offsets',[])
                frame_durations=config.get('durations_ms',[])
                offset=data.get('offset',frame_offsets[i] if i<len(frame_offsets) else [0,0])
                anchor=data.get('anchor',config.get('anchor',self._anchor))
                duration=float(data.get('duration_ms',frame_durations[i] if i<len(frame_durations) else 1000/fps))
                if not math.isfinite(duration) or duration<=0:
                    raise ValueError('Frame durations must be finite and positive')
                frames.append(path)
                offsets.append(tuple(float(v) for v in offset[:2]))
                anchors.append(tuple(float(v) for v in anchor[:2]))
                elapsed+=duration
                deadlines.append(elapsed)
            clip=Clip(name,frames,offsets,anchors,deadlines,bool(config.get('loop',True)),
                      bool(config.get('mirror_allowed',True)),config.get('direction','right')=='left',key,
                      bool(config.get('interpolate_offsets',True)))
            self._clips[key]=clip
            return clip
        except (OSError,ValueError,TypeError,KeyError,IndexError) as exc:
            logger.error('Cannot load %s: %s',name,exc)
            return None

    def has_animation(self,name):
        return self._get_clip(name) is not None

    def play(self,animation_name,force_restart=False):
        if animation_name==self._current_animation and self._clip and not force_restart and not self._completed:
            self.resume()
            return True
        clip=self._get_clip(animation_name)
        if clip is None:
            logger.warning('Animation unavailable: %s',animation_name)
            self.animation_unavailable.emit(animation_name)
            return False
        old=self._current_animation if self._clip and not self._completed else None
        self._timer.stop()
        self._generation+=1
        self._queue.clear()
        self._current_animation=animation_name
        self._current_frame_idx=0
        self._clip=clip
        self._position_ms=0.0
        self._completed=False
        self._playing=True
        self._last_ns=self._clock.nsecsElapsed()
        self._emitted_key=None
        self._current_fps=float(self._animation_configs.get(animation_name,{}).get('fps',12))
        if old:
            self.animation_cancelled.emit(old)
        self._advance_frame()
        return True

    def play_sequence(self,names):
        """Play explicit transition clips followed by a destination clip."""
        names=list(names)
        if not names or not all(self.has_animation(name) for name in names):
            return False
        # Only the final clip may loop indefinitely.
        if any(self._get_clip(name).loop for name in names[:-1]):
            return False
        if self.play(names[0],force_restart=True):
            self._queue=names[1:]
            return True
        return False

    def _accrue(self):
        now=self._clock.nsecsElapsed()
        if self._playing and not self._suspended:
            self._position_ms+=(now-self._last_ns)/1_000_000*self._speed_multiplier
        self._last_ns=now

    def pause(self):
        self._accrue()
        self._playing=False
        self._timer.stop()

    def stop(self):
        self.pause()

    def resume(self):
        if self._clip and not self._completed and not self._playing:
            self._last_ns=self._clock.nsecsElapsed()
            self._playing=True
            self._advance_frame()

    def cancel(self):
        previous=self._current_animation if self._clip and not self._completed else None
        self.pause()
        self._generation+=1
        self._queue.clear()
        self._completed=True
        if previous:
            self.animation_cancelled.emit(previous)

    def set_display_fps(self, fps):
        self._display_fps = 30 if int(fps) == 30 else 60

    def set_reduced_fps(self, reduced: bool):
        """Enable or disable reduced frame rate rendering (e.g. while sleeping)."""
        reduced = bool(reduced)
        if self._reduced_fps != reduced:
            self._reduced_fps = reduced
            if self._playing and not self._suspended:
                self._timer.stop()
                self._advance_frame()

    def set_suspended(self, suspended: bool):
        """Suspend or resume animation timer and rendering to conserve resources."""
        suspended = bool(suspended)
        if self._suspended == suspended:
            return
        self._accrue()
        self._suspended = suspended
        if suspended:
            self._timer.stop()
        else:
            if self._playing and self._clip and not self._completed:
                self._last_ns = self._clock.nsecsElapsed()
                self._advance_frame()

    def set_speed_multiplier(self,multiplier):
        multiplier=max(.1,min(5,float(multiplier)))
        if abs(multiplier-self._speed_multiplier) < 0.01:
            return
        self._accrue()
        self._speed_multiplier=multiplier
        if self._playing:
            self._advance_frame()

    def set_scale(self,scale):
        self._scale=max(.2,min(3,float(scale)))
        self._emit_current_frame(force=True)

    def set_opacity(self,opacity):
        self._opacity=max(.1,min(1,float(opacity)))
        self._emit_current_frame(force=True)

    def set_facing_left(self,facing_left):
        if bool(facing_left)==self._is_facing_left:
            return
        self._accrue()
        old_duration=self._clip.duration if self._clip else 1
        self._is_facing_left=bool(facing_left)
        clip=self._get_clip(self._current_animation)
        if clip:
            self._position_ms=self._position_ms/old_duration*clip.duration
            self._clip=clip
            self._emitted_key=None
            if self._playing:
                self._advance_frame()
            else:
                time=(self._position_ms%clip.duration if clip.loop else min(self._position_ms,clip.duration-.001))
                self._current_frame_idx=min(len(clip.frames)-1,bisect_right(clip.deadlines,time))
                self._emit_current_frame()

    @property
    def is_miles(self) -> bool:
        return bool(self._character and 'miles' in getattr(self._character, 'id', '').lower())

    def is_animated_on_twos(self) -> bool:
        """Check if character should animate 'on the twos' (12 FPS) in cinematic Spider-Verse style."""
        try:
            from services.settings_service import get_settings
            if not get_settings().get('animations.authentic_twos', True):
                return False
        except Exception:
            pass
        return self.is_miles

    def _advance_frame(self):
        if not self._playing or self._clip is None or self._suspended:
            return
        self._accrue()
        clip=self._clip
        generation=self._generation
        complete=not clip.loop and self._position_ms>=clip.duration
        time=self._position_ms%clip.duration if clip.loop else min(self._position_ms,clip.duration-.001)
        on_twos = self.is_animated_on_twos()
        if on_twos:
            # Snap to 12 FPS time intervals (83.33ms) for snappy, classic Spider-Verse keyframes
            step_ms = 1000.0 / 12.0
            stepped_time = math.floor(time / step_ms) * step_ms
            self._current_frame_idx=min(len(clip.frames)-1,bisect_right(clip.deadlines,stepped_time))
        else:
            self._current_frame_idx=min(len(clip.frames)-1,bisect_right(clip.deadlines,time))
        self._emit_current_frame()
        if generation!=self._generation or not self._playing or self._suspended:
            return
        if complete:
            self._playing=False
            self._completed=True
            self._timer.stop()
            name=self._current_animation
            self.animation_completed.emit(name)
            if generation==self._generation and self._queue:
                next_name,*remaining=self._queue
                if self.play(next_name,force_restart=True):
                    self._queue=remaining
            return
        # Schedule the next frame boundary, not a fixed tick count. Late callbacks
        # skip to the correct pose instead of slowing down the animation.
        remaining=clip.deadlines[self._current_frame_idx]-time
        delay=max(1,math.ceil(remaining/self._speed_multiplier))
        next_index=(self._current_frame_idx+1)%len(clip.frames) if clip.loop else min(self._current_frame_idx+1,len(clip.frames)-1)
        if clip.interpolate_offsets and clip.offsets[self._current_frame_idx]!=clip.offsets[next_index]:
            delay=min(delay,16)
        if on_twos:
            min_fps_delay = 83  # 12 FPS for Miles on the twos
        elif self._reduced_fps or clip.name == 'sleep':
            min_fps_delay = 125
        else:
            min_fps_delay = math.ceil(1000/self._display_fps)
        self._timer.start(max(delay, min_fps_delay))

    def _sample_offset(self,clip,index):
        offset=clip.offsets[index]
        if not clip.interpolate_offsets or self.is_animated_on_twos():
            # Snappy keyframes: no floating-point sub-pixel interpolation on twos
            return offset
        next_index=(index+1)%len(clip.frames) if clip.loop else min(index+1,len(clip.frames)-1)
        time=self._position_ms%clip.duration if clip.loop else min(self._position_ms,clip.duration)
        start=clip.deadlines[index-1] if index else 0
        progress=max(0,min(1,(time-start)/(clip.deadlines[index]-start)))
        return tuple(round((a+(b-a)*progress)*4)/4 for a,b in zip(offset,clip.offsets[next_index]))

    def _emit_current_frame(self,force=False):
        clip=self._clip
        if clip is None:
            return
        index=self._current_frame_idx
        offset=self._sample_offset(clip,index)
        key=(clip.cache_key,index,self._is_facing_left,self._scale,self._opacity,offset)
        if not force and self._emitted_key==key:
            return
        if key in self._frame_cache:
            frame=self._frame_cache[key]
            self._frame_cache.move_to_end(key)
        else:
            source=QPixmap(str(clip.frames[index]))
            if source.isNull():
                self.cancel()
                self.animation_unavailable.emit(clip.name)
                return
            frame=QPixmap(*self._canvas)
            frame.fill(Qt.transparent)
            painter=QPainter(frame)
            painter.setOpacity(self._opacity)
            x=self._anchor[0]-clip.anchors[index][0]+offset[0]
            y=self._anchor[1]-clip.anchors[index][1]+offset[1]
            painter.drawPixmap(QPointF(x,y),source)
            painter.end()
            if clip.mirror and self._is_facing_left!=clip.source_left:
                frame=frame.transformed(QTransform().scale(-1,1),Qt.SmoothTransformation)
            if self._scale!=1:
                frame=frame.scaled(max(1,round(frame.width()*self._scale)),max(1,round(frame.height()*self._scale)),Qt.KeepAspectRatio,Qt.SmoothTransformation)
            size=frame.width()*frame.height()*4
            while self._frame_cache and self._cache_bytes+size>self._cache_limit:
                _,removed=self._frame_cache.popitem(last=False)
                self._cache_bytes-=removed.width()*removed.height()*4
            if size<=self._cache_limit:
                self._frame_cache[key]=frame
                self._cache_bytes+=size
        self._emitted_key=key
        self.frame_updated.emit(frame)
