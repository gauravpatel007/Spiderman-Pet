# Settings and desktop runtime review

Policy: planning=compact; context_depth=dependency; verification_depth=impact;
delegation=none. Scope: existing web dashboard, backend wiring, pet grounding,
and regression tests. Preserve existing work and artwork.

Decisions based on inspected code:
- Remove the exported HTML's document event scheduler: it defers click and
  mousedown handlers, including navigation, outside the input event.
- Bind Settings controls once and export the refresh method used by Python.
- Limit dashboard preview encoding and avoid work while hidden.
- Keep gravity for unsupported poses and focus fallback; preserve intentional
  manual pinning and supported hanging poses.
- Connect test audio to its service and verify existing statistics reset wiring.
- Fix the duplicate `btnTestEye` declaration that prevented the whole bridge
  from parsing; apply selected themes rather than only highlighting buttons.
- Suppress global pet keyboard polling while the dashboard has focus so typing
  in search does not move and statically pin the companion.
- Notify runtime settings subscribers when factory defaults are restored.

Validation: targeted physics/settings tests and an embedded Chromium UI check,
followed by affected regression tests. Record unavailable checks explicitly.

## Observed verification

- JavaScript syntax: `node --check` passed.
- Desktop runtime regressions + web endpoints + four-character app startup:
  27 passed (Windows Qt, Chromium with `--no-sandbox` for the test process).
- Core, title dragging, WASD, advanced behavior, repertoire, trampoline and
  settings foundations: 48 passed.
- WASD, title dragging, load/audio and system integration: 26 passed.
  These groups overlap; counts are not a unique total.
- Inspected `build/runtime-review/settings-dark.png` and `settings-light.png`.
- Initial restricted localhost tests were denied by the sandbox; authorized
  localhost integration runs passed. Software-rendered captures were stale;
  hardware-rendered Windows captures were used for visual verification.
- Test teardown now deletes Qt windows on the UI thread to avoid worker-thread
  garbage collection during consecutive HTTP integration tests.

At the initial review, changes were source-only; packaging is covered below.
Audio invocation and volume were tested; physical speaker output was not.

VERDICT: PASS

## Follow-up: recorded lag, invisible search, and clipped pages

Policy: planning=replan; context_depth=dependency; verification_depth=impact;
delegation=none. Inspected frames from the supplied 21.6-second recording.

Observed causes and repairs:
- Paint containment on the search capsule clipped its dropdown. Override the
  ID-level rule; verify actual hit testing and native mouse/keyboard activation.
- The dashboard lacked a constrained scrolling flex child. Give content and
  sidebar explicit overflow, stable visible scrollbar space, and nonshrinking
  pages. Verify all seven tabs at 1100x700 and 1380x840, including wheel input.
- Cache settings filter text and hide empty sections; display a no-match state.
  Enter activates the first global search result when none is highlighted.
- Movement statistics emitted at physics-step frequency. Accumulate distance
  without notification and publish through the existing one-second timer.
- Skip preview PNG work away from Home; cap encoded image dimensions to 350x330.
- Ignore stale settings responses after newer user actions, preventing theme
  selections from being reverted by an earlier request.
- Normalize nullable application metadata so one window cannot empty the whole
  running-application list. Remove unused Framer module preloads and navigation
  animations. Avoid interpolating search input into activity empty-state HTML.
- The separate QML sidebar's battery row imposed an excessive minimum width,
  pushing Focus outside the viewport. Allow that row to shrink and elide text;
  size the custom switch explicitly. Native click regression passes.

Verification after changes:
- Current Windows Chromium dashboard, endpoints, pet/runtime regressions and
  four-character application lifecycle: 34 passed in 28.31s.
- Separate core/service regression group: 99 passed in 13.09s (one warning).
- Separate QML/native UI, activities, import and wheel group: 33 passed in
  33.71s (one warning). These three disjoint groups total 166 passing tests.
- Visual inspection: search-visible.png and settings-bottom-1100.png in
  build/runtime-review; dropdown and bottom settings controls are visible.
- JavaScript syntax check passed. PyInstaller completed successfully and bundled
  HTML, bridge JavaScript and runtime CSS hashes matched the source files.

The initial mixed Qt test run stalled; Chromium and legacy QML are tested in
separate processes. This is not a measured end-to-end FPS benchmark or a claim
that every possible app bug is eliminated. The packaged executable has not been
independently launched as primary while the user's existing instance is running.
Source application startup and shutdown are covered by the lifecycle tests.

VERDICT: PASS
