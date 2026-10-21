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

        // Page Header
        SectionHeader {
            title: "Activities Library"
            badge: "All Actions"
        }

        // Top Filter Bar Card
        Card {
            width: parent.width
            height: filterCol.implicitHeight + Theme.space24

            Column {
                id: filterCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space12
                spacing: Theme.space12

                // Row 1: Search input + State Filters
                Row {
                    width: parent.width
                    spacing: Theme.space12

                    // Search input
                    Rectangle {
                        width: parent.width * 0.5
                        height: 34
                        radius: Theme.radiusSm
                        color: Theme.bgInput
                        border.color: Theme.borderBase
                        border.width: 1

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space8
                            anchors.rightMargin: Theme.space8
                            spacing: Theme.space8

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "🔍"
                                font.pixelSize: 11
                            }

                            TextInput {
                                id: actSearchInput
                                anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - 30
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                color: Theme.textPrimary

                                Text {
                                    anchors.fill: parent
                                    visible: !actSearchInput.text && !actSearchInput.activeFocus
                                    text: "Search activities..."
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    color: Theme.textMuted
                                }

                                onTextChanged: {
                                    if (typeof activityModel !== "undefined") {
                                        activityModel.setSearchQuery(text)
                                    }
                                }
                            }
                        }
                    }

                    // State filter pills
                    Row {
                        spacing: Theme.space4
                        anchors.verticalCenter: parent.verticalCenter

                        Repeater {
                            model: ["All", "Enabled", "Disabled"]

                            Rectangle {
                                width: filterText.implicitWidth + Theme.space16
                                height: 32
                                radius: Theme.radiusSm
                                readonly property bool isSelected: (typeof activityModel !== "undefined" && activityModel.filterState === modelData) || (modelData === "All" && typeof activityModel === "undefined")
                                color: isSelected ? Theme.accent : (fMouse.containsMouse ? Theme.bgCardHover : "transparent")
                                border.color: isSelected ? "transparent" : Theme.borderBase
                                border.width: isSelected ? 0 : 1

                                Text {
                                    id: filterText
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSm
                                    font.weight: isSelected ? Font.Bold : Font.Normal
                                    color: isSelected ? "#FFFFFF" : Theme.textSecondary
                                }

                                MouseArea {
                                    id: fMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (typeof activityModel !== "undefined") {
                                            activityModel.setStateFilter(modelData)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Row 2: Mode & Frequency Controls
                Row {
                    width: parent.width
                    spacing: Theme.space24

                    // Mode: Auto vs Single
                    Row {
                        spacing: Theme.space8
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Mode:"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.bold: true
                            color: Theme.textSecondary
                        }

                        StyledButton {
                            text: "Automatic Cycle"
                            variant: (typeof activityModel !== "undefined" && activityModel.mode === "auto") ? "primary" : "secondary"
                            onClicked: if (typeof activityModel !== "undefined") activityModel.mode = "auto"
                        }

                        StyledButton {
                            text: "Single Activity"
                            variant: (typeof activityModel !== "undefined" && activityModel.mode === "single") ? "primary" : "secondary"
                            onClicked: if (typeof activityModel !== "undefined") activityModel.mode = "single"
                        }
                    }

                    // Frequency: Calm / Normal / Playful
                    Row {
                        spacing: Theme.space8
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Frequency:"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            font.bold: true
                            color: Theme.textSecondary
                        }

                        Repeater {
                            model: ["calm", "normal", "playful"]

                            StyledButton {
                                text: modelData.charAt(0).toUpperCase() + modelData.slice(1)
                                variant: (typeof activityModel !== "undefined" && activityModel.frequency === modelData) ? "primary" : "secondary"
                                onClicked: if (typeof activityModel !== "undefined") activityModel.frequency = modelData
                            }
                        }
                    }
                }
            }
        }

        // Expandable Timing & Dynamics Section
        Card {
            id: timingCard
            width: parent.width
            property bool isExpanded: false
            height: isExpanded ? timingContent.implicitHeight + Theme.space32 : 46

            Behavior on height { NumberAnimation { duration: Theme.animDuration; easing.type: Easing.OutQuad } }

            Column {
                id: timingContent
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.space12
                spacing: Theme.space12

                // Header / Toggle
                Item {
                    width: parent.width
                    height: 24

                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        spacing: Theme.space8

                        Text {
                            text: "⏱️ Timing & Animation Dynamics"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            font.bold: true
                            color: Theme.textPrimary
                        }

                        Text {
                            text: "(Speed, duration, cooldowns)"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textMuted
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        text: timingCard.isExpanded ? "▲ Hide" : "▼ Expand"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.accent
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: timingCard.isExpanded = !timingCard.isExpanded
                    }
                }

                // Timing rows
                Column {
                    width: parent.width
                    spacing: Theme.space8
                    visible: timingCard.isExpanded

                    SettingRow {
                        title: "Movement Speed"
                        description: "How fast Spider-Man traverses across window borders"
                        controlKey: "movement_speed"

                        StyledSlider {
                            from: 1.0
                            to: 8.0
                            stepSize: 0.5
                            value: (typeof activityModel !== "undefined") ? activityModel.movementSpeed : 3.0
                            suffix: " px/f"
                            onMoved: function(val) {
                                if (typeof activityModel !== "undefined") activityModel.movementSpeed = val
                            }
                        }
                    }

                    SettingRow {
                        title: "Animation Playback Speed"
                        description: "Multiplier applied to animation sprite frame rates"
                        controlKey: "anim_speed"

                        StyledSlider {
                            from: 0.5
                            to: 2.0
                            stepSize: 0.1
                            value: (typeof activityModel !== "undefined") ? activityModel.animationSpeed : 1.0
                            suffix: "x"
                            onMoved: function(val) {
                                if (typeof activityModel !== "undefined") activityModel.animationSpeed = val
                            }
                        }
                    }
                }
            }
        }

        // Activity Cards Grid
        Flow {
            width: parent.width
            spacing: Theme.space12

            Repeater {
                model: activityModel

                Card {
                    width: Math.max(260, (parent.width - Theme.space24) / 3)
                    height: 120
                    hoverable: true

                    Column {
                        anchors.fill: parent
                        anchors.margins: Theme.space12
                        spacing: Theme.space8

                        // Row 1: Name + Category badge + Toggle
                        Row {
                            width: parent.width

                            Column {
                                width: parent.width - toggleSwitch.width
                                spacing: 2

                                Text {
                                    width: parent.width - 8
                                    text: model.name
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontBase
                                    font.bold: true
                                    color: Theme.textPrimary
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: model.category
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: Theme.accent
                                }
                            }

                            StyledSwitch {
                                id: toggleSwitch
                                anchors.verticalCenter: parent.verticalCenter
                                checked: model.enabled
                                onToggled: function(val) {
                                    if (typeof activityModel !== "undefined") {
                                        activityModel.toggleActivity(model.activityId, val)
                                    }
                                }
                            }
                        }

                        // Description
                        Text {
                            width: parent.width
                            text: model.description
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textSecondary
                            elide: Text.ElideRight
                        }

                        // Row 3: Preview button (Selective preview animation)
                        Row {
                            width: parent.width

                            StyledButton {
                                text: model.isAnimating ? "⏹ Stop Preview" : "▶ Preview"
                                variant: model.isAnimating ? "primary" : "secondary"
                                onClicked: {
                                    if (typeof activityModel !== "undefined") {
                                        activityModel.previewActivity(model.activityId)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
