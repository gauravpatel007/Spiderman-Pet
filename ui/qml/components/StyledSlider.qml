import QtQuick
import ".."

Item {
    id: root

    property real from: 0.0
    property real to: 1.0
    property real stepSize: 0.1
    property real value: 0.5
    property string suffix: ""
    property bool enabledState: true
    signal moved(real newValue)

    implicitWidth: 200
    implicitHeight: 32

    Row {
        anchors.fill: parent
        spacing: Theme.space12

        Item {
            id: trackContainer
            width: parent.width - valueLabel.width - parent.spacing
            height: parent.height

            // Track background
            Rectangle {
                id: trackBg
                anchors.centerIn: parent
                width: parent.width
                height: 4
                radius: 2
                color: Theme.isDark ? "#2E2E38" : "#E2E2E8"

                // Active filled portion
                Rectangle {
                    height: parent.height
                    width: handle.x + handle.width / 2
                    radius: 2
                    color: root.enabledState ? Theme.accent : Theme.textMuted
                }
            }

            // Slider handle
            Rectangle {
                id: handle
                y: (parent.height - height) / 2
                x: {
                    var range = root.to - root.from
                    if (range <= 0) return 0
                    var progress = (root.value - root.from) / range
                    return Math.max(0, Math.min(parent.width - width, progress * (parent.width - width)))
                }
                width: 16
                height: 16
                radius: 8
                color: mouseArea.containsMouse || mouseArea.pressed ? "#FFFFFF" : (Theme.isDark ? "#F4F4F5" : "#FFFFFF")
                border.color: root.enabledState ? Theme.accent : Theme.textMuted
                border.width: 2

                Behavior on scale { NumberAnimation { duration: Theme.animDuration } }
                scale: mouseArea.pressed ? 1.2 : (mouseArea.containsMouse ? 1.1 : 1.0)
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                enabled: root.enabledState
                hoverEnabled: true
                cursorShape: root.enabledState ? Qt.PointingHandCursor : Qt.ArrowCursor

                function updateFromPos(mouseX) {
                    var range = root.to - root.from
                    var usableW = trackContainer.width - handle.width
                    if (usableW <= 0) return
                    var clampedX = Math.max(0, Math.min(usableW, mouseX - handle.width / 2))
                    var rawVal = root.from + (clampedX / usableW) * range
                    if (root.stepSize > 0) {
                        rawVal = Math.round(rawVal / root.stepSize) * root.stepSize
                    }
                    rawVal = Math.max(root.from, Math.min(root.to, rawVal))
                    root.value = rawVal
                    root.moved(rawVal)
                }

                onPressed: function(mouse) { updateFromPos(mouse.x) }
                onPositionChanged: function(mouse) {
                    if (pressed) updateFromPos(mouse.x)
                }
            }
        }

        // Value text
        Text {
            id: valueLabel
            anchors.verticalCenter: parent.verticalCenter
            text: root.stepSize < 0.1 ? root.value.toFixed(2) + root.suffix : root.value.toFixed(1) + root.suffix
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSm
            font.bold: true
            color: Theme.textSecondary
            width: 44
            horizontalAlignment: Text.AlignRight
        }
    }
}
