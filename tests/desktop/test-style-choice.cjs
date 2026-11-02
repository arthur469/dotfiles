const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const qml=path.resolve(__dirname,'../../.config/quickshell');
const page=fs.readFileSync(path.join(qml,'SettingsPages/BarPage.qml'),'utf8'),bar=fs.readFileSync(path.join(qml,'Bar.qml'),'utf8');
const picked=page.match(/current: page.val\("style"\)\s+onPicked: v => ([^\n]+)/)[1];
const setMany=page.match(/function setMany\(o\) \{([\s\S]*?)\n    \}/)[1];
const storage={};vm.createContext(storage);vm.runInContext(fs.readFileSync(path.join(qml,'scripts/storage-modules.js'),'utf8').replace(/^\.pragma[^\n]*\n/,''),storage);
for(const position of ['left','right','top','bottom'])for(const style of ['floating','joined','strip']) {
 const original={position,style:'floating',freeLayout:true,moduleGroups:[{id:'user',items:['cpu','ram'],x:.4,y:.5}],groupCells:{user:{cpu:{x:0,y:0}}},groupRotations:{user:1},moduleScale:{cpu:1.2},moduleOpacity:{cpu:.65},hidden:'net'};
 let saves=0;const model={defaults:{},s:structuredClone(original)};
 const context={page:model,s:model.s,StorageModules:storage,saveTimer:{restart(){saves++;}}};Object.defineProperty(context,"s",{get(){return model.s;},set(v){model.s=v;},configurable:true});vm.createContext(context);
 model.setMany=o=>{vm.runInContext('(function(o){'+setMany+'})',context)(o);context.s=model.s;};
 vm.runInContext('(v=>'+picked+')',context)(style);
 const expected={...original,style,freeLayout:false};
 // Storage migration may normalize empty legacy properties; user groups and coordinates must survive.
 for(const key of Object.keys(expected))assert.deepEqual(JSON.parse(JSON.stringify(model.s[key])),expected[key],key);
 assert.equal(saves,1);
 const cfg=model.s;
 const joined=vm.runInNewContext(bar.match(/readonly property bool joined: ([^\n]+)/)[1],{cfg});
 assert.equal(joined,style!=='floating');assert.equal(joined&&!cfg.freeLayout,style!=='floating');
 model.setMany({freeLayout:true});assert.deepEqual(JSON.parse(JSON.stringify(model.s.moduleGroups)),original.moduleGroups);
}
console.log('PASS: 12 style/position choices leave free layout, preserve groups/cells/rotation/scale/opacity; free layout can be restored.');
