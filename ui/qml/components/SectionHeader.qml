import QtQuick
import ".."

Item {
    id: root

    property string title: ""
    property string badge: ""
    property bool collapsible: false
    property bool expanded: true
    signal toggleExpand()

    implicitWidth: parent ? parent.width : 500
    implicitHeight: 40

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        spacing: Theme.space8

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.title
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontMd
            font.weight: Font.Bold
            color: Theme.textPrimary
        }

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            visible: root.badge.length > 0
            color: Theme.isDark ? "#2A2A32" : "#E2E2E8"
            radius: Theme.radiusSm
            width: badgeText.implicitWidth + Theme.space12
            height: 20

            Text {
                id: badgeText
                anchors.centerIn: parent
                text: root.badge
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                font.weight: Font.DemiBold
                color: Theme.textSecondary
            }
        }
    }

    Item {
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        visible: root.collapsible
        width: 24
        height: 24

        Text {
            anchors.centerIn: parent
            text: root.expanded ? "▲" : "▼"
            font.pixelSize: 10
            color: Theme.textSecondary
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                root.expanded = !root.expanded
                root.toggleExpand()
            }
        }
    }
}
