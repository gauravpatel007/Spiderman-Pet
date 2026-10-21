"""Regression test suite for Frontend Audit findings (FE-001 through FE-005)."""
import json
import pytest
from PySide6.QtCore import Qt

from tests.test_desktop_runtime_regressions import dashboard, evaluate


def ready(win, qtbot):
    qtbot.waitUntil(
        lambda: evaluate(win, qtbot, "Boolean(window.SpiderBuddy && document.getElementById('dashboard-settings-view'))"),
        timeout=15000
    )


def test_fe_001_pause_resume_toggle_and_label_sync(dashboard, qtbot):
    """FE-001: Clicking Pause button should toggle state and immediately update label between Pause and Resume."""
    win = dashboard
    ready(win, qtbot)

    # Initial state should be isRunning = true, label = 'Pause'
    initial_text = evaluate(win, qtbot, "document.querySelector('[data-framer-name=\"Pause\"] p').innerText")
    assert initial_text == "Pause"

    # Click pause button
    evaluate(win, qtbot, "document.querySelector('[data-framer-name=\"Pause\"]').click()")
    qtbot.waitUntil(
        lambda: evaluate(win, qtbot, "document.querySelector('[data-framer-name=\"Pause\"] p').innerText") == "Resume",
        timeout=3000
    )

    # Click again to resume
    evaluate(win, qtbot, "document.querySelector('[data-framer-name=\"Pause\"]').click()")
    qtbot.waitUntil(
        lambda: evaluate(win, qtbot, "document.querySelector('[data-framer-name=\"Pause\"] p').innerText") == "Pause",
        timeout=3000
    )


def test_fe_002_focus_badge_timer_under_five_minutes(dashboard, qtbot):
    """FE-002: Focus countdown badge must display 'Guardian Focus: Active' when rem > 0 even if m < 5."""
    win = dashboard
    ready(win, qtbot)

    # Simulate focus timer active with 4 minutes 30 seconds remaining (270s)
    badge_text_active = evaluate(win, qtbot, """(() => {
        window.SpiderBuddy.loadFocusSettings({
            focus_timer_active: true,
            focus_time_remaining: 270,
            continuous_work_seconds: 600,
            enable_eye_break_alert: true,
            eye_break_minutes: 10
        });
        const bdg = document.getElementById("focus-timer-badge");
        return bdg ? bdg.innerText : "";
    })()""")
    assert "Active" in badge_text_active
    assert "Break Time" not in badge_text_active

    # Now simulate countdown completion (0 seconds remaining)
    badge_text_break = evaluate(win, qtbot, """(() => {
        window.SpiderBuddy.loadFocusSettings({
            focus_timer_active: true,
            focus_time_remaining: 0,
            continuous_work_seconds: 1500,
            enable_eye_break_alert: true,
            eye_break_minutes: 10
        });
        const bdg = document.getElementById("focus-timer-badge");
        return bdg ? bdg.innerText : "";
    })()""")
    assert "Break Time" in badge_text_break


def test_fe_003_audio_meter_and_music_status_methods(dashboard, qtbot):
    """FE-003: window.SpiderBuddy must define setAudioMeter and setMusicStatus methods."""
    win = dashboard
    ready(win, qtbot)

    has_audio = evaluate(win, qtbot, "typeof window.SpiderBuddy.setAudioMeter")
    has_music = evaluate(win, qtbot, "typeof window.SpiderBuddy.setMusicStatus")
    assert has_audio == "function"
    assert has_music == "function"

    # Call methods and assert no JS exceptions are thrown
    success = evaluate(win, qtbot, """(() => {
        try {
            window.SpiderBuddy.setAudioMeter(85);
            window.SpiderBuddy.setMusicStatus("playing", 0.75);
            return true;
        } catch (e) {
            return false;
        }
    })()""")
    assert success is True


def test_fe_004_status_sync_opacity_slider(dashboard, qtbot):
    """FE-004: setTuning must update opacity slider and percentage label when opacity changes."""
    win = dashboard
    ready(win, qtbot)

    raw = evaluate(win, qtbot, """JSON.stringify((() => {
        window.SpiderBuddy.setTuning(200, 60);
        const sl = document.getElementById('slider-opacity');
        const lbl = document.getElementById('label-opacity-val');
        return {
            val: sl ? sl.value : '',
            lbl: lbl ? lbl.innerText : ''
        };
    })())""")
    res = json.loads(raw)
    assert res["val"] == "60"
    assert "60%" in res["lbl"]


def test_fe_005_home_circle_avatar_tab_return(dashboard, qtbot):
    """FE-005: Switching away from Home and returning must retain the live companion avatar frame."""
    win = dashboard
    ready(win, qtbot)

    test_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="

    # Inject frame
    evaluate(win, qtbot, f"window.SpiderBuddy.setFrame('{test_b64}')")
    src1 = evaluate(win, qtbot, "document.getElementById('companion-live-frame').src")
    assert test_b64 in src1

    # Switch away from Home
    evaluate(win, qtbot, "window.SpiderBuddy.switchTab('Activities')")

    # Switch back to Home
    evaluate(win, qtbot, "window.SpiderBuddy.switchTab('Home')")
    src2 = evaluate(win, qtbot, "document.getElementById('companion-live-frame').src")
    assert test_b64 in src2
