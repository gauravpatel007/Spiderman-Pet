import QtQuick
import QtQuick.Controls.Basic

Button {
    id: control
    required property QtObject paletteTokens
    property bool primary: false
    implicitHeight: 38
    implicitWidth: Math.max(105, label.implicitWidth + 28)
    hoverEnabled: true
    activeFocusOnTab: true
    Accessible.name: text
    contentItem: Text {
        id: label
        text: control.text; color: !control.enabled ? control.paletteTokens.muted : control.primary ? "white" : control.paletteTokens.text
        font.family: "Segoe UI"; font.pixelSize: 12; font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 8
        color: control.primary ? control.paletteTokens.accent : control.hovered ? control.paletteTokens.raised : control.paletteTokens.surface
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? "#e96780" : control.primary ? control.paletteTokens.accent : control.paletteTokens.border
        opacity: control.enabled ? 1 : 0.6
    }
}
