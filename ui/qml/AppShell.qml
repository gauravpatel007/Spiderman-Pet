import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "pages"

ApplicationWindow {
    id: window

    visible: true
    title: "Spider-Buddy Companion"
    width: 960
    height: 660
    minimumWidth: 640
    minimumHeight: 480
    color: Theme.bgBase

    // Global Key Shortcut for Ctrl+K
    Shortcut {
        sequence: "Ctrl+K"
        onActivated: searchModal.openModal()
    }

    // Connect SettingsBridge navigation
    Connections {
        target: (typeof settingsBridge !== "undefined") ? settingsBridge : null
        function onNavigationRequested(tabIndex, sectionId, controlKey) {
            sidebar.currentIndex = tabIndex
            stackLayout.currentIndex = tabIndex
            // Highlight control if currently visible
        }
    }

    Row {
        anchors.fill: parent

        // 1. Sidebar Navigation (Left)
        Sidebar {
            id: sidebar
            height: parent.height
            currentIndex: stackLayout.currentIndex
            onTabSelected: function(idx) {
                stackLayout.currentIndex = idx
            }
        }

        // 2. Main Content Area (Right)
        Column {
            width: parent.width - sidebar.width
            height: parent.height

            // Top Bar
            TopBar {
                id: topBar
                width: parent.width
                onSearchClicked: searchModal.openModal()
            }

            // Page Stack
            StackLayout {
                id: stackLayout
                width: parent.width
                height: parent.height - topBar.height
                currentIndex: 0

                HomePage { id: homePage }
                CharactersPage { id: charactersPage }
                ActivitiesPage { id: activitiesPage }
                DesktopAppsPage { id: desktopAppsPage }
                FocusBreaksPage { id: focusBreaksPage }
                ControlsPage { id: controlsPage }
                SettingsPage { id: settingsPage }
            }
        }
    }

    // 3. Global Search Modal Overlay (Spotlight)
    SearchModal {
        id: searchModal
        anchors.fill: parent
    }
}
