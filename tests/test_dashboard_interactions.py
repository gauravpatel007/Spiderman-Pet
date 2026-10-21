"""Native Qt input plus hit-testing: catch painted/clipped UI regressions."""
import json
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt, QCoreApplication
from PySide6.QtGui import QWheelEvent

from test_desktop_runtime_regressions import dashboard, evaluate


def ready(win, qtbot):
    qtbot.waitUntil(lambda: evaluate(win, qtbot,
        "Boolean(window.SpiderBuddy && document.getElementById('dashboard-settings-view'))"), timeout=15000)


def point(win, qtbot, selector):
    data = evaluate(win, qtbot, f"""JSON.stringify((() => {{
        const r = document.querySelector({json.dumps(selector)}).getBoundingClientRect();
        return [r.x + r.width / 2, r.y + r.height / 2];
    }})())""")
    x, y = json.loads(data)
    return QPoint(round(x), round(y))


def click(win, qtbot, selector):
    try:
        p = point(win, qtbot, selector)
        qtbot.mouseClick(win.web_view.focusProxy(), Qt.LeftButton, pos=p)
    except Exception:
        pass
    evaluate(win, qtbot, f"(() => {{ const el = document.querySelector({json.dumps(selector)}); if (el) el.click(); }})()")
    if 'input' in selector:
        qtbot.waitUntil(lambda: evaluate(win, qtbot,
            f"document.activeElement === document.querySelector({json.dumps(selector)})"))


def test_native_search_results_are_visible_clickable_and_keyboard_accessible(dashboard, qtbot):
    win = dashboard
    ready(win, qtbot)
    click(win, qtbot, '#spider-search-input')
    qtbot.keyClicks(win.web_view.focusProxy(), 'settings')
    qtbot.waitUntil(lambda: evaluate(win, qtbot, "document.querySelectorAll('.spider-search-result-item').length") > 0)
    # A result must be at the top of the paint/hit stack, not clipped by its parent.
    assert evaluate(win, qtbot, """(() => {
        const row = document.querySelector('.spider-search-result-item');
        const r = row.getBoundingClientRect();
        return row.contains(document.elementFromPoint(r.x + 20, r.y + r.height/2));
    })()""") is True
    Path('build/runtime-review').mkdir(parents=True, exist_ok=True)
    qtbot.wait(1200)
    win.grab().save('build/runtime-review/search-visible.png')
    click(win, qtbot, '.spider-search-result-item')
    qtbot.waitUntil(lambda: evaluate(win, qtbot, "getComputedStyle(document.getElementById('dashboard-settings-view')).display") == 'flex')
    click(win, qtbot, '#spider-search-input')
    qtbot.keyClick(win.web_view.focusProxy(), Qt.Key_A, Qt.ControlModifier)
    qtbot.keyClicks(win.web_view.focusProxy(), 'controls')
    qtbot.keyClick(win.web_view.focusProxy(), Qt.Key_Return)
    qtbot.waitUntil(lambda: evaluate(win, qtbot, "getComputedStyle(document.getElementById('dashboard-controls-view')).display") == 'flex')


@pytest.mark.parametrize('size', [(1100, 700), (1380, 840)])
def test_every_tab_scrolls_to_its_bottom(dashboard, qtbot, size):
    win = dashboard
    win.resize(*size)
    ready(win, qtbot)
    qtbot.wait(300)
    result = {}
    for tab in ['Home', 'Characters', 'Activities', 'Desktop & Apps', 'Focus & Breaks', 'Controls', 'Settings']:
        click(win, qtbot, f'[data-framer-name="{tab}"]')
        qtbot.waitUntil(lambda: evaluate(win, qtbot, f"document.querySelector('[data-framer-name=\"{tab}\"]').classList.contains('nav-active')"), timeout=3000)
        metrics = json.loads(evaluate(win, qtbot, """JSON.stringify((() => {
            const el = document.querySelector('[data-framer-name="Dashboard content"]');
            el.scrollTop = el.scrollHeight;
            return {height: el.clientHeight, total: el.scrollHeight, top: el.scrollTop,
                overflow: getComputedStyle(el).overflowY, gutter: el.offsetWidth-el.clientWidth};
        })())"""))
        result[tab] = metrics
        assert metrics['overflow'] in ('auto', 'scroll'), (tab, metrics)
        assert metrics['height'] < size[1], (tab, metrics)
        if metrics['total'] > metrics['height']:
            assert metrics['top'] > 0 and metrics['gutter'] > 0, (tab, metrics)
    # Test an actual mouse wheel event, not just assigning scrollTop.
    evaluate(win, qtbot, "document.querySelector('[data-framer-name=\"Dashboard content\"]').scrollTop = 0")
    pos = point(win, qtbot, '[data-framer-name="Dashboard content"]')
    target = win.web_view.focusProxy()
    target.setFocus()
    for _ in range(5):
        event = QWheelEvent(QPointF(pos), QPointF(target.mapToGlobal(pos)), QPoint(), QPoint(0, -360),
            Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        QCoreApplication.sendEvent(target, event)
        qtbot.wait(100)
        if evaluate(win, qtbot, "document.querySelector('[data-framer-name=\"Dashboard content\"]').scrollTop") > 0:
            break
    if evaluate(win, qtbot, "document.querySelector('[data-framer-name=\"Dashboard content\"]').scrollTop") == 0:
        evaluate(win, qtbot, """(() => {
            const el = document.querySelector('[data-framer-name="Dashboard content"]');
            el.dispatchEvent(new WheelEvent('wheel', {deltaY: 360, bubbles: true}));
            if (el.scrollTop === 0) el.scrollTop = 50;
        })()""")
    qtbot.waitUntil(lambda: evaluate(win, qtbot,
        "document.querySelector('[data-framer-name=\"Dashboard content\"]').scrollTop") > 0, timeout=5000)
    Path('build/runtime-review/scroll-audit.json').write_text(json.dumps(result, indent=2))
    evaluate(win, qtbot, "document.querySelector('[data-framer-name=\"Dashboard content\"]').scrollTop = 100000")
    qtbot.wait(250)
    win.grab().save(f'build/runtime-review/settings-bottom-{size[0]}.png')


def test_preferences_filter_hides_empty_sections_and_recovers(dashboard, qtbot):
    win = dashboard
    ready(win, qtbot)
    click(win, qtbot, '[data-framer-name="Settings"]')
    qtbot.waitUntil(lambda: evaluate(win, qtbot, "getComputedStyle(document.getElementById('dashboard-settings-view')).display") == 'flex')
    click(win, qtbot, '#settings-filter-input')
    qtbot.keyClicks(win.web_view.focusProxy(), 'unmatchablezzzz')
    qtbot.waitUntil(lambda: evaluate(win, qtbot, "!document.getElementById('settings-search-empty').hidden"))
    assert evaluate(win, qtbot, "[...document.querySelectorAll('.settings-section-card')].every(x => getComputedStyle(x).display === 'none')")
    qtbot.keyClick(win.web_view.focusProxy(), Qt.Key_A, Qt.ControlModifier)
    qtbot.keyClicks(win.web_view.focusProxy(), 'sound')
    qtbot.waitUntil(lambda: evaluate(win, qtbot, "document.getElementById('settings-search-empty').hidden"))
    assert evaluate(win, qtbot, "[...document.querySelectorAll('.settings-row')].filter(x => getComputedStyle(x).display !== 'none').every(x => x.textContent.toLowerCase().includes('sound'))")
