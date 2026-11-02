#!/usr/bin/env python3
"""Click the production workspace delegate, including a detached persistent desktop."""
from pathlib import Path
import os, subprocess as sp, tempfile
from runtime import quickshell
q=Path(os.environ.get('PR43_TEST_QML',Path(__file__).resolve().parents[2]/'.config/quickshell'))
source=(q/'Bar.qml').read_text()
component=source[source.index('    Component {\n        id: wsC'):source.index('    ProcessListPopup')].replace('Hyprland.','hyprland.').replace('Theme.','theme.')
qml='''import QtQuick
import QtQuick.Layouts
import QtTest
import Quickshell
Scope {
 id:root
 property bool interactionTesting:false
 property bool discardReleaseClick:false
 property bool manipulating:false
 property double ignoreClickUntil:0
 property var dragItem:null
 property bool nativeLeftHeld:false
 property string dragGroupId:""
 property var commands:[]
 property int settingsOpened:0
 property int index:0
 function moduleIsVertical(item){return cfg.vertical;}
 function openSettings(){settingsOpened++;}
 function beginModuleDrag(slot,point){dragItem=slot;}
 function finishModuleDrag(){dragItem=null;discardReleaseClick=true;}
 function cancelModuleDrag(){dragItem=null;}
 function updateModuleDrag(slot,point){}
 function queueSelectionWheel(delta,mods){}
 function run(command){commands.push(command);}
 QtObject{id:cfg;property int wsDot:12;property int wsGap:4;property bool tooltipHints:false;property bool wsScroll:true;property bool vertical:false}
 QtObject{id:theme;property color danger:"red";property color accent:"blue";property color accent2:"green";property color textFaint:"white";property int animMed:0}
 QtObject{id:hyprland
  property var monitors:({values:[{id:7,name:"TEST-7"},{id:8,name:"TEST-8"}]})
  property var focusedMonitor:({id:7,name:"TEST-7"})
  property var workspaces:[{id:1,monitor:{id:7,name:"TEST-7"},lastIpcObject:{monitorID:null},focused:false,urgent:false},{id:5,monitor:{id:8,name:"TEST-8"},focused:true,urgent:false}]
  function dispatch(command){root.commands.push(command);}
 }
 component Lane:GridLayout{property int gap:4;columns:cfg.vertical?1:10;rowSpacing:gap;columnSpacing:gap}
 component Tip:Item{property bool suppressed:false;property bool shown:false;property bool hot:false;property string title:"";property string hints:""}
 property int panelThick:24
 property string wsHints:""
 Window{id:win;visible:true;width:300;height:300
  Item{id:slot;property bool moduleSlotMarker:true;width:200;height:200
   Loader{id:loader;sourceComponent:wsC;width:180;height:160}
  }
  TestCase{id:events;when:false}
 }
 COMPONENT
 Timer{id:tick;interval:40;repeat:true;running:true;onTriggered:{tick.stop();try{
  const lane=loader.item.children[0],repeater=lane.children.find(c=>c.itemAt!==undefined);
  const first=repeater.itemAt(0),second=repeater.itemAt(1);
  function click(target,button){root.commands=[];events.mouseClick(target,target.width/2,target.height/2,button||Qt.LeftButton);}
  if(root.index===0){
   click(first);if(root.commands.length!==2||!root.commands[0].includes("workspace.move")||!root.commands[0].includes('"TEST-7"')||!root.commands[0].includes("workspace = 1")||!root.commands[1].includes("focus({ workspace = 1"))throw Error("Detached workspace 1 must attach before focus: "+JSON.stringify(root.commands));
  }else if(root.index===1){
   click(second);if(root.commands.length!==1||!root.commands[0].includes("workspace = 5"))throw Error("Attached workspace must focus without migration");
  }else if(root.index===2){
   hyprland.focusedMonitor=null;click(first);if(root.commands.length)throw Error("No monitor: invalid dispatch");hyprland.focusedMonitor={id:7,name:"TEST-7"};
  }else if(root.index===3){
   click(first,Qt.RightButton);if(root.commands.length||root.settingsOpened!==1)throw Error("Right click must open settings only");
  }else if(root.index<=7){
   const guard=["interactionTesting","discardReleaseClick","manipulating","ignoreClickUntil"][root.index-4];root[guard]=guard==="ignoreClickUntil"?Date.now()+1000:true;click(first);if(root.commands.length)throw Error("Blocked click dispatched: "+guard);root[guard]=guard==="ignoreClickUntil"?0:false;
  }else if(root.index===8){cfg.vertical=true;
  }else if(root.index===9){click(first);if(root.commands.length!==2)throw Error("Vertical click missed workspace");
  }else if(root.index===10){
   hyprland.workspaces=[{id:1,monitor:{id:-1,name:"?"},lastIpcObject:{},focused:false,urgent:false}];
  }else if(root.index===11){click(repeater.itemAt(0));if(root.commands.length!==2)throw Error("Stale output placeholder was not recovered");
  }else if(root.index===12){
   root.commands=[];events.mousePress(repeater.itemAt(0),first.width/2,first.height/2,Qt.LeftButton);events.wait(500);events.mouseRelease(repeater.itemAt(0),first.width/2,first.height/2,Qt.LeftButton);if(root.commands.length||root.dragItem)throw Error("Long press activated workspace or retained capture");
  }else{console.log("PASS workspace clicks 13: detached/attached/no-monitor/right-click/guards/vertical/drag release");Qt.quit();return;}
  root.index++;tick.start();
 }catch(error){console.error("FAIL",error);Qt.quit();}}}
}
'''.replace(' COMPONENT',component)
with tempfile.TemporaryDirectory(prefix='43pr-workspace-') as directory:
 p=Path(directory)/'shell.qml';p.write_text(qml)
 env=dict(os.environ,QT_QPA_PLATFORM='offscreen');env.pop('WAYLAND_DISPLAY',None)
 result=sp.run([quickshell(),'-p',str(p)],env=env,capture_output=True,text=True,timeout=10)
 log=result.stdout+result.stderr
 assert result.returncode==0 and 'PASS workspace clicks 13:' in log and 'FAIL' not in log,log
 print('PASS: 13 native workspace click cases; production delegate, detached desktop 1, normal multi-monitor focus, no screen, settings, input guards, vertical and drag release')
