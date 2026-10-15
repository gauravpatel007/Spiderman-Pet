"""Native settings dashboard with shared, live settings bindings."""
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QPixmap, QPalette, QColor
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QListWidget, QStackedWidget, QScrollArea, QComboBox, QCheckBox,
    QSlider, QSpinBox, QFormLayout, QGraphicsOpacityEffect, QFrame, QGridLayout)
from .character_selection import CharacterSelectionWidget
from .application_selector import ApplicationSelectorDialog
from services.settings_service import get_settings
from core.activity_policy import ACTIVITIES, LEGACY_FLAGS, enabled as is_activity_enabled


class MainWindow(QMainWindow):
    start_requested = Signal()
    stop_requested = Signal()
    character_changed = Signal(str)
    display_mode_changed = Signal(str)
    size_changed = Signal(int)
    activity_requested = Signal(str)
    save_position_requested = Signal()
    test_glitch_requested = Signal()
    simulate_low_battery_toggled = Signal(bool)

    def __init__(self, character_mgr, parent=None):
        super().__init__(parent)
        self.character_mgr = character_mgr
        self.settings = get_settings()
        self._bindings = {}
        self._is_running = True
        self._status_text = "Status: Idle"
        self.setWindowTitle('Spider-Buddy — Desktop Companion')
        self.setMinimumSize(720, 520)
        self.resize(940, 720)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Top-left application icon & logo
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "spiderman_face.png"
        if not logo_path.exists():
            logo_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "tray.png"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        # Left Sidebar Container
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(12)
        sidebar.setFixedWidth(188)
        sidebar.setObjectName("sidebar")

        # Top-Left: Logo of only red spiderman face only
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(8, 4, 8, 8)
        logo_layout.setAlignment(Qt.AlignLeft)

        self.top_logo_label = QLabel()
        if logo_path.exists():
            face_pix = QPixmap(str(logo_path)).scaled(30, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.top_logo_label.setPixmap(face_pix)
        logo_layout.addWidget(self.top_logo_label)
        brand = QVBoxLayout()
        brand.setSpacing(2)
        brand.addWidget(QLabel('SPIDER-BUDDY'))
        tagline = QLabel('Desktop companion')
        tagline.setObjectName('muted')
        tagline.setStyleSheet('font-size: 10px;')
        brand.addWidget(tagline)
        logo_layout.addLayout(brand)
        logo_layout.addStretch()
        sidebar_layout.addWidget(logo_container)

        self.navigation = QListWidget()
        self.navigation.setObjectName('navigation')
        self.navigation.setSpacing(3)
        self.navigation.setUniformItemSizes(True)
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sidebar_layout.addWidget(self.navigation, 1)
        footer = QLabel('YOUR DESKTOP, WITH COMPANY')
        footer.setWordWrap(True)
        footer.setObjectName('muted')
        footer.setStyleSheet('font-size: 9px; padding: 8px;')
        sidebar_layout.addWidget(footer)

        self.pages = QStackedWidget()
        layout.addWidget(sidebar)
        layout.addWidget(self.pages, 1)
        self._build_dashboard()
        page = self._page('Characters', 'Choose your companion', 'Switch instantly. One character stays active at a time.')
        self.char_selection_widget = CharacterSelectionWidget(character_mgr)
        self.char_selection_widget.character_selected.connect(self.character_changed.emit)
        page.addWidget(self.char_selection_widget)
        page.addStretch()
        self._build_display()
        self._build_applications()
        self._build_animations()
        self._build_behavior()
        self._build_appearance()
        self._build_settings()
        self.navigation.currentRowChanged.connect(self._navigate)
        self.navigation.setCurrentRow(0)
        self.settings.setting_changed.connect(self._sync)
        self.character_mgr.character_changed.connect(self._character_updated)
        QGuiApplication.instance().screenAdded.connect(self._refresh_monitors)
        QGuiApplication.instance().screenRemoved.connect(self._refresh_monitors)
        self._refresh_monitors()
        self._update_applications()
        self._character_updated(character_mgr.active_character)
        self.apply_theme()

    def _page(self, name, title, description):
        self.navigation.addItem(name)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        page = QVBoxLayout(body)
        page.setContentsMargins(12, 8, 20, 20)
        page.setSpacing(16)
        heading = QLabel(title)
        heading.setObjectName('heading')
        page.addWidget(heading)
        note = QLabel(description)
        note.setWordWrap(True)
        note.setObjectName('muted')
        page.addWidget(note)
        scroll.setWidget(body)
        self.pages.addWidget(scroll)
        return page

    def _button(self, layout, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def _combo(self, layout, label, key, choices):
        layout.addWidget(QLabel(label))
        combo = QComboBox()
        for text, value in choices:
            combo.addItem(text, value)
        combo.setCurrentIndex(max(0, combo.findData(self.settings.get(key))))
        combo.currentIndexChanged.connect(lambda index: self.settings.set(key, combo.itemData(index)) if index >= 0 else None)
        self._bindings[key] = (combo, 'combo', 1, None)
        layout.addWidget(combo)
        return combo

    def _check(self, layout, label, key, default=True):
        check = QCheckBox(label)
        check.setChecked(bool(self.settings.get(key, default)))
        check.toggled.connect(lambda value: self.settings.set(key, value))
        self._bindings[key] = (check, 'check', 1, None)
        layout.addWidget(check)
        return check

    def _slider(self, layout, label, key, low, high, factor=1, suffix=''):
        row = QHBoxLayout()
        caption = QLabel(label)
        value_label = QLabel()
        row.addWidget(caption)
        row.addStretch()
        row.addWidget(value_label)
        layout.addLayout(row)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(low, high)
        slider.setValue(round(float(self.settings.get(key, low/factor))*factor))
        value_label.setText(f'{slider.value()}{suffix}')
        slider.valueChanged.connect(lambda value: value_label.setText(f'{value}{suffix}'))
        slider.valueChanged.connect(lambda value: self.settings.set(key, value/factor))
        self._bindings[key] = (slider, 'slider', factor, (value_label, suffix))
        layout.addWidget(slider)
        return slider

    def _build_dashboard(self):
        page = self._page('Dashboard', 'Spider-Buddy', 'A small companion for your desktop and favorite apps.')
        self.preview = QLabel()
        self.preview.setMinimumHeight(220)
        self.preview.setAlignment(Qt.AlignCenter)
        page.addWidget(self.preview)
        self.active_label = QLabel('Loading character…')
        self.active_label.setObjectName('subheading')
        self.active_label.setAlignment(Qt.AlignCenter)
        page.addWidget(self.active_label)
        self.status_label = QLabel('Status: Idle')
        self.status_label.setAlignment(Qt.AlignCenter)
        page.addWidget(self.status_label)
        self.overlay_owner_label = QLabel('Companion starting…')
        self.overlay_owner_label.setWordWrap(True)
        page.addWidget(self.overlay_owner_label)
        row = QHBoxLayout()
        self.toggle_btn = self._button(row, 'Pause', self._toggle_running_state)
        self.hide_btn = self._button(row, 'Show character' if self.settings.get('general.hidden', False) else 'Hide character',
            lambda: self.settings.set('general.hidden', not self.settings.get('general.hidden', False)))
        page.addLayout(row)
        self.dashboard_apps = QLabel()
        page.addWidget(self.dashboard_apps)

        # Focus Mode Quick Toggle Card
        focus_card = QFrame()
        focus_card.setObjectName('ActivityCategoryCard')
        fc_layout = QVBoxLayout(focus_card)
        fc_layout.setContentsMargins(14, 12, 14, 12)
        fc_layout.setSpacing(6)

        fc_title = QLabel('🎯 Focus Mode (Study & Work)')
        fc_title.setObjectName('subheading')
        fc_layout.addWidget(fc_title)

        fc_desc = QLabel(
            'During focus mode, Spider-Man puts on reading glasses and sits quietly in the corner '
            'reading a comic book so you can work or study uninterrupted.'
        )
        fc_desc.setWordWrap(True)
        fc_desc.setObjectName('muted')
        fc_layout.addWidget(fc_desc)

        self.focus_mode_chk = QCheckBox('Activate Focus Mode (Reading Glasses & Comic Book in Corner)')
        self.focus_mode_chk.setChecked(bool(self.settings.get('behavior.focus_mode', False)))
        self.focus_mode_chk.toggled.connect(lambda val: self.settings.set('behavior.focus_mode', val))
        fc_layout.addWidget(self.focus_mode_chk)
        page.addWidget(focus_card)

        page.addStretch()

    def _build_display(self):
        page = self._page('Display Mode', 'Where your companion lives', 'Application mode keeps the entire character inside the selected foreground window.')
        self._combo(page, 'Display mode', 'general.display_mode', [('Entire desktop', 'desktop'), ('Selected applications', 'application')])
        self.monitor_combo = self._combo(page, 'Desktop monitor', 'general.monitor', [('Primary monitor', 'primary'), ('All monitors', 'all')])
        self.monitor_combo.setEnabled(self.settings.get('general.display_mode') == 'desktop')
        policy = QLabel('In application mode, the character hides when its app is minimized, closed, too small, or no longer in front.')
        policy.setWordWrap(True)
        page.addWidget(policy)
        self._button(page, 'Choose applications', self._open_application_selector)
        page.addStretch()

    def _build_applications(self):
        page = self._page('Applications', 'Selected applications', 'Select running apps, registered apps, or browse to an executable.')
        self.app_count_label = QLabel()
        page.addWidget(self.app_count_label)
        self.app_list = QListWidget()
        self.app_list.setObjectName("app_list")
        self.app_list.setSpacing(4)
        self.app_list.setMinimumHeight(160)
        page.addWidget(self.app_list)
        self._button(page, 'Add or remove applications', self._open_application_selector)

    def _build_animations(self):
        page = self._page(
            'Animations',
            'Activity & Animation Selection',
            'Choose which activities Spider-Man can perform. Unchecked activities will be excluded from autonomous roaming, animations, and manual play.'
        )

        # 1. Preview & Play Section
        play_card = QFrame()
        play_card.setObjectName('ActivityCategoryCard')
        play_layout = QVBoxLayout(play_card)
        play_layout.setContentsMargins(14, 12, 14, 12)
        play_layout.setSpacing(8)

        play_title = QLabel('Try an Activity on Companion')
        play_title.setObjectName('subheading')
        play_layout.addWidget(play_title)

        play_hint = QLabel('Select any currently enabled activity to test it on Spider-Man immediately:')
        play_hint.setObjectName('muted')
        play_layout.addWidget(play_hint)

        play_row = QHBoxLayout()
        self.animation_combo = QComboBox()
        self.animation_combo.setMinimumWidth(260)
        play_row.addWidget(self.animation_combo, 1)
        self.play_button = QPushButton('▶ Play Activity')
        self.play_button.setProperty('primary', 'true')
        self.play_button.clicked.connect(self._on_play_button_clicked)
        play_row.addWidget(self.play_button)
        play_layout.addLayout(play_row)
        page.addWidget(play_card)

        # 2. Quick Actions Toolbar & Counter
        toolbar_row = QHBoxLayout()
        self.activity_count_label = QLabel('Configuring activities…')
        self.activity_count_label.setStyleSheet('font-weight: 600; font-size: 13px;')
        toolbar_row.addWidget(self.activity_count_label)
        toolbar_row.addStretch()

        btn_select_all = QPushButton('Select All')
        btn_select_all.clicked.connect(self._select_all_activities)
        toolbar_row.addWidget(btn_select_all)

        btn_deselect_all = QPushButton('Deselect All')
        btn_deselect_all.clicked.connect(self._deselect_all_activities)
        toolbar_row.addWidget(btn_deselect_all)

        btn_reset = QPushButton('Reset Defaults')
        btn_reset.clicked.connect(self._reset_activity_defaults)
        toolbar_row.addWidget(btn_reset)
        page.addLayout(toolbar_row)

        self._activity_checkboxes = {}

        # 3. Featured Card: Perching on Window Title Bars & Tab Strips
        window_perch_card = QFrame()
        window_perch_card.setObjectName('ActivityCategoryCard')
        wp_layout = QVBoxLayout(window_perch_card)
        wp_layout.setContentsMargins(14, 12, 14, 12)
        wp_layout.setSpacing(10)

        wp_header = QLabel('🪟 Perching on Window Title Bars & Tab Strips')
        wp_header.setObjectName('subheading')
        wp_layout.addWidget(wp_header)

        wp_desc = QLabel(
            'Instead of just staying at the bottom edge, Spider-Buddy uses GetWindowRect to calculate '
            'the top title bar and tab strips of active apps. Spider-Man can sit upside down hanging from '
            'the title bar or perch like a gargoyle on the top-right corner.'
        )
        wp_desc.setWordWrap(True)
        wp_desc.setObjectName('muted')
        wp_layout.addWidget(wp_desc)

        # Master Toggle for Window Perching
        is_perching_enabled = bool(self.settings.get('animations.enable_window_perching', True))
        self.window_perch_master_check = QCheckBox('Enable Perching on Window Title Bars & Tab Strips')
        self.window_perch_master_check.setStyleSheet('font-weight: 600; font-size: 13px;')
        self.window_perch_master_check.setChecked(is_perching_enabled)
        self.window_perch_master_check.toggled.connect(self._on_window_perch_master_toggled)
        wp_layout.addWidget(self.window_perch_master_check)

        # Sub-panel containing options & fine-tuning
        self.window_perch_sub_panel = QWidget()
        sub_layout = QVBoxLayout(self.window_perch_sub_panel)
        sub_layout.setContentsMargins(16, 4, 8, 4)
        sub_layout.setSpacing(10)

        # Sub-activity 1: Gargoyle Perch
        perch_box = QWidget()
        perch_layout = QVBoxLayout(perch_box)
        perch_layout.setContentsMargins(0, 0, 0, 0)
        perch_layout.setSpacing(2)
        self.title_perch_chk = QCheckBox('Perch and peek over top-right corner of open windows (Peeking pose)')
        self.title_perch_chk.setChecked(is_activity_enabled(self.settings, 'title_perch'))
        self.title_perch_chk.toggled.connect(lambda val: self._on_activity_toggled('title_perch', val))
        perch_desc = QLabel('Detects the top-right header/title bar of active application windows and perches peeking over the edge with hands clutching the window top bar.')
        perch_desc.setObjectName('muted')
        perch_desc.setStyleSheet('font-size: 11px; padding-left: 22px;')
        perch_layout.addWidget(self.title_perch_chk)
        perch_layout.addWidget(perch_desc)
        sub_layout.addWidget(perch_box)
        self._activity_checkboxes['title_perch'] = self.title_perch_chk

        # Sub-activity 2: Hang from Title Bar
        hang_box = QWidget()
        hang_layout = QVBoxLayout(hang_box)
        hang_layout.setContentsMargins(0, 0, 0, 0)
        hang_layout.setSpacing(2)
        self.title_hang_chk = QCheckBox('Hang upside-down from title bar / tab strip (Web anchor)')
        self.title_hang_chk.setChecked(is_activity_enabled(self.settings, 'title_hang'))
        self.title_hang_chk.toggled.connect(lambda val: self._on_activity_toggled('title_hang', val))
        hang_desc = QLabel('Anchors a visible web strand to the title bar and suspends Spider-Man inverted over your workspace.')
        hang_desc.setObjectName('muted')
        hang_desc.setStyleSheet('font-size: 11px; padding-left: 22px;')
        hang_layout.addWidget(self.title_hang_chk)
        hang_layout.addWidget(hang_desc)
        sub_layout.addWidget(hang_box)
        self._activity_checkboxes['title_hang'] = self.title_hang_chk

        # Slider for Title Bar Vertical Offset adjustment
        offset_header = QHBoxLayout()
        offset_title = QLabel('Vertical alignment offset with tabs:')
        self.title_offset_val_lbl = QLabel(f"{int(self.settings.get('animations.title_bar_offset', 28))} px")
        self.title_offset_val_lbl.setStyleSheet('font-weight: 600;')
        offset_header.addWidget(offset_title)
        offset_header.addStretch()
        offset_header.addWidget(self.title_offset_val_lbl)
        sub_layout.addLayout(offset_header)

        self.title_offset_slider = QSlider(Qt.Horizontal)
        self.title_offset_slider.setRange(0, 80)
        self.title_offset_slider.setValue(int(self.settings.get('animations.title_bar_offset', 28)))
        self.title_offset_slider.valueChanged.connect(lambda val: (
            self.title_offset_val_lbl.setText(f"{val} px"),
            self.settings.set('animations.title_bar_offset', val)
        ))
        sub_layout.addWidget(self.title_offset_slider)

        self.window_perch_sub_panel.setEnabled(is_perching_enabled)
        wp_layout.addWidget(self.window_perch_sub_panel)
        page.addWidget(window_perch_card)

        # 4. Featured Card: Laptop Battery Saver & Spider-Verse Glitch
        battery_card = QFrame()
        battery_card.setObjectName('ActivityCategoryCard')
        bat_layout = QVBoxLayout(battery_card)
        bat_layout.setContentsMargins(14, 12, 14, 12)
        bat_layout.setSpacing(10)

        bat_header = QLabel('🔋 Laptop Battery Saver & Spider-Verse Glitch')
        bat_header.setObjectName('subheading')
        bat_layout.addWidget(bat_header)

        bat_desc = QLabel(
            'On laptops, when battery drops below 15%: Spider-Man looks exhausted (slows down pace, '
            'takes frequent breathers) and his suit flickers with a Spider-Verse chromatic aberration glitch effect.'
        )
        bat_desc.setWordWrap(True)
        bat_desc.setObjectName('muted')
        bat_layout.addWidget(bat_desc)

        bat_row = QHBoxLayout()
        self.battery_status_lbl = QLabel('🔋 Reading system power status…')
        self.battery_status_lbl.setStyleSheet('font-weight: 600; font-size: 13px;')
        bat_row.addWidget(self.battery_status_lbl, 1)

        self.btn_test_glitch = QPushButton('⚡ Preview Glitch Effect')
        self.btn_test_glitch.clicked.connect(self._on_test_glitch_clicked)
        bat_row.addWidget(self.btn_test_glitch)
        bat_layout.addLayout(bat_row)

        self.chk_simulate_battery = QCheckBox('Simulate Low Battery (<15%) & Suit Exhaustion Mode')
        self.chk_simulate_battery.toggled.connect(self.simulate_low_battery_toggled.emit)
        bat_layout.addWidget(self.chk_simulate_battery)

        page.addWidget(battery_card)

        # 5. Standard Categorized Activity Checkboxes
        categories = [
            (
                "🏃 Locomotion & Movement",
                [
                    ("walk", "Walk", "Walking along ground or ledge"),
                    ("run", "Run", "Fast running / sprinting"),
                    ("jump", "Jump", "Leaping acrobatic jump"),
                    ("fall", "Fall", "Airborne falling pose"),
                    ("land", "Land", "Crouch landing on surface"),
                    ("climb_up", "Climb Up", "Vertical climbing up edges"),
                    ("climb_down", "Climb Down", "Vertical climbing down edges"),
                    ("wall_slide", "Wall Slide", "Sliding down walls / windows"),
                    ("swing", "Web Swing", "Pendulum web swinging across screen"),
                ],
            ),
            (
                "🧘 Rest & Postures",
                [
                    ("idle", "Idle", "Standing and looking around breathing"),
                    ("sit", "Sit", "Sitting on available surfaces"),
                    ("sleep", "Sleep", "Sleeping curled up or in hammock"),
                    ("wake_up", "Wake Up", "Transition from sleeping"),
                    ("stand_up", "Stand Up", "Transition from sitting"),
                    ("perch", "Perch", "Crouched perched pose"),
                    ("hang", "Hang", "Hanging upside down"),
                ],
            ),
            (
                "✨ Expressions & Specials",
                [
                    ("wave", "Wave", "Friendly waving greeting to user"),
                    ("dance", "Dance", "Animated celebratory dance"),
                    ("celebrate", "Celebrate", "Happy victory celebration"),
                    ("interact", "Poke Reaction", "Reaction to mouse click or poke"),
                ],
            ),
            (
                "🎯 Focus Mode & Mouse Interactions",
                [
                    ("focus_read", "Focus Comic Reading", "Read comic book quietly in focus mode"),
                    ("dragged", "Mouse Dragged", "Dangling pose when dragged by mouse"),
                ],
            ),
        ]

        for cat_title, items in categories:
            cat_card = QFrame()
            cat_card.setObjectName('ActivityCategoryCard')
            cat_layout = QVBoxLayout(cat_card)
            cat_layout.setContentsMargins(14, 12, 14, 12)
            cat_layout.setSpacing(10)

            title_lbl = QLabel(cat_title)
            title_lbl.setObjectName('subheading')
            cat_layout.addWidget(title_lbl)

            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(8)

            for idx, (anim_id, anim_title, anim_desc) in enumerate(items):
                row = idx // 2
                col = idx % 2

                item_container = QWidget()
                item_layout = QVBoxLayout(item_container)
                item_layout.setContentsMargins(0, 0, 0, 0)
                item_layout.setSpacing(2)

                chk = QCheckBox(anim_title)
                chk.setToolTip(f"{anim_title}: {anim_desc}")
                chk.setChecked(is_activity_enabled(self.settings, anim_id))
                chk.toggled.connect(lambda val, aid=anim_id: self._on_activity_toggled(aid, val))

                desc_lbl = QLabel(anim_desc)
                desc_lbl.setObjectName('muted')
                desc_lbl.setStyleSheet('font-size: 11px; padding-left: 22px;')

                item_layout.addWidget(chk)
                item_layout.addWidget(desc_lbl)

                self._activity_checkboxes[anim_id] = chk
                grid.addWidget(item_container, row, col)

            cat_layout.addLayout(grid)
            page.addWidget(cat_card)

        page.addStretch()

    def _on_window_perch_master_toggled(self, checked: bool):
        self.settings.set('animations.enable_window_perching', checked)
        if hasattr(self, 'window_perch_sub_panel'):
            self.window_perch_sub_panel.setEnabled(checked)
        self._sync_animation_checkboxes()
        self._refresh_activity_options()

    def _on_activity_toggled(self, name: str, checked: bool):
        self.settings.set(f"animations.enabled.{name}", checked)
        if name in LEGACY_FLAGS:
            legacy_key = LEGACY_FLAGS[name]
            if legacy_key == 'climbing':
                up = self.settings.get('animations.enabled.climb_up', True)
                down = self.settings.get('animations.enabled.climb_down', True)
                self.settings.set('behavior.enable_climbing', up or down)
            else:
                self.settings.set(f"behavior.enable_{legacy_key}", checked)
        self._refresh_activity_options()
        self._update_activity_count_label()

    def _select_all_activities(self):
        self.settings.set('animations.enable_window_perching', True, auto_save=False)
        for name in ACTIVITIES:
            self.settings.set(f"animations.enabled.{name}", True, auto_save=False)
            if name in LEGACY_FLAGS:
                self.settings.set(f"behavior.enable_{LEGACY_FLAGS[name]}", True, auto_save=False)
        self.settings.set('behavior.enable_climbing', True, auto_save=False)
        self.settings.save()
        if hasattr(self, 'window_perch_master_check'):
            self.window_perch_master_check.blockSignals(True)
            self.window_perch_master_check.setChecked(True)
            self.window_perch_master_check.blockSignals(False)
        if hasattr(self, 'window_perch_sub_panel'):
            self.window_perch_sub_panel.setEnabled(True)
        self._sync_animation_checkboxes()
        self._refresh_activity_options()

    def _deselect_all_activities(self):
        self.settings.set('animations.enable_window_perching', False, auto_save=False)
        for name in ACTIVITIES:
            val = True if name == 'idle' else False
            self.settings.set(f"animations.enabled.{name}", val, auto_save=False)
            if name in LEGACY_FLAGS:
                self.settings.set(f"behavior.enable_{LEGACY_FLAGS[name]}", val, auto_save=False)
        self.settings.set('behavior.enable_climbing', False, auto_save=False)
        self.settings.save()
        if hasattr(self, 'window_perch_master_check'):
            self.window_perch_master_check.blockSignals(True)
            self.window_perch_master_check.setChecked(False)
            self.window_perch_master_check.blockSignals(False)
        if hasattr(self, 'window_perch_sub_panel'):
            self.window_perch_sub_panel.setEnabled(False)
        self._sync_animation_checkboxes()
        self._refresh_activity_options()

    def _reset_activity_defaults(self):
        self._select_all_activities()

    def _sync_animation_checkboxes(self):
        for name, chk in getattr(self, '_activity_checkboxes', {}).items():
            chk.blockSignals(True)
            chk.setChecked(is_activity_enabled(self.settings, name))
            chk.blockSignals(False)
        self._update_activity_count_label()

    def _update_activity_count_label(self):
        if not hasattr(self, 'activity_count_label') or not hasattr(self, '_activity_checkboxes'):
            return
        total = len(self._activity_checkboxes)
        enabled_count = sum(1 for name in self._activity_checkboxes if is_activity_enabled(self.settings, name))
        self.activity_count_label.setText(f"Active Activities: {enabled_count} of {total} enabled")

    def _build_behavior(self):
        page = self._page('Behavior', 'Set the pace', 'Choose a calm companion or a more playful one. Settings apply immediately.')
        self._combo(page, 'Activity frequency', 'behavior.preset', [('Calm', 'calm'), ('Normal', 'normal'), ('Playful', 'playful')])

        # Interactive FX Card
        fx_card = QFrame()
        fx_card.setObjectName('ActivityCategoryCard')
        fx_layout = QVBoxLayout(fx_card)
        fx_layout.setContentsMargins(14, 12, 14, 12)
        fx_layout.setSpacing(6)

        fx_title = QLabel('⚡ Interactive Features & Reactions')
        fx_title.setObjectName('subheading')
        fx_layout.addWidget(fx_title)

        fx_desc = QLabel('Control Spider-Sense cursor dodges and stylized pop-up comic dialogue bubbles.')
        fx_desc.setWordWrap(True)
        fx_desc.setObjectName('muted')
        fx_layout.addWidget(fx_desc)

        self._check(fx_layout, '⚡ "Spider-Sense" Dodging (Hops & flips out of the way on fast cursor approach)', 'behavior.enable_spider_sense_dodging', True)
        self._check(fx_layout, '💬 Comic Speech & Reaction Bubbles (Pop-up dialogue balloons with spring animation)', 'behavior.enable_comic_bubbles', True)
        page.addWidget(fx_card)

        for label, key in [('Walking','walking'), ('Running','running'), ('Jumping','jumping'), ('Sleeping','sleeping'),
                           ('Sitting','sitting'), ('Wall climbing','climbing'), ('Web swinging','swinging'), ('Hanging','hanging'),
                           ('Mouse attention','mouse_following'), ('Random activities','random_animations')]:
            self._check(page, label, 'behavior.enable_'+key)
        self._slider(page, 'Movement speed', 'behavior.movement_speed', 1, 6)
        page.addWidget(QLabel('Inactivity thresholds (minutes)'))
        form = QFormLayout()
        for label, key in [('Relax after', 'relax_seconds'), ('Sit after', 'sit_seconds'), ('Sleep after', 'sleep_seconds')]:
            box = QSpinBox()
            box.setRange(1, 120)
            path = 'behavior.inactivity.'+key
            box.setValue(round(float(self.settings.get(path, 120))/60))
            box.valueChanged.connect(lambda value, path=path: self.settings.set(path, value*60))
            self._bindings[path] = (box, 'slider', 1/60, None)
            form.addRow(label, box)
        page.addLayout(form)
        note = QLabel('Thresholds run in order: relaxing, sitting, then sleeping. Later stages cannot begin before earlier stages.')
        note.setWordWrap(True)
        page.addWidget(note)
        page.addStretch()

    def _build_appearance(self):
        page = self._page('Appearance', 'Make it yours', 'Transparent artwork scales smoothly. Facing follows movement and cursor attention.')
        self.size_slider = self._slider(page, 'Character size', 'general.scale', 100, 400, 200, ' px')
        self._slider(page, 'Opacity', 'general.opacity', 50, 100, 100, '%')
        self._combo(page, 'Animation speed', 'general.animation_speed', [('Slow', .65), ('Normal', 1.0), ('Fast', 1.5)])
        self._combo(page, 'Display frame rate', 'general.display_fps', [('Automatic', 0), ('30 FPS', 30), ('60 FPS', 60)])
        self._combo(page, 'Default position', 'general.default_position', [('Bottom left', 'bottom_left'), ('Bottom right', 'bottom_right'), ('Custom', 'custom')])
        self._button(page, 'Use current character position as custom', self.save_position_requested.emit)
        self._check(page, 'Sound effects', 'behavior.sound_enabled', False)
        self._slider(page, 'Sound volume', 'behavior.sound_volume', 0, 100, 100, '%')
        page.addStretch()

    def _build_settings(self):
        page = self._page('Settings', 'Application preferences', 'Changes are saved automatically. Closing this window keeps the companion in the system tray.')
        self._combo(page, 'Theme', 'general.theme', [('Dark', 'dark'), ('Light', 'light')])
        self._check(page, 'Start with dashboard minimized', 'system.start_minimized', True)
        self._check(page, 'Launch Spider-Buddy when Windows starts', 'system.run_on_startup', False)
        self._check(page, 'Pass all mouse clicks through the character', 'system.click_through', False)
        note = QLabel('With click-through enabled, use this dashboard or the system tray to control the companion.')
        note.setWordWrap(True)
        page.addWidget(note)
        page.addStretch()

    def _navigate(self, index):
        self.pages.setCurrentIndex(index)
        if index == 0 and hasattr(self, '_last_preview'):
            self.update_preview(self._last_preview)
        # Short transition on page changes only; no permanent animation loop.
        if hasattr(self, '_fade'):
            self._fade.stop()
            self._fade.deleteLater()
        effect = QGraphicsOpacityEffect(self.pages)
        self.pages.setGraphicsEffect(effect)
        self._fade = QPropertyAnimation(effect, b'opacity', self)
        self._fade.setDuration(140)
        self._fade.setStartValue(.5)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)
        self._fade.start()

    def _sync(self, key, value):
        binding = self._bindings.get(key)
        if binding:
            control, kind, factor, label = binding
            control.blockSignals(True)
            if kind == 'check':
                control.setChecked(bool(value))
            elif kind == 'combo':
                control.setCurrentIndex(control.findData(value))
            else:
                control.setValue(round(float(value)*factor))
                if label:
                    label[0].setText(f'{control.value()}{label[1]}')
            control.blockSignals(False)
        if key == 'animations.enable_window_perching':
            if hasattr(self, 'window_perch_master_check'):
                self.window_perch_master_check.blockSignals(True)
                self.window_perch_master_check.setChecked(bool(value))
                self.window_perch_master_check.blockSignals(False)
            if hasattr(self, 'window_perch_sub_panel'):
                self.window_perch_sub_panel.setEnabled(bool(value))
            self._sync_animation_checkboxes()
            self._refresh_activity_options()
        elif key == 'animations.title_bar_offset':
            if hasattr(self, 'title_offset_slider'):
                self.title_offset_slider.blockSignals(True)
                self.title_offset_slider.setValue(int(value))
                self.title_offset_slider.blockSignals(False)
            if hasattr(self, 'title_offset_val_lbl'):
                self.title_offset_val_lbl.setText(f"{int(value)} px")
        elif key.startswith('behavior.enable_') or key.startswith('animations.enabled.'):
            self._sync_animation_checkboxes()
            self._refresh_activity_options()
        if key == 'general.theme':
            self.apply_theme()
        elif key == 'general.target_applications':
            self._update_applications()
        elif key == 'general.display_mode':
            self.monitor_combo.setEnabled(value == 'desktop')
        elif key == 'general.hidden':
            self.hide_btn.setText('Show character' if value else 'Hide character')
        elif key == 'behavior.focus_mode':
            if hasattr(self, 'focus_mode_chk'):
                self.focus_mode_chk.blockSignals(True)
                self.focus_mode_chk.setChecked(bool(value))
                self.focus_mode_chk.blockSignals(False)

    def _refresh_monitors(self, *args):
        combo = self.monitor_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem('Primary monitor', 'primary')
        combo.addItem('All monitors', 'all')
        for screen in QGuiApplication.screens():
            combo.addItem(screen.name(), screen.name())
        combo.setCurrentIndex(max(0, combo.findData(self.settings.get('general.monitor', 'primary'))))
        combo.blockSignals(False)

    def _open_application_selector(self):
        dialog = ApplicationSelectorDialog(self)
        dialog.exec()
        self._update_applications()

    def _update_applications(self):
        apps = self.settings.get('general.target_applications', [])
        self.app_list.clear()
        for app in apps:
            self.app_list.addItem((app.get('display_name') or app.get('process_name') or app.get('executable_path', 'Application')) if isinstance(app, dict) else str(app))
        text = f'{len(apps)} selected applications'
        self.app_count_label.setText(text)
        self.dashboard_apps.setText(text)

    def _character_updated(self, profile):
        if profile is None:
            return
        self.active_label.setText(profile.display_name)
        self._refresh_activity_options()
        from PySide6.QtGui import QPixmap
        self.update_preview(QPixmap(str(profile.root_path/"preview.png")))

    def _refresh_activity_options(self):
        profile = self.character_mgr.active_character
        if profile is None:
            return
        previous = self.animation_combo.currentData()
        self.animation_combo.clear()
        
        # Populate all supported character animations + special window activities
        actions = list(profile.supported_animations)
        for special in ('title_perch', 'title_hang', 'focus_read'):
            if special not in actions:
                actions.append(special)

        for name in actions:
            title = ACTIVITIES.get(name, name.replace('_', ' ').title())
            enabled = is_activity_enabled(self.settings, name)
            suffix = "" if enabled else " (roaming disabled)"
            self.animation_combo.addItem(f"▶ {title}{suffix}", name)

        index = self.animation_combo.findData(previous)
        self.animation_combo.setCurrentIndex(max(0, index))
        self.play_button.setEnabled(self.animation_combo.count() > 0)
        self._update_activity_count_label()

    def _on_play_button_clicked(self):
        act_id = self.animation_combo.currentData() or 'idle'
        act_title = ACTIVITIES.get(act_id, act_id.replace('_', ' ').title())
        self.play_button.setText(f"✓ Playing: {act_title}")
        self.play_button.setEnabled(False)
        self.activity_requested.emit(act_id)
        QTimer.singleShot(1400, lambda: (
            self.play_button.setText('▶ Play Activity'),
            self.play_button.setEnabled(self.animation_combo.count() > 0)
        ))

    def _on_test_glitch_clicked(self):
        if hasattr(self, 'btn_test_glitch'):
            self.btn_test_glitch.setText("⚡ Glitching Suit...")
            self.btn_test_glitch.setEnabled(False)
            self.test_glitch_requested.emit()
            QTimer.singleShot(4000, lambda: (
                self.btn_test_glitch.setText("⚡ Preview Glitch Effect"),
                self.btn_test_glitch.setEnabled(True)
            ))

    def update_battery_status(self, percent: int, is_charging: bool, is_low: bool):
        if not hasattr(self, 'battery_status_lbl'):
            return
        if is_low:
            text = f"🪫 Low Battery ({percent}% - Discharging) • Exhaustion & Suit Glitch ACTIVE!"
            color = "#FF3B5C"
        elif is_charging:
            text = f"⚡ Power Connected: {percent}% Charging"
            color = "#4CAF50"
        else:
            text = f"🔋 Battery: {percent}% (Discharging)"
            color = "#97A7BC"
        self.battery_status_lbl.setText(text)
        self.battery_status_lbl.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {color};")

    def update_preview(self, pixmap):
        self._last_preview = pixmap
        if self.isVisible() and self.pages.currentIndex() == 0 and not pixmap.isNull():
            self.preview.setPixmap(pixmap.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_status(self, old, state):
        self._status_text = 'Status: '+state.value.replace('_', ' ').title()
        self.status_label.setText(self._status_text if self._is_running else 'Status: Paused')

    def set_running(self, running):
        self._is_running = running
        self.toggle_btn.setText('Pause' if running else 'Resume')
        self.status_label.setText(self._status_text if running else 'Status: Paused')

    def _toggle_running_state(self):
        if self._is_running:
            self.stop_requested.emit()
        else:
            self.start_requested.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'char_selection_widget'):
            QTimer.singleShot(0, self.char_selection_widget._reflow)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def apply_theme(self):
        light = self.settings.get('general.theme', 'dark') == 'light'
        bg, panel, fg, muted, border, hover = (('#F2F4F8','#FFFFFF','#182233','#616E82','#D8DFEA','#E9EEF6')
            if light else ('#0D1119','#161D29','#EDF2FA','#97A7BC','#2A3547','#222D3E'))
        palette = self.palette()
        for role, color in ((QPalette.Window,bg),(QPalette.Base,panel),(QPalette.AlternateBase,hover),
                            (QPalette.Text,fg),(QPalette.WindowText,fg),(QPalette.ButtonText,fg),
                            (QPalette.Button,panel),(QPalette.Highlight,'#BA2444'),(QPalette.HighlightedText,'#FFFFFF')):
            palette.setColor(role,QColor(color))
        self.setPalette(palette)
        self.setStyleSheet(f"""
            QWidget {{ color: {fg}; font-family: 'Segoe UI'; font-size: 13px; }}
            QMainWindow, QDialog, QScrollArea, QScrollArea > QWidget > QWidget {{ background-color: {bg}; }}
            QWidget#sidebar {{ background-color: {panel}; border: 1px solid {border}; border-radius: 14px; }}
            QLabel {{ background: transparent; border: none; }}
            QLabel#heading {{ font-size: 26px; font-weight: 700; padding-bottom: 4px; }}
            QLabel#subheading {{ font-size: 18px; font-weight: 600; }}
            QLabel#muted {{ color: {muted}; }}
            QAbstractItemView, QComboBox, QSpinBox, QLineEdit {{ background-color: {panel}; color: {fg};
                selection-background-color: #BA2444; selection-color: white;
                border: 1px solid {border}; border-radius: 9px; padding: 8px; }}
            QListWidget::item {{ padding: 12px; border-radius: 6px; }}
            QListWidget::item:hover {{ background: {hover}; }}
            QListWidget::item:selected {{ background: #BA2444; color: white; }}
            QListWidget#navigation {{ background: transparent; border: none; padding: 0; outline: none; }}
            QListWidget#navigation::item {{ padding: 12px 10px; color: {muted}; border-radius: 8px; }}
            QListWidget#navigation::item:hover {{ background: {hover}; color: {fg}; }}
            QListWidget#navigation::item:selected {{ background: #BA2444; color: white; font-weight: 600; }}
            QPushButton {{ background: {panel}; border: 1px solid {border}; border-radius: 8px; padding: 10px 14px; font-weight: 600; }}
            QPushButton:hover {{ background: {hover}; border-color: #CE3556; }}
            QPushButton[primary="true"] {{ background: #BA2444; color: white; border: 1px solid #BA2444; }}
            QPushButton:disabled {{ color: {muted}; background: {bg}; }}
            QPushButton:focus, QComboBox:focus, QLineEdit:focus {{ border: 1px solid #CE3556; }}
            QCheckBox {{ spacing: 10px; padding: 5px; }}
            QSlider::groove:horizontal {{ background: {border}; height: 6px; border-radius: 3px; }}
            QSlider::sub-page:horizontal {{ background: #BA2444; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: #E04365; width: 16px; margin: -5px 0; border-radius: 8px; }}
            QFrame#CharacterCard {{ background: {panel}; border: 1px solid {border}; border-radius: 12px; }}
            QFrame#CharacterCard[selected="true"] {{ border: 2px solid #CE3556; }}
            QFrame#AddCharacterCard {{ background: {panel}; border: 2px dashed {border}; border-radius: 12px; }}
            QFrame#AddCharacterCard:hover {{ border-color: #CE3556; }}
            QFrame#ActivityCategoryCard {{ background: {panel}; border: 1px solid {border}; border-radius: 12px; }}
            QScrollBar:vertical {{ background: {bg}; width: 10px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {border}; min-height: 28px; border-radius: 5px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
