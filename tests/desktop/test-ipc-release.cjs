// Execute the actual bar handlers against a lost-release sequence, without a UI.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path'),os=require('os');
const source=fs.readFileSync(path.join(__dirname,'../../.config/quickshell/Bar.qml'),'utf8');
const input=source.match(/function nativeInput\(data\)\{([\s\S]*?)\n    \}/)[1];
const reset=source.match(/function releaseInputAfterDisconnect\(\)\{([\s\S]*?)\n    \}/)[1];
const disconnect=source.match(/function onEventSocketConnectedChanged\(\) \{([\s\S]*?)\n        \}/)[1];
for(const editor of [false,true]) {
 const ctx={Hyprland:{eventSocketConnected:false},Date,Number,Math,Qt:{point:(x,y)=>({x,y})},interactionTesting:false,nativeLeftHeld:true,nativeInputToken:17,closedNativeToken:-1,discardReleaseClick:true,ignoreClickUntil:0,dragItem:{},dragGroupId:'',editOpen:editor,cancelled:0,editorCancelled:0,timerStarted:0,lastNativeKind:'',lastNativeDelta:0};ctx.root=ctx;ctx.selectionAt=()=>null;
 ctx.releaseClickTimer={restart:()=>{ctx.timerStarted++}};
 ctx.cancelModuleDrag=()=>{ctx.cancelled++;ctx.dragItem=null};
 ctx.closeEditor=accept=>{assert.strictEqual(accept,false);ctx.editorCancelled++;ctx.editOpen=false};
 vm.createContext(ctx);vm.runInContext('function releaseInputAfterDisconnect(){'+reset+'}\nfunction nativeInput(data){'+input+'}',ctx);
 vm.runInContext('(function(){'+disconnect+'})()',ctx);
 assert.strictEqual(ctx.nativeLeftHeld,false);assert.strictEqual(ctx.nativeInputToken,-1);assert.strictEqual(ctx.cancelled,1);assert.strictEqual(ctx.editorCancelled,editor?1:0);assert.ok(ctx.timerStarted>0);
 vm.runInContext('nativeInput("release,17,20,30,0")',ctx);assert.strictEqual(ctx.nativeLeftHeld,false);
 vm.runInContext('nativeInput("press,18,20,30,0");nativeInput("release,18,20,30,0")',ctx);assert.strictEqual(ctx.nativeLeftHeld,false);assert.strictEqual(ctx.nativeInputToken,18);
}
console.log('Perte IPC pendant geste/panneau : annulation, jeton périmé ignoré, nouveau clic libéré : PASS');
