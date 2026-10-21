import QtQuick
import "."

Item {
    id: root

    property bool isOpen: false
    property var searchResults: []
    property int selectedResultIndex: 0
    signal closed()

    anchors.fill: parent
    visible: isOpen

    // Backdrop
    Rectangle {
        anchors.fill: parent
        color: Theme.isDark ? "#CC0A0A0C" : "#80000000"

        MouseArea {
            anchors.fill: parent
            onClicked: root.closeModal()
        }
    }

    // Modal Box
    Rectangle {
        id: dialogBox
        width: Math.min(560, root.width - 48)
        height: Math.min(460, root.height - 80)
        anchors.horizontalCenter: parent.horizontalCenter
        y: 60
        radius: Theme.radiusMd
        color: Theme.bgCard
        border.color: Theme.borderHover
        border.width: 1

        Column {
            anchors.fill: parent
            spacing: 0

            // Search Input Header
            Rectangle {
                width: parent.width
                height: 56
                color: Theme.isDark ? "#17171B" : "#F4F4F6"
                radius: Theme.radiusMd

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.space16
                    anchors.rightMargin: Theme.space16
                    spacing: Theme.space12

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "🔍"
                        font.pixelSize: 16
                    }

                    TextInput {
                        id: searchInput
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 80
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontMd
                        color: Theme.textPrimary
                        focus: root.isOpen

                        Text {
                            anchors.fill: parent
                            visible: !searchInput.text && !searchInput.activeFocus
                            text: "Type a setting, feature, or activity (e.g. 'music', 'size', 'study')..."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            color: Theme.textMuted
                        }

                        onTextChanged: {
                            if (typeof settingsBridge !== "undefined") {
                                root.searchResults = settingsBridge.search(text)
                                root.selectedResultIndex = 0
                            }
                        }

                        Keys.onDownPressed: {
                            if (root.searchResults.length > 0) {
                                root.selectedResultIndex = Math.min(root.searchResults.length - 1, root.selectedResultIndex + 1)
                            }
                        }

                        Keys.onUpPressed: {
                            if (root.searchResults.length > 0) {
                                root.selectedResultIndex = Math.max(0, root.selectedResultIndex - 1)
                            }
                        }

                        Keys.onReturnPressed: {
                            root.selectResult(root.selectedResultIndex)
                        }

                        Keys.onEscapePressed: {
                            root.closeModal()
                        }
                    }

                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        width: 32
                        height: 22
                        radius: 4
                        color: Theme.isDark ? "#282832" : "#E2E2E8"

                        Text {
                            anchors.centerIn: parent
                            text: "ESC"
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            color: Theme.textSecondary
                        }
                    }
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.borderBase
                }
            }

            // Results List
            ListView {
                id: resultsList
                width: parent.width
                height: dialogBox.height - 56 - 40
                clip: true
                model: root.searchResults

                delegate: Rectangle {
                    width: resultsList.width
                    height: 56
                    color: index === root.selectedResultIndex ? (Theme.isDark ? "#282832" : "#EAEAEF") : "transparent"

                    Behavior on color { ColorAnimation { duration: Theme.animDuration } }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.leftMargin: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: 3
                        height: 24
                        color: Theme.accent
                        visible: index === root.selectedResultIndex
                    }

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.space16
                        anchors.rightMargin: Theme.space16
                        spacing: Theme.space12

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2
                            width: parent.width - 40

                            Text {
                                text: modelData.title
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBase
                                font.weight: Font.DemiBold
                                color: Theme.textPrimary
                            }

                            Text {
                                text: modelData.path
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSm
                                color: Theme.accent
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onEntered: root.selectedResultIndex = index
                        onClicked: root.selectResult(index)
                    }
                }

                // Empty / Placeholder state
                Item {
                    anchors.fill: parent
                    visible: root.searchResults.length === 0 && searchInput.text.length > 0

                    Column {
                        anchors.centerIn: parent
                        spacing: Theme.space8

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "No matching settings or activities found."
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBase
                            color: Theme.textSecondary
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Try searching 'headphones', 'size', 'chrome', or 'study'"
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textMuted
                        }
                    }
                }
            }

            // Footer Tips
            Rectangle {
                width: parent.width
                height: 40
                color: Theme.isDark ? "#17171B" : "#F4F4F6"

                Rectangle {
                    anchors.top: parent.top
                    width: parent.width
                    height: 1
                    color: Theme.borderBase
                }

                Row {
                    anchors.centerIn: parent
                    spacing: Theme.space16

                    Text {
                        text: "↑↓ Navigate"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }

                    Text {
                        text: "↵ Select & Jump"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }

                    Text {
                        text: "ESC Close"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSm
                        color: Theme.textMuted
                    }
                }
            }
        }
    }

    function openModal() {
        root.isOpen = true
        searchInput.text = ""
        root.searchResults = []
        searchInput.forceActiveFocus()
    }

    function closeModal() {
        root.isOpen = false
        root.closed()
    }

    function selectResult(index) {
        if (index >= 0 && index < root.searchResults.length) {
            var item = root.searchResults[index]
            if (typeof settingsBridge !== "undefined") {
                settingsBridge.requestNavigation(item.tabIndex, item.sectionId, item.controlKey)
            }
            root.closeModal()
        }
    }
}
