import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
Scope {
    id: root
    property string barPosition: "left"
    property real uiScale: 1
    property bool opened: false
    property string mode: "workspace"
    property Item targetItem: null
    property var snapshot: ({workspace:1,workspaceValue:1,window:{}})
    property int percent: 100
    onPercentChanged:slider.value=(percent-40)/60
    property int osdPercent:100
    property int osdWorkspace:0
    property bool osdAvailable:false
    property real osdDelta:0
    property int osdRequested:-1
    property string osdError:""
    function prepareOsd() {
        if(!osdAvailable && !osdQuery.running)osdQuery.running=true;
    }
    function adjustOsd(delta) {
        if(!osdAvailable){osdDelta+=delta;prepareOsd();return;}
        setOsdPercent(osdPercent+delta);
    }
    function setOsdPercent(value) {
        if(!osdAvailable){osdRequested=value;prepareOsd();return;}
        osdPercent=Math.max(40,Math.min(100,Math.round(value)));osdCommit.restart();
    }
    Connections {
        target:Hyprland
        function onRawEvent(event){if(["workspace","workspacev2","focusedmon"].includes(event.name))root.osdAvailable=false;}
    }
    Process {
        id:osdQuery;command:["python3",root.helper,"--status"]
        stdout:StdioCollector {onStreamFinished:{try{
            const d=JSON.parse(text);root.osdWorkspace=d.workspace;root.osdPercent=Math.round(d.workspaceValue*100);root.osdAvailable=d.workspace>0;root.osdError="";
            if(root.osdRequested>=0){const wanted=root.osdRequested;root.osdRequested=-1;root.setOsdPercent(wanted);}
            const delta=root.osdDelta;root.osdDelta=0;if(delta)root.adjustOsd(delta);
        }catch(e){root.osdAvailable=false;root.osdDelta=0;root.osdError=LocaleState.tr("Lecture impossible","Cannot read opacity");}}}
    }
    Timer {id:osdCommit;interval:80;onTriggered:if(root.osdAvailable)root.launch(["--workspace",String(root.osdWorkspace),"--set",String(root.osdPercent/100)])}
    property string error: ""
    property var queued: []
    readonly property string helper: Quickshell.env("HOME")+"/.config/hypr/scripts/window-opacity.py"
    readonly property var targetScreen: targetItem && targetItem.QsWindow.window ? targetItem.QsWindow.window.screen : Quickshell.screens.find(s=>Hyprland.focusedMonitor && s.name===Hyprland.focusedMonitor.name)||Quickshell.screens[0]
    readonly property bool valid: mode==="workspace" ? snapshot.workspace>0 : !!snapshot.window.address
    BarAnchor {id:placement;position:root.barPosition;target:root.targetItem;onInvalidated:root.close(false)}
    function show(scope,item) {
        if(opened && mode===scope && targetItem===(item||null)){close(true);return;}
        mode=scope==="window"?"window":"workspace";targetItem=item||null;error="";
        if(!query.running)query.running=true;
    }
    function launch(args) {
        if(writer.running){
            const pending=queued.slice(),last=pending.length?pending[pending.length-1]:null;
            const preview=args.includes("--preview")&&last&&last.includes("--preview");
            const sameWorkspace=last&&args[0]==="--workspace"&&last[0]==="--workspace"&&args[1]===last[1]&&!args.includes("--preview")&&!last.includes("--preview");
            if(preview||sameWorkspace)pending[pending.length-1]=args;else pending.push(args);
            queued=pending;return;
        }
        writer.command=["python3",helper].concat(args);writer.running=true;
    }
    function valueArgs() {
        return (mode==="window"?["--window",snapshot.window.address]:["--workspace",String(snapshot.workspace)]).concat(["--set",String(percent/100)]);
    }
    function preview(value) {percent=Math.max(40,Math.min(100,Math.round(value)));if(valid)previewTimer.restart();}
    function commit() {previewTimer.stop();if(valid)launch(valueArgs());}
    function close(accept) {if(!opened)return;opened=false;previewTimer.stop();if(accept)commit();else launch(["--cancel"]);}
    function resetAll() {osdCommit.stop();osdDelta=0;osdRequested=-1;previewTimer.stop();launch(["--reset-all"]);opened=false;}
    Process {
        id:query;command:["python3",root.helper,"--status"]
        stdout:StdioCollector {onStreamFinished:{try {const d=JSON.parse(text);root.snapshot=d;root.osdAvailable=false;root.percent=Math.round(100*(root.mode==="window"?d.window.value:d.workspaceValue));root.opened=true;Qt.callLater(()=>slider.forceActiveFocus());}catch(e){root.error=LocaleState.tr("Lecture impossible","Cannot read opacity");}}}
    }
    Timer {id:previewTimer;interval:40;onTriggered:if(root.valid)root.launch(root.valueArgs().concat(["--preview"]))}
    Process {
        id:writer
        stdout:StdioCollector {onStreamFinished:{try{const d=JSON.parse(text);if(d.success===false)root.error=d.error||LocaleState.tr("Réglage impossible","Cannot change opacity");}catch(e){root.error=LocaleState.tr("Réglage impossible","Cannot change opacity");}}}
        onExited:{if(root.queued.length){const next=root.queued[0];root.queued=root.queued.slice(1);root.launch(next);}}
    }
    PanelWindow {
        id:panel;screen:root.targetScreen
        anchors {left:true;top:true}
        implicitWidth:Math.min(440*root.uiScale,screen?screen.width-24:440)
        implicitHeight:230*root.uiScale
        readonly property point point:root.targetItem?placement.place(width,height,screen.width,screen.height,0,0):Qt.point((screen.width-width)/2,(screen.height-height)/2)
        margins.left:Math.max(8,point.x);margins.top:Math.max(8,point.y)
        visible:root.opened;color:"transparent";exclusionMode:ExclusionMode.Ignore
        WlrLayershell.namespace:"43pr-opacity";WlrLayershell.layer:WlrLayer.Overlay
        WlrLayershell.keyboardFocus:root.opened?WlrKeyboardFocus.Exclusive:WlrKeyboardFocus.None
        HyprlandFocusGrab {windows:[panel];active:panel.visible;onCleared:root.close(true)}
        Rectangle {
            anchors.fill:parent;radius:Theme.radius;color:Theme.bg;border.width:1;border.color:Theme.accent
            Keys.onPressed:event=>{if(event.key===Qt.Key_Escape){root.close(false);event.accepted=true;}else if(event.key===Qt.Key_Return||event.key===Qt.Key_Enter){root.close(true);event.accepted=true;}}
            Column {
                anchors.fill:parent;anchors.margins:18;spacing:14
                Text {width:parent.width;text:LocaleState.tr("OPACITÉ","OPACITY")+" — "+(root.mode==="window"?LocaleState.tr("FENÊTRE","WINDOW"):LocaleState.tr("BUREAU ","WORKSPACE ")+root.snapshot.workspace);color:Theme.text;font.family:Theme.fontFamily;font.bold:true;font.pixelSize:14}
                Text {width:parent.width;text:root.mode==="window"?(root.snapshot.window.title||root.snapshot.window.class||LocaleState.tr("Aucune fenêtre","No window")):LocaleState.tr("Les fenêtres verrouillées conservent leur valeur.","Locked windows keep their value.");color:Theme.textDim;font.pixelSize:11;elide:Text.ElideRight;textFormat:Text.PlainText}
                Slider {
                    id:slider;width:parent.width;enabled:root.valid
                    label:"";icon:"󰂵";displayText:root.percent+"%";displayFrom:40;displayTo:100;step:1/60
                    value:(root.percent-40)/60
                    onMoved:value=>root.preview(40+Math.round(value*60))
                    onCommitted:root.commit()
                }
                Row {
                    spacing:10
                    Rectangle {
                        width:180*root.uiScale;height:32;radius:Theme.radius;color:Qt.alpha(Theme.text,0.08)
                        Text {anchors.centerIn:parent;text:root.mode==="window"?LocaleState.tr("Suivre le bureau","Follow workspace"):LocaleState.tr("Déverrouiller tout","Unlock all");color:Theme.text;font.pixelSize:11}
                        MouseArea {anchors.fill:parent;enabled:root.valid;onClicked:{if(root.mode==="window"){root.previewTimerStop();root.launch(["--window",root.snapshot.window.address,"--reset"]);root.opened=false;}else root.resetAll();}}
                    }
                    Rectangle {
                        width:140*root.uiScale;height:32;radius:Theme.radius;color:Qt.alpha(Theme.accent,0.2)
                        Text {anchors.centerIn:parent;text:LocaleState.tr("Fermer","Close");color:Theme.text;font.pixelSize:11}
                        MouseArea {anchors.fill:parent;onClicked:root.close(true)}
                    }
                }
                Text {width:parent.width;text:root.error||(root.snapshot.window.fullscreen&&root.mode==="window"?LocaleState.tr("Le plein écran reste opaque.","Fullscreen stays opaque."):"");color:root.error?Theme.danger:Theme.textDim;font.pixelSize:11;wrapMode:Text.WordWrap}
            }
        }
    }
    function previewTimerStop(){previewTimer.stop();}
    IpcHandler {
        target:"opacity"
        function openControl(kind:string):void {root.show(kind,null);}
        function close():void {root.close(false);}
        function resetAll():void {root.resetAll();}
        function diagnostic():string {return JSON.stringify({open:root.opened,mode:root.mode,percent:root.percent,valid:root.valid,error:root.error,osdPercent:root.osdPercent,osdWorkspace:root.osdWorkspace,workspace:root.snapshot.workspace,window:root.snapshot.window.address,slider:(()=>{const p=slider.trackItem.mapToItem(panel.contentItem,0,0);return{x:p.x+panel.margins.left,y:p.y+panel.margins.top,width:slider.trackItem.width,height:slider.trackItem.height};})(),geometry:{x:panel.margins.left,y:panel.margins.top,width:panel.width,height:panel.height}});}
    }
}
