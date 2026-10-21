"""Native settings dashboard with shared, live settings bindings."""
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer, QEvent, QObject
from PySide6.QtGui import QGuiApplication, QIcon, QPixmap, QPalette, QColor
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QListWidget, QStackedWidget, QScrollArea, QComboBox, QCheckBox,
    QSlider, QSpinBox, QFormLayout, QGraphicsOpacityEffect, QFrame, QGridLayout, QSizePolicy, QProgressBar)
from .dashboard_design import DashboardDesign
from .character_selection import CharacterSelectionWidget
from .application_selector import ApplicationSelectorDialog
from services.settings_service import get_settings
from services.hotkey_service import HOTKEY_MAPPINGS
from core.activity_policy import ACTIVITIES, LEGACY_FLAGS, enabled as is_activity_enabled


SPIDEY_QUOTES = [
    "With great power comes great... need to commit to Git.",
    "Spider-Sense detects a bug somewhere in this codebase...",
    "Antigravity looks comfy today.",
    "Queens is quiet... time to write some clean, bug-free code.",
    "Remember to hydrate! Even Spider-Man drinks water.",
    "Tabs or spaces? Don't make me shoot a web at your screen!",
    "Peter Parker: Part-time superhero, full-time bug fixer.",
    "Why do bugs always attack right before deployment?!",
    "Don't worry, I'm watching your terminal for errors.",
    "Spider-Sense tingling! Did someone just push directly to main?!",
    "Stay hydrated and keep that posture straight, web-slinger!",
]


def get_battery_lore(char_id: str, percent: int, is_charging: bool, is_low: bool) -> str:
    if "miles" in str(char_id).lower():
        if is_charging:
            return "⚡ Miles Bio-Electricity: Absorbing Venom Surge" if percent < 100 else "⚡ Miles Bio-Electricity: Fully Charged!"
        elif is_low:
            return "⚠️ Miles Bio-Electricity: Depleted, needs charging!"
        else:
            return f"⚡ Miles Bio-Electricity: Stable ({percent}%)"
    else:
        if is_charging:
            return "⚡ Stark Suit: Arc Reactor Overcharged" if percent < 100 else "⚡ Stark Suit: 100% Fully Powered!"
        elif is_low:
            return "⚠️ Stark Suit: Emergency Low Power Reserve"
        else:
            return f"⚡ Stark Suit: Systems Operational ({percent}%)"


def get_spidey_sense_status(cpu: float, ram: float, is_heavy: bool) -> tuple:
    max_val = max(cpu, ram)
    if is_heavy or max_val >= 80:
        return (
            "⚠️ SPIDEY-SENSE TINGLING! Heavy workload (compiling / AI)",
            "#EF4444",
            "#7F1D1D"
        )
    elif max_val >= 50:
        return (
            "🟡 Spider-Sense: Humming (Active Tasks Running)",
            "#F59E0B",
            "#78350F"
        )
    else:
        return (
            "🟢 Spider-Sense: Quiet (Systems Cool & Relaxed)",
            "#22C55E",
            "#14532D"
        )


class WheelScrollIgnoreFilter(QObject):
    """Prevents accidental value changes from mouse wheel scrolling across all input controls.

    When scrolling over a QSlider, QSpinBox, QDoubleSpinBox, or QComboBox, this filter ignores
    the wheel event on the input widget and forwards it to the parent scroll area so the page scrolls
    smoothly without altering user settings. Sliders and inputs only change via direct clicking or dragging.
    """

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Wheel:
            from PySide6.QtWidgets import QSlider, QAbstractSpinBox, QComboBox, QTabBar, QTabWidget
            if isinstance(watched, (QSlider, QAbstractSpinBox, QComboBox, QTabBar, QTabWidget)):
                event.ignore()
                parent = watched.parent()
                if parent:
                    from PySide6.QtCore import QCoreApplication
                    QCoreApplication.sendEvent(parent, event)
                return True
        return super().eventFilter(watched, event)


class MainWindow(DashboardDesign, QMainWindow):
    start_requested = Signal()
    stop_requested = Signal()
    character_changed = Signal(str)
    display_mode_changed = Signal(str)
    size_changed = Signal(int)
    activity_requested = Signal(str)
    save_position_requested = Signal()
    test_glitch_requested = Signal()
    simulate_low_battery_toggled = Signal(bool)
    test_eye_break_requested = Signal()
    focus_timer_started = Signal(float)
    focus_timer_stopped = Signal()
    spawn_trampoline_requested = Signal()
    simulate_heavy_load_toggled = Signal(bool)
    simulate_music_toggled = Signal(bool)
    simulate_charging_toggled = Signal(bool)
    speech_bubble_requested = Signal(str, int, str)
    mood_preset_changed = Signal(str)

    def __init__(self, character_mgr, parent=None):
        super().__init__(parent)
        self.character_mgr = character_mgr
        self.settings = get_settings()
        self._wheel_filter = WheelScrollIgnoreFilter(self)
        from PySide6.QtWidgets import QApplication
        qapp = QApplication.instance()
        if qapp:
            qapp.installEventFilter(self._wheel_filter)
        self._bindings = {}
        self._is_running = True
        self._status_text = "Status: Idle"
        self._page_scroll_areas = []
        self._current_size_tier = None
        self.setWindowTitle('Spider-Buddy — Desktop Companion')
        self.setMinimumSize(640, 460)
        self.resize(1100, 780)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        self.main_root_layout = layout

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
        sidebar.setFixedWidth(240)
        sidebar.setObjectName("sidebar")
        self.sidebar = sidebar

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

        # Sidebar Battery Status Rectangle
        self.sidebar_battery_card = QFrame()
        self.sidebar_battery_card.setObjectName('SidebarBatteryCard')
        self.sidebar_battery_card.setStyleSheet("""
            QFrame#SidebarBatteryCard {
                background: #161820;
                border: 1px solid #2B2E38;
                border-radius: 8px;
            }
        """)
        sbat_layout = QHBoxLayout(self.sidebar_battery_card)
        sbat_layout.setContentsMargins(10, 7, 10, 7)
        sbat_layout.setSpacing(8)
        self.sidebar_bat_icon = QLabel("🔋")
        self.sidebar_bat_icon.setStyleSheet("font-size: 14px;")
        sbat_layout.addWidget(self.sidebar_bat_icon)
        self.sidebar_bat_text = QLabel("100% • On Battery")
        self.sidebar_bat_text.setStyleSheet("font-size: 11px; font-weight: 600; color: #E2E8F0;")
        sbat_layout.addWidget(self.sidebar_bat_text, 1)
        sidebar_layout.addWidget(self.sidebar_battery_card)

        footer = QLabel('YOUR DESKTOP, WITH COMPANY')
        footer.setWordWrap(True)
        footer.setObjectName('muted')
        footer.setStyleSheet('font-size: 9px; padding: 8px;')
        sidebar_layout.addWidget(footer)

        self.pages = QStackedWidget()
        layout.addWidget(sidebar)
        content = QVBoxLayout()
        content.setSpacing(18)
        self._install_search(content)
        content.addWidget(self.pages, 1)
        layout.addLayout(content, 1)
        self._initialize_destinations()
        self._build_dashboard()
        page = self._page('Characters', 'Choose your companion', 'Switch instantly. One character stays active at a time.')
        self.char_selection_widget = CharacterSelectionWidget(character_mgr)
        self.char_selection_widget.character_selected.connect(self.character_changed.emit)
        page.addWidget(self.char_selection_widget)
        self._build_animations()
        self._build_display()
        self._build_behavior()
        self._build_appearance()
        self._build_settings()
        self._finish_design()
        self.navigation.currentRowChanged.connect(self._navigate)
        self.navigation.currentRowChanged.connect(lambda _: self._enable_text_selection())
        self.navigation.setCurrentRow(0)
        self.settings.setting_changed.connect(self._sync)
        self.character_mgr.character_changed.connect(self._character_updated)
        QGuiApplication.instance().screenAdded.connect(self._refresh_monitors)
        QGuiApplication.instance().screenRemoved.connect(self._refresh_monitors)
        self._refresh_monitors()
        self._update_applications()
        self._character_updated(character_mgr.active_character)
        from .qml_shell import install_qml_shell
        install_qml_shell(self)
        from .qml_pages import install_qml_pages
        install_qml_pages(self)
        self.apply_theme()
        self._enable_text_selection()

    def _page(self, name, title, description):
        name = {'Dashboard':'Home', 'Animations':'Activities', 'Display Mode':'Desktop & Apps',
                'Behavior':'Controls', 'Appearance':'Characters'}.get(name, name)
        if name in getattr(self, '_routes', {}):
            return self._routes[name]
        self.navigation.addItem(name)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        page = QVBoxLayout(body)
        page.setContentsMargins(16, 12, 16, 16)
        page.setSpacing(14)
        if title:
            heading = QLabel(title)
            heading.setObjectName('heading')
            heading.setWordWrap(True)
            heading.setMinimumWidth(0)
            heading.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            heading.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
            page.addWidget(heading)
        if description:
            note = QLabel(description)
            note.setWordWrap(True)
            note.setMinimumWidth(0)
            note.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            note.setObjectName('muted')
            note.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
            page.addWidget(note)
        scroll.setWidget(body)
        self.pages.addWidget(scroll)
        self._page_scroll_areas.append((scroll, body, page))
        if hasattr(self, "_routes"):
            self._routes[name] = page
        return page

    def _button(self, layout, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def _combo(self, layout, label, key, choices):
        layout.addWidget(QLabel(label))
        combo = QComboBox()
        combo.setProperty('searchLabel', label)
        combo.setProperty('settingKey', key)
        for text, value in choices:
            combo.addItem(text, value)
        combo.setCurrentIndex(max(0, combo.findData(self.settings.get(key))))
        combo.currentIndexChanged.connect(lambda index: self.settings.set(key, combo.itemData(index)) if index >= 0 else None)
        self._bindings[key] = (combo, 'combo', 1, None)
        layout.addWidget(combo)
        return combo

    def _check(self, layout, label, key, default=True):
        check = QCheckBox(label)
        check.setProperty("settingKey", key)
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
        slider.setProperty("searchLabel", label)
        slider.setProperty("settingKey", key)
        slider.setRange(low, high)
        slider.setValue(round(float(self.settings.get(key, low/factor))*factor))
        value_label.setText(f'{slider.value()}{suffix}')
        slider.valueChanged.connect(lambda value: value_label.setText(f'{value}{suffix}'))
        slider.valueChanged.connect(lambda value: self.settings.set(key, value/factor))
        self._bindings[key] = (slider, 'slider', factor, (value_label, suffix))
        layout.addWidget(slider)
        return slider

    def _build_dashboard(self):
        home = self._page('Dashboard', 'Spider-Buddy', 'A small companion for your desktop and favorite apps.')

        # 1. Hero Stage (Companion Stage)
        hero = QFrame()
        hero.setObjectName('companionStage')
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(10)
        home.addWidget(hero)

        eyebrow = QLabel('YOUR COMPANION')
        eyebrow.setObjectName('muted')
        eyebrow.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(eyebrow)

        # 💬 Comic Speech Bubble / Daily Quotes (Requirement 4)
        self.quote_bubble = QFrame()
        self.quote_bubble.setObjectName('QuoteBubbleCard')
        self.quote_bubble.setCursor(Qt.PointingHandCursor)
        self.quote_bubble.setStyleSheet("""
            QFrame#QuoteBubbleCard {
                background: #181C28;
                border: 1.5px solid #E04A64;
                border-radius: 12px;
            }
            QFrame#QuoteBubbleCard:hover {
                background: #232838;
                border-color: #FF5C7A;
            }
        """)
        qb_layout = QVBoxLayout(self.quote_bubble)
        qb_layout.setContentsMargins(12, 8, 12, 8)
        qb_layout.setSpacing(2)

        self.quote_text = QLabel(f'💬 "{SPIDEY_QUOTES[0]}"')
        self.quote_text.setWordWrap(True)
        self.quote_text.setAlignment(Qt.AlignCenter)
        self.quote_text.setStyleSheet("font-size: 13px; font-weight: 600; color: #F1F5F9; font-style: italic;")
        qb_layout.addWidget(self.quote_text)

        self.quote_hint = QLabel("Tap bubble to hear more from Spidey")
        self.quote_hint.setAlignment(Qt.AlignCenter)
        self.quote_hint.setStyleSheet("font-size: 10px; color: #94A3B8;")
        qb_layout.addWidget(self.quote_hint)

        self.quote_bubble.mousePressEvent = lambda e: self._cycle_spidey_quote()
        hero_layout.addWidget(self.quote_bubble)

        # Character Preview
        self.preview = QLabel()
        self.preview.setMinimumHeight(190)
        self.preview.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.preview)

        self.active_label = QLabel('Loading character…')
        self.active_label.setObjectName('subheading')
        self.active_label.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.active_label)

        self.status_label = QLabel('Status: Idle')
        self.status_label.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.status_label)

        self.overlay_owner_label = QLabel('Companion starting…')
        self.overlay_owner_label.setWordWrap(True)
        self.overlay_owner_label.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.overlay_owner_label)

        # Controls & Quick Mood Presets Row (Requirement 6)
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(8)
        self.toggle_btn = self._button(ctrl_bar, 'Pause', self._toggle_running_state)
        self.hide_btn = self._button(ctrl_bar, 'Show character' if self.settings.get('general.hidden', False) else 'Hide character',
            lambda: self.settings.set('general.hidden', not self.settings.get('general.hidden', False)))

        mood_label = QLabel("Mood:")
        mood_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8; margin-left: 10px;")
        ctrl_bar.addWidget(mood_label)

        self.btn_mood_chill = QPushButton("🧘 Chill")
        self.btn_mood_hyper = QPushButton("⚡ Hyper")
        self.btn_mood_camo = QPushButton("👻 Camo")
        for btn, mode in [(self.btn_mood_chill, "chill"), (self.btn_mood_hyper, "hyper"), (self.btn_mood_camo, "camo")]:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #1E2330;
                    border: 1px solid #334155;
                    border-radius: 12px;
                    color: #E2E8F0;
                    padding: 5px 11px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #2D3748;
                    border-color: #E04A64;
                }
            """)
            btn.clicked.connect(lambda checked=False, m=mode: self._set_mood_preset(m))
            ctrl_bar.addWidget(btn)

        hero_layout.addLayout(ctrl_bar)
        self.dashboard_apps = QLabel()
        hero_layout.addWidget(self.dashboard_apps)

        # -------------------------------------------------------------------------
        # 2. GRID ROW 1: (Left: System HUD & Spidey-Sense | Right: Action Deck)
        # -------------------------------------------------------------------------
        grid_row1 = QHBoxLayout()
        grid_row1.setSpacing(14)

        # LEFT CARD: ⚡ Live System HUD & "Spidey-Sense" Monitor (Requirement 1)
        hud_card = QFrame()
        hud_card.setObjectName('ActivityCategoryCard')
        hud_layout = QVBoxLayout(hud_card)
        hud_layout.setContentsMargins(16, 14, 16, 14)
        hud_layout.setSpacing(10)

        hud_title = QLabel('⚡ Live System HUD & Spidey-Sense')
        hud_title.setObjectName('subheading')
        hud_layout.addWidget(hud_title)

        hud_sub = QLabel('Real-time battery & hardware lore monitor')
        hud_sub.setObjectName('muted')
        hud_sub.setStyleSheet('font-size: 11px;')
        hud_layout.addWidget(hud_sub)

        # Battery HUD Section
        bat_box = QFrame()
        bat_box.setStyleSheet('background: #141822; border: 1px solid #232B3E; border-radius: 8px;')
        bb_layout = QVBoxLayout(bat_box)
        bb_layout.setContentsMargins(10, 8, 10, 8)
        bb_layout.setSpacing(4)

        self.hud_battery_pct = QLabel("⚡ 100% • On Battery")
        self.hud_battery_pct.setStyleSheet("font-size: 14px; font-weight: 700; color: #22C55E;")
        bb_layout.addWidget(self.hud_battery_pct)

        self.hud_battery_lore = QLabel("Stark Suit: Systems Operational")
        self.hud_battery_lore.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8;")
        bb_layout.addWidget(self.hud_battery_lore)

        self.hud_battery_bar = QProgressBar()
        self.hud_battery_bar.setRange(0, 100)
        self.hud_battery_bar.setValue(100)
        self.hud_battery_bar.setTextVisible(False)
        self.hud_battery_bar.setFixedHeight(6)
        self.hud_battery_bar.setStyleSheet("""
            QProgressBar {
                background: #1E293B;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background: #22C55E;
                border-radius: 3px;
            }
        """)
        bb_layout.addWidget(self.hud_battery_bar)
        hud_layout.addWidget(bat_box)

        # CPU / RAM & Spidey-Sense Alert Section
        load_box = QFrame()
        load_box.setStyleSheet('background: #141822; border: 1px solid #232B3E; border-radius: 8px;')
        lb_layout = QVBoxLayout(load_box)
        lb_layout.setContentsMargins(10, 8, 10, 8)
        lb_layout.setSpacing(6)

        self.hud_load_metrics = QLabel("CPU: 0% • RAM: 0%")
        self.hud_load_metrics.setStyleSheet("font-size: 12px; font-weight: 600; color: #94A3B8;")
        lb_layout.addWidget(self.hud_load_metrics)

        self.hud_spidey_sense = QLabel("🟢 Spider-Sense: Quiet (Systems Cool)")
        self.hud_spidey_sense.setStyleSheet(
            "padding: 6px 10px; border-radius: 6px; font-weight: 600; font-size: 11px; "
            "background: #0D2618; border: 1px solid #166534; color: #4ADE80;"
        )
        lb_layout.addWidget(self.hud_spidey_sense)
        hud_layout.addWidget(load_box)

        grid_row1.addWidget(hud_card, 1)

        # RIGHT CARD: 🎮 "Action Deck" (Instant Emotes & Tricks) (Requirement 2)
        action_card = QFrame()
        action_card.setObjectName('ActivityCategoryCard')
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(16, 14, 16, 14)
        action_layout.setSpacing(10)

        act_title = QLabel('🎮 Action Deck')
        act_title.setObjectName('subheading')
        action_layout.addWidget(act_title)

        act_sub = QLabel('1-Click instant Spider-Man tricks on screen')
        act_sub.setObjectName('muted')
        act_sub.setStyleSheet('font-size: 11px;')
        action_layout.addWidget(act_sub)

        # 2x2 Action Buttons Grid
        deck_grid = QGridLayout()
        deck_grid.setSpacing(8)

        actions_def = [
            ("🕸️ Web Swing", "Swing across screen", "swing", 0, 0),
            ("🤸 Do a Flip", "Acrobatic backflip", "celebrate", 0, 1),
            ("🧗 Peek Window", "Cling to active window", "title_perch", 1, 0),
            ("💤 Power Nap", "Web hammock rest", "sleep", 1, 1),
        ]
        for name, hint, act_code, r, c in actions_def:
            btn = QPushButton(f"{name}\n{hint}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #171B26;
                    border: 1px solid #2B3346;
                    border-radius: 9px;
                    color: #F8FAFC;
                    padding: 8px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    text-align: center;
                }
                QPushButton:hover {
                    background: #232A3B;
                    border-color: #E04A64;
                    color: #FFFFFF;
                }
                QPushButton:pressed {
                    background: #11141D;
                }
            """)
            btn.clicked.connect(lambda checked=False, a=act_code: self._trigger_quick_action(a))
            deck_grid.addWidget(btn, r, c)

        action_layout.addLayout(deck_grid)
        action_layout.addStretch()
        grid_row1.addWidget(action_card, 1)

        home.addLayout(grid_row1)

        # -------------------------------------------------------------------------
        # 3. GRID ROW 2: (Left: Spider-Focus Pomodoro | Right: Today's Stats)
        # -------------------------------------------------------------------------
        grid_row2 = QHBoxLayout()
        grid_row2.setSpacing(14)

        # LEFT CARD: ⏱️ Spider-Focus / Pomodoro Companion (Requirement 3)
        pom_card = QFrame()
        pom_card.setObjectName('ActivityCategoryCard')
        pom_layout = QVBoxLayout(pom_card)
        pom_layout.setContentsMargins(16, 14, 16, 14)
        pom_layout.setSpacing(10)

        pom_title = QLabel('⏱️ Work with Spidey (Pomodoro)')
        pom_title.setObjectName('subheading')
        pom_layout.addWidget(pom_title)

        pom_sub = QLabel('25-min quiet guardian focus + 5-min stretch reminder')
        pom_sub.setObjectName('muted')
        pom_sub.setStyleSheet('font-size: 11px;')
        pom_layout.addWidget(pom_sub)

        pom_timer_box = QFrame()
        pom_timer_box.setStyleSheet('background: #141822; border: 1px solid #232B3E; border-radius: 8px;')
        ptb_layout = QVBoxLayout(pom_timer_box)
        ptb_layout.setContentsMargins(10, 6, 10, 6)
        ptb_layout.setSpacing(4)
        ptb_layout.setAlignment(Qt.AlignCenter)

        self.focus_countdown_label = QLabel('25:00')
        self.focus_countdown_label.setAlignment(Qt.AlignCenter)
        self.focus_countdown_label.setStyleSheet('font-size: 26px; font-weight: 700; color: #38BDF8;')
        ptb_layout.addWidget(self.focus_countdown_label)

        self.focus_mode_badge = QLabel('🛡️ Guardian Mode: Ready')
        self.focus_mode_badge.setAlignment(Qt.AlignCenter)
        self.focus_mode_badge.setStyleSheet('font-size: 11px; font-weight: 600; color: #94A3B8;')
        ptb_layout.addWidget(self.focus_mode_badge)
        pom_layout.addWidget(pom_timer_box)

        # Pomodoro Buttons
        pom_btn_row = QHBoxLayout()
        pom_btn_row.setSpacing(6)

        btn_focus25 = QPushButton('🎯 25m Focus')
        btn_focus25.setCursor(Qt.PointingHandCursor)
        btn_focus25.setStyleSheet('background: #1D3557; border: 1px solid #457B9D; border-radius: 8px; padding: 6px 10px; color: #F1FAEE; font-weight: 600; font-size: 11px;')
        btn_focus25.clicked.connect(lambda: self._start_pomodoro_focus(25))
        pom_btn_row.addWidget(btn_focus25)

        btn_break5 = QPushButton('☕ 5m Break')
        btn_break5.setCursor(Qt.PointingHandCursor)
        btn_break5.setStyleSheet('background: #16382B; border: 1px solid #2D6A4F; border-radius: 8px; padding: 6px 10px; color: #D8F3DC; font-weight: 600; font-size: 11px;')
        btn_break5.clicked.connect(lambda: self._start_pomodoro_break(5))
        pom_btn_row.addWidget(btn_break5)

        btn_reset_pom = QPushButton('⏹️ Reset')
        btn_reset_pom.setCursor(Qt.PointingHandCursor)
        btn_reset_pom.setStyleSheet('background: #252836; border: 1px solid #3F445B; border-radius: 8px; padding: 6px 10px; color: #CBD5E1; font-weight: 600; font-size: 11px;')
        btn_reset_pom.clicked.connect(self._reset_pomodoro)
        pom_btn_row.addWidget(btn_reset_pom)

        pom_layout.addLayout(pom_btn_row)
        grid_row2.addWidget(pom_card, 1)

        # RIGHT CARD: 📊 "Today with Spider-Man" Companion Stats (Requirement 5)
        stats_card = QFrame()
        stats_card.setObjectName('ActivityCategoryCard')
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.setContentsMargins(16, 14, 16, 14)
        stats_layout.setSpacing(10)

        stats_title = QLabel('📊 Today with Spider-Man')
        stats_title.setObjectName('subheading')
        stats_layout.addWidget(stats_title)

        stats_sub = QLabel('Daily desktop companionship metrics')
        stats_sub.setObjectName('muted')
        stats_sub.setStyleSheet('font-size: 11px;')
        stats_layout.addWidget(stats_sub)

        # Stat Tiles Box
        st_box = QFrame()
        st_box.setStyleSheet('background: #141822; border: 1px solid #232B3E; border-radius: 8px;')
        st_layout = QVBoxLayout(st_box)
        st_layout.setContentsMargins(12, 8, 12, 8)
        st_layout.setSpacing(8)

        # 1. Distance
        row_dist = QHBoxLayout()
        dist_icon = QLabel("🐾")
        dist_icon.setStyleSheet("font-size: 14px;")
        row_dist.addWidget(dist_icon)
        dist_info = QVBoxLayout()
        dist_info.setSpacing(1)
        self.stat_distance_val = QLabel("0 px")
        self.stat_distance_val.setStyleSheet("font-size: 13px; font-weight: 700; color: #38BDF8;")
        dist_info.addWidget(self.stat_distance_val)
        dist_desc = QLabel("Crawled across your open windows")
        dist_desc.setStyleSheet("font-size: 10px; color: #64748B;")
        dist_info.addWidget(dist_desc)
        row_dist.addLayout(dist_info)
        row_dist.addStretch()
        st_layout.addLayout(row_dist)

        # 2. Webs Shot
        row_webs = QHBoxLayout()
        web_icon = QLabel("🕸️")
        web_icon.setStyleSheet("font-size: 14px;")
        row_webs.addWidget(web_icon)
        web_info = QVBoxLayout()
        web_info.setSpacing(1)
        self.stat_webs_val = QLabel("0 swings")
        self.stat_webs_val.setStyleSheet("font-size: 13px; font-weight: 700; color: #E04A64;")
        web_info.addWidget(self.stat_webs_val)
        web_desc = QLabel("Web lines shot across desktop")
        web_desc.setStyleSheet("font-size: 10px; color: #64748B;")
        web_info.addWidget(web_desc)
        row_webs.addLayout(web_info)
        row_webs.addStretch()
        st_layout.addLayout(row_webs)

        # 3. Active Time
        row_time = QHBoxLayout()
        time_icon = QLabel("⏱️")
        time_icon.setStyleSheet("font-size: 14px;")
        row_time.addWidget(time_icon)
        time_info = QVBoxLayout()
        time_info.setSpacing(1)
        self.stat_active_val = QLabel("0s")
        self.stat_active_val.setStyleSheet("font-size: 13px; font-weight: 700; color: #22C55E;")
        time_info.addWidget(self.stat_active_val)
        time_desc = QLabel("Active companionship today")
        time_desc.setStyleSheet("font-size: 10px; color: #64748B;")
        time_info.addWidget(time_desc)
        row_time.addLayout(time_info)
        row_time.addStretch()
        st_layout.addLayout(row_time)

        stats_layout.addWidget(st_box)
        grid_row2.addWidget(stats_card, 1)

        home.addLayout(grid_row2)

        # Quick Navigation Links
        quick = QHBoxLayout()
        for title, route in [('Change character', 1), ('Choose activities', 2), ('Focus settings', 4)]:
            self._button(quick, title, lambda checked=False, index=route: self.navigation.setCurrentRow(index))
        home.addLayout(quick)

        # Focus Mode Quick Toggle Card on Focus & Breaks page (page index 4)
        page = self._routes['Focus & Breaks']
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

        self.focus_mode_chk = QCheckBox('Enable focus mode')
        self.focus_mode_chk.setChecked(bool(self.settings.get('behavior.focus_mode', False)))
        self.focus_mode_chk.toggled.connect(lambda val: self.settings.set('behavior.focus_mode', val))
        fc_layout.addWidget(self.focus_mode_chk)
        page.addWidget(focus_card)

    def _cycle_spidey_quote(self):
        """Cycle through witty Spider-Man quotes and emit speech bubble on overlay."""
        self._quote_index = (getattr(self, "_quote_index", 0) + 1) % len(SPIDEY_QUOTES)
        quote = SPIDEY_QUOTES[self._quote_index]
        if hasattr(self, "quote_text"):
            self.quote_text.setText(f'💬 "{quote}"')
        self.speech_bubble_requested.emit(quote, 2800, "comic")
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.refresh_home()

    def _trigger_quick_action(self, action: str):
        """Trigger an instant Spider-Man emote on user desktop."""
        if not self._is_running:
            self.set_running(True)
        self.activity_requested.emit(action)
        quotes = {
            "swing": "Thwip! Web swing engaged!",
            "celebrate": "Woohoo! Acrobatic flip landed!",
            "title_perch": "Perching right above your window!",
            "sleep": "Power nap in the web hammock... Zzz",
        }
        quote = quotes.get(action, "Spidey in action!")
        self.speech_bubble_requested.emit(quote, 2200, "action")

    def _set_mood_preset(self, mode: str):
        """Activate quick mood preset (chill, hyper, camo)."""
        self._active_mood = mode
        for btn, m in [(self.btn_mood_chill, "chill"), (self.btn_mood_hyper, "hyper"), (self.btn_mood_camo, "camo")]:
            if m == mode:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #E04A64;
                        border: 1px solid #FF5C7A;
                        border-radius: 12px;
                        color: #FFFFFF;
                        padding: 5px 11px;
                        font-size: 11px;
                        font-weight: 700;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #1E2330;
                        border: 1px solid #334155;
                        border-radius: 12px;
                        color: #E2E8F0;
                        padding: 5px 11px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background: #2D3748;
                        border-color: #E04A64;
                    }
                """)
        self.mood_preset_changed.emit(mode)
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.refresh_home()

    def _start_pomodoro_focus(self, minutes: float = 25):
        """Start 25-minute quiet guardian focus timer."""
        self.focus_timer_started.emit(minutes)
        self.settings.set("behavior.focus_mode", True)
        self.activity_requested.emit("focus_read")
        if hasattr(self, "focus_mode_badge"):
            self.focus_mode_badge.setText("🛡️ Guardian Focus: Active")
            self.focus_mode_badge.setStyleSheet("font-size: 11px; font-weight: 700; color: #38BDF8;")
        self.speech_bubble_requested.emit("🎯 25-Min Focus Started! I'll watch the perimeter while you code.", 3000, "comic")
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.refresh_home()

    def _start_pomodoro_break(self, minutes: float = 5):
        """Start 5-minute eye-break hydration reminder."""
        self.focus_timer_started.emit(minutes)
        self.settings.set("behavior.focus_mode", False)
        self.activity_requested.emit("wave")
        if hasattr(self, "focus_mode_badge"):
            self.focus_mode_badge.setText("☕ Break Time (5 Min)")
            self.focus_mode_badge.setStyleSheet("font-size: 11px; font-weight: 700; color: #22C55E;")
        self.speech_bubble_requested.emit("Time to stretch, hydrate, and rest your eyes! 🥤", 3000, "comic")
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.refresh_home()

    def _reset_pomodoro(self):
        """Reset focus countdown timer."""
        self.focus_timer_stopped.emit()
        self.settings.set("behavior.focus_mode", False)
        if hasattr(self, "focus_countdown_label"):
            self.focus_countdown_label.setText("25:00")
            self.focus_countdown_label.setStyleSheet("font-size: 26px; font-weight: 700; color: #64748B;")
        if hasattr(self, "focus_mode_badge"):
            self.focus_mode_badge.setText("🛡️ Guardian Mode: Ready")
            self.focus_mode_badge.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8;")
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.refresh_home()

    def update_companion_stats(self, stats: dict):
        """Update live companionship milestones on dashboard."""
        if hasattr(self, "stat_distance_val"):
            self.stat_distance_val.setText(stats.get("distance_text", "0 px"))
        if hasattr(self, "stat_webs_val"):
            self.stat_webs_val.setText(stats.get("webs_text", "0 swings"))
        if hasattr(self, "stat_active_val"):
            self.stat_active_val.setText(stats.get("active_text", "0s"))
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.refresh_home()


        # Page alignment is finalized after all feature groups are built.

    def _build_display(self):
        page = self._page('Display Mode', 'Where your companion lives', 'Application mode keeps the entire character inside the selected foreground window.')
        self._combo(page, 'Display mode', 'general.display_mode', [('Entire desktop', 'desktop'), ('Selected applications', 'application')])
        self.monitor_combo = self._combo(page, 'Desktop monitor', 'general.monitor', [('Primary monitor', 'primary'), ('All monitors', 'all')])
        self.monitor_combo.setEnabled(self.settings.get('general.display_mode') == 'desktop')
        policy = QLabel('In application mode, the character hides when its app is minimized, closed, too small, or no longer in front.')
        policy.setWordWrap(True)
        policy.setObjectName('muted')
        page.addWidget(policy)

        # Integrated Target Applications Card
        app_card = QFrame()
        app_card.setObjectName('ActivityCategoryCard')
        app_layout = QVBoxLayout(app_card)
        app_layout.setContentsMargins(14, 12, 14, 12)
        app_layout.setSpacing(10)

        app_header = QLabel('🎯 Target Applications (Selected Apps Mode)')
        app_header.setObjectName('subheading')
        app_layout.addWidget(app_header)

        app_desc = QLabel('Select running apps, registered apps, or browse to an executable to confine Spider-Man to those specific application windows.')
        app_desc.setWordWrap(True)
        app_desc.setObjectName('muted')
        app_layout.addWidget(app_desc)

        self.app_count_label = QLabel()
        self.app_count_label.setStyleSheet('font-weight: 600; font-size: 13px; color: #38BDF8;')
        app_layout.addWidget(self.app_count_label)

        self.app_list = QListWidget()
        self.app_list.setObjectName("app_list")
        self.app_list.setSpacing(4)
        self.app_list.setMinimumHeight(150)
        app_layout.addWidget(self.app_list)

        self._button(app_layout, '➕ Add or remove applications', self._open_application_selector)
        page.addWidget(app_card)
        # Page alignment is finalized after all feature groups are built.

    def _build_animations(self):
        page = self._page(
            'Animations',
            None,
            None,
        )

        # Header Row: Title & Subtitle on Left, Automatic Mode Switch on Top Right
        header_row = QVBoxLayout()
        header_row.setSpacing(12)
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(4)
        heading = QLabel('Playback')
        heading.setObjectName('subheading')
        heading.setWordWrap(True)
        heading.setMinimumWidth(0)
        heading.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        heading.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        header_text_layout.addWidget(heading)

        note = QLabel('Choose which activities Spider-Man can perform. Toggle Automatic mode to cycle animations or lock into a single activity.')
        note.setWordWrap(True)
        note.setMinimumWidth(0)
        note.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        note.setObjectName('muted')
        note.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        header_text_layout.addWidget(note)
        header_row.addLayout(header_text_layout, 1)

        # Top-Right Segmented Mode Control (Auto Roaming vs Single Activity)
        mode_box = QWidget()
        mode_box_layout = QVBoxLayout(mode_box)
        mode_box_layout.setContentsMargins(0, 4, 0, 10)
        mode_box_layout.setSpacing(6)
        mode_box_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        seg_frame = QFrame()
        seg_frame.setObjectName('ModeSegmentedControl')
        seg_frame.setFixedHeight(36)
        seg_frame_layout = QHBoxLayout(seg_frame)
        seg_frame_layout.setContentsMargins(3, 3, 3, 3)
        seg_frame_layout.setSpacing(4)

        self.btn_mode_auto = QPushButton('Automatic')
        self.btn_mode_auto.setCursor(Qt.PointingHandCursor)
        self.btn_mode_auto.setMinimumWidth(105)
        self.btn_mode_auto.setFixedHeight(28)
        self.btn_mode_auto.clicked.connect(lambda: self.chk_automatic_animations.setChecked(True))
        seg_frame_layout.addWidget(self.btn_mode_auto)

        self.btn_mode_single = QPushButton('Repeat one')
        self.btn_mode_single.setCursor(Qt.PointingHandCursor)
        self.btn_mode_single.setMinimumWidth(110)
        self.btn_mode_single.setFixedHeight(28)
        self.btn_mode_single.clicked.connect(lambda: self.chk_automatic_animations.setChecked(False))
        seg_frame_layout.addWidget(self.btn_mode_single)
        self.btn_auto_toggle = self.btn_mode_auto  # alias for backward compatibility

        mode_box_layout.addWidget(seg_frame)

        is_auto = self.settings.get('behavior.automatic_animations', True)
        self.lbl_mode_caption = QLabel('Cycles randomly through enabled activities' if is_auto else 'Locked to repeat single activity')
        self.lbl_mode_caption.setAlignment(Qt.AlignLeft)
        self.lbl_mode_caption.setWordWrap(True)
        self.lbl_mode_caption.setMinimumHeight(32)
        self.lbl_mode_caption.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        mode_box_layout.addWidget(self.lbl_mode_caption)

        # Hidden checkbox kept for backwards compatibility with tests / bindings
        self.chk_automatic_animations = QCheckBox()
        self.chk_automatic_animations.setVisible(False)
        self.chk_automatic_animations.setChecked(is_auto)
        self.chk_automatic_animations.toggled.connect(self._on_automatic_mode_toggled)
        mode_box_layout.addWidget(self.chk_automatic_animations)

        self._update_auto_toggle_ui(is_auto)

        header_row.addWidget(mode_box)
        page.addLayout(header_row)

        # 1. Preview & Play Section
        play_card = QFrame()
        play_card.setObjectName('ActivityCategoryCard')
        play_layout = QVBoxLayout(play_card)
        play_layout.setContentsMargins(14, 12, 14, 12)
        play_layout.setSpacing(8)

        play_title = QLabel('Choose an activity')
        play_title.setObjectName('subheading')
        play_layout.addWidget(play_title)

        self.play_hint = QLabel('When Automatic is ON, click Play to test an activity. When Automatic is OFF, Spider-Man continuously performs only this one selected activity!')
        self.play_hint.setObjectName('muted')
        self.play_hint.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        play_layout.addWidget(self.play_hint)

        play_row = QHBoxLayout()
        self.animation_combo = QComboBox()
        self.animation_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.animation_combo.setMinimumWidth(0)
        self.animation_combo.currentIndexChanged.connect(self._on_animation_combo_changed)
        play_row.addWidget(self.animation_combo, 1)
        self.play_button = QPushButton('▶ Play Activity')
        self.play_button.setProperty('primary', 'true')
        self.play_button.clicked.connect(self._on_play_button_clicked)
        play_row.addWidget(self.play_button)
        play_layout.addLayout(play_row)
        page.addWidget(play_card)

        # 2. Quick Actions Toolbar & Counter
        toolbar_row = QVBoxLayout()
        toolbar_row.setSpacing(6)
        self.activity_count_label = QLabel('Configuring activities…')
        self.activity_count_label.setStyleSheet('font-weight: 600; font-size: 12px;')
        self.activity_count_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.activity_count_label.setMinimumWidth(0)
        toolbar_row.addWidget(self.activity_count_label, 1)

        btn_group_layout = QHBoxLayout()
        btn_group_layout.setSpacing(4)
        self.btn_select_all = QPushButton('Select All')
        self.btn_select_all.clicked.connect(self._select_all_activities)
        btn_group_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton('Deselect All')
        self.btn_deselect_all.clicked.connect(self._deselect_all_activities)
        btn_group_layout.addWidget(self.btn_deselect_all)

        self.btn_reset_defaults = QPushButton('Reset Defaults')
        self.btn_reset_defaults.clicked.connect(self._reset_activity_defaults)
        btn_group_layout.addWidget(self.btn_reset_defaults)
        toolbar_row.addLayout(btn_group_layout)
        page.addLayout(toolbar_row)

        self._activity_checkboxes = {}

        # 3. Featured Card: Perching on Window Title Bars & Tab Strips
        window_perch_card = QFrame()
        window_perch_card.setObjectName('ActivityCategoryCard')
        wp_layout = QVBoxLayout(window_perch_card)
        wp_layout.setContentsMargins(14, 12, 14, 12)
        wp_layout.setSpacing(10)

        wp_header = QLabel('Window activities')
        wp_header.setObjectName('subheading')
        wp_layout.addWidget(wp_header)

        wp_desc = QLabel(
            'Let your companion rest on the edge of a window or hang from its title bar. '
            'Adjust the alignment in Desktop & Apps.'
        )
        wp_desc.setWordWrap(True)
        wp_desc.setObjectName('muted')
        wp_layout.addWidget(wp_desc)

        # Master Toggle for Window Perching
        is_perching_enabled = bool(self.settings.get('animations.enable_window_perching', True))
        self.window_perch_master_check = QCheckBox('Enable window activities')
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
        self.title_perch_chk = QCheckBox('Perch on the window edge')
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
        self.title_hang_chk = QCheckBox('Hang from the title bar')
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
        alignment = self._section('Desktop & Apps', 'Window alignment')
        alignment.addLayout(offset_header)

        self.title_offset_slider = QSlider(Qt.Horizontal)
        self.title_offset_slider.setProperty('searchLabel', 'Title bar / tab alignment')
        self.title_offset_slider.setRange(0, 80)
        self.title_offset_slider.setValue(int(self.settings.get('animations.title_bar_offset', 28)))
        self.title_offset_slider.valueChanged.connect(lambda val: (
            self.title_offset_val_lbl.setText(f"{val} px"),
            self.settings.set('animations.title_bar_offset', val)
        ))
        alignment.addWidget(self.title_offset_slider)

        self.window_perch_sub_panel.setEnabled(is_perching_enabled)
        wp_layout.addWidget(self.window_perch_sub_panel)
        self._activity_group('Windows').addWidget(window_perch_card)

        # 4. Featured Card: Laptop Battery Saver & Spider-Verse Glitch
        battery_card = QFrame()
        battery_card.setObjectName('ActivityCategoryCard')
        bat_layout = QVBoxLayout(battery_card)
        bat_layout.setContentsMargins(14, 12, 14, 12)
        bat_layout.setSpacing(10)

        bat_header = QLabel('Low-battery reaction')
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

        self.chk_enable_charging = QCheckBox('Enable yellow battery charging reaction above head')
        self.chk_enable_charging.setStyleSheet('font-weight: 600; font-size: 13px;')
        self.chk_enable_charging.setChecked(bool(self.settings.get('behavior.enable_battery_charging_reaction', True)))
        self.chk_enable_charging.toggled.connect(lambda val: self.settings.set('behavior.enable_battery_charging_reaction', val))
        self._bindings['behavior.enable_battery_charging_reaction'] = (self.chk_enable_charging, 'check', 1, None)
        bat_layout.addWidget(self.chk_enable_charging)

        self.chk_simulate_battery = QCheckBox('Preview low-battery reaction')
        self.chk_simulate_battery.toggled.connect(self.simulate_low_battery_toggled.emit)
        bat_layout.addWidget(self.chk_simulate_battery)

        self.chk_simulate_charging = QCheckBox('⚡ Preview battery charging effects (Yellow indicator above head)')
        self.chk_simulate_charging.toggled.connect(self.simulate_charging_toggled.emit)
        bat_layout.addWidget(self.chk_simulate_charging)

        self._activity_group('System').addWidget(battery_card)

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
                if anim_id == 'focus_read':
                    self._section('Focus & Breaks', 'Quiet activities').addWidget(item_container)
                else:
                    grid.addWidget(item_container, row, col)

            cat_layout.addLayout(grid)
            group = 'Movement' if 'Locomotion' in cat_title else 'Rest' if 'Rest' in cat_title else 'Expressions' if 'Expressions' in cat_title else 'Transitions'
            self._activity_group(group).addWidget(cat_card)

        # Page alignment is finalized after all feature groups are built.

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
        self._combo(self._activity_group('Timing'), 'Activity frequency', 'behavior.preset', [('Calm', 'calm'), ('Normal', 'normal'), ('Playful', 'playful')])

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

        self._check(fx_layout, 'Dodge fast cursor movements', 'behavior.enable_spider_sense_dodging', True)
        self._check(self._activity_group('Effects'), 'Comic speech bubbles', 'behavior.enable_comic_bubbles', True)
        page.addWidget(fx_card)

        # Hotkey Cheat Sheet & Individual Enable/Disable Card
        hk_card = QFrame()
        hk_card.setObjectName('ActivityCategoryCard')
        hk_layout = QVBoxLayout(hk_card)
        hk_layout.setContentsMargins(14, 12, 14, 12)
        hk_layout.setSpacing(10)

        hk_header = QLabel('Keyboard shortcuts')
        hk_header.setObjectName('subheading')
        hk_layout.addWidget(hk_header)

        hk_hint = QLabel('Press number keys 1, 2, 3... 0 (top row or numpad) from anywhere to instantly trigger animations. Enable or disable individual number keys below:')
        hk_hint.setWordWrap(True)
        hk_hint.setObjectName('muted')
        hk_layout.addWidget(hk_hint)

        # Master Controls Row
        hk_ctrl_row = QVBoxLayout()
        self.chk_master_hotkeys = QCheckBox('Enable number-key shortcuts')
        self.chk_master_hotkeys.setChecked(bool(self.settings.get('behavior.enable_animation_hotkeys', True)))
        self.chk_master_hotkeys.toggled.connect(lambda val: self.settings.set('behavior.enable_animation_hotkeys', val))
        hk_ctrl_row.addWidget(self.chk_master_hotkeys)

        self.chk_require_mod = QCheckBox('Require Modifier (Win / Alt / Ctrl)')
        self.chk_require_mod.setChecked(bool(self.settings.get('behavior.hotkeys_require_modifier', False)))
        self.chk_require_mod.toggled.connect(lambda v: self.settings.set('behavior.hotkeys_require_modifier', v))
        hk_ctrl_row.addWidget(self.chk_require_mod)

        hk_ctrl_row.addStretch()

        btn_all_keys = QPushButton('Enable All')
        btn_all_keys.setStyleSheet('padding: 4px 8px; font-size: 11px;')
        btn_all_keys.clicked.connect(self._enable_all_hotkeys)
        hk_ctrl_row.addWidget(btn_all_keys)

        btn_no_keys = QPushButton('Disable All')
        btn_no_keys.setStyleSheet('padding: 4px 8px; font-size: 11px;')
        btn_no_keys.clicked.connect(self._disable_all_hotkeys)
        hk_ctrl_row.addWidget(btn_no_keys)

        hk_layout.addLayout(hk_ctrl_row)

        grid = QGridLayout()
        grid.setSpacing(6)
        keys_order = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
        enabled_keys = self.settings.get('behavior.enabled_number_keys', {})
        self._hotkey_checkboxes = {}

        for idx, k in enumerate(keys_order):
            act_name, act_title, _ = HOTKEY_MAPPINGS[k]
            row, col = idx, 0
            cell_box = QFrame()
            cell_box.setStyleSheet(
                "QFrame { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 4px; }"
            )
            c_layout = QHBoxLayout(cell_box)
            c_layout.setContentsMargins(6, 4, 6, 4)
            c_layout.setSpacing(6)

            chk_k = QCheckBox(f"Key {k}: {act_title}")
            chk_k.setChecked(bool(enabled_keys.get(k, True)))
            chk_k.toggled.connect(lambda val, key=k: self._on_number_key_toggled(key, val))
            self._hotkey_checkboxes[k] = chk_k
            c_layout.addWidget(chk_k, 1)

            btn_test = QPushButton("▶ Test")
            btn_test.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; padding: 3px 8px; font-size: 11px; } "
                "QPushButton:hover { background: #BA2444; border-color: #E04365; color: white; }"
            )
            btn_test.clicked.connect(lambda checked=False, act=act_name: self.activity_requested.emit(act))
            c_layout.addWidget(btn_test)

            grid.addWidget(cell_box, row, col)

        hk_layout.addLayout(grid)
        page.addWidget(hk_card)

        # Eye-Break & Hydration Alert Card
        eye_card = QFrame()
        eye_card.setObjectName('ActivityCategoryCard')
        eye_layout = QVBoxLayout(eye_card)
        eye_layout.setContentsMargins(14, 12, 14, 12)
        eye_layout.setSpacing(10)

        eye_header = QLabel('Break reminders')
        eye_header.setObjectName('subheading')
        eye_layout.addWidget(eye_header)

        eye_desc = QLabel(
            'When you type continuously (default 10 minutes) or when your focus timer finishes, Spider-Man webs '
            'the top-right corner of your screen with an eye-break alert and taps on the glass ("Time for water, man! 💧").'
        )
        eye_desc.setWordWrap(True)
        eye_desc.setObjectName('muted')
        eye_layout.addWidget(eye_desc)

        self._check(
            eye_layout,
            'Enable Continuous Typing & Eye-Break Web Alert',
            'behavior.enable_eye_break_alert',
            True,
        )

        thresh_row = QHBoxLayout()
        thresh_lbl = QLabel('Continuous work alert interval:')
        thresh_lbl.setStyleSheet('font-size: 12px; color: #E0E0E0;')
        thresh_row.addWidget(thresh_lbl)
        self.spin_eye_break_mins = QSpinBox()
        self.spin_eye_break_mins.setRange(10, 180)
        self.spin_eye_break_mins.setSingleStep(5)
        self.spin_eye_break_mins.setSuffix(' min')
        self.spin_eye_break_mins.setValue(max(10, int(self.settings.get('behavior.eye_break_minutes', 10))))
        self.spin_eye_break_mins.valueChanged.connect(lambda v: self.settings.set('behavior.eye_break_minutes', float(v)))
        thresh_row.addWidget(self.spin_eye_break_mins)
        thresh_row.addStretch()
        eye_layout.addLayout(thresh_row)

        limit_mins = int(self.settings.get('behavior.eye_break_minutes', 10))
        self.lbl_eye_break_status = QLabel(f'💧 Continuous Work: 0m 0s / {limit_mins}m • Focus Timer: Inactive')
        self.lbl_eye_break_status.setStyleSheet('font-weight: 600; font-size: 12px; color: #00D2FF;')
        eye_layout.addWidget(self.lbl_eye_break_status)

        timer_row = QHBoxLayout()
        timer_lbl = QLabel('Focus Timer:')
        timer_lbl.setStyleSheet('font-size: 12px; color: #AAA;')
        timer_row.addWidget(timer_lbl)

        for mins in (25, 45, 60):
            btn_t = QPushButton(f"{mins} min")
            btn_t.setStyleSheet('padding: 4px 10px; font-size: 11px;')
            btn_t.clicked.connect(lambda checked=False, m=mins: self.focus_timer_started.emit(float(m)))
            timer_row.addWidget(btn_t)

        btn_stop = QPushButton('Cancel Timer')
        btn_stop.setStyleSheet('padding: 4px 10px; font-size: 11px;')
        btn_stop.clicked.connect(self.focus_timer_stopped.emit)
        timer_row.addWidget(btn_stop)

        timer_row.addStretch()

        btn_test_alert = QPushButton('⚡ Preview Eye-Break Alert')
        btn_test_alert.clicked.connect(self.test_eye_break_requested.emit)
        eye_layout.addLayout(timer_row)
        eye_layout.addWidget(btn_test_alert)

        self._routes['Focus & Breaks'].addWidget(eye_card)

        # Interactive Web Trampolines Card
        tramp_card = QFrame()
        tramp_card.setObjectName('ActivityCategoryCard')
        tramp_layout = QVBoxLayout(tramp_card)
        tramp_layout.setContentsMargins(14, 12, 14, 12)
        tramp_layout.setSpacing(10)

        tramp_header = QLabel('Web trampoline')
        tramp_header.setObjectName('subheading')
        tramp_layout.addWidget(tramp_header)

        tramp_desc = QLabel(
            'Hold Ctrl + Drag on Spider-Man to draw an elastic spider-web trampoline anywhere on your screen. '
            'When Spider-Man jumps or falls onto it, 2D spring physics catapult him upward before the web dissolves!'
        )
        tramp_desc.setWordWrap(True)
        tramp_desc.setObjectName('muted')
        tramp_layout.addWidget(tramp_desc)

        tramp_btn_row = QVBoxLayout()
        btn_spawn_tramp = QPushButton('🕸️ Spawn Web Trampoline Below Spider-Man')
        btn_spawn_tramp.clicked.connect(self.spawn_trampoline_requested.emit)
        tramp_btn_row.addWidget(btn_spawn_tramp)

        btn_test_bounce = QPushButton('🚀 Test Jump & Trampoline Bounce')
        btn_test_bounce.clicked.connect(lambda: (
            self.spawn_trampoline_requested.emit(),
            self.activity_requested.emit('jump'),
        ))
        tramp_btn_row.addWidget(btn_test_bounce)
        tramp_layout.addLayout(tramp_btn_row)

        self._activity_group('Effects').addWidget(tramp_card)

        # Heavy Load Classic Collapsing Beam Scene Card (>85% CPU/RAM)
        load_card = QFrame()
        load_card.setObjectName('ActivityCategoryCard')
        lc_layout = QVBoxLayout(load_card)
        lc_layout.setContentsMargins(14, 12, 14, 12)
        lc_layout.setSpacing(10)

        lc_header = QLabel('System-load reaction')
        lc_header.setObjectName('subheading')
        lc_layout.addWidget(lc_header)

        lc_desc = QLabel(
            'When CPU or RAM hits >85% (heavy code compilation, 3D rendering, or gaming): '
            'Spider-Man sweats, pants, and reenacts the iconic classic scene of lifting a heavy collapsing steel I-beam.'
        )
        lc_desc.setWordWrap(True)
        lc_desc.setObjectName('muted')
        lc_layout.addWidget(lc_desc)

        self._check(
            lc_layout,
            'Enable Heavy System Load Scene Re-enactment (>85%)',
            'behavior.enable_heavy_load_scene',
            True,
        )

        self.lbl_system_load = QLabel('🔥 System Load: CPU: 0% • RAM: 0% (Normal)')
        self.lbl_system_load.setStyleSheet('font-weight: 600; font-size: 12px; color: #38BDF8;')
        lc_layout.addWidget(self.lbl_system_load)

        self.chk_simulate_heavy_load = QCheckBox('Preview system-load reaction')
        self.chk_simulate_heavy_load.toggled.connect(self.simulate_heavy_load_toggled.emit)
        lc_layout.addWidget(self.chk_simulate_heavy_load)

        self._activity_group('System').addWidget(load_card)

        # Audio & Music Synchronization Card (WASAPI Beat-Bobbing)
        audio_card = QFrame()
        audio_card.setObjectName('ActivityCategoryCard')
        ac_layout = QVBoxLayout(audio_card)
        ac_layout.setContentsMargins(14, 12, 14, 12)
        ac_layout.setSpacing(10)

        ac_header = QLabel('React to music')
        ac_header.setObjectName('subheading')
        ac_layout.addWidget(ac_header)

        ac_desc = QLabel(
            'Using Windows Core Audio API (WASAPI), Spider-Buddy detects active audio output (Spotify, YouTube, games). '
            'When music is playing, Spider-Man puts on red-and-black over-ear headphones and bobs his head or taps his sneaker '
            'in rhythm with the beat with floating cartoon musical notes.'
        )
        ac_desc.setWordWrap(True)
        ac_desc.setObjectName('muted')
        ac_layout.addWidget(ac_desc)

        self._check(
            ac_layout,
            'Enable Headphone Beat-Bobbing on System Audio / Music',
            'behavior.enable_audio_beat_bobbing',
            True,
        )

        self.lbl_audio_status = QLabel('🎧 Audio Status: Inactive • Peak: 0%')
        self.lbl_audio_status.setStyleSheet('font-weight: 600; font-size: 12px; color: #A855F7;')
        ac_layout.addWidget(self.lbl_audio_status)

        self.chk_simulate_music = QCheckBox('Preview music reaction')
        self.chk_simulate_music.toggled.connect(self.simulate_music_toggled.emit)
        ac_layout.addWidget(self.chk_simulate_music)

        self._activity_group('Music & Sound').addWidget(audio_card)

        self._check(page, 'Follow the mouse cursor', 'behavior.enable_mouse_following')
        self._check(page, 'WASD and arrow-key movement (W: Up, A: Left, S: Down, D: Right)', 'behavior.wasd_movement_enabled')
        self._check(page, 'Keep character static where stopped (Spacebar drops to ground)', 'behavior.wasd_static_pin')
        self._slider(page, 'Mouse attention radius', 'behavior.cursor_radius', 30, 500, 1, ' px')
        self._check(self._activity_group('Timing'), 'Allow automatic activity choices', 'behavior.enable_random_animations')
        self._slider(self._activity_group('Timing'), 'Movement speed', 'behavior.movement_speed', 1, 6)
        page = self._section('Focus & Breaks', 'When you step away')
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
        # Page alignment is finalized after all feature groups are built.

    def _build_appearance(self):
        page = self._section('Characters', 'Character appearance')
        self.size_slider = self._slider(page, 'Character size', 'general.scale', 100, 400, 200, ' px')
        self._slider(page, 'Opacity', 'general.opacity', 50, 100, 100, '%')
        self._combo(self._activity_group('Timing'), 'Animation speed', 'general.animation_speed', [('Slow', .65), ('Normal', 1.0), ('Fast', 1.5)])
        self._combo(self._section('Settings', 'Rendering'), 'Display frame rate', 'general.display_fps', [('Automatic', 0), ('30 FPS', 30), ('60 FPS', 60)])
        page = self._section('Desktop & Apps', 'Placement')
        self._combo(page, 'Default position', 'general.default_position', [('Bottom left', 'bottom_left'), ('Bottom right', 'bottom_right'), ('Custom', 'custom')])
        self._button(page, 'Use current character position as custom', self.save_position_requested.emit)
        page = self._activity_group('Music & Sound')
        self._check(page, 'Sound effects', 'behavior.sound_enabled', False)
        self._slider(page, 'Sound volume', 'behavior.sound_volume', 0, 100, 100, '%')
        # Page alignment is finalized after all feature groups are built.

    def _build_settings(self):
        page = self._page('Settings', 'Application preferences', 'Changes are saved automatically. Closing this window keeps the companion in the system tray.')
        self._combo(page, 'Theme', 'general.theme', [('Dark', 'dark'), ('Light', 'light')])
        self._check(page, 'Start with dashboard minimized', 'system.start_minimized', True)
        self._check(page, 'Launch Spider-Buddy when Windows starts', 'system.run_on_startup', False)
        page = self._section('Controls', 'Mouse click-through')
        self._check(page, 'Pass all mouse clicks through the character', 'system.click_through', False)
        note = QLabel('With click-through enabled, use this dashboard or the system tray to control the companion.')
        note.setWordWrap(True)
        page.addWidget(note)
        # Page alignment is finalized after all feature groups are built.

    def _navigate(self, index):
        self.pages.setCurrentIndex(index)
        QTimer.singleShot(0, self._fit_current_page)
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
        if hasattr(self, "hud_battery_lore") and hasattr(self, "_last_battery_state"):
            pct, charging, low = self._last_battery_state
            self.hud_battery_lore.setText(get_battery_lore(profile.id, pct, charging, low))
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.refresh_home()

    def _refresh_activity_options(self):
        profile = self.character_mgr.active_character
        if profile is None:
            return
        previous = self.animation_combo.currentData()
        was_blocked = self.animation_combo.blockSignals(True)
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
        self.animation_combo.blockSignals(was_blocked)
        self.play_button.setEnabled(self.animation_combo.count() > 0)
        self._update_activity_count_label()

    def _toggle_automatic_mode(self) -> None:
        new_val = not self.settings.get('behavior.automatic_animations', True)
        self.chk_automatic_animations.setChecked(new_val)

    def _update_auto_toggle_ui(self, is_auto: bool) -> None:
        light = self.settings.get('general.theme', 'dark') == 'light'
        active_style = (
            "QPushButton { background: #BA2444; color: #FFFFFF; font-weight: 700; "
            "font-size: 11px; border-radius: 12px; padding: 6px 14px; border: none; } "
            "QPushButton:hover { background: #D02B4F; }"
        )
        inactive_style = (
            f"QPushButton {{ background: transparent; color: {'#475569' if light else '#CBD5E1'}; "
            "font-weight: 600; font-size: 11px; border-radius: 12px; padding: 6px 14px; border: none; } "
            f"QPushButton:hover {{ background: {'rgba(0,0,0,0.06)' if light else 'rgba(255,255,255,0.1)'}; "
            f"color: {'#0F172A' if light else '#FFFFFF'}; }}"
        )
        if hasattr(self, 'btn_mode_auto') and hasattr(self, 'btn_mode_single'):
            if is_auto:
                self.btn_mode_auto.setStyleSheet(active_style)
                self.btn_mode_single.setStyleSheet(inactive_style)
            else:
                self.btn_mode_auto.setStyleSheet(inactive_style)
                self.btn_mode_single.setStyleSheet(active_style)

        if hasattr(self, 'lbl_mode_caption'):
            if is_auto:
                self.lbl_mode_caption.setText('Cycles randomly through enabled activities')
                self.lbl_mode_caption.setStyleSheet(f"font-size: 11px; color: {'#64748B' if light else '#A1A1AA'}; padding-top: 3px;")
            else:
                if hasattr(self, 'animation_combo') and self.animation_combo.count() > 0:
                    current_act = self.animation_combo.currentData() or 'dance'
                else:
                    current_act = self.settings.get('behavior.locked_activity', 'dance')
                act_title = ACTIVITIES.get(current_act, current_act.replace('_', ' ').title())
                self.lbl_mode_caption.setText(f'Locked: Loops "{act_title}" continuously')
                self.lbl_mode_caption.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {'#BA2444' if light else '#FB7185'}; padding-top: 3px;")

    def _on_automatic_mode_toggled(self, checked: bool) -> None:
        self.settings.set('behavior.automatic_animations', checked)
        self._update_auto_toggle_ui(checked)
        if not checked:
            current_act = self.animation_combo.currentData() or 'dance'
            self.settings.set('behavior.locked_activity', current_act)
            self.activity_requested.emit(current_act)

    def _on_animation_combo_changed(self, index: int) -> None:
        if not self.settings.get('behavior.automatic_animations', True):
            act_id = self.animation_combo.itemData(index)
            if act_id:
                self.settings.set('behavior.locked_activity', act_id)
                self._update_auto_toggle_ui(False)
                self.activity_requested.emit(act_id)

    def _on_number_key_toggled(self, key_char: str, enabled: bool) -> None:
        enabled_map = dict(self.settings.get('behavior.enabled_number_keys', {}))
        enabled_map[key_char] = bool(enabled)
        self.settings.set('behavior.enabled_number_keys', enabled_map)

    def _enable_all_hotkeys(self) -> None:
        enabled_map = {k: True for k in HOTKEY_MAPPINGS}
        self.settings.set('behavior.enabled_number_keys', enabled_map)
        for k, chk in getattr(self, '_hotkey_checkboxes', {}).items():
            chk.blockSignals(True)
            chk.setChecked(True)
            chk.blockSignals(False)

    def _disable_all_hotkeys(self) -> None:
        enabled_map = {k: False for k in HOTKEY_MAPPINGS}
        self.settings.set('behavior.enabled_number_keys', enabled_map)
        for k, chk in getattr(self, '_hotkey_checkboxes', {}).items():
            chk.blockSignals(True)
            chk.setChecked(False)
            chk.blockSignals(False)

    def _enable_text_selection(self) -> None:
        """Allow user to highlight and copy any text throughout the entire app."""
        for lbl in self.findChildren(QLabel):
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
            if lbl.text() and not lbl.pixmap():
                lbl.setCursor(Qt.IBeamCursor)

    def _on_play_button_clicked(self):
        act_id = self.animation_combo.currentData() or 'idle'
        act_title = ACTIVITIES.get(act_id, act_id.replace('_', ' ').title())
        is_auto = self.settings.get('behavior.automatic_animations', True)
        if not is_auto:
            self.settings.set('behavior.locked_activity', act_id)
            if hasattr(self, 'lbl_auto_status'):
                self.lbl_auto_status.setText(f'Single Locked: {act_title} (OFF)')
                self.lbl_auto_status.setStyleSheet('font-size: 11px; font-weight: 600; color: #F59E0B;')
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

    def update_preview(self, pixmap):
        self._last_preview = pixmap
        if hasattr(self, "qml_frame_provider") and self.isVisible() and self.pages.currentIndex() == 0:
            self.qml_frame_provider.frame = pixmap.toImage()
            self.qml_bridge.frame_updated()
        if self.isVisible() and self.pages.currentIndex() == 0 and not pixmap.isNull():
            self.preview.setPixmap(pixmap.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_status(self, old, state):
        self._status_text = 'Status: '+state.value.replace('_', ' ').title()
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.set_status(self._is_running, self._status_text)
        self.status_label.setText(self._status_text if self._is_running else 'Status: Paused')

    def set_running(self, running):
        self._is_running = running
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.set_status(running, self._status_text)
        self.toggle_btn.setText('Pause' if running else 'Resume')
        self.status_label.setText(self._status_text if running else 'Status: Paused')

    def _toggle_running_state(self):
        if self._is_running:
            self.stop_requested.emit()
        else:
            self.start_requested.emit()

    def _update_responsive_controls(self, tier: str) -> None:
        is_compact = (tier == 'compact')
        if hasattr(self, 'btn_select_all'):
            self.btn_select_all.setText('Select All')
        if hasattr(self, 'btn_deselect_all'):
            self.btn_deselect_all.setText('None' if is_compact else 'Deselect All')
        if hasattr(self, 'btn_reset_defaults'):
            self.btn_reset_defaults.setText('Reset' if is_compact else 'Reset Defaults')
        if hasattr(self, 'btn_mode_auto'):
            self.btn_mode_auto.setText('Automatic' if is_compact else 'Automatic')
        if hasattr(self, 'btn_mode_single'):
            self.btn_mode_single.setText('Repeat one' if is_compact else 'Repeat one')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        is_big = self.isMaximized() or w >= 1180
        is_compact = (not is_big) and w < 860
        tier = "big" if is_big else ("compact" if is_compact else "normal")

        if getattr(self, "_current_size_tier", None) != tier:
            self._current_size_tier = tier
            self.apply_theme()
            self._update_responsive_controls(tier)

        if hasattr(self, 'char_selection_widget'):
            QTimer.singleShot(0, self.char_selection_widget._reflow)
        self._enable_text_selection()

        # Enforce maximum viewport width on all scroll body widgets so horizontal clipping NEVER happens
        for scroll, body, page_layout in getattr(self, '_page_scroll_areas', []):
            if scroll and scroll.viewport() and body:
                vw = scroll.viewport().width()
                if vw > 0:
                    body.setMaximumWidth(16777215)
                if page_layout:
                    if is_compact:
                        page_layout.setContentsMargins(8, 6, 8, 8)
                        page_layout.setSpacing(8)
                    elif is_big:
                        page_layout.setContentsMargins(26, 16, 26, 22)
                        page_layout.setSpacing(18)
                    else:
                        page_layout.setContentsMargins(14, 10, 14, 12)
                        page_layout.setSpacing(12)

    def _fit_current_page(self):
        scroll = self.pages.currentWidget()
        if scroll:
            scroll.widget().setMaximumWidth(16777215)
        if self.pages.currentIndex() == 1:
            self.char_selection_widget._reflow()
        if self.pages.currentIndex() == 0 and hasattr(self, '_last_preview'):
            self.update_preview(self._last_preview)

    def showEvent(self, event):
        super().showEvent(event)
        self._enable_text_selection()
        QTimer.singleShot(0, self._fit_current_page)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def apply_theme(self):
        light = self.settings.get('general.theme', 'dark') == 'light'
        bg, panel, fg, muted, border, hover = (('#F2F4F8','#FFFFFF','#182233','#616E82','#D8DFEA','#E9EEF6')
            if light else ('#101114','#191b20','#F4F4F5','#A3A6B1','#2b2e36','#252830'))
        palette = self.palette()
        for role, color in ((QPalette.Window,bg),(QPalette.Base,panel),(QPalette.AlternateBase,hover),
                            (QPalette.Text,fg),(QPalette.WindowText,fg),(QPalette.ButtonText,fg),
                            (QPalette.Button,panel),(QPalette.Highlight,'#BA2444'),(QPalette.HighlightedText,'#FFFFFF')):
            palette.setColor(role,QColor(color))
        self.setPalette(palette)

        w = self.width() if hasattr(self, 'width') else 940
        is_big = self.isMaximized() or w >= 1180
        is_compact = (not is_big) and w < 860

        if is_compact:
            base_font_size = "12px"
            heading_size = "19px"
            subheading_size = "14px"
            btn_padding = "5px 10px"
            btn_font_size = "11px"
            card_padding = "8px 10px"
            sidebar_w = 158
            sidebar_item_padding = "8px 8px"
            control_padding = "5px"
        elif is_big:
            base_font_size = "14px"
            heading_size = "28px"
            subheading_size = "20px"
            btn_padding = "12px 18px"
            btn_font_size = "13px"
            card_padding = "18px 16px"
            sidebar_w = 196
            sidebar_item_padding = "14px 12px"
            control_padding = "9px"
        else:
            base_font_size = "13px"
            heading_size = "25px"
            subheading_size = "16px"
            btn_padding = "8px 14px"
            btn_font_size = "12px"
            card_padding = "12px 14px"
            sidebar_w = 180
            sidebar_item_padding = "11px 10px"
            control_padding = "7px"

        if hasattr(self, 'sidebar'):
            self.sidebar.setFixedWidth(sidebar_w)
        if hasattr(self, 'preview'):
            prev_h = 260 if is_big else (150 if is_compact else 200)
            self.preview.setMinimumHeight(prev_h)
        if hasattr(self, 'qml_pages'):
            for qk in self.qml_pages.values():
                if qk:
                    qk.setClearColor(QColor(bg))
        if hasattr(self, '_update_search_theme'):
            self._update_search_theme(light)

        self.setStyleSheet(f"""
            QWidget {{ color: {fg}; font-family: 'Segoe UI'; font-size: {base_font_size}; }}
            QMainWindow, QDialog, QScrollArea, QScrollArea > QWidget > QWidget {{ background-color: {bg}; }}
            QWidget#sidebar {{ background-color: {panel}; border: 1px solid {border}; border-radius: 14px; }}
            QLabel {{ background: transparent; border: none; selection-background-color: #BA2444; selection-color: white; }}
            QLabel#heading {{ font-size: {heading_size}; font-weight: 700; padding-bottom: 2px; }}
            QLabel#subheading {{ font-size: {subheading_size}; font-weight: 600; }}
            QLabel#muted {{ color: {muted}; }}
            QAbstractItemView, QComboBox, QSpinBox, QLineEdit {{ background-color: {panel}; color: {fg};
                selection-background-color: #BA2444; selection-color: white;
                border: 1px solid {border}; border-radius: 8px; padding: {control_padding}; }}
            QListWidget::item {{ padding: {sidebar_item_padding}; border-radius: 6px; }}
            QListWidget::item:hover {{ background: {hover}; }}
            QListWidget::item:selected {{ background: #BA2444; color: white; }}
            QListWidget#navigation {{ background: transparent; border: none; padding: 0; outline: none; }}
            QListWidget#navigation::item {{ padding: {sidebar_item_padding}; color: {muted}; border-radius: 8px; font-size: {base_font_size}; }}
            QListWidget#navigation::item:hover {{ background: {hover}; color: {fg}; }}
            QListWidget#navigation::item:selected {{ background: #BA2444; color: white; font-weight: 600; }}
            QPushButton {{ background: {panel}; border: 1px solid {border}; border-radius: 8px; padding: {btn_padding}; font-weight: 600; font-size: {btn_font_size}; }}
            QPushButton:hover {{ background: {hover}; border-color: #CE3556; }}
            QPushButton[primary="true"] {{ background: #BA2444; color: white; border: 1px solid #BA2444; }}
            QPushButton:disabled {{ color: {muted}; background: {bg}; }}
            QPushButton:focus, QComboBox:focus, QLineEdit:focus {{ border: 1px solid #CE3556; }}
            QCheckBox {{ spacing: 8px; padding: 4px; }}
            QSlider::groove:horizontal {{ background: {border}; height: 6px; border-radius: 3px; }}
            QSlider::sub-page:horizontal {{ background: #BA2444; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: #E04365; width: 16px; margin: -5px 0; border-radius: 8px; }}
            QFrame#CharacterCard {{ background: {panel}; border: 1px solid {border}; border-radius: 12px; }}
            QFrame#CharacterCard[selected="true"] {{ border: 2px solid #CE3556; }}
            QFrame#AddCharacterCard {{ background: {panel}; border: 2px dashed {border}; border-radius: 12px; }}
            QFrame#AddCharacterCard:hover {{ border-color: #CE3556; }}
            QFrame#ActivityCategoryCard {{ background: {panel}; border: 1px solid {border}; border-radius: 12px; }}
            QFrame#companionStage {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {panel},stop:1 {hover}); border: 1px solid {border}; border-radius: 22px; }}
            QFrame#searchGlassContainer {{
                background-color: {'qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(255,255,255,0.55),stop:0.5 rgba(246,248,254,0.35),stop:1 rgba(235,239,250,0.45))' if light else 'qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(255,255,255,0.06),stop:0.5 rgba(255,255,255,0.03),stop:1 rgba(255,255,255,0.04))'};
                border: 1px solid {'rgba(255,255,255,0.85)' if light else 'rgba(255,255,255,0.12)'};
                border-bottom: 1.5px solid {'rgba(220,226,242,0.85)' if light else 'rgba(255,255,255,0.08)'};
                border-radius: 27px;
                min-height: 52px;
                max-height: 52px;
            }}
            QFrame#searchInnerPill {{
                background-color: {'#EEF1F7' if light else '#171923'};
                border: 1px solid {'rgba(255,255,255,0.95)' if light else 'rgba(255,255,255,0.06)'};
                border-radius: 19px;
                min-height: 38px;
                max-height: 38px;
            }}
            QFrame#searchInnerPill[focused="true"] {{
                background-color: {'#FFFFFF' if light else '#1C1F2C'};
                border: 1.2px solid {'#B8C2D8' if light else '#3E445A'};
            }}
            QLineEdit#settingsSearch {{
                background: transparent;
                border: none;
                color: {'#1E2538' if light else '#F4F4F6'};
                font-size: 13.5px;
                font-weight: 450;
                padding: 0;
                selection-background-color: #BA2444;
                selection-color: #FFFFFF;
            }}
            QLabel#searchBadgeKey {{
                background-color: {'#E2E5EE' if light else '#242838'};
                color: {'#757C90' if light else '#8E96AB'};
                border: 1px solid {'rgba(255,255,255,0.85)' if light else 'rgba(255,255,255,0.06)'};
                border-radius: 6px;
                font-size: 10.5px;
                font-weight: 600;
                padding: 3px 7px;
            }}
            QLabel#searchBadgeDot {{
                color: {'#9AA1B2' if light else '#646C82'};
                font-size: 12px;
                font-weight: 700;
            }}
            QFrame#topCompanionBadge {{
                background-color: {'#EEF1F7' if light else '#151729'};
                border: 1px solid {'#D8DFEA' if light else '#1E2235'};
                border-radius: 14px;
            }}
            QPushButton#topHeaderBtn {{
                background-color: {'#EEF1F7' if light else '#151729'};
                border: 1px solid {'#D8DFEA' if light else '#1E2235'};
                border-radius: 8px;
                color: {'#182233' if light else '#F8FAFC'};
                font-size: 13px;
            }}
            QPushButton#topHeaderBtn:hover {{
                background-color: {'#E2E6F0' if light else '#1C2038'};
                border-color: #F32155;
            }}
            QPushButton#topWinBtn {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: {'#757C90' if light else '#9BA8C0'};
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton#topWinBtn:hover {{
                background-color: {'#E2E6F0' if light else '#1E2235'};
                color: {'#182233' if light else '#FFFFFF'};
            }}
            QPushButton#topWinBtnClose {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: {'#757C90' if light else '#9BA8C0'};
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton#topWinBtnClose:hover {{
                background-color: #EF4444;
                color: #FFFFFF;
            }}
            QListWidget#settingsSearchResults {{
                background-color: {panel};
                border: 1.5px solid #BA2444;
                border-radius: 14px;
                padding: 6px;
                outline: none;
            }}
            QListWidget#settingsSearchResults::item {{
                padding: 10px 14px;
                border-radius: 8px;
                color: {fg};
                font-size: 13px;
            }}
            QListWidget#settingsSearchResults::item:hover {{
                background-color: {hover};
            }}
            QListWidget#settingsSearchResults::item:selected {{
                background-color: #BA2444;
                color: #FFFFFF;
                font-weight: 600;
            }}
            QTabWidget, QTabWidget::pane {{ border: none; background: transparent; }}
            QTabWidget > QWidget {{ background: transparent; }}
            QTabBar {{ background: transparent; border: none; }}
            QTabBar::tab {{ color: {muted}; background: {panel}; padding: 9px 14px; border: none; border-bottom: 2px solid transparent; font-weight: 600; font-size: 11px; }}
            QTabBar::tab:selected {{ color: {fg}; background: {hover}; border-bottom: 2px solid #E04A64; }}
            QTabBar::tab:hover {{ background: {hover}; color: {fg}; }}
            QFrame#ModeSegmentedControl {{ background: {hover}; border: 1px solid {border}; border-radius: 16px; }}
            QScrollBar:vertical {{ background: {bg}; width: 8px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {border}; min-height: 28px; border-radius: 4px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

    def keyPressEvent(self, event):
        """Allow direct keyboard activation of animations (1..0) when dashboard is focused."""
        from PySide6.QtWidgets import QLineEdit, QTextEdit
        focus = self.focusWidget()
        if isinstance(focus, (QLineEdit, QTextEdit)):
            super().keyPressEvent(event)
            return

        text = event.text()
        if text in HOTKEY_MAPPINGS:
            enabled_keys = self.settings.get("behavior.enabled_number_keys", {})
            if self.settings.get("behavior.enable_animation_hotkeys", True) and enabled_keys.get(text, True):
                act_name, title, _ = HOTKEY_MAPPINGS[text]
                self.activity_requested.emit(act_name)
                event.accept()
                return

        super().keyPressEvent(event)

    def update_eye_break_status(self, continuous_sec: float, timer_sec: float, timer_active: bool) -> None:
        """Update continuous typing and focus timer status label."""
        if hasattr(self, "lbl_eye_break_status"):
            active_mins = int(continuous_sec // 60)
            active_secs = int(continuous_sec % 60)
            limit_mins = int(self.settings.get("behavior.eye_break_minutes", 10))
            timer_text = f"{int(timer_sec // 60)}:{int(timer_sec % 60):02d} left" if timer_active else "Inactive"
            self.lbl_eye_break_status.setText(
                f"💧 Continuous Work: {active_mins}m {active_secs}s / {limit_mins}m • Focus Timer: {timer_text}"
            )

        if hasattr(self, "focus_countdown_label"):
            if timer_active:
                mins = int(timer_sec // 60)
                secs = int(timer_sec % 60)
                self.focus_countdown_label.setText(f"{mins:02d}:{secs:02d}")
                self.focus_countdown_label.setStyleSheet("font-size: 26px; font-weight: 700; color: #38BDF8;")
            elif not getattr(self, "_focus_just_started", False):
                self.focus_countdown_label.setText("25:00")
                self.focus_countdown_label.setStyleSheet("font-size: 26px; font-weight: 700; color: #64748B;")
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.refresh_home()

    def update_battery_status(self, percent: int, is_charging: bool, is_low: bool) -> None:
        """Update battery status indicator in Settings / Appearance and Sidebar."""
        self._last_battery_state = (percent, is_charging, is_low)
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.set_battery(percent, is_charging)
        if hasattr(self, "battery_status_lbl"):
            charge_str = "Charging" if is_charging else "On Battery"
            state_str = "⚠️ LOW BATTERY" if is_low else "Normal"
            color = "#FFE600" if is_charging else ("#EF4444" if is_low else "#22C55E")
            self.battery_status_lbl.setText(f"🔋 Battery: {percent}% ({charge_str}) • {state_str}")
            self.battery_status_lbl.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {color};")

        # Live HUD Battery Card update
        if hasattr(self, "hud_battery_pct"):
            charge_str = "Charging" if is_charging else "On Battery"
            icon = "⚡" if is_charging else ("🪫" if is_low else "🔋")
            color = "#FFE600" if is_charging else ("#EF4444" if is_low else "#22C55E")
            self.hud_battery_pct.setText(f"{icon} {percent}% • {charge_str}")
            self.hud_battery_pct.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {color};")
            char_id = getattr(self.character_mgr.active_character, "id", "") if self.character_mgr else ""
            self.hud_battery_lore.setText(get_battery_lore(char_id, percent, is_charging, is_low))
            self.hud_battery_bar.setValue(percent)
            bar_color = "#FFE600" if is_charging else ("#EF4444" if is_low else "#22C55E")
            self.hud_battery_bar.setStyleSheet(f"""
                QProgressBar {{
                    background: #1E293B;
                    border-radius: 3px;
                    border: none;
                }}
                QProgressBar::chunk {{
                    background: {bar_color};
                    border-radius: 3px;
                }}
            """)

        if hasattr(self, "sidebar_battery_card") and hasattr(self, "sidebar_bat_text"):
            if is_charging:
                self.sidebar_bat_icon.setText("⚡")
                self.sidebar_bat_text.setText(f"{percent}% • Charging")
                self.sidebar_bat_text.setStyleSheet("font-size: 11px; font-weight: 700; color: #FFE600;")
                self.sidebar_battery_card.setStyleSheet("""
                    QFrame#SidebarBatteryCard {
                        background: #1E1C12;
                        border: 1.5px solid #FFE600;
                        border-radius: 8px;
                    }
                """)
            elif is_low:
                self.sidebar_bat_icon.setText("🪫")
                self.sidebar_bat_text.setText(f"{percent}% • Low")
                self.sidebar_bat_text.setStyleSheet("font-size: 11px; font-weight: 700; color: #EF4444;")
                self.sidebar_battery_card.setStyleSheet("""
                    QFrame#SidebarBatteryCard {
                        background: #201416;
                        border: 1.5px solid #EF4444;
                        border-radius: 8px;
                    }
                """)
            else:
                self.sidebar_bat_icon.setText("🔋")
                self.sidebar_bat_text.setText(f"{percent}% • Battery")
                self.sidebar_bat_text.setStyleSheet("font-size: 11px; font-weight: 600; color: #E2E8F0;")
                self.sidebar_battery_card.setStyleSheet("""
                    QFrame#SidebarBatteryCard {
                        background: #161820;
                        border: 1px solid #2B2E38;
                        border-radius: 8px;
                    }
                """)
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.refresh_home()

    def update_system_load(self, cpu: float, ram: float, is_heavy: bool) -> None:
        """Update live CPU & RAM metrics label and Spidey-Sense alert."""
        if hasattr(self, "lbl_system_load"):
            state_tag = "⚠️ CRITICAL HEAVY LOAD (>85%)" if is_heavy else "Normal"
            color = "#EF4444" if is_heavy else "#38BDF8"
            self.lbl_system_load.setText(f"🔥 System Load: CPU: {int(cpu)}% • RAM: {int(ram)}% ({state_tag})")
            self.lbl_system_load.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {color};")

        if hasattr(self, "hud_load_metrics"):
            self.hud_load_metrics.setText(f"CPU: {int(cpu)}% • RAM: {int(ram)}%")
            txt, col, border = get_spidey_sense_status(cpu, ram, is_heavy)
            self.hud_spidey_sense.setText(txt)
            bg = "#2A1015" if (is_heavy or max(cpu, ram) >= 80) else ("#241C0E" if max(cpu, ram) >= 50 else "#0D2618")
            self.hud_spidey_sense.setStyleSheet(
                f"padding: 6px 10px; border-radius: 6px; font-weight: 600; font-size: 11px; "
                f"background: {bg}; border: 1px solid {border}; color: {col};"
            )
        if hasattr(self, "qml_bridge"):
            self.qml_bridge.set_load(cpu, ram)

    def update_audio_meter(self, peak: float, smoothed: float) -> None:
        """Update live audio peak indicator."""
        if hasattr(self, "lbl_audio_status") and not getattr(self, "_music_playing", False):
            pct = int(peak * 100)
            self.lbl_audio_status.setText(f"🎧 Audio Status: Listening • Peak: {pct}%")

    def update_music_state(self, is_playing: bool, volume: float) -> None:
        """Update live music playback status."""
        self._music_playing = bool(is_playing)
        if hasattr(self, "lbl_audio_status"):
            if is_playing:
                self.lbl_audio_status.setText("🎧 Music Playing: Active! • Beat-bobbing engaged")
                self.lbl_audio_status.setStyleSheet("font-weight: 600; font-size: 12px; color: #00E5FF;")
            else:
                self.lbl_audio_status.setText("🎧 Audio Status: Inactive • Peak: 0%")
                self.lbl_audio_status.setStyleSheet("font-weight: 600; font-size: 12px; color: #A855F7;")
