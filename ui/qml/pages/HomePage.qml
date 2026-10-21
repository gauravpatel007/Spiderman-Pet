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
        spacing: Theme.space24

        // Section Title
        SectionHeader {
            title: "Home"
            badge: "Live Companion"
        }

        // Two-column layout: Left Live Stage, Right Status & Quick Actions
        Row {
            width: parent.width
            spacing: Theme.space16

            // Live Stage Preview Card
            Card {
                width: (parent.width - Theme.space16) * 0.55
                height: 340

                Column {
                    anchors.fill: parent
                    anchors.margins: Theme.space16
                    spacing: Theme.space12

                    Text {
                        text: "Live Preview"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    // Interactive Stage
                    Rectangle {
                        width: parent.width
                        height: 240
                        radius: Theme.radiusSm
                        color: Theme.isDark ? "#141418" : "#EBEBEF"
                        border.color: Theme.borderBase
                        border.width: 1

                        // Grid lines for stage feel
                        Grid {
                            anchors.fill: parent
                            opacity: 0.15
                            columns: 8
                            rows: 6
                            spacing: 30
                            Repeater {
                                model: 48
                                Rectangle { width: 1; height: 1; color: Theme.textMuted }
                            }
                        }

                        // Character Graphic Centerpiece
                        Column {
                            anchors.centerIn: parent
                            spacing: Theme.space8

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "🕷️"
                                font.pixelSize: 64
                            }

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: (typeof characterModel !== "undefined") ? characterModel.activeCharacterId : "Spider-Man"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                font.bold: true
                                color: Theme.textPrimary
                            }

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: (typeof statusModel !== "undefined") ? statusModel.activeActivity : "Idle & Look Around"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                color: Theme.accent
                            }
                        }
                    }

                    Text {
                        text: "💡 Click or drag the desktop companion anytime to interact directly."
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }
                }
            }

            // Status & Quick Action Card
            Card {
                width: (parent.width - Theme.space16) * 0.45
                height: 340

                Column {
                    anchors.fill: parent
                    anchors.margins: Theme.space16
                    spacing: Theme.space16

                    Text {
                        text: "Companion Status"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    // Quick Toggle Buttons
                    Row {
                        width: parent.width
                        spacing: Theme.space8

                        StyledButton {
                            width: (parent.width - Theme.space8) / 2
                            text: (typeof statusModel !== "undefined" && statusModel.isPaused) ? "▶ Resume" : "⏸ Pause"
                            variant: (typeof statusModel !== "undefined" && statusModel.isPaused) ? "primary" : "secondary"
                            onClicked: if (typeof statusModel !== "undefined") statusModel.togglePause()
                        }

                        StyledButton {
                            width: (parent.width - Theme.space8) / 2
                            text: (typeof statusModel !== "undefined" && statusModel.isHidden) ? "👁️ Show" : "🙈 Hide"
                            variant: "secondary"
                            onClicked: if (typeof statusModel !== "undefined") statusModel.toggleHide()
                        }
                    }

                    // Focus Mode Quick Card
                    Rectangle {
                        width: parent.width
                        height: 68
                        radius: Theme.radiusSm
                        color: Theme.isDark ? "#24242C" : "#EBEBEF"
                        border.color: (typeof statusModel !== "undefined" && statusModel.isFocusMode) ? Theme.accent : Theme.borderBase
                        border.width: 1

                        Row {
                            anchors.fill: parent
                            anchors.margins: Theme.space12
                            spacing: Theme.space12

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - 56
                                spacing: 2

                                Text {
                                    text: "🌙 Focus Mode"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    font.bold: true
                                    color: Theme.textPrimary
                                }

                                Text {
                                    text: "Suppresses sudden acrobatics while working"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    color: Theme.textSecondary
                                }
                            }

                            StyledSwitch {
                                anchors.verticalCenter: parent.verticalCenter
                                checked: (typeof statusModel !== "undefined") ? statusModel.isFocusMode : false
                                onToggled: function(val) { if (typeof statusModel !== "undefined") statusModel.setFocusMode(val) }
                            }
                        }
                    }

                    // Current Target Box
                    Rectangle {
                        width: parent.width
                        height: 78
                        radius: Theme.radiusSm
                        color: Theme.isDark ? "#17171B" : "#F4F4F6"
                        border.color: Theme.borderBase
                        border.width: 1

                        Column {
                            anchors.fill: parent
                            anchors.margins: Theme.space12
                            spacing: 4

                            Text {
                                text: "Active Surface Target"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                font.bold: true
                                color: Theme.textMuted
                            }

                            Text {
                                text: (typeof statusModel !== "undefined") ? statusModel.currentTarget : "Entire Desktop"
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                font.bold: true
                                color: Theme.textPrimary
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }
    }
}
