import QtQuick
import ".."

Rectangle {
    id: root

    property bool hoverable: false
    property bool isHovered: hoverable && mouseArea.containsMouse
    property alias mouseArea: mouseArea

    color: isHovered ? Theme.bgCardHover : Theme.bgCard
    radius: Theme.radiusMd
    border.color: isHovered ? Theme.borderHover : Theme.borderBase
    border.width: 1

    Behavior on color { ColorAnimation { duration: Theme.animDuration } }
    Behavior on border.color { ColorAnimation { duration: Theme.animDuration } }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: root.hoverable
        cursorShape: root.hoverable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
}
