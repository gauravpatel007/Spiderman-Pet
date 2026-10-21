# Overlay and GUI lag review

Policy: planning=deep; context_depth=dependency; verification_depth=impact;
delegation=none. Scope: overlay lifecycle, positioning, hit testing, Focus/load
interaction and regression tests. Preserve UI, sprite files and animation data.

Evidence before edits: inspected both supplied recordings and traced animation,
movement, effects, foreground tracking and application signal connections.
A six-second isolated runtime profile recorded 0.617 seconds in 29 alpha-region
builds; effects painting also contributes GUI work. The profile is diagnostic,
not a production FPS measurement. Initial timer sample included startup and
must be excluded from latency comparisons.

Decisions:
- Replace Python per-pixel alpha scanning with equivalent byte-run scanning;
  verify identical threshold/hole behavior, then benchmark without profiling.
- Clamp fractional coordinates conservatively to prevent floor penetration.
- Read current physics coordinates for effects and bind effects visibility to
  the companion's actual show/hide lifecycle, including pause and app switches.
- Quiet Focus must suppress the heavy-load scene and its position/paint effects;
  restore current load behavior on leaving Focus. Keep hardware metrics live.

Additional confirmed issue: `_track_cursor` bypassed the Focus guard used by
normal activity requests. A live test recorded `focus_read -> jump` and a
24-pixel vertical displacement. Cursor-follow/dodge processing now returns
early during Focus/reading, while direct pet dragging remains available.

The current preview path was also encoding PNGs off Home; restored the early
visibility/tab guard while retaining its 10 Hz cap and duplicate-frame check.

Production files changed in this follow-up:
- `overlay/hit_test_manager.py`: byte-run alpha region builder, escaped threshold.
- `core/movement_controller.py`: conservative fractional footprint containment.
- `overlay/comic_effects_overlay.py`: pet-owned window; show/hide and timer
  lifecycle; current physics coordinates; monitor-aware top clamping.
- `app/application.py`: gate heavy-load scene during Focus, reapply on toggle.
- `core/behavior_controller.py`: Focus takes priority over load transitions.
- `core/interaction_manager.py`: prevent automatic cursor dodges during Focus.
- `ui/web_window.py`: skip PNG encoding when preview is not visible.

Tests: new `tests/test_overlay_stability.py`, expanded
`tests/test_app_startup.py`, adjusted `tests/test_system_load_and_audio_sync.py`
to render effects with a visible parent pet.

Observed verification:
- Native Windows Chromium/dashboard/overlay/startup tests: 47 passed (34.22s).
- Separate physics, animation, interaction and services group: 99 passed
  (25.84s), one warning. Total: 146 distinct passing tests.
- Identical-region benchmark on a 200px Tom Holland sprite: old 5.924ms,
  new 0.782ms, 7.57x faster. Pixel/holes/threshold tests also cover nine thresholds.
- Six-second instrumented Focus/charging/high-load probe: one unique physics
  position across 368 timer samples; p95 timer interval 16.86ms. Maximum interval
  125.77ms under profiling and concurrent build load: not proof of zero stutter.
- Pet and charging badge renders inspected; no sprite or UI assets changed.
  The probe's dashboard QWidget grab was blank, so it is not visual evidence
  of the dashboard. Native hit-testing/navigation tests provide that coverage.
- PyInstaller build completed at `dist/overlay-fixed/SpiderBuddy/SpiderBuddy.exe`.
  Opened its embedded Python archive and confirmed all seven changed production
  modules are included.

Limitations: not verified across fullscreen games, virtual-desktop switching,
or mixed-DPI multi-monitor transitions. No claim of eliminating all possible
GUI stalls. Source application startup is exercised; packaged primary startup
has not been independently exercised while the user's instance is running.

VERDICT: PASS
