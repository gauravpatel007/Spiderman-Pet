import os,subprocess,time,json
from pathlib import Path
from app.bootstrap import ensure_site_packages
ensure_site_packages()
from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalSocket
app=QCoreApplication([])
socket=QLocalSocket();socket.connectToServer('SpiderBuddy_Singleton_Lock_Key')
if socket.waitForConnected(300):
    socket.disconnectFromServer()
    print('Skipped executable launch: a companion is already running.')
else:
    root=Path.cwd();data=root/'build'/'packaged-smoke-user'
    env=dict(os.environ,APPDATA=str(data),QT_QPA_PLATFORM='offscreen')
    process=subprocess.Popen([str(root/'dist/verified/SpiderBuddy/SpiderBuddy.exe')],env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline=time.monotonic()+60
        logfile=data/'SpiderBuddy'/'logs'/'spider_buddy.log'
        while time.monotonic()<deadline:
            if logfile.exists() and 'Spider-Buddy launched successfully!' in logfile.read_text(encoding='utf-8'):
                break
            if process.poll() is not None:break
            time.sleep(.25)
        log=logfile.read_text(encoding='utf-8') if logfile.exists() else ''
        result={'executable_startup': 'Spider-Buddy launched successfully!' in log,
                'alive_after_startup': process.poll() is None,
                'traceback': 'Traceback' in log, 'shutdown':'test harness termination; graceful shutdown verified in source tests'}
        (root/'build/packaged-smoke-result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result))
    finally:
        if process.poll() is None:
            process.terminate();process.wait(timeout=10)

