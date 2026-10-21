import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ScrollView {
    id: page
    objectName: "qmlActivitiesPage"
    property QtObject bridge: dashboardBridge
    property QtObject library: activityLibrary
    property string selected: "idle"
    property bool detailsOpen: true
    property string category: "All"
    property string filter: "All"
    property string query: ""
    property var selectedRow: {
        var rows = library ? library.rows : [];
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].id === selected) return rows[i];
        }
        return null;
    }
    property var filteredRows: {
        var rows = library ? library.rows : [];
        return rows.filter(function(row) {
            return (category === "All" || row.category === category) &&
                (filter === "All" || (filter === "Enabled" && row.enabled) || (filter === "Disabled" && !row.enabled) || (filter === "Supported" && row.available)) &&
                (row.label + " " + row.description + " " + row.id).toLowerCase().indexOf(query.toLowerCase()) >= 0;
        });
    }
    Theme { id: colors; dark: page.bridge ? page.bridge.darkTheme : true }
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical: ScrollBar { width: 6; contentItem: Rectangle { radius: 3; color: colors.border } }
    background: Rectangle { color: colors.bg }

    Rectangle {
        anchors.fill: parent
        color: colors.bg
        z: -1
    }
    function reveal(y) { page.contentItem.contentY = Math.min(y, Math.max(0, page.contentHeight - page.availableHeight)); }

    Connections {
        target: page.bridge
        function onRevealRequested(key) {
            if (!page.bridge || page.bridge.currentRoute !== 2) return;
            page.category = "All"; page.query = ""; search.clear(); page.filter = "All";
            var opts = page.library ? page.library.options : [];
            for (var i = 0; i < opts.length; i++) {
                if (opts[i].id === key || opts[i].label === key) {
                    page.category = opts[i].category;
                    Qt.callLater(function() { page.reveal(optionsPanel.y); });
                    return;
                }
            }
            var rows = page.library ? page.library.rows : [];
            for (var j = 0; j < rows.length; j++) {
                if (rows[j].id === key || rows[j].label === key) {
                    page.selected = rows[j].id;
                    page.detailsOpen = true;
                    Qt.callLater(function() { page.reveal(details.y); });
                    return;
                }
            }
            Qt.callLater(function() { page.reveal(gallery.y); });
        }
    }

    ColumnLayout {
        width: page.availableWidth
        spacing: 16

        // 1. Header
        SelectableText {
            Layout.fillWidth: true
            text: "A little character goes a long way"
            font.pixelSize: page.width < 600 ? 23 : 28
            font.bold: true
            color: colors.text
        }
        SelectableText {
            Layout.fillWidth: true
            text: page.bridge ? (page.bridge.characterName + " · Choose what your companion can do. Preferences apply to all characters.") : ""
            color: colors.muted
            font.pixelSize: 12
        }

        // 2. Playback Controls
        Panel {
            Layout.fillWidth: true
            paletteTokens: colors
            ColumnLayout {
                width: parent.width
                spacing: 12
                SelectableText { text: "Playback mode"; color: colors.text; font.pixelSize: 16; font.bold: true }
                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    ActionButton {
                        objectName: "playbackAutomatic"
                        paletteTokens: colors
                        text: "Automatic playback"
                        primary: page.library && page.library.automatic
                        onClicked: page.library.setPlayback(true, page.selected)
                    }
                    ActionButton {
                        objectName: "playbackRepeat"
                        paletteTokens: colors
                        text: "Repeat selected activity"
                        primary: page.library && !page.library.automatic
                        enabled: page.selectedRow && page.selectedRow.available && page.selectedRow.enabled && !["music", "sound", "bubbles", "trampoline", "glitch", "battery", "charging", "load"].includes(page.selected)
                        onClicked: page.library.setPlayback(false, page.selected)
                    }
                    ComboBox {
                        id: repeatCombo
                        objectName: "repeatCombo"
                        visible: page.library && !page.library.automatic
                        implicitHeight: 38
                        model: page.library ? page.library.rows.filter(function(r) {
                            return r.available && r.enabled && !["music", "sound", "bubbles", "trampoline", "glitch", "battery", "charging", "load"].includes(r.id);
                        }) : []
                        textRole: "label"
                        palette.button: colors.raised
                        palette.buttonText: colors.text
                        palette.base: colors.surface
                        palette.text: colors.text
                        currentIndex: {
                            var items = model || [];
                            for (var i = 0; i < items.length; i++) {
                                if (items[i].id === (page.library ? page.library.locked : "")) return i;
                            }
                            return 0;
                        }
                        onActivated: {
                            var chosen = (model && model[currentIndex]) ? model[currentIndex].id : "";
                            if (chosen) page.library.setPlayback(false, chosen);
                        }
                    }
                }
                SelectableText {
                    Layout.fillWidth: true
                    text: page.library && !page.library.automatic
                          ? ("Repeating: " + (page.selectedRow ? page.selectedRow.label : page.library.locked) + ". Disabling this activity will return to automatic playback.")
                          : "Automatic playback chooses among currently allowed activities according to character personality and timers."
                    color: colors.muted
                    font.pixelSize: 12
                }
            }
        }

        // 3. Activity Details Panel
        Panel {
            id: details
            visible: page.detailsOpen
            Layout.fillWidth: true
            paletteTokens: colors
            ColumnLayout {
                width: parent.width
                spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    SelectableText {
                        Layout.fillWidth: true
                        text: page.selectedRow ? page.selectedRow.label : "Choose an activity"
                        font.pixelSize: 19
                        font.bold: true
                        color: colors.text
                    }
                    Rectangle {
                        visible: page.selectedRow && page.selectedRow.recovery
                        radius: 4
                        color: colors.raised
                        implicitWidth: recLabel.implicitWidth + 10
                        implicitHeight: 22
                        Text {
                            id: recLabel
                            anchors.centerIn: parent
                            text: "Required transition"
                            color: colors.muted
                            font.pixelSize: 10
                        }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 180
                    color: colors.raised
                    radius: 12
                    clip: true
                    Image {
                        id: detailPreviewImage
                        anchors.fill: parent
                        source: (page.library && page.library.previewId !== "")
                                ? ("image://activity/frame/" + page.library.revision)
                                : (page.selected ? ("image://activity/thumb/" + page.selected + "?rev=" + (page.library ? page.library.revision : 0)) : "")
                        cache: false
                        fillMode: Image.PreserveAspectFit
                    }
                }
                SelectableText {
                    Layout.fillWidth: true
                    text: page.selectedRow ? page.selectedRow.description : ""
                    color: colors.muted
                    font.pixelSize: 12
                }
                SelectableText {
                    Layout.fillWidth: true
                    visible: page.selectedRow && page.selectedRow.recovery
                    text: "Recovery pose: required physics transitions (falling, landing) can still complete when optional playback is disabled."
                    color: colors.muted
                    font.pixelSize: 12
                }
                SelectableText {
                    Layout.fillWidth: true
                    visible: page.selectedRow && !page.selectedRow.available
                    text: (page.selectedRow && page.selectedRow.reason) ? page.selectedRow.reason : "This character does not include this animation."
                    color: colors.accent
                    font.pixelSize: 12
                }
                SelectableText {
                    Layout.fillWidth: true
                    visible: page.selectedRow && !!page.selectedRow.prerequisites
                    text: "Prerequisite: " + (page.selectedRow ? page.selectedRow.prerequisites : "")
                    color: colors.muted
                    font.pixelSize: 12
                }
                SelectableText {
                    Layout.fillWidth: true
                    visible: page.selectedRow && page.selectedRow.available && !page.selectedRow.preview
                    text: "No isolated dashboard preview for this effect. It needs its real desktop or system context."
                    color: colors.muted
                    font.pixelSize: 12
                }

                // Action Buttons
                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    ActionButton {
                        objectName: "previewActivity"
                        paletteTokens: colors
                        text: (page.library && page.library.previewId === page.selected) ? "Restart preview" : "Preview here"
                        enabled: page.selectedRow && page.selectedRow.preview
                        onClicked: page.library.preview(page.selected)
                    }
                    ActionButton {
                        objectName: "stopPreview"
                        paletteTokens: colors
                        text: "Stop preview"
                        enabled: page.library && page.library.previewId !== ""
                        onClicked: page.library.stopPreview()
                    }
                    ActionButton {
                        objectName: "playDesktopActivity"
                        paletteTokens: colors
                        text: "Play on desktop"
                        visible: page.selectedRow && !["music", "sound", "bubbles", "trampoline", "glitch", "battery", "charging", "load"].includes(page.selected)
                        enabled: page.selectedRow && page.selectedRow.canPlayDesktop
                        onClicked: page.library.playDesktop(page.selected)
                    }
                    ActionButton {
                        paletteTokens: colors
                        text: "Test effect on desktop"
                        visible: ["music", "trampoline", "glitch", "battery", "charging", "load"].includes(page.selected)
                        enabled: page.selectedRow && page.selectedRow.enabled
                        onClicked: page.library.testDesktop(page.selected)
                    }
                    ActionButton {
                        paletteTokens: colors
                        text: "Stop desktop test"
                        visible: ["music", "battery", "charging", "load"].includes(page.selected) && page.library && page.library.isSimulating
                        onClicked: page.library.stopDesktopTest()
                    }
                }
                SelectableText {
                    objectName: "activityFeedback"
                    Layout.fillWidth: true
                    text: page.library ? page.library.message : ""
                    color: colors.muted
                    font.pixelSize: 12
                }

                // Related settings shortcuts for the selected activity
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    visible: page.selectedRow && !!page.selectedRow.relatedSettings
                    SelectableText { text: "Related settings"; color: colors.text; font.pixelSize: 13; font.bold: true }
                    Repeater {
                        model: page.library ? page.library.options.filter(function(opt) {
                            if (!page.selectedRow || !page.selectedRow.relatedSettings) return false;
                            var rels = page.selectedRow.relatedSettings.split(",");
                            return rels.indexOf(opt.id) >= 0;
                        }) : []
                        RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            SelectableText { Layout.fillWidth: true; text: modelData.label; color: colors.muted; font.pixelSize: 12 }
                            Switch {
                                visible: modelData.kind === "check"
                                checked: !!modelData.value
                                palette.highlight: colors.accent
                                onClicked: page.library.setOption(modelData.id, checked)
                            }
                        }
                    }
                }
            }
        }

        // 4. Search & Filters
        TextField {
            id: search
            objectName: "activitySearch"
            Layout.fillWidth: true
            placeholderText: "Find an activity or effect…    (e.g., walk, jump, music, window, sleep)"
            color: colors.text
            placeholderTextColor: colors.muted
            onTextChanged: page.query = text
            background: Rectangle {
                color: colors.surface
                radius: 8
                border.color: search.activeFocus ? colors.accent : colors.border
            }
            Accessible.name: "Search activities"
        }
        Flow {
            Layout.fillWidth: true
            spacing: 6
            Repeater {
                model: ["All", "Movement", "Rest & Poses", "Expressions", "Window Activities", "Music & Sound", "Effects & Toys", "System Reactions", "Advanced Transitions", "Timing"]
                ActionButton {
                    required property string modelData
                    paletteTokens: colors
                    text: modelData
                    primary: page.category === modelData
                    onClicked: page.category = modelData
                }
            }
        }
        Flow {
            Layout.fillWidth: true
            spacing: 6
            Repeater {
                model: ["All", "Enabled", "Disabled", "Supported"]
                ActionButton {
                    required property string modelData
                    paletteTokens: colors
                    text: modelData
                    primary: page.filter === modelData
                    onClicked: page.filter = modelData
                }
            }
        }
        SelectableText {
            Layout.fillWidth: true
            text: page.filteredRows.length + " activities and effects"
            color: colors.muted
            font.pixelSize: 12
        }

        // 5. Activity Cards Grid
        GridLayout {
            id: gallery
            objectName: "activityGallery"
            Layout.fillWidth: true
            columns: Math.max(1, Math.min(3, Math.floor((page.availableWidth + 14) / 240)))
            columnSpacing: 14
            rowSpacing: 14
            Repeater {
                model: page.filteredRows
                Panel {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredWidth: (page.availableWidth - 14 * (gallery.columns - 1)) / gallery.columns
                    Layout.minimumHeight: 285
                    paletteTokens: colors
                    background: Rectangle {
                        color: page.selected === modelData.id ? colors.accentSoft : colors.surface
                        radius: 14
                        border.width: page.selected === modelData.id ? 2 : 1
                        border.color: page.selected === modelData.id ? colors.accent : colors.border
                    }
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 85
                            radius: 8
                            color: colors.raised
                            clip: true
                            Image {
                                anchors.fill: parent
                                source: modelData.available ? ("image://activity/thumb/" + modelData.id + "?rev=" + (page.library ? page.library.revision : 0)) : ""
                                visible: modelData.available
                                fillMode: Image.PreserveAspectFit
                                cache: true
                            }
                            Text {
                                anchors.centerIn: parent
                                visible: !modelData.available
                                text: "No clip"
                                color: colors.muted
                                font.pixelSize: 11
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            SelectableText {
                                Layout.fillWidth: true
                                text: modelData.label
                                color: colors.text
                                font.pixelSize: 14
                                font.bold: true
                            }
                            Rectangle {
                                visible: modelData.recovery
                                radius: 4
                                color: colors.raised
                                implicitWidth: cardRecLabel.implicitWidth + 8
                                implicitHeight: 18
                                Text {
                                    id: cardRecLabel
                                    anchors.centerIn: parent
                                    text: "Required"
                                    color: colors.muted
                                    font.pixelSize: 9
                                }
                            }
                        }
                        SelectableText {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 32
                            text: modelData.description
                            color: colors.muted
                            font.pixelSize: 11
                            clip: true
                        }
                        SelectableText {
                            Layout.fillWidth: true
                            text: modelData.available ? modelData.category : (modelData.reason || "This character does not include this animation.")
                            color: modelData.available ? colors.muted : colors.accent
                            font.pixelSize: 10
                            clip: true
                        }
                        Item { Layout.fillHeight: true }
                        Switch {
                            objectName: "allow_" + modelData.id
                            text: modelData.enabled ? "Allowed" : "Disabled"
                            checked: modelData.enabled
                            enabled: modelData.available
                            palette.windowText: colors.text
                            palette.highlight: colors.accent
                            onClicked: page.library.toggle(modelData.id, checked)
                            Accessible.name: "Allow " + modelData.label
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            ActionButton {
                                objectName: "preview_" + modelData.id
                                Layout.fillWidth: true
                                paletteTokens: colors
                                text: (page.library && page.library.previewId === modelData.id) ? "Stop" : "Preview"
                                enabled: modelData.preview
                                onClicked: {
                                    if (page.library && page.library.previewId === modelData.id) {
                                        page.library.stopPreview();
                                    } else {
                                        page.selected = modelData.id;
                                        page.library.preview(modelData.id);
                                    }
                                }
                            }
                            ActionButton {
                                objectName: "inspect_" + modelData.id
                                Layout.fillWidth: true
                                paletteTokens: colors
                                text: "Details"
                                onClicked: {
                                    page.selected = modelData.id;
                                    page.detailsOpen = true;
                                    Qt.callLater(function() { page.reveal(details.y); });
                                }
                            }
                        }
                    }
                }
            }
        }
        SelectableText {
            Layout.fillWidth: true
            visible: page.filteredRows.length === 0 && page.category !== "Timing"
            text: "No matching activities. Try another category or search."
            color: colors.muted
        }

        // 6. Timing & Related settings
        Panel {
            id: optionsPanel
            Layout.fillWidth: true
            paletteTokens: colors
            ColumnLayout {
                width: parent.width
                spacing: 14
                SelectableText { text: "Related settings & timing"; color: colors.text; font.pixelSize: 17; font.bold: true }
                Repeater {
                    model: page.library ? page.library.options.filter(function(row) {
                        return page.category === "All" || row.category === page.category;
                    }) : []
                    ColumnLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 4
                        SelectableText { Layout.fillWidth: true; text: modelData.label; color: colors.text; font.pixelSize: 12 }
                        Switch {
                            visible: modelData.kind === "check"
                            checked: !!modelData.value
                            palette.highlight: colors.accent
                            onClicked: page.library.setOption(modelData.id, checked)
                            Accessible.name: modelData.label
                        }
                        Slider {
                            Layout.fillWidth: true
                            visible: modelData.kind === "slider"
                            from: modelData.low || 0
                            to: modelData.high || 100
                            stepSize: 1
                            value: Number(modelData.value) * modelData.factor
                            onMoved: page.library.setOption(modelData.id, value / modelData.factor)
                            Accessible.name: modelData.label
                            palette.highlight: colors.accent
                        }
                        SelectableText {
                            visible: modelData.kind === "slider"
                            text: Math.round(Number(modelData.value) * modelData.factor) + (modelData.suffix || "")
                            color: colors.muted
                            font.pixelSize: 12
                        }
                        ComboBox {
                            Layout.fillWidth: true
                            visible: modelData.kind === "combo"
                            model: modelData.choices || []
                            textRole: "label"
                            palette.button: colors.raised
                            palette.buttonText: colors.text
                            palette.base: colors.surface
                            palette.text: colors.text
                            currentIndex: {
                                var values = modelData.choices || [];
                                for (var i = 0; i < values.length; i++) {
                                    if (values[i].value === modelData.value) return i;
                                }
                                return 0;
                            }
                            onActivated: page.library.setOption(modelData.id, modelData.choices[currentIndex].value)
                            Accessible.name: modelData.label
                        }
                    }
                }
            }
        }

        // 7. Bulk Controls
        Panel {
            Layout.fillWidth: true
            paletteTokens: colors
            ColumnLayout {
                width: parent.width
                spacing: 10
                SelectableText { text: "Bulk permissions"; color: colors.text; font.pixelSize: 16; font.bold: true }
                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    ActionButton {
                        objectName: "bulkEnable"
                        paletteTokens: colors
                        text: "Enable supported activities"
                        onClicked: page.library.bulk("enable")
                    }
                    ActionButton {
                        objectName: "bulkDisable"
                        paletteTokens: colors
                        text: "Disable optional activities"
                        onClicked: page.library.bulk("disable")
                    }
                    ActionButton {
                        objectName: "bulkReset"
                        paletteTokens: colors
                        text: "Restore activity defaults"
                        onClicked: page.library.bulk("reset")
                    }
                }
                SelectableText {
                    Layout.fillWidth: true
                    text: "Bulk actions affect animation permissions only. Required recovery poses (falling, landing) stay active. Timing, effects, appearance, and unrelated preferences keep their current values."
                    color: colors.muted
                    font.pixelSize: 11
                }
            }
        }

        Item { implicitHeight: 16 }
    }
}
