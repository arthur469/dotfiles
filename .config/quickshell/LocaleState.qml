pragma Singleton
import QtQuick
import Quickshell
Singleton {
    readonly property string language: (Quickshell.env("LC_TIME") || Quickshell.env("LANG") || "fr_FR").split(".")[0].split("@")[0]
    readonly property var locale: Qt.locale(language)
}
