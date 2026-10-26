pragma Singleton
import Quickshell
import Quickshell.Io
import QtQuick
Scope {
    id: root
    property string sample: "- -"
    readonly property var fields: sample.trim().split(/\s+/)
    readonly property bool available: !isNaN(parseFloat(fields[0]))
    readonly property int usage: available ? Math.round(parseFloat(fields[0])) : -1
    readonly property string temperature: !isNaN(parseFloat(fields[1])) ? Math.round(parseFloat(fields[1])) + "°C" : "—"
    signal sampled()
    Process {
        id: probe
        command: ["sh", Qt.resolvedUrl("scripts/gpu-probe.sh").toString().replace("file://", "")]
        stdout: StdioCollector { onStreamFinished: { root.sample = text.trim() || "- -"; root.sampled(); } }
    }
    Timer { interval: 2000; running: true; repeat: true; triggeredOnStart: true; onTriggered: if (!probe.running) probe.running = true }
}
