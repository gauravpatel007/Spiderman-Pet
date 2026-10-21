with open('BIN/Frammer UI/js/spider_bridge.js', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if any(k in line for k in ['function loadFocusSettings', 'function updateFocusSettingsUI', 'function loadControlSettings', 'function updateControlSettingsUI', 'function loadDisplaySettings', 'function updateDisplaySettingsUI']):
            print(f'{i}: {line.strip()}')
