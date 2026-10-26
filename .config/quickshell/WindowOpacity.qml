import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
Scope {
    Timer { id: debounce; interval: 180; onTriggered: { if (!sync.running) sync.running = true; else retry.restart(); } }
    Timer { id: retry; interval: 250; onTriggered: debounce.restart() }
    Process { id: sync; command: ["python3", Quickshell.env("HOME") + "/.config/hypr/scripts/window-opacity.py", "--sync"] }
    Connections {
        target: Hyprland
        function onRawEvent(event) {
            if (["openwindow", "closewindow", "movewindow", "movewindowv2", "configreloaded", "fullscreen"].includes(event.name)) debounce.restart();
        }
    }
    Component.onCompleted: debounce.start()
}
