# BUG report 21Oct

**Scan date:** 21 October 2026  
**Project:** Spider-Buddy (Windows desktop application)  
**Scope:** Source review of the application and UI/API entry points, with generated build artifacts excluded. Reviewed 164 Python, JavaScript, QML, and JSON source/config files; checked the existing 30 test modules. This report records actionable findings and verification limits. It does not claim every possible runtime/environment issue has been reproduced.

## Findings

| Priority | Finding | Evidence and impact | Verification |
|---|---|---|---|
| High — security review | Character preview fallback joins a request-provided character ID into a filesystem path without validating or constraining the resolved path. | `ui/web_server.py`, `_handle_character_image`: `char_id` comes from the URL path or query and is used in `root / "characters" / char_id / "preview.png"`; the fallback reads that target if it exists. A traversal-style ID could escape the characters folder and return bytes from another `preview.png` file. This is a static path-containment defect; no successful runtime disclosure was demonstrated. | Static source finding. Dynamic local-server probe was not completed (see limitations). Fix by validating IDs against known character IDs and checking the resolved target remains under the characters directory. |
| Medium — security review | Local HTTP API uses wildcard CORS and exposes action routes without an origin/token check visible in the handler. | `ui/web_server.py` sets `Access-Control-Allow-Origin: *` on API responses (including action handling). The server is local, so actual cross-origin reachability depends on browser/private-network protections and deployment details; do not treat exploitability as established. | Static source finding; runtime/browser-origin behavior not verified. Restrict CORS to the app origin and add request-origin/host protections appropriate to the local API. |
| Medium — functional | Audio meter and music-state callbacks are no-ops in the main UI window. | `ui/web_window.py`, `update_audio_meter` and `update_music_state` contain only `pass`. The application connects audio and music state updates to these methods, so this window cannot reflect those updates through these callbacks. | Confirmed from source; no live audio device test performed. |
| Medium — functional | “Always on top” setting is saved and UI state refreshed, but this action does not apply a window-stacking change. | `ui/web_window.py`, `toggle_always_on_top` only writes `system.always_on_top` and reloads settings into JavaScript. No `setWindowFlags`/equivalent is invoked in this handler. Overlay types also have their own topmost behavior, so the user-visible result depends on which window the setting is intended to control. | Static finding; setting behavior across main and overlay windows needs runtime confirmation. |
| Low — UI correctness | Focus/break status is inferred from the remaining whole minutes, causing status to switch at the five-minute boundary. | `ui/web_window.py`, `update_eye_break_status`: `Focusing` when `int(remaining_sec // 60) >= 5`, otherwise `Break`. A countdown at 4:59 is labeled “Break”; the service signal shown here contains no explicit session type. | Confirmed code behavior; whether that label is incorrect for every timer mode needs product intent confirmation. |

## Test evidence

The saved test runs for this scan completed successfully:

- Native/UI-adjacent test group: **47 passed** (`build/audit-20Oct/native-tests.txt`).
- Core test group: **99 passed, 1 warning** (`build/audit-20Oct/core-tests.txt`).
- **146 tests passed** across the two groups. These are the recorded test runs available for this report; they do not constitute a manual end-to-end pass through every screen or Windows configuration.
- No production TODO/FIXME/NotImplemented markers were found in the searched source tree. Absence of markers does not establish absence of defects.

## Areas not fully verified

- Interactive search, scrolling, navigation, settings persistence, and Focus & Breaks behavior were not manually exercised screen by screen during this report pass.
- Overlay positioning/stacking across mixed DPI monitors, virtual desktops, fullscreen applications, sleep/resume, and repeated main-window show/hide needs a Windows runtime matrix.
- The previous overlay lag review documented improvement and a short instrumented run, but also observed a 125.77 ms maximum timer interval under concurrent build load. That result is evidence of a transient stall under load, not a normal-use latency guarantee; see `docs/overlay-lag-review.md`.
- Packaging and clean-install behavior were not tested here.

## Review notes

This is a new 21 October report. Earlier overlay fixes should be tracked through `docs/overlay-lag-review.md`; they are not re-listed as open defects unless this scan found new evidence. No application code was changed for this report.

**Runtime security probe limitation:** An isolated local-server verification attempt was blocked by the automatic approval service's usage limit, which reported that the action was not executed. The path/CORS items above are therefore explicitly marked as static findings or items needing runtime verification.
