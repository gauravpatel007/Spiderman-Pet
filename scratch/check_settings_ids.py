import re

content = open('BIN/Frammer UI/js/spider_bridge.js', encoding='utf-8').read()
m = re.search(r'settingsWrapper\.innerHTML\s*=\s*`([^`]+)`', content)
if m:
    html = m.group(1)
    ids_in_html = set(re.findall(r'id=["\']([^"\']+)["\']', html))
    print(f'Total IDs in settings HTML: {len(ids_in_html)}')
    check_ids = [
        'toggle-settings-dodge', 'toggle-settings-mouse-follow', 'toggle-settings-comic-bubbles',
        'toggle-settings-heavy-load', 'toggle-settings-music-sync', 'toggle-settings-battery',
        'toggle-settings-suit-glitch', 'toggle-settings-sound', 'slider-settings-sound-vol',
        'label-settings-sound-vol-val', 'toggle-settings-eye-alert', 'toggle-settings-hotkeys',
        'toggle-settings-hotkeys-mod', 'toggle-settings-wasd', 'toggle-settings-wasd-pin',
        'slider-settings-speed', 'label-settings-speed-val', 'toggle-settings-auto-anim'
    ]
    for cid in check_ids:
        print(f'{cid}: in HTML? {cid in ids_in_html}')
else:
    print('No settingsWrapper.innerHTML found')
