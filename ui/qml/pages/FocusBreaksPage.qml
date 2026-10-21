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
            title: "Focus & Breaks"
            badge: "Quiet & Reminders"
        }

        // Focus Mode Card
        Card {
            width: parent.width
            height: focusCol.implicitHeight + Theme.space32

            Column {
                id: focusCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space16
                spacing: Theme.space16

                Text {
                    text: "Focus & Quiet Modes"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.bold: true
                    color: Theme.textPrimary
                }

                SettingRow {
                    title: "Focus Mode Master Switch"
                    description: "Temporarily calms Spider-Man without modifying your saved activity settings"
                    controlKey: "focus_mode"

                    StyledSwitch {
                        checked: (typeof statusModel !== "undefined") ? statusModel.isFocusMode : false
                        onToggled: function(val) {
                            if (typeof statusModel !== "undefined") statusModel.setFocusMode(val)
                        }
                    }
                }

                SettingRow {
                    title: "Comic Reading Mode"
                    description: "Spider-Man sits calmly reading comic books quietly in the corner"
                    controlKey: "comic_reading"

                    StyledSwitch {
                        checked: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("animations.enabled.focus_read", true) : true
                        onToggled: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("animations.enabled.focus_read", val)
                        }
                    }
                }
            }
        }

        // Reminders & Health Card
        Card {
            width: parent.width
            height: reminderCol.implicitHeight + Theme.space32

            Column {
                id: reminderCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space16
                spacing: Theme.space16

                Text {
                    text: "Health & Break Reminders"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.bold: true
                    color: Theme.textPrimary
                }

                SettingRow {
                    title: "20-20-20 Eye-Break Reminders"
                    description: "Spider-Man displays gentle visual alerts to rest your eyes"
                    controlKey: "eye_break"

                    StyledSwitch {
                        checked: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("reminders.eye_break_enabled", true) : true
                        onToggled: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("reminders.eye_break_enabled", val)
                        }
                    }
                }

                SettingRow {
                    title: "Hydration Reminder Interval"
                    description: "Minutes between hydration prompts"
                    controlKey: "hydration"

                    StyledSlider {
                        from: 15
                        to: 90
                        stepSize: 5
                        value: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("reminders.hydration_interval", 45) : 45
                        suffix: " min"
                        onMoved: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("reminders.hydration_interval", val)
                        }
                    }
                }

                SettingRow {
                    title: "Inactivity to Sleep Timeout"
                    description: "Minutes of user keyboard/mouse inactivity before Spider-Man falls asleep"
                    controlKey: "sleep_timeout"

                    StyledSlider {
                        from: 1
                        to: 15
                        stepSize: 1
                        value: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("behavior.sleep_after_minutes", 5) : 5
                        suffix: " min"
                        onMoved: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("behavior.sleep_after_minutes", val)
                        }
                    }
                }
            }
        }
    }
}
