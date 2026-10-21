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

            <!-- Card 3: Mouse Cursor Interaction & Spider-Sense -->
            <div id="card-mouse-interaction" class="apple-glass-card" data-border="true" style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 18px;">
                    <div style="display: flex; flex-direction: column; gap: 4px; max-width: 85%;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 20px;">🖱️</span>
                            <h3 class="apple-card-title" style="font-size: 17px; font-weight: 600; color: #f8fafc; margin: 0; letter-spacing: -0.015em;">Mouse Interaction &amp; Spider-Sense Reflexes</h3>
                        </div>
                        <p class="apple-subtext" style="font-size: 13px; color: rgba(220, 228, 245, 0.65); margin: 0; line-height: 1.45;">
                            Configure mouse following, quick cursor dodges, and click-through mode for uninterrupted work.
                        </p>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px;">
                    <!-- Follow Mouse Cursor -->
                    <div class="apple-glass-card-sub" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 18px;">
                        <div style="display: flex; flex-direction: column; gap: 3px; max-width: 78%;">
                            <span style="font-size: 13.5px; font-weight: 500; color: #f1f5f9; letter-spacing: -0.01em;">Follow Mouse Cursor</span>
                            <span style="font-size: 11px; color: rgba(220, 228, 245, 0.5);">Spider-Man turns toward and crawls toward cursor</span>
                        </div>
                        <label class="spider-switch">
                            <input type="checkbox" id="toggle-mouse-following" checked />
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
                            <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Mouse Following</span>
                            <p class="apple-subtext" style="font-size: 12px; color: rgba(220, 228, 245, 0.65); margin: 2px 0 0 0;">Turns head and crawls toward the mouse cursor when idle.</p>
                        </div>
                        <label class="spider-switch">
                            <input id="toggle-settings-mouse-follow" type="checkbox" checked>
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

        // First hide all views completely
        [homeView, charView, actView, deskView, focusView, controlsView, settingsView].forEach(v => {
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
            "Settings": document.querySelector('[data-framer-name="Settings"]')
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

        // 3. Mouse interactions
        const tMouse = document.getElementById("toggle-mouse-following");
        if (tMouse) tMouse.checked = Boolean(cs.enable_mouse_following);

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
        if (tFollow) tFollow.checked = Boolean(s.enable_mouse_following);

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

        characters.forEach(char => {
            const isSelected = Boolean(char.selected || char.id === state.activeCharacterId);
            const card = document.createElement("div");
            card.className = "apple-glass-card";
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

            const suit = document.createElement("p");
            suit.style.fontSize = "12.5px";
            suit.style.color = "rgba(220, 228, 245, 0.65)";
            suit.style.margin = "0";
            suit.style.whiteSpace = "nowrap";
            suit.style.overflow = "hidden";
            suit.style.textOverflow = "ellipsis";
            suit.innerText = char.suit || "Classic Suit";

            info.appendChild(name);
            info.appendChild(suit);

            // Action Button
            const btn = document.createElement("button");
            btn.className = "apple-button";
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
            <button class="apple-button" style="margin-top: 6px; padding: 7px 18px; border-radius: 9999px; background: rgba(255, 45, 85, 0.15); border: 1px solid rgba(255, 45, 85, 0.4); color: #FF2D55; font-size: 12px; font-weight: 600; cursor: pointer;">
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

        // Sidebar Navigation
        bindClick('[data-framer-name="Home"]', () => switchTab("Home"));
        bindClick('[data-framer-name="Characters"]', () => switchTab("Characters"));
        bindClick('[data-framer-name="Activities"]', () => switchTab("Activities"));
        bindClick('[data-framer-name="Desktop & Apps"]', () => switchTab("Desktop & Apps"));
        bindClick('[data-framer-name="Focus & Breaks"]', () => switchTab("Focus & Breaks"));
        bindClick('[data-framer-name="Focus &amp; Breaks"]', () => switchTab("Focus & Breaks"));
        bindClick('[data-framer-name="Controls"]', () => switchTab("Controls"));

        // Bind Settings Tab & Options
        bindClick('[data-framer-name="Settings"]', () => switchTab("Settings"));

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
        loadCharacters: loadCharacters,
        loadActivities: loadActivities,
        loadTimingSettings: loadTimingSettings,
        loadDisplaySettings: loadDisplaySettings,
        loadRunningApplications: loadRunningApplications,
        loadFocusSettings: loadFocusSettings,
        loadControlSettings: loadControlSettings,
        loadAppSettings: loadAppSettings,

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
