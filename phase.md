# 🕷️ SPIDER-BUDDY

## Complete Phase-by-Phase Implementation Plan

### High-Quality Animated Spider-Man Companion for Windows

**Project:** Spider-Buddy — Interactive Desktop Companion
**Platform:** Windows 10 / Windows 11
**Application Type:** Native Windows Desktop Application
**Programming Language:** Python
**Character Style:** Premium 2.5D (3D-looking animated 2D characters)
**Characters:** Miles Morales & Tom Holland's Spider-Man
**Cost:** Free and local, using open-source tools and locally available assets
**API Keys:** Not required

---

# PHASE 0 — Project Idea & Technology Stack

### Project Idea

Build a lightweight Windows desktop application featuring a **cute, high-quality animated Spider-Man character** that walks, runs, sleeps, jumps, climbs, swings, and interacts with the user.

Users can choose:

**Character Mode:**

* 🕷️ Miles Morales
* 🕸️ Tom Holland's Spider-Man

Only **one character is active at a time**.

**Display Mode:**

* **Application Mode:** The character moves only inside selected applications, such as Antigravity, ChatGPT, VS Code, or Chrome. Multiple applications can be selected.
* **Desktop Mode:** The character moves freely throughout the Windows desktop, including across application windows.

### Technology Stack

| Component                  | Technology                                |
| -------------------------- | ----------------------------------------- |
| Programming                | Python 3.12                               |
| Desktop GUI                | PySide6 (Qt)                              |
| Transparent Overlay        | PySide6 + Windows APIs                    |
| Window Detection           | pywin32 + psutil                          |
| Character Animations       | PNG/WebP sprite sequences                 |
| Animation Processing       | Pillow                                    |
| Animation State Management | Python State Machine                      |
| Character Assets           | AI-generated 3D-style 2D animation frames |
| Settings Storage           | JSON                                      |
| Local Database             | SQLite (optional)                         |
| Packaging                  | PyInstaller                               |
| Development IDE            | Google Antigravity                        |

**Architecture:** Fully local desktop application. No backend server or web application required.

---

# PHASE 1 — Project Setup & Application Architecture

**Goal:** Establish a clean, modular application capable of supporting both characters, multiple display modes, and future animations.

## 1.1 Project Structure

Create the following architecture:

```text
SpiderBuddy/
│
├── main.py
├── requirements.txt
├── pyproject.toml
│
├── app/
│   ├── application.py
│   ├── bootstrap.py
│   └── lifecycle.py
│
├── core/
│   ├── character_manager.py
│   ├── animation_engine.py
│   ├── behavior_controller.py
│   ├── movement_controller.py
│   ├── interaction_manager.py
│   └── state_machine.py
│
├── overlay/
│   ├── transparent_overlay.py
│   ├── overlay_manager.py
│   ├── window_detector.py
│   ├── window_tracker.py
│   ├── boundary_controller.py
│   ├── monitor_manager.py
│   └── hit_test_manager.py
│
├── characters/
│   ├── miles_morales/
│   │   ├── character.json
│   │   ├── sprites/
│   │   └── animations/
│   │
│   └── tom_holland/
│       ├── character.json
│       ├── sprites/
│       └── animations/
│
├── ui/
│   ├── main_window.py
│   ├── dashboard.py
│   ├── character_selection.py
│   ├── application_selector.py
│   ├── animation_settings.py
│   ├── behavior_settings.py
│   └── system_tray.py
│
├── services/
│   ├── settings_service.py
│   ├── startup_service.py
│   └── activity_monitor.py
│
├── config/
│   ├── default_settings.json
│   └── animations.json
│
├── assets/
│   ├── icons/
│   ├── sounds/
│   └── previews/
│
├── tests/
│
└── build/
```

## 1.2 Core Requirements

Implement the following foundations:

1. Single-instance application execution.
2. Centralized settings management.
3. Character loading system.
4. Independent animation and movement controllers.
5. Windows process and window monitoring.
6. Application-wide event handling.
7. Error handling and structured logging.
8. Graceful shutdown and resource cleanup.

Use a modular architecture so the character's appearance, behavior, and display restrictions remain independent.

## 1.3 Application Startup

When Spider-Buddy launches:

```text
Launch Spider-Buddy
        ↓
Load Saved Settings
        ↓
Initialize Windows Services
        ↓
Initialize Overlay Manager
        ↓
Load Selected Character
        ↓
Initialize Animation Engine
        ↓
Apply Display Mode
        ↓
Start Character Behavior
```

The application must not start multiple companions accidentally when the executable is opened repeatedly.

### Phase 1 Deliverable

A working Python application with a basic window, persistent settings, system tray integration, and an initialized overlay system.

---

# PHASE 2 — Character Design & Animation Assets

**Goal:** Create two premium-quality Spider-Man characters with consistent artwork, expressive proportions, and reusable animation assets.

This is one of the most important phases because the quality of the entire application depends on the character assets.

## 2.1 Character 1 — Miles Morales

Use your uploaded reference image as the primary design reference.

### Appearance

| Property       | Specification                       |
| -------------- | ----------------------------------- |
| Character      | Miles Morales                       |
| Costume        | Black and red Spider-Man suit       |
| Head           | Slightly oversized                  |
| Eyes           | Large, expressive white lenses      |
| Hoodie         | Black hoodie                        |
| Headphones     | Black and red                       |
| Shoes          | Red, black, and white sneakers      |
| Body           | Small, athletic cartoon proportions |
| Visual Style   | High-quality 3D-rendered cartoon    |
| Default Height | 200 pixels                          |

**Important:** Preserve the design identity of your reference image.

Miles should look cute but not childish or excessively exaggerated.

## 2.2 Character 2 — Tom Holland's Spider-Man

Create a second character based on the Spider-Man costume from Tom Holland's movies.

### Appearance

| Property       | Specification                           |
| -------------- | --------------------------------------- |
| Character      | Peter Parker / Spider-Man               |
| Costume        | Red and blue Spider-Man suit            |
| Head           | Slightly oversized                      |
| Eyes           | Expressive white lenses                 |
| Suit Details   | Detailed spider emblem and web patterns |
| Body           | Compact, athletic                       |
| Visual Style   | Same quality as Miles Morales           |
| Default Height | 200 pixels                              |

The two characters must share compatible animation conventions.

For example:

* Similar visual proportions.
* Similar frame dimensions.
* Matching animation names.
* Consistent movement speed.
* Similar interaction behavior.

This allows users to switch characters without restarting the application.

## 2.3 Character Art Style

Use **2.5D animation**.

The character should look like a high-quality 3D model, but the application displays pre-rendered 2D frames.

This is an important distinction:

**3D-style artwork does not require a real-time 3D engine.**

Each animation is a sequence of high-quality transparent images.

Recommended specifications:

| Property                  | Value                          |
| ------------------------- | ------------------------------ |
| Original frame resolution | 512×512 or 768×768             |
| Desktop display size      | 150–350 px tall                |
| Background                | Fully transparent              |
| File format               | PNG or lossless WebP           |
| Animation playback        | 12–30 FPS, depending on action |
| Lighting                  | Consistent across frames       |
| Character position        | Consistent reference point     |
| Animation direction       | Left and right                 |

Use source artwork larger than the intended display size so resizing does not noticeably reduce quality.

## 2.4 Character Animation Library

Each character should eventually support the following activities.

| Animation   | Behavior                        | Priority |
| ----------- | ------------------------------- | -------- |
| Idle        | Normal standing and breathing   | Critical |
| Walk        | Walking left and right          | Critical |
| Run         | Faster movement                 | High     |
| Sleep       | Lying down and sleeping         | High     |
| Wake Up     | Transition from sleeping        | High     |
| Sit         | Sitting on available surfaces   | High     |
| Stand Up    | Transition from sitting         | High     |
| Jump        | Jumping between positions       | High     |
| Land        | Landing after a jump            | High     |
| Wall Climb  | Climbing application boundaries | High     |
| Web Swing   | Swinging across the window      | High     |
| Hang        | Hanging upside down             | Medium   |
| Wave        | Greeting the user               | High     |
| Look Around | Moving head and eyes            | High     |
| Stretch     | Stretching during idle time     | Medium   |
| Backflip    | Performing a flip               | Medium   |
| Dance       | Short animated dance            | Medium   |
| Fall        | Falling with gravity            | Medium   |
| Celebrate   | Happy animation                 | Medium   |
| Confused    | Funny reaction                  | Low      |

**Total: 20 proposed animations per character.**

Implement the critical actions first, followed by the remaining animations in later phases.

## 2.5 Animation Asset Creation

Use AI-generated artwork or an animation-capable character tool to produce consistent character frames.

Recommended process:

```text
Character Reference Image
          ↓
Create Character Design Sheet
          ↓
Create Front / Side / Back Views
          ↓
Generate Individual Animations
          ↓
Extract Animation Frames
          ↓
Remove Background
          ↓
Align Frames
          ↓
Normalize Character Scale
          ↓
Export Transparent PNG/WebP
          ↓
Package Animation Assets
```

A single reference image is not sufficient to produce all these movements automatically. Each animation must be generated, drawn, or rendered separately.

### Important Asset Requirements

* Keep costume details consistent.
* Avoid changing facial proportions between frames.
* Prevent flickering and accidental shape changes.
* Ensure hands and legs move naturally.
* Preserve correct character scale.
* Avoid white backgrounds or visible rectangular borders.
* Preserve alpha transparency.
* Use smooth animation transitions.

Store metadata for each animation, including its frame rate, loop behavior, direction, and character anchor point.

### Phase 2 Deliverable

Two visually consistent characters with initial idle, walking, and sleeping animation assets.

---

# PHASE 3 — Transparent Desktop Overlay System

**Goal:** Display an animated Spider-Man over Windows applications without interfering with normal computer usage.

## 3.1 Transparent Overlay

Create a transparent, frameless window using PySide6.

Requirements:

* No visible window border.
* No rectangular background.
* Only the character is visible.
* No taskbar button for the character overlay.
* Smooth animation rendering.
* Correct transparency around the character.
* Support high-resolution displays.

The overlay should contain only what is necessary to render the character.

## 3.2 Mouse Click-Through

**Critical requirement: The character must not interfere with coding or normal application interactions.**

Expected behavior:

| Mouse Position           | Expected Result             |
| ------------------------ | --------------------------- |
| Transparent overlay area | Click passes to application |
| Character body           | Character interaction       |
| Character head           | Character interaction       |
| Outside character        | Normal Windows behavior     |
| Dragging character       | Character moves             |
| Right-clicking character | Character menu opens        |

Implement precise hit testing based on the visible sprite area.

For Windows, use an appropriate combination of:

* Layered windows.
* Per-pixel alpha information.
* Native Windows hit testing.
* `WM_NCHITTEST`.
* `HTTRANSPARENT`, where applicable.
* Qt mouse event handling.

Avoid making the entire overlay mouse-interactive.

Also, do not enable `WS_EX_TRANSPARENT` indiscriminately if doing so prevents all character interactions.

## 3.3 Window Rendering Strategy

Prefer lightweight per-character transparent windows rather than one permanently interactive fullscreen overlay.

The system should support:

* Transparent animated rendering.
* Character rotation.
* Character scaling.
* Independent character positioning.
* Dynamic window boundaries.
* Reliable click-through behavior.

## 3.4 High-DPI Support

Correctly support Windows display scaling:

* 100%
* 125%
* 150%
* 175%
* 200%

The character must maintain consistent proportions and remain sharp.

### Phase 3 Deliverable

A transparent animated character that can be dragged around Windows while allowing normal interaction with the underlying applications.

---

# PHASE 4 — Display Modes: Selected Applications & Entire Desktop

**Goal:** Implement the two primary operating modes.

This is a core requirement of Spider-Buddy.

# MODE A — Selected Applications Only

In this mode, Spider-Man should appear **only inside applications selected by the user**.

### Example

The user selects:

```text
Selected Applications

☑ Google Antigravity
☑ ChatGPT
☑ Visual Studio Code
☐ Google Chrome
☐ File Explorer
```

Spider-Man is allowed to appear inside the three selected applications.

He must remain invisible in applications that are not selected.

## 4.1 Detect Installed and Running Applications

Use Windows APIs and `psutil`.

The application selector should show:

* Application icon.
* Application name.
* Executable name.
* Running status.
* Selection checkbox.

For example:

| Application | Executable          | Selected |
| ----------- | ------------------- | -------- |
| Antigravity | Detected executable | ✅        |
| ChatGPT     | Detected executable | ✅        |
| VS Code     | Code.exe            | ✅        |
| Chrome      | chrome.exe          | ❌        |

Do not assume executable names for all applications.

Resolve actual process identities from Windows.

Allow users to select currently running applications and retain their choices for future launches.

## 4.2 Multiple Application Support

Suppose the user selects:

* Antigravity
* ChatGPT
* VS Code

Expected behavior:

**Scenario 1: Antigravity is active**

Spider-Man appears inside Antigravity and roams throughout that window.

**Scenario 2: User switches to ChatGPT**

Spider-Man hides from Antigravity and appears inside ChatGPT.

**Scenario 3: User switches to VS Code**

Spider-Man moves to the VS Code overlay and resumes his activities.

**Scenario 4: User opens Chrome**

If Chrome is not selected, Spider-Man disappears.

**Scenario 5: User returns to Antigravity**

Spider-Man reappears.

### Application Switching

Implement:

* Foreground window detection.
* Selected application matching.
* Safe overlay relocation.
* Animation state preservation.
* Correct hiding and restoring.
* Optional remembered positions per application.

**Only one Spider-Man character should be displayed at a time.**

## 4.3 Window Boundaries

For every selected application, detect:

* Window X coordinate.
* Window Y coordinate.
* Window width.
* Window height.
* Minimized state.
* Maximized state.
* Foreground status.
* Monitor location.

Spider-Man must remain inside the visible application boundaries.

Example:

```text
┌────────────────────────────────────────────────┐
│                 ANTIGRAVITY IDE                │
├────────────┬───────────────────┬───────────────┤
│            │                   │               │
│ Explorer   │    Code Editor    │    AI Chat    │
│            │                   │               │
│     🕷️     │                   │               │
│            │                   │               │
│            │                   │               │
├────────────┴───────────────────┴───────────────┤
│                    Terminal                    │
│                                                │
└────────────────────────────────────────────────┘
```

The character should be able to move across the editor, sidebar, terminal, and other interface areas.

**Important:** This must be a native window overlay. Do not place the character inside a small editor webview.

## 4.4 Window Events

Support these events:

| Event                          | Character Behavior        |
| ------------------------------ | ------------------------- |
| Application opened             | Detect available window   |
| Window moved                   | Update character position |
| Window resized                 | Recalculate boundaries    |
| Window maximized               | Expand roaming area       |
| Window minimized               | Hide character            |
| Window restored                | Restore character         |
| Application closed             | Hide character            |
| Unselected application focused | Hide character            |
| Selected application focused   | Show character            |

For overlapping Windows applications, prevent Spider-Man from appearing over an unrelated foreground window.

---

# MODE B — Entire Desktop

In Desktop Mode, Spider-Man can move across the Windows desktop.

### Behavior

* Walk across the desktop.
* Move over application windows.
* Sit near the taskbar.
* Climb visible screen boundaries.
* Swing across the screen.
* Sleep in a corner.
* Follow the cursor.

Unlike Application Mode, Spider-Man is not restricted to a particular application's rectangle.

## 4.5 Multi-Monitor Support

Provide the following desktop options:

**Monitor Selection:**

* Primary monitor.
* Secondary monitor.
* All monitors.

For All Monitors mode, allow Spider-Man to transition between connected display regions.

Account for monitors with different:

* Resolutions.
* Scaling factors.
* Relative positions.
* Refresh rates.

Restrict movement to actual visible monitor areas rather than assuming every monitor forms one continuous rectangular surface.

## 4.6 Switching Between Modes

Add a simple setting:

```text
DISPLAY MODE

(●) Selected Applications
( ) Entire Desktop
```

Changing the display mode must not require restarting Spider-Buddy.

### Phase 4 Deliverable

Both display modes work correctly, including support for multiple selected applications, window lifecycle events, and multi-monitor desktops.

---

# PHASE 5 — Animation Engine

**Goal:** Build a reusable animation system capable of rendering both Spider-Man characters smoothly.

## 5.1 Animation Playback

Create an `AnimationEngine` that supports:

* Animation frame loading.
* Frame scheduling.
* Looping animations.
* One-time animations.
* Animation cancellation.
* Direction changes.
* Frame-specific offsets.
* Smooth state transitions.

Animation speed should be independent of the monitor's refresh rate.

Use elapsed time to determine which animation frame should be displayed.

## 5.2 Animation States

Define the following states:

```text
IDLE
WALKING
RUNNING
SITTING
SLEEPING
WAKING_UP
JUMPING
FALLING
LANDING
CLIMBING
SWINGING
HANGING
DANCING
INTERACTING
```

Each state has its own rules.

For example:

```text
IDLE
  ↓
WALKING
  ↓
SITTING
  ↓
SLEEPING
  ↓
WAKING_UP
  ↓
IDLE
```

Other transitions:

```text
WALKING → RUNNING → JUMPING → LANDING

IDLE → CLIMBING → HANGING → FALLING → LANDING

IDLE → WEB_SWING → LANDING
```

Prevent invalid transitions such as immediately switching from sleeping to running without an appropriate wake-up transition.

## 5.3 Animation Blending

Because this is a sprite-based system, do not assume that skeletal animation blending is available.

Instead, implement:

* Transition-specific frames.
* Frame alignment.
* Appropriate timing.
* Smooth position interpolation.
* Optional short crossfades where visually suitable.

Avoid excessive crossfading that creates ghost images.

## 5.4 Mirroring

For walking left and right:

* Reuse a horizontally flipped sprite sequence where the design permits.
* Use dedicated frames when asymmetric costume details would otherwise appear incorrect.

The character should turn naturally when changing direction.

### Phase 5 Deliverable

A fully functional sprite animation engine with idle, walking, running, sleeping, jumping, and transition support.

---

# PHASE 6 — Intelligent Movement & Physics

**Goal:** Make Spider-Man behave like a living character rather than an animation playing at one fixed position.

## 6.1 Autonomous Movement

Spider-Man should independently decide when to:

* Walk.
* Stop.
* Change direction.
* Run.
* Sit.
* Jump.
* Sleep.
* Climb.
* Swing.

Use a **finite state machine with weighted behavior selection**.

No AI API or external language model is required.

## 6.2 Movement Controller

Implement:

* Movement velocity.
* Acceleration.
* Deceleration.
* Direction.
* Gravity.
* Jump velocity.
* Landing detection.
* Boundary collision.
* Animation synchronization.

Movement and animation must remain synchronized.

For example, a walking animation should not continue when the character has stopped moving.

## 6.3 Window Edge Detection

Detect the active movement region.

When Spider-Man reaches an edge, he can:

1. Turn around.
2. Stop.
3. Jump away.
4. Begin climbing.
5. Hang from the edge.

Choose an action according to the current state and available animation assets.

The character must never unexpectedly move outside the selected application in Application Mode.

## 6.4 Climbing Behavior

Spider-Man can climb the left and right boundaries of the active window.

Expected behavior:

```text
Walking
   ↓
Reaches Window Edge
   ↓
Starts Climbing
   ↓
Moves Vertically
   ↓
Stops at Upper Boundary
   ↓
Hangs / Sits / Changes Direction
```

The character's orientation should match the surface.

## 6.5 Web-Swinging Physics

Implement simple pendulum-inspired movement.

The visual sequence should include:

* Web attachment point.
* Character swinging.
* Appropriate body rotation.
* Arc-shaped movement.
* Release.
* Falling.
* Landing.

The web line should appear attached to an appropriate location within the allowed window.

In Desktop Mode, web-swinging can cover larger distances.

In Application Mode, the entire animation must remain inside the selected application.

## 6.6 Random Behavior

Avoid repetitive behavior.

For example:

```text
Walk for 8 seconds
     ↓
Stop and Look Around
     ↓
Sit for 12 seconds
     ↓
Stand Up
     ↓
Jump
     ↓
Walk Again
```

Use controlled randomness with configurable minimum and maximum durations.

Avoid excessive jumping, swinging, or constant movement that distracts the user.

### Phase 6 Deliverable

Spider-Man autonomously walks, runs, jumps, climbs, and performs other movement behaviors within the currently selected display boundaries.

---

# PHASE 7 — Mouse Interactions & Responsive Character

**Goal:** Make Spider-Man respond naturally to the user's actions.

## 7.1 Mouse Interactions

| User Action           | Spider-Man Reaction        |
| --------------------- | -------------------------- |
| Single click          | Wave or look toward user   |
| Double click          | Backflip or celebrate      |
| Left-click drag       | Pick up and move           |
| Right-click           | Open character menu        |
| Cursor nearby         | Look toward cursor         |
| Cursor moving quickly | Occasionally react         |
| Cursor leaves region  | Resume autonomous behavior |

Mouse tracking should be lightweight and local.

## 7.2 Dragging Behavior

When the user drags Spider-Man:

1. Pause normal movement.
2. Switch to a suitable dragging pose.
3. Follow the cursor.
4. Respect current movement boundaries.
5. Detect release.
6. Transition to a landing or idle animation.

Do not allow dragging to permanently place Spider-Man outside the selected application in Application Mode.

## 7.3 Idle Detection

Detect user inactivity using Windows APIs.

Suggested default behavior:

| Inactivity   | Behavior              |
| ------------ | --------------------- |
| 0–2 minutes  | Normal activities     |
| 2–5 minutes  | More relaxed behavior |
| 5–10 minutes | Sitting or stretching |
| 10+ minutes  | Sleeping              |

These durations must be customizable.

The character should wake up when the user returns.

## 7.4 Character Context Menu

Right-clicking Spider-Man should show:

```text
🕷️ SPIDER-BUDDY

Wake Up
Sit Down
Sleep
Walk
Run
Jump
Web Swing
Dance

──────────────

Change Character
Change Display Mode
Character Size
Settings
Exit
```

Each action must execute the corresponding behavior, not merely display a placeholder.

## 7.5 Sound Effects

Optional character sound effects:

* Web shooting.
* Jumping.
* Landing.
* Sleeping.
* Character reactions.

Sound must be disabled by default or easily muted.

Provide an adjustable volume control.

### Phase 7 Deliverable

A responsive character that reacts to mouse input, supports dragging and context menus, and changes behavior according to user inactivity.

---

# PHASE 8 — Main Application UI & Settings

**Goal:** Build a professional control application for managing Spider-Buddy.

The character overlay itself should remain minimal. Configuration happens inside a separate native settings window.

## 8.1 Main Dashboard

Proposed layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ 🕷️ Spider-Buddy                                  ─  □  ×     │
├────────────────┬─────────────────────────────────────────────┤
│                │                                             │
│  Dashboard     │       SPIDER-BUDDY                          │
│                │                                             │
│  Characters    │          [ Character Preview ]              │
│                │                                             │
│  Display Mode  │       Active: Miles Morales                 │
│                │       Status: Walking                       │
│  Applications  │                                             │
│                │       [ Pause ]   [ Hide Character ]       │
│  Animations    │                                             │
│                │                                             │
│  Behavior      │       Display: Selected Applications        │
│                │       Selected Apps: 3                      │
│  Appearance    │                                             │
│                │                                             │
│  Settings      │                                             │
│                │                                             │
└────────────────┴─────────────────────────────────────────────┘
```

### UI Design

Use:

* Modern desktop styling.
* Rounded panels.
* Consistent spacing.
* Professional typography.
* Subtle animations.
* Dark and light themes.
* Responsive resizing.
* Clearly labeled controls.

Avoid unnecessary gradients, excessive glow effects, and oversized cards.

---

## 8.2 Character Selection

Display two character cards.

### Character 1

**Miles Morales**

* Black/red costume.
* Hoodie.
* Headphones.
* Sneakers.
* Slightly oversized head.

### Character 2

**Tom Holland's Spider-Man**

* Red/blue Spider-Man costume.
* Expressive white eyes.
* Small stylized body.
* Slightly oversized head.

The user chooses one.

```text
SELECT CHARACTER

┌────────────────────┐  ┌────────────────────┐
│                    │  │                    │
│   [ Miles Image ]  │  │   [ Peter Image ]  │
│                    │  │                    │
│   Miles Morales    │  │   Peter Parker     │
│                    │  │                    │
│      SELECTED      │  │      SELECT        │
└────────────────────┘  └────────────────────┘
```

Character switching must happen without closing the application.

Only one character should be active at a time.

---

## 8.3 Display Mode Settings

```text
DISPLAY MODE

● Selected Applications
○ Entire Desktop

Selected Applications:

☑ Antigravity
☑ ChatGPT
☑ VS Code
☐ Chrome

[ Add Application ]

Behavior When App Is Minimized:
☑ Hide Character

Behavior When Another App Is Active:
☑ Hide Character
```

Also include a clear indication of which selected application currently owns the character overlay.

---

## 8.4 Character Appearance Settings

Provide:

| Setting           | Options                             |
| ----------------- | ----------------------------------- |
| Character Size    | 100–400 px                          |
| Default Size      | 200 px                              |
| Animation Speed   | Slow / Normal / Fast                |
| Character Opacity | 50–100%                             |
| Default Position  | Bottom Left / Bottom Right / Custom |
| Flip Direction    | Automatic                           |
| Sound             | On / Off                            |
| Display FPS       | Automatic / 30 / 60                 |

The size control should adjust the character without damaging sprite quality.

---

## 8.5 Behavior Settings

Allow users to enable or disable individual behaviors.

```text
CHARACTER ACTIVITIES

☑ Walking
☑ Running
☑ Jumping
☑ Sleeping
☑ Sitting
☑ Wall Climbing
☑ Web Swinging
☑ Hanging
☑ Mouse Following
☑ Random Animations
☐ Sound Effects
```

### Activity Frequency

Provide three presets:

**Calm:** Mostly sits, sleeps, and occasionally walks.

**Normal:** Balanced walking, sitting, climbing, and jumping.

**Playful:** More frequent running, swinging, climbing, and reactions.

Default: **Normal**.

### Phase 8 Deliverable

A polished native desktop control panel with character selection, application selection, display modes, appearance controls, and behavior settings.

---

# PHASE 9 — Windows Integration & Background Operation

**Goal:** Make Spider-Buddy behave like a native Windows application.

## 9.1 System Tray

Spider-Buddy should continue running when the settings window is closed.

Add a system tray icon with:

* Open Dashboard.
* Show/Hide Character.
* Pause/Resume.
* Switch Character.
* Switch Display Mode.
* Exit.

Closing the dashboard must not accidentally terminate the companion.

## 9.2 Windows Startup

Provide:

**Launch Spider-Buddy When Windows Starts: On/Off**

Default: Off.

When enabled, register the application through the appropriate Windows user startup mechanism.

Do not require administrator privileges for normal operation.

## 9.3 Session Management

Handle:

* Windows lock.
* Windows unlock.
* Sleep mode.
* System resume.
* Display disconnection.
* Resolution changes.
* Monitor reconfiguration.

When Windows is locked, stop unnecessary animation activity.

When the session resumes, safely restore the current character.

## 9.4 Resource Management

Target lightweight operation.

Recommended behavior:

| State                       | Rendering         |
| --------------------------- | ----------------- |
| Character actively moving   | 30–60 FPS         |
| Character sleeping          | Reduced FPS       |
| Character hidden            | Suspend rendering |
| Selected application closed | Suspend animation |
| Windows locked              | Suspend animation |

Avoid unnecessary CPU polling.

Use Windows event notifications where practical.

## 9.5 Resource Usage Targets

Aim for:

* Low idle CPU utilization.
* Minimal memory usage.
* No GPU-heavy rendering engine.
* No background network requests.
* Fast application startup.
* No unnecessary processes.

Measure actual performance rather than assuming the targets are achieved.

### Phase 9 Deliverable

A stable Windows background application with system tray management, optional startup integration, proper session handling, and optimized resource consumption.

---

# PHASE 10 — Advanced Character Behaviors

**Goal:** Make the companion feel alive and entertaining without interfering with work.

These features should be implemented after the core system is stable.

## 10.1 Spider-Man Personality

Both characters can have different behavior profiles.

### Miles Morales

* Playful movement.
* More frequent dancing.
* Casual sitting poses.
* Occasional headphone-adjusting animation.
* Energetic jumps.
* Relaxed sleeping poses.

### Tom Holland's Spider-Man

* Energetic jumping.
* Acrobatic movements.
* More frequent wall crawling.
* Playful waving.
* Hero-style landing poses.
* Occasional web-swinging.

These differences should be implemented through configuration and animation assets rather than duplicate behavior engines.

## 10.2 Smart Activity Reactions

Provide optional reactions to simple local system events.

Examples:

**When the user returns after inactivity:**

Spider-Man wakes up and waves.

**When the selected application is opened:**

Spider-Man can enter with a short landing animation.

**When the selected application changes:**

Spider-Man can perform a short transition instead of abruptly teleporting.

**When the user has been working for a long time:**

Spider-Man may sit or sleep quietly.

Avoid monitoring private application content, keystrokes, or conversations.

## 10.3 Interactive Animations

Additional optional activities:

* Web shooting toward the cursor.
* Hanging from the upper window boundary.
* Crawling along application edges.
* Sitting on the bottom edge of a panel.
* Performing a short acrobatic sequence.
* Swinging from one edge to another.

For panel-specific behavior, use known window geometry or explicit user-defined anchor positions. Do not assume Python can automatically understand every application's internal UI layout.

## 10.4 Character Animation Cooldowns

Implement cooldowns to prevent distractions.

Examples:

* No repeated backflips within a short interval.
* Avoid web swinging continuously.
* Limit rapid behavior transitions.
* Do not repeatedly wake a sleeping character without user activity.

Make behavior frequency configurable.

### Phase 10 Deliverable

Two character-specific behavior profiles with expressive animations and controlled, context-aware interactions.

---

# PHASE 11 — Testing, Optimization & Bug Fixing

**Goal:** Verify that all core features work reliably across different Windows environments.

## 11.1 Functional Testing

| Test                         | Expected Result                   |
| ---------------------------- | --------------------------------- |
| Launch application           | Opens successfully                |
| Load Miles Morales           | Correct character appears         |
| Load Tom Holland Spider-Man  | Correct character appears         |
| Switch characters            | Works without restarting          |
| Select Antigravity           | Character stays within IDE        |
| Select ChatGPT               | Character appears inside ChatGPT  |
| Select multiple applications | Supports switching between them   |
| Open unselected application  | Character hides                   |
| Enable Desktop Mode          | Character can roam across desktop |
| Move application window      | Character follows correctly       |
| Resize application           | Boundaries update                 |
| Minimize application         | Character disappears              |
| Restore application          | Character reappears               |
| Walk animation               | Plays smoothly                    |
| Sleep animation              | Plays correctly                   |
| Web-swing animation          | Remains inside allowed boundaries |
| Click character              | Interaction works                 |
| Click transparent area       | Underlying app receives click     |
| Drag character               | Works correctly                   |
| Change character size        | Resizes correctly                 |
| Restart Spider-Buddy         | Settings persist                  |

## 11.2 Display Testing

Test:

* 1920×1080.
* 2560×1440.
* 4K where available.
* Different Windows scaling levels.
* Multiple monitors.
* Different taskbar positions.
* Maximized and restored application windows.

## 11.3 Edge Cases

Test situations such as:

* Antigravity crashes.
* ChatGPT closes unexpectedly.
* Multiple windows of the same application exist.
* A selected application starts after Spider-Buddy.
* The user switches monitors.
* The selected window becomes very small.
* A modal dialog opens.
* Windows is locked.
* Display scaling changes during execution.

Ensure the character never becomes stuck in an invisible or unresponsive state.

## 11.4 Performance Testing

Measure:

* CPU usage.
* RAM usage.
* Animation frame rate.
* Input latency.
* Window tracking latency.
* Startup time.

Optimize sprite caching and animation rendering if necessary.

### Phase 11 Deliverable

A tested and stable application with verified interaction behavior, accurate movement boundaries, and acceptable resource usage.

---

# PHASE 12 — Windows EXE Packaging & Final Release

**Goal:** Convert the Python project into a standalone Windows application.

## 12.1 Build Executable

Use PyInstaller to package the application.

Expected output:

```text
dist/
└── SpiderBuddy/
    ├── SpiderBuddy.exe
    ├── assets/
    └── required runtime files/
```

A one-folder build is recommended initially because it is easier to debug and update assets.

## 12.2 Application Assets

Package:

* Miles Morales character assets.
* Tom Holland Spider-Man character assets.
* Animation metadata.
* Application icons.
* Optional sound effects.
* Default settings.

Keep user-specific settings in the appropriate Windows user data directory rather than inside the installed application folder.

## 12.3 Windows Installation

Optionally create an installer using Inno Setup.

The installer should support:

* Installation directory selection.
* Start Menu shortcut.
* Desktop shortcut.
* Uninstallation.
* Optional startup registration.

No administrator privileges should be necessary for normal user-level installation when installed in an appropriate user directory.

## 12.4 Final Application Features

The finished product should provide:

✅ Two selectable Spider-Man characters.

✅ High-quality 2.5D animations.

✅ One active character at a time.

✅ Application-specific movement.

✅ Multiple selected applications.

✅ Entire desktop movement.

✅ Automatic window tracking.

✅ Walking, running, sleeping, jumping, climbing, and swinging.

✅ Mouse interactions.

✅ Adjustable character size.

✅ Character-specific behaviors.

✅ System tray controls.

✅ Saved preferences.

✅ Smooth animation playback.

✅ Standalone Windows executable.

✅ No API keys.

✅ Local operation.

**Distribution note:** Miles Morales and the Tom Holland Spider-Man costume designs are associated with copyrighted Marvel characters. For a personal prototype, you can work with legitimately obtained reference assets, but public distribution of branded characters or third-party models requires appropriate rights and compliance with asset licenses.

### Phase 12 Deliverable

A standalone Windows application named **Spider-Buddy**, ready for local installation and everyday use.

---

# 📊 Complete Development Roadmap

| Phase  | Focus                                   | Priority |
| ------ | --------------------------------------- | -------- |
| **0**  | Project idea and tech stack             | Planning |
| **1**  | Project architecture and setup          | Critical |
| **2**  | Character creation and animation assets | Critical |
| **3**  | Transparent Windows overlay             | Critical |
| **4**  | Application Mode and Desktop Mode       | Critical |
| **5**  | Animation engine                        | Critical |
| **6**  | Movement and physics                    | High     |
| **7**  | Mouse interactions and responsiveness   | High     |
| **8**  | Main UI and settings                    | High     |
| **9**  | Windows integration                     | High     |
| **10** | Advanced character behaviors            | Medium   |
| **11** | Testing and optimization                | Critical |
| **12** | Windows executable and packaging        | Final    |

---

## 🎯 Recommended Implementation Order

Although the full plan contains 13 phases, I recommend dividing development into **three major milestones**.

### Milestone 1 — Working Spider-Man Companion

**Phases 0–5**

At this milestone:

* Both characters can be loaded.
* Character switching works.
* The transparent overlay is functional.
* Application Mode and Desktop Mode work.
* Basic animations play.

**Result:** A real working desktop companion, even before advanced behaviors are implemented.

### Milestone 2 — Living Spider-Man

**Phases 6–9**

At this milestone:

* Spider-Man walks, jumps, sleeps, and climbs.
* Mouse interactions work.
* The UI is complete.
* Application switching works reliably.
* Background operation and Windows integration are functional.

**Result:** A usable everyday Spider-Man desktop companion.

### Milestone 3 — Premium Experience

**Phases 10–12**

At this milestone:

* Advanced Spider-Man-specific animations work.
* Character personalities are implemented.
* Performance is optimized.
* Bugs are fixed.
* The application is packaged as a Windows executable.

**Result:** A polished, high-quality Spider-Buddy application.

---

## ⭐ Important Instructions for Your Antigravity AI Agent

When implementing this project, follow these rules:

1. **Do not use pixel-art characters.** The characters must look like premium 3D-rendered cartoon characters.
2. **Do not substitute static images for animations.** Each required activity needs actual frames and functional playback.
3. **Do not generate placeholder characters and claim the project is complete.** Use approved character assets.
4. **Do not create a web application.** This must be a native Windows desktop application.
5. **Do not restrict Spider-Man to a small editor panel.** Application Mode must support the full selected application window.
6. **Do not interfere with mouse clicks or keyboard input.**
7. **Do not implement features as UI-only placeholders.** Every visible setting must be functional.
8. **Do not modify Antigravity, ChatGPT, or other selected applications internally.** Use external Windows overlay functionality.
9. **Do not introduce unnecessary API dependencies or cloud services.**
10. **Complete and test each phase before proceeding to the next.**

### Final Vision

**Spider-Buddy should feel like a tiny, living Spider-Man inside your PC.**

You can choose **Miles Morales or Tom Holland's Spider-Man**, select whether he lives inside specific applications or across the entire desktop, and watch him naturally walk, climb, swing, sleep, and interact with you while you work.

The key to achieving the quality you want is to **build and verify the character animation assets before developing advanced movement mechanics**. That avoids repeating the problems you experienced with Desk Pet 3D.
