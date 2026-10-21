import QtQuick
import ".."
import "../components"

Flickable {
    id: root

    contentWidth: width
    contentHeight: Math.max(height, mainCol.implicitHeight + Theme.space32)
    clip: true

    Column {
        id: mainCol
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Theme.space24
        spacing: Theme.space20

        SectionHeader {
            title: "Settings"
            badge: "Application & System"
        }

        // Appearance & Theme Card
        Card {
            width: parent.width
            height: themeCol.implicitHeight + Theme.space32

            Column {
                id: themeCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space16
                spacing: Theme.space16

                Text {
                    text: "Appearance"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.bold: true
                    color: Theme.textPrimary
                }

                SettingRow {
                    title: "Dashboard Theme"
                    description: "Select between Charcoal Dark mode and Light mode"
                    controlKey: "theme"

                    Row {
                        spacing: Theme.space8

                        StyledButton {
                            text: "🌙 Dark"
                            variant: (typeof settingsBridge !== "undefined" && settingsBridge.theme === "dark") ? "primary" : "secondary"
                            onClicked: if (typeof settingsBridge !== "undefined") settingsBridge.theme = "dark"
                        }

                        StyledButton {
                            text: "☀️ Light"
                            variant: (typeof settingsBridge !== "undefined" && settingsBridge.theme === "light") ? "primary" : "secondary"
                            onClicked: if (typeof settingsBridge !== "undefined") settingsBridge.theme = "light"
                        }
                    }
                }

                SettingRow {
                    title: "Reduced UI Motion"
                    description: "Instantly switches tabs and disables UI transition animations"
                    controlKey: "reduced_motion"

                    StyledSwitch {
                        checked: (typeof settingsBridge !== "undefined") ? settingsBridge.reducedMotion : false
                        onToggled: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.reducedMotion = val
                        }
                    }
                }
            }
        }

        // System Integration Card
        Card {
            width: parent.width
            height: sysCol.implicitHeight + Theme.space32

            Column {
                id: sysCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space16
                spacing: Theme.space16

                Text {
                    text: "System Integration"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.bold: true
                    color: Theme.textPrimary
                }

                SettingRow {
                    title: "Launch on Windows Startup"
                    description: "Automatically start Spider-Buddy when your PC turns on"
                    controlKey: "run_on_startup"

                    StyledSwitch {
                        checked: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("system.run_on_startup", false) : false
                        onToggled: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("system.run_on_startup", val)
                        }
                    }
                }

                SettingRow {
                    title: "Start Minimized to System Tray"
                    description: "Keep the dashboard hidden when launching on startup"
                    controlKey: "start_minimized"

                    StyledSwitch {
                        checked: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("system.start_minimized", true) : true
                        onToggled: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("system.start_minimized", val)
                        }
                    }
                }
            }
        }

        // Maintenance Card
        Card {
            width: parent.width
            height: maintCol.implicitHeight + Theme.space32

            Column {
                id: maintCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space16
                spacing: Theme.space16

                Text {
                    text: "Maintenance & Reset"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.bold: true
                    color: Theme.textPrimary
                }

                SettingRow {
                    title: "Reset Configuration"
                    description: "Restore all companion and activity options to factory defaults"
                    controlKey: "reset_config"

                    StyledButton {
                        text: "Reset Defaults"
                        variant: "danger"
                        onClicked: {
                            if (typeof settingsBridge !== "undefined") {
                                settingsBridge.resetToDefaults()
                            }
                        }
                    }
                }
            }
        }
    }
}
