from runtime import quickshell
from pathlib import Path
import os,subprocess as sp
from PIL import Image
import tempfile,shutil
root=Path(__file__).resolve().parents[2]
w=Path(tempfile.mkdtemp(prefix='43pr-surface-test-'))
shutil.copy2(root/'.config/quickshell/BarSurface.qml',w/'BarSurface.qml')
qml='''import QtQuick
import Quickshell
Scope {
 id:root
 property int index:0
 property var values:[0.4,0.7,1]
 Window {visible:true;color:"transparent";width:120;height:80
  BarSurface {id:surface;width:120;height:80;surfaceColor:Qt.rgba(.1,.2,.3,.1);surfaceOpacity:root.values[Math.floor(root.index/3)];radius:12
   holes:[{x:75,y:10,width:25,height:25,radius:4}]
   patches:[{x:10,y:10,width:30,height:30,opacity:root.values[root.index%3]}]
  }
 }
 Timer {id:tick;interval:80;running:true;onTriggered:surface.grabToImage(result=>{result.saveToFile(Qt.resolvedUrl("surface-"+root.index+".png").toString().replace("file://",""));root.index++;if(root.index===9){console.log("PASS surface render");Qt.quit();}else tick.restart();})}
}
'''
p=w/'surface-test.qml';p.write_text(qml)
try:
 env=dict(os.environ,QT_QPA_PLATFORM='offscreen');env.pop('WAYLAND_DISPLAY',None)
 r=sp.run([quickshell(),'-p',str(p)],env=env,capture_output=True,text=True,timeout=10);log=r.stdout+r.stderr;(w/'surface.log').write_text(log);assert 'PASS surface render' in log,log
 for i in range(9):
  image=Image.open(w/f'surface-{i}.png').convert('RGBA');expectedBase=round([.4,.7,1][i//3]*255);expectedPatch=round([.4,.7,1][i%3]*255)
  assert abs(image.getpixel((50,50))[3]-expectedBase)<=1,(i,image.getpixel((50,50)))
  assert abs(image.getpixel((20,20))[3]-expectedPatch)<=1,(i,image.getpixel((20,20)))
  assert image.getpixel((85,20))[3]==0;assert image.getpixel((0,0))[3]==0
 print('PASS : 9 alpha combinations, 100% = alpha 255, independent module/bubble opacity, rounded cutouts, theme alpha ignored')
finally:shutil.rmtree(w)
