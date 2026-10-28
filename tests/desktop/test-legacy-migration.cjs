const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
function load(file){const c=vm.createContext({});vm.runInContext(fs.readFileSync(file,'utf8').replace(/^\.pragma.*\n/,''),c);return c;}
const scale=load(path.join(__dirname,'../../.config/quickshell/scripts/bar-layout.js')),storage=load(process.argv[2]||path.join(__dirname,'../../.config/quickshell/scripts/storage-modules.js'));
const state={diskVolumes:['uuid:one','uuid:two'],moduleScale:{disk:.8,cpu:1.5},moduleZoom:1.2,hidden:'disk',moduleGroups:[{id:'free-example',items:['cpu','disk']}],position:'left'};
const upgraded={...state,...storage.upgrade(state,scale.migrateScales)};
assert(Math.abs(upgraded.moduleScale[storage.moduleId('uuid:one')]-.96)<1e-9);assert(Math.abs(upgraded.moduleScale.cpu-1.8)<1e-9);assert(!upgraded.moduleScale.disk);assert(upgraded.hidden.includes(storage.moduleId('uuid:two')));assert.equal(upgraded.moduleScaleVersion,2);assert.equal(Object.keys(storage.upgrade(upgraded,scale.migrateScales)).length,0);
console.log('PASS coupled legacy storage/size migration preserves effective values and visibility');
