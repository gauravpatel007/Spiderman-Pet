import QtQuick
import QtQuick.Controls.Basic

Button {
    id: control
    required property QtObject paletteTokens
    property bool selected: false
    property int iconIndex: 0
    implicitHeight: 46
    hoverEnabled: true
    activeFocusOnTab: true
    Accessible.name: text
    Accessible.role: Accessible.Button

    // Subtle crimson glow behind selected button
    Rectangle {
        anchors.fill: parent
        anchors.margins: -2
        radius: 12
        color: "#F32155"
        opacity: control.selected ? 0.35 : 0
        visible: control.selected
        z: -1
    }

    background: Rectangle {
        radius: 10
        gradient: control.selected ? activeGradient : null
        color: control.selected ? "#F32155" :
               control.hovered ? Qt.rgba(1, 1, 1, 0.06) : "transparent"
        border.width: control.activeFocus ? 2 : (control.selected ? 1 : 0)
        border.color: control.selected ? Qt.rgba(1, 1, 1, 0.25) : "#e96780"
        Behavior on color { ColorAnimation { duration: 110 } }

        Gradient {
            id: activeGradient
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#F32155" }
            GradientStop { position: 1.0; color: "#C21846" }
        }
    }

    contentItem: Item {
        Canvas {
            id: icon
            x: 12; anchors.verticalCenter: parent.verticalCenter
            width: 20; height: 20
            property color strokeColor: control.selected ? "#FFFFFF" : control.paletteTokens.muted
            onStrokeColorChanged: requestPaint()
            onPaint: {
                var c = getContext("2d"); c.reset(); c.strokeStyle = strokeColor;
                c.lineWidth = 1.6; c.lineCap = "round"; c.lineJoin = "round";
                c.beginPath();
                switch (control.iconIndex) {
                case 0: c.moveTo(2,9);c.lineTo(10,2);c.lineTo(18,9);c.moveTo(4,8);c.lineTo(4,18);c.lineTo(16,18);c.lineTo(16,8);break;
                case 1: c.arc(10,6,3.5,0,Math.PI*2);c.moveTo(3,18);c.bezierCurveTo(3,10,17,10,17,18);break;
                case 2: c.moveTo(3,11);c.lineTo(7,11);c.lineTo(10,3);c.lineTo(13,17);c.lineTo(16,9);c.lineTo(19,9);break;
                case 3: c.rect(2,3,16,11);c.moveTo(10,14);c.lineTo(10,18);c.moveTo(6,18);c.lineTo(14,18);break;
                case 4: c.arc(10,10,7.5,0,Math.PI*2);c.moveTo(10,5);c.lineTo(10,10);c.lineTo(14,12);break;
                case 5: c.rect(2,5,16,11);c.moveTo(5,9);c.lineTo(7,9);c.moveTo(10,9);c.lineTo(12,9);c.moveTo(15,9);c.lineTo(16,9);c.moveTo(6,13);c.lineTo(14,13);break;
                default: c.moveTo(3,5);c.lineTo(17,5);c.moveTo(3,10);c.lineTo(17,10);c.moveTo(3,15);c.lineTo(17,15);c.moveTo(7,3);c.lineTo(7,7);c.moveTo(13,8);c.lineTo(13,12);c.moveTo(8,13);c.lineTo(8,17);
                }
                c.stroke();
            }
        }
        Text {
            anchors.left: parent.left; anchors.leftMargin: 42
            anchors.right: parent.right; anchors.rightMargin: 7
            anchors.verticalCenter: parent.verticalCenter
            text: control.text
            color: control.selected ? "#FFFFFF" : control.paletteTokens.text
            font.family: "Segoe UI"; font.pixelSize: 13
            font.weight: control.selected ? Font.DemiBold : Font.Normal
            wrapMode: Text.NoWrap
            elide: Text.ElideRight
        }
    }
}
