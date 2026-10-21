import QtQuick

QtObject {
    property bool dark: true
    // Main backgrounds
    readonly property color bg: dark ? "#080B14" : "#f2f4f8"
    readonly property color surface: dark ? "#101422" : "#ffffff"
    readonly property color raised: dark ? "#151729" : "#f2f4f8"
    // Text
    readonly property color text: dark ? "#F8FAFC" : "#182233"
    readonly property color muted: dark ? "#9BA8C0" : "#616e82"
    // Borders
    readonly property color border: dark ? "#1E2235" : "#d8dfea"
    readonly property color borderLight: dark ? "#2B2E38" : "#d0d5e0"
    // Accent
    readonly property color accent: "#F32155"
    readonly property color accentDark: "#C21846"
    readonly property color accentSoft: dark ? "#36212a" : "#fce9ee"
    // Extra accents
    readonly property color purple: "#8B5CF6"
    readonly property color cyan: "#22D3EE"
    readonly property color green: "#21D9A0"
    // Sidebar
    readonly property color sidebarBg: dark ? "#0D0B16" : "#f5f5fa"
    // Cards
    readonly property color cardBg: dark ? "#101422" : "#ffffff"
    readonly property color cardBgSecondary: dark ? "#151729" : "#f7f8fb"
    // Radius
    readonly property int radius: 14
}
