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
            title: "Controls & Interaction"
            badge: "Shortcuts & Input"
        }

        // Keyboard Shortcuts Card
        Card {
            width: parent.width
            height: hotkeyCol.implicitHeight + Theme.space32

            Column {
                id: hotkeyCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space16
                spacing: Theme.space16

                Text {
                    text: "Keyboard Hotkeys"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.bold: true
                    color: Theme.textPrimary
                }

                SettingRow {
                    title: "Enable Number Key Hotkeys (1 - 9)"
                    description: "Trigger animations directly via keyboard (1: Walk, 2: Jump, 3: Dance, etc.)"
                    controlKey: "hotkeys"

                    StyledSwitch {
                        checked: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("behavior.enable_animation_hotkeys", true) : true
                        onToggled: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("behavior.enable_animation_hotkeys", val)
                        }
                    }
                }

                SettingRow {
                    title: "Require Modifier Key"
                    description: "Require Alt or Win key combo (e.g. Win+1) to prevent interfering with typing"
                    controlKey: "hotkey_modifier"

                    StyledSwitch {
                        checked: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("behavior.hotkeys_require_modifier", false) : false
                        onToggled: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("behavior.hotkeys_require_modifier", val)
                        }
                    }
                }
            }
        }

        // Mouse & Reflex Card
        Card {
            width: parent.width
            height: mouseCol.implicitHeight + Theme.space32

            Column {
                id: mouseCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space16
                spacing: Theme.space16

                Text {
                    text: "Mouse Interaction & Reflexes"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    font.bold: true
                    color: Theme.textPrimary
                }

                SettingRow {
                    title: "Spider-Sense Cursor Dodge"
                    description: "Spider-Man reflexively jumps or flips away when your mouse cursor approaches"
                    controlKey: "spider_sense_dodge"

                    StyledSwitch {
                        checked: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("behavior.enable_spider_sense_dodging", true) : true
                        onToggled: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("behavior.enable_spider_sense_dodging", val)
                        }
                    }
                }

                SettingRow {
                    title: "Click-Through Mode"
                    description: "Clicks pass entirely through Spider-Man to underlying applications"
                    controlKey: "click_through"

                    StyledSwitch {
                        checked: (typeof settingsBridge !== "undefined") ? settingsBridge.getWithDefault("system.click_through", false) : false
                        onToggled: function(val) {
                            if (typeof settingsBridge !== "undefined") settingsBridge.set("system.click_through", val)
                        }
                    }
                }
            }
        }
    }
}
