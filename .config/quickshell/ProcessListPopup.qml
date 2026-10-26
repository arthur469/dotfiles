import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
Scope {
    id: root
    property string position: "left"
    property real uiScale: 1
    property Item target: null
    property bool opened: false
    property string kind: "cpu"
    property var processes: []
    property string error: ""
    property string unit: ""
    property var pending: null
    property string actionMessage: ""
    property bool canForce: false
    property bool hovered: false
    property string sortMode: "usage"
    readonly property bool frozen: hovered || pending !== null
    function buttonRect(item) {
        const p = item.mapToItem(popup.contentItem, 0, 0);
        return {x:popup.point.x+p.x,y:popup.point.y+p.y,width:item.width,height:item.height};
    }
    function changeSort() {
        sortMode=sortMode === "name" ? "usage" : "name";
        const rows=processes.slice();
        rows.sort((a,b)=>sortMode === "name" ? a.name.localeCompare(b.name) || a.pid-b.pid : (b.value===null ? -1:b.value)-(a.value===null ? -1:a.value) || b.memory-a.memory);
        processes=rows;
        if(!frozen)refresh();
    }
    function requestStop(process) {
        if (!process.canStop) return;
        pending = process; canForce = false; actionMessage = "";
    }
    function stopConfirmed(force) {
        if (!pending || actionWorker.running) return;
        actionWorker.command = ["python3", Qt.resolvedUrl("scripts/system-processes.py").toString().replace("file://", ""), "--stop-pid", String(pending.pid), "--identity", pending.identity];
        if (force) actionWorker.command = actionWorker.command.concat(["--force"]);
        actionWorker.running = true;
    }
    Process {
        id: actionWorker
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text); root.actionMessage = result.message;
                    if (result.success && result.status === "sent") forceDelay.restart();
                    if (result.status === "exited") root.pending = null;
                } catch (e) { root.actionMessage = "Fermeture impossible"; }
                root.refresh();
            }
        }
    }
    Timer { id: forceDelay; interval: 1500; onTriggered: root.canForce = true }

    BarAnchor { id: placement; position: root.position; target: root.target; onInvalidated: root.close() }
    onTargetChanged: if (!target) close()
    function close() { opened = false; pending = null; canForce = false; }
    function toggle(item, type) {
        const next = type.toLowerCase();
        if (opened && target === item && kind === next) { close(); return; }
        target = item; kind = next; hovered = false; pending = null; canForce = false; processes = []; processList.contentY=0; error = ""; opened = true; refresh();
    }
    function refresh() {
        if (!opened || worker.running || frozen) return;
        worker.command = ["python3", Qt.resolvedUrl("scripts/system-processes.py").toString().replace("file://", ""), "--kind", kind, "--sort", sortMode];
        worker.running = true;
    }
    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(text);
                    if (data.kind === root.kind && data.sort === root.sortMode && root.opened && !root.frozen) { const scroll=processList.contentY; root.processes = data.processes; Qt.callLater(()=>{if(root.opened)processList.contentY=Math.max(0,Math.min(scroll,processList.contentHeight-processList.height));}); root.error = data.error || ""; root.unit = data.unit || ""; }
                } catch (e) { root.error = "Lecture des processus indisponible"; }
            }
        }
        onExited: if (root.opened && command[command.length-3] !== root.kind) root.refresh()
    }
    Timer { interval: 2500; repeat: true; running: root.opened && !root.frozen; onTriggered: root.refresh() }
    PopupWindow {
        id: popup
        anchor.window: placement.window
        anchor.adjustment: PopupAdjustment.Slide
        readonly property var output: placement.window ? placement.window.screen : null
        readonly property point point: placement.place(implicitWidth, implicitHeight, output ? output.width : 800, output ? output.height : 600, 0, 0)
        anchor.rect.x: point.x - (root.position === "right" && placement.window ? output.width - placement.window.width : 0)
        anchor.rect.y: point.y - (root.position === "bottom" && placement.window ? output.height - placement.window.height : 0)
        implicitWidth: Math.max(1, Math.min(500 * root.uiScale, (output ? output.width : 800) - 32))
        implicitHeight: Math.max(1, Math.min(126 + root.processes.length * 34 * root.uiScale + (root.pending ? 90 : 0), (output ? output.height : 600) * 0.6))
        visible: root.opened && placement.window !== null && placement.window.visible
        color: "transparent"
        HyprlandFocusGrab { windows: [popup]; active: popup.visible; onCleared: root.close() }
        Rectangle {
            HoverHandler { onHoveredChanged: { root.hovered = hovered; if (!hovered) root.refresh(); } }
            anchors.fill: parent; radius: Theme.radius; color: Theme.bg
            border.width: 1; border.color: Theme.accent
            Column {
                anchors.fill: parent; anchors.margins: 14; spacing: 8
                Item {
                    width: parent.width; height: 24
                    Text { text: root.kind.toUpperCase() + " — processus"; color: Theme.text; font.bold: true; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "×"; color: Theme.text; font.pixelSize: 20; anchors.right: parent.right; MouseArea { anchors.fill: parent; onClicked: root.close() } }
                }
                Row {
                    spacing: 8
                    Repeater {
                        id: toolRepeater
                        model: [{label:root.sortMode === "name" ? "Nom A → Z" : "Consommation ↓", action:"sort"}]
                        delegate: Rectangle {
                            required property var modelData
                            width: 150; height: 26; radius: Theme.radius; color: Qt.alpha(Theme.text, 0.08)
                            Text { anchors.centerIn: parent; text: modelData.label; color: Theme.text; font.pixelSize: 11 }
                            MouseArea { anchors.fill: parent; onClicked: {
                                root.changeSort();
                            } }
                        }
                    }
                }
                Text { width: parent.width; text: root.error || ((root.pending ? "Confirmation · " : root.hovered ? "Figée au survol · " : "") + root.unit); color: Theme.textDim; font.pixelSize: 11; wrapMode: Text.WordWrap }
                ListView {
                    id: processList
                    width: parent.width; height: Math.max(0, popup.height - y - 20 - (root.pending ? 90 : 0)); clip: true
                    model: root.processes; boundsBehavior: Flickable.StopAtBounds
                    Controls.ScrollBar.vertical: Controls.ScrollBar {
                        width: 5; policy: Controls.ScrollBar.AsNeeded
                        contentItem: Rectangle {radius:3;color:Theme.accent;opacity:0.6}
                    }
                    delegate: Item {
                        required property var modelData
                        readonly property var processData: modelData
                        readonly property Item closeButton: stopButton
                        width: ListView.view.width; height: 34 * root.uiScale
                        Text { anchors { left: parent.left; right: metric.left; rightMargin: 12; verticalCenter: parent.verticalCenter }
 text: modelData.name + "  ·  " + modelData.pid; textFormat: Text.PlainText; elide: Text.ElideRight; color: Theme.text; font.pixelSize: 12 }
                        Text { id: metric; anchors { right: stopButton.left; rightMargin: 10; verticalCenter: parent.verticalCenter }
 text: modelData.display; color: Theme.textDim; font.pixelSize: 12 }
                        Rectangle {
                            id: stopButton
                            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                            width: 24; height: 24; radius: Theme.radius
                            color: Qt.alpha(Theme.danger, stopMouse.containsMouse ? 0.25 : 0.08)
                            opacity: modelData.canStop ? 1 : 0.25
                            Text { anchors.centerIn: parent; text: "×"; color: Theme.danger; font.pixelSize: 18 }
                            MouseArea { id: stopMouse; anchors.fill: parent; hoverEnabled: true; enabled: modelData.canStop; cursorShape: Qt.PointingHandCursor; onClicked: root.requestStop(modelData) }
                        }
                    }
                }
                Column {
                    width: parent.width; spacing: 7; visible: root.pending !== null
                    Text { width: parent.width; text: root.pending ? (root.canForce ? "Le processus répond-il encore ? " : "Fermer ") + root.pending.name + " · " + root.pending.pid + " ?" : ""; color: Theme.text; font.pixelSize: 12; elide: Text.ElideRight }
                    Text { visible: root.actionMessage !== ""; text: root.actionMessage; color: Theme.textDim; font.pixelSize: 11 }
                    Row {
                        spacing: 8
                        Rectangle {
                            id: cancelButton
                            width: 100; height: 28; radius: Theme.radius; color: Qt.alpha(Theme.text, 0.08)
                            Text { anchors.centerIn: parent; text: "Annuler"; color: Theme.text; font.pixelSize: 12 }
                            MouseArea { anchors.fill: parent; onClicked: root.pending = null }
                        }
                        Rectangle {
                            id: confirmButton
                            width: 140; height: 28; radius: Theme.radius; color: Qt.alpha(Theme.danger, 0.18)
                            Text { anchors.centerIn: parent; text: root.canForce ? "Forcer l’arrêt" : "Fermer"; color: Theme.danger; font.pixelSize: 12 }
                            MouseArea { anchors.fill: parent; enabled: !actionWorker.running; onClicked: root.stopConfirmed(root.canForce) }
                        }
                    }
                }
            }
        }
    }
    IpcHandler {
        target: "processes"
        function close(): void { root.close(); }
        function diagnostic(): string { const buttons=[];
            for (let i=0;i<processList.count;i++) { const row=processList.itemAtIndex(i); if (row && row.y>=processList.contentY && row.y+row.height<=processList.contentY+processList.height) buttons.push({pid:row.processData.pid,geometry:root.buttonRect(row.closeButton)}); }
            return JSON.stringify({open:root.opened,kind:root.kind,contentY:processList.contentY,contentHeight:processList.contentHeight,listHeight:processList.height,frozen:root.frozen,sort:root.sortMode,pending:root.pending,processes:root.processes,error:root.error,buttons:buttons,tools:Array.from({length:toolRepeater.count},(_,i)=>{const item=toolRepeater.itemAt(i);return {action:item.modelData.action,geometry:root.buttonRect(item)};}),confirm:root.pending ? root.buttonRect(confirmButton) : null,cancel:root.pending ? root.buttonRect(cancelButton) : null}); }
    }
}
