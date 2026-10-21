import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ScrollView {
    id: page
    objectName: "qmlCharactersPage"
    property QtObject bridge: dashboardBridge
    property string revealedSetting: ""
    Theme { id: colors; dark: page.bridge ? page.bridge.darkTheme : true }
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical: ScrollBar { width: 6; policy: ScrollBar.AsNeeded; contentItem: Rectangle { radius: 3; color: colors.border } background: Item {} }
    background: Rectangle { color: colors.bg }

    Rectangle {
        anchors.fill: parent
        color: colors.bg
        z: -1
    }

    Connections {
        target: page.bridge
        function onRevealRequested(key) {
            page.revealedSetting = key;
            if (key === "general.scale" || key === "general.opacity") {
                page.contentItem.contentY = Math.min(appearance.y, Math.max(0, page.contentHeight-page.availableHeight));
                if (key === "general.scale") sizeSlider.forceActiveFocus(); else opacitySlider.forceActiveFocus();
            }
        }
    }
    ColumnLayout {
        width: page.availableWidth; spacing: 18
        SelectableText { Layout.fillWidth: true; text: "Choose your companion"; color: colors.text; font.pixelSize: page.width < 600 ? 23 : 28; font.bold: true }
        SelectableText { Layout.fillWidth: true; text: "One active companion. A personality of their own."; color: colors.muted; font.pixelSize: 13 }
        GridLayout {
            id: gallery
            objectName: "characterGallery"
            Layout.fillWidth: true; columns: Math.min(3, Math.max(1, Math.floor((page.availableWidth+16)/220)))
            columnSpacing: 16; rowSpacing: 16
            Repeater {
                model: page.bridge ? page.bridge.characters : []
                Panel {
                    required property var modelData
                    objectName: "character_" + modelData.id
                    Layout.fillWidth: true; Layout.preferredWidth: (page.availableWidth - (gallery.columns-1)*16)/gallery.columns
                    Layout.preferredHeight: 310; paletteTokens: colors; padding: 14
                    background: Rectangle { color: colors.surface; border.color: modelData.selected ? colors.accent : colors.border; border.width: modelData.selected ? 2 : 1; radius: 16 }
                    ColumnLayout {
                        anchors.fill: parent; spacing: 8
                        Image { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 100; source: modelData.preview; fillMode: Image.PreserveAspectFit; asynchronous: true }
                        SelectableText { Layout.fillWidth: true; text: modelData.name; color: colors.text; font.pixelSize: 15; font.bold: true; horizontalAlignment: Text.AlignHCenter }
                        SelectableText { Layout.fillWidth: true; Layout.preferredHeight: 36; text: modelData.suit; color: colors.muted; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; clip: true }
                        ActionButton { objectName: "select_" + modelData.id; Layout.fillWidth: true; paletteTokens: colors; primary: modelData.selected; text: modelData.selected ? "Selected" : "Select"; onClicked: if(page.bridge) page.bridge.selectCharacter(modelData.id) }
                    }
                }
            }
            Panel {
                Layout.fillWidth: true; Layout.preferredWidth: (page.availableWidth - (gallery.columns-1)*16)/gallery.columns
                Layout.preferredHeight: 310; paletteTokens: colors
                ColumnLayout {
                    anchors.fill: parent; spacing: 12
                    Item { Layout.fillHeight: true }
                    Text { Layout.alignment: Qt.AlignHCenter; text: "+"; color: colors.accent; font.pixelSize: 52; font.weight: Font.Light }
                    SelectableText { Layout.fillWidth: true; text: "Make it yours"; color: colors.text; font.pixelSize: 16; font.bold: true; horizontalAlignment: Text.AlignHCenter }
                    SelectableText { Layout.fillWidth: true; text: "Import your artwork and choose an animation template."; color: colors.muted; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                    Item { Layout.fillHeight: true }
                    ActionButton { objectName: "importCharacter"; Layout.fillWidth: true; paletteTokens: colors; text: "Add character"; onClicked: if(page.bridge) page.bridge.importCharacter() }
                }
            }
        }
        Panel {
            id: appearance
            objectName: "characterAppearance"
            Layout.fillWidth: true; paletteTokens: colors
            ColumnLayout {
                width: parent.width; spacing: 14
                SelectableText { text: "Character appearance"; color: colors.text; font.pixelSize: 17; font.bold: true }
                SelectableText { Layout.fillWidth: true; text: page.bridge ? page.bridge.personalityDescription : ""; color: colors.muted; font.pixelSize: 12 }
                SelectableText { text: "Size  ·  " + Math.round(sizeSlider.value) + " px"; color: colors.text; font.pixelSize: 12 }
                Slider {
                    id: sizeSlider; objectName: "characterSize"; Layout.fillWidth: true
                    from: 100; to: 400; stepSize: 1
                    value: page.bridge ? page.bridge.settingsValues.general.scale*200 : 200
                    onMoved: if(page.bridge) page.bridge.setCharacterSize(value)
                    Accessible.name: "Character size"; palette.highlight: colors.accent
                }
                SelectableText { text: "Opacity  ·  " + Math.round(opacitySlider.value) + "%"; color: colors.text; font.pixelSize: 12 }
                Slider {
                    id: opacitySlider; objectName: "characterOpacity"; Layout.fillWidth: true
                    from: 50; to: 100; stepSize: 1
                    value: page.bridge ? page.bridge.settingsValues.general.opacity*100 : 100
                    onMoved: if(page.bridge) page.bridge.setCharacterOpacity(value)
                    Accessible.name: "Character opacity"; palette.highlight: colors.accent
                }
                SelectableText { Layout.fillWidth: true; text: "Size and opacity apply to your active companion. Set allowed activities in Activities."; color: colors.muted; font.pixelSize: 11 }
            }
        }
        Item { implicitHeight: 16 }
    }
}
