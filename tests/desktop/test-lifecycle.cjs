const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');const source=fs.readFileSync(path.join(__dirname,'../../.config/quickshell/Bar.qml'),'utf8');
function body(name){const start=source.indexOf('function '+name+'('),brace=source.indexOf('{',start);let n=1,i=brace+1;while(n){if(source[i]==='{')n++;if(source[i]==='}')n--;i++;}return source.slice(brace+1,i-1);}
const c={Date,Math,Number,nativeLeftHeld:false,dragItem:{},dragGroupId:'',dragSavedAppearance:{},dragSavedCells:null,opacityGesture:true,cfg:{},releaseClickTimer:{restart(){}},selectionOsdTimer:{stop(){}},restoreAppearance(){}};c.root=c;vm.createContext(c);vm.runInContext('function cancelModuleDrag(commit){'+body('cancelModuleDrag')+'}\ncancelModuleDrag(false)',c);assert.equal(c.opacityGesture,false);assert.equal(c.dragItem,null);
for(const stale of [false,true]){
 const c={Qt:{},Number,Math,editOpen:false,dragItem:null,dragGroupId:'',opacityGesture:stale,interactionTesting:false,nativeInputToken:3,closedNativeToken:-1,nativePressSelection:{},selected:0,resized:0};c.root=c;c.selectPointerTarget=()=>{c.selected++;c.dragItem={};return true};c.adjustSelection=()=>c.resized++;vm.createContext(c);vm.runInContext('function nativeInput(data){'+body('nativeInput')+'}\nnativeInput("wheel,3,10,10,120")',c);assert.equal(c.selected,1);assert.equal(c.resized,1);
}
for(const name of ['beginModuleDrag','beginGroupDrag']){
 const c={nativeInputBridge:true,nativeLeftHeld:false};c.root=c;vm.createContext(c);vm.runInContext('function '+name+'(slot,point){'+body(name)+'}\n'+name+'({},{});',c);assert.equal(c.dragItem,undefined);
}
console.log('PASS cancellation clears size mode; a new quick wheel always acquires its press target');
