import re

with open('BIN/Frammer UI/js/spider_bridge.js', 'r', encoding='utf-8') as f:
    js_code = f.read()

with open('ui/web_window.py', 'r', encoding='utf-8') as f:
    py_code = f.read()

dispatched = set(re.findall(r'sendAction\(\s*["\']([^"\']+)["\']', js_code))
print(f'Total actions dispatched in JS: {len(dispatched)}')
print('Dispatched actions in JS:')
for a in sorted(dispatched):
    print(f'  JS: {a}')

handled = set(re.findall(r'action\s*==\s*["\']([^"\']+)["\']', py_code))
print(f'\nTotal actions handled in web_window.py: {len(handled)}')
print('Handled actions in Python:')
for a in sorted(handled):
    print(f'  PY: {a}')

unhandled_in_py = dispatched - handled
print(f'\nDispatched in JS but NOT handled in Python: {len(unhandled_in_py)}')
for a in sorted(unhandled_in_py):
    print(f'  UNHANDLED: {a}')

unhandled_in_js = handled - dispatched
print(f'\nHandled in Python but NOT dispatched in JS: {len(unhandled_in_js)}')
for a in sorted(unhandled_in_js):
    print(f'  UNUSED_IN_PY: {a}')
