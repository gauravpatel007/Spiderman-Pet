# Spider-Buddy

Local native Windows desktop companion built with Python, PySide6, pywin32,
psutil, and Pillow. No API key or backend service is needed.

## Run

From the project folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python main.py
```

The implementation has been tested with Python 3.13 and PySide6 6.12 on this
Windows machine. The plan proposes Python 3.12; that interpreter has not been
tested here. Closing the dashboard hides it. Use the tray's Exit command or
Ctrl+C in the launching terminal to terminate the companion.

The selected character and preferences live in `%APPDATA%/SpiderBuddy/settings.json`.
Logs rotate in `%APPDATA%/SpiderBuddy/logs/`. Failed JSON replacement preserves
the previous settings file. A second launch opens the existing dashboard.

## Verify

```powershell
python -m pytest tests -q
python scripts/audit_character_assets.py
```

Tests use an offscreen Qt platform and project-local test preferences. The asset
audit writes `build/phase2_asset_audit.json`. A passing technical audit alone does
not establish natural movement or visual quality. Per the latest build direction,
tests and the audit are deferred until implementation is finished.

## Current scope

See [PHASE_STATUS.md](PHASE_STATUS.md) for acceptance results against
[phase.md](phase.md). The existing prototype includes some later-phase code,
but that does not mean those phases have been verified or completed.

Both characters now have locally rigged idle, walk, run, sleep, wake-up, sit,
stand-up and wave sequences. Miles retains his three source poses. Right-click the
companion and open **Character activities** to select the new clips.

Rebuild articulated animations with:

```powershell
python scripts/build_articulated_assets.py
```

To recreate the underlying source cutouts first, run
`python scripts/rebuild_character_art.py`, then the articulated builder above.
The second step replaces the older bobbing-only cycles. Original JPEGs are preserved.
Editable cutout layers and joint definitions live in each character's `rig/` folder.

## Overlay controls

The character's transparent padding and gaps are excluded from its input area.
Click the visible character to interact, drag it to reposition, double-click to
open the dashboard, or right-click for its activity menu. The overlay does not
accept keyboard focus.

Source artwork is rendered at the current monitor's pixel density. The renderer
also supports rotation via `TransparentOverlay.set_rotation(degrees)`; saved
`general.rotation`, `general.opacity`, and `system.click_through` settings apply
through the overlay manager. Full click-through disables character interactions;
use the tray to exit or open the dashboard in that mode. Normal mode uses the
sprite silhouette and keeps the character interactive.

Phase 3 is implemented but has not been runtime-tested; validation is deferred
until the build is finished, per the requested workflow.

## Application and desktop modes

In **Selected Applications**, open Select Applications and check a running or
registered installed executable. Browse can add an executable that is not listed.
Choices persist after the app closes; changing a document title does not change
ownership. Old name-based selections can be replaced by selecting the running app.
The companion hides when an unselected application is foreground, when its owner
is minimized/closed, or when the visible window is too small for the companion.

In **Entire Desktop**, choose Primary, a named display, or All monitors. Movement
uses visible work areas and excludes gaps/taskbars. The owner line below these
controls explains which app is hosting the companion or why it is hidden.
Phase 4 implementation is awaiting the deferred final runtime validation.

## Animation playback

Clips use monotonic elapsed time and their manifest timing, independent of monitor
refresh rate. Pause/resume preserves the current pose and elapsed phase. Sleeping
and seated characters play wake-up/stand-up before the requested next activity.

`animation_manifest.json` supports an ordered `frames` list, `fps`, `loop`,
`anchor`, `offsets`, optional `durations_ms`, and `mirror_allowed`. A frame may also
be an object with `path`, `offset`, `anchor`, and `duration_ms`. Optional
`directions.left` / `directions.right` objects override frame lists and metadata
for asymmetric artwork. Frames align to the manifest's common canvas/anchor.
Changing offsets interpolate by default; set `interpolate_offsets: false` for
intentional discrete offsets. Runtime honors these fields; final testing is deferred.


## Autonomous movement

Phase 6 adds acceleration, gravity, jumping, wall climbing and pendulum swinging
with a visible web strand. Movement stays within the selected visible regions.
Character physics profiles tune speeds and jump strength; the movement-speed
setting scales locomotion. Walking playback follows speed and pauses at a stop.

Default action durations are configurable in JSON under
`behavior.durations.<state>.min` and `.max` (seconds). The defaults favor walking
and rest, with longer sitting/sleeping intervals. `behavior.special_cooldown_seconds`
defaults to 20 to space out autonomous jumps and swings. Climbing and swinging
respect their existing settings toggles. Final runtime testing remains deferred.


## Mouse interactions and inactivity

Click the companion to wave; double-click to celebrate. Drag to pick it up and
release to land or fall within the current movement area. Nearby cursor movement
gets its attention; leaving lets autonomous behavior resume.

Right-click for activities, character/display selection, size, Settings and Exit.
The Sound submenu enables/mutes original local cues and adjusts volume. New
installs start muted. Dance and celebration use locally articulated character rigs.

Inactivity defaults to relaxed behavior after 2 minutes, sitting after 5, and
sleeping after 10. Returning input wakes the character. Customize seconds in
`behavior.inactivity.relax_seconds`, `sit_seconds` and `sleep_seconds` in settings.
Phase 7 is implemented; interactive testing remains deferred.


## Dashboard and preferences

Phase 8 provides sidebar pages for Dashboard, Characters, Display Mode,
Applications, Animations, Behavior, Appearance and Settings. Preview current
activity, pause/resume or hide/show the companion, switch characters, and choose
applications without restarting. Closing the dashboard keeps the tray available.

Appearance includes size, opacity, animation speed, a frame-rate ceiling,
position, sound and volume. Capture the current position to save a custom default.
Behavior offers individual activity switches, Calm/Normal/Playful presets and
inactivity thresholds. Settings includes dark/light themes and click-through.
Changes save immediately and synchronize with context-menu controls.
Runtime and visual testing remain deferred until the final validation phase.
