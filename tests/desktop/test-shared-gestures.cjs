// Exercise the production input controller and layout rules. Only compositor
// geometry, timers and output/persistence boundaries are supplied by the fixture.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const q=process.env.PR43_TEST_QML||path.join(__dirname,'../../.config/quickshell');
const source=fs.readFileSync(path.join(q,'Bar.qml'),'utf8');
function body(name){const start=source.indexOf('function '+name+'(');assert(start>=0,name);const brace=source.indexOf('{',start);let n=1,i=brace+1;while(n&&i<source.length){if(source[i]==='{')n++;if(source[i]==='}')n--;i++;}return source.slice(brace+1,i-1);}
const modules=['cpu','ram','gpu','disk:one','ws','tasks','minigroup-work','media','brightness','opacity','volume','battery','net','notif','wall','settings','power','clock'];
function fixture(){
 const window={screen:{x:0,y:0,width:2000,height:1000},contentItem:{},width:2000,height:1000};
 const slots=modules.map((id,i)=>({modelData:id,visible:true,hostWindow:window,width:28,height:28,x:20+i*50,y:100,mapToItem:(target,x,y)=>({x:20+i*50+x,y:100+y})}));
 const panel={groupId:'free-shared',hostWindow:window,visible:true,width:1000,height:100,model:modules,x:0,y:80,mapToItem:(target,x,y)=>({x,y:y+80})};
 const c={Date,Math,Number,Qt:{point:(x,y)=>({x,y}),NoModifier:0},moduleIds:modules,moduleSlots:slots,bubblePanels:[panel],calendarControllers:[],cfg:{moduleScale:{},moduleZoom:1,groupOpacity:{},moduleOpacity:{},groupCells:{},groupRotations:{},position:'left'},dragItem:null,dragGroupId:'',dragWindow:null,dragMoved:false,dragModuleRotation:0,dragSavedCells:null,dragSavedAppearance:null,dragSavedRotations:null,nativeInputBridge:true,nativeLeftHeld:false,nativeInputToken:0,closedNativeToken:-1,editOpen:false,interactionTesting:false,opacityGesture:false,ignoreClickUntil:0,gestureMode:'',releaseCount:0,saveCount:0,selectionSizing:false,selectedScale:1};
 c.root=c;Object.defineProperty(c,'vertical',{get:()=>['left','right'].includes(c.cfg.position)});c.layoutGroups=[{id:panel.groupId,items:modules}];c.taskRect=item=>({x:item.x,y:item.y,width:item.width,height:item.height});
 c.cfgFile={waitForJob(){}};c.processPopup={close(){}};c.notificationController=null;c.powerController=null;c.volumeController=null;
 c.releaseClickTimer={restart(){c.releaseCount++},stop(){}};c.selectionOsdTimer={restart(){},stop(){}};c.save=()=>c.saveCount++;
 c.sectionOf=()=>panel.groupId;c.rotateDrag=()=>{};
 vm.createContext(c);vm.runInContext('const BarLayout={};',c);
 const layout=vm.createContext({});vm.runInContext(fs.readFileSync(path.join(q,'scripts/bar-layout.js'),'utf8').replace(/^\.pragma.*\n/,''),layout);c.BarLayout=layout;
 const names=['flushSelectionWheel','hitAt','selectionAt','selectPointerTarget','beginModuleDrag','beginGroupDrag','recordDragTargets','rememberDrag','appearanceSnapshot','restoreAppearance','adjustSelection','cancelModuleDrag','nativeInput','releaseInputAfterDisconnect','finishModuleDrag','finishGroupDrag'];
 vm.runInContext(names.map(name=>'function '+name+'('+({flushSelectionWheel:'',hitAt:'x,y',selectionAt:'x,y',selectPointerTarget:'hit',beginModuleDrag:'slot, point',beginGroupDrag:'panel, point',recordDragTargets:'window',rememberDrag:'',appearanceSnapshot:'',restoreAppearance:'state',adjustSelection:'delta, modifiers',cancelModuleDrag:'commit',nativeInput:'data',releaseInputAfterDisconnect:'',finishModuleDrag:'',finishGroupDrag:'panel'}[name])+'){'+body(name)+'}').join('\n'),c);
 // `const BarLayout` would shadow the injected production rule object.
 vm.runInContext('Object.assign(BarLayout, globalThis.BarLayout);',c);
 return c;
}
let cases=0;
for(const id of modules)for(const initial of [.5,1,2]){
 const c=fixture(),slot=c.moduleSlots.find(s=>s.modelData===id),x=slot.x+14,y=114;c.cfg.moduleScale={[id]:initial};
 c.nativeInput(`press,17,${x},${y},0`);c.nativeInput(`wheel,17,${x},${y},120`);
 assert.equal(c.dragItem.modelData,id);assert(Math.abs(c.cfg.moduleScale[id]-Math.min(2,initial+.05))<1e-8,id);
 // Continuation outside every module and near another value control remains owned.
 c.nativeInput('wheel,17,1990,990,-120');assert.equal(c.dragItem.modelData,id);
 const expected=Math.max(.5,Math.min(2,initial+.05)-.05);assert(Math.abs(c.cfg.moduleScale[id]-expected)<1e-8);
 for(const other of modules.filter(m=>m!==id))assert.equal(c.cfg.moduleScale[other],undefined,'unrelated consumer changed');
 // Escape-style cancellation restores the exact original values and closes token.
 c.cancelModuleDrag(false);assert.equal(c.cfg.moduleScale[id],initial);assert.equal(c.dragItem,null);assert.equal(c.opacityGesture,false);
 c.nativeInput('wheel,17,1990,990,120');assert.equal(c.cfg.moduleScale[id],initial,'cancelled token reopened');
 c.nativeInput('release,17,1990,990,0');assert.equal(c.nativeLeftHeld,false);
 // A new press must recover immediately; a stale event cannot resize it.
 c.nativeInput(`press,18,${x},${y},0`);c.nativeInput(`wheel,17,${x},${y},120`);assert.equal(c.cfg.moduleScale[id],initial);
 c.nativeInput(`wheel,18,${x},${y},-120`);c.nativeInput('release,18,1990,990,0');
 assert(Math.abs(c.cfg.moduleScale[id]-Math.max(.5,initial-.05))<1e-8);assert.equal(c.dragItem,null);assert.equal(c.nativeLeftHeld,false);cases++;
}
for(const position of ['left','top','right','bottom']){
 const c=fixture();c.cfg.position=position;c.cfg.moduleScale={cpu:.75,ram:1.25};
 c.nativeInput('press,30,2,82,0');c.nativeInput('wheel,30,2,82,120');assert.equal(c.dragGroupId,'free-shared');
 const before=c.cfg.moduleScale.cpu/.75;assert(Math.abs(c.cfg.moduleScale.ram/1.25-before)<.0002);
 c.nativeInput('release,30,1990,990,0');assert.equal(c.dragGroupId,'');assert.equal(c.nativeLeftHeld,false);cases++;
}
{
 const c=fixture();c.nativeInput('press,40,34,114,0');c.nativeInput('wheel,40,34,114,120');const before=c.cfg.moduleScale.cpu;
 c.gestureMode='move';c.nativeInput('wheel,40,34,114,120');assert.equal(c.cfg.moduleScale.cpu,before,'wheel took over an existing move gesture');cases++;
}
console.log(`PASS shared production controller: ${cases} cases; 18 consumers, limits, continuation, cancellation, stale/new tokens, group ratios and exclusivity`);
