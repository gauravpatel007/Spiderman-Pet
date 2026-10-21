from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QKeySequence, QShortcut, QPixmap, QPainter, QPen, QColor, QFont, QIcon
from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QTabWidget,
                             QPushButton, QCheckBox, QComboBox, QSpinBox, QSlider)


DESTINATIONS = [
    ('Home', 'Your desktop. A little more alive.', 'Your companion, at a glance.'),
    ('Characters', 'Choose your companion', 'One active companion. A personality of their own.'),
    ('Activities', 'A little character goes a long way', 'Choose what your companion can do. Preferences apply to all characters.'),
    ('Desktop & Apps', 'Find their place', 'Choose where your companion appears and how they sit on your windows.'),
    ('Focus & Breaks', 'Make room for focus', 'Quiet company while you work. A gentle reminder when it is time to pause.'),
    ('Controls', 'On your terms', 'Set up keyboard shortcuts and mouse interactions.'),
    ('Settings', 'The essentials', 'Window appearance, startup and rendering preferences.'),
]


class DashboardDesign:
    def _initialize_destinations(self):
        self._routes = {}
        self._sections = {}
        for name, title, description in DESTINATIONS:
            self._page(name, title, description)

    def _section(self, route, title):
        key = (route, title)
        if key not in self._sections:
            card = QFrame()
            card.setObjectName('ActivityCategoryCard')
            card.setProperty('sectionTitle', title)
            content = QVBoxLayout(card)
            content.setContentsMargins(20, 18, 20, 18)
            content.setSpacing(12)
            label = QLabel(title)
            label.setObjectName('subheading')
            content.addWidget(label)
            self._routes[route].addWidget(card)
            self._sections[key] = content
        return self._sections[key]

    def _activity_group(self, title):
        if not hasattr(self, 'activity_tabs'):
            self.activity_tabs = QTabWidget()
            self.activity_tabs.setObjectName('ActivityTabs')
            self.activity_tabs.setDocumentMode(False)
            self.activity_tabs.setUsesScrollButtons(True)
            self.activity_tabs.setElideMode(Qt.ElideNone)
            self.activity_tabs.tabBar().wheelEvent = lambda event: event.ignore()
            self.activity_tabs.setStyleSheet("""
                QTabWidget, QTabWidget::pane {
                    background: transparent;
                    border: none;
                }
                QTabWidget > QWidget {
                    background: transparent;
                }
                QTabBar {
                    background: transparent;
                    border: none;
                }
                QTabBar::tab {
                    color: #94A3B8;
                    background: #181824;
                    padding: 8px 14px;
                    margin-right: 4px;
                    border: 1px solid #282838;
                    border-bottom: 2px solid transparent;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    font-weight: 600;
                    font-size: 11px;
                }
                QTabBar::tab:selected {
                    color: #FFFFFF;
                    background: #252538;
                    border-bottom: 2px solid #BA2444;
                }
                QTabBar::tab:hover {
                    color: #FFFFFF;
                    background: #202030;
                }
            """)
            self._routes['Activities'].addWidget(self.activity_tabs)
            self._activity_groups = {}
        if title not in self._activity_groups:
            body = QWidget()
            layout = QVBoxLayout(body)
            layout.setContentsMargins(0, 16, 0, 0)
            layout.setSpacing(14)
            layout.setAlignment(Qt.AlignTop)
            self.activity_tabs.addTab(body, title)
            self._activity_groups[title] = layout
        return self._activity_groups[title]

    def _create_search_icon_pixmap(self, color_str="#9CA3B5"):
        pix = QPixmap(36, 36)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(color_str), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawEllipse(7, 7, 13, 13)
        p.drawLine(17, 17, 26, 26)
        p.end()
        return pix

    def _create_bell_icon_pixmap(self, color_str="#9CA3B5"):
        pix = QPixmap(36, 36)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(color_str), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawArc(12, 9, 12, 12, 0, 180 * 16)
        p.drawLine(12, 15, 10, 21)
        p.drawLine(24, 15, 26, 21)
        p.drawLine(8, 21, 28, 21)
        p.drawArc(16, 21, 4, 4, 180 * 16, 180 * 16)
        p.end()
        return pix

    def _create_gear_icon_pixmap(self, color_str="#9CA3B5"):
        pix = QPixmap(36, 36)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(color_str), 1.6)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawEllipse(13, 13, 10, 10)
        p.drawLine(18, 9, 18, 11)
        p.drawLine(18, 25, 18, 27)
        p.drawLine(9, 18, 11, 18)
        p.drawLine(25, 18, 27, 18)
        p.drawLine(12, 12, 13, 13)
        p.drawLine(23, 23, 24, 24)
        p.drawLine(24, 12, 23, 13)
        p.drawLine(12, 24, 13, 23)
        p.end()
        return pix

    def _update_search_theme(self, light: bool):
        if hasattr(self, 'search_icon_label'):
            color = "#9CA3B5" if light else "#767E96"
            self.search_icon_label.setPixmap(self._create_search_icon_pixmap(color))

    def _install_search(self, layout):
        # Outer frosted glass pill container
        self.search_container = QFrame()
        self.search_container.setObjectName("searchGlassContainer")
        container_layout = QHBoxLayout(self.search_container)
        container_layout.setContentsMargins(8, 7, 8, 7)
        container_layout.setSpacing(0)

        # Inner pill bar
        self.search_pill = QFrame()
        self.search_pill.setObjectName("searchInnerPill")
        self.search_pill.setFixedWidth(420)
        pill_layout = QHBoxLayout(self.search_pill)
        pill_layout.setContentsMargins(14, 0, 12, 0)
        pill_layout.setSpacing(10)

        # Search icon
        self.search_icon_label = QLabel()
        self.search_icon_label.setObjectName("searchIconLabel")
        self.search_icon_label.setFixedSize(16, 16)
        self.search_icon_label.setScaledContents(True)
        self.search_icon_label.setPixmap(self._create_search_icon_pixmap("#9CA3B5"))
        pill_layout.addWidget(self.search_icon_label)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setObjectName("settingsSearch")
        self.search_input.setPlaceholderText("Find a feature or setting...  (Ctrl + K)")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setAccessibleName("Search all settings")
        pill_layout.addWidget(self.search_input, 1)

        # Shortcut badges container: [Ctrl] · [K]
        self.search_badges = QWidget()
        self.search_badges.setObjectName("searchBadgesWidget")
        badge_layout = QHBoxLayout(self.search_badges)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setSpacing(4)

        self.search_badge_ctrl = QLabel("Ctrl")
        self.search_badge_ctrl.setObjectName("searchBadgeKey")
        badge_layout.addWidget(self.search_badge_ctrl)

        self.search_badge_dot = QLabel("·")
        self.search_badge_dot.setObjectName("searchBadgeDot")
        badge_layout.addWidget(self.search_badge_dot)

        self.search_badge_k = QLabel("K")
        self.search_badge_k.setObjectName("searchBadgeKey")
        badge_layout.addWidget(self.search_badge_k)

        pill_layout.addWidget(self.search_badges)
        container_layout.addWidget(self.search_pill)
        container_layout.addStretch()

        # Status badge: ● Companion Active
        self.top_companion_badge = QFrame()
        self.top_companion_badge.setObjectName("topCompanionBadge")
        badge_l = QHBoxLayout(self.top_companion_badge)
        badge_l.setContentsMargins(10, 4, 12, 4)
        badge_l.setSpacing(6)
        c_dot = QLabel("●")
        c_dot.setStyleSheet("color: #21D9A0; font-size: 11px;")
        c_lbl = QLabel("Companion Active")
        c_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px; font-weight: 600; font-family: 'Segoe UI';")
        badge_l.addWidget(c_dot)
        badge_l.addWidget(c_lbl)
        container_layout.addWidget(self.top_companion_badge)

        # Notification bell
        font_win = QFont("Segoe UI", 11, QFont.Bold)

        self.top_btn_bell = QPushButton()
        self.top_btn_bell.setObjectName("topHeaderBtn")
        self.top_btn_bell.setIcon(QIcon(self._create_bell_icon_pixmap("#9CA3B5")))
        self.top_btn_bell.setIconSize(QSize(18, 18))
        self.top_btn_bell.setStyleSheet("background-color: #151729; border: 1px solid #1E2235; border-radius: 8px;")
        self.top_btn_bell.setFixedSize(32, 32)
        container_layout.addWidget(self.top_btn_bell)

        # Settings gear
        self.top_btn_settings = QPushButton()
        self.top_btn_settings.setObjectName("topHeaderBtn")
        self.top_btn_settings.setIcon(QIcon(self._create_gear_icon_pixmap("#9CA3B5")))
        self.top_btn_settings.setIconSize(QSize(18, 18))
        self.top_btn_settings.setStyleSheet("background-color: #151729; border: 1px solid #1E2235; border-radius: 8px;")
        self.top_btn_settings.setFixedSize(32, 32)
        self.top_btn_settings.clicked.connect(lambda: self.navigation.setCurrentRow(6))
        container_layout.addWidget(self.top_btn_settings)

        # Window controls: — □ ✕
        self.top_btn_min = QPushButton("—")
        self.top_btn_min.setObjectName("topWinBtn")
        self.top_btn_min.setFont(font_win)
        self.top_btn_min.setStyleSheet("background-color: transparent; border: none; color: #FFFFFF; font-family: 'Segoe UI'; font-size: 14px; font-weight: bold;")
        self.top_btn_min.setFixedSize(28, 28)
        self.top_btn_min.clicked.connect(self.showMinimized)
        container_layout.addWidget(self.top_btn_min)

        self.top_btn_max = QPushButton("□")
        self.top_btn_max.setObjectName("topWinBtn")
        self.top_btn_max.setFont(font_win)
        self.top_btn_max.setStyleSheet("background-color: transparent; border: none; color: #FFFFFF; font-family: 'Segoe UI'; font-size: 14px; font-weight: bold;")
        self.top_btn_max.setFixedSize(28, 28)
        self.top_btn_max.clicked.connect(lambda: self.showNormal() if self.isMaximized() else self.showMaximized())
        container_layout.addWidget(self.top_btn_max)

        self.top_btn_close = QPushButton("✕")
        self.top_btn_close.setObjectName("topWinBtnClose")
        self.top_btn_close.setFont(font_win)
        self.top_btn_close.setStyleSheet("background-color: transparent; border: none; color: #FFFFFF; font-family: 'Segoe UI'; font-size: 14px; font-weight: bold;")
        self.top_btn_close.setFixedSize(28, 28)
        self.top_btn_close.clicked.connect(self.close)
        container_layout.addWidget(self.top_btn_close)

        layout.addWidget(self.search_container)

        self.search_results = QListWidget()
        self.search_results.setObjectName("settingsSearchResults")
        self.search_results.setMaximumHeight(200)
        self.search_results.hide()
        layout.addWidget(self.search_results)

        # Delegate clicks anywhere in the capsule to input focus
        def focus_search(event):
            self.search_input.setFocus()
            event.accept()

        self.search_container.mousePressEvent = focus_search
        self.search_pill.mousePressEvent = focus_search
        self.search_icon_label.mousePressEvent = focus_search
        self.search_badges.mousePressEvent = focus_search

        # Dynamic focus property for styling
        orig_focus_in = self.search_input.focusInEvent
        orig_focus_out = self.search_input.focusOutEvent
        def on_focus_in(event):
            orig_focus_in(event)
            self.search_pill.setProperty("focused", True)
            self.search_pill.style().unpolish(self.search_pill)
            self.search_pill.style().polish(self.search_pill)
        def on_focus_out(event):
            orig_focus_out(event)
            self.search_pill.setProperty("focused", False)
            self.search_pill.style().unpolish(self.search_pill)
            self.search_pill.style().polish(self.search_pill)
        self.search_input.focusInEvent = on_focus_in
        self.search_input.focusOutEvent = on_focus_out

        # Auto-hide badges when text is entered
        self.search_input.textChanged.connect(lambda txt: self.search_badges.setVisible(not bool(txt)))

        self.search_input.textChanged.connect(self._search_settings)
        self.search_input.returnPressed.connect(self._open_first_search_result)
        self.search_results.itemActivated.connect(self._open_search_result)
        self.search_results.itemClicked.connect(self._open_search_result)
        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self.search_input.setFocus)
        self._search_shortcut = shortcut

    def _index_search(self):
        self._search_entries = []
        for index, (scroll, body, _) in enumerate(self._page_scroll_areas):
            route = self.navigation.item(index).text()
            for widget in body.findChildren(QWidget):
                if not isinstance(widget, (QCheckBox, QComboBox, QSlider, QSpinBox, QPushButton)):
                    continue
                label = widget.property('searchLabel')
                key = widget.property('settingKey') or ''
                if not label:
                    label = widget.text() if isinstance(widget, (QCheckBox, QPushButton)) else widget.accessibleName()
                if not label or not str(label).strip():
                    continue
                aliases = ''
                if any(word in str(label).lower() for word in ('music', 'audio')):
                    aliases += ' headphones beat bobbing music audio'
                if 'application' in str(label).lower():
                    aliases += ' chrome vscode executable selected apps'
                if 'focus' in str(label).lower():
                    aliases += ' study quiet stop moving reading'
                if 'size' in str(label).lower():
                    aliases += ' bigger smaller scale'
                if 'opacity' in str(label).lower():
                    aliases += ' transparent transparency'
                if 'break' in str(label).lower():
                    aliases += ' hydration water eyes reminder'
                self._search_entries.append((index, str(label), route, widget,
                    (str(label)+' '+key+' '+route+aliases).lower()))

    def _search_settings(self, text):
        self.search_results.clear()
        words = text.lower().split()
        if not words:
            self.search_results.hide()
            return
        for entry in self._search_entries:
            if all(word in entry[4] for word in words):
                item = QListWidgetItem(f'{entry[1]}  ·  {entry[2]}')
                item.setData(Qt.UserRole, self._search_entries.index(entry))
                self.search_results.addItem(item)
                if self.search_results.count() >= 12:
                    break
        if not self.search_results.count():
            item = QListWidgetItem('No matching settings. Try “music”, “size” or “keyboard”.')
            item.setFlags(Qt.NoItemFlags)
            self.search_results.addItem(item)
        self.search_results.setCurrentRow(0)
        self.search_results.show()

    def _open_first_search_result(self):
        if self.search_results.count():
            self._open_search_result(self.search_results.item(0))

    def _open_search_result(self, item):
        entry_id = item.data(Qt.UserRole)
        if entry_id is None:
            return
        index, label, _, target, _ = self._search_entries[entry_id]
        self.navigation.setCurrentRow(index)
        parent = target
        while parent is not None:
            if hasattr(self, 'activity_tabs'):
                tab_index = self.activity_tabs.indexOf(parent)
                if tab_index >= 0:
                    self.activity_tabs.setCurrentIndex(tab_index)
            parent = parent.parentWidget()
        quick = getattr(self, "qml_pages", {}).get(index)
        if quick is not None and self.qml_page_hosts[index].currentWidget() is quick:
            self.search_input.clear()
            quick.setFocus(Qt.ShortcutFocusReason)
            self.qml_bridge.revealRequested.emit(str(target.property("settingKey") or target.property("searchLabel") or label))
            return
        self.search_input.clear()
        def reveal():
            self._page_scroll_areas[index][0].ensureWidgetVisible(target, 24, 70)
            target.setFocus(Qt.ShortcutFocusReason)
            target.setProperty('searchMatch', True)
            target.style().unpolish(target)
            target.style().polish(target)
        def clear_highlight():
            target.setProperty('searchMatch', False)
            target.style().unpolish(target)
            target.style().polish(target)
        QTimer.singleShot(0, reveal)
        QTimer.singleShot(1600, target, clear_highlight)

    def _finish_design(self):
        order = ['Movement', 'Rest', 'Expressions', 'Windows', 'Music & Sound', 'Effects', 'System', 'Timing', 'Transitions']
        for index, title in enumerate(order):
            current = self.activity_tabs.indexOf(self._activity_groups[title].parentWidget())
            self.activity_tabs.tabBar().moveTab(current, index)
        self.activity_tabs.setCurrentIndex(0)
        # Every page has one header, consistent readable text and no emoji-heavy labels.
        for _, body, layout in self._page_scroll_areas:
            for label in body.findChildren(QLabel):
                label.setWordWrap(True)
                label.setMinimumWidth(0)
            for widget in body.findChildren(QWidget):
                if isinstance(widget, (QLabel, QPushButton, QCheckBox)):
                    text = widget.text()
                    while text and (ord(text[0]) > 0xffff or text[0] in '⚡▶✓🎯🪟🕸️🔋💧🏗️🎧✨🧘🏃⌨️💬'):
                        text = text[1:].lstrip('\ufe0f ')
                    widget.setText(text)
            layout.addStretch()
        self.toggle_btn.setProperty('primary', True)
        self.spin_eye_break_mins.setProperty('searchLabel', 'Work-break reminder interval')
        self.animation_combo.setProperty('searchLabel', 'Choose activity for playback')
        self._index_search()
