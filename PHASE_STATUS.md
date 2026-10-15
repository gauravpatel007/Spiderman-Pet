# Phase acceptance status

Updated 2026-10-14. Implementation follows phase.md in order. Per the latest user instruction,
formal testing is deferred until the build is finished. Existing later-phase
prototype code is not accepted merely because its modules exist.

| Phase | Status | Evidence / remaining work |
| --- | --- | --- |
| 0 — Scope and stack | Confirmed | Native Windows, local/free, PySide6, PNG assets, JSON settings. Actual tested Python is 3.13; plan's 3.12 remains untested. |
| 1 — Foundations | Implemented and regression-tested | Bootstrap, instance ownership/IPC, persistent settings, character loading, initialized services/overlay/dashboard/tray, logging and shutdown. |
| 2 — Character animation assets | Animation build implemented; final validation deferred | Eight locally rigged clips per character, editable cutout rigs, manifests and runtime playback. |
| 3 — Transparent overlay | Implemented; final validation deferred | Alpha-shaped input, native hit testing, gesture separation, rotation and DPI-aware cached rendering. |
| 4 — Display modes | Implemented; final validation deferred | Persistent executable selections, foreground ownership, window following, monitor selection, visible-region containment and DPI conversion. |
| 5 — Animation engine | Implemented; final validation deferred | Elapsed-time scheduling, manifest-driven clips, aligned/interpolated offsets, directional assets, pause/cancel/sequence playback and posture transitions. |
| 6 — Movement and physics | Pending acceptance | Movement/animation synchronization and real climbing/swinging. |
| 7 — Interaction | Implemented; final validation deferred | Click/celebration reactions, cursor attention, bounded dragging, inactivity stages, working context controls and optional local sound. |
| 8 — Dashboard/settings | Implemented; final validation deferred | Sidebar dashboard, themes, live appearance and behavior controls, application selection, activity playback and pause/hide. |
| 9 — Windows integration | Pending acceptance | Session handling, background pause, startup and measured usage. |
| 10 — Advanced behavior | Pending acceptance | Character-specific actions with cooldowns and authored assets. |
| 11 — Validation | Pending | Native interactive, DPI/monitor and performance matrix. |
| 12 — Packaging | Pending | Standalone executable and packaged-asset smoke test. |

## Phase 1 work in this pass

- Removed eager Qt imports from package bootstrap; dependency setup precedes Qt.
- Removed the hardcoded Python 3.13 dependency path; uses the running interpreter.
- Added rotating logs and idempotent logging setup, including windowless launches.
- Added QLockFile ownership with process-aware stale-lock handling. Lock/server
  failures never permit an unguarded second companion.
- IPC handles queued data and fragmented newline-framed commands.
- Startup failures clean up partially initialized components and release ownership.
- Settings saves use a flushed temporary file plus atomic replacement.
- Invalid setting types fall back to defaults; mutable values are returned as copies.
- Character choices from all entry points persist, including the tray.
- Tray menu ownership and display-mode checkmarks remain synchronized.
- Tests use isolated settings and instance keys so they do not stop a live companion.

Validation: final full regression run passed all 24 tests (12.08 seconds).
Includes separate-process duplicate launch/wake-up, fragmented IPC, interrupted
save, corrupt settings, both character startup frames, repeated shutdown and
SIGINT/SIGTERM/SIGBREAK handling. Offscreen tests do not certify real desktop
click-through, monitor scaling, or Windows lock/resume (later phases).

## Phase 2 animation build

Built locally from the existing full-body artwork using authored polygon cutouts
and joint pivots. No API, model download, or paid service. Each character has:

- Idle: 24 frames, 12 FPS; independent head motion, torso breathing and arm movement.
- Walk: 24 frames, 24 FPS; alternating leg rotation and arm counter-motion.
- Run: 16 frames, 24 FPS; stronger stride and body lift.
- Sleep: 24 frames, 8 FPS; reclined pose, covered lenses and breathing.
- Wake-up: 18 frames, 12 FPS; rising from recline and reopening lenses.
- Sit: 24 frames, 12 FPS; bent-leg pose and head movement.
- Stand-up: 12 frames, 12 FPS; returns from the seated pose.
- Wave: 24 frames, 16 FPS; independent hand/arm motion.

Total: 166 frames per character, 332 newly rendered frames. Other existing poses
remain intact, including Miles's peeking and web poses. Character IDs and source
JPEGs are preserved. The new work is a 2D cutout rig, not newly modeled 3D artwork.
The original costume is retained; hoodie/headphone/sneaker redesign and the full
20-action library in the plan are still future artwork work.

Files: `scripts/build_articulated_assets.py`, each character's `rig/` folder and
`animation_manifest.json`. Runtime reads manifest FPS/loop settings and loads the
new sequences. New state names and a Character activities context submenu expose
all eight clips. One-shot animations now emit completion once.

Previews: `build/miles_morales-phase2.gif` and `build/tom_holland-phase2.gif`.
No automated tests or asset audit were run for this build, as requested. The old
phase2_asset_audit.json describes the previous still-pose library and is obsolete.
Formal tests and full visual acceptance are deferred to the final validation pass.

## Phase 3 overlay build

- One small frameless, translucent tool window; no taskbar entry and no keyboard focus.
- The native window mask follows the current rendered alpha silhouette, including
  interior holes. Transparent padding is excluded from cross-process hit testing.
- WM_NCHITTEST maps native physical client coordinates into logical sprite pixels;
  WM_MOUSEACTIVATE avoids taking focus away from the user's active application.
- Normal mode retains character interaction. Optional full click-through uses
  Qt.WindowTransparentForInput only when explicitly enabled in settings.
- Clicks and drags are distinct. Dragging begins at the system drag-distance
  threshold; single clicks wait for the double-click interval. Double-click opens
  the dashboard without also emitting a single-click reaction.
- Mouse capture continues a drag outside the silhouette. Hiding/capture loss cancels
  gestures and releases the movement controller's drag suspension.
- Source frames are resized at physical pixel resolution, tagged with the current
  device-pixel ratio, and rendered from a bounded 24-entry cache. Monitor/DPR changes
  invalidate that cache. Fractional scaling uses Qt's PassThrough rounding policy.
- Rotation expands the rendered bounds without stretching the character; movement
  dimensions track the actual rendered window. Opacity and full click-through
  settings apply immediately. Rotation is exposed through set_rotation and the
  general.rotation setting; a dashboard control belongs to the later UI phase.
- Stop hides the overlay and stops animation. Settings changes cannot reshow a
  paused overlay. Application mode no longer unconditionally shows an unselected pet
  at the end of start().

No tests, application launch, or DPI/native input validation performed in this
phase, as requested. Final validation must cover transparent holes over a different
process, body dragging across the mask, click/double-click/right-click, hide during
capture, negative monitor coordinates, 100/125/150/175/200% scaling and live
mixed-DPI monitor transitions. Actual application-window coordinate normalization
and multi-monitor containment remain Phase 4 work.

## Phase 4 display-mode build

- Application selections now save detected executable paths and process names.
  Window/document titles are presentation only and cannot select unrelated apps.
  Legacy strings match exact executable/product names; selecting a running entry
  migrates the choice to an executable record.
- The selector displays executable icons, names and running status, preserves
  checked selections during refresh, and retains choices for closed applications.
  Windows App Paths registrations provide installed applications; Browse adds other
  executables without requiring them to be running. No guessed executable aliases.
- One 100ms foreground tracker replaces duplicate window polling. It detects owner,
  geometry, minimized/visible state and process identity changes. Desktop mode stops
  this tracker. Cloaked windows on other virtual desktops are excluded.
- Application mode follows the selected foreground window, remembers local offsets
  per HWND/PID, relocates on move/resize/maximize, and hides on minimize/close or
  unselected foreground focus. Oversized companions hide until the window fits.
- Native window rectangles use DWM frame bounds when available and are split by
  native monitor geometry before conversion to each screen's logical Qt coordinates.
  Work-area intersections exclude offscreen areas and taskbars.
- Desktop mode offers primary, a specific named monitor, or all monitors. Geometry,
  work-area, DPI and screen add/remove changes refresh constraints.
- Movement is limited to a union of actual visible regions rather than one large
  bounding rectangle. Monitor-edge transfers allow traversal of separate Qt screen
  coordinate islands while placing the pet back on visible work areas.
- The dashboard displays the current overlay owner/hide reason and exposes monitor
  selection. Tray display-mode changes synchronize the radio buttons immediately.

No tests or application launch were performed. Runtime verification of window
changes, process identity access restrictions, mixed-DPI geometry and monitor-edge
transfers remains in the final validation pass. Installed-app discovery is limited
  to App Paths registrations plus explicit Browse; it is not a full inventory of
all Windows packages.

## Phase 5 animation-engine build

- Replaced one-frame-per-timeout advancement with a monotonic nanosecond clock and
  elapsed clip time. Late callbacks select the correct pose rather than slowing the
  whole clip. Precise single-shot timers target the next frame deadline.
- Manifest frame lists define playback order. Clips support FPS, per-frame duration,
  loop behavior, anchors, offsets, and explicit left/right variants. Legacy folders
  still load PNG/WebP sequences when a clip has no manifest entry.
- Frames align onto a common character canvas. Offset interpolation runs only when
  neighboring offsets differ, capped at roughly 60 updates/second. Ordinary clips
  wake only at their authored frame rate; no blanket crossfade/ghost images.
- Supports play, forced restart, pause, resume, cancellation and explicit clip
  sequences. Speed changes preserve elapsed animation phase. One-shots hold their
  final frame and emit completion once; cancelled clips do not emit completion.
- Direction variants preserve gait phase. Mirroring is used only when permitted;
  asymmetric artwork can supply directions.left/right frames instead.
- Lazy frame decoding and a 48 MiB LRU render cache replace eager loading of every
  animation. Character switches clear the old cache. Missing/broken clips are
  reported, not replaced with a fabricated placeholder character.
- Resting state transitions route sleep through wake-up and sit through stand-up,
  then continue the requested action. Repeated requests during a transition update
  its destination; dragging can interrupt. Jump completion routes to falling.
- Pause/resume of the companion retains the current clip. Saved animation speed
  changes affect playback immediately. The dance state is defined for future assets;
  it is not exposed as an available activity without a supplied clip.

No tests or runtime launch performed, as requested. Final validation must include
late timer delivery, pause/speed changes mid-clip, terminal frame holds, cancellation
callbacks, directional variants, malformed/missing assets and chained transitions.
The original asset-audit report and earlier test counts describe previous builds.


## Phase 6 movement and physics build

- Replaced frame-dependent position increments with monotonic elapsed time,
  bounded physics substeps, persistent subpixel coordinates, acceleration,
  deceleration and gravity. Character profiles supply walking/running/climbing
  speeds, jump impulse and gravity; the movement-speed setting scales locomotion.
- Jump apex and floor collisions drive fall/landing transitions. Jump clip
  completion no longer cuts the trajectory short. Gait playback follows actual
  horizontal speed and pauses when motion stops.
- Boundary choices use available clips and weighted selection: stop, turn, jump
  away or climb. Both wall sides support climbing and body orientation; the upper
  boundary leads to hanging, perching or climbing back down.
- Swing uses an anchored damped pendulum, body rotation, tangential release and
  subsequent gravity/landing. A separate noninteractive web window draws a strand
  clipped to allowed regions. Pose rotation stays inside a fixed sprite canvas,
  preventing rotation from repeatedly changing physics dimensions.
- Existing visible-region containment and desktop monitor transfers remain in use.
  Region/size/position changes release an existing swing; stopping or hiding the
  companion hides the web. Dragging cancels the strand and physics motion.
- Weighted choices include walking, running, rest, sitting, sleeping and occasional
  jumping/swinging. Configurable behavior.durations.<state>.min/max values are in
  seconds; behavior.special_cooldown_seconds limits frequent jump/swing choices.
  Movement speed and climbing/swinging toggles update active behavior.

No tests or application launch performed, per request. The final pass must verify
collision/corner transitions, wall orientation, swing release, strand positioning,
small windows, moving/resizing owners, mixed-DPI monitor transfers and timer stalls.
This phase adds procedural motion to the existing artwork: climb/swing states still
use their existing pose assets, not newly authored multi-frame limb animations.


## Phase 7 mouse interactions and responsiveness build

- Single click requests a wave; double click requests a two-second celebration.
  Dashboard access is now through Settings in the character menu or the tray.
  Existing double-click suppression prevents a duplicate delayed single click.
- Added local rig-based dance (48 frames), celebration (32 frames), and dragging
  (24 frames) clips for each character. Manifest entries make dance/celebration
  one-shots and dragging a loop. No paid services or downloads were used.
- A 100 ms cursor poll observes position only while the companion runs. Nearby
  cursor attention stops walking and turns the character toward the pointer;
  occasional fast-pointer waves have a cooldown. Leaving the vicinity/region
  restores autonomy. Hidden overlays skip observation and idle users do not keep
  the character permanently attentive. This uses whole-character facing, not
  independent eye tracking.
- Dragging suspends physics, uses the new pose and existing region projection,
  and releases into landing or falling. Existing hide/capture-loss cleanup remains.
- GetLastInputInfo drives configurable 120/300/600-second thresholds for relaxed,
  seated and sleeping behavior. Returning input wakes sleepers and stands seated
  characters. Explicit actions have a short grace period. Corrected unsigned
  32-bit uptime wraparound in idle-duration calculation.
- Context actions include wake/sit/sleep/walk/run/jump/swing/dance, character and
  display-mode selection, sizes, settings and exit. Unavailable clips or swing
  without room are disabled. Size changes synchronize the overlay and dashboard.
- Added original locally synthesized jump/web/landing/sleep/reaction WAV cues,
  optional Qt sound playback, a mute toggle and volume slider in the context menu.
  New installs default to muted; existing saved preferences are preserved.
- Cursor observation and audio stop with pause/shutdown. Audio reactions are
  suppressed while the overlay is hidden. Asset generation is reproducible with
  scripts/build_interaction_assets.py; the full rig builder also includes new clips.

No tests or application launch performed, per request. Deferred validation covers
click/double-click timing, capture loss, constrained dragging, input returning during
sleep/wake transitions, menu actions, cursor polling and audio-backend availability.

## Phase 8 dashboard and settings build

- Replaced the single tall panel with eight sidebar pages: Dashboard, Characters,
  Display Mode, Applications, Animations, Behavior, Appearance and Settings.
  Pages scroll within resizable layouts, with short page transitions and shared
  dark/light styling. Character cards and the application selector inherit theme.
- Dashboard displays the live sprite, selected character, activity, owner/hide
  reason and application count. Pause/resume and persistent hide/show are separate
  controls. Closing the panel keeps the existing tray workflow.
- Character selection updates in place. Activity playback exposes enabled profile
  clips and routes through the existing state/interaction controllers. A paused
  companion resumes when an activity is explicitly requested.
- Appearance controls include 100–400 px size, 50–100% opacity, slow/normal/fast
  animation speed, automatic/30/60 FPS, bottom-left/right/custom placement,
  sound enable and volume. Custom positions save normalized coordinates relative
  to the current/last allowed region. Frame caps affect both movement callbacks
  and animation scheduling; Automatic uses authored timing with a 60 Hz ceiling.
- Behavior controls gate walking, running, jumping, sleep, sitting, climbing,
  swinging, hanging, cursor attention and random activities. Disabling an active
  behavior transitions safely to idle/fall. Calm/Normal/Playful presets adjust
  weighted choices and action durations. Inactivity thresholds are editable in
  minutes and respected in stage order.
- Settings bindings synchronize context-menu changes, theme, application choices,
  monitors, size and sound without creating duplicate handlers. Available monitor
  choices refresh when screens are added or removed. Character switches reapply
  physics while preserving pause state.
- Application-mode hiding on minimize/close/foreground loss remains mandatory and
  is explained as a policy, rather than exposing a switch that defeats containment.
  Artwork/costumes remain the existing local rigs; this UI phase adds no new costume.

No tests, GUI launch or visual runtime verification performed, per request.
The deferred pass must cover both themes, resize/DPI layouts, cross-surface setting
synchronization, preset/toggle combinations, playback, pause/hide and positioning.
