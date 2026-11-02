#!/usr/bin/env python3
"""Exercise production migration with real JsonAdapter QVariant lists."""
from pathlib import Path
import re,json,tempfile,subprocess as sp,os
from runtime import quickshell
root=Path(__file__).resolve().parents[2];bar=(root/'.config/quickshell/Bar.qml').read_text()
defaults=bar[bar.index('    readonly property var defaults:'):bar.index('    readonly property var positions:')]
file=bar[bar.index('    FileView {'):bar.index("    // Only the bar's own changes")]
migrate=bar[bar.index('    function migrateDisks()'):bar.index('    function resetSettings()')]
for saved,wanted in [({'moduleGroups':[{'id':'free-personal','items':['cpu','clock']}],'moduleZoom':1.3,'hidden':'','startMods':'','centerMods':'','endMods':''},1.3),({'barScale':.8},.8),({},1)]:
 with tempfile.TemporaryDirectory(prefix='43pr-migration-') as d:
  folder=Path(d);(folder/'value.json').write_text(json.dumps(saved))
  file_copy=file.replace('Quickshell.env("HOME") + "/.config/quickshell/state/bar-state.json"',json.dumps(str(folder/'value.json')))
  shell='import QtQuick\nimport Quickshell\nimport Quickshell.Io\n'
  for alias,name in [('BarLayout','bar-layout.js'),('StorageModules','storage-modules.js')]:shell+='import '+json.dumps((root/'.config/quickshell/scripts'/name).as_uri())+' as '+alias+'\n'
  shell+='Scope {id:root;property bool manipulating:false;'+defaults+file_copy+migrate+'''
 function csv(value){return String(value||"").split(",").filter(Boolean);}
 function applyLayout(patch){for(const key in patch)cfg[key]=patch[key];}
 Timer{interval:300;running:true;onTriggered:{
  const okay=cfg.moduleRegistryVersion===1 && cfg.barScale===WANTED && cfg.moduleZoom===WANTED && cfg.hidden.split(",").includes("temp");
  console.log(okay?"PASS MIGRATION":"FAIL MIGRATION",cfg.barScale,cfg.moduleZoom,cfg.hidden);Qt.quit();
 }}
}'''.replace('WANTED',str(wanted))
  p=folder/'shell.qml';p.write_text(shell);r=sp.run([quickshell(),'-p',str(p)],capture_output=True,text=True,timeout=5,env=dict(os.environ,QT_QPA_PLATFORM='offscreen'));log=r.stdout+r.stderr
  assert r.returncode==0 and 'PASS MIGRATION' in log and 'TypeError' not in log,log
print('PASS real JsonAdapter group-list migration, legacy zoom, native scale and fresh defaults')
