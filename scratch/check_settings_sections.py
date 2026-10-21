import re

content = open('BIN/Frammer UI/js/spider_bridge.js', encoding='utf-8').read()
m = re.search(r'settingsWrapper\.innerHTML\s*=\s*`([^`]+)`', content)
if m:
    html = m.group(1)
    sections = re.findall(r'<div[^>]*class=["\']([^"\']*(?:settings-section|apple-glass-card)[^"\']*)["\']', html)
    print('Sections in settings HTML:')
    for s in sections:
        print('  Section class:', s)
