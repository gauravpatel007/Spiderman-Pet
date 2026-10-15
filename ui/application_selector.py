"""Persistent executable selections, including applications not currently running."""
import os
from pathlib import Path
from PySide6.QtCore import Qt,Signal,QFileInfo
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QListWidget,QListWidgetItem,QLineEdit,QFileDialog,QFileIconProvider)
from overlay.window_detector import WindowDetector
from services.settings_service import get_settings


def identity_key(identity):
    if isinstance(identity,dict):
        return os.path.normcase(identity.get('executable_path') or identity.get('process_name','')).casefold()
    return str(identity).casefold()


class ApplicationSelectorDialog(QDialog):
    applications_selected=Signal(list)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.settings=get_settings()
        self._selections=self.settings.get('general.target_applications',[])
        self.setWindowTitle('Select applications — Spider-Buddy')
        self.resize(620,560)
        layout=QVBoxLayout(self)
        title=QLabel('Choose applications that may host your companion')
        layout.addWidget(title)
        description=QLabel('Selections follow the executable, even when document titles change.\nUse Browse to add an installed application that is not running.')
        description.setWordWrap(True)
        layout.addWidget(description)
        self.app_list=QListWidget()
        layout.addWidget(self.app_list)
        custom=QHBoxLayout()
        self.custom_input=QLineEdit()
        self.custom_input.setPlaceholderText('Exact executable name, e.g. editor.exe')
        custom.addWidget(self.custom_input)
        add=QPushButton('Add')
        add.clicked.connect(self._add_custom_app)
        custom.addWidget(add)
        browse=QPushButton('Browse…')
        browse.clicked.connect(self._browse)
        custom.addWidget(browse)
        layout.addLayout(custom)
        buttons=QHBoxLayout()
        refresh=QPushButton('Refresh running apps')
        refresh.clicked.connect(self.refresh_applications)
        buttons.addWidget(refresh)
        buttons.addStretch()
        cancel=QPushButton('Cancel')
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        save=QPushButton('Save selection')
        save.clicked.connect(self._save_and_close)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        self.refresh_applications()

    def _checked(self):
        return [self.app_list.item(i).data(Qt.UserRole) for i in range(self.app_list.count())
                if self.app_list.item(i).checkState()==Qt.Checked]

    def refresh_applications(self):
        if self.app_list.count():
            self._selections=self._checked()
        windows=WindowDetector.get_visible_windows()
        rows={}
        migrated=set()
        for window in windows:
            record=window.identity
            if not record['process_name']:
                continue
            key=identity_key(record)
            checked=any(WindowDetector.matches(window,s) for s in self._selections)
            if checked:
                migrated.update(identity_key(s) for s in self._selections if WindowDetector.matches(window,s))
            rows[key]=(record,True,checked)
        for selection in self._selections:
            key=identity_key(selection)
            if key not in migrated and key not in rows:
                rows[key]=(selection,False,True)
        for record in WindowDetector.get_installed_applications():
            key = identity_key(record)
            if key not in rows:
                checked = any(identity_key(s) == key for s in self._selections)
                rows[key] = (record, False, checked)
        self.app_list.clear()
        icons=QFileIconProvider()
        for record,running,checked in sorted(rows.values(),key=lambda r: str(r[0]).casefold()):
            if isinstance(record,dict):
                name=record.get('display_name') or record.get('process_name','Application')
                process=record.get('process_name','')
                path=record.get('executable_path','')
            else:
                name=str(record)
                process='Exact legacy name — reselect a running app for path matching'
                path=''
            item=QListWidgetItem(f'{name}\n{process}  •  {"Running" if running else "Not running / saved"}')
            item.setData(Qt.UserRole,record)
            item.setToolTip(path or process)
            item.setFlags(item.flags()|Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            if path and Path(path).is_file():
                item.setIcon(icons.icon(QFileInfo(path)))
            self.app_list.addItem(item)

    def _add(self,record):
        selected=self._checked()
        selected=[s for s in selected if identity_key(s)!=identity_key(record)]
        selected.append(record)
        self._selections=selected
        self.app_list.clear()
        self.refresh_applications()

    def _browse(self):
        path,_=QFileDialog.getOpenFileName(self,'Select application executable','','Applications (*.exe)')
        if path:
            self._add({'executable_path':os.path.normpath(path),'process_name':Path(path).name,'display_name':Path(path).stem})

    def _add_custom_app(self):
        name=self.custom_input.text().strip()
        if name:
            if name.lower().endswith('.exe'):
                self._add({'executable_path':name if os.path.isabs(name) else '',
                    'process_name':Path(name).name,'display_name':Path(name).stem})
            else:
                self._add(name)
            self.custom_input.clear()

    def _save_and_close(self):
        selected=self._checked()
        self.settings.set('general.target_applications',selected)
        self.applications_selected.emit(selected)
        self.accept()
