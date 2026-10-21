import re

content = open('BIN/Frammer UI/js/spider_bridge.js', encoding='utf-8').read()
# Let's inspect lines 1650 to 2220
lines = content.splitlines()[1650:2220]
for i, line in enumerate(lines, 1651):
    if any(k in line for k in ['addEventListener', 'sendAction', 'getElementById']):
        print(f'{i}: {line[:120]}')
