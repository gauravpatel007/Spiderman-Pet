import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ScrollView {
    id: page
    objectName: "qmlHomePage"
    property QtObject bridge: dashboardBridge
    Theme { id: colors; dark: page.bridge ? page.bridge.darkTheme : true }
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical: ScrollBar {
        width: 5; policy: ScrollBar.AsNeeded
        contentItem: Rectangle { radius: 2; color: colors.border; opacity: 0.5 }
        background: Item {}
    }
    background: Rectangle { color: colors.bg }

    // Solid dark base
    Rectangle {
        anchors.fill: parent
        color: colors.bg
        z: -3
    }

    // Cinematic city background with crimson webs
    Image {
        anchors.fill: parent
        source: page.bridge ? page.bridge.bgImagePath : ""
        fillMode: Image.PreserveAspectCrop
        opacity: colors.dark ? 0.35 : 0.08
        z: -2
        smooth: true
    }

    // Subtle dark gradient overlay
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0.03, 0.04, 0.08, 0.40) }
            GradientStop { position: 1.0; color: Qt.rgba(0.03, 0.04, 0.08, 0.80) }
        }
        z: -1
    }

    function actionAllowed(name) {
        if (!page.bridge) return false;
        var entries = page.bridge.activities;
        for (var i = 0; i < entries.length; i++) {
            if (entries[i].id === name) return entries[i].enabled && entries[i].available;
        }
        return false;
    }

    Connections {
        target: page.bridge
        function onRevealRequested(key) {
            if (!page.bridge || page.bridge.currentRoute !== 0) return;
            var name = key.toLowerCase();
            var targetY = name.indexOf("focus") >= 0 || name.indexOf("break") >= 0 || name.indexOf("reset") >= 0 || name.indexOf("swing") >= 0 || name.indexOf("perch") >= 0 || name.indexOf("nap") >= 0 || name.indexOf("celebrat") >= 0 ? row1Layout.y : 0;
            page.contentItem.contentY = Math.min(targetY, Math.max(0, page.contentHeight - page.availableHeight));
        }
    }

    ColumnLayout {
        width: page.availableWidth
        spacing: 11

        // ═══════════════════════════════════════════
        //  PAGE HEADING
        // ═══════════════════════════════════════════
        Item {
            Layout.fillWidth: true
            Layout.topMargin: 2
            Layout.leftMargin: 20; Layout.rightMargin: 20
            implicitHeight: 60

            ColumnLayout {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                RowLayout {
                    spacing: 8
                    SelectableText {
                        text: "Your desktop."
                        color: "#F8FAFC"
                        font.pixelSize: 26; font.bold: true; font.family: "Segoe UI"
                    }
                    SelectableText {
                        text: "A little more alive."
                        color: "#F32155"
                        font.pixelSize: 26; font.bold: true; font.family: "Segoe UI"
                    }
                }
                SelectableText {
                    text: "Your companion, at a glance."
                    color: colors.muted
                    font.pixelSize: 13; font.family: "Segoe UI"
                }
            }

            // Decorative script "Small moments, Big vibes 👑" (top-right)
            Column {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 12
                spacing: -2
                opacity: 0.85
                Text {
                    anchors.right: parent.right
                    text: "Small"
                    color: "#F32155"; font.pixelSize: 13
                    font.italic: true; font.family: "Segoe UI"
                    rotation: -6
                }
                Text {
                    anchors.right: parent.right
                    text: "moments"
                    color: "#F32155"; font.pixelSize: 12
                    font.italic: true; font.family: "Segoe UI"
                    rotation: -4
                }
                Text {
                    anchors.right: parent.right
                    text: "Big vibes \uD83D\uDC51"
                    color: "#F32155"; font.pixelSize: 16
                    font.italic: true; font.bold: true; font.family: "Segoe UI"
                    rotation: -2
                }
            }
        }

        // ═══════════════════════════════════════════
        //  ROW 1: Companion (Hero) | Pomodoro | Quick Actions
        // ═══════════════════════════════════════════
        RowLayout {
            id: row1Layout
            Layout.fillWidth: true
            Layout.leftMargin: 20; Layout.rightMargin: 20
            spacing: 12

            // ── CARD 1: YOUR COMPANION (Hero) ──
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredWidth: 620
                Layout.minimumWidth: 440
                implicitHeight: 326
                radius: 14
                color: colors.dark ? "#101422" : colors.surface
                border.width: 1
                border.color: colors.dark ? Qt.rgba(0.95, 0.13, 0.33, 0.20) : colors.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    // Card Header
                    RowLayout {
                        spacing: 7
                        Text { text: "\u265B"; color: "#F32155"; font.pixelSize: 13 }
                        Text {
                            text: "YOUR COMPANION"
                            color: colors.muted; font.pixelSize: 10
                            font.letterSpacing: 2; font.weight: Font.DemiBold
                            font.family: "Segoe UI"
                        }
                    }

                    // Content: Info (Left) + Mascot Stage (Right)
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 12

                        // Left Column: Quote + Details + Pause/Hide
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 8

                            // Speech Bubble
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: quoteContent.implicitHeight + 14
                                radius: 10
                                color: colors.dark ? "#151729" : colors.raised
                                border.width: 1
                                border.color: colors.dark ? "#1E2235" : colors.border

                                RowLayout {
                                    id: quoteContent
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 7

                                    Text {
                                        text: "\u201C"
                                        color: "#F32155"
                                        font.pixelSize: 20; font.bold: true
                                        Layout.alignment: Qt.AlignTop
                                    }
                                    SelectableText {
                                        Layout.fillWidth: true
                                        text: page.bridge && page.bridge.homeData.quote ? page.bridge.homeData.quote : "With great power comes great... need to commit to Git."
                                        color: colors.muted; font.pixelSize: 12
                                        font.italic: true; font.family: "Segoe UI"
                                        wrapMode: TextEdit.WordWrap
                                    }
                                    Button {
                                        implicitWidth: 22; implicitHeight: 22
                                        Layout.alignment: Qt.AlignTop
                                        onClicked: if (page.bridge) page.bridge.homeAction("quote")
                                        contentItem: Text {
                                            text: "\u21BB"; color: colors.muted
                                            font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                        background: Rectangle { color: "transparent" }
                                    }
                                }
                            }

                            // Metadata
                            ColumnLayout {
                                spacing: 4
                                RowLayout {
                                    spacing: 7
                                    Text { text: "\uD83D\uDC64"; font.pixelSize: 12 }
                                    SelectableText {
                                        text: page.bridge ? page.bridge.characterName : "Tom Holland Spider-Man"
                                        color: colors.text; font.pixelSize: 14; font.bold: true
                                        font.family: "Segoe UI"
                                    }
                                }
                                RowLayout {
                                    spacing: 7
                                    Rectangle { width: 7; height: 7; radius: 3.5; color: "#21D9A0" }
                                    SelectableText {
                                        text: "Status: " + (page.bridge ? page.bridge.activity : "Idle")
                                        color: colors.muted; font.pixelSize: 12; font.family: "Segoe UI"
                                    }
                                }
                                RowLayout {
                                    spacing: 7
                                    Text { text: "\u25A3"; color: colors.muted; font.pixelSize: 11 }
                                    SelectableText {
                                        text: "Target: Desktop (This Window)"
                                        color: colors.muted; font.pixelSize: 12; font.family: "Segoe UI"
                                    }
                                }
                            }

                            Item { Layout.fillHeight: true }

                            // Action Buttons
                            RowLayout {
                                spacing: 8
                                Button {
                                    objectName: "homePause"
                                    implicitWidth: 100; implicitHeight: 32
                                    text: page.bridge && page.bridge.running ? "\u23F8  Pause" : "\u25B6  Resume"
                                    onClicked: if (page.bridge) page.bridge.togglePause()
                                    contentItem: Text {
                                        text: parent.text; color: "white"
                                        font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    background: Rectangle {
                                        radius: 8
                                        gradient: Gradient {
                                            orientation: Gradient.Horizontal
                                            GradientStop { position: 0.0; color: "#F32155" }
                                            GradientStop { position: 1.0; color: "#C21846" }
                                        }
                                    }
                                }
                                Button {
                                    objectName: "homeVisibility"
                                    implicitWidth: 90; implicitHeight: 32
                                    text: page.bridge && page.bridge.hidden ? "\uD83D\uDC41  Show" : "\uD83D\uDC41  Hide"
                                    onClicked: if (page.bridge) page.bridge.setHidden(!page.bridge.hidden)
                                    contentItem: Text {
                                        text: parent.text; color: colors.text
                                        font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    background: Rectangle {
                                        radius: 8; color: colors.dark ? "#151729" : colors.raised
                                        border.width: 1; border.color: colors.dark ? "#2B2E38" : colors.border
                                    }
                                }
                            }
                        }

                        // Right Column: Mascot Stage
                        Item {
                            Layout.preferredWidth: 210
                            Layout.fillHeight: true

                            // Glowing platform rings
                            Canvas {
                                id: stagePedestal
                                anchors.fill: parent
                                onPaint: {
                                    var ctx = getContext("2d");
                                    ctx.reset();
                                    var cx = width / 2;
                                    var cy = height * 0.52;

                                    // Ambient background spotlight glow
                                    var radGlow = ctx.createRadialGradient(cx, cy - 15, 10, cx, cy - 15, 85);
                                    radGlow.addColorStop(0, Qt.rgba(0.95, 0.13, 0.33, 0.22));
                                    radGlow.addColorStop(0.6, Qt.rgba(0.95, 0.13, 0.33, 0.06));
                                    radGlow.addColorStop(1, "transparent");
                                    ctx.fillStyle = radGlow;
                                    ctx.beginPath();
                                    ctx.arc(cx, cy - 15, 85, 0, Math.PI * 2);
                                    ctx.fill();

                                    // Outer neon circular ring
                                    ctx.beginPath();
                                    ctx.ellipse(cx - 68, cy + 44, 136, 32);
                                    ctx.lineWidth = 2;
                                    ctx.strokeStyle = "#F32155";
                                    ctx.stroke();

                                    // Inner neon ring
                                    ctx.beginPath();
                                    ctx.ellipse(cx - 50, cy + 46, 100, 24);
                                    ctx.lineWidth = 1;
                                    ctx.strokeStyle = Qt.rgba(0.95, 0.13, 0.33, 0.4);
                                    ctx.stroke();
                                }
                            }

                            // Live mascot frame
                            Image {
                                objectName: "livePreview"
                                anchors.centerIn: parent
                                anchors.verticalCenterOffset: -12
                                width: 160; height: 185
                                source: (page.bridge && page.bridge.frameRevision > 0) ? ("image://companion/frame/" + page.bridge.frameRevision) : (page.bridge ? page.bridge.characterPreview : "")
                                cache: false; asynchronous: false
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                            }
                        }
                    }

                    // Mood Presets Row
                    RowLayout {
                        Layout.fillWidth: true
                        Item { Layout.fillWidth: true }
                        RowLayout {
                            spacing: 7
                            Text {
                                text: "\uD83C\uDFAD Mood Presets"
                                color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                            }
                            Repeater {
                                model: [
                                    { label: "Chill", id: "chill", icon: "\uD83E\uDDD8" },
                                    { label: "Hyper", id: "hyper", icon: "\u26A1" },
                                    { label: "Camo", id: "camo", icon: "\uD83D\uDC7B" }
                                ]
                                Button {
                                    required property var modelData
                                    implicitWidth: 72; implicitHeight: 28
                                    property bool isActive: (page.bridge && page.bridge.homeData.mood) ? (page.bridge.homeData.mood === modelData.id) : (modelData.id === "chill")
                                    text: modelData.icon + " " + modelData.label
                                    onClicked: if (page.bridge) page.bridge.homeAction(modelData.id)
                                    contentItem: Text {
                                        text: parent.text; color: parent.isActive ? "#F8FAFC" : colors.muted
                                        font.pixelSize: 10; font.family: "Segoe UI"; font.weight: Font.DemiBold
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    background: Rectangle {
                                        radius: 7
                                        color: parent.isActive ? Qt.rgba(0.95, 0.13, 0.33, 0.28) : (colors.dark ? "#151729" : colors.raised)
                                        border.width: 1
                                        border.color: parent.isActive ? "#F32155" : (colors.dark ? "#1E2235" : colors.border)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ── CARD 2: WORK WITH YOUR COMPANION (Pomodoro) ──
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredWidth: 380
                Layout.minimumWidth: 290
                implicitHeight: 326
                radius: 14
                color: colors.dark ? "#101422" : colors.surface
                border.width: 1
                border.color: colors.dark ? "#1E2235" : colors.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    // Header
                    RowLayout {
                        Layout.fillWidth: true; spacing: 8
                        Text { text: "\u23F1"; color: "#F32155"; font.pixelSize: 13 }
                        Text {
                            text: "Work with your companion"
                            color: colors.text; font.pixelSize: 14; font.bold: true
                            font.family: "Segoe UI"
                        }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            width: 58; height: 20; radius: 10
                            color: Qt.rgba(0.13, 0.85, 0.63, 0.15)
                            border.width: 1; border.color: Qt.rgba(0.13, 0.85, 0.63, 0.3)
                            RowLayout {
                                anchors.centerIn: parent; spacing: 4
                                Rectangle { width: 5; height: 5; radius: 2.5; color: "#21D9A0" }
                                Text { text: "Focus"; color: "#21D9A0"; font.pixelSize: 10; font.bold: true; font.family: "Segoe UI" }
                            }
                        }
                    }

                    // Countdown Ring
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 142
                        Layout.alignment: Qt.AlignHCenter

                        Canvas {
                            id: timerCanvas
                            anchors.centerIn: parent
                            width: 136; height: 136
                            property real progress: {
                                var t = (page.bridge && page.bridge.homeData.timer) ? page.bridge.homeData.timer : "25:00";
                                var parts = t.split(":");
                                if (parts.length === 2) {
                                    var mins = parseInt(parts[0]) || 0;
                                    var secs = parseInt(parts[1]) || 0;
                                    return (mins * 60 + secs) / 1500.0;
                                }
                                return 1.0;
                            }
                            onProgressChanged: requestPaint()

                            onPaint: {
                                var ctx = getContext("2d");
                                ctx.reset();
                                var cx = width / 2, cy = height / 2, r = 58;

                                // Background track
                                ctx.beginPath();
                                ctx.arc(cx, cy, r, 0, Math.PI * 2);
                                ctx.lineWidth = 6;
                                ctx.strokeStyle = colors.dark ? "#1B1E2D" : "#e0e4ed";
                                ctx.stroke();

                                // Progress arc
                                if (progress > 0) {
                                    ctx.beginPath();
                                    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.min(1.0, progress));
                                    ctx.lineWidth = 6;
                                    ctx.lineCap = "round";
                                    ctx.strokeStyle = "#F32155";
                                    ctx.stroke();
                                }

                                // Outer glow
                                ctx.beginPath();
                                ctx.arc(cx, cy, r + 8, 0, Math.PI * 2);
                                ctx.lineWidth = 1;
                                ctx.strokeStyle = Qt.rgba(0.95, 0.13, 0.33, 0.20);
                                ctx.stroke();
                            }
                        }

                        Column {
                            anchors.centerIn: timerCanvas; spacing: 2
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: (page.bridge && page.bridge.homeData.timer) ? page.bridge.homeData.timer : "25:00"
                                color: colors.text; font.pixelSize: 28; font.bold: true
                                font.family: "Segoe UI"
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "Focus Time"
                                color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                            }
                        }
                    }

                    // Ready Status Pill
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 32; radius: 8
                        color: colors.dark ? "#151729" : colors.raised
                        border.width: 1; border.color: colors.dark ? "#1E2235" : colors.border

                        RowLayout {
                            anchors.centerIn: parent; spacing: 6
                            Rectangle { width: 6; height: 6; radius: 3; color: "#21D9A0" }
                            Text {
                                text: "Ready"
                                color: "#21D9A0"; font.pixelSize: 12; font.bold: true; font.family: "Segoe UI"
                            }
                            Text {
                                text: "·  Stay focused. We got this!"
                                color: colors.muted; font.pixelSize: 11; font.family: "Segoe UI"
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Action Buttons
                    RowLayout {
                        Layout.fillWidth: true; spacing: 6
                        Button {
                            objectName: "focus25"
                            Layout.fillWidth: true; implicitHeight: 32
                            onClicked: if (page.bridge) page.bridge.homeAction("focus25")
                            contentItem: RowLayout {
                                spacing: 5; anchors.centerIn: parent
                                Text { text: "\u25B6"; color: "white"; font.pixelSize: 10 }
                                Text { text: "25m Focus"; color: "white"; font.pixelSize: 11; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                            }
                            background: Rectangle {
                                radius: 8
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0.0; color: "#F32155" }
                                    GradientStop { position: 1.0; color: "#C21846" }
                                }
                            }
                        }
                        Button {
                            Layout.fillWidth: true; implicitHeight: 32
                            onClicked: if (page.bridge) page.bridge.homeAction("break5")
                            contentItem: RowLayout {
                                spacing: 4; anchors.centerIn: parent
                                Text { text: "\u2615"; font.pixelSize: 10; color: colors.text }
                                Text { text: "5m Break"; color: colors.text; font.pixelSize: 11; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                            }
                            background: Rectangle {
                                radius: 8; color: colors.dark ? "#151729" : colors.raised
                                border.width: 1; border.color: colors.dark ? "#2B2E38" : colors.border
                            }
                        }
                        Button {
                            Layout.fillWidth: true; implicitHeight: 32
                            onClicked: if (page.bridge) page.bridge.homeAction("resetTimer")
                            contentItem: RowLayout {
                                spacing: 4; anchors.centerIn: parent
                                Text { text: "\u21BB"; font.pixelSize: 11; color: colors.text }
                                Text { text: "Reset"; color: colors.text; font.pixelSize: 11; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                            }
                            background: Rectangle {
                                radius: 8; color: colors.dark ? "#151729" : colors.raised
                                border.width: 1; border.color: colors.dark ? "#2B2E38" : colors.border
                            }
                        }
                    }
                }
            }

            // ── CARD 3: A LITTLE ACTION (2x2 Grid) ──
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredWidth: 340
                Layout.minimumWidth: 260
                implicitHeight: 326
                radius: 14
                color: colors.dark ? "#101422" : colors.surface
                border.width: 1
                border.color: colors.dark ? "#1E2235" : colors.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    RowLayout {
                        spacing: 8
                        Text { text: "\u26A1"; color: "#F32155"; font.pixelSize: 13 }
                        Text {
                            text: "A little action"
                            color: colors.text; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"
                        }
                    }
                    Text {
                        text: "Quick triggers for some fun!"
                        color: colors.muted; font.pixelSize: 12; font.family: "Segoe UI"
                    }

                    Item { Layout.fillHeight: true }

                    // 2x2 Grid of Actions
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2; columnSpacing: 8; rowSpacing: 8

                        Repeater {
                            model: [
                                { name: "Web swing", id: "swing", icon: "\uD83D\uDD78" },
                                { name: "Celebrate / Flip", id: "celebrate", icon: "\uD83E\uDD38" },
                                { name: "Window perch", id: "title_perch", icon: "\u229E" },
                                { name: "Power nap", id: "sleep", icon: "zZ\u00B2" }
                            ]
                            Button {
                                required property var modelData
                                Layout.fillWidth: true
                                implicitHeight: 82
                                enabled: page.actionAllowed(modelData.id)
                                onClicked: if (page.bridge) page.bridge.homeAction(modelData.id)

                                contentItem: Item {
                                    anchors.fill: parent
                                    ColumnLayout {
                                        anchors.centerIn: parent
                                        spacing: 4
                                        Text {
                                            Layout.alignment: Qt.AlignHCenter
                                            text: modelData.icon
                                            color: enabled ? "#F32155" : colors.muted
                                            font.pixelSize: 22
                                        }
                                        Text {
                                            Layout.alignment: Qt.AlignHCenter
                                            text: modelData.name
                                            color: enabled ? colors.text : colors.muted
                                            font.pixelSize: 11; font.weight: Font.DemiBold; font.family: "Segoe UI"
                                        }
                                    }
                                    Text {
                                        anchors.right: parent.right; anchors.rightMargin: 7
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "\u203A"; color: colors.muted; font.pixelSize: 15
                                    }
                                }

                                background: Rectangle {
                                    radius: 10
                                    color: parent.hovered ? (colors.dark ? "#1A1D33" : colors.raised) : (colors.dark ? "#151729" : colors.surface)
                                    border.width: 1
                                    border.color: parent.hovered ? "#F32155" : (colors.dark ? "#1E2235" : colors.border)
                                    opacity: enabled ? 1 : 0.4
                                    Behavior on color { ColorAnimation { duration: 120 } }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ═══════════════════════════════════════════
        //  ROW 2: System Status | Today with companion
        // ═══════════════════════════════════════════
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20; Layout.rightMargin: 20
            spacing: 12

            // ── CARD 4: SYSTEM STATUS ──
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredWidth: 700
                implicitHeight: 188
                radius: 14
                color: colors.dark ? "#101422" : colors.surface
                border.width: 1; border.color: colors.dark ? "#1E2235" : colors.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    // Header
                    RowLayout {
                        Layout.fillWidth: true; spacing: 8
                        Text { text: "\u2726"; color: "#F32155"; font.pixelSize: 13 }
                        Text {
                            text: "System status"
                            color: colors.text; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"
                        }
                        Item { Layout.fillWidth: true }
                        RowLayout {
                            spacing: 5
                            Rectangle { width: 6; height: 6; radius: 3; color: "#22D3EE" }
                            Text {
                                text: "Spidey-Sense: Quiet (Systems Cool)"
                                color: "#22D3EE"; font.pixelSize: 11; font.family: "Segoe UI"
                            }
                        }
                    }

                    // 3 Sections: Battery | Hardware Load | Spidey-Sense
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 14

                        // Section 1: Battery
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 6
                            RowLayout {
                                spacing: 5
                                Text { text: "\uD83D\uDD0B"; font.pixelSize: 12 }
                                Text { text: "Battery"; color: colors.text; font.pixelSize: 12; font.bold: true; font.family: "Segoe UI" }
                            }
                            Text {
                                text: "65% · On battery"
                                color: colors.muted; font.pixelSize: 11; font.family: "Segoe UI"
                            }
                            // Progress bar
                            Rectangle {
                                Layout.fillWidth: true; height: 5; radius: 2.5
                                color: colors.dark ? "#1E2235" : "#e0e4ed"
                                Rectangle {
                                    width: parent.width * 0.65; height: parent.height; radius: 2.5
                                    color: "#22D3EE"
                                }
                            }
                            Item { implicitHeight: 2 }
                            Text { text: "Suit Lore"; color: colors.text; font.pixelSize: 10; font.bold: true; font.family: "Segoe UI" }
                            Text {
                                text: "\u26A1 Stark Suit · Systems Operational"
                                color: "#21D9A0"; font.pixelSize: 10; font.family: "Segoe UI"
                            }
                        }

                        // Divider
                        Rectangle { width: 1; Layout.fillHeight: true; color: colors.dark ? "#1E2235" : colors.border }

                        // Section 2: Hardware Load
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 6
                            Text {
                                text: "Hardware Load"
                                color: colors.muted; font.pixelSize: 11; font.family: "Segoe UI"
                            }
                            RowLayout {
                                Layout.fillWidth: true; spacing: 14
                                Layout.alignment: Qt.AlignHCenter

                                // CPU Gauge (32%)
                                ColumnLayout {
                                    spacing: 3
                                    Canvas {
                                        width: 52; height: 52
                                        onPaint: {
                                            var ctx = getContext("2d");
                                            ctx.reset();
                                            var cx = 26, cy = 26, r = 21;
                                            ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
                                            ctx.lineWidth = 4.5; ctx.strokeStyle = colors.dark ? "#1E2235" : "#e0e4ed";
                                            ctx.stroke();
                                            ctx.beginPath();
                                            ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * 0.32);
                                            ctx.lineWidth = 4.5; ctx.lineCap = "round";
                                            ctx.strokeStyle = "#8B5CF6";
                                            ctx.stroke();
                                        }
                                        Text {
                                            anchors.centerIn: parent
                                            text: "32%"
                                            color: colors.text; font.pixelSize: 12; font.bold: true; font.family: "Segoe UI"
                                        }
                                    }
                                    Text {
                                        text: "CPU"; color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                                        Layout.alignment: Qt.AlignHCenter
                                    }
                                }

                                // RAM Gauge (48%)
                                ColumnLayout {
                                    spacing: 3
                                    Canvas {
                                        width: 52; height: 52
                                        onPaint: {
                                            var ctx = getContext("2d");
                                            ctx.reset();
                                            var cx = 26, cy = 26, r = 21;
                                            ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
                                            ctx.lineWidth = 4.5; ctx.strokeStyle = colors.dark ? "#1E2235" : "#e0e4ed";
                                            ctx.stroke();
                                            ctx.beginPath();
                                            ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * 0.48);
                                            ctx.lineWidth = 4.5; ctx.lineCap = "round";
                                            ctx.strokeStyle = "#8B5CF6";
                                            ctx.stroke();
                                        }
                                        Text {
                                            anchors.centerIn: parent
                                            text: "48%"
                                            color: colors.text; font.pixelSize: 12; font.bold: true; font.family: "Segoe UI"
                                        }
                                    }
                                    Text {
                                        text: "RAM"; color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                                        Layout.alignment: Qt.AlignHCenter
                                    }
                                }
                            }
                        }

                        // Divider
                        Rectangle { width: 1; Layout.fillHeight: true; color: colors.dark ? "#1E2235" : colors.border }

                        // Section 3: Spidey-Sense
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 6
                            RowLayout {
                                spacing: 5
                                Text { text: "\uD83D\uDD77"; color: "#22D3EE"; font.pixelSize: 12 }
                                Text { text: "Spidey-Sense"; color: colors.text; font.pixelSize: 12; font.bold: true; font.family: "Segoe UI" }
                            }
                            // Waveform bars
                            Canvas {
                                Layout.fillWidth: true; height: 34
                                onPaint: {
                                    var ctx = getContext("2d");
                                    ctx.reset();
                                    var w = width, h = height;
                                    ctx.strokeStyle = "#22D3EE";
                                    ctx.lineWidth = 1.5;
                                    ctx.beginPath();
                                    for (var x = 0; x < w; x++) {
                                        var y = h / 2 + Math.sin(x * 0.09) * 9 * Math.cos(x * 0.02);
                                        if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                                    }
                                    ctx.stroke();

                                    ctx.globalAlpha = 0.4;
                                    ctx.beginPath();
                                    for (var x2 = 0; x2 < w; x2++) {
                                        var y2 = h / 2 + Math.cos(x2 * 0.07 + 1) * 6;
                                        if (x2 === 0) ctx.moveTo(x2, y2); else ctx.lineTo(x2, y2);
                                    }
                                    ctx.stroke();
                                }
                            }
                            // Status indicator
                            RowLayout {
                                spacing: 5
                                Rectangle {
                                    width: 18; height: 18; radius: 9
                                    color: Qt.rgba(0.13, 0.85, 0.63, 0.15)
                                    Rectangle { anchors.centerIn: parent; width: 7; height: 7; radius: 3.5; color: "#21D9A0" }
                                }
                                ColumnLayout {
                                    spacing: 0
                                    Text { text: "Quiet"; color: "#22D3EE"; font.pixelSize: 10; font.bold: true; font.family: "Segoe UI" }
                                    Text { text: "(Systems Cool)"; color: colors.muted; font.pixelSize: 9; font.family: "Segoe UI" }
                                }
                            }
                        }
                    }
                }
            }

            // ── CARD 5: TODAY WITH YOUR COMPANION ──
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredWidth: 540
                implicitHeight: 188
                radius: 14
                color: colors.dark ? "#101422" : colors.surface
                border.width: 1; border.color: colors.dark ? "#1E2235" : colors.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    // Header
                    RowLayout {
                        Layout.fillWidth: true; spacing: 8
                        Text { text: "\uD83D\uDCCA"; color: "#F32155"; font.pixelSize: 13 }
                        Text {
                            text: "Today with your companion"
                            color: colors.text; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: "Oct 17, 2026"
                            color: colors.muted; font.pixelSize: 11; font.family: "Segoe UI"
                        }
                    }

                    // 3 Stat Columns (Equal width, beautifully aligned)
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 0

                        // Col 1: Distance
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            spacing: 3
                            Rectangle {
                                Layout.alignment: Qt.AlignHCenter
                                width: 30; height: 30; radius: 7
                                color: Qt.rgba(0.95, 0.13, 0.33, 0.15)
                                Text { anchors.centerIn: parent; text: "\uD83D\uDC63"; color: "#F32155"; font.pixelSize: 14 }
                            }
                            Text {
                                text: "Distance"
                                color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                                Layout.alignment: Qt.AlignHCenter
                            }
                            Text {
                                text: "8.4K"
                                color: colors.text; font.pixelSize: 22; font.bold: true; font.family: "Segoe UI"
                                Layout.alignment: Qt.AlignHCenter
                            }
                            Text {
                                text: "pixels traversed"
                                color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                                Layout.alignment: Qt.AlignHCenter
                            }
                        }

                        // Divider
                        Rectangle { width: 1; Layout.fillHeight: true; color: colors.dark ? "#1E2235" : colors.border }

                        // Col 2: Webs
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            spacing: 3
                            Rectangle {
                                Layout.alignment: Qt.AlignHCenter
                                width: 30; height: 30; radius: 7
                                color: Qt.rgba(0.95, 0.13, 0.33, 0.15)
                                Text { anchors.centerIn: parent; text: "\uD83D\uDD78"; color: "#F32155"; font.pixelSize: 14 }
                            }
                            Text {
                                text: "Webs"
                                color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                                Layout.alignment: Qt.AlignHCenter
                            }
                            Text {
                                text: "12"
                                color: colors.text; font.pixelSize: 22; font.bold: true; font.family: "Segoe UI"
                                Layout.alignment: Qt.AlignHCenter
                            }
                            Text {
                                text: "web lines shot"
                                color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                                Layout.alignment: Qt.AlignHCenter
                            }
                        }

                        // Divider
                        Rectangle { width: 1; Layout.fillHeight: true; color: colors.dark ? "#1E2235" : colors.border }

                        // Col 3: Active time
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            spacing: 3
                            Rectangle {
                                Layout.alignment: Qt.AlignHCenter
                                width: 30; height: 30; radius: 7
                                color: Qt.rgba(0.95, 0.13, 0.33, 0.15)
                                Text { anchors.centerIn: parent; text: "\uD83D\uDD52"; color: "#F32155"; font.pixelSize: 14 }
                            }
                            Text {
                                text: "Active time"
                                color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                                Layout.alignment: Qt.AlignHCenter
                            }
                            Text {
                                text: "2h 36m"
                                color: colors.text; font.pixelSize: 22; font.bold: true; font.family: "Segoe UI"
                                Layout.alignment: Qt.AlignHCenter
                            }
                            Text {
                                text: "companionship uptime"
                                color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                                Layout.alignment: Qt.AlignHCenter
                            }
                        }
                    }
                }
            }
        }

        // ═══════════════════════════════════════════
        //  ROW 3: QUICK NAVIGATION (Full width card)
        // ═══════════════════════════════════════════
        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 20; Layout.rightMargin: 20
            implicitHeight: 102
            radius: 14
            color: colors.dark ? "#101422" : colors.surface
            border.width: 1; border.color: colors.dark ? "#1E2235" : colors.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Text { text: "\uD83E\uDDED"; color: "#F32155"; font.pixelSize: 13 }
                    Text {
                        text: "Quick navigation"
                        color: colors.text; font.pixelSize: 14; font.bold: true; font.family: "Segoe UI"
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: "More features. More fun."
                        color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                    }
                }

                RowLayout {
                    Layout.fillWidth: true; spacing: 10

                    Repeater {
                        model: [
                            { title: "Change character", desc: "Explore different companions", icon: "\uD83C\uDFAD", target: 1 },
                            { title: "Choose activities", desc: "Discover new desktop tricks", icon: "\u26A1", target: 2 },
                            { title: "Focus settings", desc: "Customize your focus & breaks", icon: "\uD83C\uDFAF", target: 4 }
                        ]
                        Button {
                            required property var modelData
                            Layout.fillWidth: true; implicitHeight: 46
                            onClicked: if (page.bridge) page.bridge.navigate(modelData.target)
                            contentItem: RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10; anchors.rightMargin: 10
                                spacing: 10

                                Rectangle {
                                    width: 30; height: 30; radius: 7
                                    color: Qt.rgba(0.95, 0.13, 0.33, 0.15)
                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.icon; font.pixelSize: 14
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 1
                                    Text {
                                        text: modelData.title
                                        color: colors.text; font.pixelSize: 12; font.bold: true; font.family: "Segoe UI"
                                    }
                                    Text {
                                        text: modelData.desc
                                        color: colors.muted; font.pixelSize: 10; font.family: "Segoe UI"
                                        elide: Text.ElideRight; Layout.fillWidth: true
                                    }
                                }
                                Text {
                                    text: "\u203A"; color: colors.muted; font.pixelSize: 16
                                }
                            }
                            background: Rectangle {
                                radius: 8
                                color: parent.hovered ? (colors.dark ? "#181B2E" : colors.raised) : (colors.dark ? "#141727" : colors.surface)
                                border.width: 1
                                border.color: parent.hovered ? "#F32155" : (colors.dark ? "#1E2235" : colors.border)
                                Behavior on color { ColorAnimation { duration: 120 } }
                            }
                        }
                    }
                }
            }
        }

        Item { implicitHeight: 6 }
    }
}
