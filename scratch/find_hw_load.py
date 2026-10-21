with open('BIN/Frammer UI/index.html', encoding='utf-8') as f:
    text = f.read()

import re
idx = text.find('data-framer-name="Hardware load"')
if idx != -1:
    print(text[idx:idx+1500])
