This plan completes the Spider-Buddy desktop companion redesign. It is written so a developer joining the project can understand the application, preserve existing functionality, and implement the remaining work without relying on earlier conversations.

**Project context and current state**

Spider-Buddy is a Windows desktop companion application. Animated characters move around the desktop, interact with application windows, respond to music and system conditions, and participate in focus and break activities.

The project is located at:

`G:\Languages\Projects\Pet`

The application uses a **Python backend with PySide6**. Its dashboard is being migrated from Qt Widgets to **QML**, while retaining the existing character, animation, settings, and operating-system integration services.

This is a dashboard migration and integration task. It does not require changing programming languages, replacing the animation engine, or regenerating character artwork.

Steps 1–4 are already complete:

| Completed step | Result |
|---|---|
| 1. Feature inventory | Existing features and settings were documented and assigned to destinations. |
| 2. Dashboard organization | Features were reorganized into seven tabs, with settings search. |
| 3. QML foundation | A QML sidebar, shared theme components, and a Python-to-QML bridge were introduced. |
| 4. Home and Characters | These pages now use QML, including live preview, character selection, appearance controls, and the existing import dialog. |

The dashboard has seven destinations:

1. Home
2. Characters
3. Activities
4. Desktop & Apps
5. Focus & Breaks
6. Controls
7. Settings

The current implementation is transitional. Some pages remain native Qt Widgets. Hidden native controls still supply some state and search information to migrated pages. Steps 5–7 must finish the migration and remove those dependencies.

The developer must read these documents before implementation:

- [Feature map](G:/Languages/Projects/Pet/docs/ui-redesign/feature-map.md)
- [Settings inventory](G:/Languages/Projects/Pet/docs/ui-redesign/settings-inventory.csv)
- [Implementation status](G:/Languages/Projects/Pet/docs/ui-redesign/implementation-status.md)

Important implementation files include:

| File or area | Responsibility |
|---|---|
| `ui/main_window.py` | Existing dashboard controls, signals, and integration points |
| `ui/dashboard_design.py` | Page organization and current settings search |
| `ui/qml_bridge.py` | Observable data and commands exposed to QML |
| `ui/qml_shell.py` | QML sidebar integration |
| `ui/qml_pages.py` | Home and Characters page hosting and live image provider |
| `ui/qml/` | QML pages and shared UI components |
| `app/application.py` | Application wiring between UI and backend services |
| `core/` | Character management, behavior, activity policies, and interactions |
| `services/` | Settings, music/audio, timers, system monitoring, and related services |
| `overlay/` | Desktop character rendering and associated effects |
| `SpiderBuddy.spec` | Executable packaging configuration |

**Rules that apply to every remaining step**

- Preserve existing user changes, character assets, imported characters, and saved settings.
- Keep Python responsible for application behavior and persistent state.
- Let QML display state and issue validated commands.
- Use one authoritative settings service; do not introduce a separate QML settings store.
- Keep dashboard, tray, shortcuts, and backend state synchronized.
- Every optional activity or effect must have an understandable enable/disable setting.
- An activity being enabled means it is allowed. It does not mean it must play immediately.
- Previewing an activity must not silently enable it or change persistent preferences.
- Unsupported activities must be identified honestly for the selected character.
- Do not remove legacy UI until its replacement has feature parity.
- Reuse shared QML components instead of styling every control separately.
- Use focused verification during implementation; run broad validation in Step 8.
- Update the implementation-status document after each completed step.

---

**STEP 5 — Activities: visual library, permissions, and previews**

**Objective**

Replace the existing native Activities page with a QML page that makes it easy to answer:

- What can this character do?
- Which activities are currently allowed?
- What does an activity look like?
- How do I change playback behavior?
- Where do I configure music, window poses, effects, and system reactions?

**5.1 Audit the existing activity behavior**

Before building the page:

1. Inspect the activity definitions and policy logic.
2. Identify which activities each character supports.
3. Identify supported aliases or fallbacks.
4. Identify every legacy setting that affects the same activity.
5. Identify automatic, manual, shortcut, and system-triggered execution paths.
6. Record which transitions are required for safe behavior, such as landing or recovering after a drag.
7. Map every existing Activities control to its QML replacement.

Do not treat the presence of an animation name alone as proof that a complete activity works. Some activities depend on overlays, positioning logic, audio detection, or window information.

**5.2 Build the page layout**

The Activities page should contain:

| Area | Contents |
|---|---|
| Header | Page title, explanation, and active character |
| Search and filters | Search activities; filter by category, enabled state, and support |
| Playback controls | Automatic playback and repeat-one activity mode |
| Activity library | Responsive activity cards |
| Activity details | Larger preview, description, permissions, and related settings |
| Timing section | Movement speed, animation speed, intervals, and cooldowns |
| Bulk controls | Enable supported activities, disable optional activities, restore activity defaults |

The grid should adapt to available width. Cards should remain readable rather than shrinking text to fit.

On narrow windows, the detail view can open as a drawer or dedicated section. On wider windows, it can appear beside the library if there is sufficient space.

**5.3 Organize the library**

Use the following categories, adapting names to the actual inventory:

| Category | Examples |
|---|---|
| Movement | Walking, running, jumping, climbing, wall sliding, swinging |
| Rest & Poses | Idle, sitting, sleeping, waking, standing, hanging, perching |
| Expressions | Waving, dancing, celebrating, interaction poses |
| Window Activities | Title-bar perching, title-bar hanging, corner positioning |
| Music & Sound | Music response, dance behavior, headphones, beat movement, sound effects |
| Effects & Toys | Existing web effects, speech bubbles, suit effects, trampoline features |
| System Reactions | Battery, charging, and heavy-system-load reactions |
| Advanced Transitions | Falling, landing, dragging, and other transition poses |

Expose only implemented functionality. If a listed example is absent from the project, do not add a nonfunctional placeholder.

**5.4 Define the activity data exposed to QML**

Each activity entry should expose enough information to render and operate the card:

- Stable activity ID.
- Display name.
- Category.
- Short description.
- Enabled state.
- Supported state for the active character.
- Explanation when unavailable.
- Whether a preview is available.
- Whether desktop playback is currently possible.
- Relevant prerequisites.
- Related settings.
- Whether the entry is optional behavior or a required transition.

Use stable IDs for logic. Do not use translated or user-facing labels as identifiers.

The model must refresh when:

- The selected character changes.
- Characters are imported or rediscovered.
- An activity setting changes.
- A relevant dependency changes.
- Settings are reloaded.

**5.5 Implement activity cards**

Each card should contain:

- An image or lightweight preview.
- Activity name.
- Short description.
- Enable/disable switch.
- Support status.
- Preview action.
- A clear route to advanced options when applicable.

Avoid running every card animation simultaneously. Prefer static thumbnails, with animation only for the selected or actively previewed item.

Show unavailable states with an explanation, such as:

> This character does not include this animation.

Do not show a working-looking control that silently does nothing.

**5.6 Implement dashboard previews**

Create a preview controller that uses the selected character’s existing assets and rendering behavior.

Requirements:

- Preview inside the dashboard.
- Do not move or interrupt the desktop companion.
- Do not alter activity permissions.
- Do not modify persistent playback mode.
- Do not start real system simulations.
- Stop playback when the preview closes.
- Stop playback when navigating away.
- Release resources when changing characters.
- Handle missing or invalid frames gracefully.
- Limit active previews to avoid unnecessary CPU and memory use.

For composite activities, include the relevant effect where supported. For example, a music preview should represent the headphone overlay if headphones are part of the implemented activity.

If an activity cannot be faithfully previewed, explain the limitation rather than substituting an unrelated animation.

**5.7 Separate preview from desktop playback**

Use distinct actions:

- **Preview** — plays only inside the dashboard.
- **Play on desktop** — requests the real activity through the existing backend.

Desktop playback must validate:

- Character support.
- Activity permission.
- Application state.
- Required context, such as an eligible window.
- Applicable focus-mode restrictions.

If playback is blocked, show the reason. Do not silently change other settings to make it run.

**5.8 Preserve playback modes**

Provide clear controls for existing automatic and repeat-one behavior.

For automatic playback:

- The backend chooses among permitted activities.
- Existing timing and behavior rules remain active.

For repeat-one playback:

- The user selects a supported, permitted activity.
- The UI clearly displays the chosen activity.
- Disabling that activity or switching to an incompatible character resolves the invalid selection predictably.
- The UI and backend remain synchronized.

Do not leave repeat-one mode pointing at an unsupported activity.

**5.9 Consolidate permissions**

Audit every trigger path so optional activities obey the same policy:

- Automatic behavior.
- Dashboard actions.
- Tray actions.
- Keyboard shortcuts.
- Music reactions.
- Battery and load reactions.
- Window interactions.

Preserve necessary physical transitions. Disabling optional jumping, for example, must not prevent the character from completing a landing after an already-started movement.

Bulk controls must have explicit scope. “Reset activity defaults” must not reset appearance, selected applications, or unrelated preferences.

**5.10 Expose related settings**

Place related controls with their activity category:

- Window activity permissions in Window Activities.
- Headphone and music-response options in Music & Sound.
- Battery and system-load responses in System Reactions.
- Existing effect switches in Effects & Toys.
- Playback intervals and speed in Timing.

Maintain one owner for each setting. Other pages may link to it, but should not create competing controls.

**Step 5 completion criteria**

- The Activities page runs in QML.
- Existing activity functionality is represented.
- Switching characters updates availability and previews.
- Optional activities have working permission controls.
- Previewing does not modify saved state or desktop behavior.
- Desktop playback uses validated backend commands.
- Bulk operations affect only their stated scope.
- Previews stop correctly and do not accumulate timers or resources.
- Focused integration checks pass.

---

**STEP 6 — Migrate Desktop & Apps, Focus & Breaks, Controls, and Settings**

**Objective**

Replace the four remaining native content pages with QML while making feature ownership obvious.

**6.1 Establish shared page components**

Extend the existing QML component set with reusable controls where needed:

- Page heading and description.
- Section panel.
- Setting row with label, help text, and control.
- Toggle row.
- Slider with displayed value.
- Selection control.
- Application list row.
- Shortcut recorder.
- Inline validation message.
- Empty state.
- Advanced-options section.
- Scoped reset action.

Each component should support:

- Dark and light themes.
- Keyboard navigation.
- Visible focus.
- Disabled-state explanations.
- Text wrapping.
- Accessible names.
- Consistent spacing.

**6.2 Desktop & Apps page**

This page owns **where the companion is allowed to operate**.

Sections:

| Section | Responsibilities |
|---|---|
| Display scope | Entire desktop or selected applications |
| Selected applications | View, add, remove, and identify configured applications |
| Window behavior | Existing boundary and placement settings |
| Monitor behavior | Existing monitor selection or movement rules |
| Placement | Existing starting position and position-recovery controls |

Implementation requirements:

1. Preserve existing application selection capabilities:
   - Running applications.
   - Registered applications where supported.
   - Browsing to an executable.
2. Present each selected application with a readable name and useful identifying information.
3. Handle duplicate selections.
4. Explain that an application can remain selected while it is not running.
5. Handle missing executables or unavailable windows.
6. Keep saved application selections intact when switching display modes.
7. Show empty-state guidance when selected-app mode has no configured applications.
8. Route updates through existing window and overlay services.
9. Keep activity permissions in Activities.

For example, Desktop & Apps controls which windows are eligible. Activities controls whether title-bar perching is allowed.

**6.3 Focus & Breaks page**

This page owns **when the companion should become quiet and how work/break sessions operate**.

Sections:

| Section | Responsibilities |
|---|---|
| Focus mode | Enable focus and explain its effect |
| Quiet behavior | Existing focus-related behavior choices |
| Focus timer | Existing focus-session controls and supported duration settings |
| Break timer | Existing break-session controls |
| Eye-break reminders | Existing reminder enablement, timing, and status |

Implementation requirements:

1. Reuse the existing timer services.
2. Do not create a second countdown in QML.
3. Keep Home, sidebar, and this page synchronized.
4. Display clear timer states:
   - Ready.
   - Running.
   - Finished.
   - Paused, only if supported by the backend.
5. Preserve existing rules for entering and leaving focus mode.
6. Make reset and stop behavior explicit.
7. Keep reminder preferences separate from the current timer session.
8. Link to relevant Activities controls for focus-reading or other quiet poses.
9. Respect character support and activity permissions.
10. Do not let closing the dashboard accidentally stop a backend timer.

**6.4 Controls page**

This page owns **how the user interacts with the companion**.

Sections should reflect implemented features:

- Mouse interaction.
- Dragging.
- Keyboard movement.
- Global shortcuts.
- Click-through behavior.
- Other existing direct-control options.

Implementation requirements:

1. Show current shortcut assignments.
2. Provide a clear shortcut-editing interaction.
3. Validate empty, invalid, duplicate, or conflicting assignments.
4. Report registration failures.
5. Apply changed shortcuts without leaving old registrations active.
6. Preserve existing mouse and drag behavior.
7. Explain interactions between click-through and direct mouse control.
8. Keep a reachable way to restore interaction through the tray or dashboard.
9. Do not capture normal typing outside the intended shortcut-recording interaction.
10. Persist assignments through the settings service.

Only expose features already supported or explicitly implemented as part of the migration.

**6.5 Settings page**

This page owns **application-wide preferences and maintenance controls**.

Sections:

| Section | Responsibilities |
|---|---|
| Appearance | Dashboard theme and existing global appearance options |
| Startup & tray | Launch behavior, tray behavior, and close behavior |
| Performance | Existing rendering or resource-related options |
| Preferences | Existing import/export/reset capabilities |
| Diagnostics | Version information and existing log/diagnostic access |

Implementation requirements:

1. Apply theme changes immediately across all QML pages.
2. Preserve startup configuration behavior.
3. Make the distinction between closing the dashboard and exiting the application clear.
4. Validate preference imports before applying them.
5. Keep reset scopes explicit.
6. Preserve character data when resetting unrelated application preferences.
7. Show restart requirements only for options that actually require restart.
8. Do not expose backend settings that have no verified runtime effect.
9. Route operating-system changes through the existing platform implementation.
10. Provide useful error messages when an operation fails.

**6.6 Wire every page through the bridge**

For each control:

1. Identify its authoritative backend value.
2. Expose that value with a change notification.
3. Implement a typed command or validated setter.
4. Connect the command to the existing service.
5. Observe external changes from tray actions and other pages.
6. Define error behavior.
7. Confirm persistence where appropriate.

Avoid a generic unrestricted “set any key” API unless it has a strict registry defining allowed keys, types, and ranges.

**6.7 Migrate one page at a time**

Recommended order:

1. Desktop & Apps.
2. Focus & Breaks.
3. Controls.
4. Settings.

For each page:

- Build QML.
- Connect services.
- Check feature parity.
- Verify resizing and theme behavior.
- Keep the native fallback until Step 7 cleanup.

**Step 6 completion criteria**

- All seven dashboard destinations now display QML content.
- Every migrated control changes the intended backend state.
- External state changes update the UI.
- Application selection, timers, shortcuts, and preferences remain functional.
- Existing settings survive the migration.
- No feature is lost or duplicated ambiguously.
- Focused checks pass for the migrated integrations.

---

**STEP 7 — Search, preferences, and migration cleanup**

**Objective**

Turn the transitional dashboard into a maintainable QML application that no longer depends on hidden Qt Widgets for data, search, or control behavior.

**7.1 Build a structured feature registry**

The current search depends on native widgets. Replace it with explicit metadata.

Each searchable entry should include:

- Stable feature ID.
- Display name.
- Description.
- Owning page.
- Owning section.
- Search keywords and aliases.
- Related setting key, if applicable.
- Target QML control or anchor.
- Availability rules.
- Optional advanced-section identifier.

Examples of aliases:

| User search | Destination |
|---|---|
| headphones | Activities → Music & Sound |
| transparent | Characters → Opacity |
| title bar | Activities → Window Activities |
| selected apps | Desktop & Apps |
| reading | Relevant focus behavior or activity |
| keyboard movement | Controls |
| start with Windows | Settings → Startup |

The feature registry should be the source of search metadata, not a copy generated from control labels at runtime.

**7.2 Implement complete search navigation**

When a user chooses a result:

1. Navigate to the correct page.
2. Open the required section.
3. Expand advanced options if necessary.
4. Wait for the target control to exist and finish layout.
5. Scroll the target into view.
6. Briefly highlight it.
7. Move keyboard focus appropriately.
8. Preserve the current value.
9. Explain unavailability if the control cannot currently be used.

Search should support:

- Partial matches.
- Case-insensitive matching.
- Familiar synonyms.
- Keyboard selection.
- Enter to open.
- Escape to dismiss.
- Clear empty and no-results states.
- Ctrl+K from anywhere in the dashboard.

Avoid stale results after character changes or settings changes.

**7.3 Remove Home’s hidden-widget state adapter**

Home currently reads some values from native labels. Replace those reads with explicit observable state.

Move these values into a proper presentation model or bridge properties:

- Current quote.
- Overlay owner or active-window description.
- Focus countdown.
- Timer state.
- System-load information.
- Battery description.
- Companion statistics.
- Selected mood.
- Any other currently label-derived state.

The backend service remains authoritative. The bridge formats or exposes its state; QML binds to it.

Do not use hidden labels as a data store.

**7.4 Consolidate commands and notifications**

Review every bridge command for:

- Argument validation.
- Supported ranges.
- Invalid values.
- Missing characters.
- Unavailable activities.
- Dependency checks.
- Error reporting.
- Correct change notifications.

Prevent update loops where:

1. QML changes a value.
2. Python emits a notification.
3. The notification triggers another write.
4. The cycle repeats.

Programmatic value updates should refresh controls without being interpreted as new user input.

**7.5 Migrate legacy settings safely**

Use the settings inventory to identify:

- Renamed keys.
- Duplicate controls.
- Deprecated aliases.
- Legacy activity flags.
- Conflicting playback settings.
- Defaults that were previously implicit.

Define deterministic migration rules:

1. Prefer an existing valid canonical value.
2. Use a legacy value only when appropriate.
3. Preserve disabled activities.
4. Preserve selected applications.
5. Preserve character selection and appearance settings.
6. Preserve user shortcut assignments.
7. Preserve unknown data unless there is a documented reason to discard it.
8. Write a migration version.
9. Make migration safe to run more than once.
10. Handle malformed or partial settings gracefully.

Before modifying an existing settings file, retain a recoverable copy or use the project’s established backup mechanism.

Settings writes should use the existing reliable persistence path, including atomic replacement if supported or added during this work.

**7.6 Remove obsolete native content**

Once feature parity is established:

- Remove native page construction that is no longer used.
- Remove hidden widgets used only for search.
- Remove obsolete label adapters.
- Remove duplicate signal handlers.
- Remove unused stylesheets.
- Remove unused imports and dead helper methods.
- Update application wiring to target bridge/controller APIs.
- Update tests to exercise the current interface.

Do not remove native dialogs merely because they are native. An existing file picker, import workflow, or platform dialog can remain if it is the correct implementation.

Distinguish obsolete dashboard widgets from useful native platform integration.

**7.7 Define startup-error recovery**

After removing the full native fallback, QML loading failures must remain understandable.

Provide a small recovery path that:

- Reports that the dashboard could not load.
- Logs the useful error details.
- Allows the user to close the application cleanly.
- Provides access to diagnostics where practical.

Do not silently leave a blank dashboard.

**7.8 Finish interaction and visual consistency**

Review all pages for:

- Consistent labels and terminology.
- Consistent setting ownership.
- Predictable tab order.
- Visible keyboard focus.
- Readable disabled states.
- Accessible control names.
- Adequate contrast.
- Long text wrapping.
- Empty states.
- Loading states.
- Error states.
- Dark/light theme consistency.
- Narrow-window behavior.
- Scroll restoration where useful.

Avoid horizontal overflow. Do not hide essential controls merely to make a page fit.

**7.9 Update documentation**

Update:

- Feature map.
- Settings inventory.
- Migration notes.
- Implementation status.
- Relevant developer instructions for adding future settings or activities.

Document how a future developer should:

1. Add a backend setting.
2. Expose it through the bridge.
3. Add its QML control.
4. Register it for search.
5. Define migration behavior if needed.
6. Verify it.

**Step 7 completion criteria**

- Search no longer inspects hidden native widgets.
- Home state no longer comes from hidden labels.
- Legacy settings migrate without losing user intent.
- Every setting has a clear owner.
- Obsolete dashboard code is removed.
- QML errors produce an understandable recovery path.
- Documentation reflects the final architecture.
- Focused checks pass after cleanup.

---

**STEP 8 — Final validation, fixes, and executable delivery**

**Objective**

Verify the completed application as a whole, fix integration defects, and produce a usable Windows executable.

**8.1 Establish a validation checklist**

Compare the finished app with the feature inventory.

For every feature, record:

- Owning page.
- Backend connection.
- Persistence behavior.
- Verification method.
- Result.
- Any remaining limitation.

Do not assume that a visible control proves the feature works.

**8.2 Run the full automated regression suite**

Run the project’s existing tests after Steps 5–7 are complete.

Add or update meaningful coverage for:

- Bridge validation.
- Settings migration.
- Search navigation.
- Activity permissions.
- Character changes.
- Preview lifecycle.
- Application selection.
- Timer synchronization.
- Shortcut updates.
- Shutdown cleanup.

Investigate failures rather than weakening assertions to match broken behavior.

After fixing a failure, rerun the affected checks. Repeat broader tests when the fix could affect other areas.

**8.3 Validate all character types**

Check:

- Tom Holland.
- Miles Morales.
- Other installed built-in characters.
- Imported characters.

For each applicable character, verify:

- Selection.
- Preview loading.
- Size and opacity.
- Supported activity detection.
- Activity preview.
- Desktop playback.
- Music accessories and effects.
- Window poses.
- Switching while an activity is active.

Ensure missing assets produce controlled behavior rather than crashes or stale images from another character.

**8.4 Validate activity permissions and interactions**

Check combinations, not only individual switches:

- Disabled activity during automatic playback.
- Disabled activity requested manually.
- Character switch while repeat-one mode is active.
- Focus mode while music is playing.
- Title-bar activity with no eligible window.
- Selected-app mode when the selected app closes.
- Pause/resume during a reaction.
- Hide/show during an activity.
- Necessary recovery transitions after disabling optional movement.

Confirm that disabling one feature does not disable unrelated functionality.

**8.5 Validate dashboard behavior**

Check every page at:

- The minimum supported window size.
- A normal desktop window size.
- Maximized size.
- Relevant Windows display scaling, where available.

Verify:

- Responsive grids.
- No horizontal clipping.
- Scroll access to all controls.
- Long character and application names.
- Dark and light themes.
- Keyboard navigation.
- Search reveal and focus.
- Dialog positioning.
- Empty and error states.
- State synchronization after tray actions.

Offscreen screenshots are useful, but do not substitute for native Windows rendering checks when that environment is available.

**8.6 Validate settings persistence and migration**

Test with isolated data directories:

1. Fresh installation defaults.
2. Existing current settings.
3. Legacy settings.
4. Partial settings.
5. Malformed settings.
6. Settings with imported characters and selected applications.

Verify:

- User preferences survive restart.
- Migration runs safely once and repeatedly.
- Reset controls affect only their stated scope.
- Invalid data is handled without destroying unrelated preferences.
- The selected character and permitted activities remain correct.

Do not run destructive reset checks against the user’s real preferences.

**8.7 Validate resource usage and preview cleanup**

Measure behavior while:

- The dashboard is idle.
- Home displays the live character.
- An activity preview is running.
- Pages are changed repeatedly.
- Characters are switched repeatedly.
- The dashboard is hidden.
- The companion is paused.

Look for:

- Accumulating timers.
- Repeated signal connections.
- Growing image caches.
- Unreleased previews.
- Unnecessary rendering when hidden.
- Persistent background activity after shutdown.

Optimize demonstrated issues without changing intended behavior.

**8.8 Validate clean shutdown**

Check all supported exit paths:

- Dashboard close, according to configured close behavior.
- Tray Quit.
- Explicit application exit.
- Ctrl+C when launched from a terminal.

Confirm that shutdown stops:

- Animation timers.
- Preview timers.
- Window polling.
- Audio monitoring.
- System monitoring.
- Global hotkeys.
- Worker threads.
- Overlay windows.

There must be no repeated traceback, hanging process, or thread-destruction error during a normal exit.

The earlier Ctrl+C complaint makes terminal shutdown a required final check.

**8.9 Build the executable**

Review and update packaging so it includes:

- QML pages.
- Shared QML components.
- Required Qt Quick modules and plugins.
- Character assets expected in the distribution.
- Images, icons, and configuration defaults.
- Runtime dependencies.
- Any files required by import or settings migration.

Use paths that work from the packaged application, not only from the repository’s working directory.

Keep writable preferences and imported content in the intended user-data location.

**8.10 Smoke-test the packaged application**

Launch the executable independently of the development launcher.

Verify at minimum:

1. Startup succeeds.
2. Sidebar and all pages load.
3. Character assets load.
4. Character switching works.
5. Activities can be configured.
6. Settings persist after restart.
7. Search reaches controls.
8. An existing import workflow opens correctly.
9. Tray behavior works.
10. Exit completes cleanly.

Where possible, launch from a different working directory to detect accidental repository-relative paths.

If a clean-machine or native-GPU check is unavailable, record it as unverified rather than claiming it passed.

**8.11 Deliver the result**

Provide:

- Absolute path to the built executable or distribution folder.
- Brief instructions for running it.
- Validation summary.
- Any known limitations.
- Any checks that could not be performed.
- Updated implementation-status document.

Do not mark Step 8 complete if packaging failed or the packaged application does not launch.

**Step 8 completion criteria**

- Full regression results are recorded.
- Identified blocking defects are fixed.
- Core user workflows work across relevant characters.
- Shutdown is clean.
- Packaging includes the required runtime files.
- The executable passes its smoke test.
- Remaining environmental limitations are disclosed accurately.

---

**Implementation order and reporting**

Perform the work in this order:

**Step 5 → Step 6 → Step 7 → Step 8**

Do not stop between completed steps to request permission to continue.

After completing each step, report:

- `Step 5 DONE`
- `Step 6 DONE`
- `Step 7 DONE`
- `Step 8 DONE`

A step is complete only when its implementation and required verification are complete. If blocked, report the actual blocker instead of marking it done.

**Copy-ready handoff prompt**

```text
Implement the complete remaining Spider-Buddy dashboard redesign plan
provided above, covering Steps 5, 6, 7, and 8.

Project:
G:\Languages\Projects\Pet

Read the current code and these documents first:
- docs/ui-redesign/feature-map.md
- docs/ui-redesign/settings-inventory.csv
- docs/ui-redesign/implementation-status.md

Steps 1–4 are already complete. Preserve their functionality and all
existing user changes. The application uses Python/PySide6 with QML
dashboard pages. Continue this architecture.

Execute sequentially:

Step 5:
Build the QML Activities library with character-specific support,
individual permissions, safe dashboard previews, validated desktop
playback, existing playback modes, timing controls, and related settings.

Step 6:
Migrate Desktop & Apps, Focus & Breaks, Controls, and Settings to QML.
Preserve all current service connections and saved settings. Keep each
feature in its assigned destination.

Step 7:
Replace widget-based search with a feature registry. Remove hidden-widget
state adapters. Consolidate bridge commands and settings migration.
Remove obsolete native dashboard code only after feature parity.
Finish accessibility, responsive behavior, error recovery, and documentation.

Step 8:
Run full regression and integration validation, fix failures, verify
character behavior and clean shutdown including Ctrl+C, build the Windows
executable, and smoke-test the packaged application.

Follow every requirement and completion criterion in the detailed plan.

Do actual implementation. Do not stop after proposing another plan.
Do not rebuild completed steps unnecessarily.
Do not replace character artwork or redesign unrelated backend systems.
Do not overwrite existing user work.
Do not add a second settings store or duplicate backend timers in QML.

Use focused verification during Steps 5–7.
Perform broad validation and packaging in Step 8.
Report honestly which checks ran and which remain unavailable.

Update docs/ui-redesign/implementation-status.md after each step.

After completing each step, write its exact completion line:
Step 5 DONE
Step 6 DONE
Step 7 DONE
Step 8 DONE

Continue automatically through all remaining steps.
Ask only when an essential decision or genuine blocker cannot be resolved
from the code, documentation, and this plan.

At final delivery, provide the absolute executable/distribution path,
a concise validation summary, and any unresolved limitations.
Never mark a blocked or unfinished step complete.
```