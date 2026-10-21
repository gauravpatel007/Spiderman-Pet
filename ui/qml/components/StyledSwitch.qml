import QtQuick
import ".."

Item {
    id: root

    property bool checked: false
    property bool enabledState: true
    signal toggled(bool newState)

    implicitWidth: 44
    implicitHeight: 24

    Rectangle {
        id: track
        anchors.fill: parent
        radius: height / 2
        color: {
            if (!root.enabledState) return Theme.isDark ? "#2A2A30" : "#D4D4D8"
            if (root.checked) return Theme.accent
            return Theme.isDark ? "#2E2E38" : "#CBD5E1"
        }
        border.color: root.checked ? "transparent" : Theme.borderBase
        border.width: root.checked ? 0 : 1

        Behavior on color { ColorAnimation { duration: Theme.animDuration } }

        Rectangle {
            id: thumb
            width: parent.height - 4
            height: width
            radius: width / 2
            y: 2
            x: root.checked ? (parent.width - width - 2) : 2
            color: root.enabledState ? "#FFFFFF" : (Theme.isDark ? "#52525B" : "#A1A1AA")

            Behavior on x { NumberAnimation { duration: Theme.animDuration; easing.type: Easing.OutQuad } }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.enabledState
        cursorShape: root.enabledState ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            root.checked = !root.checked
            root.toggled(root.checked)
        }
    }
}
