import QtQuick
import ".."
import "../components"

Item {
    id: root

    Flickable {
        anchors.fill: parent
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

            // Header with Import Button
            Row {
                width: parent.width

                SectionHeader {
                    width: parent.width - importBtn.width - Theme.space16
                    title: "Characters"
                    badge: "Companion Gallery"
                }

                StyledButton {
                    id: importBtn
                    anchors.verticalCenter: parent.verticalCenter
                    text: "+ Import Artwork"
                    variant: "secondary"
                    onClicked: importDialog.openModal()
                }
            }

            // Responsive Character Gallery
            Flow {
                width: parent.width
                spacing: Theme.space16

                Repeater {
                    model: characterModel

                    Card {
                        width: Math.max(160, (parent.width - Theme.space32) / 3)
                        height: 220
                        hoverable: true
                        border.color: model.isActive ? Theme.accent : (isHovered ? Theme.borderHover : Theme.borderBase)
                        border.width: model.isActive ? 2 : 1

                        Column {
                            anchors.fill: parent
                            anchors.margins: Theme.space12
                            spacing: Theme.space8

                            // Preview Box
                            Rectangle {
                                width: parent.width
                                height: 110
                                radius: Theme.radiusSm
                                color: Theme.isDark ? "#17171C" : "#EBEBEF"

                                Image {
                                    anchors.centerIn: parent
                                    width: 80
                                    height: 80
                                    fillMode: Image.PreserveAspectFit
                                    source: model.previewUrl
                                    visible: model.previewUrl.length > 0
                                }

                                Text {
                                    anchors.centerIn: parent
                                    visible: model.previewUrl.length === 0
                                    text: "🕷️"
                                    font.pixelSize: 42
                                }

                                // Active Tag
                                Rectangle {
                                    anchors.top: parent.top
                                    anchors.right: parent.right
                                    anchors.margins: 6
                                    width: 54
                                    height: 20
                                    radius: 4
                                    color: Theme.accent
                                    visible: model.isActive

                                    Text {
                                        anchors.centerIn: parent
                                        text: "ACTIVE"
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 9
                                        font.bold: true
                                        color: "#FFFFFF"
                                    }
                                }
                            }

                            // Info
                            Text {
                                width: parent.width
                                text: model.displayName
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                font.bold: true
                                color: Theme.textPrimary
                                elide: Text.ElideRight
                            }

                            Text {
                                width: parent.width
                                text: model.suit
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                color: Theme.textMuted
                                elide: Text.ElideRight
                            }

                            StyledButton {
                                width: parent.width
                                text: model.isActive ? "Selected" : "Select"
                                variant: model.isActive ? "ghost" : "secondary"
                                enabledState: !model.isActive
                                onClicked: {
                                    if (typeof characterModel !== "undefined") {
                                        characterModel.setActiveCharacter(model.charId)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Appearance & Customization Section
            Card {
                width: parent.width
                height: appearanceCol.implicitHeight + Theme.space32

                Column {
                    id: appearanceCol
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: Theme.space16
                    spacing: Theme.space16

                    Text {
                        text: "Character Appearance"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        font.bold: true
                        color: Theme.textPrimary
                    }

                    SettingRow {
                        title: "Character Size / Scale"
                        description: "Adjust how large the character renders on your screen (50% to 250%)"
                        controlKey: "scale"

                        StyledSlider {
                            from: 0.5
                            to: 2.5
                            stepSize: 0.1
                            value: (typeof characterModel !== "undefined") ? characterModel.scale : 1.0
                            suffix: "x"
                            onMoved: function(val) {
                                if (typeof characterModel !== "undefined") characterModel.scale = val
                            }
                        }
                    }

                    SettingRow {
                        title: "Character Opacity"
                        description: "Control transparency level of the companion overlay"
                        controlKey: "opacity"

                        StyledSlider {
                            from: 0.2
                            to: 1.0
                            stepSize: 0.05
                            value: (typeof characterModel !== "undefined") ? characterModel.opacity : 1.0
                            suffix: ""
                            onMoved: function(val) {
                                if (typeof characterModel !== "undefined") characterModel.opacity = val
                            }
                        }
                    }
                }
            }
        }
    }

    // Modal Import Dialog
    ImportDialog {
        id: importDialog
        anchors.fill: parent
    }
}
