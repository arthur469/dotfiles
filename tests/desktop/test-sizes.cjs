const fs=require('fs'),vm=require('vm'),assert=require('assert');const a=vm.createContext({});vm.runInContext(fs.readFileSync(process.argv[2]||require('path').join(__dirname,'../../.config/quickshell/scripts/bar-layout.js'),'utf8').replace(/^\.pragma.*\n/,''),a);
const old={moduleZoom:1.2,moduleScale:{cpu:.8,ram:1.5},moduleScaleVersion:1};const migrated={...old,...a.migrateScales(old)};
assert.equal(a.moduleScale(migrated,'cpu'),.96);assert(Math.abs(a.moduleScale(migrated,'ram')-1.8)<1e-9);assert.equal(a.moduleScale(migrated,'clock'),1.2);assert.equal(Object.keys(a.migrateScales(migrated)).length,0);
const uniform={...migrated,...a.uniformScale(1.25)};for(const id of ['cpu','ram','clock','tasks','disk:new','unavailable-hidden'])assert.equal(a.moduleScale(uniform,id),1.25);assert.equal(Object.keys(uniform.moduleScale).length,0);
const resized=a.resizeModules({},['tasks'],.05,1.25);assert.equal(resized.values.tasks,1.3);assert.equal(resized.average,1.3);
assert.equal(a.uniformScale(100).moduleZoom,2);assert.equal(a.uniformScale(.1).moduleZoom,.5);
console.log('PASS absolute sizes, global normalization, hidden/new modules, legacy migration, resize after normalization');
