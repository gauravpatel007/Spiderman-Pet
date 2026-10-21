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
            title: "Desktop & Apps"
            badge: "Target Surfaces"
        }

        // Target Area Selection Card
        Card {
            width: parent.width
            height: targetCol.implicitHeight + Theme.space32

            Column {
                id: targetCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space16
                spacing: Theme.space16

                Text {
                    text: "Display Surface Mode"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.bold: true
                    color: Theme.textPrimary
                }

                SettingRow {
                    title: "Entire Desktop"
                    description: "Spider-Man roams across all visible displays, monitors, and the taskbar"
                    controlKey: "display_desktop"

                    StyledButton {
                        text: (typeof settingsBridge !== "undefined" && settingsBridge.getWithDefault("general.display_mode", "desktop") === "desktop") ? "Active" : "Select"
                        variant: (typeof settingsBridge !== "undefined" && settingsBridge.getWithDefault("general.display_mode", "desktop") === "desktop") ? "primary" : "secondary"
                        onClicked: if (typeof settingsBridge !== "undefined") settingsBridge.set("general.display_mode", "desktop")
                    }
                }

                SettingRow {
                    title: "Selected Applications Only"
                    description: "Restricts Spider-Man to active windows of specific target programs"
                    controlKey: "display_apps"

                    StyledButton {
                        text: (typeof settingsBridge !== "undefined" && settingsBridge.getWithDefault("general.display_mode", "desktop") === "applications") ? "Active" : "Select"
                        variant: (typeof settingsBridge !== "undefined" && settingsBridge.getWithDefault("general.display_mode", "desktop") === "applications") ? "primary" : "secondary"
                        onClicked: if (typeof settingsBridge !== "undefined") settingsBridge.set("general.display_mode", "applications")
                    }
                }
            }
        }

        // Positioning & Window Alignment Card
        Card {
            width: parent.width
            height: posCol.implicitHeight + Theme.space32

            Column {
                id: posCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space16
                spacing: Theme.space16

                Text {
                    text: "Positioning & Window Alignment"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.bold: true
                    color: Theme.textPrimary
                }

                SettingRow {
                    title: "Always on Top"
                    description: "Keep companion overlay rendered above all other running windows"
                    controlKey: "always_on_top"

                    StyledSwitch {
                        checked: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("system.always_on_top", true) : true
                        onToggled: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("system.always_on_top", val)
                        }
                    }
                }

                SettingRow {
                    title: "Title-Bar Alignment Offset"
                    description: "Vertical offset for perching and dangling from window headers"
                    controlKey: "title_bar_offset"

                    StyledSlider {
                        from: 10
                        to: 50
                        stepSize: 1
                        value: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("animations.title_bar_offset", 28) : 28
                        suffix: " px"
                        onMoved: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("animations.title_bar_offset", val)
                        }
                    }
                }
            }
        }
    }
}
