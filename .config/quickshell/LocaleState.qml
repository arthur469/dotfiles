pragma Singleton
import QtQuick
import Quickshell
Singleton {
    readonly property string uiLanguage: (Quickshell.env("LC_ALL") || Quickshell.env("LC_MESSAGES") || Quickshell.env("LANG") || "en_US").split(".")[0].split("@")[0]
    function tr(fr, en) { return uiLanguage.toLowerCase().startsWith("fr") ? fr : en; }
    readonly property string language: (Quickshell.env("LC_TIME") || Quickshell.env("LANG") || "fr_FR").split(".")[0].split("@")[0]
    readonly property var locale: Qt.locale(language)
}
