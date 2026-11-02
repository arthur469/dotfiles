#!/usr/bin/env python3
"""Native Escape dispatch with production shortcuts and search-key handler."""
from pathlib import Path
import os,re,subprocess as sp,tempfile
from runtime import quickshell
q=Path(os.environ.get('PR43_TEST_QML',Path(__file__).resolve().parents[2]/'.config/quickshell'))
source=(q/'SettingsWindow.qml').read_text()
shortcuts='\n'.join(re.findall(r'            Shortcut \{[^{}]*\}',source))
search=source[source.index('                                            Keys.onEscapePressed: {'):source.index('                                            // Keep the box in sync')].strip()
qml='''import QtQuick
import Quickshell
import QtTest
Scope {
 id:root
 property bool showing:true
 property string searchQuery:""
 property int index:0
 function hide(){showing=false;}
 Window {id:win;visible:true;width:400;height:200
  function focusSearch(){searchInput.forceActiveFocus();}
 SHORTCUTS
  Rectangle {id:backdrop;anchors.fill:parent;focus:root.showing;Keys.onEscapePressed:root.hide()}
  Item {anchors.fill:parent
   TextInput{id:control;x:10;y:10;width:100;height:30;text:"focused child"}
   TextInput{id:searchInput;x:10;y:60;width:100;height:30;text:root.searchQuery
    SEARCH
   }
  }
  TestCase{id:events;when:false}
 }
 property int phase:0
 Timer {interval:50;running:true;repeat:true;onTriggered:{try{
  if(root.phase===0){root.showing=true;win.requestActivate();if(root.index===0)control.forceActiveFocus();else{root.searchQuery="cpu";searchInput.forceActiveFocus();}root.phase=1;return;}
  if(root.phase===1){events.keyClick(Qt.Key_Escape);root.phase=2;return;}
  if(root.index===0){if(root.showing)throw Error("Escape from focused child did not close settings");root.index=1;root.phase=0;return;}
  if(root.phase===2){if(!root.showing||root.searchQuery!=="")throw Error("Search Escape must clear text first");events.keyClick(Qt.Key_Escape);root.phase=3;return;}
  if(root.showing)throw Error("Second search Escape did not close settings");
  console.log("PASS settings Escape: focused child closes; search clears then closes");Qt.quit();
 }catch(error){console.error("FAIL",error);Qt.quit();}}}
}
'''.replace('SHORTCUTS',shortcuts).replace('SEARCH',search)
with tempfile.TemporaryDirectory(prefix='43pr-settings-escape-') as directory:
 p=Path(directory)/'shell.qml';p.write_text(qml)
 env=dict(os.environ,QT_QPA_PLATFORM='offscreen');env.pop('WAYLAND_DISPLAY',None)
 result=sp.run([quickshell(),'-p',str(p)],env=env,capture_output=True,text=True,timeout=8);log=result.stdout+result.stderr
 assert result.returncode==0 and 'PASS settings Escape:' in log and 'FAIL' not in log,log
 print('PASS: native Escape with focused settings control; search clear then close; production Shortcut and search handler')
