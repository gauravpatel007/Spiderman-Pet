from pathlib import Path
p = Path("overlay/overlay_manager.py")
text = p.read_text(encoding="utf-8")

old = """            if not window or not window.is_visible or window.is_minimized:
                # Fallback to monitor ceiling so Spider-Man can always hang from screen top
                active_area = self.movement.active_region() or (self.movement.regions[0] if self.movement.regions else None)
                if active_area is None:
                    return False
                area = active_area
            else:
                candidates = [part.intersected(allowed)
                              for part in self.monitor_mgr.window_regions(window.rect)
                              for allowed in self.movement.regions]
                candidates = [a for a in candidates if a.width() >= self.movement.width and a.height() >= self.movement.height]
                if not candidates:
                    active_area = self.movement.active_region() or (self.movement.regions[0] if self.movement.regions else None)
                    if active_area is None:
                        return False
                    area = active_area
                else:
                    area = min(candidates, key=lambda r: (r.top(), -r.right()))

            offset = max(0, min(120, int(self.settings.get('animations.title_bar_offset', 28))))"""

new = """            if not window or not window.is_visible or window.is_minimized:
                return False

            candidates = [part.intersected(allowed)
                          for part in self.monitor_mgr.window_regions(window.rect)
                          for allowed in self.movement.regions]
            candidates = [a for a in candidates if a.width() >= self.movement.width and a.height() >= self.movement.height]
            if not candidates:
                return False
            area = min(candidates, key=lambda r: (r.top(), -r.right()))

            settings = getattr(self, 'settings', None) or get_settings()
            offset = max(0, min(120, int(settings.get('animations.title_bar_offset', 28))))"""

text = text.replace(old.replace("\r\n", "\n"), new.replace("\r\n", "\n"))
p.write_text(text, encoding="utf-8")
print("Updated overlay_manager.py position_activity successfully!")
