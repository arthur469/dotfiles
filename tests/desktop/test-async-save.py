#!/usr/bin/env python3
"""Reproduit une écriture asynchrone dont l'écho écrase un réglage plus récent."""
from pathlib import Path
import tempfile,subprocess,json,re
bar=(Path(__file__).resolve().parents[2]/'.config/quickshell/Bar.qml').read_text()
body=re.search(r'Timer \{ id: saveTimer; interval: 300; onTriggered: \{(.*)\} \}',bar).group(1).replace('cfgFile','file')
assert 'root.manipulating' in body, 'Pas de protection des sauvegardes de geste'
from runtime import quickshell
binary=quickshell();results=[]
for guarded in [False,True]:
 with tempfile.TemporaryDirectory(prefix='p0-write-') as d:
  base=Path(d);(base/'value.json').write_text('{"value":1}')
  qml='''import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
 id:root
 property bool manipulating:true
 FileView {id:file;path:PATH;adapter:JsonAdapter{id:cfg;property real value:1}}
 Timer {id:save;interval:50;onTriggered:{GUARD;file.writeAdapter();}}
 Timer {interval:100;running:true;onTriggered:{cfg.value=.95;ACTION;}}
 Timer {interval:300;running:true;onTriggered:{console.log("DURING",cfg.value);root.manipulating=false;save.restart();}}
 Timer {interval:500;running:true;onTriggered:{console.log("FINAL",cfg.value);Qt.quit();}}
}'''
  # Unguarded write's completion can deserialize the earlier snapshot into cfg.
  qml=qml.replace('PATH',json.dumps(str(base/'value.json'))).replace('GUARD',body.replace('file.writeAdapter();','') if guarded else '').replace('ACTION','save.restart();cfg.value=.9;' if guarded else 'file.writeAdapter();cfg.value=.9;')
  (base/'shell.qml').write_text(qml);r=subprocess.run([binary,'-p',str(base/'shell.qml'),'--no-color'],text=True,capture_output=True,timeout=8);text=r.stdout+r.stderr
  during=.9 if 'DURING 0.9\n' in text else .95 if 'DURING 0.95\n' in text else None
  assert during==(.9 if guarded else .95),text
  results.append({'guarded':guarded,'during':during,'final':json.loads((base/'value.json').read_text())['value'],'log':text})
print(json.dumps(results,indent=2))
