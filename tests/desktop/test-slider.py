from pathlib import Path
import tempfile,subprocess as sp,os,shutil
from runtime import quickshell
r=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='43pr-slider-') as d:
 p=Path(d);shutil.copy2(r/'.config/quickshell/Slider.qml',p/'Slider.qml')
 (p/'Theme.qml').write_text('''pragma Singleton
import QtQuick
QtObject{property color accent:"blue";property color trackBg:"gray";property color border:"gray";property color text:"white";property color textDim:"gray";property color bg:"black";property int radius:10;property int animFast:120;property string fontFamily:"monospace";property string iconFont:"monospace";function alpha(color,a){return Qt.rgba(color.r,color.g,color.b,a);}}
''')
 (p/'shell.qml').write_text('''import QtQuick
import Quickshell
import QtTest
Scope {
 Window{visible:true;width:500;height:100;Slider{id:slider;width:400;height:38}}
 TestCase{id:events;when:false}
 Timer{interval:80;running:true;onTriggered:{try{for(const ratio of [0,.25,.5,.75,1]){const q=slider.trackItem.mapToItem(slider,slider.trackItem.width*ratio,2);events.mouseClick(slider,q.x,q.y,Qt.LeftButton,Qt.NoModifier,1);if(Math.abs(slider.value-ratio)>.003)throw Error("Bad slider coordinate: "+ratio+" -> "+slider.value);}console.log("PASS slider positions");}catch(e){console.error("FAIL",e);}Qt.quit();}}
}
''');env=dict(os.environ,QT_QPA_PLATFORM='offscreen');env.pop('WAYLAND_DISPLAY',None);result=sp.run([quickshell(),'-p',str(p/'shell.qml')],env=env,text=True,capture_output=True,timeout=5);log=result.stdout+result.stderr;assert 'PASS slider positions' in log and 'FAIL' not in log,log
 print('PASS shared slider: exact 0/25/50/75/100% input coordinates despite padded hit area')
