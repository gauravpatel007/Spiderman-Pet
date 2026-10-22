# Script to construct and verify the sticky notes injection into spider_bridge.js
import os
import re

JS_PATH = r"g:\Languages\Projects\Pet\Pet A2 Final\Frontend\js\spider_bridge.js"

with open(JS_PATH, "r", encoding="utf-8") as f:
    content = f.read()

print("Original JS length:", len(content))
assert "contentArea.appendChild(profileWrapper);" in content
assert "function switchTab(tabName) {" in content
assert "updateSidebarActiveItem(activeName) {" in content
assert 'bindClick(\'[data-framer-name="Settings"]\'' in content
print("All anchor points verified successfully!")
