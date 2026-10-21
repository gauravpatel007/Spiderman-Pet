import QtQuick
import QtQuick.Controls.Basic

Frame {
    required property QtObject paletteTokens
    padding: 20
    background: Rectangle {
        color: paletteTokens.surface
        border.color: paletteTokens.border
        radius: 16
    }
}
