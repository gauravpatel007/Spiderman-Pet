/**
 * SpiderBuddy Web Bridge
 * Connects the Framer HTML/CSS/JS UI to the Spider-Buddy Python backend.
 * Provides live bi-directional updates, interactive triggers, and tab switching (Home, Characters, etc.).
 */
(function () {
    console.log("[SpiderBuddy Bridge] Initializing Web Bridge with Characters tab...");

    const state = {
        currentTab: "Home",
        isRunning: true,
        isHidden: false,
        activity: "IDLE",
        activeCharacterId: "tom_holland",
        characterName: "Tom Holland Spider-Man",
        quote: "“With great power comes great… need to commit to Git.”",
        batteryPercent: 100,
        isCharging: false,
        suitLore: "Stark Suit",
        suitStatus: "Systems Operational",
        cpu: 0,
        ram: 0,
        distance: "0 px",
        webs: 0,
        uptime: "0m",
        companionSize: 200,
        companionOpacity: 100,
        lastFrameB64: null,
        audioMeter: 0,
        musicStatus: "idle",
        musicVolume: 1.0,
        characters: [],
        activities: [],
        selectedCategory: "All",
        searchQuery: "",
        timing: {
            special_cooldown: 20,
            idle_timeout: 15,
            sleep_after: 5,
            automatic: true,
            locked_activity: "dance"
        },
        displaySettings: {
            display_mode: "desktop",
            monitor: "primary",
            default_position: "bottom_right",
            title_bar_offset: 28,
            window_perching: true,
            title_hang: true,
            target_applications: []
        },
        runningApps: [],
        appSearchQuery: "",
        focusSettings: {
            focus_mode: false,
            focus_timer_active: false,
            focus_time_remaining: 0,
            continuous_work_seconds: 0,
            enable_eye_break_alert: true,
            eye_break_minutes: 10,
            inactivity_relax_minutes: 2,
            inactivity_sit_minutes: 5,
            inactivity_sleep_minutes: 10
        },
        controlSettings: {
            enable_animation_hotkeys: true,
            hotkeys_require_modifier: false,
            wasd_movement_enabled: true,
            wasd_static_pin: true,
            enable_mouse_following: true,
            enable_spider_sense_dodging: true,
            cursor_radius: 180,
            click_through: false,
            sound_enabled: false,
            sound_volume: 25,
            movement_speed: 3.0,
            preset: "normal",
            enable_comic_bubbles: true,
            enable_sticky_notes: true,
            enable_fling_physics: true,
            enable_web_shoot_cursor: true,
            hotkeys: []
        },
        appSettings: {
            theme: "dark",
            display_fps: 0,
            animation_speed: 1.0,
            start_minimized: true,
            run_on_startup: false,
            always_on_top: false,
            click_through: false,
            automatic_animations: true,
            enable_animation_hotkeys: true,
            enable_eye_break_alert: true,
            enable_spider_sense_dodging: true,
            enable_sticky_notes: true,
            enable_fling_physics: true,
            enable_web_shoot_cursor: true,
            config_path: "",
            version: "v2.5.0"
        }
    };

    let appSettingsRevision = 0;
    let appSettingsRequest = 0;
    function sendAction(action, payload = {}) {
        appSettingsRevision++;
        const body = { action, ...payload };
        console.log("[SpiderBuddy Bridge] Action dispatched:", body);

        // 1. If Qt WebChannel is available
        if (window.qtBridge && typeof window.qtBridge.handleAction === "function") {
            window.qtBridge.handleAction(JSON.stringify(body));
            return Promise.resolve({ status: "ok" });
        }

        // 2. HTTP REST endpoint on local server
        return fetch("/api/action", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        }).then(res => res.json()).catch(err => {
            console.warn("[SpiderBuddy Bridge] Action fetch error:", err);
            return { error: String(err) };
        });
    }

    // ── Setup Hero Circle with Live Animated Sprite ───────────────────────
    function setupCharacterHeroArea() {
        const area = document.querySelector('[data-framer-name="Character illustration area"]');
        if (!area) return;

        area.style.position = "relative";
        area.style.overflow = "hidden";
        area.style.cursor = "pointer";
        area.setAttribute("title", "Click to interact with your companion!");

        let container = document.getElementById("companion-avatar-container");
        if (!container) {
            area.innerHTML = `
                <div id="companion-avatar-container" style="position: relative; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; pointer-events: none;">
                    <img id="companion-live-frame" src="/api/character_preview" alt="Spider-Buddy" 
                         style="max-width: 175px; max-height: 165px; object-fit: contain; filter: drop-shadow(0 0 16px rgba(243, 33, 85, 0.55)); transform: translateY(-4px); transition: filter 0.3s ease, transform 0.2s ease;" />
                    <div id="companion-activity-badge" style="position: absolute; bottom: 8px; font-size: 11px; font-weight: 700; color: #32dbc9; background: rgba(8, 14, 25, 0.88); padding: 3px 12px; border-radius: 14px; border: 1px solid rgba(50, 219, 201, 0.45); text-transform: uppercase; letter-spacing: 0.6px; box-shadow: 0 2px 8px rgba(0,0,0,0.4);">
                        ${state.activity}
                    </div>
                </div>
            `;
        }

        area.onclick = (e) => {
            e.preventDefault();
            sendAction("play_activity", { activity: "celebrate" });
            const img = document.getElementById("companion-live-frame");
            if (img) {
                img.style.transform = "translateY(-12px) scale(1.08)";
                setTimeout(() => { img.style.transform = "translateY(-4px)"; }, 280);
            }
        };
    }

    // ── Setup Tab Views & Switcher ────────────────────────────────────────
    function setupViews() {
        const contentArea = document.querySelector('[data-framer-name="Dashboard content"]');
        if (!contentArea) return;

        // Check if already wrapped
        if (document.getElementById("dashboard-home-view")) return;

        // Wrap existing Home children
        const homeWrapper = document.createElement("div");
        homeWrapper.id = "dashboard-home-view";
        homeWrapper.className = "dashboard-tab-view";
        homeWrapper.style.width = "100%";
        homeWrapper.style.flexDirection = "column";
        homeWrapper.style.gap = "28px";
        homeWrapper.style.setProperty("display", "flex", "important");

        while (contentArea.firstChild) {
            homeWrapper.appendChild(contentArea.firstChild);
        }
        contentArea.appendChild(homeWrapper);

        // Create Characters Tab Container
        const charactersWrapper = document.createElement("div");
        charactersWrapper.id = "dashboard-characters-view";
        charactersWrapper.className = "dashboard-tab-view tab-hidden";
        charactersWrapper.style.width = "100%";
        charactersWrapper.style.gap = "28px";
        charactersWrapper.style.setProperty("display", "none", "important");
        charactersWrapper.innerHTML = `
            <!-- Characters Header -->
            <div data-framer-name="Characters header" class="apple-header-block" style="display: flex; flex-direction: column; gap: 6px;">
                <div style="display: flex; gap: 10px; align-items: baseline;">
                    <h1 class="apple-title" style="font-size: 34px; font-weight: 700; color: #f4f5ff; margin: 0; line-height: 1.15; letter-spacing: -0.028em;">Choose your</h1>
                    <span class="apple-title-accent" style="font-size: 34px; font-weight: 700; color: #FF2D55; line-height: 1.15; letter-spacing: -0.028em;">companion.</span>
                </div>
                <p class="apple-subtext" style="font-size: 15px; color: rgba(220, 228, 245, 0.72); margin: 0; font-weight: 400; letter-spacing: -0.01em;">
                    One active companion at a time. Each with unique suits, physics, and personality.
                </p>
            </div>

            <!-- Character Cards Grid -->
            <div id="characters-gallery-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 20px; width: 100%;">
                <!-- Dynamic cards populated here -->
            </div>

            <!-- Appearance & Customization Card -->
            <div class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0 0 4px 0; letter-spacing: -0.015em;">Character Appearance &amp; Tuning</h3>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0;">
                            Live adjustments for your desktop companion's display size and transparency.
                        </p>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px;">
                    <!-- Size Slider -->
                    <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; gap: 12px; padding: 18px 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 14px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">Companion Size</span>
                            <span id="label-size-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #00F5D4; background: rgba(0, 245, 212, 0.12); border: 1px solid rgba(0, 245, 212, 0.3); padding: 2px 10px; border-radius: 9999px;">200 px</span>
                        </div>
                        <input id="slider-size" type="range" min="100" max="400" value="200" class="apple-slider"
                               style="width: 100%; accent-color: #FF2D55; cursor: pointer; height: 6px; border-radius: 9999px;" />
                        <div style="display: flex; gap: 8px; margin-top: 4px; flex-wrap: wrap;">
                            <button class="preset-btn apple-button apple-preset-pill" data-size="160">160px (Compact)</button>
                            <button class="preset-btn apple-button apple-preset-pill" data-size="200">200px (Default)</button>
                            <button class="preset-btn apple-button apple-preset-pill" data-size="260">260px (Large)</button>
                        </div>
                    </div>

                    <!-- Opacity Slider -->
                    <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; gap: 12px; padding: 18px 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 14px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">Window Transparency</span>
                            <span id="label-opacity-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #00F5D4; background: rgba(0, 245, 212, 0.12); border: 1px solid rgba(0, 245, 212, 0.3); padding: 2px 10px; border-radius: 9999px;">100%</span>
                        </div>
                        <input id="slider-opacity" type="range" min="40" max="100" value="100" class="apple-slider"
                               style="width: 100%; accent-color: #FF2D55; cursor: pointer; height: 6px; border-radius: 9999px;" />
                        <div style="display: flex; gap: 8px; margin-top: 4px; flex-wrap: wrap;">
                            <button class="preset-op-btn apple-button apple-preset-pill" data-op="70">70%</button>
                            <button class="preset-op-btn apple-button apple-preset-pill" data-op="85">85%</button>
                            <button class="preset-op-btn apple-button apple-preset-pill" data-op="100">100%</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        contentArea.appendChild(charactersWrapper);

        // Bind Sliders
        const sliderSize = document.getElementById("slider-size");
        const labelSize = document.getElementById("label-size-val");
        if (sliderSize && labelSize) {
            sliderSize.addEventListener("input", (e) => {
                const val = parseInt(e.target.value);
                labelSize.innerText = `${val} px`;
                sendAction("set_size", { size: val });
            });
            document.querySelectorAll(".preset-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const s = parseInt(btn.getAttribute("data-size"));
                    sliderSize.value = s;
                    labelSize.innerText = `${s} px`;
                    sendAction("set_size", { size: s });
                });
            });
        }

        const sliderOp = document.getElementById("slider-opacity");
        const labelOp = document.getElementById("label-opacity-val");
        if (sliderOp && labelOp) {
            sliderOp.addEventListener("input", (e) => {
                const val = parseInt(e.target.value);
                labelOp.innerText = `${val}%`;
                sendAction("set_opacity", { opacity: val });
            });
            document.querySelectorAll(".preset-op-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const op = parseInt(btn.getAttribute("data-op"));
                    sliderOp.value = op;
                    labelOp.innerText = `${op}%`;
                    sendAction("set_opacity", { opacity: op });
                });
            });
        }

        // Create Activities Tab Container
        const activitiesWrapper = document.createElement("div");
        activitiesWrapper.id = "dashboard-activities-view";
        activitiesWrapper.className = "dashboard-tab-view tab-hidden";
        activitiesWrapper.style.width = "100%";
        activitiesWrapper.style.flexDirection = "column";
        activitiesWrapper.style.gap = "26px";
        activitiesWrapper.style.setProperty("display", "none", "important");
        activitiesWrapper.innerHTML = `
            <!-- Activities Header -->
            <div data-framer-name="Activities header" class="apple-header-block" style="display: flex; flex-direction: column; gap: 6px;">
                <div style="display: flex; gap: 10px; align-items: baseline;">
                    <h1 class="apple-title" style="font-size: 34px; font-weight: 700; color: #f4f5ff; margin: 0; line-height: 1.15; letter-spacing: -0.028em;">Choose your</h1>
                    <span class="apple-title-accent" style="font-size: 34px; font-weight: 700; color: #FF2D55; line-height: 1.15; letter-spacing: -0.028em;">activities.</span>
                </div>
                <p class="apple-subtext" style="font-size: 15px; color: rgba(220, 228, 245, 0.72); margin: 0; font-weight: 400; letter-spacing: -0.01em;">
                    Enable, disable, or instantly trigger companion animations, window tricks, and desktop behaviors.
                </p>
            </div>

            <!-- Controls & Filters Card -->
            <div class="apple-glass-card" style="display: flex; flex-direction: column; gap: 16px; padding: 20px 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <div id="activity-category-pills" style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <!-- Category pills rendered dynamically -->
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button id="btn-bulk-enable" class="apple-button" style="background: rgba(48, 209, 88, 0.15); border: 1px solid rgba(48, 209, 88, 0.4); color: #30D158; padding: 7px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">✓ Enable All</button>
                        <button id="btn-bulk-disable" class="apple-button" style="background: rgba(255, 69, 58, 0.15); border: 1px solid rgba(255, 69, 58, 0.4); color: #FF453A; padding: 7px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">✕ Disable All</button>
                        <button id="btn-bulk-reset" class="apple-button" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: #e2e8f0; padding: 7px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">↺ Defaults</button>
                    </div>
                </div>

                <!-- Spotlight Search Input Row -->
                <div style="display: flex; align-items: center; position: relative; width: 100%;">
                    <span style="position: absolute; left: 16px; color: rgba(255, 255, 255, 0.45); font-size: 14px; pointer-events: none;">🔍</span>
                    <input id="activity-search-input" type="text" placeholder="Search activities by name or description..." 
                           class="apple-search-box"
                           style="width: 100%; box-sizing: border-box; background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 11px 16px 11px 42px; color: #f8fafc; font-size: 13.5px; outline: none; transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);" />
                </div>
            </div>

            <!-- Activities Cards Grid -->
            <div id="activities-gallery-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 18px; width: 100%;">
                <!-- Dynamic cards populated here -->
            </div>

            <!-- Autonomy & Timing Preferences Card -->
            <div class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0 0 4px 0; letter-spacing: -0.015em;">Autonomy &amp; Timing Preferences</h3>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0;">
                            Configure companion autonomy and idle decision schedules.
                        </p>
                    </div>
                </div>

                <!-- Autonomy Mode Toggle -->
                <div class="apple-glass-card-sub" style="display: flex; align-items: center; justify-content: space-between; padding: 18px 20px;">
                    <div>
                        <span style="font-size: 14px; font-weight: 600; color: #f8fafc; letter-spacing: -0.01em;">AI Autonomous Brain</span>
                        <p class="apple-subtext" style="font-size: 12.5px; color: rgba(220, 228, 245, 0.65); margin: 3px 0 0 0;">
                            Allows the companion to freely explore windows, climb, and perform spontaneous tricks.
                        </p>
                    </div>
                    <label class="spider-switch">
                        <input id="toggle-automatic-mode" type="checkbox" checked>
                        <span class="spider-slider"></span>
                    </label>
                </div>

                <!-- 3 Sliders Grid -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 18px;">
                    <!-- Special Cooldown -->
                    <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; gap: 10px; padding: 16px 18px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px; font-weight: 500; color: #f1f5f9;">Special Trick Cooldown</span>
                            <span id="label-cooldown-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #00F5D4; background: rgba(0, 245, 212, 0.12); border: 1px solid rgba(0, 245, 212, 0.3); padding: 2px 10px; border-radius: 9999px;">20 s</span>
                        </div>
                        <input id="slider-cooldown" type="range" min="1" max="120" value="20" class="apple-slider"
                               style="width: 100%; accent-color: #FF2D55; cursor: pointer; height: 6px; border-radius: 9999px;" />
                        <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Seconds between special tricks</span>
                    </div>

                    <!-- Idle Timeout -->
                    <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; gap: 10px; padding: 16px 18px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px; font-weight: 500; color: #f1f5f9;">Idle Switch Timeout</span>
                            <span id="label-idle-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #00F5D4; background: rgba(0, 245, 212, 0.12); border: 1px solid rgba(0, 245, 212, 0.3); padding: 2px 10px; border-radius: 9999px;">15 s</span>
                        </div>
                        <input id="slider-idle" type="range" min="1" max="120" value="15" class="apple-slider"
                               style="width: 100%; accent-color: #FF2D55; cursor: pointer; height: 6px; border-radius: 9999px;" />
                        <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Seconds before switching activities</span>
                    </div>

                    <!-- Sleep After -->
                    <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; gap: 10px; padding: 16px 18px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px; font-weight: 500; color: #f1f5f9;">Sleep Inactivity Timer</span>
                            <span id="label-sleep-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #00F5D4; background: rgba(0, 245, 212, 0.12); border: 1px solid rgba(0, 245, 212, 0.3); padding: 2px 10px; border-radius: 9999px;">5 m</span>
                        </div>
                        <input id="slider-sleep" type="range" min="1" max="60" value="5" class="apple-slider"
                               style="width: 100%; accent-color: #FF2D55; cursor: pointer; height: 6px; border-radius: 9999px;" />
                        <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Minutes of user inactivity before sleep</span>
                    </div>
                </div>
            </div>
        `;
        contentArea.appendChild(activitiesWrapper);

        // Bind Activities Controls
        const searchInput = document.getElementById("activity-search-input");
        if (searchInput) {
            searchInput.addEventListener("input", (e) => {
                state.searchQuery = e.target.value.toLowerCase().trim();
                renderActivities();
            });
        }
        const btnEnable = document.getElementById("btn-bulk-enable");
        if (btnEnable) {
            btnEnable.addEventListener("click", () => {
                sendAction("bulk_activities", { mode: "enable" });
                state.activities.forEach(a => { a.enabled = true; });
                renderActivities();
            });
        }
        const btnDisable = document.getElementById("btn-bulk-disable");
        if (btnDisable) {
            btnDisable.addEventListener("click", () => {
                sendAction("bulk_activities", { mode: "disable" });
                state.activities.forEach(a => { if (!a.is_transition) a.enabled = false; });
                renderActivities();
            });
        }
        const btnReset = document.getElementById("btn-bulk-reset");
        if (btnReset) {
            btnReset.addEventListener("click", () => {
                sendAction("bulk_activities", { mode: "reset" });
                loadActivities();
                loadTimingSettings();
            });
        }
        const sCooldown = document.getElementById("slider-cooldown");
        const lCooldown = document.getElementById("label-cooldown-val");
        if (sCooldown && lCooldown) {
            sCooldown.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                lCooldown.innerText = `${val} s`;
                sendAction("set_timing", { key: "special_cooldown", value: val });
            });
        }
        const sIdle = document.getElementById("slider-idle");
        const lIdle = document.getElementById("label-idle-val");
        if (sIdle && lIdle) {
            sIdle.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                lIdle.innerText = `${val} s`;
                sendAction("set_timing", { key: "idle_timeout", value: val });
            });
        }
        const sSleep = document.getElementById("slider-sleep");
        const lSleep = document.getElementById("label-sleep-val");
        if (sSleep && lSleep) {
            sSleep.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                lSleep.innerText = `${val} m`;
                sendAction("set_timing", { key: "sleep_after", value: val });
            });
        }
        const toggleAuto = document.getElementById("toggle-automatic-mode");
        if (toggleAuto) {
            toggleAuto.addEventListener("change", (e) => {
                const isAuto = e.target.checked;
                sendAction("set_playback_mode", { automatic: isAuto, locked_activity: state.timing.locked_activity });
            });
        }

        // Create Desktop & Apps Tab Container
        const desktopWrapper = document.createElement("div");
        desktopWrapper.id = "dashboard-desktop-view";
        desktopWrapper.className = "dashboard-tab-view tab-hidden";
        desktopWrapper.style.width = "100%";
        desktopWrapper.style.flexDirection = "column";
        desktopWrapper.style.gap = "26px";
        desktopWrapper.style.setProperty("display", "none", "important");
        desktopWrapper.innerHTML = `
            <!-- Desktop & Apps Header -->
            <div data-framer-name="Desktop header" class="apple-header-block" style="display: flex; flex-direction: column; gap: 6px;">
                <div style="display: flex; gap: 10px; align-items: baseline;">
                    <h1 class="apple-title" style="font-size: 34px; font-weight: 700; color: #f4f5ff; margin: 0; line-height: 1.15; letter-spacing: -0.028em;">Where your</h1>
                    <span class="apple-title-accent" style="font-size: 34px; font-weight: 700; color: #FF2D55; line-height: 1.15; letter-spacing: -0.028em;">companion lives.</span>
                </div>
                <p class="apple-subtext" style="font-size: 15px; color: rgba(220, 228, 245, 0.72); margin: 0; font-weight: 400; letter-spacing: -0.01em;">
                    Configure display mode boundaries, target applications, multi-monitor behavior, and window edge perching.
                </p>
            </div>

            <!-- Card 1: Display Mode & Habitat -->
            <div class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 22px;">
                <div>
                    <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0 0 4px 0; letter-spacing: -0.015em;">Display Mode &amp; Habitat</h3>
                    <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0;">
                        Choose whether Spider-Man explores the entire desktop or stays strictly confined to specific application windows.
                    </p>
                </div>

                <!-- 2 Mode Selector Cards -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
                    <!-- Entire Desktop Tile -->
                    <div id="mode-card-desktop" class="apple-glass-card-sub" style="border: 1.5px solid rgba(255, 45, 85, 0.85); background: rgba(255, 45, 85, 0.08); padding: 20px; cursor: pointer; transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1); display: flex; flex-direction: column; gap: 10px; box-shadow: 0 8px 24px -6px rgba(255, 45, 85, 0.25);">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 22px;">🖥️</span>
                                <h4 style="font-size: 15px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.01em;">Entire Desktop</h4>
                            </div>
                            <span id="badge-mode-desktop" class="apple-pill-badge" style="background: rgba(255, 45, 85, 0.2); color: #FF2D55; border: 1px solid rgba(255, 45, 85, 0.5); font-size: 10px; font-weight: 700; padding: 3px 10px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.04em;">ACTIVE</span>
                        </div>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; line-height: 1.45;">
                            The companion roams freely across taskbars, window perches, and edges of your monitors.
                        </p>
                    </div>

                    <!-- Selected Applications Tile -->
                    <div id="mode-card-application" class="apple-glass-card-sub" style="border: 1px solid rgba(255, 255, 255, 0.08); padding: 20px; cursor: pointer; transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1); display: flex; flex-direction: column; gap: 10px;">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 22px;">🎯</span>
                                <h4 style="font-size: 15px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.01em;">Selected Applications</h4>
                            </div>
                            <span id="badge-mode-app" class="apple-pill-badge" style="display: none; background: rgba(0, 245, 212, 0.2); color: #00F5D4; border: 1px solid rgba(0, 245, 212, 0.5); font-size: 10px; font-weight: 700; padding: 3px 10px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.04em;">ACTIVE</span>
                        </div>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; line-height: 1.45;">
                            The companion stays inside chosen foreground windows and automatically hides when apps minimize or lose focus.
                        </p>
                    </div>
                </div>

                <!-- Monitor & Placement Options Row -->
                <div class="apple-glass-card-sub" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; padding: 18px 20px;">
                    <!-- Desktop Monitor -->
                    <div id="monitor-section" style="display: flex; flex-direction: column; gap: 8px;">
                        <span style="font-size: 13px; font-weight: 600; color: #f1f5f9;">Desktop Monitor</span>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <button class="monitor-btn apple-button apple-preset-pill active" data-monitor="primary" style="background: rgba(255, 45, 85, 0.18); border-color: rgba(255, 45, 85, 0.5); color: #fff;">Primary Monitor</button>
                            <button class="monitor-btn apple-button apple-preset-pill" data-monitor="all">All Monitors (Span)</button>
                        </div>
                        <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Select which screen Spider-Man explores</span>
                    </div>

                    <!-- Default Screen Position -->
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <span style="font-size: 13px; font-weight: 600; color: #f1f5f9;">Default Screen Position</span>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <button class="position-btn apple-button apple-preset-pill" data-pos="bottom_left">Bottom Left</button>
                            <button class="position-btn apple-button apple-preset-pill active" data-pos="bottom_right" style="background: rgba(255, 45, 85, 0.18); border-color: rgba(255, 45, 85, 0.5); color: #fff;">Bottom Right</button>
                            <button class="position-btn apple-button apple-preset-pill" data-pos="custom">Custom</button>
                        </div>
                        <div style="margin-top: 4px;">
                            <button id="btn-save-current-pos" class="apple-button" style="background: rgba(0, 245, 212, 0.12); border: 1px solid rgba(0, 245, 212, 0.35); color: #00F5D4; padding: 6px 14px; border-radius: 9999px; font-size: 11.5px; font-weight: 600; cursor: pointer;">📍 Use Current Position as Custom</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Card 2: Target Applications -->
            <div id="target-apps-card" class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 18px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Target Applications</h3>
                            <span id="target-apps-count-badge" class="apple-pill-badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 9999px;">0 selected</span>
                        </div>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 4px 0 0 0;">
                            In Selected Applications mode, Spider-Man will only appear when these apps are active.
                        </p>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button id="btn-refresh-apps" class="apple-button" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.14); color: #f1f5f9; padding: 7px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">🔄 Scan Running Apps</button>
                        <button id="btn-browse-app" class="apple-button" style="background: rgba(255, 45, 85, 0.15); border: 1px solid rgba(255, 45, 85, 0.4); color: #FF2D55; padding: 7px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">📁 Browse .exe...</button>
                    </div>
                </div>

                <!-- Add Custom App Input Row -->
                <div style="display: flex; gap: 10px; width: 100%;">
                    <input id="input-add-app" type="text" placeholder="Add executable by name, e.g. Code.exe, chrome.exe..." 
                           class="apple-search-box"
                           style="flex: 1; background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 10px 16px; color: #f8fafc; font-size: 13px; outline: none;" />
                    <button id="btn-add-app" class="apple-button apple-button-primary" style="background: #FF2D55; border: none; color: #fff; padding: 10px 20px; border-radius: 12px; font-size: 13px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 14px rgba(255, 45, 85, 0.35);">+ Add App</button>
                </div>

                <!-- Search Apps Input Row -->
                <div style="display: flex; align-items: center; position: relative; width: 100%;">
                    <span style="position: absolute; left: 16px; color: rgba(255, 255, 255, 0.45); font-size: 14px; pointer-events: none;">🔍</span>
                    <input id="app-search-input" type="text" placeholder="Filter applications list..." 
                           class="apple-search-box"
                           style="width: 100%; box-sizing: border-box; background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 10px 16px 10px 42px; color: #f8fafc; font-size: 13px; outline: none;" />
                </div>

                <!-- Application List Container -->
                <div id="target-apps-list" style="display: flex; flex-direction: column; gap: 8px; max-height: 280px; overflow-y: auto; padding-right: 4px;">
                    <!-- Dynamically populated rows -->
                </div>
            </div>

            <!-- Card 3: Window Alignment & Perching -->
            <div class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
                <div>
                    <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0 0 4px 0; letter-spacing: -0.015em;">Window Alignment &amp; Perching Tricks</h3>
                    <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0;">
                        Fine-tune how your companion interacts with application windows and browser title bars.
                    </p>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
                    <!-- Perch Switch -->
                    <div class="apple-glass-card-sub" style="display: flex; align-items: center; justify-content: space-between; padding: 16px 20px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc; letter-spacing: -0.01em;">Window Edge Perching</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">
                                Companion rests on window borders and follows movements.
                            </p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-window-perch" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Title Hang Switch -->
                    <div class="apple-glass-card-sub" style="display: flex; align-items: center; justify-content: space-between; padding: 16px 20px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc; letter-spacing: -0.01em;">Title Bar Hanging</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">
                                Hang upside down from active browser or window title bars.
                            </p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-title-hang" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>
                </div>

                <!-- Vertical Offset Slider -->
                <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; gap: 10px; padding: 18px 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 14px; font-weight: 500; color: #f1f5f9;">Vertical Alignment Offset with Tabs / Title Bar</span>
                        <span id="label-title-offset-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #00F5D4; background: rgba(0, 245, 212, 0.12); border: 1px solid rgba(0, 245, 212, 0.3); padding: 2px 10px; border-radius: 9999px;">28 px</span>
                    </div>
                    <input id="slider-title-offset" type="range" min="0" max="80" value="28" class="apple-slider"
                           style="width: 100%; accent-color: #FF2D55; cursor: pointer; height: 6px; border-radius: 9999px;" />
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: rgba(220, 228, 245, 0.5);">
                        <span>0 px (Flush with top border)</span>
                        <span>Adjust to sit perfectly along tabs or headers</span>
                        <span>80 px (Deep offset)</span>
                    </div>
                </div>
            </div>
        `;
        contentArea.appendChild(desktopWrapper);

        // Bind Desktop & Apps Controls
        const cardDesk = document.getElementById("mode-card-desktop");
        const cardApp = document.getElementById("mode-card-application");
        if (cardDesk && cardApp) {
            cardDesk.addEventListener("click", () => {
                state.displaySettings.display_mode = "desktop";
                updateDisplaySettingsUI();
                sendAction("set_display_mode", { mode: "desktop" });
            });
            cardApp.addEventListener("click", () => {
                state.displaySettings.display_mode = "application";
                updateDisplaySettingsUI();
                sendAction("set_display_mode", { mode: "application" });
            });
        }

        document.querySelectorAll(".monitor-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const mon = btn.getAttribute("data-monitor");
                state.displaySettings.monitor = mon;
                updateDisplaySettingsUI();
                sendAction("set_monitor", { monitor: mon });
            });
        });

        document.querySelectorAll(".position-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const pos = btn.getAttribute("data-pos");
                state.displaySettings.default_position = pos;
                updateDisplaySettingsUI();
                sendAction("set_default_position", { position: pos });
            });
        });

        const btnSavePos = document.getElementById("btn-save-current-pos");
        if (btnSavePos) {
            btnSavePos.addEventListener("click", () => {
                sendAction("save_current_position");
                btnSavePos.innerText = "✓ Position Saved!";
                setTimeout(() => { btnSavePos.innerText = "📍 Use Current Position as Custom"; }, 1500);
            });
        }

        const tPerch = document.getElementById("toggle-window-perch");
        if (tPerch) {
            tPerch.addEventListener("change", (e) => {
                state.displaySettings.window_perching = e.target.checked;
                sendAction("toggle_window_perch", { enabled: e.target.checked });
            });
        }

        const tHang = document.getElementById("toggle-title-hang");
        if (tHang) {
            tHang.addEventListener("change", (e) => {
                state.displaySettings.title_hang = e.target.checked;
                sendAction("toggle_title_hang", { enabled: e.target.checked });
            });
        }

        const sOffset = document.getElementById("slider-title-offset");
        const lOffset = document.getElementById("label-title-offset-val");
        if (sOffset && lOffset) {
            sOffset.addEventListener("input", (e) => {
                const val = parseInt(e.target.value);
                lOffset.innerText = `${val} px`;
                state.displaySettings.title_bar_offset = val;
                sendAction("set_title_offset", { offset: val });
            });
        }

        const btnAddApp = document.getElementById("btn-add-app");
        const inputAddApp = document.getElementById("input-add-app");
        if (btnAddApp && inputAddApp) {
            const doAdd = () => {
                const val = inputAddApp.value.trim();
                if (!val) {
                    inputAddApp.focus();
                    inputAddApp.style.borderColor = "#FF2D55";
                    inputAddApp.style.boxShadow = "0 0 14px rgba(255, 45, 85, 0.45)";
                    const origPh = inputAddApp.placeholder;
                    inputAddApp.placeholder = "⚠️ Type executable name or pick an .exe file...";
                    setTimeout(() => {
                        inputAddApp.style.borderColor = "rgba(255, 255, 255, 0.1)";
                        inputAddApp.style.boxShadow = "none";
                        inputAddApp.placeholder = origPh;
                    }, 2500);
                    sendAction("browse_application");
                    return;
                }

                const origText = btnAddApp.innerText;
                btnAddApp.innerText = "Adding...";
                btnAddApp.style.opacity = "0.75";

                sendAction("add_target_application", { application: val }).then(() => {
                    inputAddApp.value = "";
                    btnAddApp.innerText = "✓ Added!";
                    btnAddApp.style.background = "#30D158";
                    btnAddApp.style.opacity = "1";
                    setTimeout(() => {
                        btnAddApp.innerText = origText;
                        btnAddApp.style.background = "#FF2D55";
                    }, 1800);
                    loadDisplaySettings();
                }).catch(() => {
                    btnAddApp.innerText = origText;
                    btnAddApp.style.opacity = "1";
                });
            };
            btnAddApp.addEventListener("click", doAdd);
            inputAddApp.addEventListener("keydown", (e) => {
                if (e.key === "Enter") doAdd();
            });
        }

        const appSearch = document.getElementById("app-search-input");
        if (appSearch) {
            appSearch.addEventListener("input", (e) => {
                state.appSearchQuery = e.target.value;
                renderTargetApplications();
            });
        }

        const btnRefreshApps = document.getElementById("btn-refresh-apps");
        if (btnRefreshApps) {
            btnRefreshApps.addEventListener("click", () => {
                const origText = btnRefreshApps.innerText;
                btnRefreshApps.innerText = "⏳ Scanning...";
                btnRefreshApps.style.opacity = "0.75";
                fetch("/api/running_applications")
                    .then(res => res.json())
                    .then(apps => {
                        state.runningApps = apps;
                        renderTargetApplications();
                        btnRefreshApps.innerText = `✅ Found ${apps.length} Apps`;
                        btnRefreshApps.style.opacity = "1";
                        setTimeout(() => {
                            btnRefreshApps.innerText = origText;
                        }, 2500);
                    })
                    .catch(err => {
                        console.warn("[SpiderBuddy Bridge] Failed to load running apps:", err);
                        btnRefreshApps.innerText = "❌ Scan Failed";
                        setTimeout(() => {
                            btnRefreshApps.innerText = origText;
                            btnRefreshApps.style.opacity = "1";
                        }, 2000);
                    });
            });
        }

        const btnBrowseApp = document.getElementById("btn-browse-app");
        if (btnBrowseApp) {
            btnBrowseApp.addEventListener("click", () => {
                const origText = btnBrowseApp.innerText;
                btnBrowseApp.innerText = "📂 Opening...";
                sendAction("browse_application");
                setTimeout(() => {
                    btnBrowseApp.innerText = origText;
                }, 1500);
            });
        }

        // Create Focus & Breaks Tab Container
        const focusWrapper = document.createElement("div");
        focusWrapper.id = "dashboard-focus-view";
        focusWrapper.className = "dashboard-tab-view tab-hidden";
        focusWrapper.style.width = "100%";
        focusWrapper.style.flexDirection = "column";
        focusWrapper.style.gap = "26px";
        focusWrapper.style.setProperty("display", "none", "important");
        focusWrapper.innerHTML = `
            <!-- Focus & Breaks Header -->
            <div data-framer-name="Focus header" class="apple-header-block" style="display: flex; flex-direction: column; gap: 6px;">
                <div style="display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap;">
                    <h1 class="apple-title" style="font-size: 34px; font-weight: 700; color: #f4f5ff; margin: 0; line-height: 1.15; letter-spacing: -0.028em;">Focus, recharge,</h1>
                    <span class="apple-title-accent" style="font-size: 34px; font-weight: 700; color: #FF2D55; line-height: 1.15; letter-spacing: -0.028em;">rest.</span>
                </div>
                <p class="apple-subtext" style="font-size: 15px; color: rgba(220, 228, 245, 0.72); margin: 0; font-weight: 400; letter-spacing: -0.01em;">
                    Configure quiet guardian focus mode, continuous typing eye-break web alerts, and companion resting thresholds.
                </p>
            </div>

            <!-- Card 1: Spider-Focus Pomodoro & Quiet Companion -->
            <div id="pomodoro-focus-card" class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
                <!-- Header with Focus Mode switch -->
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 18px;">
                    <div style="display: flex; flex-direction: column; gap: 4px; max-width: 75%;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 20px;">🎯</span>
                            <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Quiet Focus Mode (Study &amp; Work)</h3>
                        </div>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; line-height: 1.45;">
                            Spider-Man puts on reading glasses and sits quietly in the corner reading a comic book (<span style="color:#00D2FF; font-weight: 600;">focus_read</span>) so you can work uninterrupted.
                        </p>
                    </div>
                    <label class="spider-switch">
                        <input type="checkbox" id="toggle-focus-mode" />
                        <span class="spider-slider"></span>
                    </label>
                </div>

                <!-- Pomodoro Timer Clock Row -->
                <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 28px 20px; gap: 14px; position: relative;">
                    <div id="focus-timer-clock" style="font-variant-numeric: tabular-nums; font-size: 58px; font-weight: 700; color: #00D2FF; letter-spacing: 1px; text-shadow: 0 0 28px rgba(0, 210, 255, 0.4);">
                        25:00
                    </div>
                    <div id="focus-timer-badge" class="apple-pill-badge" style="background: rgba(0, 210, 255, 0.12); border: 1px solid rgba(0, 210, 255, 0.35); color: #00D2FF; padding: 5px 16px; border-radius: 9999px; font-size: 12px; font-weight: 600; letter-spacing: 0.3px;">
                        🛡️ Guardian Mode: Ready
                    </div>

                    <!-- Preset Buttons -->
                    <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; margin-top: 8px;">
                        <button class="focus-preset-btn apple-button apple-preset-pill active" data-min="25" style="background: rgba(255, 45, 85, 0.18); border-color: rgba(255, 45, 85, 0.5); color: #fff;">🎯 25m Focus</button>
                        <button class="focus-preset-btn apple-button apple-preset-pill" data-min="45">🧠 45m Deep Work</button>
                        <button class="focus-preset-btn apple-button apple-preset-pill" data-min="60">📚 60m Marathon</button>
                        <button class="focus-preset-btn apple-button apple-preset-pill" data-min="5" style="color: #00F5D4; border-color: rgba(0, 245, 212, 0.3);">☕ 5m Quick Break</button>
                        <button id="btn-cancel-focus-timer" class="apple-button" style="background: rgba(255, 69, 58, 0.12); border: 1px solid rgba(255, 69, 58, 0.4); color: #FF453A; padding: 8px 16px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">✕ Cancel Timer</button>
                    </div>

                    <!-- Direct Activity Preview Buttons -->
                    <div style="display: flex; gap: 12px; margin-top: 8px; flex-wrap: wrap;">
                        <button id="btn-play-focus-read" class="apple-button" style="background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12); color: rgba(220, 228, 245, 0.8); font-size: 12px; padding: 6px 14px; border-radius: 9999px; cursor: pointer;">📖 Preview Focus Comic Reading</button>
                        <button id="btn-play-sleep-nap" class="apple-button" style="background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12); color: rgba(220, 228, 245, 0.8); font-size: 12px; padding: 6px 14px; border-radius: 9999px; cursor: pointer;">🕸️ Nap in Web Hammock</button>
                    </div>
                </div>
            </div>

            <!-- Card 2: Continuous Typing & Eye-Break Web Alert -->
            <div id="eye-break-card" class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 18px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                    <div style="display: flex; flex-direction: column; gap: 4px; max-width: 75%;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 20px;">💧</span>
                            <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Continuous Work &amp; Eye-Break Web Alert</h3>
                        </div>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; line-height: 1.45;">
                            When you type continuously or when your focus timer finishes, Spider-Man webs the top corner and taps on the glass: <em>“Time for water, man! 💧”</em>
                        </p>
                    </div>
                    <label class="spider-switch">
                        <input type="checkbox" id="toggle-eye-break" checked />
                        <span class="spider-slider"></span>
                    </label>
                </div>

                <!-- Interval Slider -->
                <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; gap: 10px; padding: 18px 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 14px; font-weight: 500; color: #f1f5f9;">Continuous Work Alert Interval</span>
                        <span id="label-eye-interval-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #00F5D4; background: rgba(0, 245, 212, 0.12); border: 1px solid rgba(0, 245, 212, 0.3); padding: 2px 10px; border-radius: 9999px;">10 min</span>
                    </div>
                    <input id="slider-eye-interval" type="range" min="10" max="180" step="5" value="10" class="apple-slider"
                           style="width: 100%; accent-color: #FF2D55; cursor: pointer; height: 6px; border-radius: 9999px;" />
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: rgba(220, 228, 245, 0.5);">
                        <span>10 min (Frequent reminders)</span>
                        <span>Spider-Man monitors continuous keyboard &amp; mouse work</span>
                        <span>180 min (Maximum interval)</span>
                    </div>
                </div>

                <!-- Live Work Tracker & Action -->
                <div class="apple-glass-card-sub" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; flex-wrap: wrap; gap: 14px;">
                    <div style="display: flex; flex-direction: column; gap: 8px; flex: 1; min-width: 240px;">
                        <div id="eye-break-status-text" style="font-size: 13px; font-weight: 600; color: #00D2FF; letter-spacing: -0.01em;">
                            💧 Continuous Work: 0m 0s / 10m • Focus Timer: Inactive
                        </div>
                        <div style="width: 100%; height: 6px; background: rgba(0, 0, 0, 0.45); border-radius: 9999px; overflow: hidden;">
                            <div id="eye-break-progress-bar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #00F5D4, #00D2FF); transition: width 0.3s ease;"></div>
                        </div>
                    </div>
                    <button id="btn-test-eye-break" class="apple-button" style="background: rgba(255, 45, 85, 0.15); border: 1px solid rgba(255, 45, 85, 0.4); color: #FF2D55; padding: 9px 18px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">
                        ⚡ Preview Eye-Break Alert
                    </button>
                </div>
            </div>

            <!-- Card 3: Inactivity & Resting Thresholds -->
            <div id="inactivity-card" class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 18px;">
                <div style="display: flex; flex-direction: column; gap: 4px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 20px;">🌙</span>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">When You Step Away (Inactivity Stages)</h3>
                    </div>
                    <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; line-height: 1.45;">
                        When you leave your computer, Spider-Man progressively settles down to conserve your system resources and let you rest.
                    </p>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px;">
                    <!-- Stage 1: Relax -->
                    <div class="apple-glass-card-sub" style="padding: 18px 20px; display: flex; flex-direction: column; gap: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px; font-weight: 600; color: #f1f5f9;">1. Relax After</span>
                            <span id="label-inactivity-relax-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #00F5D4; background: rgba(0, 245, 212, 0.12); border: 1px solid rgba(0, 245, 212, 0.3); padding: 2px 10px; border-radius: 9999px;">2 min</span>
                        </div>
                        <input id="slider-inactivity-relax" type="range" min="1" max="30" value="2" class="apple-slider"
                               style="width: 100%; accent-color: #00F5D4; cursor: pointer; height: 6px; border-radius: 9999px;" />
                        <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Companion stops jumping and stretches leisurely</span>
                    </div>

                    <!-- Stage 2: Sit -->
                    <div class="apple-glass-card-sub" style="padding: 18px 20px; display: flex; flex-direction: column; gap: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px; font-weight: 600; color: #f1f5f9;">2. Sit After</span>
                            <span id="label-inactivity-sit-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #00D2FF; background: rgba(0, 210, 255, 0.12); border: 1px solid rgba(0, 210, 255, 0.3); padding: 2px 10px; border-radius: 9999px;">5 min</span>
                        </div>
                        <input id="slider-inactivity-sit" type="range" min="1" max="60" value="5" class="apple-slider"
                               style="width: 100%; accent-color: #00D2FF; cursor: pointer; height: 6px; border-radius: 9999px;" />
                        <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Companion sits down on window ledge or taskbar</span>
                    </div>

                    <!-- Stage 3: Sleep -->
                    <div class="apple-glass-card-sub" style="padding: 18px 20px; display: flex; flex-direction: column; gap: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px; font-weight: 600; color: #f1f5f9;">3. Sleep After</span>
                            <span id="label-inactivity-sleep-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #BF5AF2; background: rgba(191, 90, 242, 0.12); border: 1px solid rgba(191, 90, 242, 0.3); padding: 2px 10px; border-radius: 9999px;">10 min</span>
                        </div>
                        <input id="slider-inactivity-sleep" type="range" min="1" max="120" value="10" class="apple-slider"
                               style="width: 100%; accent-color: #BF5AF2; cursor: pointer; height: 6px; border-radius: 9999px;" />
                        <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Spins a web hammock and enters zero-CPU deep sleep</span>
                    </div>
                </div>

                <div class="apple-glass-card-sub" style="display: flex; align-items: center; gap: 10px; font-size: 12px; color: rgba(220, 228, 245, 0.75); padding: 12px 16px;">
                    <span style="font-size: 14px;">💡</span>
                    <span>Thresholds run in sequence: <strong>Relaxing &rarr; Sitting &rarr; Sleeping</strong>. Later stages cannot begin before earlier stages complete.</span>
                </div>
            </div>
        `;
        contentArea.appendChild(focusWrapper);

        // Bind Focus & Breaks Controls
        const tFocusMode = document.getElementById("toggle-focus-mode");
        if (tFocusMode) {
            tFocusMode.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.focusSettings.focus_mode = en;
                sendAction("toggle_focus_mode", { enabled: en });
            });
        }

        document.querySelectorAll(".focus-preset-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const mins = parseFloat(btn.getAttribute("data-min"));
                sendAction("start_focus_timer", { minutes: mins });
            });
        });

        const btnCancelFocus = document.getElementById("btn-cancel-focus-timer");
        if (btnCancelFocus) {
            btnCancelFocus.addEventListener("click", () => {
                sendAction("stop_focus_timer");
            });
        }

        const btnPlayFocusRead = document.getElementById("btn-play-focus-read");
        if (btnPlayFocusRead) {
            btnPlayFocusRead.addEventListener("click", () => {
                sendAction("play_activity", { activity: "focus_read" });
            });
        }

        const btnPlaySleep = document.getElementById("btn-play-sleep-nap");
        if (btnPlaySleep) {
            btnPlaySleep.addEventListener("click", () => {
                sendAction("play_activity", { activity: "sleep" });
            });
        }

        const tEyeBreak = document.getElementById("toggle-eye-break");
        if (tEyeBreak) {
            tEyeBreak.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.focusSettings.enable_eye_break_alert = en;
                sendAction("toggle_eye_break", { enabled: en });
            });
        }

        const sEyeInterval = document.getElementById("slider-eye-interval");
        const lEyeInterval = document.getElementById("label-eye-interval-val");
        if (sEyeInterval && lEyeInterval) {
            sEyeInterval.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                lEyeInterval.innerText = `${val} min`;
                sendAction("set_eye_break_interval", { minutes: val });
            });
        }

        const btnTestEye = document.getElementById("btn-test-eye-break");
        if (btnTestEye) {
            btnTestEye.addEventListener("click", () => {
                sendAction("test_eye_break");
            });
        }

        const sInactRelax = document.getElementById("slider-inactivity-relax");
        const lInactRelax = document.getElementById("label-inactivity-relax-val");
        if (sInactRelax && lInactRelax) {
            sInactRelax.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                lInactRelax.innerText = `${val} min`;
                sendAction("set_inactivity_threshold", { stage: "relax", minutes: val });
            });
        }

        const sInactSit = document.getElementById("slider-inactivity-sit");
        const lInactSit = document.getElementById("label-inactivity-sit-val");
        if (sInactSit && lInactSit) {
            sInactSit.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                lInactSit.innerText = `${val} min`;
                sendAction("set_inactivity_threshold", { stage: "sit", minutes: val });
            });
        }

        const sInactSleep = document.getElementById("slider-inactivity-sleep");
        const lInactSleep = document.getElementById("label-inactivity-sleep-val");
        if (sInactSleep && lInactSleep) {
            sInactSleep.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                lInactSleep.innerText = `${val} min`;
                sendAction("set_inactivity_threshold", { stage: "sleep", minutes: val });
            });
        }

        // Create Controls Tab Container
        const controlsWrapper = document.createElement("div");
        controlsWrapper.id = "dashboard-controls-view";
        controlsWrapper.className = "dashboard-tab-view tab-hidden";
        controlsWrapper.style.width = "100%";
        controlsWrapper.style.flexDirection = "column";
        controlsWrapper.style.gap = "26px";
        controlsWrapper.style.setProperty("display", "none", "important");
        controlsWrapper.innerHTML = `
            <!-- Controls Header -->
            <div data-framer-name="Controls header" class="apple-header-block" style="display: flex; flex-direction: column; gap: 6px;">
                <div style="display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap;">
                    <h1 class="apple-title" style="font-size: 34px; font-weight: 700; color: #f4f5ff; margin: 0; line-height: 1.15; letter-spacing: -0.028em;">Controls, shortcuts &amp;</h1>
                    <span class="apple-title-accent" style="font-size: 34px; font-weight: 700; color: #FF2D55; line-height: 1.15; letter-spacing: -0.028em;">locomotion.</span>
                </div>
                <p class="apple-subtext" style="font-size: 15px; color: rgba(220, 228, 245, 0.72); margin: 0; font-weight: 400; letter-spacing: -0.01em;">
                    Configure global number-key animation shortcuts, WASD manual locomotion, mouse tracking, and reaction physics.
                </p>
            </div>

            <!-- Card 1: Global Number-Key Shortcuts (Keys 1–0 & Numpad) -->
            <div id="card-hotkeys" class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
                <!-- Header with Master Hotkeys Switch -->
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 18px;">
                    <div style="display: flex; flex-direction: column; gap: 4px; max-width: 75%;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 20px;">⌨️</span>
                            <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Global Number-Key Shortcuts</h3>
                        </div>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; line-height: 1.45;">
                            Press number keys <strong>1, 2, 3... 0</strong> (top row or numpad) from anywhere in Windows to trigger animations instantly.
                        </p>
                    </div>
                    <label class="spider-switch">
                        <input type="checkbox" id="toggle-master-hotkeys" checked />
                        <span class="spider-slider"></span>
                    </label>
                </div>

                <!-- Sub-row: Modifier requirement and Enable/Disable All -->
                <div class="apple-glass-card-sub" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; padding: 14px 18px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <label class="spider-switch">
                            <input type="checkbox" id="toggle-hotkeys-modifier" />
                            <span class="spider-slider"></span>
                        </label>
                        <div style="display: flex; flex-direction: column; gap: 2px;">
                            <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">Require Modifier Key (Win / Alt / Ctrl)</span>
                            <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Prevents accidental triggers while typing in text editors or browsers</span>
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button id="btn-enable-all-hotkeys" class="apple-button" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.14); color: #f1f5f9; padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">Enable All</button>
                        <button id="btn-disable-all-hotkeys" class="apple-button" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.14); color: #f1f5f9; padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">Disable All</button>
                    </div>
                </div>

                <!-- Dynamic Grid for 10 Number Keys -->
                <div id="hotkeys-grid-container" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 12px;">
                    <!-- Rendered dynamically by renderHotkeysGrid() -->
                </div>
            </div>

            <!-- Card 2: Manual Locomotion (WASD) & Static Pinning -->
            <div id="card-locomotion" class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 18px;">
                    <div style="display: flex; flex-direction: column; gap: 4px; max-width: 75%;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 20px;">🎮</span>
                            <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Manual Keyboard Locomotion (WASD)</h3>
                        </div>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; line-height: 1.45;">
                            Control Spider-Man in real time with keyboard keys. Press <strong>W, A, S, D</strong> or Arrow keys; hold <strong>Shift</strong> to sprint.
                        </p>
                    </div>
                    <label class="spider-switch">
                        <input type="checkbox" id="toggle-wasd-enabled" checked />
                        <span class="spider-slider"></span>
                    </label>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px;">
                    <!-- Static Pinning Switch -->
                    <div class="apple-glass-card-sub" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 18px;">
                        <div style="display: flex; flex-direction: column; gap: 3px; max-width: 78%;">
                            <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">Keep Static Where Stopped</span>
                            <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Companion stays perched where keys are released. Press <strong>Spacebar</strong> to drop to ground.</span>
                        </div>
                        <label class="spider-switch">
                            <input type="checkbox" id="toggle-wasd-pin" checked />
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Movement Speed Slider -->
                    <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; gap: 8px; padding: 16px 18px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9;">Movement Speed</span>
                            <span id="label-movement-speed-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #FF2D55; background: rgba(255, 45, 85, 0.12); border: 1px solid rgba(255, 45, 85, 0.3); padding: 2px 10px; border-radius: 9999px;">3.0x</span>
                        </div>
                        <input type="range" id="slider-movement-speed" min="1" max="6" step="0.5" value="3.0" class="apple-slider" style="flex: 1; accent-color: #FF2D55; cursor: pointer; height: 6px; border-radius: 9999px;" />
                        <div style="display: flex; justify-content: space-between; font-size: 11px; color: rgba(220, 228, 245, 0.5);">
                            <span>1.0x (Relaxed stroll)</span>
                            <span>6.0x (Maximum overdrive)</span>
                        </div>
                    </div>
                </div>

                <!-- Interactive Manual Testing D-Pad -->
                <div class="apple-glass-card-sub" style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px; padding: 18px 20px;">
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <span style="font-size: 14px; font-weight: 600; color: #f8fafc; letter-spacing: -0.01em;">🎮 Quick Locomotion Pad</span>
                        <span style="font-size: 12px; color: rgba(220, 228, 245, 0.65);">Click directional pads to test character locomotion signals immediately.</span>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                        <button class="dpad-btn apple-button" data-act="jump" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.14); color: #fff; padding: 8px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">⬆️ W / Up (Leap)</button>
                        <button class="dpad-btn apple-button" data-act="walk" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.14); color: #fff; padding: 8px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">⬅️ A (Walk Left)</button>
                        <button class="dpad-btn apple-button" data-act="sit" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.14); color: #fff; padding: 8px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">⬇️ S (Crouch/Sit)</button>
                        <button class="dpad-btn apple-button" data-act="run" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.14); color: #fff; padding: 8px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">➡️ D (Sprint Right)</button>
                        <button class="dpad-btn apple-button" data-act="idle" style="background: rgba(255, 45, 85, 0.18); border: 1px solid rgba(255, 45, 85, 0.5); color: #fff; padding: 8px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; cursor: pointer;">⏹ Spacebar (Drop)</button>
                    </div>
                </div>
            </div>

            <!-- Card 3: Desktop Pet Live Interactions (Mouse & Physics) -->
            <div id="card-mouse-interaction" class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 18px;">
                    <div style="display: flex; flex-direction: column; gap: 4px; max-width: 85%;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 20px;">🚀</span>
                            <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Desktop Pet Live Interactions (Mouse &amp; Physics)</h3>
                        </div>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; line-height: 1.45;">
                            Configure drag-and-throw kinetic fling physics, real-time web shooting to cursor, mouse follow chase, and desktop sticky notes.
                        </p>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px;">
                    <!-- 1. Drag-and-Throw (Fling Physics) -->
                    <div class="apple-glass-card-sub" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 18px;">
                        <div style="display: flex; flex-direction: column; gap: 4px; max-width: 78%;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 13.5px; font-weight: 600; color: #f1f5f9; letter-spacing: -0.01em;">🚀 Drag-and-Throw (Fling Physics)</span>
                                <span id="badge-fling-physics" style="font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 9999px; background: rgba(16, 185, 129, 0.2); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.4); letter-spacing: 0.02em;">ON</span>
                            </div>
                            <span style="font-size: 11px; color: rgba(220, 228, 245, 0.55); line-height: 1.4;">Grab and fling Spider-Man with mouse; flies with kinetic velocity, rebounds off borders, and catches with a safety web strand. Turn OFF to disable throwing.</span>
                        </div>
                        <label class="spider-switch" title="Toggle Drag-and-Throw Kinetic Physics ON or OFF">
                            <input type="checkbox" id="toggle-fling-physics" checked />
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- 2. Web-Shoot to Cursor -->
                    <div class="apple-glass-card-sub" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 18px;">
                        <div style="display: flex; flex-direction: column; gap: 4px; max-width: 74%;">
                            <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">🕸️ Web-Shoot to Cursor (Ctrl + Click)</span>
                            <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Press Ctrl + Click anywhere on desktop to shoot real-time web strand toward cursor with comic "THWIP!" effect</span>
                            <div style="margin-top: 4px;">
                                <button id="btn-test-web-shoot" class="apple-button" style="background: rgba(0, 210, 255, 0.14); border: 1px solid rgba(0, 210, 255, 0.35); color: #00D2FF; padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;">
                                    <span>🎯</span> <span>Shoot Web Now</span>
                                </button>
                            </div>
                        </div>
                        <label class="spider-switch">
                            <input type="checkbox" id="toggle-web-shoot-cursor" checked />
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- 3. Mouse Chase / Follow Mode -->
                    <div class="apple-glass-card-sub" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 18px;">
                        <div style="display: flex; flex-direction: column; gap: 3px; max-width: 78%;">
                            <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">🎯 Mouse Chase / Follow Mode</span>
                            <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Spider-Man tracks cursor, turns, walks, and hops toward your mouse while you work</span>
                        </div>
                        <label class="spider-switch">
                            <input type="checkbox" id="toggle-mouse-following" checked />
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- 4. Spider Sticky Notes System -->
                    <div class="apple-glass-card-sub" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 18px;">
                        <div style="display: flex; flex-direction: column; gap: 3px; max-width: 78%;">
                            <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">📝 Spider Sticky Notes System</span>
                            <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Global master toggle for floating web-hanging desktop sticky notes and tasks</span>
                        </div>
                        <label class="spider-switch">
                            <input type="checkbox" id="toggle-sticky-notes-enabled" checked />
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Spider-Sense Dodging -->
                    <div class="apple-glass-card-sub" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 18px;">
                        <div style="display: flex; flex-direction: column; gap: 3px; max-width: 78%;">
                            <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">⚡ Spider-Sense Cursor Dodge</span>
                            <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Leaps away in reflex when mouse cursor approaches rapidly</span>
                        </div>
                        <label class="spider-switch">
                            <input type="checkbox" id="toggle-spider-sense" checked />
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Pass Clicks Through -->
                    <div class="apple-glass-card-sub" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 18px;">
                        <div style="display: flex; flex-direction: column; gap: 3px; max-width: 78%;">
                            <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">Pass Clicks Through Companion</span>
                            <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Mouse clicks pass straight through to underlying windows</span>
                        </div>
                        <label class="spider-switch">
                            <input type="checkbox" id="toggle-click-through" />
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Cursor Radius Slider -->
                    <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; gap: 8px; padding: 16px 18px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9;">Mouse Attention Radius</span>
                            <span id="label-cursor-radius-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #00D2FF; background: rgba(0, 210, 255, 0.12); border: 1px solid rgba(0, 210, 255, 0.3); padding: 2px 10px; border-radius: 9999px;">180 px</span>
                        </div>
                        <input type="range" id="slider-cursor-radius" min="30" max="500" step="10" value="180" class="apple-slider" style="flex: 1; accent-color: #00D2FF; cursor: pointer; height: 6px; border-radius: 9999px;" />
                        <div style="display: flex; justify-content: space-between; font-size: 11px; color: rgba(220, 228, 245, 0.5);">
                            <span>30 px (Close vicinity)</span>
                            <span>500 px (Wide screen radius)</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Card 4: Sound Effects & Comic Dialogue Bubbles -->
            <div id="card-sound-dialogue" class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 18px;">
                    <div style="display: flex; flex-direction: column; gap: 4px; max-width: 85%;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 20px;">🔊</span>
                            <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Audio, Dialogue &amp; Companion Pacing</h3>
                        </div>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; line-height: 1.45;">
                            Adjust sound cues, comic speech bubbles, and autonomous action pacing.
                        </p>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px;">
                    <!-- Sound Effects Toggle & Volume Slider -->
                    <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; gap: 12px; padding: 16px 18px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="display: flex; flex-direction: column; gap: 3px;">
                                <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">Sound Effects</span>
                                <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Web thwip, swing whoosh, and landing sounds</span>
                            </div>
                            <label class="spider-switch">
                                <input type="checkbox" id="toggle-sound-effects" />
                                <span class="spider-slider"></span>
                            </label>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                            <span style="font-size: 13px; color: rgba(220, 228, 245, 0.7);">Volume</span>
                            <span id="label-sound-volume-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 600; color: #00F5D4; background: rgba(0, 245, 212, 0.12); border: 1px solid rgba(0, 245, 212, 0.3); padding: 2px 10px; border-radius: 9999px;">25%</span>
                        </div>
                        <input type="range" id="slider-sound-volume" min="0" max="100" step="5" value="25" class="apple-slider" style="flex: 1; accent-color: #00F5D4; cursor: pointer; height: 6px; border-radius: 9999px;" />
                    </div>

                    <!-- Comic Speech Bubbles & Pacing Preset -->
                    <div class="apple-glass-card-sub" style="display: flex; flex-direction: column; gap: 12px; padding: 16px 18px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="display: flex; flex-direction: column; gap: 3px;">
                                <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">Comic Speech Bubbles</span>
                                <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Pop-up comic dialogues during activities</span>
                            </div>
                            <label class="spider-switch">
                                <input type="checkbox" id="toggle-comic-bubbles" checked />
                                <span class="spider-slider"></span>
                            </label>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 6px; margin-top: 4px;">
                            <span style="font-size: 13px; color: rgba(220, 228, 245, 0.7);">Activity Frequency / Pacing</span>
                            <div style="display: flex; gap: 8px;">
                                <button class="pacing-preset-btn apple-button apple-preset-pill" data-pacing="calm" style="flex: 1;">Calm</button>
                                <button class="pacing-preset-btn apple-button apple-preset-pill active" data-pacing="normal" style="flex: 1; background: rgba(255, 45, 85, 0.18); border-color: rgba(255, 45, 85, 0.5); color: #fff;">Normal</button>
                                <button class="pacing-preset-btn apple-button apple-preset-pill" data-pacing="playful" style="flex: 1;">Playful</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        contentArea.appendChild(controlsWrapper);

        // Bind Controls Tab Listeners
        const tMasterHotkeys = document.getElementById("toggle-master-hotkeys");
        if (tMasterHotkeys) {
            tMasterHotkeys.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.enable_animation_hotkeys = en;
                sendAction("toggle_animation_hotkeys", { enabled: en });
            });
        }

        const tHotkeysMod = document.getElementById("toggle-hotkeys-modifier");
        if (tHotkeysMod) {
            tHotkeysMod.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.hotkeys_require_modifier = en;
                sendAction("toggle_hotkeys_require_modifier", { enabled: en });
            });
        }

        const btnEnableAllHk = document.getElementById("btn-enable-all-hotkeys");
        if (btnEnableAllHk) {
            btnEnableAllHk.addEventListener("click", () => {
                sendAction("set_all_number_keys", { enabled: true });
            });
        }

        const btnDisableAllHk = document.getElementById("btn-disable-all-hotkeys");
        if (btnDisableAllHk) {
            btnDisableAllHk.addEventListener("click", () => {
                sendAction("set_all_number_keys", { enabled: false });
            });
        }

        const tWasd = document.getElementById("toggle-wasd-enabled");
        if (tWasd) {
            tWasd.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.wasd_movement_enabled = en;
                sendAction("toggle_wasd", { enabled: en });
            });
        }

        const tWasdPin = document.getElementById("toggle-wasd-pin");
        if (tWasdPin) {
            tWasdPin.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.wasd_static_pin = en;
                sendAction("toggle_wasd_static_pin", { enabled: en });
            });
        }

        const sSpeed = document.getElementById("slider-movement-speed");
        const lSpeed = document.getElementById("label-movement-speed-val");
        if (sSpeed && lSpeed) {
            sSpeed.addEventListener("input", (e) => {
                const spd = parseFloat(e.target.value);
                lSpeed.innerText = `${spd.toFixed(1)}x`;
                sendAction("set_movement_speed", { speed: spd });
            });
        }

        document.querySelectorAll(".dpad-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const act = btn.getAttribute("data-act");
                sendAction("play_activity", { activity: act });
            });
        });

        const tFling = document.getElementById("toggle-fling-physics");
        if (tFling) {
            tFling.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.enable_fling_physics = en;
                state.appSettings.enable_fling_physics = en;
                updateFlingPhysicsUI(en);
                sendAction("toggle_fling_physics", { enabled: en });
                showProfileToast(en ? "🚀 Drag-and-Throw kinetic fling enabled!" : "⏸️ Drag-and-Throw disabled.");
            });
        }

        const tWebShoot = document.getElementById("toggle-web-shoot-cursor");
        if (tWebShoot) {
            tWebShoot.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.enable_web_shoot_cursor = en;
                sendAction("toggle_web_shoot_cursor", { enabled: en });
            });
        }

        const btnTestShoot = document.getElementById("btn-test-web-shoot");
        if (btnTestShoot) {
            btnTestShoot.addEventListener("click", () => {
                sendAction("shoot_web_cursor", {});
            });
        }

        const tStickyNotes = document.getElementById("toggle-sticky-notes-enabled");
        if (tStickyNotes) {
            tStickyNotes.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.enable_sticky_notes = en;
                state.appSettings.enable_sticky_notes = en;
                updateStickyNotesMasterToggleUI(en);
                sendAction("toggle_sticky_notes", { enabled: en });
                showProfileToast(en ? "🟢 Sticky notes turned ON - visible on desktop!" : "⚪ Sticky notes turned OFF - hidden on desktop.");
            });
        }

        const tMouseFollow = document.getElementById("toggle-mouse-following");
        if (tMouseFollow) {
            tMouseFollow.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.enable_mouse_following = en;
                sendAction("toggle_mouse_following", { enabled: en });
            });
        }

        const tSpiderSense = document.getElementById("toggle-spider-sense");
        if (tSpiderSense) {
            tSpiderSense.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.enable_spider_sense_dodging = en;
                sendAction("toggle_spider_sense_dodging", { enabled: en });
            });
        }

        const tClickThrough = document.getElementById("toggle-click-through");
        if (tClickThrough) {
            tClickThrough.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.click_through = en;
                sendAction("toggle_click_through", { enabled: en });
            });
        }

        const sCursorRad = document.getElementById("slider-cursor-radius");
        const lCursorRad = document.getElementById("label-cursor-radius-val");
        if (sCursorRad && lCursorRad) {
            sCursorRad.addEventListener("input", (e) => {
                const rad = parseInt(e.target.value);
                lCursorRad.innerText = `${rad} px`;
                sendAction("set_cursor_radius", { radius: rad });
            });
        }

        const tSound = document.getElementById("toggle-sound-effects");
        if (tSound) {
            tSound.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.sound_enabled = en;
                sendAction("toggle_sound", { enabled: en });
            });
        }

        const sSoundVol = document.getElementById("slider-sound-volume");
        const lSoundVol = document.getElementById("label-sound-volume-val");
        if (sSoundVol && lSoundVol) {
            sSoundVol.addEventListener("input", (e) => {
                const vol = parseInt(e.target.value);
                lSoundVol.innerText = `${vol}%`;
                sendAction("set_sound_volume", { volume: vol });
            });
        }

        const tComicBubbles = document.getElementById("toggle-comic-bubbles");
        if (tComicBubbles) {
            tComicBubbles.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.enable_comic_bubbles = en;
                sendAction("toggle_comic_bubbles", { enabled: en });
            });
        }

        document.querySelectorAll(".pacing-preset-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const p = btn.getAttribute("data-pacing");
                state.controlSettings.preset = p;
                sendAction("set_pacing_preset", { preset: p });
                updatePacingButtons(p);
            });
        });

        // ── Create Settings Tab Container (Apple Design System macOS System Settings) ──
        const settingsWrapper = document.createElement("div");
        settingsWrapper.id = "dashboard-settings-view";
        settingsWrapper.className = "dashboard-tab-view tab-hidden";
        settingsWrapper.style.width = "100%";
        settingsWrapper.style.flexDirection = "column";
        settingsWrapper.style.gap = "26px";
        settingsWrapper.style.setProperty("display", "none", "important");
        settingsWrapper.innerHTML = `
            <!-- Settings Header Block -->
            <div data-framer-name="Settings header" class="apple-header-block" style="display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; gap: 10px; align-items: baseline;">
                    <h1 class="apple-title" style="font-size: 34px; font-weight: 700; color: #f4f5ff; margin: 0; line-height: 1.15; letter-spacing: -0.028em;">System &amp;</h1>
                    <span class="apple-title-accent" style="font-size: 34px; font-weight: 700; color: #FF2D55; line-height: 1.15; letter-spacing: -0.028em;">Preferences.</span>
                </div>
                <p class="apple-subtext" style="font-size: 15px; color: rgba(220, 228, 245, 0.72); margin: 0; font-weight: 400; letter-spacing: -0.01em;">
                    Tune graphics performance, Windows integration, behavioral autonomy, audio cues, and disk storage.
                </p>
                <!-- Apple Instant Search Filter Input -->
                <div style="position: relative; max-width: 440px; margin-top: 6px;">
                    <input id="settings-filter-input" type="text" placeholder="Filter preferences by keyword..." class="apple-search-box" style="width: 100%; box-sizing: border-box; height: 38px; border-radius: 12px; background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12); color: #fff; padding: 0 14px 0 36px; font-size: 13.5px; outline: none; transition: all 0.2s ease;">
                    <span style="position: absolute; left: 12px; top: 10px; opacity: 0.5; font-size: 14px; pointer-events: none;">🔍</span>
                </div>
            </div>

            <!-- Group 1: Windows & Desktop Integration -->
            <div class="apple-glass-card settings-section-card" data-border="true" style="padding: 22px 24px; display: flex; flex-direction: column; gap: 18px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #0A84FF 0%, #0066CC 100%); display: flex; align-items: center; justify-content: center; font-size: 16px; box-shadow: 0 2px 8px rgba(10, 132, 255, 0.35);">🪟</div>
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Windows &amp; Desktop Integration</h3>
                        <p class="apple-subtext" style="font-size: 12.5px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">System startup, system tray behavior, and window layer behavior.</p>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <!-- Row: Run on Startup -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Run on Windows Login</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Automatically launch Spider-Buddy upon logging into Windows.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-run-on-startup" type="checkbox">
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Row: Start Minimized -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Start Minimized in System Tray</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Launch quietly into the system tray without opening the main window.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-start-minimized" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Row: Always on Top -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Always on Top Overlay</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Keep companion visible floating above active foreground windows.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-always-on-top" type="checkbox">
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Row: Transparent Click-Through -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Transparent Click-Through</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Pass all mouse clicks through the companion overlay to underlying desktop windows.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-click-through" type="checkbox">
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Row: Monitor Selection -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Active Desktop Monitor</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Choose which display the companion explores.</p>
                        </div>
                        <div style="display: flex; gap: 6px; background: rgba(0, 0, 0, 0.3); padding: 4px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08);">
                            <button class="settings-mon-btn apple-button" data-mon="primary" style="border-radius: 8px; padding: 6px 14px; font-size: 12px; cursor: pointer;">Primary</button>
                            <button class="settings-mon-btn apple-button" data-mon="secondary" style="border-radius: 8px; padding: 6px 14px; font-size: 12px; cursor: pointer;">Secondary</button>
                            <button class="settings-mon-btn apple-button" data-mon="all" style="border-radius: 8px; padding: 6px 14px; font-size: 12px; cursor: pointer;">All Displays</button>
                        </div>
                    </div>

                    <!-- Row: Default Corner Position -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Default Desktop Position</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Corner where companion resets when desktop habitat initializes.</p>
                        </div>
                        <div style="display: flex; gap: 6px; background: rgba(0, 0, 0, 0.3); padding: 4px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08);">
                            <button class="settings-pos-btn apple-button" data-pos="bottom_right" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">Bottom Right</button>
                            <button class="settings-pos-btn apple-button" data-pos="bottom_left" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">Bottom Left</button>
                            <button class="settings-pos-btn apple-button" data-pos="top_right" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">Top Right</button>
                            <button class="settings-pos-btn apple-button" data-pos="top_left" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">Top Left</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Group 2: Appearance, Framerate & Graphics Engine -->
            <div class="apple-glass-card settings-section-card" data-border="true" style="padding: 22px 24px; display: flex; flex-direction: column; gap: 18px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #AF52DE 0%, #7928CA 100%); display: flex; align-items: center; justify-content: center; font-size: 16px; box-shadow: 0 2px 8px rgba(175, 82, 222, 0.35);">🎨</div>
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Appearance &amp; Graphics Engine</h3>
                        <p class="apple-subtext" style="font-size: 12.5px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Theme aesthetics, framerate limits, playback speed, and film-authentic cadence.</p>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <!-- Theme Selector -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Dashboard Surface Theme</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Select the primary visual glass palette for Spider-Buddy.</p>
                        </div>
                        <div style="display: flex; gap: 6px; background: rgba(0, 0, 0, 0.3); padding: 4px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08);">
                            <button class="theme-select-btn apple-button" data-theme="dark" style="border-radius: 8px; padding: 6px 14px; font-size: 12.5px; cursor: pointer;">Dark Spider</button>
                            <button class="theme-select-btn apple-button" data-theme="midnight" style="border-radius: 8px; padding: 6px 14px; font-size: 12.5px; cursor: pointer;">Midnight OLED</button>
                            <button class="theme-select-btn apple-button" data-theme="light" style="border-radius: 8px; padding: 6px 14px; font-size: 12.5px; cursor: pointer;">Light Glass</button>
                        </div>
                    </div>

                    <!-- FPS Limit -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Target Framerate Limit</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Cap rendering ticks to minimize background CPU/GPU footprint.</p>
                        </div>
                        <div style="display: flex; gap: 6px; background: rgba(0, 0, 0, 0.3); padding: 4px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08);">
                            <button class="fps-select-btn apple-button" data-fps="0" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">VSync (Auto)</button>
                            <button class="fps-select-btn apple-button" data-fps="30" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">30 FPS</button>
                            <button class="fps-select-btn apple-button" data-fps="60" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">60 FPS</button>
                            <button class="fps-select-btn apple-button" data-fps="120" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">120 FPS</button>
                        </div>
                    </div>

                    <!-- Animation Speed -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Playback Speed Multiplier</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Adjust frame playback tempo for all acrobatic animations.</p>
                        </div>
                        <div style="display: flex; gap: 6px; background: rgba(0, 0, 0, 0.3); padding: 4px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08);">
                            <button class="anim-speed-btn apple-button" data-speed="0.75" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">0.75x</button>
                            <button class="anim-speed-btn apple-button" data-speed="1.0" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">1.0x Normal</button>
                            <button class="anim-speed-btn apple-button" data-speed="1.25" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">1.25x Fast</button>
                            <button class="anim-speed-btn apple-button" data-speed="1.5" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">1.5x Hyper</button>
                        </div>
                    </div>

                    <!-- Authentic Twos -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Spider-Verse "Animated on the 2s"</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Film-authentic 12fps step timing mimicking Into the Spider-Verse comic styling.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-authentic-twos" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Scale Slider -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; flex-direction: column; gap: 8px; padding: 14px 18px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Companion Height Scale</span>
                                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Resize the floating character on your desktop.</p>
                            </div>
                            <span id="label-settings-size-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 700; color: #FF2D55; background: rgba(255, 45, 85, 0.15); border: 1px solid rgba(255, 45, 85, 0.35); padding: 2px 10px; border-radius: 9999px;">200 px</span>
                        </div>
                        <input id="slider-settings-size" type="range" min="100" max="400" step="10" value="200" class="apple-slider">
                    </div>

                    <!-- Opacity Slider -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; flex-direction: column; gap: 8px; padding: 14px 18px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Stealth Transparency</span>
                                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Control character visual opacity.</p>
                            </div>
                            <span id="label-settings-opacity-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 700; color: #00F5D4; background: rgba(0, 245, 212, 0.12); border: 1px solid rgba(0, 245, 212, 0.3); padding: 2px 10px; border-radius: 9999px;">100%</span>
                        </div>
                        <input id="slider-settings-opacity" type="range" min="40" max="100" step="5" value="100" class="apple-slider">
                    </div>
                </div>
            </div>

            <!-- Group 3: Behavioral Autonomy & Reactions -->
            <div class="apple-glass-card settings-section-card" data-border="true" style="padding: 22px 24px; display: flex; flex-direction: column; gap: 18px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #FF2D55 0%, #D81B43 100%); display: flex; align-items: center; justify-content: center; font-size: 16px; box-shadow: 0 2px 8px rgba(255, 45, 85, 0.35);">⚡</div>
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Autonomy, Pacing &amp; Reactions</h3>
                        <p class="apple-subtext" style="font-size: 12.5px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">AI behavioral autonomy, personality presets, and interactive reactions.</p>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <!-- Auto Mode -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Autonomous AI Brain</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Allows Spider-Man to freely crawl, climb, perch, and do spontaneous tricks.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-auto-anim" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Personality Preset -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Pacing Personality Preset</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Tune how frequently the companion changes poses or executes acrobatics.</p>
                        </div>
                        <div style="display: flex; gap: 6px; background: rgba(0, 0, 0, 0.3); padding: 4px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08);">
                            <button class="settings-preset-btn apple-button" data-preset="calm" style="border-radius: 8px; padding: 6px 14px; font-size: 12px; cursor: pointer;">Calm</button>
                            <button class="settings-preset-btn apple-button" data-preset="normal" style="border-radius: 8px; padding: 6px 14px; font-size: 12px; cursor: pointer;">Normal</button>
                            <button class="settings-preset-btn apple-button" data-preset="playful" style="border-radius: 8px; padding: 6px 14px; font-size: 12px; cursor: pointer;">Playful</button>
                        </div>
                    </div>

                    <!-- Crawling Speed Slider -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; flex-direction: column; gap: 8px; padding: 14px 18px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Crawling Movement Speed</span>
                                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Velocity across screen edges, taskbars, and windows.</p>
                            </div>
                            <span id="label-settings-speed-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 700; color: #FF2D55; background: rgba(255, 45, 85, 0.15); border: 1px solid rgba(255, 45, 85, 0.35); padding: 2px 10px; border-radius: 9999px;">3.0x</span>
                        </div>
                        <input id="slider-settings-speed" type="range" min="1.0" max="6.0" step="0.5" value="3.0" class="apple-slider">
                    </div>

                    <!-- Spider-Sense Dodging -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Spider-Sense Cursor Dodging</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Instinctively jumps away when the mouse cursor approaches rapidly.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-dodge" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Mouse Following -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">🎯 Mouse Chase / Follow Mode</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Turns head, walks, and playfully hops toward the mouse cursor while working.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-mouse-follow" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Fling Physics -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">🚀 Drag-and-Throw (Fling Physics)</span>
                                <span id="badge-settings-fling-physics" style="font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 9999px; background: rgba(16, 185, 129, 0.2); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.4); letter-spacing: 0.02em;">ON</span>
                            </div>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Throws Spider-Man with kinetic momentum; rebounds off borders and deploys safety web strand.</p>
                        </div>
                        <label class="spider-switch" title="Toggle Drag-and-Throw Kinetic Physics ON or OFF">
                            <input id="toggle-settings-fling-physics" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Web-Shoot to Cursor -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">🕸️ Web-Shoot to Cursor (Ctrl + Click)</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Press Ctrl + Click anywhere on desktop to shoot real-time web line toward mouse with comic "THWIP!".</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-web-shoot-cursor" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Spider Sticky Notes Master Toggle -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">📝 Spider Sticky Notes System</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Master toggle for desktop web-hanging sticky notes and task management overlay.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-sticky-notes" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Comic Bubbles -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Comic Speech Bubbles</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Displays speech bubbles with quotes and reactions on screen.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-comic-bubbles" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Heavy Load Scene -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Collapsing Beam Under Heavy Load</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Triggers superhero collapsing beam lift scene when CPU or RAM &gt; 85%.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-heavy-load" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Audio Beat Sync -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Headphone Beat-Bobbing (Music Sync)</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Puts on headphones and bobs head to system audio and music beats.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-music-sync" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Battery Reactions -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Battery Charging Reactions</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Venom bio-electric surge / Stark suit recharge reactions when AC power plugs in.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-battery" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Low Battery Glitch -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Low Battery Suit Glitch</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Triggers dimensional suit glitch impulses when laptop battery is low.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-suit-glitch" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>
                </div>
            </div>

            <!-- Group 4: Audio & Sound Effects -->
            <div class="apple-glass-card settings-section-card" data-border="true" style="padding: 22px 24px; display: flex; flex-direction: column; gap: 18px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #34C759 0%, #288C3E 100%); display: flex; align-items: center; justify-content: center; font-size: 16px; box-shadow: 0 2px 8px rgba(52, 199, 89, 0.35);">🔊</div>
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Audio &amp; Sound Effects</h3>
                        <p class="apple-subtext" style="font-size: 12.5px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Comic sound effects on web shoots, thwips, acrobatics, and landings.</p>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <!-- Master Sound Toggle -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Enable Sound Effects</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Play comic web shooting and landing audio effects.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-sound" type="checkbox">
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Volume Slider & Test Button -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; flex-direction: column; gap: 10px; padding: 14px 18px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Effects Volume Level</span>
                                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Adjust the output volume for companion audio cues.</p>
                            </div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span id="label-settings-sound-vol-val" class="apple-pill-badge" style="font-size: 12px; font-weight: 700; color: #34C759; background: rgba(52, 199, 89, 0.15); border: 1px solid rgba(52, 199, 89, 0.35); padding: 2px 10px; border-radius: 9999px;">25%</span>
                                <button id="btn-settings-test-sound" class="apple-button" style="border-radius: 8px; padding: 4px 12px; font-size: 12px; cursor: pointer; color: #fff; background: rgba(255, 255, 255, 0.1);">Test Web SFX 🎵</button>
                            </div>
                        </div>
                        <input id="slider-settings-sound-vol" type="range" min="0" max="100" step="5" value="25" class="apple-slider">
                    </div>
                </div>
            </div>

            <!-- Group 5: Vision Health & Focus Breaks -->
            <div class="apple-glass-card settings-section-card" data-border="true" style="padding: 22px 24px; display: flex; flex-direction: column; gap: 18px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #FF9F0A 0%, #D47A00 100%); display: flex; align-items: center; justify-content: center; font-size: 16px; box-shadow: 0 2px 8px rgba(255, 159, 10, 0.35);">👁️</div>
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Health &amp; Vision Eye Breaks</h3>
                        <p class="apple-subtext" style="font-size: 12.5px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Prevent eye strain and maintain healthy ergonomics while working.</p>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <!-- Eye Break Toggle -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">20-20-20 Eye Break Reminders</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Notifies you to look at something 20 feet away for 20 seconds.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-eye-alert" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Interval Selection -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Continuous Typing Reminder Interval</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Time of unbroken computer usage before reminder fires.</p>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="display: flex; gap: 6px; background: rgba(0, 0, 0, 0.3); padding: 4px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08);">
                                <button class="settings-interval-btn apple-button" data-mins="10" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">10 Min</button>
                                <button class="settings-interval-btn apple-button" data-mins="20" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">20 Min</button>
                                <button class="settings-interval-btn apple-button" data-mins="30" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">30 Min</button>
                                <button class="settings-interval-btn apple-button" data-mins="60" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer;">60 Min</button>
                            </div>
                            <button id="btn-settings-test-eye" class="apple-button" style="border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer; color: #fff; background: rgba(255, 255, 255, 0.1);">Test Alert 💧</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Group 6: Controls & Shortcuts -->
            <div class="apple-glass-card settings-section-card" data-border="true" style="padding: 22px 24px; display: flex; flex-direction: column; gap: 18px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #FF9500 0%, #CC7A00 100%); display: flex; align-items: center; justify-content: center; font-size: 16px; box-shadow: 0 2px 8px rgba(255, 149, 0, 0.35);">⌨️</div>
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Keyboard &amp; Shortcut Preferences</h3>
                        <p class="apple-subtext" style="font-size: 12.5px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Global keyboard shortcuts and manual WASD desktop controls.</p>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <!-- Hotkeys Master -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Global Quick Action Hotkeys</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Trigger companion acrobatics with keyboard numbers 1–0.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-hotkeys" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- Require Modifier -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Require Win / Alt Modifier Key</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Requires pressing Win+1..0 or Alt+1..0 to prevent collision with typing.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-hotkeys-mod" type="checkbox">
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- WASD Movement -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">WASD Manual Desktop Control</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Drive companion directly around your desktop using W, A, S, D keys.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-wasd" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <!-- WASD Pin -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Pin After WASD Manual Movement</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Keep companion pinned at chosen spot until you give another command.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-wasd-pin" type="checkbox" checked>
                            <span class="spider-slider"></span>
                        </label>
                    </div>
                </div>
            </div>

            <!-- Group 7: Storage, Data & Maintenance -->
            <div class="apple-glass-card settings-section-card" data-border="true" style="padding: 22px 24px; display: flex; flex-direction: column; gap: 18px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #30B0C7 0%, #1A7080 100%); display: flex; align-items: center; justify-content: center; font-size: 16px; box-shadow: 0 2px 8px rgba(48, 176, 199, 0.35);">🧹</div>
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Storage, Cache &amp; Maintenance</h3>
                        <p class="apple-subtext" style="font-size: 12.5px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Inspect configuration, clear temporary cache buffers, and manage settings.</p>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <!-- Config File Location -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; flex-wrap: wrap; gap: 10px;">
                        <div style="flex: 1 1 300px; min-width: 0;">
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Configuration File Path</span>
                            <p id="settings-config-path-text" style="font-family: var(--font-mono); font-size: 11.5px; color: rgba(220, 228, 245, 0.7); margin: 4px 0 0 0; word-break: break-all; background: rgba(0, 0, 0, 0.25); padding: 6px 10px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.06);">
                                %APPDATA%/SpiderBuddy/settings.json
                            </p>
                        </div>
                        <button id="btn-open-config-folder" class="apple-button" style="border-radius: 8px; padding: 8px 16px; font-size: 12.5px; cursor: pointer; color: #fff; background: rgba(255, 255, 255, 0.1);">Reveal in Explorer 📂</button>
                    </div>

                    <!-- Temp Cache & Logs -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Frame Buffers &amp; Web Cache</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Calculated temporary files footprint on disk: <strong id="settings-cache-size-text" style="color: #00F5D4;">2.4 MB</strong></p>
                        </div>
                        <button id="btn-clear-cache" class="apple-button" style="border-radius: 8px; padding: 8px 16px; font-size: 12.5px; cursor: pointer; color: #fff; background: rgba(255, 255, 255, 0.1);">Clear Cache 🧹</button>
                    </div>

                    <!-- Reset Stats -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Reset Gameplay Statistics</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Zero out total distance crawled, web swings, and active time.</p>
                        </div>
                        <button id="btn-reset-stats" class="apple-button" style="border-radius: 8px; padding: 8px 16px; font-size: 12.5px; cursor: pointer; color: #fff; background: rgba(255, 255, 255, 0.1);">Reset Stats 📊</button>
                    </div>

                    <!-- Restore Defaults (Danger) -->
                    <div class="apple-glass-card-sub settings-row" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-color: rgba(255, 45, 85, 0.25);">
                        <div>
                            <span style="font-size: 14px; font-weight: 600; color: #FF2D55;">Restore All Settings to Defaults</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Wipe custom preferences and restore Spider-Buddy to factory defaults.</p>
                        </div>
                        <button id="btn-reset-defaults" class="apple-button" style="border-radius: 8px; padding: 8px 16px; font-size: 12.5px; cursor: pointer; color: #FF2D55; background: rgba(255, 45, 85, 0.15); border-color: rgba(255, 45, 85, 0.4);">Reset to Defaults ⚠️</button>
                    </div>
                </div>
            </div>

            <!-- Group 8: About Spider-Buddy -->
            <div class="apple-glass-card settings-section-card" data-border="true" style="padding: 22px 24px; display: flex; flex-direction: column; gap: 14px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #FF2D55 0%, #D81B43 100%); display: flex; align-items: center; justify-content: center; font-size: 16px; box-shadow: 0 2px 8px rgba(255, 45, 85, 0.35);">🕷️</div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Spider-Buddy Desktop Companion</h3>
                        <span id="settings-app-version-badge" class="apple-pill-badge" style="background: rgba(255, 45, 85, 0.2); color: #FF2D55; border: 1px solid rgba(255, 45, 85, 0.5); font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">v2.5.0</span>
                    </div>
                </div>
                <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                    <span id="settings-platform-badge" class="apple-pill-badge" style="background: rgba(255, 255, 255, 0.08); color: rgba(255, 255, 255, 0.8); border: 1px solid rgba(255, 255, 255, 0.12); font-size: 11px; padding: 4px 10px; border-radius: 6px;">Windows Desktop</span>
                    <span id="settings-engine-badge" class="apple-pill-badge" style="background: rgba(255, 255, 255, 0.08); color: rgba(255, 255, 255, 0.8); border: 1px solid rgba(255, 255, 255, 0.12); font-size: 11px; padding: 4px 10px; border-radius: 6px;">PySide6 Qt 6.8 • Chromium WebEngine</span>
                </div>
                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.5); margin: 4px 0 0 0;">
                    Crafted with Apple Human Interface Guidelines and Into the Spider-Verse aesthetics. Pair-programmed with Google Antigravity.
                </p>
            </div>
        `;
        contentArea.appendChild(settingsWrapper);

        // Search stable text (innerText on hidden rows can trigger layout).
        const sFilter = document.getElementById("settings-filter-input");
        const emptySettings = document.createElement("p");
        emptySettings.id = "settings-search-empty";
        emptySettings.textContent = "No preferences match your search.";
        emptySettings.hidden = true;
        settingsWrapper.appendChild(emptySettings);
        const searchableSections = [...settingsWrapper.querySelectorAll(".settings-section-card")].map(section => ({
            section,
            rows: [...section.querySelectorAll(".settings-row")].map(row => ({row, text: row.textContent.toLowerCase()})),
            text: section.textContent.toLowerCase()
        }));
        if (sFilter) {
            sFilter.addEventListener("input", () => {
                const q = sFilter.value.toLowerCase().trim();
                let matches = 0;
                searchableSections.forEach(({section, rows, text}) => {
                    let visible = !q || (!rows.length && text.includes(q));
                    rows.forEach(({row, text}) => {
                        const match = !q || text.includes(q);
                        row.style.setProperty("display", match ? "flex" : "none", "important");
                        visible = visible || match;
                    });
                    section.style.setProperty("display", visible ? "flex" : "none", "important");
                    if (visible) matches++;
                });
                emptySettings.hidden = matches > 0;
            });
        }

        // Group 1: Windows Toggles
        const tRunStartup = document.getElementById("toggle-run-on-startup");
        if (tRunStartup) {
            tRunStartup.addEventListener("change", (e) => {
                sendAction("toggle_run_on_startup", { enabled: e.target.checked });
            });
        }
        const tStartMin = document.getElementById("toggle-start-minimized");
        if (tStartMin) {
            tStartMin.addEventListener("change", (e) => {
                sendAction("toggle_start_minimized", { enabled: e.target.checked });
            });
        }
        const tAlwaysTop = document.getElementById("toggle-always-on-top");
        if (tAlwaysTop) {
            tAlwaysTop.addEventListener("change", (e) => {
                sendAction("toggle_always_on_top", { enabled: e.target.checked });
            });
        }
        const tSettingsClick = document.getElementById("toggle-settings-click-through");
        if (tSettingsClick) {
            tSettingsClick.addEventListener("change", (e) => {
                sendAction("toggle_click_through", { enabled: e.target.checked });
            });
        }
        document.querySelectorAll(".settings-mon-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const mon = btn.getAttribute("data-mon");
                sendAction("set_monitor", { monitor: mon });
                updateSettingsMonitorButtons(mon);
            });
        });
        document.querySelectorAll(".settings-pos-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const pos = btn.getAttribute("data-pos");
                sendAction("set_default_position", { position: pos });
                updateSettingsPositionButtons(pos);
            });
        });

        // Group 2: Appearance & Sliders
        const tAuthTwos = document.getElementById("toggle-authentic-twos");
        if (tAuthTwos) {
            tAuthTwos.addEventListener("change", (e) => {
                sendAction("toggle_authentic_twos", { enabled: e.target.checked });
            });
        }
        const sSetSize = document.getElementById("slider-settings-size");
        const lSetSize = document.getElementById("label-settings-size-val");
        if (sSetSize && lSetSize) {
            sSetSize.addEventListener("input", (e) => {
                const val = parseInt(e.target.value);
                lSetSize.innerText = `${val} px`;
                sendAction("set_size", { size: val });
                const mainSizeSlider = document.getElementById("slider-size");
                if (mainSizeSlider) mainSizeSlider.value = val;
            });
        }
        const sSetOp = document.getElementById("slider-settings-opacity");
        const lSetOp = document.getElementById("label-settings-opacity-val");
        if (sSetOp && lSetOp) {
            sSetOp.addEventListener("input", (e) => {
                const val = parseInt(e.target.value);
                lSetOp.innerText = `${val}%`;
                sendAction("set_opacity", { opacity: val });
                const mainOpSlider = document.getElementById("slider-opacity");
                if (mainOpSlider) mainOpSlider.value = val;
            });
        }

        // Group 3: Autonomy Toggles & Sliders
        const tSetAuto = document.getElementById("toggle-settings-auto-anim");
        if (tSetAuto) {
            tSetAuto.addEventListener("change", (e) => {
                sendAction("toggle_automatic_animations", { enabled: e.target.checked });
            });
        }
        document.querySelectorAll(".settings-preset-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const p = btn.getAttribute("data-preset");
                sendAction("set_pacing_preset", { preset: p });
                updateSettingsPresetButtons(p);
            });
        });
        const sSetSpd = document.getElementById("slider-settings-speed");
        const lSetSpd = document.getElementById("label-settings-speed-val");
        if (sSetSpd && lSetSpd) {
            sSetSpd.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                lSetSpd.innerText = `${val.toFixed(1)}x`;
                sendAction("set_movement_speed", { speed: val });
            });
        }
        const tSetDodge = document.getElementById("toggle-settings-dodge");
        if (tSetDodge) {
            tSetDodge.addEventListener("change", (e) => {
                sendAction("toggle_spider_sense_dodging", { enabled: e.target.checked });
            });
        }
        const tSetFollow = document.getElementById("toggle-settings-mouse-follow");
        if (tSetFollow) {
            tSetFollow.addEventListener("change", (e) => {
                sendAction("toggle_mouse_following", { enabled: e.target.checked });
            });
        }
        const tSetFling = document.getElementById("toggle-settings-fling-physics");
        if (tSetFling) {
            tSetFling.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.enable_fling_physics = en;
                state.appSettings.enable_fling_physics = en;
                updateFlingPhysicsUI(en);
                sendAction("toggle_fling_physics", { enabled: en });
                showProfileToast(en ? "🚀 Drag-and-Throw kinetic fling enabled!" : "⏸️ Drag-and-Throw disabled.");
            });
        }
        const tSetWebShoot = document.getElementById("toggle-settings-web-shoot-cursor");
        if (tSetWebShoot) {
            tSetWebShoot.addEventListener("change", (e) => {
                sendAction("toggle_web_shoot_cursor", { enabled: e.target.checked });
            });
        }
        const tSetSticky = document.getElementById("toggle-settings-sticky-notes");
        if (tSetSticky) {
            tSetSticky.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.enable_sticky_notes = en;
                state.appSettings.enable_sticky_notes = en;
                updateStickyNotesMasterToggleUI(en);
                sendAction("toggle_sticky_notes", { enabled: en });
                showProfileToast(en ? "🟢 Sticky notes turned ON - visible on desktop!" : "⚪ Sticky notes turned OFF - hidden on desktop.");
            });
        }
        const tSetBubbles = document.getElementById("toggle-settings-comic-bubbles");
        if (tSetBubbles) {
            tSetBubbles.addEventListener("change", (e) => {
                sendAction("toggle_comic_bubbles", { enabled: e.target.checked });
            });
        }
        const tSetHeavy = document.getElementById("toggle-settings-heavy-load");
        if (tSetHeavy) {
            tSetHeavy.addEventListener("change", (e) => {
                sendAction("toggle_heavy_load_scene", { enabled: e.target.checked });
            });
        }
        const tSetMusic = document.getElementById("toggle-settings-music-sync");
        if (tSetMusic) {
            tSetMusic.addEventListener("change", (e) => {
                sendAction("toggle_audio_beat_bobbing", { enabled: e.target.checked });
            });
        }
        const tSetBattery = document.getElementById("toggle-settings-battery");
        if (tSetBattery) {
            tSetBattery.addEventListener("change", (e) => {
                sendAction("toggle_battery_charging_reaction", { enabled: e.target.checked });
            });
        }
        const tSetGlitch = document.getElementById("toggle-settings-suit-glitch");
        if (tSetGlitch) {
            tSetGlitch.addEventListener("change", (e) => {
                sendAction("toggle_suit_glitch", { enabled: e.target.checked });
            });
        }

        // Group 4: Audio
        const tSetSound = document.getElementById("toggle-settings-sound");
        if (tSetSound) {
            tSetSound.addEventListener("change", (e) => {
                sendAction("toggle_sound", { enabled: e.target.checked });
            });
        }
        const sSetSoundVol = document.getElementById("slider-settings-sound-vol");
        const lSetSoundVol = document.getElementById("label-settings-sound-vol-val");
        if (sSetSoundVol && lSetSoundVol) {
            sSetSoundVol.addEventListener("input", (e) => {
                const val = parseInt(e.target.value);
                lSetSoundVol.innerText = `${val}%`;
                sendAction("set_sound_volume", { volume: val });
            });
        }
        const btnTestSound = document.getElementById("btn-settings-test-sound");
        if (btnTestSound) {
            btnTestSound.addEventListener("click", () => {
                sendAction("play_test_sound");
            });
        }

        // Group 5: Health
        const tSetEye = document.getElementById("toggle-settings-eye-alert");
        if (tSetEye) {
            tSetEye.addEventListener("change", (e) => {
                sendAction("toggle_eye_break", { enabled: e.target.checked });
            });
        }
        document.querySelectorAll(".settings-interval-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const mins = parseFloat(btn.getAttribute("data-mins"));
                sendAction("set_eye_break_interval", { minutes: mins });
                updateSettingsIntervalButtons(mins);
            });
        });
        const btnSettingsTestEye = document.getElementById("btn-settings-test-eye");
        if (btnSettingsTestEye) {
            btnSettingsTestEye.addEventListener("click", () => {
                sendAction("test_eye_break");
            });
        }

        // Group 6: Controls
        const tSetHk = document.getElementById("toggle-settings-hotkeys");
        if (tSetHk) {
            tSetHk.addEventListener("change", (e) => {
                sendAction("toggle_animation_hotkeys", { enabled: e.target.checked });
            });
        }
        const tSetHkMod = document.getElementById("toggle-settings-hotkeys-mod");
        if (tSetHkMod) {
            tSetHkMod.addEventListener("change", (e) => {
                sendAction("toggle_hotkeys_require_modifier", { enabled: e.target.checked });
            });
        }
        const tSetWasd = document.getElementById("toggle-settings-wasd");
        if (tSetWasd) {
            tSetWasd.addEventListener("change", (e) => {
                sendAction("toggle_wasd", { enabled: e.target.checked });
            });
        }
        const tSetWasdPin = document.getElementById("toggle-settings-wasd-pin");
        if (tSetWasdPin) {
            tSetWasdPin.addEventListener("change", (e) => {
                sendAction("toggle_wasd_static_pin", { enabled: e.target.checked });
            });
        }

        // Group 7: Maintenance Buttons
        const btnOpenCfg = document.getElementById("btn-open-config-folder");
        if (btnOpenCfg) {
            btnOpenCfg.addEventListener("click", () => {
                sendAction("open_config_folder");
            });
        }
        const btnClearCache = document.getElementById("btn-clear-cache");
        if (btnClearCache) {
            btnClearCache.addEventListener("click", () => {
                sendAction("clear_app_cache");
            });
        }
        const btnResetStats = document.getElementById("btn-reset-stats");
        if (btnResetStats) {
            btnResetStats.addEventListener("click", () => {
                sendAction("reset_companion_stats");
            });
        }
        const btnResetDefaults = document.getElementById("btn-reset-defaults");
        if (btnResetDefaults) {
            btnResetDefaults.addEventListener("click", () => {
                if (confirm("Are you sure you want to restore all settings to default values?")) {
                    sendAction("reset_all_settings");
                }
            });
        }

        // ── Create Profile Tab Container (Apple Design System: My Profile & Bin) ──
        const profileWrapper = document.createElement("div");
        profileWrapper.id = "dashboard-profile-view";
        profileWrapper.className = "dashboard-tab-view tab-hidden";
        profileWrapper.style.width = "100%";
        profileWrapper.style.flexDirection = "column";
        profileWrapper.style.gap = "26px";
        profileWrapper.style.setProperty("display", "none", "important");
        profileWrapper.innerHTML = `
            <!-- Profile Header Block -->
            <div data-framer-name="Profile header" class="apple-header-block" style="display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 12px;">
                    <div style="display: flex; gap: 10px; align-items: baseline;">
                        <h1 class="apple-title" style="font-size: 34px; font-weight: 700; color: #f4f5ff; margin: 0; line-height: 1.15; letter-spacing: -0.028em;">My</h1>
                        <span class="apple-title-accent" style="font-size: 34px; font-weight: 700; color: #FF2D55; line-height: 1.15; letter-spacing: -0.028em;">Profile.</span>
                    </div>
                    <!-- Operative Live Status Capsule -->
                    <div class="apple-pill-badge" style="display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 9999px; background: rgba(52, 199, 89, 0.12); border: 1px solid rgba(52, 199, 89, 0.32); color: #34c759; font-size: 12px; font-weight: 600;">
                        <span style="width: 7px; height: 7px; border-radius: 50%; background: #34c759; box-shadow: 0 0 8px #34c759;"></span>
                        <span>Multiverse Sync Active</span>
                    </div>
                </div>
                <p class="apple-subtext" style="font-size: 15px; color: rgba(220, 228, 245, 0.72); margin: 0; font-weight: 400; letter-spacing: -0.01em;">
                    Operative identity, companion telemetry, hero achievements, and removed character recycle bin.
                </p>

                <!-- Apple macOS Segmented Control Tab Bar -->
                <div style="margin-top: 10px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                    <div class="apple-segmented-bar" role="tablist">
                        <button class="apple-segmented-item active" id="seg-profile-overview" data-target="overview" role="tab" aria-selected="true">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                            <span>Operative Overview</span>
                        </button>
                        <button class="apple-segmented-item" id="seg-profile-preferences" data-target="preferences" role="tab" aria-selected="false">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                            <span>Preferences &amp; Bio</span>
                        </button>
                        <button class="apple-segmented-item" id="seg-profile-bin" data-target="bin" role="tab" aria-selected="false">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                            <span>Character Bin</span>
                            <span id="bin-counter-badge" class="apple-pill-badge" style="font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 9999px; background: rgba(255, 45, 85, 0.16); color: #ff2d55; border: 1px solid rgba(255, 45, 85, 0.3);">2</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Subview 1: Operative Overview -->
            <div id="profile-subview-overview" style="display: flex; flex-direction: column; gap: 22px;">
                <!-- Hero Identity Card -->
                <div class="apple-glass-card" data-border="true" style="padding: 24px 26px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px;">
                    <div style="display: flex; align-items: center; gap: 20px;">
                        <div style="position: relative; flex-shrink: 0;">
                            <div style="width: 72px; height: 72px; border-radius: 18px; overflow: hidden; background: #0c0f18; border: 1.5px solid rgba(255, 45, 85, 0.4); border-top: 1.5px solid rgba(255, 255, 255, 0.4); box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.3);">
                                <img id="profile-main-avatar" src="images/spiderman_brand_icon.png" alt="Profile" style="width: 100%; height: 100%; object-fit: cover;" />
                            </div>
                            <span style="position: absolute; bottom: -2px; right: -2px; width: 14px; height: 14px; border-radius: 50%; background: #34c759; border: 2.5px solid #090c14; box-shadow: 0 0 10px #34c759;"></span>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 4px;">
                            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                                <h2 id="profile-display-name-text" style="font-size: 22px; font-weight: 700; color: #f4f5ff; margin: 0; letter-spacing: -0.02em;">Peter Parker</h2>
                                <span id="profile-callsign-badge" style="font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px; background: rgba(255, 45, 85, 0.16); color: #ff2d55; border: 1px solid rgba(255, 45, 85, 0.32); letter-spacing: 0.02em;">Spider-Operative</span>
                                <span style="font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px; background: rgba(255, 159, 10, 0.15); color: #ff9f0a; border: 1px solid rgba(255, 159, 10, 0.32);">Level 7 Master</span>
                            </div>
                            <p id="profile-bio-text" style="font-size: 13.5px; color: rgba(220, 228, 245, 0.82); margin: 0; line-height: 1.45; font-style: italic; max-width: 580px;">
                                "With great power comes great responsibility. Balancing desktop productivity with web-slinging acrobatics."
                            </p>
                            <div style="display: flex; align-items: center; gap: 16px; margin-top: 6px; font-size: 12px; color: rgba(220, 228, 245, 0.6); flex-wrap: wrap;">
                                <span>🕷️ Active: <strong id="profile-active-char-chip" style="color: #34c759; font-weight: 600;">Tom Holland Spider-Man</strong></span>
                                <span>💻 Windows 11 Desktop</span>
                                <span>📅 Operative Since Oct 2026</span>
                            </div>
                        </div>
                    </div>
                    <button id="btn-jump-to-edit-profile" class="apple-button" style="padding: 9px 18px; border-radius: 10px; font-size: 13px; font-weight: 600; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.16); color: #fff; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                        <span>✎ Edit Preferences</span>
                    </button>
                </div>

                <!-- Apple Fitness / Health Style Metrics Grid -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                    <!-- Card 1 -->
                    <div class="apple-glass-card-sub" style="padding: 18px 20px; display: flex; flex-direction: column; gap: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 12px; font-weight: 600; color: rgba(220, 228, 245, 0.65); text-transform: uppercase; letter-spacing: 0.05em;">Companion Time</span>
                            <span style="font-size: 18px;">⏱️</span>
                        </div>
                        <div style="font-size: 24px; font-weight: 700; color: #f4f5ff; letter-spacing: -0.02em;">18h 42m</div>
                        <div style="font-size: 12px; color: #34c759; display: flex; align-items: center; gap: 4px;">
                            <span>↑ Active Today: 1h 15m</span>
                        </div>
                    </div>

                    <!-- Card 2 -->
                    <div class="apple-glass-card-sub" style="padding: 18px 20px; display: flex; flex-direction: column; gap: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 12px; font-weight: 600; color: rgba(220, 228, 245, 0.65); text-transform: uppercase; letter-spacing: 0.05em;">Focus Sessions</span>
                            <span style="font-size: 18px;">🎯</span>
                        </div>
                        <div style="font-size: 24px; font-weight: 700; color: #f4f5ff; letter-spacing: -0.02em;">14 Sessions</div>
                        <div style="font-size: 12px; color: rgba(220, 228, 245, 0.7);">350 mins deep work</div>
                    </div>

                    <!-- Card 3 -->
                    <div class="apple-glass-card-sub" style="padding: 18px 20px; display: flex; flex-direction: column; gap: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 12px; font-weight: 600; color: rgba(220, 228, 245, 0.65); text-transform: uppercase; letter-spacing: 0.05em;">Acrobatics</span>
                            <span style="font-size: 18px;">🕸️</span>
                        </div>
                        <div style="font-size: 24px; font-weight: 700; color: #f4f5ff; letter-spacing: -0.02em;">76 Tricks</div>
                        <div style="font-size: 12px; color: rgba(220, 228, 245, 0.7);">Top: Backflip &amp; Perch</div>
                    </div>

                    <!-- Card 4 -->
                    <div class="apple-glass-card-sub" style="padding: 18px 20px; display: flex; flex-direction: column; gap: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 12px; font-weight: 600; color: rgba(220, 228, 245, 0.65); text-transform: uppercase; letter-spacing: 0.05em;">Multiverse Roster</span>
                            <span style="font-size: 18px;">🦸</span>
                        </div>
                        <div style="font-size: 24px; font-weight: 700; color: #f4f5ff; letter-spacing: -0.02em;">5 Active</div>
                        <div style="font-size: 12px; color: #ff2d55;"><span id="profile-stats-bin-count">2</span> in Recycle Bin</div>
                    </div>

                    <!-- Card 5 -->
                    <div class="apple-glass-card-sub" style="padding: 18px 20px; display: flex; flex-direction: column; gap: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 12px; font-weight: 600; color: rgba(220, 228, 245, 0.65); text-transform: uppercase; letter-spacing: 0.05em;">Companion Harmony</span>
                            <span style="font-size: 18px;">❤️</span>
                        </div>
                        <div style="font-size: 24px; font-weight: 700; color: #f4f5ff; letter-spacing: -0.02em;">98% Bond</div>
                        <div style="width: 100%; height: 5px; border-radius: 9999px; background: rgba(255, 255, 255, 0.1); overflow: hidden; margin-top: 2px;">
                            <div style="width: 98%; height: 100%; background: linear-gradient(90deg, #34c759, #ff2d55); border-radius: 9999px;"></div>
                        </div>
                    </div>
                </div>

                <!-- Hero Milestones & Badges Section -->
                <div class="apple-glass-card" data-border="true" style="padding: 24px 26px; display: flex; flex-direction: column; gap: 18px;">
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0 0 4px 0; letter-spacing: -0.015em;">Operative Milestones &amp; Badges</h3>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0;">Special achievements earned by interacting with Spider-Buddy and finishing focus sprints.</p>
                    </div>

                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px;">
                        <!-- Badge 1 -->
                        <div class="apple-glass-card-sub" style="padding: 14px 16px; display: flex; align-items: center; gap: 14px;">
                            <div style="width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, #FF9F0A 0%, #D87B00 100%); display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 3px 10px rgba(255, 159, 10, 0.35); flex-shrink: 0;">🏅</div>
                            <div>
                                <div style="font-size: 13.5px; font-weight: 600; color: #f4f5ff;">Multiverse Hopper</div>
                                <div style="font-size: 12px; color: rgba(220, 228, 245, 0.65);">Unlocked 4+ Spider-suits</div>
                                <span style="font-size: 10.5px; color: #34c759; font-weight: 600;">✓ Unlocked</span>
                            </div>
                        </div>

                        <!-- Badge 2 -->
                        <div class="apple-glass-card-sub" style="padding: 14px 16px; display: flex; align-items: center; gap: 14px;">
                            <div style="width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, #0A84FF 0%, #005BBB 100%); display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 3px 10px rgba(10, 132, 255, 0.35); flex-shrink: 0;">🎯</div>
                            <div>
                                <div style="font-size: 13.5px; font-weight: 600; color: #f4f5ff;">Deep Focus Master</div>
                                <div style="font-size: 12px; color: rgba(220, 228, 245, 0.65);">Completed 10+ Pomodoro sessions</div>
                                <span style="font-size: 10.5px; color: #34c759; font-weight: 600;">✓ Unlocked</span>
                            </div>
                        </div>

                        <!-- Badge 3 -->
                        <div class="apple-glass-card-sub" style="padding: 14px 16px; display: flex; align-items: center; gap: 14px;">
                            <div style="width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, #FF2D55 0%, #C41235 100%); display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 3px 10px rgba(255, 45, 85, 0.35); flex-shrink: 0;">🕸️</div>
                            <div>
                                <div style="font-size: 13.5px; font-weight: 600; color: #f4f5ff;">Web-Slinger Acrobat</div>
                                <div style="font-size: 12px; color: rgba(220, 228, 245, 0.65);">Triggered 50+ animations</div>
                                <span style="font-size: 10.5px; color: #34c759; font-weight: 600;">✓ Unlocked</span>
                            </div>
                        </div>

                        <!-- Badge 4 -->
                        <div class="apple-glass-card-sub" style="padding: 14px 16px; display: flex; align-items: center; gap: 14px;">
                            <div style="width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, #AF52DE 0%, #7E2BB5 100%); display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 3px 10px rgba(175, 82, 222, 0.35); flex-shrink: 0;">🌙</div>
                            <div>
                                <div style="font-size: 13.5px; font-weight: 600; color: #f4f5ff;">Night Vigilante</div>
                                <div style="font-size: 12px; color: rgba(220, 228, 245, 0.65);">Active past 11:00 PM</div>
                                <span style="font-size: 10.5px; color: #34c759; font-weight: 600;">✓ Unlocked</span>
                            </div>
                        </div>

                        <!-- Badge 5 -->
                        <div class="apple-glass-card-sub" style="padding: 14px 16px; display: flex; align-items: center; gap: 14px;">
                            <div style="width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, #30D158 0%, #1A8C35 100%); display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 3px 10px rgba(48, 209, 88, 0.35); flex-shrink: 0;">🪟</div>
                            <div>
                                <div style="font-size: 13.5px; font-weight: 600; color: #f4f5ff;">Desktop Percher</div>
                                <div style="font-size: 12px; color: rgba(220, 228, 245, 0.65);">Perched on 5 app windows</div>
                                <span style="font-size: 10.5px; color: #34c759; font-weight: 600;">✓ Unlocked</span>
                            </div>
                        </div>

                        <!-- Badge 6 -->
                        <div class="apple-glass-card-sub" style="padding: 14px 16px; display: flex; align-items: center; gap: 14px;">
                            <div style="width: 40px; height: 40px; border-radius: 12px; background: rgba(255, 255, 255, 0.1); display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0;">⚡</div>
                            <div>
                                <div style="font-size: 13.5px; font-weight: 600; color: #f4f5ff;">Multiverse Overclock</div>
                                <div style="font-size: 12px; color: rgba(220, 228, 245, 0.65);">High performance tuning</div>
                                <span style="font-size: 10.5px; color: #ff9f0a; font-weight: 600;">In Progress (85%)</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Subview 2: Preferences & Bio -->
            <div id="profile-subview-preferences" style="display: none; flex-direction: column; gap: 22px;">
                <!-- Operative Profile Form -->
                <div class="apple-glass-card" data-border="true" style="padding: 24px 26px; display: flex; flex-direction: column; gap: 18px;">
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0 0 4px 0; letter-spacing: -0.015em;">Operative Identity &amp; Bio</h3>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0;">Customize how your profile appears in Spider-Buddy and on your local desktop dashboard.</p>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 14px;">
                        <div class="apple-glass-card-sub" style="padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                            <div>
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Display Name</span>
                                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Your preferred operative or real name.</p>
                            </div>
                            <input id="input-profile-name" type="text" value="Peter Parker" class="apple-search-box" style="width: 240px; height: 36px; border-radius: 10px; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: #fff; padding: 0 12px; font-size: 13.5px; outline: none;" />
                        </div>

                        <div class="apple-glass-card-sub" style="padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                            <div>
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Hero Codename / Callsign</span>
                                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Displayed on your sidebar profile tile.</p>
                            </div>
                            <input id="input-profile-callsign" type="text" value="Spider-Operative" class="apple-search-box" style="width: 240px; height: 36px; border-radius: 10px; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: #fff; padding: 0 12px; font-size: 13.5px; outline: none;" />
                        </div>

                        <div class="apple-glass-card-sub" style="padding: 14px 18px; display: flex; flex-direction: column; gap: 8px;">
                            <div>
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Bio / Status Motto</span>
                                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Your personal creed or daily focus mantra.</p>
                            </div>
                            <textarea id="input-profile-bio" rows="2" style="width: 100%; box-sizing: border-box; border-radius: 10px; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: #fff; padding: 10px 12px; font-size: 13.5px; font-family: inherit; resize: vertical; outline: none;">With great power comes great responsibility. Balancing desktop productivity with web-slinging acrobatics.</textarea>
                        </div>

                        <div class="apple-glass-card-sub" style="padding: 14px 18px; display: flex; flex-direction: column; gap: 10px;">
                            <div>
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Quick Profile Avatar Preset</span>
                                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Pick your active hero icon.</p>
                            </div>
                            <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center;" id="profile-avatar-picker-row">
                                <div class="profile-avatar-option active" data-img="images/spiderman_brand_icon.png" style="width: 44px; height: 44px; border-radius: 12px; overflow: hidden; cursor: pointer; border: 2px solid #FF2D55; box-shadow: 0 2px 8px rgba(255, 45, 85, 0.4); flex-shrink: 0;">
                                    <img src="images/spiderman_brand_icon.png" style="width: 100%; height: 100%; object-fit: cover;" />
                                </div>
                                <div class="profile-avatar-option" data-img="images/miles_brand_avatar.jpg" style="width: 44px; height: 44px; border-radius: 12px; overflow: hidden; cursor: pointer; border: 2px solid rgba(255, 255, 255, 0.15); flex-shrink: 0;">
                                    <img src="images/miles_brand_avatar.jpg" style="width: 100%; height: 100%; object-fit: cover;" />
                                </div>
                                <div class="profile-avatar-option" data-img="images/amazing_spiderman_face.jpg" style="width: 44px; height: 44px; border-radius: 12px; overflow: hidden; cursor: pointer; border: 2px solid rgba(255, 255, 255, 0.15); flex-shrink: 0;">
                                    <img src="images/amazing_spiderman_face.jpg" style="width: 100%; height: 100%; object-fit: cover;" />
                                </div>
                                <div class="profile-avatar-option" data-img="images/spiderman_avatar_brand.png" style="width: 44px; height: 44px; border-radius: 12px; overflow: hidden; cursor: pointer; border: 2px solid rgba(255, 255, 255, 0.15); flex-shrink: 0;">
                                    <img src="images/spiderman_avatar_brand.png" style="width: 100%; height: 100%; object-fit: cover;" />
                                </div>
                                <div id="btn-upload-avatar" title="Upload new profile photo" style="width: 44px; height: 44px; border-radius: 12px; border: 2px dashed rgba(255, 255, 255, 0.35); background: rgba(255, 255, 255, 0.05); display: flex; align-items: center; justify-content: center; cursor: pointer; color: #f8fafc; transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1); flex-shrink: 0;">
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                        <line x1="12" y1="5" x2="12" y2="19"></line>
                                        <line x1="5" y1="12" x2="19" y2="12"></line>
                                    </svg>
                                </div>
                                <input type="file" id="profile-avatar-file-input" accept="image/png, image/jpeg, image/jpg, image/webp, image/gif" style="display: none;" />
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Immersion & Audio Toggles -->
                <div class="apple-glass-card" data-border="true" style="padding: 24px 26px; display: flex; flex-direction: column; gap: 14px;">
                    <div>
                        <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0 0 4px 0; letter-spacing: -0.015em;">Immersion &amp; Audio Feedback</h3>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0;">Personal audio and haptic cues triggered during companion activities.</p>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <div class="apple-glass-card-sub" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                            <div>
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Web-Shooter Sound FX</span>
                                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Play comic whooshes and thwip audio cues during jumps.</p>
                            </div>
                            <label class="spider-switch"><input id="toggle-profile-sfx" type="checkbox" checked><span class="spider-slider"></span></label>
                        </div>

                        <div class="apple-glass-card-sub" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                            <div>
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Focus Session Voice Pings</span>
                                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Companion chimes when pomodoro interval completes.</p>
                            </div>
                            <label class="spider-switch"><input id="toggle-profile-voice" type="checkbox" checked><span class="spider-slider"></span></label>
                        </div>

                        <div class="apple-glass-card-sub" style="display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;">
                            <div>
                                <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Auto-Perch on Active Code Editors</span>
                                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Companion perches atop VS Code, Antigravity, or terminal windows.</p>
                            </div>
                            <label class="spider-switch"><input id="toggle-profile-perch" type="checkbox" checked><span class="spider-slider"></span></label>
                        </div>
                    </div>

                    <div style="display: flex; align-items: center; gap: 14px; margin-top: 10px;">
                        <button id="btn-save-profile" class="apple-button" style="background: linear-gradient(135deg, #FF2D55 0%, #D81B43 100%); color: #fff; border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 12px; padding: 10px 24px; font-weight: 600; font-size: 14px; cursor: pointer; box-shadow: 0 4px 14px rgba(255, 45, 85, 0.35);">
                            Save Profile Preferences
                        </button>
                        <span id="profile-save-toast" style="font-size: 13px; color: #34c759; font-weight: 600; opacity: 0; transition: opacity 0.3s ease;">
                            ✓ Profile saved successfully!
                        </span>
                    </div>
                </div>
            </div>

            <!-- Subview 3: Character Bin (Requested Feature) -->
            <div id="profile-subview-bin" style="display: none; flex-direction: column; gap: 20px;">
                <!-- Bin Header & Controls Card -->
                <div class="apple-glass-card" data-border="true" style="padding: 22px 24px; display: flex; flex-direction: column; gap: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 14px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 32px; height: 32px; border-radius: 8px; background: rgba(255, 45, 85, 0.16); border: 1px solid rgba(255, 45, 85, 0.35); display: flex; align-items: center; justify-content: center; font-size: 16px;">🗑️</div>
                                <h3 class="apple-card-title" style="font-size: 18px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Character Recycle Bin</h3>
                            </div>
                            <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 4px 0 0 0;">
                                Characters deleted or removed from your collection are stored here. You can restore them to your active roster anytime, or permanently delete them.
                            </p>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                            <button id="btn-bin-simulate" class="apple-button" style="padding: 7px 14px; border-radius: 9px; font-size: 12.5px; font-weight: 600; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.16); color: #f4f5ff; cursor: pointer;" title="Simulate removing a character to test the recycle bin">
                                + Send Test Hero to Bin
                            </button>
                            <button id="btn-bin-restore-all" class="apple-button" style="padding: 7px 14px; border-radius: 9px; font-size: 12.5px; font-weight: 600; background: rgba(52, 199, 89, 0.15); border: 1px solid rgba(52, 199, 89, 0.35); color: #34c759; cursor: pointer;">
                                ↺ Restore All
                            </button>
                            <button id="btn-bin-empty" class="apple-button" style="padding: 7px 14px; border-radius: 9px; font-size: 12.5px; font-weight: 600; background: rgba(255, 45, 85, 0.15); border: 1px solid rgba(255, 45, 85, 0.35); color: #ff2d55; cursor: pointer;">
                                ✕ Empty Bin
                            </button>
                        </div>
                    </div>

                    <!-- Bin Search Input -->
                    <div style="position: relative; max-width: 360px;">
                        <input id="bin-filter-input" type="text" placeholder="Filter removed characters..." class="apple-search-box" style="width: 100%; box-sizing: border-box; height: 36px; border-radius: 10px; background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12); color: #fff; padding: 0 14px 0 34px; font-size: 13px; outline: none;" />
                        <span style="position: absolute; left: 10px; top: 9px; opacity: 0.5; font-size: 13px; pointer-events: none;">🔍</span>
                    </div>
                </div>

                <!-- Removed Characters Grid -->
                <div id="bin-characters-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 18px; width: 100%;">
                    <!-- Dynamic removed characters populated here -->
                </div>

                <!-- Empty State -->
                <div id="bin-empty-state" class="apple-glass-card" data-border="true" style="padding: 44px 20px; display: none; flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 12px;">
                    <div style="width: 60px; height: 60px; border-radius: 18px; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.1); display: flex; align-items: center; justify-content: center; font-size: 28px;">🗑️</div>
                    <h3 style="font-size: 17px; font-weight: 600; color: #f4f5ff; margin: 0;">Recycle Bin is Empty</h3>
                    <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; max-width: 380px;">
                        No removed characters in the bin. Characters deleted or removed from your collection will appear here for recovery.
                    </p>
                    <button id="btn-bin-empty-add-sample" class="apple-button" style="margin-top: 8px; padding: 8px 18px; border-radius: 9999px; font-size: 12.5px; font-weight: 600; background: rgba(255, 45, 85, 0.16); border: 1px solid rgba(255, 45, 85, 0.35); color: #ff2d55; cursor: pointer;">
                        + Add Sample Character to Bin
                    </button>
                </div>
            </div>
        `;
        contentArea.appendChild(profileWrapper);

        // ── Sticky Notes View Container ────────────────────────────────────
        const stickyNotesWrapper = document.createElement("div");
        stickyNotesWrapper.id = "dashboard-sticky-notes-view";
        stickyNotesWrapper.className = "dashboard-tab-view tab-hidden";
        stickyNotesWrapper.style.width = "100%";
        stickyNotesWrapper.style.flexDirection = "column";
        stickyNotesWrapper.style.gap = "26px";
        stickyNotesWrapper.style.setProperty("display", "none", "important");
        stickyNotesWrapper.innerHTML = `
            <!-- Sticky Notes Header -->
            <div data-framer-name="Sticky notes header" class="apple-header-block" style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 16px;">
                <div style="display: flex; flex-direction: column; gap: 6px;">
                    <div style="display: flex; gap: 10px; align-items: baseline;">
                        <h1 class="apple-title" style="font-size: 34px; font-weight: 700; color: #f4f5ff; margin: 0; line-height: 1.15; letter-spacing: -0.028em;">Spider Sticky</h1>
                        <span class="apple-title-accent" style="font-size: 34px; font-weight: 700; color: #FF2D55; line-height: 1.15; letter-spacing: -0.028em;">Notes &amp; Reminders.</span>
                    </div>
                    <p class="apple-subtext" style="font-size: 15px; color: rgba(220, 228, 245, 0.72); margin: 0; font-weight: 400; letter-spacing: -0.01em;">
                        🕸️ Frosted glass notes hanging from webs on your desktop. Real-time tasks, auto-saving, and multiverse themes.
                    </p>
                </div>
                    <!-- Simple Sticky Notes ON / OFF Toggle Option -->
                    <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(255, 255, 255, 0.06); padding: 6px 14px; border-radius: 9999px; border: 1px solid rgba(255, 255, 255, 0.12);">
                        <span style="font-size: 13px; color: #f1f5f9; font-weight: 500;">Sticky Notes:</span>
                        <span id="label-sticky-notes-simple-status" style="font-size: 12px; font-weight: 700; color: #10B981; min-width: 26px;">ON</span>
                        <label class="spider-switch" style="margin: 0; transform: scale(0.82); transform-origin: center; cursor: pointer;" title="Toggle Sticky Notes ON or OFF">
                            <input type="checkbox" id="toggle-sticky-notes-header-enabled" checked />
                            <span class="spider-slider"></span>
                        </label>
                    </div>

                    <button id="btn-toggle-all-desktop-notes" class="apple-button" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.16); color: #f1f5f9; padding: 9px 18px; border-radius: 9999px; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 7px; backdrop-filter: blur(12px); transition: all 0.2s;">
                        <span>🕸️</span> <span id="label-toggle-all-desktop">Toggle Desktop Notes</span>
                    </button>
                    <button id="btn-create-sticky-note" class="apple-button" style="background: linear-gradient(135deg, #FF2D55 0%, #D81B43 100%); border: 1px solid rgba(255, 255, 255, 0.25); color: #ffffff; padding: 9px 20px; border-radius: 9999px; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 7px; box-shadow: 0 4px 16px rgba(255, 45, 85, 0.35); transition: all 0.2s;">
                        <span style="font-size: 16px; font-weight: bold; line-height: 1;">+</span> <span>New Sticky Note</span>
                    </button>
                </div>
            </div>

            <!-- Stats & Metrics Cards -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; width: 100%;">
                <div class="apple-glass-card-sub" style="padding: 16px 20px; border-radius: 16px; background: rgba(22, 27, 46, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); display: flex; align-items: center; gap: 14px;">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(255, 45, 85, 0.15); border: 1px solid rgba(255, 45, 85, 0.3); display: flex; align-items: center; justify-content: center; font-size: 20px;">📝</div>
                    <div>
                        <div id="stat-total-notes" style="font-size: 22px; font-weight: 700; color: #ffffff; line-height: 1.1;">0</div>
                        <div style="font-size: 12px; color: rgba(220, 228, 245, 0.6); margin-top: 2px;">Total Sticky Notes</div>
                    </div>
                </div>
                <div class="apple-glass-card-sub" style="padding: 16px 20px; border-radius: 16px; background: rgba(22, 27, 46, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); display: flex; align-items: center; gap: 14px;">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(0, 245, 212, 0.15); border: 1px solid rgba(0, 245, 212, 0.3); display: flex; align-items: center; justify-content: center; font-size: 20px;">✓</div>
                    <div>
                        <div id="stat-completed-tasks" style="font-size: 22px; font-weight: 700; color: #00F5D4; line-height: 1.1;">0 / 0</div>
                        <div style="font-size: 12px; color: rgba(220, 228, 245, 0.6); margin-top: 2px;">Tasks Completed</div>
                    </div>
                </div>
                <div class="apple-glass-card-sub" style="padding: 16px 20px; border-radius: 16px; background: rgba(22, 27, 46, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); display: flex; align-items: center; gap: 14px;">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(168, 85, 247, 0.15); border: 1px solid rgba(168, 85, 247, 0.3); display: flex; align-items: center; justify-content: center; font-size: 20px;">🕸️</div>
                    <div>
                        <div id="stat-desktop-visible" style="font-size: 22px; font-weight: 700; color: #c084fc; line-height: 1.1;">0</div>
                        <div style="font-size: 12px; color: rgba(220, 228, 245, 0.6); margin-top: 2px;">Hanging on Desktop</div>
                    </div>
                </div>
            </div>

            <!-- Filter & Search Toolbar -->
            <div class="apple-glass-card" style="padding: 16px 20px; border-radius: 18px; display: flex; flex-direction: column; gap: 14px; background: rgba(15, 20, 36, 0.7); border: 1px solid rgba(255, 255, 255, 0.09);">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <!-- Theme filter pills -->
                    <div id="sticky-theme-pills" style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <button class="sticky-filter-pill active" data-theme="all" style="padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; background: rgba(255, 255, 255, 0.15); color: #fff; border: 1px solid rgba(255, 255, 255, 0.3); cursor: pointer; transition: all 0.2s;">All Suits</button>
                        <button class="sticky-filter-pill" data-theme="spidey_red" style="padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; background: rgba(255, 45, 85, 0.12); color: #FF2D55; border: 1px solid rgba(255, 45, 85, 0.3); cursor: pointer; transition: all 0.2s;">🔴 Classic Red</button>
                        <button class="sticky-filter-pill" data-theme="miles_black" style="padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; background: rgba(255, 59, 48, 0.12); color: #ff6b6b; border: 1px solid rgba(255, 59, 48, 0.3); cursor: pointer; transition: all 0.2s;">⚡ Miles Morales</button>
                        <button class="sticky-filter-pill" data-theme="gwen_cyan" style="padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; background: rgba(0, 245, 212, 0.12); color: #00F5D4; border: 1px solid rgba(0, 245, 212, 0.3); cursor: pointer; transition: all 0.2s;">✨ Ghost-Spider</button>
                        <button class="sticky-filter-pill" data-theme="symbiote_purple" style="padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; background: rgba(168, 85, 247, 0.12); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); cursor: pointer; transition: all 0.2s;">🔮 Symbiote</button>
                        <button class="sticky-filter-pill" data-theme="spider_gold" style="padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600; background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); cursor: pointer; transition: all 0.2s;">🟡 Iron Spider</button>
                    </div>
                    <!-- Search input -->
                    <div style="position: relative; min-width: 240px; flex: 1; max-width: 320px;">
                        <span style="position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: rgba(255, 255, 255, 0.4); font-size: 13px; pointer-events: none;">🔍</span>
                        <input id="sticky-notes-search" type="text" placeholder="Search tasks & notes..." style="width: 100%; box-sizing: border-box; padding: 8px 14px 8px 36px; border-radius: 9999px; background: rgba(8, 12, 22, 0.7); border: 1px solid rgba(255, 255, 255, 0.12); color: #ffffff; font-size: 13px; outline: none; transition: border-color 0.2s;" />
                    </div>
                </div>
            </div>

            <!-- Notes Cards Grid -->
            <div id="sticky-notes-cards-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; width: 100%;">
                <!-- Dynamic cards populated here -->
            </div>

            <!-- Create Note Dialog Modal -->
            <div id="sticky-note-modal" style="display: none; position: fixed; inset: 0; background: rgba(5, 8, 16, 0.75); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); z-index: 10000; align-items: center; justify-content: center;">
                <div class="apple-glass-card" style="width: 480px; max-width: 90vw; padding: 28px; border-radius: 24px; background: rgba(18, 22, 38, 0.95); border: 1px solid rgba(255, 255, 255, 0.18); box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6); display: flex; flex-direction: column; gap: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 24px;">🕸️</span>
                            <h3 style="font-size: 18px; font-weight: 700; color: #f4f5ff; margin: 0;">Create Spider Sticky Note</h3>
                        </div>
                        <button id="modal-close-btn" style="background: rgba(255, 255, 255, 0.08); border: none; color: #cbd5e1; width: 28px; height: 28px; border-radius: 50%; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center;">✕</button>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 14px;">
                        <div>
                            <label style="font-size: 12px; font-weight: 600; color: rgba(220, 228, 245, 0.8); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; display: block;">Note Title</label>
                            <input id="modal-note-title" type="text" placeholder="e.g. Patrol Checklist & Daily Tasks" style="width: 100%; box-sizing: border-box; padding: 10px 14px; border-radius: 12px; background: rgba(8, 12, 22, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #fff; font-size: 14px; outline: none;" />
                        </div>

                        <div>
                            <label style="font-size: 12px; font-weight: 600; color: rgba(220, 228, 245, 0.8); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; display: block;">Suit Theme</label>
                            <div id="modal-theme-options" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                                <button type="button" class="modal-theme-opt active" data-theme="spidey_red" style="padding: 10px; border-radius: 12px; background: rgba(255, 45, 85, 0.16); border: 1.5px solid #FF2D55; color: #FF2D55; font-size: 12px; font-weight: 600; cursor: pointer;">🔴 Classic Red</button>
                                <button type="button" class="modal-theme-opt" data-theme="miles_black" style="padding: 10px; border-radius: 12px; background: rgba(255, 59, 48, 0.08); border: 1px solid rgba(255, 255, 255, 0.12); color: #ff6b6b; font-size: 12px; font-weight: 600; cursor: pointer;">⚡ Miles</button>
                                <button type="button" class="modal-theme-opt" data-theme="gwen_cyan" style="padding: 10px; border-radius: 12px; background: rgba(0, 245, 212, 0.08); border: 1px solid rgba(255, 255, 255, 0.12); color: #00F5D4; font-size: 12px; font-weight: 600; cursor: pointer;">✨ Gwen Cyan</button>
                                <button type="button" class="modal-theme-opt" data-theme="symbiote_purple" style="padding: 10px; border-radius: 12px; background: rgba(168, 85, 247, 0.08); border: 1px solid rgba(255, 255, 255, 0.12); color: #c084fc; font-size: 12px; font-weight: 600; cursor: pointer;">🔮 Symbiote</button>
                                <button type="button" class="modal-theme-opt" data-theme="spider_gold" style="padding: 10px; border-radius: 12px; background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(255, 255, 255, 0.12); color: #fbbf24; font-size: 12px; font-weight: 600; cursor: pointer;">🟡 Iron Spider</button>
                            </div>
                        </div>

                        <div>
                            <label style="font-size: 12px; font-weight: 600; color: rgba(220, 228, 245, 0.8); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; display: block;">Template Starter</label>
                            <div style="display: flex; gap: 8px;">
                                <button type="button" class="modal-template-btn active" data-type="checklist" style="flex: 1; padding: 8px; border-radius: 10px; background: rgba(255, 255, 255, 0.12); border: 1px solid rgba(255, 255, 255, 0.25); color: #fff; font-size: 12px; font-weight: 600; cursor: pointer;">✓ Tasks Checklist</button>
                                <button type="button" class="modal-template-btn" data-type="notes" style="flex: 1; padding: 8px; border-radius: 10px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #cbd5e1; font-size: 12px; font-weight: 600; cursor: pointer;">📝 Freeform Memo</button>
                            </div>
                        </div>

                        <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 13px; color: #e2e8f0; margin-top: 4px;">
                            <input id="modal-desktop-visible" type="checkbox" checked style="accent-color: #FF2D55; width: 16px; height: 16px; cursor: pointer;" />
                            <span>🕸️ Hang immediately on Desktop with spider-web string</span>
                        </label>
                    </div>

                    <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px;">
                        <button id="modal-cancel-btn" class="apple-button" style="padding: 10px 18px; border-radius: 12px; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: #cbd5e1; font-size: 13px; font-weight: 600; cursor: pointer;">Cancel</button>
                        <button id="modal-submit-btn" class="apple-button" style="padding: 10px 22px; border-radius: 12px; background: linear-gradient(135deg, #FF2D55 0%, #D81B43 100%); border: 1px solid rgba(255, 255, 255, 0.25); color: #fff; font-size: 13px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 16px rgba(255, 45, 85, 0.35);">Create Note</button>
                    </div>
                </div>
            </div>
        `;
        contentArea.appendChild(stickyNotesWrapper);


    }


    // ═════════════════════════════════════════════════════════════════════════
    // ── My Profile & Character Recycle Bin Logic ────────────────────────────
    // ═════════════════════════════════════════════════════════════════════════

    state.binCharacters = [];
    state.userProfile = null;
    let profileInitialized = false;

    async function loadProfileView() {
        // Fetch or load profile
        try {
            const res = await fetch("/api/user_profile");
            if (res.ok) {
                state.userProfile = await res.json();
            }
        } catch (e) {
            console.warn("[SpiderBuddy Profile] Could not fetch profile API:", e);
        }

        if (!state.userProfile) {
            const local = localStorage.getItem("spider_buddy_user_profile");
            if (local) {
                try { state.userProfile = JSON.parse(local); } catch (e) {}
            }
        }

        if (!state.userProfile) {
            state.userProfile = {
                name: "Peter Parker",
                callsign: "Spider-Operative",
                rank: "Level 7 Companion Master",
                bio: "With great power comes great responsibility. Balancing desktop productivity with web-slinging acrobatics.",
                avatar: "images/spiderman_brand_icon.png"
            };
        }

        // Apply profile values to UI
        updateProfileDOM();

        // Load Bin characters
        await loadBinCharacters();

        // Initialize event handlers once
        if (!profileInitialized) {
            initProfileHandlers();
            profileInitialized = true;
        }
    }

    function updateProfileDOM() {
        const p = state.userProfile || {};
        const nameEl = document.getElementById("profile-display-name-text");
        const callsignEl = document.getElementById("profile-callsign-badge");
        const bioEl = document.getElementById("profile-bio-text");
        const avatarEl = document.getElementById("profile-main-avatar");

        const sidebarName = document.getElementById("sidebar-profile-display-name");
        const sidebarSub = document.getElementById("sidebar-profile-callsign");
        const sidebarAvatar = document.getElementById("sidebar-profile-avatar-img");

        const inputName = document.getElementById("input-profile-name");
        const inputCallsign = document.getElementById("input-profile-callsign");
        const inputBio = document.getElementById("input-profile-bio");

        if (nameEl) nameEl.textContent = p.name || "Peter Parker";
        if (callsignEl) callsignEl.textContent = p.callsign || "Spider-Operative";
        if (bioEl) bioEl.textContent = `"${p.bio || "With great power comes great responsibility."}"`;
        if (avatarEl) {
            if (p.avatar) avatarEl.src = p.avatar;
            avatarEl.style.cursor = "pointer";
            avatarEl.title = "Click or double-click to view in big screen";
            avatarEl.onclick = (e) => {
                e.stopPropagation();
                openImageLightbox(avatarEl.src, p.name || "Profile Avatar");
            };
            avatarEl.ondblclick = (e) => {
                e.stopPropagation();
                openImageLightbox(avatarEl.src, p.name || "Profile Avatar");
            };
        }

        if (sidebarName) sidebarName.textContent = p.name || "My Profile";
        if (sidebarSub) sidebarSub.textContent = p.callsign || "Spider-Operative";
        if (sidebarAvatar && p.avatar) sidebarAvatar.src = p.avatar;

        const sidebarAvatarBox = document.querySelector(".sidebar-profile-avatar-box");
        if (sidebarAvatarBox) {
            sidebarAvatarBox.title = "Click or double-click to view profile photo in big screen";
            sidebarAvatarBox.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                const curSrc = (sidebarAvatar && sidebarAvatar.src) || p.avatar || "images/spiderman_brand_icon.png";
                openImageLightbox(curSrc, p.name || "Operative Profile");
            };
            sidebarAvatarBox.ondblclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                const curSrc = (sidebarAvatar && sidebarAvatar.src) || p.avatar || "images/spiderman_brand_icon.png";
                openImageLightbox(curSrc, p.name || "Operative Profile");
            };
        }

        if (inputName) inputName.value = p.name || "Peter Parker";
        if (inputCallsign) inputCallsign.value = p.callsign || "Spider-Operative";
        if (inputBio) inputBio.value = p.bio || "";

        // Update active companion chip
        const actChip = document.getElementById("profile-active-char-chip");
        if (actChip && state.activeCharacterId) {
            const found = (state.characters || []).find(c => c.id === state.activeCharacterId);
            if (found) {
                actChip.textContent = `${found.name} (${found.suit || "Hero Suit"})`;
            }
        }

        // Render profile avatar presets, custom avatars, and upload (+) button
        renderProfileAvatarPicker();
    }

    // —————————————————————————————————————————————————————————
    // Desktop Big-Screen Image Lightbox Preview
    // Opens a focused window overlay with full-res image & close button
    // —————————————————————————————————————————————————————————
    function openImageLightbox(imgSrc, title = "") {
        if (!imgSrc) return;

        let lightbox = document.getElementById("spider-image-lightbox");
        if (!lightbox) {
            lightbox = document.createElement("div");
            lightbox.id = "spider-image-lightbox";
            lightbox.className = "spider-lightbox-overlay";
            lightbox.innerHTML = `
                <button class="spider-lightbox-close" id="spider-lightbox-close-btn" title="Close preview (Esc)" aria-label="Close">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
                <div class="spider-lightbox-content" id="spider-lightbox-content-box">
                    <img class="spider-lightbox-img" id="spider-lightbox-img-el" src="" alt="Full view" />
                    <div class="spider-lightbox-caption" id="spider-lightbox-caption-box">
                        <span class="spider-lightbox-title" id="spider-lightbox-title-text"></span>
                        <span class="spider-lightbox-hint">• Double-click or Esc to close</span>
                    </div>
                </div>
            `;
            document.body.appendChild(lightbox);

            const closeLightbox = () => {
                lightbox.classList.remove("active");
                setTimeout(() => {
                    if (!lightbox.classList.contains("active")) {
                        lightbox.style.display = "none";
                    }
                }, 220);
            };

            const closeBtn = lightbox.querySelector("#spider-lightbox-close-btn");
            if (closeBtn) {
                closeBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    closeLightbox();
                });
            }

            // Close when clicking outside image
            lightbox.addEventListener("click", (e) => {
                if (e.target === lightbox || e.target.id === "spider-lightbox-content-box") {
                    closeLightbox();
                }
            });

            // Double click on the lightbox image itself closes it
            const imgEl = lightbox.querySelector("#spider-lightbox-img-el");
            if (imgEl) {
                imgEl.addEventListener("dblclick", (e) => {
                    e.stopPropagation();
                    closeLightbox();
                });
            }

            // Close on Escape key
            document.addEventListener("keydown", (e) => {
                if (e.key === "Escape" && lightbox.classList.contains("active")) {
                    closeLightbox();
                }
            });

            lightbox._close = closeLightbox;
        }

        const imgEl = lightbox.querySelector("#spider-lightbox-img-el");
        const titleEl = lightbox.querySelector("#spider-lightbox-title-text");
        if (imgEl) {
            imgEl.src = imgSrc;
            imgEl.alt = title || "Expanded view";
        }
        if (titleEl) {
            titleEl.textContent = title || "Image Preview";
        }

        lightbox.style.display = "flex";
        void lightbox.offsetWidth; // Force layout reflow
        lightbox.classList.add("active");
    }

    window.openImageLightbox = openImageLightbox;
    if (window.SpiderBuddy) {
        window.SpiderBuddy.openImageLightbox = openImageLightbox;
    }

    const DEFAULT_PROFILE_AVATARS = [
        "images/spiderman_brand_icon.png",
        "images/miles_brand_avatar.jpg",
        "images/amazing_spiderman_face.jpg",
        "images/spiderman_avatar_brand.png"
    ];

    function renderProfileAvatarPicker() {
        const row = document.getElementById("profile-avatar-picker-row");
        if (!row) return;

        const currentActive = (state.userProfile && state.userProfile.avatar) || DEFAULT_PROFILE_AVATARS[0];
        const customAvatars = (state.userProfile && Array.isArray(state.userProfile.custom_avatars)) ? state.userProfile.custom_avatars : [];

        row.innerHTML = "";

        // 1. Default 4 Presets (Cannot be deleted!)
        DEFAULT_PROFILE_AVATARS.forEach(imgUrl => {
            const isActive = currentActive === imgUrl;
            const item = document.createElement("div");
            item.className = `profile-avatar-option ${isActive ? "active" : ""}`;
            item.setAttribute("data-img", imgUrl);
            item.title = "Preset Hero Avatar (Click to select • Double-click to expand)";
            item.style.cssText = `
                width: 44px; height: 44px; border-radius: 12px; overflow: hidden; cursor: pointer;
                border: 2px solid ${isActive ? "#FF2D55" : "rgba(255, 255, 255, 0.15)"};
                box-shadow: ${isActive ? "0 2px 8px rgba(255, 45, 85, 0.4)" : "none"};
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
                position: relative; flex-shrink: 0; box-sizing: border-box;
            `;
            item.innerHTML = `<img src="${imgUrl}" style="width: 100%; height: 100%; object-fit: cover; display: block;" onerror="this.src='images/spiderman_brand_icon.png'" />`;

            item.addEventListener("click", () => selectProfileAvatar(imgUrl));
            item.addEventListener("dblclick", (e) => {
                e.preventDefault();
                e.stopPropagation();
                openImageLightbox(imgUrl, "Preset Hero Avatar");
            });
            row.appendChild(item);
        });

        // 2. Custom Uploaded Avatars (Can be deleted, showing a red delete badge button on top-right)
        customAvatars.forEach(imgUrl => {
            const isActive = currentActive === imgUrl;
            const container = document.createElement("div");
            container.style.cssText = "position: relative; width: 44px; height: 44px; flex-shrink: 0;";

            const item = document.createElement("div");
            item.className = `profile-avatar-option ${isActive ? "active" : ""}`;
            item.setAttribute("data-img", imgUrl);
            item.title = "Custom Profile Avatar (Click to select • Double-click to expand)";
            item.style.cssText = `
                width: 44px; height: 44px; border-radius: 12px; overflow: hidden; cursor: pointer;
                border: 2px solid ${isActive ? "#FF2D55" : "rgba(255, 255, 255, 0.15)"};
                box-shadow: ${isActive ? "0 2px 8px rgba(255, 45, 85, 0.4)" : "none"};
                transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1); box-sizing: border-box;
            `;
            item.innerHTML = `<img src="${imgUrl}" style="width: 100%; height: 100%; object-fit: cover; display: block;" onerror="this.src='images/spiderman_brand_icon.png'" />`;

            item.addEventListener("click", () => selectProfileAvatar(imgUrl));
            item.addEventListener("dblclick", (e) => {
                e.preventDefault();
                e.stopPropagation();
                openImageLightbox(imgUrl, "Custom Profile Photo");
            });

            // Delete button on top-right corner
            const delBtn = document.createElement("button");
            delBtn.className = "custom-avatar-delete-btn";
            delBtn.title = "Delete this custom avatar";
            delBtn.setAttribute("aria-label", "Delete this custom avatar");
            delBtn.style.cssText = `
                position: absolute; top: -6px; right: -6px; width: 20px; height: 20px;
                border-radius: 50%; background: #FF2D55; border: 1.5px solid rgba(255, 255, 255, 0.9);
                color: #ffffff; display: flex; align-items: center; justify-content: center;
                cursor: pointer; padding: 0; z-index: 10;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
                transition: transform 0.15s ease, background 0.15s ease;
            `;
            delBtn.innerHTML = `
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            `;
            delBtn.addEventListener("mouseenter", () => {
                delBtn.style.transform = "scale(1.18)";
                delBtn.style.background = "#ff4d6d";
            });
            delBtn.addEventListener("mouseleave", () => {
                delBtn.style.transform = "scale(1)";
                delBtn.style.background = "#FF2D55";
            });
            delBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                deleteCustomAvatar(imgUrl);
            });

            container.appendChild(item);
            container.appendChild(delBtn);
            row.appendChild(container);
        });

        // 3. "+" Plus Button to open File Manager / File Selector
        const addBtn = document.createElement("div");
        addBtn.id = "btn-upload-avatar";
        addBtn.title = "Upload new profile photo (Open File Manager)";
        addBtn.setAttribute("role", "button");
        addBtn.style.cssText = `
            width: 44px; height: 44px; border-radius: 12px;
            border: 2px dashed rgba(255, 255, 255, 0.35);
            background: rgba(255, 255, 255, 0.05);
            display: flex; align-items: center; justify-content: center;
            cursor: pointer; color: #f8fafc;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            flex-shrink: 0; box-sizing: border-box;
        `;
        addBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
        `;
        addBtn.addEventListener("mouseenter", () => {
            addBtn.style.borderColor = "#FF2D55";
            addBtn.style.background = "rgba(255, 45, 85, 0.15)";
            addBtn.style.color = "#FF2D55";
            addBtn.style.transform = "scale(1.05)";
            addBtn.style.boxShadow = "0 2px 10px rgba(255, 45, 85, 0.35)";
        });
        addBtn.addEventListener("mouseleave", () => {
            addBtn.style.borderColor = "rgba(255, 255, 255, 0.35)";
            addBtn.style.background = "rgba(255, 255, 255, 0.05)";
            addBtn.style.color = "#f8fafc";
            addBtn.style.transform = "scale(1)";
            addBtn.style.boxShadow = "none";
        });

        // Hidden file input
        const fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.id = "profile-avatar-file-input";
        fileInput.accept = "image/png, image/jpeg, image/jpg, image/webp, image/gif";
        fileInput.style.display = "none";

        addBtn.addEventListener("click", () => {
            fileInput.value = "";
            fileInput.click();
        });

        fileInput.addEventListener("change", handleAvatarFileUpload);

        row.appendChild(addBtn);
        row.appendChild(fileInput);
    }

    function selectProfileAvatar(imgUrl) {
        state.userProfile = state.userProfile || {};
        state.userProfile.avatar = imgUrl;

        const mainAv = document.getElementById("profile-main-avatar");
        const sideAv = document.getElementById("sidebar-profile-avatar-img");
        if (mainAv) mainAv.src = imgUrl;
        if (sideAv) sideAv.src = imgUrl;

        document.querySelectorAll(".profile-avatar-option").forEach(o => {
            if (o.getAttribute("data-img") === imgUrl) {
                o.classList.add("active");
                o.style.borderColor = "#FF2D55";
                o.style.boxShadow = "0 2px 8px rgba(255, 45, 85, 0.4)";
            } else {
                o.classList.remove("active");
                o.style.borderColor = "rgba(255, 255, 255, 0.15)";
                o.style.boxShadow = "none";
            }
        });

        localStorage.setItem("spider_buddy_user_profile", JSON.stringify(state.userProfile));
        fetch("/api/user_profile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(state.userProfile)
        }).catch(err => console.warn("[SpiderBuddy Profile] Auto-sync failed:", err));
    }

    async function handleAvatarFileUpload(e) {
        const file = e.target.files && e.target.files[0];
        if (!file) return;

        if (!file.type.startsWith("image/")) {
            alert("Please select a valid image file (PNG, JPG, WEBP, GIF).");
            return;
        }

        const reader = new FileReader();
        reader.onload = async (evt) => {
            const dataUrl = evt.target.result;
            showProfileToast("Uploading profile photo...");

            let finalUrl = dataUrl;
            try {
                const res = await fetch("/api/upload_profile_avatar", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        filename: file.name,
                        image_data: dataUrl
                    })
                });

                if (res.ok) {
                    const data = await res.json();
                    state.userProfile = state.userProfile || {};
                    state.userProfile.custom_avatars = data.custom_avatars || [];
                    finalUrl = data.url || dataUrl;
                    state.userProfile.avatar = finalUrl;
                } else {
                    throw new Error("Server upload returned non-200");
                }
            } catch (err) {
                console.warn("[SpiderBuddy Profile] Upload API error, using local data URL:", err);
                state.userProfile = state.userProfile || {};
                state.userProfile.custom_avatars = state.userProfile.custom_avatars || [];
                if (!state.userProfile.custom_avatars.includes(dataUrl)) {
                    state.userProfile.custom_avatars.push(dataUrl);
                }
                state.userProfile.avatar = dataUrl;
            }

            localStorage.setItem("spider_buddy_user_profile", JSON.stringify(state.userProfile));
            updateProfileDOM();
            showProfileToast("✓ Profile photo uploaded!");
        };
        reader.readAsDataURL(file);
    }

    async function deleteCustomAvatar(imgUrl) {
        if (!imgUrl) return;
        const confirmed = window.confirm("Are you sure you want to delete this custom profile photo?");
        if (!confirmed) return;

        try {
            const res = await fetch("/api/delete_profile_avatar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: imgUrl })
            });
            if (res.ok) {
                const data = await res.json();
                state.userProfile = state.userProfile || {};
                state.userProfile.custom_avatars = data.custom_avatars || [];
                if (data.avatar) {
                    state.userProfile.avatar = data.avatar;
                }
            } else {
                throw new Error("Server delete error");
            }
        } catch (err) {
            console.warn("[SpiderBuddy Profile] Delete API error, updating locally:", err);
            state.userProfile = state.userProfile || {};
            state.userProfile.custom_avatars = (state.userProfile.custom_avatars || []).filter(u => u !== imgUrl);
            if (state.userProfile.avatar === imgUrl) {
                state.userProfile.avatar = DEFAULT_PROFILE_AVATARS[0];
            }
        }

        if (state.userProfile.avatar === imgUrl) {
            state.userProfile.avatar = DEFAULT_PROFILE_AVATARS[0];
        }

        localStorage.setItem("spider_buddy_user_profile", JSON.stringify(state.userProfile));
        updateProfileDOM();
        showProfileToast("✓ Profile photo deleted!");
    }

    async function loadBinCharacters() {
        try {
            const res = await fetch("/api/bin/characters");
            if (res.ok) {
                state.binCharacters = await res.json();
            }
        } catch (e) {
            console.warn("[SpiderBuddy Bin] Could not fetch bin API:", e);
        }

        if (!Array.isArray(state.binCharacters) || state.binCharacters.length === 0) {
            const local = localStorage.getItem("spider_buddy_bin_characters");
            if (local) {
                try {
                    const parsed = JSON.parse(local);
                    if (Array.isArray(parsed) && parsed.length > 0) {
                        state.binCharacters = parsed;
                    }
                } catch (e) {}
            }
        }

        // If still empty on initial setup, seed 2 sample characters so bin is interactive
        if (!state.binCharacters || state.binCharacters.length === 0) {
            state.binCharacters = [
                {
                    id: "spider_2099",
                    name: "Spider-Man 2099",
                    display_name: "Spider-Man 2099 (Miguel O'Hara)",
                    suit: "Nueva York 2099 Suit",
                    description: "Earth-928 high-tech nano-weave suit with talons and accelerated vision.",
                    avatar: "images/spiderman_brand_icon.png",
                    preview_url: "images/spiderman_brand_icon.png",
                    removed_at: new Date().toISOString(),
                    removed_date_str: "Oct 21, 2026 • 04:45 PM"
                },
                {
                    id: "symbiote_classic",
                    name: "Symbiote Spider-Man",
                    display_name: "Symbiote Peter Parker",
                    suit: "Alien Symbiote Black Suit",
                    description: "Alien symbiote suit with liquid web shooters and shapeshifting tendrils.",
                    avatar: "images/spiderman_avatar_brand.png",
                    preview_url: "images/spiderman_avatar_brand.png",
                    removed_at: new Date().toISOString(),
                    removed_date_str: "Oct 21, 2026 • 05:15 PM"
                }
            ];
            saveBinLocal();
        }

        updateBinUI();
    }

    function saveBinLocal() {
        localStorage.setItem("spider_buddy_bin_characters", JSON.stringify(state.binCharacters || []));
    }

    function updateBinUI() {
        const binList = state.binCharacters || [];
        const badge = document.getElementById("bin-counter-badge");
        const statsBinCount = document.getElementById("profile-stats-bin-count");
        const grid = document.getElementById("bin-characters-grid");
        const emptyState = document.getElementById("bin-empty-state");

        if (badge) badge.textContent = String(binList.length);
        if (statsBinCount) statsBinCount.textContent = String(binList.length);

        if (!grid) return;
        grid.innerHTML = "";

        if (binList.length === 0) {
            if (emptyState) emptyState.style.display = "flex";
            return;
        }

        if (emptyState) emptyState.style.display = "none";

        binList.forEach(item => {
            const card = document.createElement("div");
            card.className = "apple-glass-card-sub";
            card.style.padding = "18px 20px";
            card.style.display = "flex";
            card.style.flexDirection = "column";
            card.style.gap = "14px";
            card.style.borderRadius = "16px";
            card.style.border = "1px solid rgba(255, 255, 255, 0.08)";
            card.style.background = "rgba(19, 23, 36, 0.65)";
            card.style.transition = "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)";

            const imgSrc = item.avatar || item.preview_url || "images/spiderman_brand_icon.png";
            const dateLabel = item.removed_date_str || "Recently removed";

            card.innerHTML = `
                <div style="display: flex; gap: 14px; align-items: center;">
                    <div style="width: 52px; height: 52px; border-radius: 14px; overflow: hidden; background: #0c0f18; border: 1px solid rgba(255, 45, 85, 0.3); flex-shrink: 0; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);">
                        <img src="${imgSrc}" alt="${item.name}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='images/spiderman_brand_icon.png'" />
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1 1 auto;">
                        <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                            <span style="font-size: 15px; font-weight: 700; color: #f4f5ff;">${item.name || item.display_name}</span>
                            <span class="apple-pill-badge" style="font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 4px; background: rgba(255, 255, 255, 0.08); color: rgba(220, 228, 245, 0.8);">Removed</span>
                        </div>
                        <span style="font-size: 12px; font-weight: 500; color: #FF2D55;">${item.suit || "Custom Suit"}</span>
                        <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">📅 ${dateLabel}</span>
                    </div>
                </div>
                <p style="font-size: 12px; color: rgba(220, 228, 245, 0.7); margin: 0; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                    ${item.description || "Stored safely in recycle bin. Can be restored to your active companion gallery anytime."}
                </p>
                <div style="display: flex; gap: 10px; align-items: center; margin-top: 4px; padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.06);">
                    <button class="bin-btn-restore apple-button" data-id="${item.id}" style="flex: 1; padding: 7px 12px; border-radius: 9px; font-size: 12px; font-weight: 600; background: linear-gradient(135deg, #30D158 0%, #1A8C35 100%); color: #fff; border: 1px solid rgba(255, 255, 255, 0.2); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 2px 8px rgba(48, 209, 88, 0.3);">
                        <span>↺ Restore</span>
                    </button>
                    <button class="bin-btn-delete apple-button" data-id="${item.id}" style="padding: 7px 12px; border-radius: 9px; font-size: 12px; font-weight: 600; background: rgba(255, 45, 85, 0.12); color: #ff2d55; border: 1px solid rgba(255, 45, 85, 0.28); cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;">
                        <span>✕ Delete</span>
                    </button>
                </div>
            `;

            const cardImg = card.querySelector("img");
            if (cardImg) {
                cardImg.style.cursor = "pointer";
                cardImg.title = "Double-click to view in big screen";
                cardImg.addEventListener("dblclick", (e) => {
                    e.stopPropagation();
                    openImageLightbox(imgSrc, `${item.name || item.display_name} (Recycle Bin)`);
                });
            }

            grid.appendChild(card);
        });

        // Bind restore buttons
        grid.querySelectorAll(".bin-btn-restore").forEach(btn => {
            btn.addEventListener("click", () => {
                const cid = btn.getAttribute("data-id");
                restoreFromBin(cid);
            });
        });

        // Bind delete buttons
        grid.querySelectorAll(".bin-btn-delete").forEach(btn => {
            btn.addEventListener("click", () => {
                const cid = btn.getAttribute("data-id");
                deleteFromBinPermanently(cid);
            });
        });
    }

    async function addToBin(char) {
        if (!char || !char.id) return;
        const now = new Date();
        const item = {
            id: char.id,
            name: char.name || char.display_name || "Custom Hero",
            display_name: char.display_name || char.name || "Custom Hero",
            suit: char.suit || "Hero Suit",
            description: char.description || "Custom Spider-Man hero suit.",
            avatar: char.preview_url || char.avatar || "images/spiderman_brand_icon.png",
            preview_url: char.preview_url || "images/spiderman_brand_icon.png",
            removed_at: now.toISOString(),
            removed_date_str: now.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" })
        };

        state.binCharacters = state.binCharacters || [];
        state.binCharacters = state.binCharacters.filter(c => c.id !== char.id);
        state.binCharacters.unshift(item);
        saveBinLocal();
        updateBinUI();

        try {
            await fetch("/api/bin/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ character: item })
            });
        } catch (e) {
            console.warn("[SpiderBuddy Bin] Failed to sync add to bin API:", e);
        }

        window.dispatchEvent(new CustomEvent("spider:character-removed", { detail: item }));
    }

    async function restoreFromBin(cid) {
        if (!cid) return;
        const item = (state.binCharacters || []).find(c => c.id === cid);
        state.binCharacters = (state.binCharacters || []).filter(c => c.id !== cid);
        saveBinLocal();
        updateBinUI();

        try {
            await fetch("/api/bin/restore", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ character_id: cid })
            });
        } catch (e) {
            console.warn("[SpiderBuddy Bin] Failed to sync restore API:", e);
        }

        // Notify app and reload active characters gallery
        if (window.SpiderBuddy && window.SpiderBuddy.loadCharacters) {
            window.SpiderBuddy.loadCharacters();
        }

        window.dispatchEvent(new CustomEvent("spider:character-restored", { detail: { id: cid, item } }));

        showProfileToast(`✓ Restored "${(item && item.name) || cid}" to character collection!`);
    }

    async function deleteFromBinPermanently(cid) {
        if (!cid) return;
        const confirmed = confirm("Are you sure you want to permanently delete this character from the bin?\nThis cannot be undone.");
        if (!confirmed) return;

        state.binCharacters = (state.binCharacters || []).filter(c => c.id !== cid);
        saveBinLocal();
        updateBinUI();

        try {
            await fetch("/api/bin/delete", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ character_id: cid })
            });
        } catch (e) {
            console.warn("[SpiderBuddy Bin] Failed to sync delete API:", e);
        }

        showProfileToast("Permanently removed from bin.");
    }

    async function emptyBin() {
        if (!state.binCharacters || state.binCharacters.length === 0) return;
        const confirmed = confirm("Are you sure you want to permanently purge all characters from the recycle bin?");
        if (!confirmed) return;

        state.binCharacters = [];
        saveBinLocal();
        updateBinUI();

        try {
            await fetch("/api/bin/empty", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({})
            });
        } catch (e) {
            console.warn("[SpiderBuddy Bin] Failed to sync empty bin API:", e);
        }

        showProfileToast("Recycle bin emptied.");
    }

    function switchProfileSegment(target) {
        const segOverview = document.getElementById("seg-profile-overview");
        const segPrefs = document.getElementById("seg-profile-preferences");
        const segBin = document.getElementById("seg-profile-bin");

        const viewOverview = document.getElementById("profile-subview-overview");
        const viewPrefs = document.getElementById("profile-subview-preferences");
        const viewBin = document.getElementById("profile-subview-bin");

        [segOverview, segPrefs, segBin].forEach(s => {
            if (s) {
                s.classList.remove("active");
                s.setAttribute("aria-selected", "false");
            }
        });

        [viewOverview, viewPrefs, viewBin].forEach(v => {
            if (v) v.style.display = "none";
        });

        if (target === "preferences") {
            if (segPrefs) {
                segPrefs.classList.add("active");
                segPrefs.setAttribute("aria-selected", "true");
            }
            if (viewPrefs) viewPrefs.style.display = "flex";
        } else if (target === "bin") {
            if (segBin) {
                segBin.classList.add("active");
                segBin.setAttribute("aria-selected", "true");
            }
            if (viewBin) viewBin.style.display = "flex";
        } else {
            if (segOverview) {
                segOverview.classList.add("active");
                segOverview.setAttribute("aria-selected", "true");
            }
            if (viewOverview) viewOverview.style.display = "flex";
        }
    }

    function showProfileToast(msg) {
        const toast = document.getElementById("profile-save-toast");
        if (toast) {
            toast.textContent = msg;
            toast.style.opacity = "1";
            setTimeout(() => { toast.style.opacity = "0"; }, 3000);
        }
    }

    function initProfileHandlers() {
        // Segment switching
        const segOverview = document.getElementById("seg-profile-overview");
        const segPrefs = document.getElementById("seg-profile-preferences");
        const segBin = document.getElementById("seg-profile-bin");

        if (segOverview) segOverview.addEventListener("click", () => switchProfileSegment("overview"));
        if (segPrefs) segPrefs.addEventListener("click", () => switchProfileSegment("preferences"));
        if (segBin) segBin.addEventListener("click", () => switchProfileSegment("bin"));

        const jumpBtn = document.getElementById("btn-jump-to-edit-profile");
        if (jumpBtn) jumpBtn.addEventListener("click", () => switchProfileSegment("preferences"));

        // Avatar presets and upload picker
        renderProfileAvatarPicker();

        // Left sidebar bottom avatar & card trigger bindings
        const sidebarAvatarBox = document.querySelector(".sidebar-profile-avatar-box");
        if (sidebarAvatarBox) {
            sidebarAvatarBox.title = "Click or double-click to view profile photo in big screen";
            sidebarAvatarBox.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                const avImg = document.getElementById("sidebar-profile-avatar-img");
                const src = (avImg && avImg.getAttribute("src")) || (state.userProfile && state.userProfile.avatar) || "images/spiderman_brand_icon.png";
                openImageLightbox(src, (state.userProfile && state.userProfile.name) || "Operative Profile");
            };
            sidebarAvatarBox.ondblclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                const avImg = document.getElementById("sidebar-profile-avatar-img");
                const src = (avImg && avImg.getAttribute("src")) || (state.userProfile && state.userProfile.avatar) || "images/spiderman_brand_icon.png";
                openImageLightbox(src, (state.userProfile && state.userProfile.name) || "Operative Profile");
            };
        }

        const sidebarCard = document.getElementById("sidebar-profile-card");
        if (sidebarCard) {
            sidebarCard.ondblclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                const avImg = document.getElementById("sidebar-profile-avatar-img");
                const src = (avImg && avImg.getAttribute("src")) || (state.userProfile && state.userProfile.avatar) || "images/spiderman_brand_icon.png";
                openImageLightbox(src, (state.userProfile && state.userProfile.name) || "Operative Profile");
            };
        }

        // Save profile preferences
        const saveBtn = document.getElementById("btn-save-profile");
        if (saveBtn) {
            saveBtn.addEventListener("click", async () => {
                const nameInp = document.getElementById("input-profile-name");
                const callsignInp = document.getElementById("input-profile-callsign");
                const bioInp = document.getElementById("input-profile-bio");

                state.userProfile = state.userProfile || {};
                state.userProfile.name = nameInp ? nameInp.value.trim() : state.userProfile.name;
                state.userProfile.callsign = callsignInp ? callsignInp.value.trim() : state.userProfile.callsign;
                state.userProfile.bio = bioInp ? bioInp.value.trim() : state.userProfile.bio;

                localStorage.setItem("spider_buddy_user_profile", JSON.stringify(state.userProfile));
                updateProfileDOM();

                try {
                    await fetch("/api/user_profile", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(state.userProfile)
                    });
                } catch (e) {
                    console.warn("[SpiderBuddy Profile] Could not save profile API:", e);
                }

                showProfileToast("✓ Profile preferences saved!");
            });
        }

        // Bin actions
        const restoreAllBtn = document.getElementById("btn-bin-restore-all");
        if (restoreAllBtn) {
            restoreAllBtn.addEventListener("click", () => {
                const list = [...(state.binCharacters || [])];
                if (list.length === 0) return;
                list.forEach(c => restoreFromBin(c.id));
                showProfileToast("✓ Restored all characters to collection!");
            });
        }

        const emptyBtn = document.getElementById("btn-bin-empty");
        if (emptyBtn) emptyBtn.addEventListener("click", emptyBin);

        const simulateBtn = document.getElementById("btn-bin-simulate");
        const addSampleBtn = document.getElementById("btn-bin-empty-add-sample");

        const addSample = () => {
            const sampleId = "sample_hero_" + Date.now();
            addToBin({
                id: sampleId,
                name: "Spider-Punk (Hobie Brown)",
                display_name: "Spider-Punk (Hobie Brown)",
                suit: "Anarchy Punk Guitar Suit",
                description: "Earth-138 punk rock spider hero wielding a custom electric guitar with seismic distortion.",
                avatar: "images/spiderman_avatar_brand.png",
                preview_url: "images/spiderman_avatar_brand.png"
            });
            showProfileToast("Added Spider-Punk to Recycle Bin!");
        };

        if (simulateBtn) simulateBtn.addEventListener("click", addSample);
        if (addSampleBtn) addSampleBtn.addEventListener("click", addSample);

        // Filter bin input
        const binFilter = document.getElementById("bin-filter-input");
        if (binFilter) {
            binFilter.addEventListener("input", (e) => {
                const q = e.target.value.toLowerCase().trim();
                const grid = document.getElementById("bin-characters-grid");
                if (!grid) return;
                grid.querySelectorAll(".apple-glass-card-sub").forEach(card => {
                    const text = card.textContent.toLowerCase();
                    card.style.display = text.includes(q) ? "flex" : "none";
                });
            });
        }
    }


    // ═════════════════════════════════════════════════════════════════════════
    // ── Spider Sticky Notes & Reminders Logic ────────────────────────────────
    // ═════════════════════════════════════════════════════════════════════════

    state.stickyNotes = [];
    state.stickyNotesFilter = "all";
    state.stickyNotesSearch = "";
    let stickyNotesInitialized = false;

    const THEME_PALETTES = {
        "spidey_red": {
            name: "Classic Spider-Red",
            accent: "#FF2D55",
            border: "rgba(255, 45, 85, 0.45)",
            glow: "0 8px 32px rgba(255, 45, 85, 0.22)",
            bg: "linear-gradient(150deg, rgba(35, 14, 24, 0.78) 0%, rgba(18, 12, 22, 0.88) 100%)",
            badgeBg: "rgba(255, 45, 85, 0.15)",
            badgeColor: "#FF2D55"
        },
        "miles_black": {
            name: "Miles Morales Shadow",
            accent: "#FF3B30",
            border: "rgba(255, 59, 48, 0.42)",
            glow: "0 8px 32px rgba(255, 59, 48, 0.2)",
            bg: "linear-gradient(150deg, rgba(20, 20, 28, 0.85) 0%, rgba(10, 10, 16, 0.95) 100%)",
            badgeBg: "rgba(255, 59, 48, 0.15)",
            badgeColor: "#ff6b6b"
        },
        "gwen_cyan": {
            name: "Ghost-Spider Cyan",
            accent: "#00F5D4",
            border: "rgba(0, 245, 212, 0.42)",
            glow: "0 8px 32px rgba(0, 245, 212, 0.2)",
            bg: "linear-gradient(150deg, rgba(12, 32, 38, 0.78) 0%, rgba(14, 20, 32, 0.88) 100%)",
            badgeBg: "rgba(0, 245, 212, 0.15)",
            badgeColor: "#00F5D4"
        },
        "symbiote_purple": {
            name: "Symbiote Violet",
            accent: "#A855F7",
            border: "rgba(168, 85, 247, 0.42)",
            glow: "0 8px 32px rgba(168, 85, 247, 0.2)",
            bg: "linear-gradient(150deg, rgba(28, 16, 40, 0.78) 0%, rgba(14, 10, 26, 0.88) 100%)",
            badgeBg: "rgba(168, 85, 247, 0.15)",
            badgeColor: "#c084fc"
        },
        "spider_gold": {
            name: "Iron Spider Gold",
            accent: "#F59E0B",
            border: "rgba(245, 158, 11, 0.42)",
            glow: "0 8px 32px rgba(245, 158, 11, 0.2)",
            bg: "linear-gradient(150deg, rgba(38, 28, 14, 0.78) 0%, rgba(20, 16, 12, 0.88) 100%)",
            badgeBg: "rgba(245, 158, 11, 0.15)",
            badgeColor: "#fbbf24"
        }
    };

    function updateStickyNotesMasterToggleUI(isEnabled) {
        const en = Boolean(isEnabled);
        const tHeader = document.getElementById("toggle-sticky-notes-header-enabled");
        const tCtrl = document.getElementById("toggle-sticky-notes-enabled");
        const tSet = document.getElementById("toggle-settings-sticky-notes");
        const statusLabel = document.getElementById("label-sticky-notes-simple-status");

        if (tHeader) tHeader.checked = en;
        if (tCtrl) tCtrl.checked = en;
        if (tSet) tSet.checked = en;

        if (statusLabel) {
            statusLabel.textContent = en ? "ON" : "OFF";
            statusLabel.style.color = en ? "#10B981" : "#EF4444";
        }
    }

    function updateFlingPhysicsUI(isEnabled) {
        const en = Boolean(isEnabled);
        const tFling = document.getElementById("toggle-fling-physics");
        const tSetFling = document.getElementById("toggle-settings-fling-physics");
        const badgeCtrl = document.getElementById("badge-fling-physics");
        const badgeSet = document.getElementById("badge-settings-fling-physics");

        if (tFling) tFling.checked = en;
        if (tSetFling) tSetFling.checked = en;

        [badgeCtrl, badgeSet].forEach(badge => {
            if (badge) {
                if (en) {
                    badge.textContent = "ON";
                    badge.style.background = "rgba(16, 185, 129, 0.2)";
                    badge.style.color = "#10B981";
                    badge.style.borderColor = "rgba(16, 185, 129, 0.4)";
                } else {
                    badge.textContent = "OFF";
                    badge.style.background = "rgba(239, 68, 68, 0.2)";
                    badge.style.color = "#EF4444";
                    badge.style.borderColor = "rgba(239, 68, 68, 0.4)";
                }
            }
        });
    }

    async function loadStickyNotes() {
        try {
            const res = await fetch("/api/sticky_notes");
            if (res.ok) {
                const data = await res.json();
                state.stickyNotes = Array.isArray(data.notes) ? data.notes : [];
                console.log("[SpiderBuddy Notes] Loaded notes:", state.stickyNotes.length);
            }
        } catch (err) {
            console.warn("[SpiderBuddy Notes] Failed to fetch notes:", err);
        }

        renderStickyNotesDashboard();
        initStickyNotesEventsOnce();

        const isEn = (state.controlSettings && state.controlSettings.enable_sticky_notes !== undefined)
            ? state.controlSettings.enable_sticky_notes
            : (state.appSettings && state.appSettings.enable_sticky_notes !== undefined
                ? state.appSettings.enable_sticky_notes
                : true);
        updateStickyNotesMasterToggleUI(Boolean(isEn));
    }

    function initStickyNotesEventsOnce() {
        if (stickyNotesInitialized) return;
        stickyNotesInitialized = true;

        // Simple Sticky Notes ON / OFF Toggle in Header
        const tStickyHeader = document.getElementById("toggle-sticky-notes-header-enabled");
        if (tStickyHeader) {
            tStickyHeader.addEventListener("change", (e) => {
                const en = e.target.checked;
                state.controlSettings.enable_sticky_notes = en;
                state.appSettings.enable_sticky_notes = en;
                updateStickyNotesMasterToggleUI(en);
                sendAction("toggle_sticky_notes", { enabled: en });
                showProfileToast(en ? "🟢 Sticky notes turned ON - visible on desktop!" : "⚪ Sticky notes turned OFF - hidden on desktop.");
            });
        }

        // Search listener
        const searchInput = document.getElementById("sticky-notes-search");
        if (searchInput) {
            searchInput.addEventListener("input", (e) => {
                state.stickyNotesSearch = (e.target.value || "").toLowerCase().trim();
                renderStickyNotesGrid();
            });
        }

        // Theme filter pills
        const pillsContainer = document.getElementById("sticky-theme-pills");
        if (pillsContainer) {
            pillsContainer.querySelectorAll(".sticky-filter-pill").forEach(pill => {
                pill.addEventListener("click", () => {
                    pillsContainer.querySelectorAll(".sticky-filter-pill").forEach(p => {
                        p.classList.remove("active");
                        p.style.background = "rgba(255, 255, 255, 0.08)";
                        p.style.borderColor = "rgba(255, 255, 255, 0.15)";
                    });
                    pill.classList.add("active");
                    pill.style.background = "rgba(255, 255, 255, 0.2)";
                    pill.style.borderColor = "rgba(255, 255, 255, 0.4)";
                    state.stickyNotesFilter = pill.getAttribute("data-theme") || "all";
                    renderStickyNotesGrid();
                });
            });
        }

        // Top action buttons
        const btnCreate = document.getElementById("btn-create-sticky-note");
        if (btnCreate) {
            btnCreate.addEventListener("click", openCreateNoteModal);
        }

        const btnToggleAll = document.getElementById("btn-toggle-all-desktop-notes");
        if (btnToggleAll) {
            btnToggleAll.addEventListener("click", toggleAllDesktopNotes);
        }

        // Modal event listeners
        const modal = document.getElementById("sticky-note-modal");
        const modalClose = document.getElementById("modal-close-btn");
        const modalCancel = document.getElementById("modal-cancel-btn");
        const modalSubmit = document.getElementById("modal-submit-btn");

        if (modalClose) modalClose.addEventListener("click", closeCreateNoteModal);
        if (modalCancel) modalCancel.addEventListener("click", closeCreateNoteModal);
        if (modalSubmit) modalSubmit.addEventListener("click", submitCreateNoteModal);

        if (modal) {
            modal.addEventListener("click", (e) => {
                if (e.target === modal) closeCreateNoteModal();
            });
        }

        // Modal theme buttons
        const themeOpts = document.querySelectorAll(".modal-theme-opt");
        themeOpts.forEach(btn => {
            btn.addEventListener("click", () => {
                themeOpts.forEach(b => {
                    b.classList.remove("active");
                    b.style.borderColor = "rgba(255, 255, 255, 0.12)";
                    b.style.boxShadow = "none";
                });
                btn.classList.add("active");
                const th = btn.getAttribute("data-theme");
                const pal = THEME_PALETTES[th] || THEME_PALETTES["spidey_red"];
                btn.style.borderColor = pal.accent;
                btn.style.boxShadow = `0 0 12px ${pal.border}`;
            });
        });

        // Modal template buttons
        const tmplBtns = document.querySelectorAll(".modal-template-btn");
        tmplBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                tmplBtns.forEach(b => {
                    b.classList.remove("active");
                    b.style.background = "rgba(255, 255, 255, 0.05)";
                    b.style.borderColor = "rgba(255, 255, 255, 0.1)";
                    b.style.color = "#cbd5e1";
                });
                btn.classList.add("active");
                btn.style.background = "rgba(255, 255, 255, 0.16)";
                btn.style.borderColor = "rgba(255, 255, 255, 0.3)";
                btn.style.color = "#fff";
            });
        });
    }

    function renderStickyNotesDashboard() {
        const totalNotesEl = document.getElementById("stat-total-notes");
        const completedTasksEl = document.getElementById("stat-completed-tasks");
        const desktopVisEl = document.getElementById("stat-desktop-visible");

        let totalTasks = 0;
        let completedTasks = 0;
        let desktopVisibleCount = 0;

        (state.stickyNotes || []).forEach(note => {
            if (note.desktop_visible !== false) desktopVisibleCount++;
            const tasks = Array.isArray(note.items) ? note.items : (Array.isArray(note.tasks) ? note.tasks : []);
            totalTasks += tasks.length;
            completedTasks += tasks.filter(t => t.done || t.completed).length;
        });

        if (totalNotesEl) totalNotesEl.innerText = state.stickyNotes.length;
        if (completedTasksEl) completedTasksEl.innerText = `${completedTasks} / ${totalTasks}`;
        if (desktopVisEl) desktopVisEl.innerText = desktopVisibleCount;

        renderStickyNotesGrid();
    }

    function renderStickyNotesGrid() {
        const grid = document.getElementById("sticky-notes-cards-grid");
        if (!grid) return;

        let filtered = state.stickyNotes || [];

        if (state.stickyNotesFilter && state.stickyNotesFilter !== "all") {
            filtered = filtered.filter(n => (n.color || n.color_theme || "spidey_red") === state.stickyNotesFilter);
        }

        if (state.stickyNotesSearch) {
            const q = state.stickyNotesSearch;
            filtered = filtered.filter(n => {
                const titleMatch = (n.title || "").toLowerCase().includes(q);
                const descMatch = (n.content || "").toLowerCase().includes(q);
                const tasks = Array.isArray(n.items) ? n.items : (Array.isArray(n.tasks) ? n.tasks : []);
                const taskMatch = tasks.some(t => (t.text || "").toLowerCase().includes(q));
                return titleMatch || descMatch || taskMatch;
            });
        }

        if (filtered.length === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1 / -1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 24px; text-align: center; background: rgba(22, 27, 46, 0.45); border-radius: 20px; border: 1px dashed rgba(255, 255, 255, 0.12); gap: 12px;">
                    <div style="font-size: 36px;">🕸️</div>
                    <h3 style="font-size: 17px; font-weight: 600; color: #f4f5ff; margin: 0;">No Sticky Notes Found</h3>
                    <p style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; max-width: 360px;">
                        ${state.stickyNotesSearch ? "Try adjusting your search query or suit filter." : "Create your first web-hanging desktop note to organize your daily missions!"}
                    </p>
                    <button onclick="SpiderBuddy.openCreateNoteModal()" class="apple-button" style="margin-top: 8px; padding: 8px 20px; border-radius: 9999px; background: rgba(255, 45, 85, 0.16); border: 1px solid rgba(255, 45, 85, 0.35); color: #ff2d55; font-size: 13px; font-weight: 600; cursor: pointer;">
                        + Create Sticky Note
                    </button>
                </div>
            `;
            return;
        }

        grid.innerHTML = filtered.map(note => {
            const themeKey = note.color || note.color_theme || "spidey_red";
            const pal = THEME_PALETTES[themeKey] || THEME_PALETTES["spidey_red"];
            const isDesktop = note.desktop_visible !== false;
            const isPinned = !!(note.pinned !== undefined ? note.pinned : note.is_pinned);
            const tasks = Array.isArray(note.items) ? note.items : (Array.isArray(note.tasks) ? note.tasks : []);

            const tasksHtml = tasks.map((task, idx) => {
                const isCompleted = !!(task.done || task.completed);
                return `
                <div class="sticky-task-item" style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 5px 8px; border-radius: 8px; background: rgba(255, 255, 255, 0.03); transition: background 0.15s;">
                    <label style="display: flex; align-items: center; gap: 9px; cursor: pointer; flex: 1; min-width: 0;">
                        <input type="checkbox" ${isCompleted ? "checked" : ""} 
                               onchange="SpiderBuddy.toggleNoteItem('${note.id}', ${idx})" 
                               style="accent-color: ${pal.accent}; width: 16px; height: 16px; cursor: pointer; border-radius: 4px;" />
                        <span style="font-size: 13px; color: ${isCompleted ? "rgba(220, 228, 245, 0.45)" : "#f1f5f9"}; text-decoration: ${isCompleted ? "line-through" : "none"}; word-break: break-word;">
                            ${escapeHtml(task.text || "")}
                        </span>
                    </label>
                    <button onclick="SpiderBuddy.deleteNoteItem('${note.id}', ${idx})" 
                            title="Delete task" 
                            style="background: transparent; border: none; color: rgba(255, 255, 255, 0.35); font-size: 13px; cursor: pointer; padding: 2px 6px; border-radius: 4px; transition: color 0.15s;"
                            onmouseover="this.style.color='#FF453A'" onmouseout="this.style.color='rgba(255, 255, 255, 0.35)'">✕</button>
                </div>
            `;
            }).join("");

            return `
                <div class="apple-glass-card sticky-note-card" data-note-id="${note.id}" 
                     style="padding: 20px; border-radius: 20px; background: ${pal.bg}; border: 1px solid ${pal.border}; box-shadow: ${pal.glow}; display: flex; flex-direction: column; gap: 14px; position: relative; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s;">
                    
                    <!-- Decorative Top Web Strand Accent -->
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, ${pal.accent} 0%, rgba(255, 255, 255, 0.8) 50%, ${pal.accent} 100%);"></div>

                    <!-- Note Header -->
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                        <div style="flex: 1; min-width: 0;">
                            <input type="text" class="sticky-title-input" value="${escapeHtml(note.title || "Sticky Note")}" 
                                   onchange="SpiderBuddy.updateNoteTitle('${note.id}', this.value)"
                                   style="width: 100%; box-sizing: border-box; background: transparent; border: none; border-bottom: 1px dashed rgba(255, 255, 255, 0.2); color: #ffffff; font-size: 16px; font-weight: 700; padding: 2px 0 4px 0; outline: none;" />
                            <div style="display: flex; gap: 6px; align-items: center; margin-top: 6px;">
                                <span style="font-size: 10.5px; font-weight: 700; color: ${pal.badgeColor}; background: ${pal.badgeBg}; padding: 2px 8px; border-radius: 9999px; border: 1px solid ${pal.border}; text-transform: uppercase;">${pal.name}</span>
                                ${isPinned ? '<span style="font-size: 10.5px; font-weight: 600; color: #ffd166; background: rgba(255, 209, 102, 0.15); padding: 2px 7px; border-radius: 9999px;">📌 Pinned</span>' : ''}
                            </div>
                        </div>

                        <!-- Action Icons -->
                        <div style="display: flex; gap: 6px; align-items: center;">
                            <button onclick="SpiderBuddy.toggleNotePin('${note.id}')" 
                                    title="${isPinned ? "Unpin note" : "Pin always on top"}" 
                                    style="background: ${isPinned ? "rgba(255, 209, 102, 0.2)" : "rgba(255, 255, 255, 0.08)"}; border: 1px solid ${isPinned ? "rgba(255, 209, 102, 0.4)" : "rgba(255, 255, 255, 0.12)"}; color: ${isPinned ? "#ffd166" : "#cbd5e1"}; width: 28px; height: 28px; border-radius: 8px; font-size: 13px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s;">📌</button>
                            
                            <button onclick="SpiderBuddy.toggleNoteDesktop('${note.id}')" 
                                    title="${isDesktop ? "Hide from Desktop" : "Show hanging on Desktop"}" 
                                    style="background: ${isDesktop ? "rgba(168, 85, 247, 0.2)" : "rgba(255, 255, 255, 0.08)"}; border: 1px solid ${isDesktop ? "rgba(168, 85, 247, 0.4)" : "rgba(255, 255, 255, 0.12)"}; color: ${isDesktop ? "#c084fc" : "#cbd5e1"}; width: 28px; height: 28px; border-radius: 8px; font-size: 13px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s;">🕸️</button>

                            <button onclick="SpiderBuddy.deleteNote('${note.id}')" 
                                    title="Delete sticky note" 
                                    style="background: rgba(255, 69, 58, 0.1); border: 1px solid rgba(255, 69, 58, 0.25); color: #FF453A; width: 28px; height: 28px; border-radius: 8px; font-size: 13px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s;">🗑️</button>
                        </div>
                    </div>

                    <!-- Theme Switcher Dots -->
                    <div style="display: flex; gap: 7px; align-items: center; padding-top: 2px;">
                        <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5); font-weight: 500;">Suit Theme:</span>
                        ${Object.keys(THEME_PALETTES).map(key => {
                            const p = THEME_PALETTES[key];
                            const isCur = key === themeKey;
                            return `
                                <button onclick="SpiderBuddy.setNoteTheme('${note.id}', '${key}')" 
                                        title="${p.name}" 
                                        style="width: 14px; height: 14px; border-radius: 50%; background: ${p.accent}; border: ${isCur ? "2px solid #ffffff" : "1px solid rgba(255,255,255,0.3)"}; box-shadow: ${isCur ? `0 0 8px ${p.accent}` : "none"}; cursor: pointer; padding: 0; outline: none; transition: transform 0.15s;" 
                                        onmouseover="this.style.transform='scale(1.25)'" onmouseout="this.style.transform='scale(1)'"></button>
                            `;
                        }).join("")}
                    </div>

                    <!-- Tasks List Section -->
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                        <div style="font-size: 11.5px; font-weight: 600; color: rgba(220, 228, 245, 0.7); text-transform: uppercase; letter-spacing: 0.5px;">Tasks &amp; To-Do</div>
                        <div class="sticky-tasks-container" style="display: flex; flex-direction: column; gap: 4px; max-height: 180px; overflow-y: auto;">
                            ${tasksHtml || '<div style="font-size: 12px; color: rgba(220, 228, 245, 0.4); font-style: italic; padding: 4px 0;">No tasks yet. Add one below!</div>'}
                        </div>
                        
                        <!-- Add Task Input Row -->
                        <div style="display: flex; gap: 6px; margin-top: 4px;">
                            <input id="new-task-input-${note.id}" type="text" placeholder="+ Add a task (Press Enter)..." 
                                   onkeydown="if(event.key==='Enter') SpiderBuddy.addNoteTask('${note.id}')"
                                   style="flex: 1; padding: 6px 10px; border-radius: 8px; background: rgba(8, 12, 22, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); color: #fff; font-size: 12.5px; outline: none;" />
                            <button onclick="SpiderBuddy.addNoteTask('${note.id}')" 
                                    class="apple-button" 
                                    style="padding: 6px 12px; border-radius: 8px; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: #fff; font-size: 13px; font-weight: 700; cursor: pointer;">+</button>
                        </div>
                    </div>

                    <!-- Freeform Notes Memo Textarea -->
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <div style="font-size: 11.5px; font-weight: 600; color: rgba(220, 228, 245, 0.7); text-transform: uppercase; letter-spacing: 0.5px;">Notes &amp; Details</div>
                        <textarea onchange="SpiderBuddy.updateNoteContent('${note.id}', this.value)" 
                                  placeholder="Write notes, links, or coordinates here..." 
                                  style="width: 100%; box-sizing: border-box; height: 64px; resize: vertical; padding: 8px 10px; border-radius: 8px; background: rgba(8, 12, 22, 0.5); border: 1px solid rgba(255, 255, 255, 0.1); color: #e2e8f0; font-size: 12.5px; font-family: inherit; outline: none; line-height: 1.4;">${escapeHtml(note.content || "")}</textarea>
                    </div>

                    <!-- Card Footer Bar -->
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: rgba(220, 228, 245, 0.5); border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 8px; margin-top: 4px;">
                        <span>📍 X: ${note.pos_x !== undefined ? note.pos_x : (note.x || 300)}px • Y: ${note.pos_y !== undefined ? note.pos_y : (note.y || 80)}px</span>
                        <span>${isDesktop ? "🕸️ Web-Hanging Active" : "💤 Dashboard Only"}</span>
                    </div>
                </div>
            `;
        }).join("");
    }

    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // ── CRUD Actions ────────────────────────────────────────────────────────

    async function createStickyNote(data) {
        try {
            const res = await fetch("/api/sticky_notes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "create", ...data })
            });
            if (res.ok) {
                const resData = await res.json();
                console.log("[SpiderBuddy Notes] Created note:", resData);
                await loadStickyNotes();
                showProfileToast("🕸️ Spider Sticky Note created and web-hung!");
            }
        } catch (err) {
            console.error("[SpiderBuddy Notes] Create failed:", err);
        }
    }

    async function updateNoteTitle(id, title) {
        const note = (state.stickyNotes || []).find(n => n.id === id);
        if (note) note.title = title;
        await sendNoteUpdate(id, { title: title });
    }

    async function updateNoteContent(id, content) {
        const note = (state.stickyNotes || []).find(n => n.id === id);
        if (note) note.content = content;
        await sendNoteUpdate(id, { content: content });
    }

    async function setNoteTheme(id, theme) {
        const note = (state.stickyNotes || []).find(n => n.id === id);
        if (note) {
            note.color = theme;
            note.color_theme = theme;
        }
        renderStickyNotesDashboard();
        await sendNoteUpdate(id, { color: theme, color_theme: theme });
    }

    async function toggleNotePin(id) {
        const note = (state.stickyNotes || []).find(n => n.id === id);
        if (!note) return;
        const curPinned = !!(note.pinned !== undefined ? note.pinned : note.is_pinned);
        note.pinned = !curPinned;
        note.is_pinned = !curPinned;
        renderStickyNotesDashboard();
        await sendNoteUpdate(id, { pinned: note.pinned, is_pinned: note.is_pinned });
        showProfileToast(note.pinned ? "📌 Sticky Note pinned on top" : "📌 Sticky Note unpinned");
    }

    async function toggleNoteDesktop(id) {
        const note = (state.stickyNotes || []).find(n => n.id === id);
        if (!note) return;
        try {
            const res = await fetch("/api/sticky_notes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "toggle_desktop", id: id })
            });
            if (res.ok) {
                note.desktop_visible = !note.desktop_visible;
                renderStickyNotesDashboard();
                showProfileToast(note.desktop_visible ? "🕸️ Note hanging on Desktop" : "💤 Note hidden from Desktop");
            }
        } catch (err) {
            console.error("[SpiderBuddy Notes] Desktop toggle failed:", err);
        }
    }

    async function toggleNoteItem(id, itemIndex) {
        const note = (state.stickyNotes || []).find(n => n.id === id);
        const tasks = note ? (Array.isArray(note.items) ? note.items : (Array.isArray(note.tasks) ? note.tasks : [])) : [];
        if (tasks[itemIndex]) {
            const nextDone = !(tasks[itemIndex].done || tasks[itemIndex].completed);
            tasks[itemIndex].done = nextDone;
            tasks[itemIndex].completed = nextDone;
            renderStickyNotesDashboard();
        }
        try {
            await fetch("/api/sticky_notes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "toggle_item", id: id, item_index: itemIndex })
            });
        } catch (err) {
            console.error("[SpiderBuddy Notes] Toggle item failed:", err);
        }
    }

    async function addNoteTask(id) {
        const input = document.getElementById(`new-task-input-${id}`);
        if (!input) return;
        const text = (input.value || "").trim();
        if (!text) return;

        const note = (state.stickyNotes || []).find(n => n.id === id);
        if (!note) return;
        const tasks = Array.isArray(note.items) ? note.items : (Array.isArray(note.tasks) ? note.tasks : []);
        const newItem = { id: `item_${Date.now()}`, text: text, done: false, completed: false };
        tasks.push(newItem);
        note.items = tasks;
        note.tasks = tasks;

        input.value = "";
        renderStickyNotesDashboard();
        await sendNoteUpdate(id, { items: tasks, tasks: tasks });
    }

    async function deleteNoteItem(id, itemIndex) {
        const note = (state.stickyNotes || []).find(n => n.id === id);
        if (!note) return;
        const tasks = Array.isArray(note.items) ? note.items : (Array.isArray(note.tasks) ? note.tasks : []);
        tasks.splice(itemIndex, 1);
        note.items = tasks;
        note.tasks = tasks;
        renderStickyNotesDashboard();
        await sendNoteUpdate(id, { items: tasks, tasks: tasks });
    }

    async function deleteNote(id) {
        const note = (state.stickyNotes || []).find(n => n.id === id);
        const name = (note && note.title) || "this note";
        if (!confirm(`Delete "${name}"?`)) return;

        try {
            const res = await fetch("/api/sticky_notes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "delete", id: id })
            });
            if (res.ok) {
                state.stickyNotes = (state.stickyNotes || []).filter(n => n.id !== id);
                renderStickyNotesDashboard();
                showProfileToast("🗑️ Note deleted.");
            }
        } catch (err) {
            console.error("[SpiderBuddy Notes] Delete failed:", err);
        }
    }

    async function toggleAllDesktopNotes() {
        const allVisible = (state.stickyNotes || []).every(n => n.desktop_visible !== false);
        const newState = !allVisible;
        (state.stickyNotes || []).forEach(n => { n.desktop_visible = newState; });
        renderStickyNotesDashboard();

        try {
            await fetch("/api/sticky_notes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "save_all", notes: state.stickyNotes })
            });
            showProfileToast(newState ? "🕸️ All notes displayed on Desktop!" : "💤 All desktop notes hidden.");
        } catch (err) {
            console.error("[SpiderBuddy Notes] Toggle all failed:", err);
        }
    }

    async function sendNoteUpdate(id, patch) {
        try {
            await fetch("/api/sticky_notes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "update", id: id, ...patch })
            });
        } catch (err) {
            console.error("[SpiderBuddy Notes] Update failed:", err);
        }
    }

    // ── Modal Handlers ──────────────────────────────────────────────────────

    function openCreateNoteModal() {
        const modal = document.getElementById("sticky-note-modal");
        const titleInput = document.getElementById("modal-note-title");
        if (titleInput) titleInput.value = "";
        if (modal) {
            modal.style.display = "flex";
            if (titleInput) titleInput.focus();
        }
    }

    function closeCreateNoteModal() {
        const modal = document.getElementById("sticky-note-modal");
        if (modal) modal.style.display = "none";
    }

    async function submitCreateNoteModal() {
        const titleInput = document.getElementById("modal-note-title");
        const title = (titleInput && titleInput.value.trim()) || "Spider Mission Note";

        const activeThemeBtn = document.querySelector(".modal-theme-opt.active");
        const theme = (activeThemeBtn && activeThemeBtn.getAttribute("data-theme")) || "spidey_red";

        const activeTmplBtn = document.querySelector(".modal-template-btn.active");
        const tmplType = (activeTmplBtn && activeTmplBtn.getAttribute("data-type")) || "checklist";

        const desktopVis = document.getElementById("modal-desktop-visible");
        const isDesktop = desktopVis ? desktopVis.checked : true;

        let starterTasks = [];
        if (tmplType === "checklist") {
            starterTasks = [
                { text: "Check patrol coordinates", completed: false },
                { text: "Review daily reminders", completed: false }
            ];
        }

        const newNoteData = {
            title: title,
            content: tmplType === "notes" ? "Spider memo & details..." : "",
            color_theme: theme,
            tasks: starterTasks,
            desktop_visible: isDesktop,
            is_pinned: false,
            x: 240 + Math.floor(Math.random() * 200),
            y: 80 + Math.floor(Math.random() * 80)
        };

        closeCreateNoteModal();
        await createStickyNote(newNoteData);
    }

    // ── Switch Tabs ───────────────────────────────────────────────────────
    function switchTab(tabName) {
        if (state.currentTab === tabName) return;
        state.currentTab = tabName;
        sendAction("dashboard_tab", {tab: tabName});
        console.log("[SpiderBuddy Bridge] Switch to tab:", tabName);

        const homeView = document.getElementById("dashboard-home-view");
        const charView = document.getElementById("dashboard-characters-view");
        const actView = document.getElementById("dashboard-activities-view");
        const deskView = document.getElementById("dashboard-desktop-view");
        const focusView = document.getElementById("dashboard-focus-view");
        const controlsView = document.getElementById("dashboard-controls-view");
        const settingsView = document.getElementById("dashboard-settings-view");
        const profileView = document.getElementById("dashboard-profile-view");
        const notesView = document.getElementById("dashboard-sticky-notes-view");

        // First hide all views completely
        [homeView, charView, actView, deskView, focusView, controlsView, settingsView, profileView, notesView].forEach(v => {
            if (v) {
                v.classList.add("tab-hidden");
                v.style.setProperty("display", "none", "important");
            }
        });

        // Reset scroll position to top
        const mainDash = document.querySelector('[data-framer-name="Main dashboard"]');
        if (mainDash) mainDash.scrollTop = 0;
        const contentArea = document.querySelector('[data-framer-name="Dashboard content"]');
        if (contentArea) contentArea.scrollTop = 0;
        window.scrollTo(0, 0);

        if (tabName === "Characters") {
            if (charView) {
                charView.classList.remove("tab-hidden");
                charView.style.setProperty("display", "flex", "important");
                loadCharacters();
            }
            updateSidebarActiveItem("Characters");
        } else if (tabName === "Activities") {
            if (actView) {
                actView.classList.remove("tab-hidden");
                actView.style.setProperty("display", "flex", "important");
                loadActivities();
                loadTimingSettings();
            }
            updateSidebarActiveItem("Activities");
        } else if (tabName === "Desktop & Apps") {
            if (deskView) {
                deskView.classList.remove("tab-hidden");
                deskView.style.setProperty("display", "flex", "important");
                loadDisplaySettings();
                loadRunningApplications();
            }
            updateSidebarActiveItem("Desktop & Apps");
        } else if (tabName === "Focus & Breaks") {
            if (focusView) {
                focusView.classList.remove("tab-hidden");
                focusView.style.setProperty("display", "flex", "important");
                loadFocusSettings();
            }
            updateSidebarActiveItem("Focus & Breaks");
        } else if (tabName === "Controls") {
            if (controlsView) {
                controlsView.classList.remove("tab-hidden");
                controlsView.style.setProperty("display", "flex", "important");
                loadControlSettings();
            }
            updateSidebarActiveItem("Controls");
        } else if (tabName === "Settings") {
            if (settingsView) {
                settingsView.classList.remove("tab-hidden");
                settingsView.style.setProperty("display", "flex", "important");
                loadAppSettings();
            }
            updateSidebarActiveItem("Settings");
        } else if (tabName === "Home") {
            if (homeView) {
                homeView.classList.remove("tab-hidden");
                homeView.style.setProperty("display", "flex", "important");
                const img = document.getElementById("companion-live-frame");
                if (img && state.lastFrameB64) {
                    const srcVal = state.lastFrameB64.startsWith("data:") ? state.lastFrameB64 : "data:image/png;base64," + state.lastFrameB64;
                    if (img.src !== srcVal) {
                        img.src = srcVal;
                    }
                }
            }
            updateSidebarActiveItem("Home");
        } else if (tabName === "Profile" || tabName === "My Profile") {
            if (profileView) {
                profileView.classList.remove("tab-hidden");
                profileView.style.setProperty("display", "flex", "important");
                loadProfileView();
            }
            updateSidebarActiveItem("Profile");
        } else if (tabName === "Sticky Notes" || tabName === "StickyNotes" || tabName === "Spider Sticky Notes") {
            if (notesView) {
                notesView.classList.remove("tab-hidden");
                notesView.style.setProperty("display", "flex", "important");
                loadStickyNotes();
            }
            updateSidebarActiveItem("Sticky Notes");
        }
    }

    function updateSidebarActiveItem(activeName) {
        const navMap = {
            "Home": document.querySelector('[data-framer-name="Home"]'),
            "Characters": document.querySelector('[data-framer-name="Characters"]'),
            "Activities": document.querySelector('[data-framer-name="Activities"]'),
            "Desktop & Apps": document.querySelector('[data-framer-name="Desktop & Apps"]'),
            "Focus & Breaks": document.querySelector('[data-framer-name="Focus & Breaks"]'),
            "Controls": document.querySelector('[data-framer-name="Controls"]'),
            "Settings": document.querySelector('[data-framer-name="Settings"]'),
            "Sticky Notes": document.querySelector('[data-framer-name="Sticky Notes"]'),
            "Profile": document.getElementById("sidebar-profile-card") || document.querySelector('[data-framer-name="My Profile"]')
        };

        Object.keys(navMap).forEach(key => {
            const el = navMap[key];
            if (!el) return;
            const textEl = el.querySelector("p");

            if (key === activeName) {
                el.classList.add("nav-active");
                el.classList.remove("nav-inactive");
                el.style.setProperty("background", "linear-gradient(135deg, #FF2D55 0%, #D81B43 100%)", "important");
                el.style.setProperty("border", "1px solid rgba(255, 255, 255, 0.22)", "important");
                el.style.setProperty("border-top", "1px solid rgba(255, 255, 255, 0.38)", "important");
                el.style.setProperty("border-radius", "12px", "important");
                el.style.setProperty("box-shadow", "0 4px 18px rgba(255, 45, 85, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.25)", "important");
                el.style.setProperty("outline", "none", "important");
                el.removeAttribute("data-border");
                if (textEl) {
                    textEl.style.setProperty("color", "#ffffff", "important");
                    textEl.style.setProperty("font-weight", "600", "important");
                }
                const svg = el.querySelector("svg");
                if (svg) {
                    svg.style.setProperty("opacity", "1", "important");
                    svg.style.setProperty("color", "#ffffff", "important");
                }
                el.querySelectorAll("use").forEach(u => {
                    u.style.setProperty("fill", "#ffffff", "important");
                    u.style.setProperty("color", "#ffffff", "important");
                });
            } else {
                el.classList.remove("nav-active");
                el.classList.add("nav-inactive");
                el.style.setProperty("background", "transparent", "important");
                el.style.setProperty("border", "1px solid transparent", "important");
                el.style.setProperty("border-radius", "12px", "important");
                el.style.setProperty("box-shadow", "none", "important");
                el.style.setProperty("outline", "none", "important");
                el.removeAttribute("data-border");
                if (textEl) {
                    textEl.style.setProperty("color", "var(--apple-text-secondary)", "important");
                    textEl.style.setProperty("font-weight", "500", "important");
                }
                const svg = el.querySelector("svg");
                if (svg) {
                    svg.style.setProperty("opacity", "0.82", "important");
                    svg.style.setProperty("color", "inherit", "important");
                }
                el.querySelectorAll("use").forEach(u => {
                    u.style.removeProperty("fill");
                    u.style.removeProperty("color");
                });
            }
        });
    }

    // ── Load & Render Desktop & Apps Settings ──────────────────────────────
    function loadDisplaySettings() {
        fetch("/api/display_settings")
            .then(res => res.json())
            .then(data => {
                state.displaySettings = data;
                updateDisplaySettingsUI();
                renderTargetApplications();
            })
            .catch(err => console.warn("[SpiderBuddy Bridge] Failed to load display settings:", err));
    }

    function updateDisplaySettingsUI() {
        const ds = state.displaySettings;
        if (!ds) return;

        // Display Mode Card Styles
        const cardDesk = document.getElementById("mode-card-desktop");
        const cardApp = document.getElementById("mode-card-application");
        const badgeDesk = document.getElementById("badge-mode-desktop");
        const badgeApp = document.getElementById("badge-mode-app");
        const monSection = document.getElementById("monitor-section");

        if (ds.display_mode === "desktop") {
            if (cardDesk) {
                cardDesk.style.border = "2px solid #f51a58";
                cardDesk.style.background = "#14172a";
                cardDesk.style.boxShadow = "0 0 20px rgba(245, 26, 88, 0.25)";
            }
            if (cardApp) {
                cardApp.style.border = "1px solid #232b3e";
                cardApp.style.background = "#090d18";
                cardApp.style.boxShadow = "none";
            }
            if (badgeDesk) badgeDesk.style.display = "inline-block";
            if (badgeApp) badgeApp.style.display = "none";
            if (monSection) monSection.style.opacity = "1";
        } else {
            if (cardApp) {
                cardApp.style.border = "2px solid #32dbc9";
                cardApp.style.background = "#14172a";
                cardApp.style.boxShadow = "0 0 20px rgba(50, 219, 201, 0.25)";
            }
            if (cardDesk) {
                cardDesk.style.border = "1px solid #232b3e";
                cardDesk.style.background = "#090d18";
                cardDesk.style.boxShadow = "none";
            }
            if (badgeDesk) badgeDesk.style.display = "none";
            if (badgeApp) badgeApp.style.display = "inline-block";
            if (monSection) monSection.style.opacity = "0.5";
        }

        // Monitor buttons
        document.querySelectorAll(".monitor-btn").forEach(btn => {
            const m = btn.getAttribute("data-monitor");
            if (m === ds.monitor) {
                btn.style.background = "rgba(245, 26, 88, 0.2)";
                btn.style.borderColor = "#f51a58";
                btn.style.color = "#ffffff";
            } else {
                btn.style.background = "#182033";
                btn.style.borderColor = "#2d3852";
                btn.style.color = "#bac5da";
            }
        });

        // Position buttons
        document.querySelectorAll(".position-btn").forEach(btn => {
            const p = btn.getAttribute("data-pos");
            if (p === ds.default_position) {
                btn.style.background = "rgba(245, 26, 88, 0.2)";
                btn.style.borderColor = "#f51a58";
                btn.style.color = "#ffffff";
            } else {
                btn.style.background = "#182033";
                btn.style.borderColor = "#2d3852";
                btn.style.color = "#bac5da";
            }
        });

        // Window Perching switches
        const tPerch = document.getElementById("toggle-window-perch");
        if (tPerch) tPerch.checked = Boolean(ds.window_perching);

        const tHang = document.getElementById("toggle-title-hang");
        if (tHang) tHang.checked = Boolean(ds.title_hang);

        // Title Offset Slider
        const slOffset = document.getElementById("slider-title-offset");
        const lblOffset = document.getElementById("label-title-offset-val");
        if (slOffset) slOffset.value = ds.title_bar_offset || 28;
        if (lblOffset) lblOffset.innerText = `${ds.title_bar_offset || 28} px`;
    }

    function loadRunningApplications() {
        fetch("/api/running_applications")
            .then(res => res.json())
            .then(apps => {
                state.runningApps = apps;
                renderTargetApplications();
            })
            .catch(err => console.warn("[SpiderBuddy Bridge] Failed to load running apps:", err));
    }

    function renderTargetApplications() {
        const container = document.getElementById("target-apps-list");
        const badgeCount = document.getElementById("target-apps-count-badge");
        if (!container) return;

        const targetApps = (state.displaySettings && state.displaySettings.target_applications) || [];
        if (badgeCount) {
            badgeCount.innerText = `${targetApps.length} selected`;
        }

        container.innerHTML = "";

        const q = state.appSearchQuery.toLowerCase().trim();
        const appMap = new Map();

        function normAppKey(name) {
            if (!name) return "";
            return String(name).toLowerCase().replace(/\.exe$/i, "").replace(/[^a-z0-9]/g, "");
        }

        // 1. Target apps registered
        targetApps.forEach(app => {
            const rawName = typeof app === "string" ? app : (app.process_name || app.display_name);
            const key = normAppKey(rawName);
            appMap.set(key, {
                process_name: typeof app === "object" ? (app.process_name || rawName) : rawName,
                display_name: typeof app === "object" ? (app.display_name || rawName) : rawName,
                executable_path: typeof app === "object" ? (app.executable_path || "") : "",
                is_selected: true,
                is_running: false
            });
        });

        // 2. Running apps detected
        (state.runningApps || []).forEach(app => {
            const key = normAppKey(app.process_name) || normAppKey(app.display_name);
            if (appMap.has(key)) {
                const existing = appMap.get(key);
                existing.is_running = true;
                if (app.title) existing.title = app.title;
                if (app.executable_path && !existing.executable_path) existing.executable_path = app.executable_path;
            } else {
                appMap.set(key, {
                    process_name: app.process_name,
                    display_name: app.display_name || app.process_name,
                    executable_path: app.executable_path || "",
                    title: app.title || "",
                    is_selected: false,
                    is_running: true
                });
            }
        });

        let allRows = Array.from(appMap.values());
        if (q) {
            allRows = allRows.filter(a =>
                a.process_name.toLowerCase().includes(q) ||
                (a.display_name && a.display_name.toLowerCase().includes(q)) ||
                (a.title && a.title.toLowerCase().includes(q))
            );
        }

        // Sort: selected first, then running, then alphabetically
        allRows.sort((a, b) => {
            if (a.is_selected !== b.is_selected) return b.is_selected ? 1 : -1;
            if (a.is_running !== b.is_running) return b.is_running ? 1 : -1;
            return a.display_name.localeCompare(b.display_name);
        });

        if (allRows.length === 0) {
            container.innerHTML = `
                <div style="padding: 24px; text-align: center; color: #64748b; font-size: 13px;">
                    No applications match your filter. Type an executable above and click "+ Add App".
                </div>
            `;
            return;
        }

        allRows.forEach(app => {
            const row = document.createElement("div");
            row.className = "apple-glass-card-sub";
            row.style.display = "flex";
            row.style.alignItems = "center";
            row.style.justifyContent = "space-between";
            row.style.padding = "12px 16px";
            row.style.background = app.is_selected ? "rgba(255, 45, 85, 0.08)" : "rgba(10, 14, 25, 0.55)";
            row.style.border = app.is_selected ? "1px solid rgba(255, 45, 85, 0.38)" : "1px solid rgba(255, 255, 255, 0.07)";
            row.style.borderRadius = "14px";
            row.style.transition = "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)";

            const left = document.createElement("div");
            left.style.display = "flex";
            left.style.alignItems = "center";
            left.style.gap = "14px";

            // App icon indicator
            const iconBadge = document.createElement("div");
            iconBadge.style.width = "36px";
            iconBadge.style.height = "36px";
            iconBadge.style.borderRadius = "10px";
            iconBadge.style.background = app.is_selected ? "rgba(255, 45, 85, 0.18)" : "rgba(255, 255, 255, 0.06)";
            iconBadge.style.border = "1px solid " + (app.is_selected ? "rgba(255, 45, 85, 0.3)" : "rgba(255, 255, 255, 0.08)");
            iconBadge.style.display = "flex";
            iconBadge.style.alignItems = "center";
            iconBadge.style.justifyContent = "center";
            iconBadge.style.fontSize = "17px";
            iconBadge.innerText = app.is_selected ? "🎯" : "💻";
            left.appendChild(iconBadge);

            const meta = document.createElement("div");
            meta.style.display = "flex";
            meta.style.flexDirection = "column";
            meta.style.gap = "3px";

            const titleRow = document.createElement("div");
            titleRow.style.display = "flex";
            titleRow.style.alignItems = "center";
            titleRow.style.gap = "8px";

            const nameEl = document.createElement("span");
            nameEl.style.fontSize = "13.5px";
            nameEl.style.fontWeight = "600";
            nameEl.style.color = "#f8fafc";
            nameEl.style.letterSpacing = "-0.01em";
            nameEl.innerText = app.display_name;
            titleRow.appendChild(nameEl);

            if (app.is_running) {
                const runBadge = document.createElement("span");
                runBadge.className = "apple-pill-badge";
                runBadge.style.background = "rgba(48, 209, 88, 0.15)";
                runBadge.style.color = "#30D158";
                runBadge.style.border = "1px solid rgba(48, 209, 88, 0.35)";
                runBadge.style.fontSize = "9.5px";
                runBadge.style.fontWeight = "700";
                runBadge.style.padding = "2px 8px";
                runBadge.style.borderRadius = "9999px";
                runBadge.style.letterSpacing = "0.03em";
                runBadge.innerText = "RUNNING";
                titleRow.appendChild(runBadge);
            }
            meta.appendChild(titleRow);

            const subEl = document.createElement("span");
            subEl.style.fontSize = "11.5px";
            subEl.style.color = "rgba(220, 228, 245, 0.55)";
            subEl.innerText = app.process_name + (app.title && app.title !== app.process_name ? ` · ${app.title}` : "");
            meta.appendChild(subEl);
            left.appendChild(meta);

            // Right side: Toggle switch + Remove button
            const right = document.createElement("div");
            right.style.display = "flex";
            right.style.alignItems = "center";
            right.style.gap = "12px";

            const switchLabel = document.createElement("label");
            switchLabel.className = "spider-switch";
            const chk = document.createElement("input");
            chk.type = "checkbox";
            chk.checked = app.is_selected;
            chk.onchange = () => {
                if (chk.checked) {
                    sendAction("add_target_application", { application: app.process_name });
                } else {
                    sendAction("remove_target_application", { application: app.process_name });
                }
            };
            const slSpan = document.createElement("span");
            slSpan.className = "spider-slider";
            switchLabel.appendChild(chk);
            switchLabel.appendChild(slSpan);
            right.appendChild(switchLabel);

            if (app.is_selected) {
                const btnDel = document.createElement("button");
                btnDel.innerHTML = "✕";
                btnDel.className = "apple-button";
                btnDel.style.background = "rgba(255, 69, 58, 0.12)";
                btnDel.style.border = "1px solid rgba(255, 69, 58, 0.3)";
                btnDel.style.color = "#FF453A";
                btnDel.style.cursor = "pointer";
                btnDel.style.fontSize = "12px";
                btnDel.style.padding = "5px 10px";
                btnDel.style.borderRadius = "9999px";
                btnDel.title = "Remove from target applications";
                btnDel.onclick = () => {
                    sendAction("remove_target_application", { application: app.process_name });
                };
                right.appendChild(btnDel);
            }

            row.appendChild(left);
            row.appendChild(right);
            container.appendChild(row);
        });
    }

    // ── Load & Render Focus & Breaks Settings ──────────────────────────────
    function loadFocusSettings(overrideData) {
        if (overrideData && typeof overrideData === "object") {
            state.focusSettings = Object.assign(state.focusSettings, overrideData);
            updateFocusSettingsUI();
            return;
        }
        fetch("/api/focus_settings")
            .then(res => res.json())
            .then(data => {
                state.focusSettings = Object.assign(state.focusSettings, data);
                updateFocusSettingsUI();
            })
            .catch(err => console.warn("[SpiderBuddy Bridge] Failed to load focus settings:", err));
    }

    function updateFocusSettingsUI() {
        const fs = state.focusSettings;
        if (!fs) return;

        // 1. Focus Mode Switch
        const tFocus = document.getElementById("toggle-focus-mode");
        if (tFocus) tFocus.checked = Boolean(fs.focus_mode);

        // 2. Timer Clock & Badge
        const clk = document.getElementById("focus-timer-clock");
        const bdg = document.getElementById("focus-timer-badge");
        if (fs.focus_timer_active) {
            const rem = Math.max(0, fs.focus_time_remaining || 0);
            const m = Math.floor(rem / 60);
            const s = Math.floor(rem % 60);
            const timeStr = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
            if (clk) {
                clk.innerText = timeStr;
                clk.style.color = "#38bdf8";
                clk.style.textShadow = "0 0 24px rgba(56, 189, 248, 0.55)";
            }
            const isBreak = rem === 0;
            if (bdg) {
                bdg.innerText = !isBreak ? "🛡️ Guardian Focus: Active" : "☕ Break Time (5 Min)";
                bdg.style.color = !isBreak ? "#38bdf8" : "#22c55e";
                bdg.style.borderColor = !isBreak ? "rgba(56, 189, 248, 0.4)" : "rgba(34, 197, 94, 0.4)";
                bdg.style.background = !isBreak ? "rgba(56, 189, 248, 0.12)" : "rgba(34, 197, 94, 0.12)";
            }
        } else {
            if (clk) {
                clk.innerText = "25:00";
                clk.style.color = "#64748b";
                clk.style.textShadow = "none";
            }
            if (bdg) {
                bdg.innerText = "🛡️ Guardian Mode: Ready";
                bdg.style.color = "#94a3b8";
                bdg.style.borderColor = "rgba(148, 163, 184, 0.3)";
                bdg.style.background = "rgba(148, 163, 184, 0.08)";
            }
        }

        // 3. Eye Break Web Alert Switch & Slider
        const tEye = document.getElementById("toggle-eye-break");
        if (tEye) tEye.checked = Boolean(fs.enable_eye_break_alert);

        const sEye = document.getElementById("slider-eye-interval");
        const lEye = document.getElementById("label-eye-interval-val");
        if (sEye) sEye.value = fs.eye_break_minutes || 10;
        if (lEye) lEye.innerText = `${fs.eye_break_minutes || 10} min`;

        // Update progress bar
        const continuousSec = fs.continuous_work_seconds || 0;
        const limitSec = (fs.eye_break_minutes || 10) * 60;
        const curM = Math.floor(continuousSec / 60);
        const curS = Math.floor(continuousSec % 60);
        const statusEl = document.getElementById("eye-break-status-text");
        const barEl = document.getElementById("eye-break-progress-bar");
        if (statusEl) {
            statusEl.innerText = `💧 Continuous Work: ${curM}m ${curS}s / ${fs.eye_break_minutes || 10}m • Focus Timer: ${fs.focus_timer_active ? "Active" : "Inactive"}`;
        }
        if (barEl) {
            const pct = Math.min(100, Math.round((continuousSec / limitSec) * 100));
            barEl.style.width = `${pct}%`;
        }

        // 4. Inactivity Sliders
        const sRelax = document.getElementById("slider-inactivity-relax");
        const lRelax = document.getElementById("label-inactivity-relax-val");
        if (sRelax) sRelax.value = fs.inactivity_relax_minutes || 2;
        if (lRelax) lRelax.innerText = `${fs.inactivity_relax_minutes || 2} min`;

        const sSit = document.getElementById("slider-inactivity-sit");
        const lSit = document.getElementById("label-inactivity-sit-val");
        if (sSit) sSit.value = fs.inactivity_sit_minutes || 5;
        if (lSit) lSit.innerText = `${fs.inactivity_sit_minutes || 5} min`;

        const sSleep = document.getElementById("slider-inactivity-sleep");
        const lSleep = document.getElementById("label-inactivity-sleep-val");
        if (sSleep) sSleep.value = fs.inactivity_sleep_minutes || 10;
        if (lSleep) lSleep.innerText = `${fs.inactivity_sleep_minutes || 10} min`;
    }

    // ── Load & Render Controls Settings ────────────────────────────────────
    function loadControlSettings() {
        fetch("/api/control_settings")
            .then(res => res.json())
            .then(data => {
                state.controlSettings = Object.assign(state.controlSettings, data);
                updateControlSettingsUI();
            })
            .catch(err => console.warn("[SpiderBuddy Bridge] Failed to load control settings:", err));
    }

    function updateControlSettingsUI() {
        const cs = state.controlSettings;
        if (!cs) return;

        // 1. Hotkeys master & modifier switches
        const tMaster = document.getElementById("toggle-master-hotkeys");
        if (tMaster) tMaster.checked = Boolean(cs.enable_animation_hotkeys);

        const tMod = document.getElementById("toggle-hotkeys-modifier");
        if (tMod) tMod.checked = Boolean(cs.hotkeys_require_modifier);

        // Render hotkeys grid
        if (Array.isArray(cs.hotkeys)) {
            renderHotkeysGrid(cs.hotkeys);
        }

        // 2. Locomotion WASD
        const tWasd = document.getElementById("toggle-wasd-enabled");
        if (tWasd) tWasd.checked = Boolean(cs.wasd_movement_enabled);

        const tPin = document.getElementById("toggle-wasd-pin");
        if (tPin) tPin.checked = Boolean(cs.wasd_static_pin);

        const sSpeed = document.getElementById("slider-movement-speed");
        const lSpeed = document.getElementById("label-movement-speed-val");
        if (sSpeed) sSpeed.value = cs.movement_speed || 3.0;
        if (lSpeed) lSpeed.innerText = `${Number(cs.movement_speed || 3.0).toFixed(1)}x`;

        // 3. Mouse interactions & Physics
        const tFling = document.getElementById("toggle-fling-physics");
        if (tFling) tFling.checked = Boolean(cs.enable_fling_physics !== undefined ? cs.enable_fling_physics : true);
        updateFlingPhysicsUI(Boolean(cs.enable_fling_physics !== undefined ? cs.enable_fling_physics : true));

        const tWebShoot = document.getElementById("toggle-web-shoot-cursor");
        if (tWebShoot) tWebShoot.checked = Boolean(cs.enable_web_shoot_cursor !== undefined ? cs.enable_web_shoot_cursor : true);

        const tStickyNotes = document.getElementById("toggle-sticky-notes-enabled");
        if (tStickyNotes) tStickyNotes.checked = Boolean(cs.enable_sticky_notes !== undefined ? cs.enable_sticky_notes : true);
        updateStickyNotesMasterToggleUI(Boolean(cs.enable_sticky_notes !== undefined ? cs.enable_sticky_notes : true));

        const tMouse = document.getElementById("toggle-mouse-following");
        if (tMouse) tMouse.checked = Boolean(cs.enable_mouse_following !== undefined ? cs.enable_mouse_following : true);

        const tDodge = document.getElementById("toggle-spider-sense");
        if (tDodge) tDodge.checked = Boolean(cs.enable_spider_sense_dodging);

        const tClick = document.getElementById("toggle-click-through");
        if (tClick) tClick.checked = Boolean(cs.click_through);

        const sRad = document.getElementById("slider-cursor-radius");
        const lRad = document.getElementById("label-cursor-radius-val");
        if (sRad) sRad.value = cs.cursor_radius || 180;
        if (lRad) lRad.innerText = `${cs.cursor_radius || 180} px`;

        // 4. Sound & dialogue
        const tSnd = document.getElementById("toggle-sound-effects");
        if (tSnd) tSnd.checked = Boolean(cs.sound_enabled);

        const sVol = document.getElementById("slider-sound-volume");
        const lVol = document.getElementById("label-sound-volume-val");
        if (sVol) sVol.value = cs.sound_volume !== undefined ? cs.sound_volume : 25;
        if (lVol) lVol.innerText = `${cs.sound_volume !== undefined ? cs.sound_volume : 25}%`;

        const tComic = document.getElementById("toggle-comic-bubbles");
        if (tComic) tComic.checked = Boolean(cs.enable_comic_bubbles);

        updatePacingButtons(cs.preset || "normal");
    }

    function updatePacingButtons(activePreset) {
        document.querySelectorAll(".pacing-preset-btn").forEach(btn => {
            const p = btn.getAttribute("data-pacing");
            if (p === activePreset) {
                btn.style.background = "rgba(245, 26, 88, 0.15)";
                btn.style.borderColor = "#f51a58";
                btn.style.color = "#fff";
            } else {
                btn.style.background = "#182033";
                btn.style.borderColor = "#2d3852";
                btn.style.color = "#bac5da";
            }
        });
    }

    function renderHotkeysGrid(hotkeys) {
        const grid = document.getElementById("hotkeys-grid-container");
        if (!grid) return;
        grid.innerHTML = "";

        if (!Array.isArray(hotkeys) || hotkeys.length === 0) {
            grid.innerHTML = `<div style="grid-column: 1 / -1; color: #8e9bb3; font-size: 13px; text-align: center; padding: 18px;">No number key shortcuts loaded.</div>`;
            return;
        }

        hotkeys.forEach(hk => {
            const card = document.createElement("div");
            card.className = "apple-glass-card-sub";
            card.style.padding = "14px 18px";
            card.style.display = "flex";
            card.style.alignItems = "center";
            card.style.justifyContent = "space-between";
            card.style.gap = "14px";
            card.style.borderRadius = "14px";
            card.style.transition = "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)";

            card.innerHTML = `
                <div style="display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0;">
                    <span style="background: rgba(255, 45, 85, 0.15); border: 1px solid rgba(255, 45, 85, 0.35); color: #FF2D55; font-family: -apple-system, BlinkMacSystemFont, monospace; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 8px; flex-shrink: 0; box-shadow: 0 2px 6px rgba(0,0,0,0.25);">Key ${hk.key}</span>
                    <div style="display: flex; flex-direction: column; gap: 2px; overflow: hidden;">
                        <span style="font-weight: 600; color: #f8fafc; font-size: 14px; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; letter-spacing: -0.01em;">${hk.title}</span>
                        <span style="font-size: 11.5px; color: #00D2FF; white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">${hk.quote || hk.action}</span>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 12px;">
                    <button class="test-hotkey-btn apple-button" data-act="${hk.action}" data-quote="${(hk.quote || '').replace(/"/g, '&quot;')}" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: #f1f5f9; border-radius: 9999px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer;">▶ Test</button>
                    <label class="spider-switch" style="flex-shrink: 0;">
                        <input type="checkbox" class="toggle-number-key" data-key="${hk.key}" ${hk.enabled ? "checked" : ""} />
                        <span class="spider-slider"></span>
                    </label>
                </div>
            `;

            const btnTest = card.querySelector(".test-hotkey-btn");
            if (btnTest) {
                btnTest.addEventListener("click", () => {
                    sendAction("test_hotkey", {
                        activity: hk.action,
                        quote: hk.quote
                    });
                });
            }

            const chkKey = card.querySelector(".toggle-number-key");
            if (chkKey) {
                chkKey.addEventListener("change", (e) => {
                    sendAction("toggle_number_key", {
                        key: hk.key,
                        enabled: e.target.checked
                    });
                });
            }

            grid.appendChild(card);
        });
    }


    // ── Load & Render Application Settings (Apple Design System) ─────────
    function loadAppSettings() {
        const revision = appSettingsRevision;
        const request = ++appSettingsRequest;
        fetch("/api/app_settings")
            .then(res => res.json())
            .then(data => {
                // Ignore a response started before the user's latest edit or
                // superseded by a newer refresh. Never undo a fresh selection.
                if (revision !== appSettingsRevision || request !== appSettingsRequest) return;
                state.appSettings = Object.assign(state.appSettings || {}, data);
                updateAppSettingsUI();
            })
            .catch(err => console.warn("[SpiderBuddy Bridge] Failed to load app settings:", err));
    }

    function updateAppSettingsUI() {
        const s = state.appSettings;
        if (!s) return;

        // 1. Theme
        updateThemeButtons(s.theme || "dark");

        // 2. FPS
        updateFpsButtons(s.display_fps || 0);

        // 3. Animation Speed
        updateAnimSpeedButtons(s.animation_speed || 1.0);

        // 4. Windows Integration
        const tStartMin = document.getElementById("toggle-start-minimized");
        if (tStartMin) tStartMin.checked = Boolean(s.start_minimized);

        const tStartup = document.getElementById("toggle-run-on-startup");
        if (tStartup) tStartup.checked = Boolean(s.run_on_startup);

        const tAlwaysOnTop = document.getElementById("toggle-always-on-top");
        if (tAlwaysOnTop) tAlwaysOnTop.checked = Boolean(s.always_on_top);

        const tClick = document.getElementById("toggle-settings-click-through");
        if (tClick) tClick.checked = Boolean(s.click_through);

        updateSettingsMonitorButtons(s.monitor || "primary");
        updateSettingsPositionButtons(s.default_position || "bottom_right");

        // 5. Appearance & Graphics Engine
        const tAuthTwos = document.getElementById("toggle-authentic-twos");
        if (tAuthTwos) tAuthTwos.checked = Boolean(s.authentic_twos);

        const sSetSize = document.getElementById("slider-settings-size");
        const lSetSize = document.getElementById("label-settings-size-val");
        if (sSetSize) sSetSize.value = s.companion_size || 200;
        if (lSetSize) lSetSize.innerText = `${s.companion_size || 200} px`;

        const sSetOp = document.getElementById("slider-settings-opacity");
        const lSetOp = document.getElementById("label-settings-opacity-val");
        if (sSetOp) sSetOp.value = s.companion_opacity !== undefined ? s.companion_opacity : 100;
        if (lSetOp) lSetOp.innerText = `${s.companion_opacity !== undefined ? s.companion_opacity : 100}%`;

        // 6. Autonomy, Pacing & Reactions
        const tAuto = document.getElementById("toggle-settings-auto-anim");
        if (tAuto) tAuto.checked = Boolean(s.automatic_animations);

        updateSettingsPresetButtons(s.preset || "normal");

        const sSetSpd = document.getElementById("slider-settings-speed");
        const lSetSpd = document.getElementById("label-settings-speed-val");
        if (sSetSpd) sSetSpd.value = s.movement_speed || 3.0;
        if (lSetSpd) lSetSpd.innerText = `${Number(s.movement_speed || 3.0).toFixed(1)}x`;

        const tDodge = document.getElementById("toggle-settings-dodge");
        if (tDodge) tDodge.checked = Boolean(s.enable_spider_sense_dodging);

        const tFollow = document.getElementById("toggle-settings-mouse-follow");
        if (tFollow) tFollow.checked = Boolean(s.enable_mouse_following !== undefined ? s.enable_mouse_following : true);

        const tFling = document.getElementById("toggle-settings-fling-physics");
        if (tFling) tFling.checked = Boolean(s.enable_fling_physics !== undefined ? s.enable_fling_physics : true);
        updateFlingPhysicsUI(Boolean(s.enable_fling_physics !== undefined ? s.enable_fling_physics : true));

        const tWebShoot = document.getElementById("toggle-settings-web-shoot-cursor");
        if (tWebShoot) tWebShoot.checked = Boolean(s.enable_web_shoot_cursor !== undefined ? s.enable_web_shoot_cursor : true);

        const tSticky = document.getElementById("toggle-settings-sticky-notes");
        if (tSticky) tSticky.checked = Boolean(s.enable_sticky_notes !== undefined ? s.enable_sticky_notes : true);
        updateStickyNotesMasterToggleUI(Boolean(s.enable_sticky_notes !== undefined ? s.enable_sticky_notes : true));

        const tBubbles = document.getElementById("toggle-settings-comic-bubbles");
        if (tBubbles) tBubbles.checked = Boolean(s.enable_comic_bubbles);

        const tHeavy = document.getElementById("toggle-settings-heavy-load");
        if (tHeavy) tHeavy.checked = Boolean(s.enable_heavy_load_scene);

        const tMusic = document.getElementById("toggle-settings-music-sync");
        if (tMusic) tMusic.checked = Boolean(s.enable_audio_beat_bobbing);

        const tBat = document.getElementById("toggle-settings-battery");
        if (tBat) tBat.checked = Boolean(s.enable_battery_charging_reaction);

        const tGlitch = document.getElementById("toggle-settings-suit-glitch");
        if (tGlitch) tGlitch.checked = Boolean(s.enable_suit_glitch);

        // 7. Audio & SFX
        const tSnd = document.getElementById("toggle-settings-sound");
        if (tSnd) tSnd.checked = Boolean(s.sound_enabled);

        const sSndVol = document.getElementById("slider-settings-sound-vol");
        const lSndVol = document.getElementById("label-settings-sound-vol-val");
        if (sSndVol) sSndVol.value = s.sound_volume !== undefined ? s.sound_volume : 25;
        if (lSndVol) lSndVol.innerText = `${s.sound_volume !== undefined ? s.sound_volume : 25}%`;

        // 8. Health & Vision Eye Breaks
        const tEye = document.getElementById("toggle-settings-eye-alert");
        if (tEye) tEye.checked = Boolean(s.enable_eye_break_alert);

        updateSettingsIntervalButtons(s.eye_break_minutes !== undefined ? s.eye_break_minutes : 10);

        // 9. Keyboard Shortcuts & WASD
        const tHk = document.getElementById("toggle-settings-hotkeys");
        if (tHk) tHk.checked = Boolean(s.enable_animation_hotkeys);

        const tHkMod = document.getElementById("toggle-settings-hotkeys-mod");
        if (tHkMod) tHkMod.checked = Boolean(s.hotkeys_require_modifier);

        const tWasd = document.getElementById("toggle-settings-wasd");
        if (tWasd) tWasd.checked = Boolean(s.wasd_movement_enabled);

        const tWasdPin = document.getElementById("toggle-settings-wasd-pin");
        if (tWasdPin) tWasdPin.checked = Boolean(s.wasd_static_pin);

        // 10. Diagnostics, Storage & About
        const pathEl = document.getElementById("settings-config-path-text");
        if (pathEl && s.config_path) {
            pathEl.innerText = s.config_path;
            pathEl.title = s.config_path;
        }

        const cacheEl = document.getElementById("settings-cache-size-text");
        if (cacheEl && s.cache_size) {
            cacheEl.innerText = s.cache_size;
        }

        const verEl = document.getElementById("settings-app-version-badge");
        if (verEl && s.version) {
            verEl.innerText = s.version;
        }

        const platEl = document.getElementById("settings-platform-badge");
        if (platEl && s.platform) {
            platEl.innerText = s.platform;
        }

        const engEl = document.getElementById("settings-engine-badge");
        if (engEl && s.engine) {
            engEl.innerText = s.engine;
        }
    }

    function updateThemeButtons(activeTheme) {
        document.documentElement.dataset.theme = activeTheme;
        document.documentElement.style.colorScheme = activeTheme === "light" ? "light" : "dark";
        document.querySelectorAll(".theme-select-btn").forEach(btn => {
            const t = btn.getAttribute("data-theme");
            if (t === activeTheme) {
                btn.style.setProperty("background", "var(--apple-crimson-gradient)", "important");
                btn.style.setProperty("border-color", "rgba(255, 45, 85, 0.5)", "important");
                btn.style.setProperty("color", "#fff", "important");
                btn.style.setProperty("box-shadow", "0 2px 10px var(--apple-crimson-glow)", "important");
                btn.style.setProperty("font-weight", "600", "important");
            } else {
                btn.style.setProperty("background", "rgba(255, 255, 255, 0.08)", "important");
                btn.style.setProperty("border-color", "var(--apple-border)", "important");
                btn.style.setProperty("color", "var(--apple-text-secondary)", "important");
                btn.style.setProperty("box-shadow", "none", "important");
                btn.style.setProperty("font-weight", "500", "important");
            }
        });
        const lbl = document.querySelector('.framer-121j3ed p');
        if (lbl) lbl.innerText = activeTheme === "light" ? "Switch to dark theme" : "Switch to light theme";
    }

    function updateFpsButtons(activeFps) {
        document.querySelectorAll(".fps-select-btn").forEach(btn => {
            const f = parseInt(btn.getAttribute("data-fps"));
            if (f === activeFps) {
                btn.style.setProperty("background", "var(--apple-crimson-gradient)", "important");
                btn.style.setProperty("border-color", "rgba(255, 45, 85, 0.5)", "important");
                btn.style.setProperty("color", "#fff", "important");
                btn.style.setProperty("box-shadow", "0 2px 10px var(--apple-crimson-glow)", "important");
                btn.style.setProperty("font-weight", "600", "important");
            } else {
                btn.style.setProperty("background", "rgba(255, 255, 255, 0.08)", "important");
                btn.style.setProperty("border-color", "var(--apple-border)", "important");
                btn.style.setProperty("color", "var(--apple-text-secondary)", "important");
                btn.style.setProperty("box-shadow", "none", "important");
                btn.style.setProperty("font-weight", "500", "important");
            }
        });
    }

    function updateAnimSpeedButtons(activeSpeed) {
        document.querySelectorAll(".anim-speed-btn").forEach(btn => {
            const spd = parseFloat(btn.getAttribute("data-speed"));
            if (Math.abs(spd - activeSpeed) < 0.05) {
                btn.style.setProperty("background", "var(--apple-crimson-gradient)", "important");
                btn.style.setProperty("border-color", "rgba(255, 45, 85, 0.5)", "important");
                btn.style.setProperty("color", "#fff", "important");
                btn.style.setProperty("box-shadow", "0 2px 10px var(--apple-crimson-glow)", "important");
                btn.style.setProperty("font-weight", "600", "important");
            } else {
                btn.style.setProperty("background", "rgba(255, 255, 255, 0.08)", "important");
                btn.style.setProperty("border-color", "var(--apple-border)", "important");
                btn.style.setProperty("color", "var(--apple-text-secondary)", "important");
                btn.style.setProperty("box-shadow", "none", "important");
                btn.style.setProperty("font-weight", "500", "important");
            }
        });
    }

    function updateSettingsMonitorButtons(activeMon) {
        document.querySelectorAll(".settings-mon-btn").forEach(btn => {
            const m = btn.getAttribute("data-mon");
            if (m === activeMon) {
                btn.style.setProperty("background", "var(--apple-crimson-gradient)", "important");
                btn.style.setProperty("border-color", "rgba(255, 45, 85, 0.5)", "important");
                btn.style.setProperty("color", "#fff", "important");
                btn.style.setProperty("box-shadow", "0 2px 10px var(--apple-crimson-glow)", "important");
                btn.style.setProperty("font-weight", "600", "important");
            } else {
                btn.style.setProperty("background", "rgba(255, 255, 255, 0.08)", "important");
                btn.style.setProperty("border-color", "var(--apple-border)", "important");
                btn.style.setProperty("color", "var(--apple-text-secondary)", "important");
                btn.style.setProperty("box-shadow", "none", "important");
                btn.style.setProperty("font-weight", "500", "important");
            }
        });
    }

    function updateSettingsPositionButtons(activePos) {
        document.querySelectorAll(".settings-pos-btn").forEach(btn => {
            const p = btn.getAttribute("data-pos");
            if (p === activePos) {
                btn.style.setProperty("background", "var(--apple-crimson-gradient)", "important");
                btn.style.setProperty("border-color", "rgba(255, 45, 85, 0.5)", "important");
                btn.style.setProperty("color", "#fff", "important");
                btn.style.setProperty("box-shadow", "0 2px 10px var(--apple-crimson-glow)", "important");
                btn.style.setProperty("font-weight", "600", "important");
            } else {
                btn.style.setProperty("background", "rgba(255, 255, 255, 0.08)", "important");
                btn.style.setProperty("border-color", "var(--apple-border)", "important");
                btn.style.setProperty("color", "var(--apple-text-secondary)", "important");
                btn.style.setProperty("box-shadow", "none", "important");
                btn.style.setProperty("font-weight", "500", "important");
            }
        });
    }

    function updateSettingsPresetButtons(activePreset) {
        document.querySelectorAll(".settings-preset-btn").forEach(btn => {
            const p = btn.getAttribute("data-preset");
            if (p === activePreset) {
                btn.style.setProperty("background", "var(--apple-crimson-gradient)", "important");
                btn.style.setProperty("border-color", "rgba(255, 45, 85, 0.5)", "important");
                btn.style.setProperty("color", "#fff", "important");
                btn.style.setProperty("box-shadow", "0 2px 10px var(--apple-crimson-glow)", "important");
                btn.style.setProperty("font-weight", "600", "important");
            } else {
                btn.style.setProperty("background", "rgba(255, 255, 255, 0.08)", "important");
                btn.style.setProperty("border-color", "var(--apple-border)", "important");
                btn.style.setProperty("color", "var(--apple-text-secondary)", "important");
                btn.style.setProperty("box-shadow", "none", "important");
                btn.style.setProperty("font-weight", "500", "important");
            }
        });
    }

    function updateSettingsIntervalButtons(activeMins) {
        document.querySelectorAll(".settings-interval-btn").forEach(btn => {
            const m = parseFloat(btn.getAttribute("data-mins"));
            if (Math.abs(m - parseFloat(activeMins)) < 0.1) {
                btn.style.setProperty("background", "var(--apple-crimson-gradient)", "important");
                btn.style.setProperty("border-color", "rgba(255, 45, 85, 0.5)", "important");
                btn.style.setProperty("color", "#fff", "important");
                btn.style.setProperty("box-shadow", "0 2px 10px var(--apple-crimson-glow)", "important");
                btn.style.setProperty("font-weight", "600", "important");
            } else {
                btn.style.setProperty("background", "rgba(255, 255, 255, 0.08)", "important");
                btn.style.setProperty("border-color", "var(--apple-border)", "important");
                btn.style.setProperty("color", "var(--apple-text-secondary)", "important");
                btn.style.setProperty("box-shadow", "none", "important");
                btn.style.setProperty("font-weight", "500", "important");
            }
        });
    }

    // ── Load & Render Characters ──────────────────────────────────────────
    function loadCharacters() {
        const grid = document.getElementById("characters-gallery-grid");
        if (!grid) return;

        window.SpiderBuddy.setTuning(state.companionSize, state.companionOpacity);

        fetch("/api/characters")
            .then(res => res.json())
            .then(characters => {
                const charsStr = JSON.stringify(characters);
                if (state._lastCharsStr === charsStr && grid.children.length > 0) {
                    return;
                }
                state._lastCharsStr = charsStr;
                state.characters = characters;
                const active = characters.find(c => c.selected);
                if (active) {
                    state.activeCharacterId = active.id;
                }
                renderCharacterCards(characters);
            })
            .catch(() => {
                // Fallback default characters list if offline
                const fallback = [
                    { id: "tom_holland", name: "Tom Holland Spider-Man", suit: "Integrated Red, Blue & Gold Stark Suit", personality: "Tech-savvy · Energetic", selected: true, preview_url: "/api/character_image/tom_holland.png" },
                    { id: "miles_morales", name: "Miles Morales", suit: "Classic Black & Red Suit", personality: "Bio-Electric · Streetwise", selected: false, preview_url: "/api/character_image/miles_morales.png" },
                    { id: "spider_2", name: "Spider-Man 2", suit: "Advanced White Spider Suit", personality: "Experienced · Acrobatic", selected: false, preview_url: "/api/character_image/spider_2.png" },
                    { id: "gwen_stacy_1", name: "Ghost-Spider (Gwen)", suit: "Hooded Ghost-Spider Suit", personality: "Agile · Rhythmic", selected: false, preview_url: "/api/character_image/gwen_stacy_1.png" }
                ];
                renderCharacterCards(fallback);
            });
    }

    function renderCharacterCards(characters) {
        const grid = document.getElementById("characters-gallery-grid");
        if (!grid) return;

        grid.innerHTML = "";

        const PROTECTED_IDS = new Set(["tom_holland", "miles_morales", "gwen_stacy_1", "gwen_stacy", "spider_2"]);

        characters.forEach(char => {
            const isSelected = Boolean(char.selected || char.id === state.activeCharacterId);
            const canDelete = Boolean(char.can_delete && !PROTECTED_IDS.has(char.id));
            const card = document.createElement("div");
            card.className = "apple-glass-card" + (isSelected ? " selected" : "");
            card.style.background = isSelected ? "rgba(255, 45, 85, 0.08)" : "rgba(19, 23, 36, 0.65)";
            card.style.backdropFilter = "blur(14px)";
            card.style.webkitBackdropFilter = "blur(14px)";
            card.style.border = isSelected ? "1.5px solid rgba(255, 45, 85, 0.85)" : "1px solid rgba(255, 255, 255, 0.08)";
            card.style.borderTop = isSelected ? "1.5px solid rgba(255, 45, 85, 0.95)" : "1px solid rgba(255, 255, 255, 0.18)";
            card.style.borderRadius = "20px";
            card.style.padding = "20px";
            card.style.display = "flex";
            card.style.flexDirection = "column";
            card.style.gap = "14px";
            card.style.boxShadow = isSelected ? "0 14px 34px -8px rgba(255, 45, 85, 0.35)" : "0 12px 30px -8px rgba(0, 0, 0, 0.5)";
            card.style.transition = "transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease, box-shadow 0.25s ease";
            card.style.cursor = "pointer";

            card.addEventListener("mouseenter", () => {
                card.style.transform = "translateY(-4px)";
                if (!isSelected) {
                    card.style.borderColor = "rgba(255, 255, 255, 0.25)";
                    card.style.boxShadow = "0 18px 36px -8px rgba(0, 0, 0, 0.65)";
                }
            });
            card.addEventListener("mouseleave", () => {
                card.style.transform = "translateY(0)";
                if (!isSelected) {
                    card.style.borderColor = "rgba(255, 255, 255, 0.08)";
                    card.style.boxShadow = "0 12px 30px -8px rgba(0, 0, 0, 0.5)";
                }
            });

            // Character Pedestal Circle
            const previewContainer = document.createElement("div");
            previewContainer.style.width = "100%";
            previewContainer.style.height = "156px";
            previewContainer.style.borderRadius = "16px";
            previewContainer.style.background = isSelected
                ? "radial-gradient(circle at 50% 30%, rgba(255, 45, 85, 0.22) 0%, rgba(12, 16, 28, 0.92) 100%)"
                : "radial-gradient(circle at 50% 30%, rgba(255, 255, 255, 0.08) 0%, rgba(12, 16, 28, 0.92) 100%)";
            previewContainer.style.border = isSelected ? "1px solid rgba(255, 45, 85, 0.35)" : "1px solid rgba(255, 255, 255, 0.08)";
            previewContainer.style.display = "flex";
            previewContainer.style.alignItems = "center";
            previewContainer.style.justifyContent = "center";
            previewContainer.style.position = "relative";
            previewContainer.style.overflow = "hidden";

            const img = document.createElement("img");
            img.src = char.preview_url || `/api/character_image/${char.id}.png`;
            img.alt = char.name;
            img.style.maxHeight = "134px";
            img.style.maxWidth = "134px";
            img.style.objectFit = "contain";
            img.style.filter = isSelected ? "drop-shadow(0 0 16px rgba(255, 45, 85, 0.5))" : "drop-shadow(0 0 10px rgba(0, 0, 0, 0.6))";
            previewContainer.appendChild(img);

            // Delete Button (ONLY for custom characters, never for the 4 default companions)
            if (canDelete) {
                const delBtn = document.createElement("button");
                delBtn.className = "apple-char-delete-btn";
                delBtn.title = `Delete ${char.name}`;
                delBtn.setAttribute("aria-label", `Delete ${char.name}`);
                delBtn.innerHTML = `
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        <line x1="10" y1="11" x2="10" y2="17"></line>
                        <line x1="14" y1="11" x2="14" y2="17"></line>
                    </svg>
                `;
                delBtn.style.position = "absolute";
                delBtn.style.top = "10px";
                delBtn.style.right = "10px";
                delBtn.style.width = "32px";
                delBtn.style.height = "32px";
                delBtn.style.borderRadius = "50%";
                delBtn.style.background = "rgba(20, 24, 38, 0.82)";
                delBtn.style.backdropFilter = "blur(10px)";
                delBtn.style.webkitBackdropFilter = "blur(10px)";
                delBtn.style.border = "1px solid rgba(255, 69, 105, 0.45)";
                delBtn.style.color = "#ff4d6d";
                delBtn.style.display = "flex";
                delBtn.style.alignItems = "center";
                delBtn.style.justifyContent = "center";
                delBtn.style.cursor = "pointer";
                delBtn.style.zIndex = "10";
                delBtn.style.transition = "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)";
                delBtn.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.4)";

                delBtn.addEventListener("mouseenter", (e) => {
                    e.stopPropagation();
                    delBtn.style.background = "#FF2D55";
                    delBtn.style.borderColor = "#FF2D55";
                    delBtn.style.color = "#ffffff";
                    delBtn.style.transform = "scale(1.12)";
                    delBtn.style.boxShadow = "0 4px 16px rgba(255, 45, 85, 0.6)";
                });

                delBtn.addEventListener("mouseleave", (e) => {
                    e.stopPropagation();
                    delBtn.style.background = "rgba(20, 24, 38, 0.82)";
                    delBtn.style.borderColor = "rgba(255, 69, 105, 0.45)";
                    delBtn.style.color = "#ff4d6d";
                    delBtn.style.transform = "scale(1)";
                    delBtn.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.4)";
                });

                delBtn.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    const confirmed = window.confirm(`Are you sure you want to delete "${char.name}"?\nThis cannot be undone.`);
                    if (!confirmed) return;

                    delBtn.disabled = true;
                    delBtn.style.opacity = "0.4";
                    state._lastCharsStr = null;

                    try {
                        if (typeof addToBin === "function") {
                            addToBin(char);
                        }
                        await sendAction("delete_character", { character_id: char.id });
                    } catch (err) {
                        console.error("Failed to delete character:", err);
                    }

                    setTimeout(() => {
                        state._lastCharsStr = null;
                        if (window.SpiderBuddy && window.SpiderBuddy.loadCharacters) {
                            window.SpiderBuddy.loadCharacters();
                        } else {
                            loadCharacters();
                        }
                    }, 150);
                });

                previewContainer.appendChild(delBtn);
            }

            // Character Info
            const info = document.createElement("div");
            info.style.display = "flex";
            info.style.flexDirection = "column";
            info.style.gap = "4px";

            const name = document.createElement("h4");
            name.style.fontSize = "15.5px";
            name.style.fontWeight = "600";
            name.style.color = "#f8fafc";
            name.style.letterSpacing = "-0.012em";
            name.style.margin = "0";
            name.innerText = char.name;

            if (canDelete) {
                const titleRow = document.createElement("div");
                titleRow.style.display = "flex";
                titleRow.style.alignItems = "center";
                titleRow.style.justifyContent = "space-between";
                titleRow.appendChild(name);

                const badge = document.createElement("span");
                badge.innerText = "Custom";
                badge.style.fontSize = "10.5px";
                badge.style.fontWeight = "600";
                badge.style.padding = "2px 8px";
                badge.style.borderRadius = "9999px";
                badge.style.background = "rgba(255, 45, 85, 0.12)";
                badge.style.border = "1px solid rgba(255, 45, 85, 0.3)";
                badge.style.color = "#ff4d6d";
                titleRow.appendChild(badge);

                info.appendChild(titleRow);
            } else {
                info.appendChild(name);
            }

            const suit = document.createElement("p");
            suit.style.fontSize = "12.5px";
            suit.style.color = "rgba(220, 228, 245, 0.65)";
            suit.style.margin = "0";
            suit.style.whiteSpace = "nowrap";
            suit.style.overflow = "hidden";
            suit.style.textOverflow = "ellipsis";
            suit.innerText = char.suit || "Classic Suit";

            info.appendChild(suit);

            // Action Button
            const btn = document.createElement("button");
            btn.className = "apple-button" + (isSelected ? " active-companion-btn" : "");
            btn.style.width = "100%";
            btn.style.padding = "9px 0";
            btn.style.borderRadius = "9999px";
            btn.style.fontSize = "13px";
            btn.style.fontWeight = "600";
            btn.style.cursor = "pointer";

            if (isSelected) {
                btn.innerText = "✓ Active Companion";
                btn.style.background = "#FF2D55";
                btn.style.color = "#ffffff";
                btn.style.border = "none";
                btn.style.boxShadow = "0 4px 14px rgba(255, 45, 85, 0.4)";
            } else {
                btn.innerText = "Select Companion";
                btn.style.background = "rgba(255, 255, 255, 0.08)";
                btn.style.color = "#f1f5f9";
                btn.style.border = "1px solid rgba(255, 255, 255, 0.15)";
            }

            const selectHandler = () => {
                state.activeCharacterId = char.id;
                sendAction("select_character", { character_id: char.id });
                renderCharacterCards(characters.map(c => ({ ...c, selected: c.id === char.id })));
            };

            card.addEventListener("click", selectHandler);
            card.addEventListener("dblclick", (e) => {
                if (e.target.closest && e.target.closest(".apple-char-delete-btn")) return;
                e.preventDefault();
                e.stopPropagation();
                const charImg = char.preview_url || `/api/character_image/${char.id}.png`;
                openImageLightbox(charImg, `${char.name} • ${char.suit || "Companion"}`);
            });
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                selectHandler();
            });

            card.appendChild(previewContainer);
            card.appendChild(info);
            card.appendChild(btn);
            grid.appendChild(card);
        });

        // "+ Add Character" Card
        const addCard = document.createElement("div");
        addCard.className = "apple-glass-card";
        addCard.style.background = "rgba(16, 20, 34, 0.4)";
        addCard.style.border = "1.5px dashed rgba(255, 45, 85, 0.4)";
        addCard.style.borderRadius = "20px";
        addCard.style.padding = "20px";
        addCard.style.display = "flex";
        addCard.style.flexDirection = "column";
        addCard.style.alignItems = "center";
        addCard.style.justifyContent = "center";
        addCard.style.gap = "12px";
        addCard.style.textAlign = "center";
        addCard.style.cursor = "pointer";
        addCard.style.minHeight = "240px";
        addCard.style.transition = "all 0.25s cubic-bezier(0.16, 1, 0.3, 1)";

        addCard.innerHTML = `
            <div style="width: 54px; height: 54px; border-radius: 50%; background: rgba(255, 45, 85, 0.12); border: 1px solid rgba(255, 45, 85, 0.35); display: flex; align-items: center; justify-content: center; color: #FF2D55; font-size: 28px; font-weight: 300;">
                +
            </div>
            <div>
                <h4 style="font-size: 15px; font-weight: 600; color: #f8fafc; margin: 0 0 4px 0; letter-spacing: -0.01em;">Make it yours</h4>
                <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 0; line-height: 1.45;">
                    Import custom artwork or sprite sheets &amp; choose templates.
                </p>
            </div>
            <button class="apple-button" style="margin-top: 6px; padding: 7px 18px; border-radius: 9999px; background: rgba(255, 45, 85, 0.15); border: 1px solid rgba(255, 45, 85, 0.4); color: #FF2D55; font-size: 12px; font-weight: 600; cursor: pointer; pointer-events: none;">
                + Add Character
            </button>
        `;

        addCard.addEventListener("mouseenter", () => {
            addCard.style.transform = "translateY(-4px)";
            addCard.style.borderColor = "#FF2D55";
            addCard.style.background = "rgba(255, 45, 85, 0.08)";
            addCard.style.boxShadow = "0 12px 28px -6px rgba(255, 45, 85, 0.25)";
        });
        addCard.addEventListener("mouseleave", () => {
            addCard.style.transform = "translateY(0)";
            addCard.style.borderColor = "rgba(255, 45, 85, 0.4)";
            addCard.style.background = "rgba(16, 20, 34, 0.4)";
            addCard.style.boxShadow = "none";
        });

        addCard.addEventListener("click", () => {
            sendAction("open_import_dialog");
        });

        grid.appendChild(addCard);
    }

    // ── Load & Render Activities ──────────────────────────────────────────
    const CATEGORY_COLORS = {
        "Movement": "#3b82f6",
        "Rest & Poses": "#10b981",
        "Expressions": "#a855f7",
        "Window Tricks": "#f51a58",
        "Advanced Transitions": "#f97316",
        "Effects & Reactions": "#eab308"
    };

    function loadActivities() {
        fetch("/api/activities")
            .then(res => res.json())
            .then(acts => {
                const actsStr = JSON.stringify(acts);
                const grid = document.getElementById("activities-gallery-grid");
                if (state._lastActsStr === actsStr && grid && grid.children.length > 0) {
                    return;
                }
                state._lastActsStr = actsStr;
                state.activities = acts;
                renderCategoryPills();
                renderActivities();
            })
            .catch(err => {
                console.warn("[SpiderBuddy Bridge] Failed to load activities:", err);
            });
    }

    function loadTimingSettings() {
        fetch("/api/timing_settings")
            .then(res => res.json())
            .then(timing => {
                state.timing = timing;
                const sCooldown = document.getElementById("slider-cooldown");
                const lCooldown = document.getElementById("label-cooldown-val");
                if (sCooldown && lCooldown && timing.special_cooldown !== undefined) {
                    sCooldown.value = timing.special_cooldown;
                    lCooldown.innerText = `${timing.special_cooldown} s`;
                }
                const sIdle = document.getElementById("slider-idle");
                const lIdle = document.getElementById("label-idle-val");
                if (sIdle && lIdle && timing.idle_timeout !== undefined) {
                    sIdle.value = timing.idle_timeout;
                    lIdle.innerText = `${timing.idle_timeout} s`;
                }
                const sSleep = document.getElementById("slider-sleep");
                const lSleep = document.getElementById("label-sleep-val");
                if (sSleep && lSleep && timing.sleep_after !== undefined) {
                    sSleep.value = timing.sleep_after;
                    lSleep.innerText = `${timing.sleep_after} m`;
                }
                const toggleAuto = document.getElementById("toggle-automatic-mode");
                if (toggleAuto && timing.automatic !== undefined) {
                    toggleAuto.checked = timing.automatic;
                }
            })
            .catch(() => {});
    }

    function renderCategoryPills() {
        const container = document.getElementById("activity-category-pills");
        if (!container) return;

        const categories = ["All", "Movement", "Rest & Poses", "Expressions", "Window Tricks", "Advanced Transitions", "Effects & Reactions"];
        container.innerHTML = "";

        categories.forEach(cat => {
            const btn = document.createElement("button");
            btn.className = "activity-category-pill" + (cat === state.selectedCategory ? " active" : "");
            btn.innerText = cat;
            btn.addEventListener("click", () => {
                state.selectedCategory = cat;
                renderCategoryPills();
                renderActivities();
            });
            container.appendChild(btn);
        });
    }

    function renderActivities() {
        const grid = document.getElementById("activities-gallery-grid");
        if (!grid) return;

        grid.innerHTML = "";

        const filtered = state.activities.filter(act => {
            const matchCategory = state.selectedCategory === "All" || act.category === state.selectedCategory;
            const matchQuery = !state.searchQuery || 
                act.label.toLowerCase().includes(state.searchQuery) || 
                act.description.toLowerCase().includes(state.searchQuery) ||
                act.category.toLowerCase().includes(state.searchQuery);
            return matchCategory && matchQuery;
        });

        if (filtered.length === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 48px; text-align: center; color: #64748b; font-family: 'IBM Plex Sans', sans-serif;">
                    <p style="font-size: 16px; margin-bottom: 6px;">No activities found matching your search.</p>
                    <p style="font-size: 13px; color: #475569;">Try clearing your search query or selecting a different category.</p>
                </div>
            `;
            return;
        }

        filtered.forEach(act => {
            const card = document.createElement("div");
            card.className = "apple-glass-card";
            card.style.background = act.enabled ? "rgba(19, 23, 36, 0.65)" : "rgba(15, 18, 28, 0.4)";
            card.style.backdropFilter = "blur(14px)";
            card.style.webkitBackdropFilter = "blur(14px)";
            card.style.border = act.enabled ? "1px solid rgba(255, 255, 255, 0.08)" : "1px solid rgba(255, 255, 255, 0.04)";
            card.style.borderTop = act.enabled ? "1px solid rgba(255, 255, 255, 0.18)" : "1px solid rgba(255, 255, 255, 0.08)";
            card.style.borderRadius = "18px";
            card.style.padding = "18px";
            card.style.display = "flex";
            card.style.flexDirection = "column";
            card.style.gap = "12px";
            card.style.opacity = act.enabled ? "1.0" : "0.55";
            card.style.transition = "transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, opacity 0.2s ease, box-shadow 0.25s ease";

            card.addEventListener("mouseenter", () => {
                if (act.enabled) {
                    card.style.transform = "translateY(-3px)";
                    card.style.borderColor = "rgba(255, 255, 255, 0.2)";
                    card.style.boxShadow = "0 14px 28px -6px rgba(0, 0, 0, 0.6)";
                }
            });
            card.addEventListener("mouseleave", () => {
                card.style.transform = "translateY(0)";
                card.style.borderColor = act.enabled ? "rgba(255, 255, 255, 0.08)" : "rgba(255, 255, 255, 0.04)";
                card.style.boxShadow = "none";
            });

            // Pedestal with image & category badge
            const catColor = CATEGORY_COLORS[act.category] || "#94a3b8";
            const pedestal = document.createElement("div");
            pedestal.style.width = "100%";
            pedestal.style.height = "116px";
            pedestal.style.borderRadius = "14px";
            pedestal.style.background = "radial-gradient(circle at 50% 30%, rgba(255, 45, 85, 0.14) 0%, rgba(12, 16, 28, 0.9) 100%)";
            pedestal.style.border = "1px solid rgba(255, 255, 255, 0.08)";
            pedestal.style.display = "flex";
            pedestal.style.alignItems = "center";
            pedestal.style.justifyContent = "center";
            pedestal.style.position = "relative";
            pedestal.style.overflow = "hidden";

            const img = document.createElement("img");
            img.src = act.icon_url || `/api/activity_icon/${act.id}.png`;
            img.alt = act.label;
            img.style.maxHeight = "88px";
            img.style.maxWidth = "88px";
            img.style.objectFit = "contain";
            img.style.filter = "drop-shadow(0 0 12px rgba(255, 45, 85, 0.4))";
            pedestal.appendChild(img);

            const badge = document.createElement("span");
            badge.className = "apple-pill-badge";
            badge.setAttribute("data-category", act.category);
            badge.style.position = "absolute";
            badge.style.top = "8px";
            badge.style.right = "8px";
            badge.style.fontSize = "9.5px";
            badge.style.fontWeight = "700";
            badge.style.color = catColor;
            badge.style.background = "rgba(10, 14, 25, 0.85)";
            badge.style.padding = "2px 8px";
            badge.style.borderRadius = "9999px";
            badge.style.border = `1px solid ${catColor}55`;
            badge.style.textTransform = "uppercase";
            badge.style.letterSpacing = "0.04em";
            badge.innerText = act.category;
            pedestal.appendChild(badge);

            // Title & Description
            const info = document.createElement("div");
            info.style.display = "flex";
            info.style.flexDirection = "column";
            info.style.gap = "4px";

            const title = document.createElement("h4");
            title.style.fontSize = "15px";
            title.style.fontWeight = "600";
            title.style.color = "#f8fafc";
            title.style.letterSpacing = "-0.012em";
            title.style.margin = "0";
            title.innerText = act.label;

            const desc = document.createElement("p");
            desc.className = "apple-subtext";
            desc.style.fontSize = "12px";
            desc.style.color = "rgba(220, 228, 245, 0.65)";
            desc.style.margin = "0";
            desc.style.lineHeight = "1.4";
            desc.style.minHeight = "34px";
            desc.innerText = act.description;

            info.appendChild(title);
            info.appendChild(desc);

            // Controls row: Switch + Play button
            const controlsRow = document.createElement("div");
            controlsRow.style.display = "flex";
            controlsRow.style.justifyContent = "space-between";
            controlsRow.style.alignItems = "center";
            controlsRow.style.paddingTop = "10px";
            controlsRow.style.borderTop = "1px solid rgba(255, 255, 255, 0.08)";

            // Switch container
            const switchLabel = document.createElement("label");
            switchLabel.className = "spider-switch";

            const switchInput = document.createElement("input");
            switchInput.type = "checkbox";
            switchInput.checked = Boolean(act.enabled);
            switchInput.addEventListener("change", (e) => {
                act.enabled = e.target.checked;
                card.style.opacity = act.enabled ? "1.0" : "0.55";
                card.style.borderColor = act.enabled ? "rgba(255, 255, 255, 0.08)" : "rgba(255, 255, 255, 0.04)";
                sendAction("toggle_activity", { activity: act.id, enabled: act.enabled });
                playBtn.style.opacity = act.enabled ? "1.0" : "0.4";
                playBtn.style.pointerEvents = act.enabled ? "auto" : "none";
            });

            const switchSlider = document.createElement("span");
            switchSlider.className = "spider-slider";

            switchLabel.appendChild(switchInput);
            switchLabel.appendChild(switchSlider);

            // Play Trigger Button
            const playBtn = document.createElement("button");
            playBtn.innerText = "▶ Play";
            playBtn.className = "apple-button";
            playBtn.style.background = "rgba(255, 255, 255, 0.08)";
            playBtn.style.border = "1px solid rgba(255, 255, 255, 0.15)";
            playBtn.style.color = "#f1f5f9";
            playBtn.style.padding = "6px 14px";
            playBtn.style.borderRadius = "9999px";
            playBtn.style.fontSize = "12px";
            playBtn.style.fontWeight = "600";
            playBtn.style.cursor = "pointer";
            playBtn.style.opacity = act.enabled ? "1.0" : "0.4";
            playBtn.style.pointerEvents = act.enabled ? "auto" : "none";

            playBtn.addEventListener("mouseenter", () => {
                if (act.enabled) {
                    playBtn.style.background = "#FF2D55";
                    playBtn.style.borderColor = "#FF2D55";
                    playBtn.style.color = "#fff";
                    playBtn.style.boxShadow = "0 3px 12px rgba(255, 45, 85, 0.4)";
                }
            });
            playBtn.addEventListener("mouseleave", () => {
                playBtn.style.background = "rgba(255, 255, 255, 0.08)";
                playBtn.style.borderColor = "rgba(255, 255, 255, 0.15)";
                playBtn.style.color = "#f1f5f9";
                playBtn.style.boxShadow = "none";
            });

            playBtn.addEventListener("click", () => {
                sendAction("play_activity", { activity: act.id });
                window.SpiderBuddy.setActivity(act.label);
                playBtn.style.transform = "scale(0.94)";
                playBtn.innerText = "✓ Triggered!";
                setTimeout(() => {
                    playBtn.style.transform = "scale(1)";
                    playBtn.innerText = "▶ Play";
                }, 700);
            });

            controlsRow.appendChild(switchLabel);
            controlsRow.appendChild(playBtn);

            card.appendChild(pedestal);
            card.appendChild(info);
            card.appendChild(controlsRow);
            grid.appendChild(card);
        });
    }

    // ── Wire Navigation & Interactive Controls ────────────────────────────
    function wireInteractiveControls() {
        function bindClick(selector, handler) {
            const el = typeof selector === "string" ? document.querySelector(selector) : selector;
            if (!el) return;
            el.style.cursor = "pointer";
            el.style.transition = "transform 0.15s ease, opacity 0.15s ease";
            el.addEventListener("mousedown", () => { el.style.transform = "scale(0.96)"; });
            el.addEventListener("mouseup", () => { el.style.transform = "scale(1)"; });
            el.addEventListener("mouseleave", () => { el.style.transform = "scale(1)"; });
            el.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                handler(e);
            }, true);
        }

        // Global robust delegation for sidebar navigation & quick nav cards
        document.addEventListener("click", (e) => {
            const charBtn = e.target.closest('[data-framer-name="Characters"], [data-framer-name="Change character"]');
            if (charBtn) {
                e.preventDefault();
                e.stopPropagation();
                switchTab("Characters");
                return;
            }
            const actBtn = e.target.closest('[data-framer-name="Activities"], [data-framer-name="Choose activities"]');
            if (actBtn) {
                e.preventDefault();
                e.stopPropagation();
                switchTab("Activities");
                return;
            }
            const deskBtn = e.target.closest('[data-framer-name="Desktop & Apps"], [data-framer-name="Desktop &amp; Apps"]');
            if (deskBtn) {
                e.preventDefault();
                e.stopPropagation();
                switchTab("Desktop & Apps");
                return;
            }
            const focusBtn = e.target.closest('[data-framer-name="Focus & Breaks"], [data-framer-name="Focus &amp; Breaks"], [data-framer-name="Focus settings"]');
            if (focusBtn) {
                e.preventDefault();
                e.stopPropagation();
                switchTab("Focus & Breaks");
                return;
            }
            const ctrlBtn = e.target.closest('[data-framer-name="Controls"]');
            if (ctrlBtn) {
                e.preventDefault();
                e.stopPropagation();
                switchTab("Controls");
                return;
            }
            const homeBtn = e.target.closest('[data-framer-name="Home"]');
            if (homeBtn) {
                e.preventDefault();
                e.stopPropagation();
                switchTab("Home");
                return;
            }
            const setBtn = e.target.closest('[data-framer-name="Settings"], [data-framer-name="Setting"]');
            if (setBtn) {
                e.preventDefault();
                e.stopPropagation();
                switchTab("Settings");
                return;
            }
            const profBtn = e.target.closest('#sidebar-profile-card, [data-framer-name="My Profile"], [data-framer-name="Profile"]');
            if (profBtn) {
                const avatarClicked = e.target.closest('.sidebar-profile-avatar-box, .sidebar-profile-squircle, #sidebar-profile-avatar-img');
                if (avatarClicked) {
                    e.preventDefault();
                    e.stopPropagation();
                    const avImg = document.getElementById("sidebar-profile-avatar-img");
                    const src = (avImg && avImg.getAttribute("src")) || (state.userProfile && state.userProfile.avatar) || "images/spiderman_brand_icon.png";
                    const heroName = (state.userProfile && state.userProfile.name) || "Operative Profile";
                    openImageLightbox(src, heroName);
                    return;
                }
                e.preventDefault();
                e.stopPropagation();
                switchTab("Profile");
                return;
            }
        }, true);

        // Action buttons
        bindClick('[data-framer-name="Pause"]', () => {
            const nextRunning = !state.isRunning;
            window.SpiderBuddy.setRunning(nextRunning);
            sendAction(nextRunning ? "resume" : "pause");
        });

        // Sidebar Pause companion click
        bindClick('[data-framer-name="Current companion"] .framer-91hj6l', () => {
            const nextRunning = !state.isRunning;
            window.SpiderBuddy.setRunning(nextRunning);
            sendAction(nextRunning ? "resume" : "pause");
        });

        bindClick('[data-framer-name="Hide"]', () => {
            sendAction("hide");
        });

        function setMoodVisuals(activeMood) {
            ["Chill", "Hyper", "Camo"].forEach(m => {
                const el = document.querySelector(`[data-framer-name="${m}"]`);
                if (!el) return;
                if (m.toLowerCase() === activeMood.toLowerCase()) {
                    el.style.border = "1.5px solid #f51a58";
                    el.style.boxShadow = "0 0 12px rgba(245, 26, 88, 0.5)";
                } else {
                    el.style.border = "1px solid rgba(255, 255, 255, 0.12)";
                    el.style.boxShadow = "none";
                }
            });
        }

        bindClick('[data-framer-name="Chill"]', () => {
            setMoodVisuals("chill");
            sendAction("mood", { mood: "chill" });
            window.SpiderBuddy.setActivity("CHILL");
        });

        bindClick('[data-framer-name="Hyper"]', () => {
            setMoodVisuals("hyper");
            sendAction("mood", { mood: "hyper" });
            window.SpiderBuddy.setActivity("HYPER");
        });

        bindClick('[data-framer-name="Camo"]', () => {
            setMoodVisuals("camo");
            sendAction("mood", { mood: "camo" });
            window.SpiderBuddy.setActivity("CAMO");
        });

        // Quick triggers with visual pulse
        function pulseTrigger(selector) {
            const el = document.querySelector(selector);
            if (el) {
                el.style.boxShadow = "0 0 16px rgba(245, 26, 88, 0.6)";
                setTimeout(() => { el.style.boxShadow = "none"; }, 400);
            }
        }

        bindClick('[data-framer-name="Web swing"]', () => {
            pulseTrigger('[data-framer-name="Web swing"]');
            sendAction("play_activity", { activity: "swing" });
            window.SpiderBuddy.setActivity("SWINGING");
        });

        bindClick('[data-framer-name="Celebrate / Flip"]', () => {
            pulseTrigger('[data-framer-name="Celebrate / Flip"]');
            sendAction("play_activity", { activity: "celebrate" });
            window.SpiderBuddy.setActivity("CELEBRATING");
        });

        bindClick('[data-framer-name="Window perch"]', () => {
            pulseTrigger('[data-framer-name="Window perch"]');
            sendAction("play_activity", { activity: "perch" });
            window.SpiderBuddy.setActivity("PERCHING");
        });

        bindClick('[data-framer-name="Power nap"]', () => {
            pulseTrigger('[data-framer-name="Power nap"]');
            sendAction("play_activity", { activity: "sleep" });
            window.SpiderBuddy.setActivity("SLEEPING");
        });

        // Focus Timer Buttons
        bindClick('[data-framer-name="25m Focus"]', () => {
            sendAction("start_focus", { minutes: 25 });
            window.SpiderBuddy.setTimer("25:00", "Focusing");
            window.SpiderBuddy.setActivity("FOCUSING");
        });

        bindClick('[data-framer-name="5m Break"]', () => {
            sendAction("start_focus", { minutes: 5 });
            window.SpiderBuddy.setTimer("05:00", "Short Break");
            window.SpiderBuddy.setActivity("BREAK");
        });

        bindClick('[data-framer-name="Reset"]', () => {
            sendAction("stop_focus");
            window.SpiderBuddy.setTimer("25:00", "Ready");
            window.SpiderBuddy.setActivity("IDLE");
        });

        // Sidebar Navigation & Brand Tile
        const brandTile = document.getElementById("spider-brand-tile") || document.querySelector('[data-framer-name="Brand"]');
        if (brandTile) {
            brandTile.addEventListener("click", () => switchTab("Home"));
            brandTile.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    switchTab("Home");
                }
            });
        }
        bindClick('[data-framer-name="Home"]', () => switchTab("Home"));
        bindClick('[data-framer-name="Characters"]', () => switchTab("Characters"));
        bindClick('[data-framer-name="Activities"]', () => switchTab("Activities"));
        bindClick('[data-framer-name="Desktop & Apps"]', () => switchTab("Desktop & Apps"));
        bindClick('[data-framer-name="Focus & Breaks"]', () => switchTab("Focus & Breaks"));
        bindClick('[data-framer-name="Focus &amp; Breaks"]', () => switchTab("Focus & Breaks"));
        bindClick('[data-framer-name="Controls"]', () => switchTab("Controls"));

        // Bind Sticky Notes & Settings Tab
        bindClick('[data-framer-name="Sticky Notes"]', () => switchTab("Sticky Notes"));
        bindClick('[data-framer-name="Settings"]', () => switchTab("Settings"));
        bindClick('#sidebar-profile-card', (e) => {
            if (e && e.target && e.target.closest && e.target.closest('.sidebar-profile-avatar-box, .sidebar-profile-squircle, #sidebar-profile-avatar-img')) {
                return;
            }
            switchTab("Profile");
        });
        bindClick('[data-framer-name="My Profile"]', (e) => {
            if (e && e.target && e.target.closest && e.target.closest('.sidebar-profile-avatar-box, .sidebar-profile-squircle, #sidebar-profile-avatar-img')) {
                return;
            }
            switchTab("Profile");
        });

        // Left sidebar bottom avatar click and double-click triggers
        const sidebarAvatarBox = document.querySelector(".sidebar-profile-avatar-box");
        if (sidebarAvatarBox) {
            sidebarAvatarBox.title = "Click or double-click to view profile photo in big screen";
            sidebarAvatarBox.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                const avImg = document.getElementById("sidebar-profile-avatar-img");
                const src = (avImg && avImg.getAttribute("src")) || (state.userProfile && state.userProfile.avatar) || "images/spiderman_brand_icon.png";
                openImageLightbox(src, (state.userProfile && state.userProfile.name) || "Operative Profile");
            });
            sidebarAvatarBox.addEventListener("dblclick", (e) => {
                e.preventDefault();
                e.stopPropagation();
                const avImg = document.getElementById("sidebar-profile-avatar-img");
                const src = (avImg && avImg.getAttribute("src")) || (state.userProfile && state.userProfile.avatar) || "images/spiderman_brand_icon.png";
                openImageLightbox(src, (state.userProfile && state.userProfile.name) || "Operative Profile");
            });
        }
        const sidebarCardEl = document.getElementById("sidebar-profile-card");
        if (sidebarCardEl) {
            sidebarCardEl.addEventListener("dblclick", (e) => {
                e.preventDefault();
                e.stopPropagation();
                const avImg = document.getElementById("sidebar-profile-avatar-img");
                const src = (avImg && avImg.getAttribute("src")) || (state.userProfile && state.userProfile.avatar) || "images/spiderman_brand_icon.png";
                openImageLightbox(src, (state.userProfile && state.userProfile.name) || "Operative Profile");
            });
        }

        // Theme buttons
        document.querySelectorAll(".theme-select-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const t = btn.getAttribute("data-theme");
                state.appSettings = state.appSettings || {};
                state.appSettings.theme = t;
                sendAction("set_theme", { theme: t });
                updateThemeButtons(t);
            });
        });

        // FPS buttons
        document.querySelectorAll(".fps-select-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const fps = parseInt(btn.getAttribute("data-fps"));
                state.appSettings = state.appSettings || {};
                state.appSettings.display_fps = fps;
                sendAction("set_display_fps", { fps: fps });
                updateFpsButtons(fps);
            });
        });

        // Animation speed buttons
        document.querySelectorAll(".anim-speed-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const spd = parseFloat(btn.getAttribute("data-speed"));
                state.appSettings = state.appSettings || {};
                state.appSettings.animation_speed = spd;
                sendAction("set_animation_speed", { speed: spd });
                updateAnimSpeedButtons(spd);
            });
        });

        // Settings switches and maintenance actions are bound once in setupViews.
        bindClick("#btn-factory-reset", () => {
            if (confirm("Restore all settings to factory defaults?")) {
                sendAction("reset_all_settings");
            }
        });
        bindClick("#btn-reload-ui", () => sendAction("reload_ui"));

        bindClick('.framer-121j3ed', () => {
            const cur = (state.appSettings && state.appSettings.theme) || "dark";
            const nextTheme = cur === "light" ? "dark" : "light";
            state.appSettings = state.appSettings || {};
            state.appSettings.theme = nextTheme;
            sendAction("set_theme", { theme: nextTheme });
            updateThemeButtons(nextTheme);
            const lbl = document.querySelector('.framer-121j3ed p');
            if (lbl) lbl.innerText = nextTheme === "light" ? "Switch to dark theme" : "Switch to light theme";
        });


        // Quick navigation buttons from Home tab
        bindClick('[data-framer-name="Change character"]', () => switchTab("Characters"));
        bindClick('[data-framer-name="Choose activities"]', () => switchTab("Activities"));
        bindClick('[data-framer-name="Focus settings"]', () => switchTab("Focus & Breaks"));
    }

    // ── Public API exposed on window.SpiderBuddy ──────────────────────────
    window.SpiderBuddy = {
        dispatchAction: sendAction,
        switchTab: switchTab,
        setTheme: updateThemeButtons,
        loadCharacters: loadCharacters,
        loadActivities: loadActivities,
        loadTimingSettings: loadTimingSettings,
        loadDisplaySettings: loadDisplaySettings,
        loadRunningApplications: loadRunningApplications,
        loadFocusSettings: loadFocusSettings,
        loadControlSettings: loadControlSettings,
        loadAppSettings: loadAppSettings,
        loadProfileView: loadProfileView,
        switchProfileSegment: switchProfileSegment,
        addToBin: addToBin,
        restoreFromBin: restoreFromBin,
        getBinCharacters: () => state.binCharacters || [],
        loadStickyNotes: loadStickyNotes,
        createStickyNote: createStickyNote,
        updateNoteTitle: updateNoteTitle,
        updateNoteContent: updateNoteContent,
        setNoteTheme: setNoteTheme,
        toggleNotePin: toggleNotePin,
        toggleNoteDesktop: toggleNoteDesktop,
        toggleNoteItem: toggleNoteItem,
        addNoteTask: addNoteTask,
        deleteNoteItem: deleteNoteItem,
        deleteNote: deleteNote,
        openCreateNoteModal: openCreateNoteModal,
        closeCreateNoteModal: closeCreateNoteModal,
        updateStickyNotesMasterToggleUI: updateStickyNotesMasterToggleUI,
        updateFlingPhysicsUI: updateFlingPhysicsUI,

        setEyeBreakProgress(continuousSec, limitSec) {
            state.focusSettings.continuous_work_seconds = continuousSec;
            const curM = Math.floor(continuousSec / 60);
            const curS = Math.floor(continuousSec % 60);
            const limitM = Math.round(limitSec / 60);
            const statusEl = document.getElementById("eye-break-status-text");
            const barEl = document.getElementById("eye-break-progress-bar");
            if (statusEl) {
                statusEl.innerText = `💧 Continuous Work: ${curM}m ${curS}s / ${limitM}m • Focus Timer: ${state.focusSettings.focus_timer_active ? "Active" : "Inactive"}`;
            }
            if (barEl && limitSec > 0) {
                const pct = Math.min(100, Math.round((continuousSec / limitSec) * 100));
                barEl.style.width = `${pct}%`;
            }
        },

        setTuning(size, opacity) {
            if (size !== undefined && size !== null) {
                state.companionSize = size;
                const sl = document.getElementById("slider-size");
                const lbl = document.getElementById("label-size-val");
                if (sl) sl.value = size;
                if (lbl) lbl.innerText = `${size} px`;
            }
            if (opacity !== undefined && opacity !== null) {
                state.companionOpacity = opacity;
                const slOp = document.getElementById("slider-opacity");
                const lblOp = document.getElementById("label-opacity-val");
                if (slOp) slOp.value = opacity;
                if (lblOp) lblOp.innerText = `${opacity}%`;
            }
        },

        setFrame(b64Data) {
            if (!b64Data) return;
            state.lastFrameB64 = b64Data;
            const img = document.getElementById("companion-live-frame");
            if (img && state.currentTab === "Home") {
                const srcVal = b64Data.startsWith("data:") ? b64Data : "data:image/png;base64," + b64Data;
                if (img.src !== srcVal) {
                    img.src = srcVal;
                }
            }
        },

        setActivity(activityName) {
            const newAct = String(activityName || "IDLE").toUpperCase();
            if (state.activity === newAct) return;
            state.activity = newAct;
            const badge = document.getElementById("companion-activity-badge");
            if (badge && badge.innerText !== newAct) badge.innerText = newAct;

            const dispStr = "Status: " + newAct.charAt(0) + newAct.slice(1).toLowerCase();
            const statusEl = document.querySelector('[data-framer-name="Your companion"] .framer-1xw2jy2 p');
            if (statusEl && statusEl.innerText !== dispStr) {
                statusEl.innerText = dispStr;
            }

            const sideStatusEl = document.querySelector('[data-framer-name="Current companion"] .framer-sgw6qu p');
            const sideStr = newAct.charAt(0) + newAct.slice(1).toLowerCase();
            if (sideStatusEl && sideStatusEl.innerText !== sideStr) {
                sideStatusEl.innerText = sideStr;
            }
        },

        setCharacter(name, quote) {
            if (name && state.characterName !== name) {
                state.characterName = name;
                const nameEl = document.querySelector('[data-framer-name="Your companion"] .framer-quemdd p');
                if (nameEl && nameEl.innerText !== name) nameEl.innerText = name;
                const sideNameEl = document.querySelector('[data-framer-name="Current companion"] .framer-1xc69zo p');
                if (sideNameEl && sideNameEl.innerText !== name) sideNameEl.innerText = name;
            }
            if (quote && state.quote !== quote) {
                state.quote = quote;
                const quoteEl = document.querySelector('[data-framer-name="Companion quote"] p');
                if (quoteEl && quoteEl.innerText !== quote) quoteEl.innerText = quote;
            }
        },

        setRunning(isRunning) {
            const bRunning = Boolean(isRunning);
            state.isRunning = bRunning;
            const pauseBtnText = document.querySelector('[data-framer-name="Pause"] p');
            const pText = bRunning ? "Pause" : "Resume";
            if (pauseBtnText && pauseBtnText.innerText !== pText) {
                pauseBtnText.innerText = pText;
            }
            const sidePauseText = document.querySelector('[data-framer-name="Current companion"] .framer-91hj6l p');
            const sidePText = bRunning ? "Pause companion" : "Resume companion";
            if (sidePauseText && sidePauseText.innerText !== sidePText) {
                sidePauseText.innerText = sidePText;
            }
        },

        setHidden(isHidden) {
            state.isHidden = Boolean(isHidden);
            const hideBtnText = document.querySelector('[data-framer-name="Hide"] p');
            const targetText = state.isHidden ? "Show" : "Hide";
            if (hideBtnText && hideBtnText.innerText !== targetText) {
                hideBtnText.innerText = targetText;
            }
            const hideBtn = document.querySelector('[data-framer-name="Hide"]');
            if (hideBtn) {
                const targetOpacity = state.isHidden ? "0.6" : "1.0";
                if (hideBtn.style.opacity !== targetOpacity) {
                    hideBtn.style.opacity = targetOpacity;
                }
            }
        },

        setBattery(percent, isCharging, isLow, suitLore, loreStatus) {
            const p = Math.round(percent);
            const c = Boolean(isCharging);
            if (state.batteryPercent === p && state.isCharging === c && state.suitLore === suitLore && state.loreStatus === loreStatus) {
                return;
            }
            state.batteryPercent = p;
            state.isCharging = c;
            state.suitLore = suitLore;
            state.loreStatus = loreStatus;
            const batText = `${state.batteryPercent}% · ${state.isCharging ? "Charging" : "On battery"}`;

            const batEl = document.querySelector('[data-framer-name="Battery and suit"] .framer-1djadwo p');
            if (batEl && batEl.innerText !== batText) batEl.innerText = batText;

            const batFillEl = document.getElementById("apple-battery-fill");
            if (batFillEl) batFillEl.style.width = `${Math.min(100, Math.max(0, p))}%`;

            const batChipEl = document.getElementById("apple-bat-chip");
            if (batChipEl) {
                const chipText = c ? "⚡ Charging" : "On Battery";
                if (batChipEl.innerText !== chipText) {
                    batChipEl.innerText = chipText;
                    batChipEl.className = c ? "apple-pod-tag apple-tag-green" : "apple-pod-tag apple-tag-blue";
                }
            }

            const sideBatEl = document.querySelector('.framer-kvb96p p');
            if (sideBatEl && sideBatEl.innerText !== batText) sideBatEl.innerText = batText;

            if (suitLore) {
                const loreEl = document.querySelector('[data-framer-name="Battery and suit"] .framer-16hyfq4 p');
                if (loreEl && loreEl.innerText !== suitLore) loreEl.innerText = suitLore;
            }
            if (loreStatus) {
                const loreStatEl = document.querySelector('[data-framer-name="Battery and suit"] .framer-1hn0my1 p');
                if (loreStatEl && loreStatEl.innerText !== loreStatus) loreStatEl.innerText = loreStatus;
            }
        },

        setHardwareLoad(cpu, ram, isHeavy, spideySenseText, spideySenseColor) {
            const c = Math.round(cpu);
            const r = Math.round(ram);
            if (state.cpu !== c || state.ram !== r) {
                state.cpu = c;
                state.ram = r;
                const loadEl = document.querySelector('[data-framer-name="Hardware load"] .framer-19xeu90 p');
                const loadText = `${state.cpu}% ${state.ram}%`;
                if (loadEl && loadEl.innerText !== loadText) loadEl.innerText = loadText;

                const cpuValEl = document.getElementById("apple-cpu-val");
                if (cpuValEl && cpuValEl.innerText !== `${c}%`) cpuValEl.innerText = `${c}%`;
                const cpuBarEl = document.getElementById("apple-cpu-bar");
                if (cpuBarEl) cpuBarEl.style.width = `${Math.min(100, Math.max(0, c))}%`;

                const ramValEl = document.getElementById("apple-ram-val");
                if (ramValEl && ramValEl.innerText !== `${r}%`) ramValEl.innerText = `${r}%`;
                const ramBarEl = document.getElementById("apple-ram-bar");
                if (ramBarEl) ramBarEl.style.width = `${Math.min(100, Math.max(0, r))}%`;

                const loadBadgeEl = document.getElementById("apple-load-badge");
                if (loadBadgeEl) {
                    if (c > 75 || r > 85) {
                        if (loadBadgeEl.innerText !== "Heavy") {
                            loadBadgeEl.innerText = "Heavy";
                            loadBadgeEl.className = "apple-pod-tag apple-tag-amber";
                        }
                    } else {
                        if (loadBadgeEl.innerText !== "Optimal") {
                            loadBadgeEl.innerText = "Optimal";
                            loadBadgeEl.className = "apple-pod-tag apple-tag-blue";
                        }
                    }
                }
            }

            if (spideySenseText && state.spideySenseText !== spideySenseText) {
                state.spideySenseText = spideySenseText;
                const senseEl = document.querySelector('[data-framer-name="Spider-Sense"] .framer-1qtpc5s p');
                if (senseEl) {
                    if (senseEl.innerText !== spideySenseText) senseEl.innerText = spideySenseText;
                    if (spideySenseColor && senseEl.style.color !== spideySenseColor) senseEl.style.color = spideySenseColor;
                }
            }
        },

        setStats(distance, webs, uptime) {
            if (distance !== undefined && state.statsDistance !== distance) {
                state.statsDistance = distance;
                const distEl = document.querySelector('[data-framer-name="Distance"] .framer-1ndz97i p');
                if (distEl && distEl.innerText !== String(distance)) distEl.innerText = String(distance);
            }
            if (webs !== undefined && state.statsWebs !== webs) {
                state.statsWebs = webs;
                const websEl = document.querySelector('[data-framer-name="Webs"] .framer-10kb0sf p');
                if (websEl && websEl.innerText !== String(webs)) websEl.innerText = String(webs);
            }
            if (uptime !== undefined && state.statsUptime !== uptime) {
                state.statsUptime = uptime;
                const upEl = document.querySelector('[data-framer-name="Active time"] .framer-lk63rt p');
                if (upEl && upEl.innerText !== String(uptime)) upEl.innerText = String(uptime);
            }
        },

        setTimer(timeStr, statusStr) {
            if (timeStr) {
                const timerEl = document.querySelector('[data-framer-name="Timer ring"] .framer-hmo7gg p');
                if (timerEl) timerEl.innerText = timeStr;
                const clockEl = document.getElementById("focus-timer-clock");
                if (clockEl) {
                    clockEl.innerText = timeStr;
                    clockEl.style.color = (timeStr === "25:00" && (!statusStr || statusStr === "Ready")) ? "#64748b" : "#38bdf8";
                    clockEl.style.textShadow = (timeStr === "25:00" && (!statusStr || statusStr === "Ready")) ? "none" : "0 0 24px rgba(56, 189, 248, 0.55)";
                }
            }
            if (statusStr) {
                const statusEl = document.querySelector('[data-framer-name="Focus status"] .framer-1m18unj p');
                if (statusEl) statusEl.innerText = statusStr;
                const badgeEl = document.getElementById("focus-timer-badge");
                if (badgeEl) {
                    badgeEl.innerText = statusStr === "Ready" ? "🛡️ Guardian Mode: Ready" : (statusStr === "Focusing" ? "🛡️ Guardian Focus: Active" : `☕ ${statusStr}`);
                    badgeEl.style.color = statusStr === "Ready" ? "#94a3b8" : (statusStr === "Focusing" ? "#38bdf8" : "#22c55e");
                }
            }
        },

        setCacheSize(size) {
            const el = document.getElementById("settings-cache-size-text");
            if (el && size) {
                el.innerText = size;
            }
        },

        setAudioMeter(peak) {
            const val = Math.max(0, Math.min(100, Math.round(Number(peak) || 0)));
            state.audioMeter = val;
            const meterBar = document.getElementById("audio-meter-bar");
            if (meterBar) {
                meterBar.style.width = `${val}%`;
            }
            const meterText = document.getElementById("audio-meter-val");
            if (meterText) {
                meterText.innerText = `${val}%`;
            }
        },

        setMusicStatus(status, volume) {
            state.musicStatus = String(status || "idle");
            state.musicVolume = Number(volume) || 0;
            const musEl = document.getElementById("music-status-text");
            if (musEl) {
                musEl.innerText = state.musicStatus;
            }
        }
    };

    function startStatusSync() {
        setInterval(() => {
            if (document.hidden) return;
            fetch("/api/status")
                .then(r => r.json())
                .then(data => {
                    if (data && typeof data === "object") {
                        if (data.status && data.status.toUpperCase() !== state.activity) {
                            window.SpiderBuddy.setActivity(data.status);
                        }
                        if (data.is_running !== undefined && Boolean(data.is_running) !== state.isRunning) {
                            window.SpiderBuddy.setRunning(data.is_running);
                        }
                        if (data.character_name && data.character_name !== state.characterName) {
                            window.SpiderBuddy.setCharacter(data.character_name);
                        }
                        if (data.is_hidden !== undefined && Boolean(data.is_hidden) !== state.isHidden) {
                            window.SpiderBuddy.setHidden(data.is_hidden);
                        }
                        const sizeChanged = data.companion_size !== undefined && data.companion_size !== state.companionSize;
                        const opacityChanged = data.companion_opacity !== undefined && data.companion_opacity !== state.companionOpacity;
                        if (sizeChanged || opacityChanged) {
                            if (sizeChanged) state.companionSize = data.companion_size;
                            if (opacityChanged) state.companionOpacity = data.companion_opacity;
                            window.SpiderBuddy.setTuning(
                                data.companion_size !== undefined ? data.companion_size : state.companionSize,
                                data.companion_opacity !== undefined ? data.companion_opacity : state.companionOpacity
                            );
                        }
                    }
                })
                .catch(() => {});
        }, 2500);
    }

    function init() {
        const mainDash = document.querySelector('[data-framer-name="Main dashboard"]');
        if (mainDash) mainDash.scrollTop = 0;
        setupCharacterHeroArea();
        setupViews();
        wireInteractiveControls();
        updateSidebarActiveItem("Home");
        loadAppSettings();
        startStatusSync();
        console.log("[SpiderBuddy Bridge] Web Bridge with Characters tab ready!");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => setTimeout(init, 300));
    } else {
        setTimeout(init, 300);
    }
})();
