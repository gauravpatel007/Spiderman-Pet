import QtQuick
import "."

Rectangle {
    id: root

    signal searchClicked()
    signal minimizeClicked()
    signal closeClicked()

    height: 54
    color: Theme.bgHeader
    border.color: Theme.borderBase
    border.width: 1

    Row {
        anchors.left: parent.left
        anchors.leftMargin: Theme.space16
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.space12

        // Global Search Bar Trigger
        Rectangle {
            id: searchBar
            width: 320
            height: 34
            radius: Theme.radiusSm
            color: searchMouse.containsMouse ? Theme.bgCardHover : Theme.bgInput
            border.color: searchMouse.containsMouse ? Theme.borderHover : Theme.borderBase
            border.width: 1

            Behavior on color { ColorAnimation { duration: Theme.animDuration } }
            Behavior on border.color { ColorAnimation { duration: Theme.animDuration } }

            Row {
                anchors.fill: parent
                anchors.leftMargin: Theme.space12
                anchors.rightMargin: Theme.space8
                spacing: Theme.space8

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "🔍"
                    font.pixelSize: 12
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Search settings & activities..."
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBase
                    color: Theme.textMuted
                }

                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    anchors.rightMargin: Theme.space8
                    width: 46
                    height: 20
                    radius: 4
                    color: Theme.isDark ? "#2A2A34" : "#E2E2E8"

                    Text {
                        anchors.centerIn: parent
                        text: "Ctrl + K"
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.bold: true
                        color: Theme.textSecondary
                    }
                }
            }

            MouseArea {
                id: searchMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.searchClicked()
            }
        }
    }

    // Right-aligned status indicators
    Row {
        anchors.right: parent.right
        anchors.rightMargin: Theme.space16
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.space12

        // Target Indicator
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            height: 28
            width: targetText.implicitWidth + Theme.space16
            radius: Theme.radiusSm
            color: Theme.isDark ? "#202026" : "#EAEAEF"
            border.color: Theme.borderBase
            border.width: 1

            Text {
                id: targetText
                anchors.centerIn: parent
                text: "🎯 " + ((typeof statusModel !== "undefined") ? statusModel.currentTarget : "Desktop")
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textSecondary
                elide: Text.ElideRight
            }
        }

        // Focus Badge
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            height: 28
            width: focusText.implicitWidth + Theme.space16
            radius: Theme.radiusSm
            visible: (typeof statusModel !== "undefined") && statusModel.isFocusMode
            color: Theme.accentSubtle
            border.color: Theme.accent
            border.width: 1

            Text {
                id: focusText
                anchors.centerIn: parent
                text: "🌙 Focus Active"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.bold: true
                color: Theme.accent
            }
        }
    }
}
