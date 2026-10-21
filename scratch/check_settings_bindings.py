import re

content = open('BIN/Frammer UI/js/spider_bridge.js', encoding='utf-8').read()
m = re.search(r'settingsWrapper\.innerHTML\s*=\s*`([^`]+)`', content)
if m:
    html = m.group(1)
    ids_in_html = set(re.findall(r'id=["\']([^"\']+)["\']', html))
    print(f'Total IDs in settings HTML: {len(ids_in_html)}')
    
    # Check which IDs appear outside innerHTML
    after_html = content[content.find(m.group(0)) + len(m.group(0)):]
    
    unbound_ids = []
    bound_ids = []
    for cid in sorted(ids_in_html):
        # Look for getElementById(cid) or querySelector(#cid)
        if f'"{cid}"' in after_html or f"'{cid}'" in after_html or f'#{cid}' in after_html:
            bound_ids.append(cid)
        else:
            unbound_ids.append(cid)
            
    print(f'Bound IDs ({len(bound_ids)}):')
    for cid in bound_ids:
        print(f'  [BOUND] {cid}')
    print(f'\nUnbound IDs ({len(unbound_ids)}):')
    for cid in unbound_ids:
        print(f'  [UNBOUND] {cid}')
