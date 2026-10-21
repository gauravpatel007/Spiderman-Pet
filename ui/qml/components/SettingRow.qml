import QtQuick
import ".."

Rectangle {
    id: root

    property string title: ""
    property string description: ""
    property string controlKey: ""
    property bool highlighted: false
    default property alias content: controlSlot.data

    implicitWidth: parent ? parent.width : 500
    implicitHeight: Math.max(52, col.implicitHeight + Theme.space16)
    radius: Theme.radiusSm

    color: highlighted ? Theme.accentSubtle : "transparent"
    border.color: highlighted ? Theme.accent : "transparent"
    border.width: highlighted ? 1 : 0

    Behavior on color { ColorAnimation { duration: Theme.animDurationSlow } }
    Behavior on border.color { ColorAnimation { duration: Theme.animDurationSlow } }

    function triggerHighlight() {
        root.highlighted = true
        highlightTimer.restart()
    }

    Timer {
        id: highlightTimer
        interval: 2200
        onTriggered: root.highlighted = false
    }

    Row {
        anchors.fill: parent
        anchors.leftMargin: Theme.space8
        anchors.rightMargin: Theme.space8
        spacing: Theme.space16

        Column {
            id: col
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - controlSlot.width - parent.spacing - Theme.space16
            spacing: Theme.space2

            Text {
                width: parent.width
                text: root.title
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBase
                font.weight: Font.DemiBold
                color: Theme.textPrimary
                elide: Text.ElideRight
            }

            Text {
                width: parent.width
                text: root.description
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textSecondary
                wrapMode: Text.WordWrap
                visible: root.description.length > 0
            }
        }

        Item {
            id: controlSlot
            anchors.verticalCenter: parent.verticalCenter
            width: childrenRect.width > 0 ? childrenRect.width : 160
            height: childrenRect.height > 0 ? childrenRect.height : 32
        }
    }
}
