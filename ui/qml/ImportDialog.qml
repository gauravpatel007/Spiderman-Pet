import QtQuick
import QtQuick.Dialogs
import "."
import "components"

Item {
    id: root

    property bool isOpen: false
    signal closed()

    anchors.fill: parent
    visible: isOpen

    // Backdrop
    Rectangle {
        anchors.fill: parent
        color: Theme.isDark ? "#CC0A0A0C" : "#80000000"

        MouseArea {
            anchors.fill: parent
            onClicked: root.closeModal()
        }
    }

    // Modal Box
    Rectangle {
        id: dialogBox
        width: Math.min(500, root.width - 48)
        height: Math.min(480, root.height - 60)
        anchors.centerIn: parent
        radius: Theme.radiusMd
        color: Theme.bgCard
        border.color: Theme.borderHover
        border.width: 1

        Column {
            anchors.fill: parent
            anchors.margins: Theme.space24
            spacing: Theme.space16

            // Header
            Row {
                width: parent.width

                Text {
                    width: parent.width - closeBtn.width
                    text: "Import Custom Artwork"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontLg
                    font.bold: true
                    color: Theme.textPrimary
                }

                StyledButton {
                    id: closeBtn
                    text: "✕"
                    variant: "ghost"
                    implicitWidth: 32
                    implicitHeight: 32
                    onClicked: root.closeModal()
                }
            }

            Text {
                width: parent.width
                text: "Select a transparent PNG character image to automatically generate animated action clips."
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.textSecondary
                wrapMode: Text.WordWrap
            }

            // Character Name Field
            Column {
                width: parent.width
                spacing: Theme.space4

                Text {
                    text: "Companion Name:"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.bold: true
                    color: Theme.textPrimary
                }

                Rectangle {
                    width: parent.width
                    height: 36
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: Theme.borderBase
                    border.width: 1

                    TextInput {
                        id: nameInput
                        anchors.fill: parent
                        anchors.margins: Theme.space8
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        color: Theme.textPrimary
                        text: "Custom Hero"
                    }
                }
            }

            // Suit Name Field
            Column {
                width: parent.width
                spacing: Theme.space4

                Text {
                    text: "Suit / Skin Description:"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.bold: true
                    color: Theme.textPrimary
                }

                Rectangle {
                    width: parent.width
                    height: 36
                    radius: Theme.radiusSm
                    color: Theme.bgInput
                    border.color: Theme.borderBase
                    border.width: 1

                    TextInput {
                        id: suitInput
                        anchors.fill: parent
                        anchors.margins: Theme.space8
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBase
                        color: Theme.textPrimary
                        text: "Custom Suit"
                    }
                }
            }

            // Image File Path Field
            Column {
                width: parent.width
                spacing: Theme.space4

                Text {
                    text: "Artwork File Path (.png):"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSm
                    font.bold: true
                    color: Theme.textPrimary
                }

                Row {
                    width: parent.width
                    spacing: Theme.space8

                    Rectangle {
                        width: parent.width - browseBtn.width - Theme.space8
                        height: 36
                        radius: Theme.radiusSm
                        color: Theme.bgInput
                        border.color: Theme.borderBase
                        border.width: 1

                        TextInput {
                            id: pathInput
                            anchors.fill: parent
                            anchors.margins: Theme.space8
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSm
                            color: Theme.textPrimary
                            clip: true
                        }
                    }

                    StyledButton {
                        id: browseBtn
                        text: "Browse..."
                        variant: "secondary"
                        onClicked: fileDialog.open()
                    }
                }
            }

            // Status feedback
            Text {
                id: statusFeedback
                width: parent.width
                text: ""
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSm
                color: Theme.accent
                wrapMode: Text.WordWrap
            }

            Item { width: 1; height: 16 }

            // Action Buttons
            Row {
                anchors.right: parent.right
                spacing: Theme.space8

                StyledButton {
                    text: "Cancel"
                    variant: "ghost"
                    onClicked: root.closeModal()
                }

                StyledButton {
                    text: "Create Companion"
                    variant: "primary"
                    onClicked: {
                        var rawName = nameInput.text.trim()
                        var cid = rawName.toLowerCase().replace(/[^a-z0-9_]/g, "_")
                        if (!cid) cid = "custom_" + Date.now()
                        if (typeof characterModel !== "undefined") {
                            statusFeedback.text = "Processing artwork and generating animations..."
                            characterModel.importCharacter(cid, rawName, suitInput.text.trim(), pathInput.text.trim())
                        }
                    }
                }
            }
        }
    }

    FileDialog {
        id: fileDialog
        title: "Select Companion Artwork PNG"
        nameFilters: ["PNG Images (*.png)", "All Files (*.*)"]
        onAccepted: {
            var selected = fileDialog.selectedFile.toString()
            if (selected.startsWith("file:///")) {
                selected = selected.substring(8)
            }
            pathInput.text = selected
        }
    }

    function openModal() {
        root.isOpen = true
        statusFeedback.text = ""
    }

    function closeModal() {
        root.isOpen = false
        root.closed()
    }
}
