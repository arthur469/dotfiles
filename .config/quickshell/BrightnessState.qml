pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
Singleton {
    id: root
    property real value: 0.55
    property bool available: false
    property string error: ""
    property string output: ""
    property int pending: -1
    function refresh(name) { if (name !== undefined) output=name; if (!worker.running) launch(-1); }
    function set(percent) { pending=Math.max(1,Math.min(100,Math.round(percent))); value=pending/100; applyTimer.restart(); }
    function launch(percent) {
        let args=["python3",Qt.resolvedUrl("scripts/brightness.py").toString().replace("file://","")];
        if(output)args=args.concat(["--output",output]); if(percent>=0)args=args.concat(["--set",String(percent)]);
        worker.command=args; worker.running=true;
    }
    Timer { id: applyTimer; interval: 100; onTriggered: { if(worker.running) { restart(); return; } const next=root.pending;root.pending=-1;root.launch(next); } }
    Process {
        id: worker
        stdout: StdioCollector { onStreamFinished: { try { const d=JSON.parse(text);root.available=d.available;root.error=d.error||"";if(d.available && root.pending<0)root.value=d.value/100; } catch(e) {root.error="Lecture de luminosité impossible";} } }
    }
}
