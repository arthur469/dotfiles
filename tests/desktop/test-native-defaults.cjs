const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),expected=JSON.parse(fs.readFileSync(path.join(root,'tests/fixtures/upstream-defaults-50bab24.json'),'utf8'));
const profilePath=path.join(root,'profiles/personal-defaults.json');
const profile=fs.existsSync(profilePath)?JSON.parse(fs.readFileSync(profilePath,'utf8')):[];
let checked=0;
for(const [rel,properties] of Object.entries(expected.root_properties)){
 const source=fs.readFileSync(path.join(root,rel),'utf8');
 const actual=new Map([...source.matchAll(/^    (?:readonly )?property (?:int|real|bool|string|color) (\w+):\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|true|false|-?\d+(?:\.\d+)?)(\s*(?:\/\/[^\n]*)?)$/gm)].map(m=>[m[1],m[2]]));
 for(const [key,value] of Object.entries(properties))if(actual.has(key)){
  const override=profile.find(x=>x.path===rel&&x.property===key);
  assert.equal(actual.get(key),override?override.personal:value,rel+':'+key);checked++;
 }
}
for(const rel of ['.config/quickshell/Bar.qml','.config/quickshell/SettingsPages/BarPage.qml']){
 const source=fs.readFileSync(path.join(root,rel),'utf8');const object=source.match(/readonly property var defaults: \((\{[\s\S]*?\})\)/)[1];
 const actual=vm.runInNewContext('('+object+')');
 for(const [key,value] of Object.entries(expected.bar)){assert.deepEqual(JSON.parse(JSON.stringify(actual[key])),value,rel+':'+key);checked++;}
}
const keys=fs.readFileSync(path.join(root,'.config/hypr/keybinds.lua'),'utf8');
for(const [key,value] of Object.entries(expected.keybinds)){const actual=keys.match(new RegExp('^local '+key+'\\s*=\\s*("[^"\\n]*")','m'));assert.ok(actual,key);assert.equal(JSON.parse(actual[1]),value,key);checked++;}
const page=fs.readFileSync(path.join(root,'.config/quickshell/SettingsPages/KeybindsPage.qml'),'utf8');
for(const bind of expected.shortcut_page){const line=page.split('\n').find(x=>new RegExp('id:\\s*"'+bind.id+'"').test(x)&&x.includes('def:'));assert.ok(line,bind.id);assert.equal(line.match(/def:\s*"([^"]+)"/)[1],bind.default,bind.id);checked++;}
console.log(JSON.stringify({checked,upstream:expected.upstream_commit,profileOverrides:profile.length,nativeDefaultsPreserved:true}));
