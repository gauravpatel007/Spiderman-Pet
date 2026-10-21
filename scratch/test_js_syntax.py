import sys
from pathlib import Path
from PySide6.QtCore import QUrl, QCoreApplication
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage

app = QApplication.instance() or QApplication(sys.argv)

page = QWebEnginePage()
messages = []

def on_console(level, msg, line, source):
    messages.append((level, msg, line, source))
    print(f"[{level}] {source}:{line} - {msg}")

page.javaScriptConsoleMessage = on_console

html_path = Path("BIN/Frammer UI/index.html").resolve()
url = QUrl.fromLocalFile(str(html_path))
page.setUrl(url)

loaded = [False]
def on_load(ok):
    loaded[0] = True

page.loadFinished.connect(on_load)

for _ in range(50):
    app.processEvents()
    if loaded[0]:
        break
    import time
    time.sleep(0.05)

print(f"Page loaded: {loaded[0]}")
print(f"Total console messages: {len(messages)}")

# Test evaluating window.SpiderBuddy
res = []
page.runJavaScript("Boolean(window.SpiderBuddy)", lambda val: res.append(val))

for _ in range(20):
    app.processEvents()
    if res:
        break
    import time
    time.sleep(0.05)

print(f"window.SpiderBuddy exists: {res}")
