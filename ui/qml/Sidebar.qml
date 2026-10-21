import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root
    objectName: "qmlSidebar"
    property QtObject bridge: (typeof dashboardBridge !== "undefined") ? dashboardBridge : null
    property int currentIndex: root.bridge ? root.bridge.currentRoute : 0
    signal tabSelected(int idx)
    Theme { id: tokens; dark: root.bridge ? root.bridge.darkTheme : true }
    color: tokens.dark ? "#0D0B16" : tokens.surface
    radius: 0
    clip: true

    // Thin crimson separator on right edge
    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: tokens.dark ? Qt.rgba(0.95, 0.13, 0.33, 0.22) : tokens.border
        z: 2
    }

    // Faint spiderweb in bottom-left corner
    Canvas {
        id: spiderweb
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        width: 120; height: 120
        opacity: tokens.dark ? 0.18 : 0.05
        z: 0
        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            ctx.strokeStyle = "#F32155";
            ctx.lineWidth = 1;
            // Draw spiderweb radial lines from corner (0, 120)
            var ox = 0, oy = 120;
            var angles = [0, 15, 30, 45, 60, 75, 90];
            for (var i = 0; i < angles.length; i++) {
                var rad = angles[i] * Math.PI / 180;
                ctx.beginPath();
                ctx.moveTo(ox, oy);
                ctx.lineTo(ox + Math.cos(rad) * 110, oy - Math.sin(rad) * 110);
                ctx.stroke();
            }
            // Draw concentric web rings
            var rings = [25, 45, 65, 85, 105];
            for (var r = 0; r < rings.length; r++) {
                var radius = rings[r];
                ctx.beginPath();
                for (var j = 0; j < angles.length; j++) {
                    var a = angles[j] * Math.PI / 180;
                    var px = ox + Math.cos(a) * radius;
                    var py = oy - Math.sin(a) * radius;
                    if (j === 0) ctx.moveTo(px, py);
                    else ctx.lineTo(px, py);
                }
                ctx.stroke();
            }
        }
    }

    ScrollView {
        id: sidebarScroll
        anchors.fill: parent; anchors.margins: 0
        contentWidth: availableWidth
        z: 1
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical: ScrollBar {
            width: 4
            policy: ScrollBar.AsNeeded
            contentItem: Rectangle { radius: 2; color: tokens.border; opacity: parent.active ? 1 : 0.4 }
            background: Item {}
        }
        ColumnLayout {
            width: sidebarScroll.availableWidth
            spacing: 3

            // ── Top Branding ──
            Item {
                Layout.fillWidth: true; implicitHeight: 74
                Layout.leftMargin: 16; Layout.topMargin: 8
                Rectangle {
                    x: 0; y: 14; width: 38; height: 38; radius: 10
                    gradient: Gradient {
                        orientation: Gradient.Vertical
                        GradientStop { position: 0.0; color: "#F32155" }
                        GradientStop { position: 1.0; color: "#C21846" }
                    }
                    Text {
                        anchors.centerIn: parent
                        text: "S"
                        color: "white"
                        font.pixelSize: 22; font.bold: true; font.family: "Segoe UI"
                    }
                }
                Column {
                    x: 50; y: 16; width: parent.width - 66; spacing: 3
                    Text {
                        width: parent.width
                        text: "SPIDER-BUDDY"
                        color: tokens.text
                        font.pixelSize: 13; font.bold: true; font.letterSpacing: 0.5
                        font.family: "Segoe UI"
                    }
                    Text {
                        width: parent.width
                        text: "Desktop Companion"
                        color: tokens.muted
                        font.pixelSize: 10; font.family: "Segoe UI"
                        elide: Text.ElideRight
                    }
                }
            }

            // ── Navigation Items ──
            Item { Layout.fillWidth: true; implicitHeight: 6 }
            Repeater {
                model: root.bridge ? root.bridge.destinations : []
                NavButton {
                    required property var modelData
                    objectName: "route_" + modelData.index
                    Layout.fillWidth: true
                    Layout.leftMargin: 10; Layout.rightMargin: 10
                    paletteTokens: tokens
                    text: modelData.label; iconIndex: modelData.index
                    selected: root.bridge ? (root.bridge.currentRoute === modelData.index) : (root.currentIndex === modelData.index)
                    onClicked: {
                        if (root.bridge) root.bridge.navigate(modelData.index);
                        root.currentIndex = modelData.index;
                        root.tabSelected(modelData.index);
                    }
                }
            }

            // ── Spacer ──
            Item { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 16 }

            // ── Companion Status Card ──
            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 12; Layout.rightMargin: 12
                implicitHeight: statusCol.implicitHeight + 28
                color: tokens.dark ? "#151729" : tokens.raised
                radius: 14
                border.width: 1
                border.color: tokens.dark ? Qt.rgba(0.95, 0.13, 0.33, 0.18) : tokens.border

                ColumnLayout {
                    id: statusCol
                    anchors.left: parent.left; anchors.right: parent.right
                    anchors.top: parent.top; anchors.margins: 14; spacing: 10

                    // Label
                    Text {
                        text: "YOUR COMPANION"
                        color: tokens.muted; font.pixelSize: 10; font.letterSpacing: 1.5
                        font.family: "Segoe UI"; font.weight: Font.DemiBold
                    }

                    // Avatar + name row
                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        // Mini avatar circle
                        Rectangle {
                            width: 36; height: 36; radius: 18
                            color: tokens.dark ? "#101422" : "#e0e4ed"
                            border.width: 1.5; border.color: tokens.dark ? "#F32155" : tokens.border
                            clip: true
                            Image {
                                anchors.centerIn: parent
                                width: 32; height: 32
                                source: root.bridge ? root.bridge.characterPreview : ""
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                            }
                        }
                        ColumnLayout {
                            spacing: 3
                            Text {
                                text: root.bridge ? root.bridge.characterName : "Tom Holland Spider-Man"
                                color: tokens.text; font.pixelSize: 12; font.bold: true
                                font.family: "Segoe UI"
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                            }
                            RowLayout {
                                spacing: 6
                                Rectangle {
                                    width: 7; height: 7; radius: 3.5
                                    color: root.bridge && root.bridge.running ? "#21D9A0" : "#d9ab64"
                                }
                                Text {
                                    text: root.bridge ? root.bridge.activity : "Idle"
                                    color: tokens.muted; font.pixelSize: 11; font.family: "Segoe UI"
                                }
                            }
                        }
                    }

                    // Pause button
                    Button {
                        objectName: "pauseButton"
                        Layout.fillWidth: true
                        implicitHeight: 34
                        text: root.bridge && root.bridge.running ? "\u23F8  Pause companion" : "\u25B6  Resume companion"
                        font.pixelSize: 11; font.family: "Segoe UI"; font.weight: Font.DemiBold
                        onClicked: if (root.bridge) root.bridge.togglePause()
                        contentItem: Text {
                            text: parent.text; color: tokens.text
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 11; font.family: "Segoe UI"; font.weight: Font.DemiBold
                        }
                        background: Rectangle {
                            color: "transparent"
                            border.color: tokens.dark ? "#2B2E38" : tokens.border
                            border.width: 1; radius: 8
                        }
                    }
                }
            }

            // ── Focus Mode Toggle ──
            Item {
                Layout.fillWidth: true; implicitHeight: 36
                Layout.leftMargin: 16; Layout.rightMargin: 16; Layout.topMargin: 4
                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Focus mode"
                    color: tokens.text; font.pixelSize: 12; font.family: "Segoe UI"
                }
                Switch {
                    id: focusSwitch
                    implicitWidth: 48
                    implicitHeight: 32
                    objectName: "focusSwitch"
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    checked: root.bridge ? root.bridge.focusMode : false
                    onClicked: if (root.bridge) root.bridge.setFocus(checked)
                    indicator: Rectangle {
                        width: 42; height: 22; radius: 11
                        color: focusSwitch.checked ? "#F32155" : (tokens.dark ? "#2B2E38" : "#ccc")
                        border.color: focusSwitch.checked ? "#C21846" : (tokens.dark ? "#3A3E4A" : "#bbb")
                        Behavior on color { ColorAnimation { duration: 150 } }
                        Rectangle {
                            x: focusSwitch.checked ? parent.width - width - 3 : 3
                            anchors.verticalCenter: parent.verticalCenter
                            width: 16; height: 16; radius: 8
                            color: "white"
                            Behavior on x { NumberAnimation { duration: 150 } }
                        }
                    }
                    contentItem: Item {}
                }
            }

            // ── Battery Info ──
            RowLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.leftMargin: 16; Layout.rightMargin: 16
                spacing: 6
                Text {
                    text: "\uD83D\uDD0B"
                    font.pixelSize: 13
                }
                Text {
                    text: root.bridge ? root.bridge.battery : "65% · On battery"
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    elide: Text.ElideRight
                    color: tokens.muted; font.pixelSize: 12; font.family: "Segoe UI"
                }
            }

            // ── Theme Switch ──
            Button {
                objectName: "themeButton"
                Layout.fillWidth: true
                Layout.leftMargin: 14; Layout.rightMargin: 14; Layout.bottomMargin: 14
                implicitHeight: 30
                text: tokens.dark ? "\u263C  Switch to light theme" : "\u263E  Switch to dark theme"
                onClicked: if (root.bridge) root.bridge.setTheme(tokens.dark ? "light" : "dark")
                contentItem: Text {
                    text: parent.text
                    color: tokens.muted; font.pixelSize: 11; font.family: "Segoe UI"
                    horizontalAlignment: Text.AlignLeft
                }
                background: Rectangle {
                    color: parent.hovered ? (tokens.dark ? Qt.rgba(1,1,1,0.04) : tokens.raised) : "transparent"
                    radius: 6
                }
            }
        }
    }
}
