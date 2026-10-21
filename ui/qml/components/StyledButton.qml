import QtQuick
import ".."

Rectangle {
    id: root

    property string text: ""
    property string variant: "secondary" // primary, secondary, ghost, danger
    property bool enabledState: true
    signal clicked()

    implicitWidth: Math.max(80, label.implicitWidth + Theme.space24)
    implicitHeight: 34
    radius: Theme.radiusSm

    color: {
        if (!enabledState) return Theme.isDark ? "#222226" : "#E2E2E6"
        if (mouseArea.pressed) {
            if (variant === "primary") return Theme.accentHover
            if (variant === "danger") return "#991B1B"
            return Theme.isDark ? "#2E2E36" : "#DADAE0"
        }
        if (mouseArea.containsMouse) {
            if (variant === "primary") return Theme.accentHover
            if (variant === "danger") return "#DC2626"
            return Theme.isDark ? "#282830" : "#E4E4EB"
        }
        if (variant === "primary") return Theme.accent
        if (variant === "danger") return "#B91C1C"
        if (variant === "ghost") return "transparent"
        return Theme.bgCard
    }

    border.color: {
        if (!enabledState) return "transparent"
        if (variant === "primary" || variant === "danger") return "transparent"
        if (mouseArea.containsMouse) return Theme.borderHover
        return Theme.borderBase
    }
    border.width: (variant === "ghost" && !mouseArea.containsMouse) ? 0 : 1

    Behavior on color { ColorAnimation { duration: Theme.animDuration } }
    Behavior on border.color { ColorAnimation { duration: Theme.animDuration } }

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBase
        font.weight: root.variant === "primary" ? Font.DemiBold : Font.Normal
        color: {
            if (!root.enabledState) return Theme.textMuted
            if (root.variant === "primary" || root.variant === "danger") return Theme.accentText
            return Theme.textPrimary
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        enabled: root.enabledState
        hoverEnabled: true
        cursorShape: root.enabledState ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.clicked()
    }
}
