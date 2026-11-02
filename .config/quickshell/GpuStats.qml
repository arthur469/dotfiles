pragma Singleton
import Quickshell
import Quickshell.Io
import QtQuick
Scope {
    id: root
    property string sample: "- -"
    property real average:-1
    function acceptSample(text) {
        const values=text.trim().split(/\s+/),value=parseFloat(values[0]);
        if(isNaN(value))average=-1;else{const bounded=Math.max(0,Math.min(100,value));average=average<0?bounded:average*.6+bounded*.4;}
        sample=(average<0?"-":String(Math.round(average)))+" "+(values[1]||"-");sampled();
    }
    readonly property var fields: sample.trim().split(/\s+/)
    readonly property bool available: !isNaN(parseFloat(fields[0]))
    readonly property int usage: available ? Math.round(parseFloat(fields[0])) : -1
    readonly property string temperature: !isNaN(parseFloat(fields[1])) ? Math.round(parseFloat(fields[1])) + "°C" : "—"
    signal sampled()
    Process {
        id: probe
        command: ["sh", Qt.resolvedUrl("scripts/gpu-probe.sh").toString().replace("file://", "")]
        stdout: StdioCollector { onStreamFinished: { root.acceptSample(text); } }
    }
    Timer { interval: 2000; running: true; repeat: true; triggeredOnStart: true; onTriggered: if (!probe.running) probe.running = true }
}
