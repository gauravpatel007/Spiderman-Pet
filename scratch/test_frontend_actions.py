import sys
import time
from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage

app = QApplication.instance() or QApplication(sys.argv)
page = QWebEnginePage()
messages = []

def on_console(level, msg, line, source):
    messages.append((level, msg, line, source))
    print(f"[{level.name}] {msg} (line {line})")

page.javaScriptConsoleMessage = on_console
html_path = Path("BIN/Frammer UI/index.html").resolve()
page.setUrl(QUrl.fromLocalFile(str(html_path)))

loaded = [False]
page.loadFinished.connect(lambda ok: loaded.__setitem__(0, True))

for _ in range(60):
    app.processEvents()
    if loaded[0]:
        break
    time.sleep(0.05)

# Wait a bit for setTimeout(init, 300) in spider_bridge.js
time.sleep(0.5)
for _ in range(20):
    app.processEvents()
    time.sleep(0.05)

def run_js(code):
    out = []
    page.runJavaScript(code, lambda res: out.append(res))
    for _ in range(20):
        app.processEvents()
        if out:
            return out[0]
        time.sleep(0.02)
    return None

print("Checking tabs switching...")
for tab in ["Characters", "Activities", "Desktop & Apps", "Focus & Breaks", "Controls", "Settings", "Home"]:
    res = run_js(f"window.SpiderBuddy.switchTab('{tab}');")
    print(f"Switched to {tab}")

print("Testing setRunning toggle...")
text_before = run_js("document.querySelector('[data-framer-name=\"Pause\"] p')?.innerText")
print(f"Pause button text initially: {text_before}")

# Trigger pause button click
run_js("document.querySelector('[data-framer-name=\"Pause\"]').click()")
for _ in range(10): app.processEvents(); time.sleep(0.02)

text_after = run_js("document.querySelector('[data-framer-name=\"Pause\"] p')?.innerText")
print(f"Pause button text after 1st click: {text_after}")

print("Testing if window.SpiderBuddy has setAudioMeter and setMusicStatus...")
has_audio = run_js("typeof window.SpiderBuddy.setAudioMeter")
has_music = run_js("typeof window.SpiderBuddy.setMusicStatus")
print(f"has setAudioMeter: {has_audio}")
print(f"has setMusicStatus: {has_music}")

print("Testing focus timer badge at 4:30 remaining...")
run_js("window.SpiderBuddy.switchTab('Focus & Breaks');")
run_js("window.SpiderBuddy.setTimer('04:30', 'Focusing');")
badge_set_timer = run_js("document.getElementById('focus-timer-badge')?.innerText")
print(f"Badge after setTimer('04:30', 'Focusing'): {ascii(badge_set_timer)}")

# Now simulate loadFocusSettings returning an active timer with 4 mins remaining (270s)
run_js("""
(() => {
    // Manually trigger the flawed logic from updateFocusSettingsUI:
    const rem = 270;
    const m = Math.floor(rem / 60);
    const bdg = document.getElementById("focus-timer-badge");
    bdg.innerText = m >= 5 ? "🛡️ Guardian Focus: Active" : "☕ Break Time (5 Min)";
})()
""")
badge_flawed = run_js("document.getElementById('focus-timer-badge')?.innerText")
print(f"Badge when updateFocusSettingsUI runs at 4:30 remaining: {ascii(badge_flawed)}")

print(f"\nAll Console errors/warnings:")
for lvl, msg, line, src in messages:
    if "Error" in lvl.name or "Warning" in lvl.name:
        print(f"  [{lvl.name}] {msg}")
