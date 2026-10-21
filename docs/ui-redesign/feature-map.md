# Spider-Buddy UI redesign — Step 1 feature inventory

Status: COMPLETE — 2026-10-16 (Asia/Calcutta). Documentation only; no application behavior changed.

## Evidence and scope

Inspected the current dashboard, character picker/importer, application selector, tray menu, companion context menu, default configuration, and settings references in app/core/overlay/services. `settings-inventory.csv` maps 105 existing keys, including all 98 default leaf keys. `inventory-validation.json` records coverage. Key coverage is a static inventory, not proof that every runtime feature is implemented correctly.

The target is a Qt Quick/QML dashboard with the existing Python services and desktop overlay retained. This inventory is the implementation contract for subsequent steps. Existing behavior is distinguished below from proposed controls; proposed controls are not represented as already implemented.

## Navigation and ownership

| Destination | Sections and responsibilities | Current location |
|---|---|---|
| Home | Live companion/status, current activity, active application/monitor, pause/resume, show/hide, Focus shortcut, links to character and placement settings | Dashboard and tray |
| Characters | Responsive gallery, active character, import/create, character details, personality description, size, opacity; advanced rotation only if verified | Characters, import dialog, Appearance, context menu |
| Activities | Searchable activity cards, automatic/repeat-one playback, timing, effects, music, system reactions | Animations, Behavior, Appearance, tray |
| Desktop & Apps | Desktop/application mode, target apps, monitor, placement, title/tab alignment, always-on-top if verified | Display Mode, Appearance, context menu |
| Focus & Breaks | Focus toggle, reading behavior, focus timer, work reminders, inactivity progression | Dashboard, Animations, Behavior, tray |
| Controls | Keyboard actions, modifier policy, WASD/arrows, cursor attention/radius, Spider-Sense, click-through, drag/pin instructions | Behavior, Settings, companion gestures |
| Settings | Theme, startup, frame rate, proposed reduced motion, diagnostics, version, reset | Settings, Appearance, logs |

A feature has exactly one editable owner. Other pages, tray, and context menus are shortcuts bound to the same state. Cross-links must use stable route/section/control IDs, not page indexes.

## Complete activity allocation

| Owner / category | Activities |
|---|---|
| Activities / Movement | walk, run, jump, climb_up, climb_down, wall_slide, swing |
| Activities / Rest & Poses | idle/look around, sit, sleep, wake_up, stand_up, perch, hang |
| Activities / Expressions | wave, dance, celebrate, interact |
| Activities / Window Activities | title_perch, title_hang; master window-perching enable |
| Activities / Advanced transition poses | fall, land, dragged |
| Focus & Breaks / Quiet behavior | focus_read; indexed in activity search as a linked result, without a second switch |

Activity cards expose enabled state, availability, preview, and relevant details. Global preferences apply to all characters; supported clip availability is evaluated for the selected character. Personality affects relative frequencies, not permission to bypass a disabled activity. Imported characters retain their own artwork and inherited personality unless their metadata specifies another profile.

## Non-setting actions and transient state

These actions must survive the migration even though they are not configuration keys.

| Existing action / status | New home | Migration behavior |
|---|---|---|
| Start, pause, resume; current activity/status | Home | Shared controller state; pause is distinct from hide and focus |
| Show/hide companion | Home | Mirror tray action and saved hidden preference |
| Open dashboard by tray/double click | Home / window navigation | Reopen existing window, do not create another companion |
| Close dashboard to tray; Exit; console signal shutdown | Window shell / tray | Preserve close-to-tray and explicit quit distinction |
| Select character, character submenu | Characters | Shared selection model; refresh all entry points after imports |
| Import artwork, choose template, name/suit, progress/error/cancel | Characters / Add character | Preserve validation, background work, transparent artwork generation, atomic installation and existing import cancellation limitations |
| Character preview, active badge, artwork dimensions | Characters | Consistent preview area; no aspect distortion |
| Select running/registered application, browse executable, add/remove target | Desktop & Apps / Applications | Preserve executable identity and display names; show unavailable/closed target status |
| Active owner label, selected application count | Desktop & Apps; compact Home summary | Derived live state, not another setting |
| Save current position as custom | Desktop & Apps / Placement | Preserve normalized position format and automatic restoration state |
| Preview activity; select single looping action | Activities | Dashboard-only preview; separate explicit desktop playback selection |
| Select all, deselect all, reset activity defaults | Activities | Explicit scope, preserve physical recovery; reset only activity controls |
| Glitch preview | Activities / Effects & Toys / Suit glitch | Local preview, no permanent preference changes |
| Simulate low battery | Activities / System Reactions / Battery / Preview | Clearly temporary; end simulation on closing preview |
| Simulate heavy load | Activities / System Reactions / System load / Preview | Do not change real CPU/RAM readings or preference state |
| Simulate music | Activities / Music & Sound / Preview | Temporary preview; distinguish simulated and detected audio |
| Battery percentage/charging, CPU/RAM, audio level/music status | Corresponding activity detail | Keep raw diagnostics out of Home; retain useful enabled/active status |
| Start 25/45/60-minute focus timer, cancel, remaining time | Focus & Breaks / Timer | Runtime timer state separate from saved focus behavior |
| Continuous-work time, reminder interval, preview eye-break alert | Focus & Breaks / Break reminders | One interval label; remove hardcoded tray '60-Min' mismatch with configurable default |
| Spawn trampoline, test jump/bounce | Activities / Effects & Toys / Web trampoline | Distinguish preview from explicit desktop spawn |
| Shoot web | Activities / Effects & Toys / Web shot | Preserve context action, introduce independent enable switch |
| Drag, throw/release, Shift-drag pin, unpin | Controls / Mouse interaction | Document gestures; preserve context-menu unpin recovery |
| Click reaction, double-click dashboard, right-click menu | Controls / Mouse interaction | Document existing gestures; never hide recovery navigation behind optional visual effects |
| Number-key test buttons; top-row/numpad shortcuts | Controls / Keyboard | Preview only; actual shortcuts respect activity permissions |
| Keyboard manual movement and sprint | Controls / Keyboard | Explain WASD/arrows and Shift; honor enable setting |
| Context sit/sleep/wake/walk/run/jump/swing/dance | Companion context menu -> Activities | Use same availability/permission model as dashboard |
| Context character/size/display/sound controls | Shortcuts to owning pages | Retain existing quick actions with synchronized values |

## Duplicates and conflicting concepts to resolve

1. Legacy `behavior.enable_walking/running/jumping/sleeping/sitting/climbing/swinging/hanging` overlaps `animations.enabled.*`. Migrate the current effective AND result; never re-enable an activity that was effectively disabled. Climbing maps to both directional activities.
2. `behavior.enable_random_animations` and `behavior.automatic_animations` overlap. Model playback explicitly: automatic, repeat-one, and stationary/paused intent. Do not interpret random-off as permission to start the saved repeat action. Keep the old values until migration is versioned and tested.
3. `behavior.enable_music_sync` aliases the audio setting; `behavior.enable_heavy_load_reaction` aliases the system-load setting. Canonical explicit keys win; aliases supply values only when canonical keys are absent.
4. Focus mode, timer, and reminder enable are separate concepts. Starting a timer does not silently rewrite activity preferences. Focus suppresses distractions temporarily, then restores prior effective playback state.
5. Old idle/sleep timeout keys overlap the inactivity sequence. Verify live consumers before retiring keys; expose one Relax -> Sit -> Sleep progression.
6. Window perching is an activity; its placement offset belongs in Desktop & Apps. Provide a direct link rather than duplicate controls. Label offset as manual alignment: GetWindowRect does not identify browser tab strips semantically.
7. Sound effects and music detection are separate controls in one category. Muting companion sound must not disable reacting to music.
8. Paused, hidden, pinned, focused, unavailable target, and disabled activity require distinct status text with a useful recovery action.
9. Keep all current preferences and imported artwork. Migration must be backed up/versioned and idempotent; unknown keys survive. No reset-on-upgrade.

## Missing controls / proposed additions

| Proposed control | Owner | Current gap |
|---|---|---|
| Low-battery reaction enable | Activities / System Reactions | Simulation exists; no independent preference in current defaults |
| Suit-switch glitch enable | Activities / Effects & Toys | Preview exists; no dedicated switch in current defaults |
| Web shot and web trampoline enables | Activities / Effects & Toys | Actions exist; no independent master switches |
| Optional drag/throw/pin gesture switches | Controls / Mouse interaction | Gestures exist; independent opt-outs not inventoried |
| Quiet-mode allowed behaviors summary | Focus & Breaks | Effective suppression rules need explicit presentation |
| Global settings search, aliases, result deep links | Window shell | No unified feature discovery |
| System theme, reduced UI motion | Settings / Appearance | Dark/light exist; additions require implementation |
| Section reset, diagnostics export/open logs, version panel | Settings | Add scoped recovery and support tools |
| Persistent route/category/filter state | Window shell | Preserve location during window close/reopen |

No new key names are finalized in Step 1; define them in the settings schema during the foundation step. Existing rotation, always-on-top, authentic-twos, and heavy-load threshold references require wiring verification before being advertised as working editable options. Personality editing is not promised: show the current profile first; retain per-character metadata.

## Interaction and enable rules

- All optional activities and effects have explicit opt-outs. Parent-off preserves child selections.
- Desktop hotkeys, context actions, and repeat mode honor disabled activities. The isolated dashboard preview can demonstrate a disabled activity without changing settings.
- Disabling an active effect stops it and releases its monitoring subscription when unused. Necessary falling/landing physics continue even when decorative poses are disabled.
- Unsupported clips show an explanation; never substitute another character's artwork.
- Focus mode wins over distracting automatic/music/system actions; dragging and explicit exit/recovery remain usable. A reminder may occur in focus only if its separate setting allows it.
- Tests/simulations are transient preview sessions, labeled as such and cleaned up on exit. No live desktop side effects from merely browsing activity cards.
- Clicking a search result opens its owner, expands the relevant section, scrolls to and highlights the control. Disabled controls explain the prerequisite.

## Search vocabulary seed

| Query aliases | Destination |
|---|---|
| headphones, music, audio, beat, bobbing | Activities / Music & Sound |
| mute, volume, sound | Activities / Music & Sound / Sound effects |
| Chrome, VS Code, selected apps, executable | Desktop & Apps / Applications |
| title bar, tabs, window perch, hang upside down | Activities / Window Activities (alignment link to Desktop & Apps) |
| size, bigger, smaller, transparent, opacity | Characters / Character appearance |
| study, quiet, stop moving, comic, reading | Focus & Breaks / Quiet behavior |
| water, hydration, eyes, reminder, break | Focus & Breaks / Break reminders |
| keyboard, hotkey, numbers, WASD, arrows | Controls / Keyboard |
| mouse, cursor, dodge, click through, pin, throw | Controls / Mouse interaction |
| battery, exhausted, CPU, RAM, beam | Activities / System Reactions |
| glitch, bubbles, web, trampoline | Activities / Effects & Toys |
| startup, launch, minimized, theme, FPS, logs | Settings, matching subsection |

## Step 1 acceptance and handoff

- PASS: all 98 default leaf settings mapped; 105 existing settings keys inventoried overall.
- PASS: all 24 activity identifiers assigned an owner, including the linked focus-reading setting.
- PASS: dashboard signals, tray/context actions, import and application-selection flows inventoried separately from settings.
- PASS: duplicate switches, legacy aliases, missing opt-outs, and unverified advanced controls explicitly recorded.
- PASS: runtime application files unchanged by this step.

Next: Step 2 creates Home, Characters, and Activities mockups in normal and narrow layouts using this map. Do not start QML implementation until the visual direction is reviewed. Later steps: foundation, Home/Characters, Activities, remaining pages, search/migration, then final validation/package.
