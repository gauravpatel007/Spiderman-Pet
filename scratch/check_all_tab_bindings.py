import re

content = open('BIN/Frammer UI/js/spider_bridge.js', encoding='utf-8').read()

def check_tab_bindings(tab_name, wrapper_name):
    # Find the HTML inside wrapper.innerHTML = `...`
    pattern = rf'{wrapper_name}\.innerHTML\s*=\s*`([^`]+)`'
    m = re.search(pattern, content)
    if not m:
        print(f'No HTML found for {tab_name} ({wrapper_name})')
        return
    html = m.group(1)
    ids_in_html = set(re.findall(r'id=["\']([^"\']+)["\']', html))
    print(f'\n--- {tab_name} (Total IDs: {len(ids_in_html)}) ---')
    
    # Check which IDs are used in JS
    for cid in sorted(ids_in_html):
        # Look outside the innerHTML assignment
        matches = len(re.findall(rf'["\']{cid}["\']|#{cid}\b', content))
        # Note: 1 match could be in innerHTML or outside
        print(f'  {cid}: total occurrences = {matches}')

check_tab_bindings('Characters', 'charactersWrapper')
check_tab_bindings('Activities', 'activitiesWrapper')
check_tab_bindings('Desktop & Apps', 'desktopWrapper')
check_tab_bindings('Focus & Breaks', 'focusWrapper')
check_tab_bindings('Controls', 'controlsWrapper')
