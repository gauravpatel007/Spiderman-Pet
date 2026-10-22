# Complete implementation script for Spider Sticky Notes in Frontend/js/spider_bridge.js
import os
import re

JS_PATH = r"g:\Languages\Projects\Pet\Pet A2 Final\Frontend\js\spider_bridge.js"

with open(JS_PATH, "r", encoding="utf-8") as f:
    js_content = f.read()

# 1. HTML Wrapper to add into setupViews() right after `contentArea.appendChild(profileWrapper);`
WRAPPER_CODE = """
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
                <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
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
"""

# Check replacement position for WRAPPER_CODE
profile_append = "contentArea.appendChild(profileWrapper);"
assert profile_append in js_content, "Profile wrapper append anchor not found!"
js_content = js_content.replace(profile_append, profile_append + "\n" + WRAPPER_CODE, 1)

# 2. Logic implementation to place before `// ── Switch Tabs`
LOGIC_CODE = '''
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
    }

    function initStickyNotesEventsOnce() {
        if (stickyNotesInitialized) return;
        stickyNotesInitialized = true;

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
            if (Array.isArray(note.tasks)) {
                totalTasks += note.tasks.length;
                completedTasks += note.tasks.filter(t => t.completed).length;
            }
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
            filtered = filtered.filter(n => (n.color_theme || "spidey_red") === state.stickyNotesFilter);
        }

        if (state.stickyNotesSearch) {
            const q = state.stickyNotesSearch;
            filtered = filtered.filter(n => {
                const titleMatch = (n.title || "").toLowerCase().includes(q);
                const descMatch = (n.content || "").toLowerCase().includes(q);
                const taskMatch = Array.isArray(n.tasks) && n.tasks.some(t => (t.text || "").toLowerCase().includes(q));
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
            const themeKey = note.color_theme || "spidey_red";
            const pal = THEME_PALETTES[themeKey] || THEME_PALETTES["spidey_red"];
            const isDesktop = note.desktop_visible !== false;
            const isPinned = !!note.is_pinned;
            const tasks = Array.isArray(note.tasks) ? note.tasks : [];

            const tasksHtml = tasks.map((task, idx) => `
                <div class="sticky-task-item" style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 5px 8px; border-radius: 8px; background: rgba(255, 255, 255, 0.03); transition: background 0.15s;">
                    <label style="display: flex; align-items: center; gap: 9px; cursor: pointer; flex: 1; min-width: 0;">
                        <input type="checkbox" ${task.completed ? "checked" : ""} 
                               onchange="SpiderBuddy.toggleNoteItem('${note.id}', ${idx})" 
                               style="accent-color: ${pal.accent}; width: 16px; height: 16px; cursor: pointer; border-radius: 4px;" />
                        <span style="font-size: 13px; color: ${task.completed ? "rgba(220, 228, 245, 0.45)" : "#f1f5f9"}; text-decoration: ${task.completed ? "line-through" : "none"}; word-break: break-word;">
                            ${escapeHtml(task.text || "")}
                        </span>
                    </label>
                    <button onclick="SpiderBuddy.deleteNoteItem('${note.id}', ${idx})" 
                            title="Delete task" 
                            style="background: transparent; border: none; color: rgba(255, 255, 255, 0.35); font-size: 13px; cursor: pointer; padding: 2px 6px; border-radius: 4px; transition: color 0.15s;"
                            onmouseover="this.style.color='#FF453A'" onmouseout="this.style.color='rgba(255, 255, 255, 0.35)'">✕</button>
                </div>
            `).join("");

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
                        <span>📍 X: ${note.x || 300}px • Y: ${note.y || 80}px</span>
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
        if (note) note.color_theme = theme;
        renderStickyNotesDashboard();
        await sendNoteUpdate(id, { color_theme: theme });
    }

    async function toggleNotePin(id) {
        const note = (state.stickyNotes || []).find(n => n.id === id);
        if (!note) return;
        note.is_pinned = !note.is_pinned;
        renderStickyNotesDashboard();
        await sendNoteUpdate(id, { is_pinned: note.is_pinned });
        showProfileToast(note.is_pinned ? "📌 Sticky Note pinned on top" : "📌 Sticky Note unpinned");
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
        if (note && Array.isArray(note.tasks) && note.tasks[itemIndex]) {
            note.tasks[itemIndex].completed = !note.tasks[itemIndex].completed;
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
        if (!Array.isArray(note.tasks)) note.tasks = [];
        note.tasks.push({ text: text, completed: false });

        input.value = "";
        renderStickyNotesDashboard();
        await sendNoteUpdate(id, { tasks: note.tasks });
    }

    async function deleteNoteItem(id, itemIndex) {
        const note = (state.stickyNotes || []).find(n => n.id === id);
        if (!note || !Array.isArray(note.tasks)) return;
        note.tasks.splice(itemIndex, 1);
        renderStickyNotesDashboard();
        await sendNoteUpdate(id, { tasks: note.tasks });
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
'''

# Check anchor for LOGIC_CODE
switch_tab_anchor = "    // ── Switch Tabs ───────────────────────────────────────────────────────\n    function switchTab(tabName) {"
assert switch_tab_anchor in js_content, "switchTab anchor not found!"
js_content = js_content.replace(switch_tab_anchor, LOGIC_CODE + "\n" + switch_tab_anchor, 1)

# 3. Update switchTab(tabName)
# Add notesView to view list
old_views_code = """        const profileView = document.getElementById("dashboard-profile-view");

        // First hide all views completely
        [homeView, charView, actView, deskView, focusView, controlsView, settingsView, profileView].forEach(v => {"""

new_views_code = """        const profileView = document.getElementById("dashboard-profile-view");
        const notesView = document.getElementById("dashboard-sticky-notes-view");

        // First hide all views completely
        [homeView, charView, actView, deskView, focusView, controlsView, settingsView, profileView, notesView].forEach(v => {"""

assert old_views_code in js_content, "old_views_code anchor not found!"
js_content = js_content.replace(old_views_code, new_views_code, 1)

# Add branch in switchTab
old_profile_branch = """        } else if (tabName === "Profile" || tabName === "My Profile") {
            if (profileView) {
                profileView.classList.remove("tab-hidden");
                profileView.style.setProperty("display", "flex", "important");
                loadProfileView();
            }
            updateSidebarActiveItem("Profile");
        }"""

new_profile_branch = """        } else if (tabName === "Profile" || tabName === "My Profile") {
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
        }"""

assert old_profile_branch in js_content, "old_profile_branch anchor not found!"
js_content = js_content.replace(old_profile_branch, new_profile_branch, 1)

# 4. Update updateSidebarActiveItem
old_nav_map = """            "Settings": document.querySelector('[data-framer-name="Settings"]'),
            "Profile": document.getElementById("sidebar-profile-card") || document.querySelector('[data-framer-name="My Profile"]')"""

new_nav_map = """            "Settings": document.querySelector('[data-framer-name="Settings"]'),
            "Sticky Notes": document.querySelector('[data-framer-name="Sticky Notes"]'),
            "Profile": document.getElementById("sidebar-profile-card") || document.querySelector('[data-framer-name="My Profile"]')"""

assert old_nav_map in js_content, "old_nav_map anchor not found!"
js_content = js_content.replace(old_nav_map, new_nav_map, 1)

# 5. Update sidebar bindings
old_bindings = """        // Bind Settings Tab & Options
        bindClick('[data-framer-name="Settings"]', () => switchTab("Settings"));"""

new_bindings = """        // Bind Sticky Notes & Settings Tab
        bindClick('[data-framer-name="Sticky Notes"]', () => switchTab("Sticky Notes"));
        bindClick('[data-framer-name="Settings"]', () => switchTab("Settings"));"""

assert old_bindings in js_content, "old_bindings anchor not found!"
js_content = js_content.replace(old_bindings, new_bindings, 1)

# 6. Update window.SpiderBuddy exports
old_exports = """        loadProfileView: loadProfileView,
        switchProfileSegment: switchProfileSegment,
        addToBin: addToBin,
        restoreFromBin: restoreFromBin,
        getBinCharacters: () => state.binCharacters || [],"""

new_exports = """        loadProfileView: loadProfileView,
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
        closeCreateNoteModal: closeCreateNoteModal,"""

assert old_exports in js_content, "old_exports anchor not found!"
js_content = js_content.replace(old_exports, new_exports, 1)

# Write to file
with open(JS_PATH, "w", encoding="utf-8") as f:
    f.write(js_content)

print("spider_bridge.js updated successfully! New length:", len(js_content))
