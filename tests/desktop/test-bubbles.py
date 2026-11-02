#!/usr/bin/env python3
"""Render the real Slot/Panel and module components offscreen; no live desktop."""
from pathlib import Path
import json, os, re, shutil, subprocess as sp, tempfile
from runtime import quickshell
from PIL import Image

q=Path(os.environ.get('PR43_TEST_QML',Path(__file__).resolve().parents[2]/'.config/quickshell'))
source=(q/'Bar.qml').read_text()
def section(start,end):
    return source[source.index(start):source.index(end,source.index(start))].replace('Theme.','theme.').replace('LocaleState.','locale.')
components=section('    component Interactive:','    // One of the three bar sections:')+section('    component Panel:','    // ───────────────────────── Bar helper components')+section('    component ResourceBadge:','    Component {\n        id: statsC')
properties='    property string checkKind:'+json.dumps(os.environ.get('PR43_BUBBLE_CHECK','all'))+'\n'+'\n'.join(line for line in source.splitlines() if re.match(r'    readonly property (int|real) (bubblePadding|panelThick|moduleGap):',line))
prefix='''import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import "bar-layout.js" as BarLayout
import "storage-modules.js" as StorageModules
Scope {
 id:root
 property var moduleSlots:[]
 property var bubblePanels:[]
 property var dragItem:null
 property var mergePanel:null
 property var previewCells:({})
 property string dragGroupId:""
 property int dragModuleRotation:0
 property bool dragMoved:false
 property bool editOpen:false
 property var editTarget:null
 property bool nativeInputBridge:false
 property bool nativeLeftHeld:false
 property bool discardReleaseClick:false
 property bool interactionTesting:true
 property var appDragItem:null
 property real ignoreClickUntil:0
 property bool opacityGesture:false
 property bool vertical:cfg.position==="left"||cfg.position==="right"
 property real barRadius:8
 property color borderColor:"blue"
 property bool joined:true
 property var sz:({icon:16*cfg.scale,taskIcon:18*cfg.scale,clock:12*cfg.scale})
 property int sizeIconGap:12
 property real iconYOffset:1
 property int index:0
 property var cases:[]
 property var comps:({icon:iconC,ws:workspaceC,cpu:resourceC,ram:ramC,gpu:gpuC})
 property var modeWidths:({})
 function s(n){return Math.round(n*cfg.scale);}
 function moduleIsVertical(item){let p=item;while(p){if(p.moduleSlotMarker)return p.moduleVertical;p=p.parent;}return vertical;}
 function moduleFactor(id){return cfg.factor*(cfg.factors[id]===undefined?1:cfg.factors[id]);}
 function moduleAlpha(id){return .7;}
 function groupAlpha(id){return .7;}
 function isOn(id){return true;}
 function modVisible(id){return true;}
 function sectionOf(id){return "group";}
 function cancelModuleDrag(){}
 function closeEditor(accept){}
 function openSettings(){}
 function openEditor(item,group,mode){}
 function selectPanelPointer(panel,point){}
 function beginModuleDrag(slot,point){}
 function updateModuleDrag(slot,point){}
 function finishModuleDrag(){}
 function finishGroupDrag(panel){}
 function beginGroupDrag(panel,point){}
 function updateGroupDrag(panel,point){}
 function queueSelectionWheel(delta,mods){return true;}
 QtObject {id:cfg
  property string position:"left"
  property int thickness:20
  property int taskIconSize:18
  property real scale:1
  property var factors:({})
  property real factor:1
  property string statsMode:"default"
  property real statsScale:1
  property bool statsBorder:true
  property bool statsPercent:false
  property int modPad:20
  property bool tooltipHints:false
  property bool border:false
  property var groupRotations:({})
  property var groupCells:({})
 }
 QtObject {id:theme;property color bg:"#101010";property color text:"white";property color textDim:"gray";property color accent:"blue";property color danger:"red";property int radius:8;property string iconFont:"JetBrainsMono Nerd Font"}
 QtObject {id:locale;function tr(fr,en){return en;}}
 component Tip:Item{property var target:null;property bool hot:false;property string title:"";property string hints:"";property bool suppressed:false;property bool shown:false}
 Component {id:iconC;Mod{text:"\\uDB81\\uDC25";baseSize:root.sz.icon}}
 Component {id:resourceC;ResourceBadge{label:"CPU";value:root.reading.value;warning:root.reading.warning}}
 Component {id:ramC;ResourceBadge{label:"RAM";value:root.reading.value;warning:root.reading.warning}}
 Component {id:gpuC;ResourceBadge{label:"GPU";value:root.reading.value;warning:root.reading.warning}}
 Component {id:workspaceC;Mod{text:"1"}}
 Component {id:diskC;ResourceBadge{label:"DSQ";value:root.reading.value;warning:root.reading.warning}}
 Component {id:tasksC;Mod{text:"3"}}
 Window {id:window;visible:true;width:900;height:850
  Text {id:nativeReference;visible:false;text:"\\uDB81\\uDC25";font.family:theme.iconFont;font.pixelSize:root.sz.icon;renderType:Text.NativeRendering}
  Panel {id:single;x:10;y:10;groupId:"free-single";model:["settings"]}
  Item {id:groupCapture;x:198.70125;y:98.744;width:Math.ceil(group.width)+4;height:Math.ceil(group.height)+4;z:group.z
   Panel {id:group;x:2;y:2;groupId:"free-group";model:["ws","cpu","ram","gpu","disk:fixture","power"]}
  }
  Panel {id:front;x:200;y:100;groupId:"free-front";model:["net"]}
 }
'''
suffix='''
 Component.onCompleted:{for(const position of ["left","top","right","bottom"])for(const factor of [.5,1,2])for(const scale of [1,1.5])for(const mode of ["default","compact"])cases.push({position:position,rotation:0,factor:factor,scale:scale,mode:mode});for(const rotation of [1,2,3])for(const mode of ["default","compact"])cases.push({position:"left",rotation:rotation,factor:1,scale:1,mode:mode});for(const position of ["left","top"])for(const mode of ["default","compact"])for(const reading of [{value:"0",warning:false},{value:"—",warning:false},{value:"100",warning:true}])cases.push({position:position,rotation:0,factor:1,scale:1,mode:mode,reading:reading});for(const position of ["left","top","right","bottom"])for(const scale of [1,1.5])for(const mode of ["default","compact"])cases.push({position:position,rotation:0,factor:1,scale:scale,mode:mode,outline:true});}
 property var reading:({value:"100",warning:false})
 property int phase:0
 Timer {id:bubbleTick;interval:20;repeat:true;running:true;onTriggered:{try{
  const c=root.cases[root.index];
  if(root.phase===0){groupCapture.x=198.70125;groupCapture.y=98.744;cfg.thickness=c.outline?16:20;cfg.factors=c.outline?({cpu:.9104,ram:.9105,gpu:.9105,"disk:fixture":.972,ws:.9104}):({});group.model=c.outline?["ws","cpu","ram","gpu","disk:fixture"]:["ws","cpu","ram","gpu","disk:fixture","power"];cfg.position=c.position;cfg.factor=c.factor;cfg.scale=c.scale;cfg.statsMode=c.mode;root.reading=c.reading||({value:"100",warning:false});let state={moduleGroups:[{id:"free-group",items:group.model},{id:"free-single",items:single.model},{id:"free-front",items:front.model}],groupCells:{},groupRotations:{}};for(let turn=0;turn<c.rotation;turn++)for(const id of ["free-group","free-single","free-front"])state=Object.assign({},state,BarLayout.rotateGroup(state,["ws","cpu","ram","gpu","disk:fixture","power","settings","net"],id,root.vertical));cfg.groupCells=state.groupCells;cfg.groupRotations=state.groupRotations;root.dragGroupId="";root.phase=1;return;}
  const slots=root.moduleSlots.filter(s=>group.model.includes(s.modelData));
  const cross=group.rotatedVertical?"width":"height",along=group.rotatedVertical?"height":"width",axis=group.rotatedVertical?"y":"x";
  const measured=Math.max(...slots.map(s=>s[cross]));
  for(const slot of slots.filter(s=>["cpu","ram","gpu","disk:fixture"].includes(s.modelData))){
   const resource=slot.item;
   const surface=resource.children.find(child=>(child.children||[]).some(row=>(row.children||[]).some(text=>text.text!==undefined)));
   const inset=root.s(1),insetX=resource.moduleVertical?inset:0,insetY=resource.moduleVertical?0:inset;
   if(!surface||Math.abs(surface.x-insetX)>.01||Math.abs(surface.y-insetY)>.01||Math.abs(surface.width-resource.width+2*insetX)>.01||Math.abs(surface.height-resource.height+2*insetY)>.01)throw Error("Resource paint loses its lateral bubble inset");
   const row=surface.children.find(child=>(child.children||[]).some(text=>text.text!==undefined));
   const bounds=row.mapToItem(resource,0,0,row.width,row.height),pad=Math.round(2*cfg.scale);
   if(bounds.x<pad-.05||bounds.y<pad-.05||bounds.x+bounds.width>resource.width-pad+.05||bounds.y+bounds.height>resource.height-pad+.05)throw Error("Enlarged resource text crosses its border "+JSON.stringify({case:c,bounds:bounds,width:resource.width,height:resource.height,pad:pad,scale:row.scale,rowWidth:row.width,implicitWidth:row.implicitWidth}));
   for(const text of row.children.filter(child=>child.text!==undefined))if(text.renderType!==Text.QtRendering||!text.antialiasing)throw Error("Resource text is not smoothly rendered");
   const value=row.children.find(child=>child.text===resource.value);
   const label=row.children.find(child=>child.text===resource.label);
   if(!value||!value.visible||String(value.color)!==String(resource.warning?theme.danger:theme.text))throw Error("Resource value/warning lost "+slot.modelData);
   if(!label||label.visible===resource.compact)throw Error("Resource label visibility changed "+slot.modelData);
   if(row.scale*resource.fontPx>root.sz.clock+.01)throw Error("Resource number exceeds clock size");
   const desired=root.sz.clock/resource.fontPx;
   if(row.implicitWidth*desired<=resource.width-2*pad && row.implicitHeight*desired<=resource.height-2*pad && Math.abs(row.scale-desired)>.01)throw Error("Resource number misses clock size despite enough room");
  }

  const shape=Object.assign({},c);delete shape.mode;
  const key=JSON.stringify(shape),widths={};
  for(const slot of slots.filter(s=>["cpu","ram","gpu","disk:fixture"].includes(s.modelData)))widths[slot.modelData]=slot.width;
  if(root.modeWidths[key])for(const id in widths)if(Math.abs(widths[id]-root.modeWidths[key][id])>.01)throw Error("Default/compact resource width changed "+id+" "+JSON.stringify(c)+" "+widths[id]+" vs "+root.modeWidths[key][id]);
  root.modeWidths[key]=widths;
  const region=group.inputRegion;
  for(const slot of slots)for(const fx of [.05,.95])for(const fy of [.05,.95]){
   const point=slot.mapToItem(window.contentItem,slot.width*fx,slot.height*fy);
   const x=Math.max(Math.ceil(slot.mapToItem(window.contentItem,0,0).x),Math.min(Math.ceil(slot.mapToItem(window.contentItem,slot.width,0).x)-1,Math.round(point.x)));
   const y=Math.max(Math.ceil(slot.mapToItem(window.contentItem,0,0).y),Math.min(Math.ceil(slot.mapToItem(window.contentItem,0,slot.height).y)-1,Math.round(point.y)));
   if(x<region.x||x>=region.x+region.width||y<region.y||y>=region.y+region.height)throw Error("Input region clips a module pixel "+JSON.stringify(c)+" "+x+","+y+" region "+region.x+","+region.y+" "+region.width+"x"+region.height);
  }
  if(c.reading){
   const resource=slots.find(s=>s.modelData==="cpu").item;
   const texts=[];function visit(item){if(!item.visible)return;if(item.text!==undefined)texts.push(item);for(const child of item.children||[])visit(child);}visit(resource);
   const value=texts.find(t=>t.text===c.reading.value);if(!value)throw Error("Resource reading not rendered");
   if(String(value.color)!==String(c.reading.warning?theme.danger:theme.text))throw Error("Warning colour not rendered");
   if(texts.some(t=>t.text==="CPU")!==(c.mode==="default"))throw Error("Compact/default label visibility changed");
  }
  if((root.checkKind==="all"||root.checkKind==="width")&&Math.abs(group[cross]-measured)>.01)throw Error("Bubble adds transverse padding "+JSON.stringify(c)+" "+group[cross]+" vs "+measured);
  const one=root.moduleSlots.find(s=>s.modelData==="settings");
  if(root.checkKind==="all"||root.checkKind==="native"){
   const expectedWidth=one.moduleVertical?root.panelThick:nativeReference.implicitWidth+cfg.modPad;
   const expectedHeight=one.moduleVertical?Math.max(20,nativeReference.implicitHeight+8):Math.max(root.panelThick-2,nativeReference.implicitHeight);
   if(Math.abs(one.item.implicitWidth-expectedWidth)>.01||Math.abs(one.item.implicitHeight-expectedHeight)>.01)throw Error("Native icon hit-box metrics changed "+JSON.stringify(c)+" "+one.item.implicitWidth+"x"+one.item.implicitHeight+" vs "+expectedWidth+"x"+expectedHeight);
  }
  if((root.checkKind==="all"||root.checkKind==="width")&&Math.abs(single[cross]-one[cross])>.01)throw Error("Single module adds transverse padding");
  const sorted=slots.slice().sort((a,b)=>a[axis]-b[axis]);
  for(let i=1;i<sorted.length;i++){const gap=sorted[i][axis]-sorted[i-1][axis]-sorted[i-1][along];if((root.checkKind==="all"||root.checkKind==="gap")&&Math.abs(gap-Math.round(2*cfg.scale))>.01)throw Error("Native resource gap changed "+gap+" "+JSON.stringify(c));}
  root.dragGroupId="free-group";
  if((root.checkKind==="all"||root.checkKind==="stack")&&!(group.z>front.z))throw Error("Dragged group below another bubble");
  root.dragGroupId="";
  if(group.z!==front.z)throw Error("Group retained elevated stacking after release");
  if(c.outline){
   const slot=slots.find(s=>s.modelData==="disk:fixture"),r=slot.mapToItem(group,0,0,slot.width,slot.height);
   console.log("OUTLINE",JSON.stringify({index:root.index,vertical:slot.moduleVertical,factor:slot.sizeFactor,offsetX:group.x,offsetY:group.y,rect:{x:r.x,y:r.y,width:r.width,height:r.height},width:group.width,height:group.height,case:c}));
   bubbleTick.stop();groupCapture.grabToImage(result=>{result.saveToFile(Qt.resolvedUrl("outline-"+root.index+".png").toString().replace("file://",""));root.index++;root.phase=0;if(root.index===root.cases.length){console.log("PASS bubble geometry/spacing/stacking",root.index);Qt.quit();}else bubbleTick.start();},Qt.size(groupCapture.width,groupCapture.height));return;
  }
  root.index++;root.phase=0;if(root.index===root.cases.length){console.log("PASS bubble geometry/spacing/stacking",root.index);Qt.quit();}
 }catch(error){console.error("FAIL",error);Qt.quit();}}}
}
'''
with tempfile.TemporaryDirectory(prefix='43pr-bubble-') as directory:
    folder=Path(directory)
    for file in ['BarSurface.qml','scripts/bar-layout.js','scripts/storage-modules.js']:
        shutil.copy2(q/file,folder/Path(file).name)
    (folder/'shell.qml').write_text(prefix+properties+'\n'+components+suffix)
    env=dict(os.environ,QT_QPA_PLATFORM='offscreen');env.pop('WAYLAND_DISPLAY',None)
    result=sp.run([quickshell(),'-p',str(folder/'shell.qml')],env=env,capture_output=True,text=True,timeout=20)
    log=result.stdout+result.stderr
    assert result.returncode==0 and 'PASS bubble geometry/spacing/stacking 82' in log and 'FAIL' not in log,log
    rendered=[json.loads(line.split('OUTLINE ',1)[1]) for line in log.splitlines() if 'OUTLINE ' in line]
    assert len(rendered)==16,('missing mixed-scale outline renders',len(rendered))
    for item in rendered:
        im=Image.open(folder/f"outline-{item['index']}.png").convert('RGBA');r=item['rect']
        # Canvas textures round fractional extents to integer pixels. The
        # integer capture wrapper keeps both ends, unlike grabbing a partial item.
        if item['vertical']:
            centre=int(item['offsetY']+r['y']+r['height']/2)
            positions=[int(item['offsetX']),int(item['offsetX'])+int(item['width']+.5)-1]
            pixels=[im.getpixel((x,centre)) for x in positions]
        else:
            centre=int(item['offsetX']+r['x']+r['width']/2)
            positions=[int(item['offsetY']),int(item['offsetY'])+int(item['height']+.5)-1]
            pixels=[im.getpixel((centre,y)) for y in positions]
        assert all(max(abs(channel-16) for channel in pixel[:3])<=12 and pixel[3]>=20 for pixel in pixels),('widest disk badge covers bubble lateral background',item['case'],pixels)
        inset=int(item['case']['scale']+.5)*item['factor'];stroke=item['factor']
        offset=item['offsetX'] if item['vertical'] else item['offsetY'];extent=item['width'] if item['vertical'] else item['height']
        positions=[int(offset+inset+stroke/2),int(offset+extent-inset-stroke/2)]
        strokes=[im.getpixel((x,centre)) for x in positions] if item['vertical'] else [im.getpixel((centre,y)) for y in positions]
        assert all(max(pixel[:3])>=32 for pixel in strokes),('badge outline disappeared inside its lateral inset',item['case'],strokes)
    print('PASS: 82 native bubble geometries; four positions/rotations, 0.5–2 sizes, 1–1.5 scales; native icon metrics, equal compact/default widths for CPU/RAM/GPU/DSQ, zero/unknown/warning resource values, single/group width, 2px native resource spacing, drag stacking and release; 16 mixed-zoom rendered pixel checks preserve both lateral bubble edges')
