import QtQuick
import Quickshell
import Quickshell.Io
import "../"
Item {
    id:page
    implicitHeight:content.implicitHeight
    property real marginLeft:0
    property real marginRight:10
    property real marginTop:0
    property real marginBottom:0
    property var opacityController:null
    onOpacityControllerChanged:if(opacityController)opacityController.prepareOsd()
    property int moduleZoomPercent:100
    property int pendingModuleZoom:-1
    function requestModuleZoom(percent){moduleZoomPercent=Math.max(50,Math.min(200,Math.round(percent)));pendingModuleZoom=moduleZoomPercent;if(!zoomApply.running)zoomApply.start();}
    FileView {id:barZoomFile;path:Quickshell.env("HOME")+"/.config/quickshell/state"+"/bar-state.json";watchChanges:true;onFileChanged:reload();onLoaded:{try{if(page.pendingModuleZoom<0&&!zoomWriter.running){page.moduleZoomPercent=Math.round((JSON.parse(text()).moduleZoom??1)*100);zoomRow.control.value=(page.moduleZoomPercent-50)/150;}}catch(e){}}}
    Timer {id:zoomApply;interval:60;onTriggered:{if(zoomWriter.running){restart();return;}if(page.pendingModuleZoom<0)return;zoomWriter.command=["qs","ipc","-p",Quickshell.env("HOME")+"/.config/quickshell","call","bar","setZoomPercent",String(page.pendingModuleZoom)];page.pendingModuleZoom=-1;zoomWriter.running=true;}}
    Process {id:zoomWriter;onExited:if(page.pendingModuleZoom>=0)zoomApply.restart()}
    function zoomDiagnostic(){const p=zoomRow.control.trackItem.mapToGlobal(0,0);return{percent:moduleZoomPercent,x:p.x,y:p.y,width:zoomRow.control.trackItem.width,height:zoomRow.control.trackItem.height};}
    Connections {target:page.opacityController
        function onOsdAvailableChanged(){if(page.opacityController&&!page.opacityController.osdAvailable)page.opacityController.prepareOsd();}
        function onOsdPercentChanged(){opacityRow.control.value=(page.opacityController.osdPercent-40)/60;}
    }
    component DisplayAdjustment:Column {
        id:row
        required property string title
        required property string glyph
        property int minimum:0
        property int maximum:100
        property int percent:100
        property bool available:true
        property bool resettable:false
        property int resetPercent:100
        readonly property alias control:slider
        signal adjusted(int percent)
        width:parent.width;spacing:8
        onPercentChanged:slider.value=(percent-minimum)/(maximum-minimum)
        Text {text:row.title;color:Theme.text;font.family:Theme.fontFamily;font.pixelSize:Theme.textSizeGroup}
        Slider {id:slider;width:parent.width;icon:row.glyph;enabled:row.available;opacity:enabled?1:0.45
            value:(row.percent-row.minimum)/(row.maximum-row.minimum);step:1/(row.maximum-row.minimum)
            resettable:row.resettable;resetValue:(row.resetPercent-row.minimum)/(row.maximum-row.minimum)
            displayFrom:row.minimum;displayTo:row.maximum;displayText:row.available?row.percent+"%":"—"
            onMoved:v=>row.adjusted(row.minimum+Math.round(v*(row.maximum-row.minimum)))
        }
    }
    Column {id:content;width:parent.width;spacing:14
        Rectangle {width:parent.width;height:rows.implicitHeight+28;radius:Theme.radius;color:"transparent";border.width:1;border.color:Theme.border
            Column {id:rows;anchors.left:parent.left;anchors.right:parent.right;anchors.top:parent.top;anchors.margins:14;spacing:16
                DisplayAdjustment {title:LocaleState.tr("LUMINOSITÉ","BRIGHTNESS");glyph:"󰃠";available:BrightnessState.available;percent:Math.round(BrightnessState.value*100);onAdjusted:p=>BrightnessState.set(p)}
                DisplayAdjustment {id:zoomRow;title:LocaleState.tr("ZOOM DES MODULES","MODULE ZOOM");glyph:"󰍉";minimum:50;maximum:200;percent:page.moduleZoomPercent;resettable:true;onAdjusted:p=>page.requestModuleZoom(p)}
                DisplayAdjustment {id:opacityRow;title:LocaleState.tr("OPACITÉ DU BUREAU","WORKSPACE OPACITY");glyph:"󰗌";minimum:40;available:!!page.opacityController&&page.opacityController.osdAvailable;percent:page.opacityController?page.opacityController.osdPercent:100;resettable:true;resetPercent:40;onAdjusted:p=>{if(page.opacityController)page.opacityController.setOsdPercent(p);}}
            }
            Component.onCompleted:BrightnessState.refresh()
        }
        Rectangle {width:parent.width;height:36;radius:Theme.radius;color:Theme.alpha(Theme.accent,0.1);border.width:1;border.color:Theme.border
            Text {anchors.centerIn:parent;text:LocaleState.tr("Rétablir les opacités des modules","Reset module opacities");color:Theme.text;font.family:Theme.fontFamily;font.pixelSize:Theme.textSizeSmall}
            MouseArea {anchors.fill:parent;onClicked:Quickshell.execDetached(["qs","ipc","call","bar","resetOpacities"])}
        }
    }
}
