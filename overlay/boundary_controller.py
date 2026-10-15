"""Visible movement regions for selected applications and desktop monitors."""
from PySide6.QtCore import QObject,QRect,Signal


class BoundaryController(QObject):
    bounds_changed=Signal(QRect)
    regions_changed=Signal(list)
    visibility_changed=Signal(bool)

    def __init__(self,monitor_mgr,parent=None):
        super().__init__(parent)
        self.monitor_mgr=monitor_mgr
        self.mode='desktop'
        self.monitor_selection='primary'
        self.current_bounds=monitor_mgr.get_primary_work_area()
        self.current_regions=[self.current_bounds]
        self.is_character_visible=True
        monitor_mgr.screens_changed.connect(self._on_display_changed)

    def set_mode(self,mode):
        if mode not in ('desktop','application'):
            return
        self.mode=mode
        if mode=='desktop':
            self.set_desktop_bounds()
        else:
            self._set_regions([])

    def _set_regions(self,regions):
        regions=[QRect(r) for r in regions if not r.isEmpty()]
        self.current_regions=regions
        bounds=QRect()
        for region in regions:
            bounds=bounds.united(region)
        self.current_bounds=bounds
        self.regions_changed.emit(regions)
        self.bounds_changed.emit(bounds)
        visible=bool(regions)
        self.is_character_visible=visible
        self.visibility_changed.emit(visible)

    def set_desktop_bounds(self):
        self._set_regions(self.monitor_mgr.work_areas(self.monitor_selection))

    def update_application_regions(self,regions):
        if self.mode=='application':
            self._set_regions(regions)

    def update_application_bounds(self,window_rect,is_minimized,is_target_active):
        regions=[window_rect] if window_rect and not is_minimized and is_target_active else []
        self.update_application_regions(regions)

    def _on_display_changed(self,*args):
        if self.mode=='desktop':
            self.set_desktop_bounds()
