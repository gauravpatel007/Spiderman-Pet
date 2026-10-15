"""Logical work areas and native-to-Qt coordinate conversion per monitor."""
from PySide6.QtCore import QObject,QRect,QPoint,Signal
from PySide6.QtGui import QGuiApplication


class MonitorManager(QObject):
    screens_changed=Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self._screens=[]
        app=QGuiApplication.instance()
        if app:
            app.screenAdded.connect(self._changed)
            app.screenRemoved.connect(self._changed)
            app.primaryScreenChanged.connect(self._changed)
        self._connect_screens()

    def _connect_screens(self):
        app=QGuiApplication.instance()
        current=app.screens() if app else []
        for screen in current:
            if screen not in self._screens:
                for signal in (screen.geometryChanged,screen.availableGeometryChanged,
                               screen.logicalDotsPerInchChanged):
                    signal.connect(self._changed)
        self._screens=current

    def _changed(self,*args):
        self._connect_screens()
        self.screens_changed.emit()

    def get_primary_screen(self):
        return QGuiApplication.primaryScreen()

    def get_primary_work_area(self):
        screen=self.get_primary_screen()
        return screen.availableGeometry() if screen else QRect(0,0,1920,1080)

    def work_areas(self,selection='primary'):
        screens=QGuiApplication.screens()
        if selection=='all':
            return [s.availableGeometry() for s in screens]
        screen=next((s for s in screens if s.name()==selection),None) if selection!='primary' else None
        return [(screen or self.get_primary_screen()).availableGeometry()] if screens else [QRect(0,0,1920,1080)]

    def get_virtual_desktop_rect(self):
        rect=QRect()
        for area in self.work_areas('all'):
            rect=rect.united(area)
        return rect

    def get_screen_at(self,x,y):
        return QGuiApplication.screenAt(QPoint(x,y))

    def window_regions(self,physical_rect):
        """Split a native window across physical displays before converting DPI."""
        native={}
        try:
            import win32api
            for handle,_,_ in win32api.EnumDisplayMonitors():
                info=win32api.GetMonitorInfo(handle)
                native[info['Device']]=info['Monitor']
        except ImportError:
            pass
        regions=[]
        for screen in QGuiApplication.screens():
            logical=screen.geometry()
            dpr=screen.devicePixelRatio()
            coords=native.get(screen.name())
            if coords:
                l,t,r,b=coords
                monitor=QRect(l,t,r-l,b-t)
            else:
                monitor=QRect(logical.x(),logical.y(),round(logical.width()*dpr),round(logical.height()*dpr))
            part=physical_rect.intersected(monitor)
            if part.isEmpty():
                continue
            # Round inward so no pixel escapes a selected window.
            import math
            left=logical.x()+math.ceil((part.x()-monitor.x())/dpr)
            top=logical.y()+math.ceil((part.y()-monitor.y())/dpr)
            right=logical.x()+math.floor((part.x()+part.width()-monitor.x())/dpr)
            bottom=logical.y()+math.floor((part.y()+part.height()-monitor.y())/dpr)
            area=QRect(left,top,max(0,right-left),max(0,bottom-top)).intersected(screen.availableGeometry())
            if not area.isEmpty():
                regions.append(area)
        return regions
