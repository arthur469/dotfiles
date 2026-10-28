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
    property var groups: []
    property var expanded: ({})
    property string error: ""
    property string unit: ""
    property var pending: null
    property Item pendingAnchor: null
    property string actionMessage: ""
    property bool canForce: false
    property bool hovered: false
    property string sortMode: "usage"
    readonly property bool frozen: hovered || pending !== null
    readonly property var rows: {
        const result=[];
        for(const group of groups) {
            result.push(group);
            if(expanded[group.key])for(const child of group.children)result.push(Object.assign({},child,{group:false,parentKey:group.key}));
        }
        return result;
    }
    function buttonRect(item) {
        const p = item.mapToItem(popup.contentItem, 0, 0);
        return {x:popup.point.x+p.x,y:popup.point.y+p.y,width:item.width,height:item.height};
    }
    function changeSort() {
        setSort(sortMode === "name" ? "usage" : sortMode === "usage" && kind === "gpu" ? "memory" : "name");
    }
    function setSort(mode) {
        if (!["usage","name"].concat(kind === "gpu" ? ["memory"] : []).includes(mode)) return;
        sortMode=mode;
        const compare=(a,b)=>sortMode==="name" ? a.name.toLowerCase().localeCompare(b.name.toLowerCase())||a.pid-b.pid : sortMode==="memory" ? b.memory-a.memory||(b.value||0)-(a.value||0)||a.pid-b.pid : (b.value||0)-(a.value||0)||b.memory-a.memory||a.pid-b.pid;
        groups=groups.slice().sort(compare).map(g=>Object.assign({},g,{children:g.children.slice().sort(compare)}));
        if(!frozen)refresh();
    }
    function requestStop(process,anchor) {
        if (!process.canStop) return;
        forceDelay.stop();pending = process; pendingAnchor=anchor;canForce = false; actionMessage = "";
    }
    function stopConfirmed(force) {
        if (!pending || actionWorker.running) return;
        actionWorker.command = ["python3", Qt.resolvedUrl("scripts/system-processes.py").toString().replace("file://", "")];
        if(pending.group)actionWorker.command=actionWorker.command.concat(["--stop-group",JSON.stringify(pending.members)]);
        else actionWorker.command=actionWorker.command.concat(["--stop-pid",String(pending.pid),"--identity",pending.identity]);
        if (force) actionWorker.command = actionWorker.command.concat(["--force"]);
        actionWorker.command=actionWorker.command.concat(["--language",LocaleState.uiLanguage]);actionWorker.running = true;
    }
    Process {
        id: actionWorker
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    root.actionMessage=result.success ? LocaleState.tr("Demande de fermeture envoyée.","Close request sent.") : LocaleState.tr(result.message,"Cannot close this process; refresh the list.");
                    if (result.success && result.status === "sent") forceDelay.restart();
                    if (result.status === "exited") {forceDelay.stop();root.pending=null;root.pendingAnchor=null;}
                } catch (e) { root.actionMessage = LocaleState.tr("Fermeture impossible","Cannot close process"); }
                root.refresh();
            }
        }
    }
    Timer { id: forceDelay; interval: 1500; onTriggered: root.canForce = true }
    BarAnchor { id: placement; position: root.position; target: root.target; onInvalidated: root.close() }
    onTargetChanged: if (!target) close()
    function close() { forceDelay.stop();opened = false; pending = null; pendingAnchor=null;canForce = false; }
    function toggle(item, type) {
        const next = type.toLowerCase();
        if (opened && target === item && kind === next) { close(); return; }
        target = item; kind = next; hovered = false; pending = null;pendingAnchor=null;canForce = false;
        if (kind !== "gpu" && sortMode === "memory") sortMode = "usage";
        processes = [];groups=[];expanded=({});processList.contentY=0;error = "";opened = true;refresh();
    }
    function refresh() {
        if (!opened || worker.running || frozen) return;
        worker.command = ["python3", Qt.resolvedUrl("scripts/system-processes.py").toString().replace("file://", ""), "--kind", kind, "--sort", sortMode,"--language",LocaleState.uiLanguage];
        worker.running = true;
    }
    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(text);
                    if (data.kind === root.kind && data.sort === root.sortMode && root.opened && !root.frozen) {
                        const scroll=processList.contentY;root.processes=data.processes;root.groups=data.groups||[];
                        root.error=data.error ? LocaleState.tr(data.error,"Process details unavailable") : "";
                        root.unit=root.kind==="cpu" ? LocaleState.tr("100 % = un cœur","100% = one core") : root.kind==="ram" ? LocaleState.tr("Mémoire proportionnelle (PSS), RSS si indisponible","Proportional memory (PSS), RSS when unavailable") : LocaleState.tr("GPU · mémoire vidéo","GPU · video memory");
                        Qt.callLater(()=>{if(root.opened)processList.contentY=Math.max(0,Math.min(scroll,processList.contentHeight-processList.height));});
                    }
                } catch (e) { root.error = LocaleState.tr("Lecture des processus indisponible","Cannot read processes"); }
            }
        }
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
        implicitWidth: Math.max(1, Math.min(540 * root.uiScale, (output ? output.width : 800) - 32))
        implicitHeight: Math.max(1, Math.min(126 + root.rows.length * 34 * root.uiScale, (output ? output.height : 600) * 0.65))
        visible: root.opened && placement.window !== null && placement.window.visible
        color: "transparent"
        HyprlandFocusGrab { windows: [popup]; active: popup.visible; onCleared: root.close() }
        Rectangle {
            id: surface
            HoverHandler { onHoveredChanged: { root.hovered = hovered; if (!hovered) root.refresh(); } }
            anchors.fill: parent; radius: Theme.radius; color: Theme.bg
            border.width: 1; border.color: Theme.accent
            Column {
                anchors.fill: parent; anchors.margins: 14; spacing: 8
                Item {
                    width: parent.width; height: 24
                    Text { text: root.kind.toUpperCase() + LocaleState.tr(" — applications et processus"," — apps and processes"); color: Theme.text; font.bold: true; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "×"; color: Theme.text; font.pixelSize: 20; anchors.right: parent.right; MouseArea { anchors.fill: parent; onClicked: root.close() } }
                }
                Row {
                    spacing: 8
                    Repeater {
                        id: toolRepeater
                        model: [{mode:"usage",label:LocaleState.tr("Consommation ↓","Usage ↓")}].concat(root.kind === "gpu" ? [{mode:"memory",label:"VRAM ↓"}] : []).concat([{mode:"name",label:LocaleState.tr("Nom A → Z","Name A → Z")}])
                        delegate: Rectangle {
                            required property var modelData
                            width: Math.min(150, (popup.width - 44) / (root.kind === "gpu" ? 3 : 2)); height: 26; radius: Theme.radius; color: Qt.alpha(Theme.text, root.sortMode === modelData.mode ? 0.2 : 0.08)
                            Text { anchors.centerIn: parent; text: modelData.label; color: Theme.text; font.pixelSize: 11 }
                            MouseArea { anchors.fill: parent; onClicked: root.setSort(modelData.mode) }
                        }
                    }
                }
                Text { width: parent.width; text: root.error || ((root.pending ? LocaleState.tr("Confirmation · ","Confirm · ") : root.hovered ? LocaleState.tr("Figée au survol · ","Frozen while hovered · ") : "") + root.unit); color: Theme.textDim; font.pixelSize: 11; wrapMode: Text.WordWrap }
                ListView {
                    id: processList
                    width: parent.width; height: Math.max(0, popup.height - y - 20);clip: true
                    model: root.rows; boundsBehavior: Flickable.StopAtBounds
                    onMovementStarted:{root.pending=null;root.pendingAnchor=null;}
                    Controls.ScrollBar.vertical: Controls.ScrollBar {
                        width: 5; policy: Controls.ScrollBar.AsNeeded
                        contentItem: Rectangle {radius:3;color:Theme.accent;opacity:0.6}
                    }
                    delegate: Item {
                        id: processRow
                        required property var modelData
                        readonly property var processData: modelData
                        readonly property Item closeButton: stopButton
                        width: ListView.view.width; height: 34 * root.uiScale
                        Text {
                            id: nameText
                            anchors { left: parent.left; leftMargin:modelData.group?20:32;right:metric.left;rightMargin:12;verticalCenter:parent.verticalCenter }
                            text: modelData.name + (modelData.group ? " ("+modelData.children.length+")" : " · "+modelData.pid)
                            textFormat:Text.PlainText;elide:Text.ElideRight;color:Theme.text;font.pixelSize:12;font.bold:modelData.group===true
                        }
                        Text {visible:modelData.group===true;anchors.left:parent.left;anchors.verticalCenter:parent.verticalCenter;text:root.expanded[modelData.key]?"▾":"▸";color:Theme.accent;font.pixelSize:16}
                        MouseArea {
                            anchors.left:parent.left;anchors.right:metric.left;height:parent.height;enabled:modelData.group===true;cursorShape:Qt.PointingHandCursor
                            onClicked:{const next=Object.assign({},root.expanded);next[modelData.key]=!next[modelData.key];root.expanded=next;}
                        }
                        Text {id:metric;anchors {right:stopButton.left;rightMargin:10;verticalCenter:parent.verticalCenter}text:modelData.display;color:Theme.textDim;font.pixelSize:12}
                        Rectangle {
                            id: stopButton
                            anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                            width: 24; height: 24; radius: Theme.radius
                            color: Qt.alpha(Theme.danger, stopMouse.containsMouse ? 0.25 : 0.08);opacity:modelData.canStop?1:0.25
                            Text { anchors.centerIn: parent; text: "×"; color: Theme.danger; font.pixelSize: 18 }
                            MouseArea { id:stopMouse;anchors.fill:parent;hoverEnabled:true;enabled:modelData.canStop;cursorShape:Qt.PointingHandCursor;onClicked:root.requestStop(modelData,stopButton) }
                        }
                    }
                }
            }
            Rectangle {
                id: confirmation
                visible:root.pending!==null && root.pendingAnchor!==null
                z:10;width:Math.min(surface.width-20,350*root.uiScale);height:110
                x:Math.max(10,surface.width-width-10)
                y:{const scroll=processList.contentY;return root.pendingAnchor?Math.max(8,Math.min(surface.height-height-8,root.pendingAnchor.mapToItem(surface,0,0).y-height/2+12)):8;}
                radius:Theme.radius;color:Theme.bg;border.width:1;border.color:Theme.danger
                Column {
                    anchors.fill:parent;anchors.margins:10;spacing:8
                    Text {width:parent.width;text:root.pending?LocaleState.tr("Fermer ","Close ")+root.pending.name+(root.pending.group?" ("+root.pending.members.length+")":" · "+root.pending.pid)+" ?":"";color:Theme.text;font.pixelSize:12;elide:Text.ElideRight}
                    Text {width:parent.width;text:root.actionMessage;color:Theme.textDim;font.pixelSize:11;elide:Text.ElideRight}
                    Row {
                        spacing:8
                        Rectangle {id:cancelButton;width:100;height:28;radius:Theme.radius;color:Qt.alpha(Theme.text,0.08)
                            Text {anchors.centerIn:parent;text:LocaleState.tr("Annuler","Cancel");color:Theme.text;font.pixelSize:12}
                            MouseArea {anchors.fill:parent;onClicked:{forceDelay.stop();root.pending=null;root.pendingAnchor=null;}}
                        }
                        Rectangle {id:confirmButton;width:150;height:28;radius:Theme.radius;color:Qt.alpha(Theme.danger,0.18)
                            Text {anchors.centerIn:parent;text:root.canForce?LocaleState.tr("Forcer l’arrêt","Force stop"):LocaleState.tr("Fermer","Close");color:Theme.danger;font.pixelSize:12}
                            MouseArea {anchors.fill:parent;enabled:!actionWorker.running;onClicked:root.stopConfirmed(root.canForce)}
                        }
                    }
                }
            }
        }
    }
    IpcHandler {
        target: "processes"
        function close(): void { root.close(); }
        function diagnostic(): string {const buttons=[];
            for(let i=0;i<processList.count;i++){const row=processList.itemAtIndex(i);if(row&&row.y>=processList.contentY&&row.y+row.height<=processList.contentY+processList.height)buttons.push({pid:row.processData.pid,key:row.processData.key||"",group:row.processData.group===true,geometry:root.buttonRect(row.closeButton)});}
            return JSON.stringify({open:root.opened,kind:root.kind,contentY:processList.contentY,contentHeight:processList.contentHeight,listHeight:processList.height,frozen:root.frozen,sort:root.sortMode,pending:root.pending,processCount:root.processes.length,groupCount:root.groups.length,processes:root.processes.slice(0,20),groups:root.groups.slice(0,80).map(g=>({key:g.key,name:g.name,pid:g.pid,value:g.value,childCount:g.children.length,expanded:!!root.expanded[g.key]})),error:root.error,buttons:buttons,confirm:root.pending?root.buttonRect(confirmButton):null,cancel:root.pending?root.buttonRect(cancelButton):null});}
    }
}
