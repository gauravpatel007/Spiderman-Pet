import re
from pathlib import Path

html_path = Path("BIN/Frammer UI/index.html")
raw = html_path.read_text(encoding="utf-8")

def safe_replace(content, pattern, new_text):
    match = pattern.search(content)
    if not match:
        raise ValueError("Pattern not found")
    return content[:match.start()] + new_text + content[match.end():]

# 1. Update CSS
css_pattern = re.compile(
    r"/\* Floating Spotlight Search Results Dropdown \*/.*?(?=/\* Hide framer's old rich text node inside search field \*/)",
    re.DOTALL
)

new_css = """/* Floating Spotlight Search Results Dropdown */
    #spider-search-dropdown {
      position: absolute !important;
      top: calc(100% + 8px) !important;
      left: 0 !important;
      right: 0 !important;
      background: #0f131d !important;
      border: 1px solid rgba(255, 255, 255, 0.08) !important;
      border-top: 1px solid rgba(255, 255, 255, 0.14) !important;
      border-radius: 12px !important;
      box-shadow: 
        0 16px 40px rgba(0, 0, 0, 0.75),
        0 4px 16px rgba(0, 0, 0, 0.5),
        inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
      z-index: 99999 !important;
      overflow-y: auto !important;
      overflow-x: hidden !important;
      display: none !important;
      flex-direction: column !important;
      padding: 6px !important;
      min-width: 100% !important;
      max-height: min(490px, calc(100vh - 110px)) !important;
      contain: layout style !important;
      animation: searchDropIn 0.15s cubic-bezier(0.16, 1, 0.3, 1) both !important;
    }
    #spider-search-dropdown.visible {
      display: flex !important;
    }
    @keyframes searchDropIn {
      from { opacity: 0; transform: translateY(-4px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    #spider-search-dropdown::-webkit-scrollbar {
      display: block !important;
      width: 6px !important;
    }
    #spider-search-dropdown::-webkit-scrollbar-track {
      background: transparent !important;
    }
    #spider-search-dropdown::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.16) !important;
      border-radius: 6px !important;
    }
    #spider-search-dropdown::-webkit-scrollbar-thumb:hover {
      background: rgba(255, 255, 255, 0.3) !important;
    }

    .spider-search-result-item {
      display: flex !important;
      align-items: center !important;
      gap: 12px !important;
      padding: 10px 12px !important;
      min-height: 58px !important;
      border-radius: 10px !important;
      border: 1px solid transparent !important;
      cursor: pointer !important;
      background: transparent !important;
      transition: background 150ms ease-out, border-color 150ms ease-out !important;
      user-select: none !important;
      box-sizing: border-box !important;
      flex-shrink: 0 !important;
    }
    .spider-search-result-item:hover {
      background: #1b1f2b !important;
      border-color: rgba(255, 255, 255, 0.08) !important;
    }
    .spider-search-result-item.active {
      background: rgba(225, 29, 72, 0.12) !important;
      border-color: rgba(225, 29, 72, 0.3) !important;
    }

    .spider-search-result-icon {
      width: 32px !important;
      height: 32px !important;
      flex-shrink: 0 !important;
      border-radius: 8px !important;
      background: rgba(255, 255, 255, 0.03) !important;
      border: 1px solid rgba(255, 255, 255, 0.06) !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      color: #8f9bb3 !important;
      transition: color 150ms ease-out, background 150ms ease-out, border-color 150ms ease-out !important;
    }
    .spider-search-result-icon svg {
      width: 18px !important;
      height: 18px !important;
      stroke: currentColor !important;
      stroke-width: 2 !important;
      fill: none !important;
      stroke-linecap: round !important;
      stroke-linejoin: round !important;
      display: block !important;
    }
    .spider-search-result-item:hover .spider-search-result-icon {
      color: #e2e8f0 !important;
      background: rgba(255, 255, 255, 0.06) !important;
      border-color: rgba(255, 255, 255, 0.1) !important;
    }
    .spider-search-result-item.active .spider-search-result-icon {
      color: #ff2d55 !important;
      background: rgba(225, 29, 72, 0.14) !important;
      border-color: rgba(225, 29, 72, 0.28) !important;
    }

    .spider-search-result-text {
      flex: 1 1 auto !important;
      min-width: 0 !important;
      display: flex !important;
      flex-direction: column !important;
      justify-content: center !important;
      gap: 2px !important;
    }
    .spider-search-result-title {
      font-size: 13.5px !important;
      font-weight: 500 !important;
      color: #f1f5f9 !important;
      letter-spacing: -0.01em !important;
      white-space: nowrap !important;
      overflow: hidden !important;
      text-overflow: ellipsis !important;
      line-height: 1.35 !important;
      transition: color 150ms ease-out !important;
    }
    .spider-search-result-item.active .spider-search-result-title {
      color: #ffffff !important;
    }
    .spider-search-result-title .spider-search-highlight {
      color: #ff3b6a !important;
      font-weight: 600 !important;
      text-decoration: underline !important;
      text-decoration-color: rgba(255, 59, 106, 0.45) !important;
      text-underline-offset: 2.5px !important;
    }
    .spider-search-result-sub {
      font-size: 12px !important;
      color: #8e9bb0 !important;
      font-weight: 400 !important;
      white-space: nowrap !important;
      overflow: hidden !important;
      text-overflow: ellipsis !important;
      letter-spacing: -0.005em !important;
      line-height: 1.35 !important;
      transition: color 150ms ease-out !important;
    }
    .spider-search-result-item:hover .spider-search-result-sub {
      color: #a0aec0 !important;
    }
    .spider-search-result-item.active .spider-search-result-sub {
      color: #cbd5e1 !important;
    }

    .spider-search-result-tag {
      font-size: 11px !important;
      font-weight: 500 !important;
      color: #94a3b8 !important;
      background: rgba(255, 255, 255, 0.04) !important;
      border: 1px solid rgba(255, 255, 255, 0.08) !important;
      border-radius: 6px !important;
      padding: 2.5px 8px !important;
      flex-shrink: 0 !important;
      margin-left: auto !important;
      align-self: center !important;
      letter-spacing: 0.015em !important;
      transition: all 150ms ease-out !important;
    }
    .spider-search-result-item:hover .spider-search-result-tag {
      color: #cbd5e1 !important;
      background: rgba(255, 255, 255, 0.07) !important;
      border-color: rgba(255, 255, 255, 0.13) !important;
    }
    .spider-search-result-item.active .spider-search-result-tag {
      color: #fda4af !important;
      background: rgba(225, 29, 72, 0.16) !important;
      border-color: rgba(225, 29, 72, 0.32) !important;
    }

    .spider-search-divider {
      height: 1px !important;
      background: rgba(255, 255, 255, 0.06) !important;
      margin: 4px 0 !important;
    }
    .spider-search-empty {
      padding: 32px 16px !important;
      text-align: center !important;
      display: flex !important;
      flex-direction: column !important;
      align-items: center !important;
      justify-content: center !important;
      gap: 6px !important;
    }
    .spider-search-empty-icon {
      width: 36px !important;
      height: 36px !important;
      border-radius: 50% !important;
      background: rgba(255, 255, 255, 0.03) !important;
      border: 1px solid rgba(255, 255, 255, 0.06) !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      color: #64748b !important;
      margin-bottom: 4px !important;
    }
    .spider-search-empty-icon svg {
      width: 18px !important;
      height: 18px !important;
      stroke: currentColor !important;
      stroke-width: 2 !important;
      fill: none !important;
    }
    .spider-search-empty-title {
      font-size: 13.5px !important;
      font-weight: 500 !important;
      color: #e2e8f0 !important;
    }
    .spider-search-empty-sub {
      font-size: 12px !important;
      color: #64748b !important;
    }

    /* Light Theme Adaptivity for Search */
    html[data-theme="light"] #spider-search-dropdown {
      background: #ffffff !important;
      border-color: rgba(0, 0, 0, 0.1) !important;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.12), 0 4px 12px rgba(0, 0, 0, 0.06) !important;
    }
    html[data-theme="light"] #spider-search-dropdown::-webkit-scrollbar-thumb {
      background: rgba(0, 0, 0, 0.15) !important;
    }
    html[data-theme="light"] .spider-search-result-item:hover {
      background: #f1f5f9 !important;
      border-color: rgba(0, 0, 0, 0.06) !important;
    }
    html[data-theme="light"] .spider-search-result-item.active {
      background: rgba(225, 29, 72, 0.08) !important;
      border-color: rgba(225, 29, 72, 0.22) !important;
    }
    html[data-theme="light"] .spider-search-result-icon {
      color: #64748b !important;
      background: rgba(0, 0, 0, 0.03) !important;
      border-color: rgba(0, 0, 0, 0.06) !important;
    }
    html[data-theme="light"] .spider-search-result-item:hover .spider-search-result-icon {
      color: #1e293b !important;
      background: rgba(0, 0, 0, 0.05) !important;
    }
    html[data-theme="light"] .spider-search-result-item.active .spider-search-result-icon {
      color: #e11d48 !important;
      background: rgba(225, 29, 72, 0.1) !important;
      border-color: rgba(225, 29, 72, 0.2) !important;
    }
    html[data-theme="light"] .spider-search-result-title {
      color: #1e293b !important;
    }
    html[data-theme="light"] .spider-search-result-sub {
      color: #64748b !important;
    }
    html[data-theme="light"] .spider-search-result-tag {
      color: #64748b !important;
      background: rgba(0, 0, 0, 0.04) !important;
      border-color: rgba(0, 0, 0, 0.08) !important;
    }
    html[data-theme="light"] .spider-search-result-item.active .spider-search-result-tag {
      color: #be123c !important;
      background: rgba(225, 29, 72, 0.09) !important;
      border-color: rgba(225, 29, 72, 0.2) !important;
    }

    """

raw = safe_replace(raw, css_pattern, new_css)

# 2. Update JS
js_pattern = re.compile(
    r"<!-- Spider-Buddy Spotlight Search Logic -->\s*<script id=\"spider-search-logic\">.*?</script>",
    re.DOTALL
)

new_js = """<!-- Spider-Buddy Spotlight Search Logic -->
  <script id="spider-search-logic">
  (function () {
    // ── Lucide-Style Minimal Monochromatic Outline Icons ──
    const ICONS = {
      home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
      characters: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
      activities: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
      desktop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
      focus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
      controls: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>',
      settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
      moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
      zap: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
      rocket: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>',
      pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a1 1 0 0 0 0-2H8a1 1 0 0 0 0 2h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/></svg>',
      chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
      trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>',
      eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>',
      keyboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2" ry="2"/><line x1="6" y1="8" x2="6.01" y2="8"/><line x1="10" y1="8" x2="10.01" y2="8"/><line x1="14" y1="8" x2="14.01" y2="8"/><line x1="18" y1="8" x2="18.01" y2="8"/><line x1="6" y1="12" x2="6.01" y2="12"/><line x1="10" y1="12" x2="10.01" y2="12"/><line x1="14" y1="12" x2="14.01" y2="12"/><line x1="18" y1="12" x2="18.01" y2="12"/><line x1="7" y1="16" x2="17" y2="16"/></svg>',
      volume: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>',
      pause: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="10" y1="15" x2="10" y2="9"/><line x1="14" y1="15" x2="14" y2="9"/></svg>',
      play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>',
      music: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
      web: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M2 12h20M4.93 4.93l14.14 14.14M4.93 19.07l14.14-14.14"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="8"/></svg>',
      shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
      scale: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>',
      window: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M10 4v4"/><path d="M2 8h20"/><path d="M6 4v4"/></svg>',
      mouse: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z"/><path d="M13 13l6 6"/></svg>'
    };

    function getIconSvg(item) {
      if (item.iconKey && ICONS[item.iconKey]) return ICONS[item.iconKey];
      if (item.icon && typeof item.icon === "string" && item.icon.includes("<svg")) return item.icon;
      return ICONS.settings;
    }

    // ── Search Index: all features & settings ──────────────────────────────
    const SEARCH_INDEX = [
      { iconKey: "home",       title: "Home",             sub: "Dashboard overview & live status", tab: "Home", tag: "Tab" },
      { iconKey: "characters", title: "Characters",       sub: "Choose your active companion",     tab: "Characters", tag: "Tab" },
      { iconKey: "activities", title: "Activities",       sub: "Animations, effects & tricks",     tab: "Activities", tag: "Tab" },
      { iconKey: "desktop",    title: "Desktop & Apps",   sub: "Display scope, perching & apps", tab: "Desktop & Apps", tag: "Tab" },
      { iconKey: "focus",      title: "Focus & Breaks",   sub: "Pomodoro timers & eye health",  tab: "Focus & Breaks", tag: "Tab" },
      { iconKey: "controls",   title: "Controls",         sub: "Hotkeys, WASD & audio",           tab: "Controls", tag: "Tab" },
      { iconKey: "settings",   title: "Settings",         sub: "Preferences, FPS & diagnostics",  tab: "Settings", tag: "Tab" },
      { iconKey: "moon",       title: "Theme Mode",        sub: "Switch dark or light surface",    tab: "Settings", tag: "Setting" },
      { iconKey: "zap",        title: "Display Frame Rate",sub: "Auto, 30 FPS, or 60 FPS limit",  tab: "Settings", tag: "Setting" },
      { iconKey: "rocket",     title: "Windows Startup",  sub: "Run Spider-Buddy on login",       tab: "Settings", tag: "Setting" },
      { iconKey: "pin",        title: "Always on Top",    sub: "Float above foreground windows",  tab: "Settings", tag: "Setting" },
      { iconKey: "chart",      title: "Reset Statistics", sub: "Reset crawled distance & webs", tab: "Settings", tag: "Action" },
      { iconKey: "trash",      title: "Clear Cache",      sub: "Purge frame buffers & logs",      tab: "Settings", tag: "Action" },
      { iconKey: "eye",        title: "20-20-20 Eye Break",sub: "Vision health interval alert",  tab: "Focus & Breaks", tag: "Focus" },
      { iconKey: "keyboard",   title: "WASD Movement",    sub: "Walk, climb & crawl with WASD", tab: "Controls", tag: "Controls" },
      { iconKey: "volume",     title: "Sound Effects",    sub: "Comic audio volume & toggle",     tab: "Controls", tag: "Audio" },
      { iconKey: "pause",      title: "Pause Companion",  sub: "Temporarily pause animations",    tab: "Home", tag: "Action" },
      { iconKey: "play",       title: "Resume Companion", sub: "Resume companion activity",         tab: "Home", tag: "Action" },
      { iconKey: "music",      title: "Dance",            sub: "Trigger dance animation",         tab: "Activities", tag: "Action" },
      { iconKey: "web",        title: "Web Swing",        sub: "Acrobatic swing across screen",   tab: "Activities", tag: "Action" },
      { iconKey: "shield",     title: "Tom Holland",      sub: "MCU Spider-Man suit",             tab: "Characters", tag: "Character" },
      { iconKey: "zap",        title: "Miles Morales",    sub: "Into the Spider-Verse suit",      tab: "Characters", tag: "Character" },
      { iconKey: "shield",     title: "Spider-Gwen",      sub: "Ghost-Spider hero suit",          tab: "Characters", tag: "Character" },
      { iconKey: "scale",      title: "Companion Size",   sub: "Scale companion (100px - 400px)", tab: "Characters", tag: "Appearance" },
      { iconKey: "window",     title: "Window Perching",  sub: "Perch atop active window corners",tab: "Desktop & Apps", tag: "Display" },
      { iconKey: "mouse",      title: "Mouse Follow",     sub: "Look and crawl toward cursor",    tab: "Controls", tag: "Controls" }
    ];

    function init() {
      const input    = document.getElementById("spider-search-input");
      const clear    = document.getElementById("spider-search-clear");
      const dropdown = document.getElementById("spider-search-dropdown");
      const field    = document.querySelector('[data-framer-name="Search field"]');

      if (!input || !clear || !dropdown || !field) return;

      let activeIdx  = -1;

      // ── Ctrl+K global shortcut ──
      document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "k") {
          e.preventDefault();
          input.focus();
          input.select();
        }
        if (e.key === "Escape" && document.activeElement === input) {
          closeDropdown();
          input.blur();
        }
      });

      // Search this small local index synchronously for immediate feedback.
      input.addEventListener("input", () => {
        const q = input.value.trim();
        clear.classList.toggle("visible", q.length > 0);
        if (q.length > 0) {
          renderDropdown(q);
        } else {
          closeDropdown();
        }
        activeIdx = -1;
      });

      input.addEventListener("focus", () => {
        if (input.value.trim()) renderDropdown(input.value.trim());
      });

      // ── Clear button ──
      clear.addEventListener("click", () => {
        input.value = "";
        clear.classList.remove("visible");
        closeDropdown();
        input.focus();
      });

      // ── Mic button interaction ──
      const micBtn = document.getElementById("spider-search-mic-btn");
      if (micBtn) {
        micBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          input.focus();
          if (!dropdown.classList.contains("visible")) {
            renderDropdown(input.value.trim() || "");
          }
        });
      }

      // ── Keyboard nav inside dropdown ──
      input.addEventListener("keydown", (e) => {
        const items = dropdown.querySelectorAll(".spider-search-result-item");
        if (!items.length) return;
        if (e.key === "ArrowDown") {
          e.preventDefault();
          activeIdx = Math.min(activeIdx + 1, items.length - 1);
          updateActive(items);
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          activeIdx = Math.max(activeIdx - 1, 0);
          updateActive(items);
        } else if (e.key === "Enter") {
          e.preventDefault();
          items[Math.max(0, activeIdx)].click();
        }
      });

      // ── Click outside closes ──
      document.addEventListener("mousedown", (e) => {
        if (!field.contains(e.target)) closeDropdown();
      });

      function updateActive(items) {
        items.forEach((item, i) => {
          const isActive = (i === activeIdx);
          item.classList.toggle("active", isActive);
          item.setAttribute("aria-selected", isActive ? "true" : "false");
        });
        if (items[activeIdx]) items[activeIdx].scrollIntoView({block: "nearest"});
      }

      function closeDropdown() {
        dropdown.classList.remove("visible");
        dropdown.innerHTML = "";
        activeIdx = -1;
      }

      function renderDropdown(query) {
        const q = query.toLowerCase();
        const results = SEARCH_INDEX.filter(r =>
          r.title.toLowerCase().includes(q) ||
          r.sub.toLowerCase().includes(q) ||
          r.tag.toLowerCase().includes(q)
        );

        dropdown.innerHTML = "";

        if (!results.length) {
          dropdown.innerHTML = `
            <div class="spider-search-empty">
              <div class="spider-search-empty-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
              </div>
              <div class="spider-search-empty-title">No results for "${escHtml(query)}"</div>
              <div class="spider-search-empty-sub">Try searching for companion features, tabs, or settings</div>
            </div>
          `;
          dropdown.classList.add("visible");
          return;
        }

        results.forEach((r, i) => {
          const item = document.createElement("div");
          item.className = "spider-search-result-item" + (i === activeIdx ? " active" : "");
          item.setAttribute("role", "option");
          item.setAttribute("aria-selected", i === activeIdx ? "true" : "false");
          item.innerHTML = `
            <div class="spider-search-result-icon">${getIconSvg(r)}</div>
            <div class="spider-search-result-text">
              <div class="spider-search-result-title">${highlight(r.title, q)}</div>
              <div class="spider-search-result-sub">${r.sub}</div>
            </div>
            <span class="spider-search-result-tag">${r.tag}</span>
          `;
          item.addEventListener("mousedown", (e) => { e.preventDefault(); });
          item.addEventListener("click", () => {
            input.value = r.title;
            clear.classList.add("visible");
            closeDropdown();
            // Switch to the right tab if the nav system is available
            if (window.SpiderBuddy && typeof window.SpiderBuddy.switchTab === "function") {
              window.SpiderBuddy.switchTab(r.tab);
            } else if (typeof switchTab === "function") {
              switchTab(r.tab);
            } else {
              const navItem = document.querySelector(`[data-framer-name="${r.tab}"]`);
              if (navItem) navItem.click();
            }
          });
          dropdown.appendChild(item);
        });

        dropdown.classList.add("visible");
      }

      function highlight(text, query) {
        if (!query) return escHtml(text);
        const qTrim = query.trim().toLowerCase();
        const idx = text.toLowerCase().indexOf(qTrim);
        if (idx === -1) return escHtml(text);
        const before = escHtml(text.slice(0, idx));
        const matched = escHtml(text.slice(idx, idx + qTrim.length));
        const after = escHtml(text.slice(idx + qTrim.length));
        return before + '<span class="spider-search-highlight">' + matched + '</span>' + after;
      }

      function escHtml(str) {
        return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
      }
    }

    // Wait for DOM
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      // In case Framer renders late
      const t = setInterval(() => {
        if (document.getElementById("spider-search-input")) {
          clearInterval(t);
          init();
        }
      }, 80);
      setTimeout(() => clearInterval(t), 5000);
    }
  })();
  </script>"""

raw = safe_replace(raw, js_pattern, new_js)

html_path.write_text(raw, encoding="utf-8")
Path("BIN/Frammer UI/index").write_text(raw, encoding="utf-8")
print("SUCCESSFULLY_UPDATED_WITH_CLEAN_REPLACE")
