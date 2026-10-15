import os
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['APPDATA']=str(Path.cwd()/'build'/'ui-review-user')
from app.bootstrap import ensure_site_packages
ensure_site_packages()
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from services.settings_service import get_settings
from core.character_manager import CharacterManager
from ui.main_window import MainWindow
app=QApplication([])
from PySide6.QtGui import QFontDatabase, QFont
for filename in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf','seguiemj.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+filename)
app.setFont(QFont('Segoe UI',10))
mgr=CharacterManager();mgr.set_active_character('miles_morales')
window=MainWindow(mgr)
window.show()
out=Path('build/ui-review');out.mkdir(parents=True,exist_ok=True)
for theme in ('dark','light'):
    get_settings().set('general.theme',theme)
    for width,height in ((940,720),(1280,900),(720,560)):
        window.resize(width,height)
        for index,name in ((1,'characters'),(3,'applications'),(5,'behavior')):
            window.navigation.setCurrentRow(index)
            if hasattr(window,'_fade'):window._fade.stop()
            effect=window.pages.graphicsEffect()
            if effect:effect.setOpacity(1)
            for _ in range(4):app.processEvents()
            window.grab().save(str(out/f'{theme}-{name}-{width}.png'))
            if index==1:
                cards=list(window.char_selection_widget.cards.values())
                print(theme,width,'grid',window.char_selection_widget.width(),[(c.width(),c.height(),c.x()) for c in cards],flush=True)
window.hide()
