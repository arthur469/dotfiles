"""Compare the actual shared badge's native mode to the upstream component."""
from pathlib import Path
import tempfile,subprocess as sp,os,shutil
from runtime import quickshell
root=Path(__file__).resolve().parents[2];q=root/'.config/quickshell';s=(q/'Bar.qml').read_text()
component=s[s.index('    component ResourceBadge:'):s.index('    Component {\n        id: statsC')].replace('Theme.','theme.')
reference=(root/'tests/fixtures/native-stat-badge-50bab24.qmlpart').read_text().replace('Theme.','theme.')
prefix='''import QtQuick
import QtQuick.Layouts
import Quickshell
Scope {
 id:root
 property bool vertical:true
 property real factor:1
 property var sz:({taskIcon:18*factor,clock:12*factor})
 property int panelThick:Math.round(32*factor)
 function moduleIsVertical(item){return vertical;}
 function s(value){return Math.round(value*factor);}
 component Interactive:Item{property bool warning:false;property bool interactive:true}
 QtObject{id:theme;property color text:"white";property color danger:"red";property string iconFont:"JetBrainsMono Nerd Font"}
 QtObject{id:cfg;property string statsMode:"native";property bool statsPercent:false;property bool statsBorder:true;property real statsScale:1}
 property var cases:[]
 property int index:0
 property int phase:0
 Window {visible:true;width:700;height:300
  ResourceBadge{id:actual;x:20;y:20;label:"CPU";value:"100";unit:"%"}
  StatBadge{id:expected;x:350;y:20;label:"CPU";valueText:"100";unit:"%"}
 }
 Component.onCompleted:{for(const vertical of [true,false])for(const factor of [.8,1.5])for(const scale of [.7,1,1.6])for(const border of [true,false])for(const symbols of [true,false])cases.push({vertical,factor,scale,border,symbols});}
 Timer{interval:20;running:true;repeat:true;onTriggered:{try{
  const c=root.cases[root.index];if(root.phase===0){root.vertical=c.vertical;root.factor=c.factor;cfg.statsScale=c.scale;cfg.statsBorder=c.border;cfg.statsPercent=c.symbols;root.phase=1;return;}
  function same(a,b,label){if(Math.abs(a-b)>.05)throw Error(label+" "+a+" != "+b+" "+JSON.stringify(c));}
  same(actual.implicitWidth,expected.implicitWidth,"module width");same(actual.implicitHeight,expected.implicitHeight,"module height");
  const a=actual.children[0],b=expected.children[0];same(a.width,b.width,"badge width");same(a.height,b.height,"badge height");same(a.x,b.x,"badge offset");
  const ar=a.children[0],br=b.children[0];same(ar.implicitWidth,br.implicitWidth,"text width");same(ar.implicitHeight,br.implicitHeight,"text height");
  if(a.border.width!==b.border.width)throw Error("Border setting lost");
  root.index++;root.phase=0;if(root.index===root.cases.length){console.log("PASS native badge equivalence",root.index);Qt.quit();}
 }catch(error){console.error("FAIL",error);Qt.quit();}}}
}
'''
with tempfile.TemporaryDirectory(prefix='43pr-native-badge-') as d:
 p=Path(d)/'shell.qml';p.write_text(prefix.replace('}\n', '}\n',1))
 # Inline component definitions belong to the existing Scope.
 text=prefix;at=text.index(' property var cases:[]');text=text[:at]+component+reference+text[at:];p.write_text(text)
 env=dict(os.environ,QT_QPA_PLATFORM='offscreen');env.pop('WAYLAND_DISPLAY',None)
 r=sp.run([quickshell(),'-p',str(p)],env=env,capture_output=True,text=True,timeout=12);log=r.stdout+r.stderr
 assert r.returncode==0 and 'PASS native badge equivalence 48' in log and 'FAIL' not in log,log
 print('PASS: 48 native badge cases, geometry/text/border/symbols match upstream across orientations and scales')
