from runtime import quickshell
#!/usr/bin/env python3
"""Real QML pointer events with simulated battery/disabled states; no desktop input."""
from pathlib import Path
import tempfile,os,subprocess as sp
root=Path(__file__).resolve().parents[2];source=(root/'.config/quickshell/Bar.qml').read_text()
def section(start,end):return source[source.index(start):source.index(end,source.index(start))].replace('Theme.','theme.').replace('LocaleState.','locale.')
components=section('    component Interactive:','    component Mod:')+section('    component Mod:','    component Slot:')+section('    Component {\n        id: batteryC','    // ───────────────────────── The bar')
prefix='''import QtQuick
import QtQuick.Layouts
import Quickshell
import QtTest
Scope {
 id:root
 property var dragItem:null
 property var appDragItem:null
 property bool appDragNative:false
 property bool nativeInputBridge:false
 property bool nativeLeftHeld:false
 property bool discardReleaseClick:false
 property bool interactionTesting:true
 property real ignoreClickUntil:0
 property bool editOpen:false
 property bool vertical:true
 property var sz:({icon:16})
 property int panelThick:26
 property int sizeIconGap:12
 property real iconYOffset:1
 property int resizes:0
 property int index:0
 property int phase:0
 property var cases:[]
 property bool batLow:false
 property bool batCharging:false
 property string batIcon:"\\uf244"
 property string batTip:"Battery fixture"
 readonly property bool manipulating:dragItem!==null
 function moduleIsVertical(item){return vertical;}
 function beginModuleDrag(slot,point){dragItem=slot;}
 function finishModuleDrag(){dragItem=null;}
 function cancelModuleDrag(){dragItem=null;}
 function updateModuleDrag(slot,point){}
 function queueSelectionWheel(delta,modifiers){resizes++;return true;}
 function openSettings(){}
 function openEditor(item,group,mode){}
 function beginAppDrag(item,point){}
 function s(v){return v;}
 QtObject{id:cfg;property bool tooltipHints:false;property int modPad:20}
 QtObject{id:locale;function tr(fr,en){return en;}}
 QtObject{id:theme;property real radius:10;property color bg:"#101010";property color text:"white";property color textDim:"gray";property color accent:"blue";property color danger:"red";property string iconFont:"monospace"}
 component Tip:Item{property bool hot:false;property string title:"";property string hints:"";property bool suppressed:false;property bool shown:false;property var target:null}
'''
suffix='''
 Window {visible:true;width:300;height:300
  Item {id:slot;property bool moduleSlotMarker:true;width:loader.implicitWidth;height:loader.implicitHeight
   Loader {id:loader;sourceComponent:batteryC;onLoaded:item.disabled=false}
  }
 }
 TestCase {id:events;when:false}
 Component.onCompleted:{for(const vertical of [false,true])for(const low of [false,true])for(const charging of [false,true])for(const disabled of [false,true])for(const size of [8,16,32])cases.push({vertical:vertical,low:low,charging:charging,disabled:disabled,size:size});}
 Timer {id:tick;interval:35;running:true;repeat:true;onTriggered:{
  try{
   const c=root.cases[root.index];
   if(root.phase===0){root.vertical=c.vertical;root.batLow=c.low;root.batCharging=c.charging;root.sz=({icon:c.size});loader.item.disabled=c.disabled;root.phase=1;return;}
   for(const p of [[.5,.5],[.1,.1],[.9,.1],[.1,.9],[.9,.9]]){
    const before=root.resizes,x=slot.width*p[0],y=slot.height*p[1];events.mousePress(slot,x,y,Qt.LeftButton,Qt.NoModifier,1);events.mouseWheel(slot,x,y,0,120,Qt.LeftButton,Qt.NoModifier,1);events.mouseRelease(slot,x,y,Qt.LeftButton,Qt.NoModifier,1);
    if(root.resizes!==before+1||root.manipulating)throw Error("State failed "+JSON.stringify(c));
   }
   root.phase=0;root.index++;if(root.index===root.cases.length){console.log("PASS simulated component states",root.index,"points",root.index*5);Qt.quit();}
  }catch(error){console.error("FAIL",error);Qt.quit();}
 }}
}
'''
with tempfile.TemporaryDirectory(prefix='43pr-component-states-') as d:
 p=Path(d)/'shell.qml';p.write_text(prefix+components+suffix);env=dict(os.environ,QT_QPA_PLATFORM='offscreen');env.pop('WAYLAND_DISPLAY',None)
 executable=quickshell();r=sp.run([str(executable),'-p',str(p)],env=env,capture_output=True,text=True,timeout=20);log=r.stdout+r.stderr
 assert 'PASS simulated component states 48 points 240' in log and 'FAIL' not in log,log
 print('PASS: 48 simulated battery/disabled/charging/low/orientation/size states, 240 actual QML pointer points')
