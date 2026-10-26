#!/usr/bin/python3
"""Use the real backlight or this output's DDC/CI VCP 10, never a gamma filter."""
import argparse,subprocess,json,re,os,fcntl
from pathlib import Path

def run(args):return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL,timeout=8)
def brightness(output,value=None,delta=None):
 folder=Path(os.environ['XDG_RUNTIME_DIR'])/'43pr-brightness';folder.mkdir(mode=0o700,exist_ok=True)
 with (folder/'lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if list(Path('/sys/class/backlight').glob('*')):
   percent=int(run(['brightnessctl','-m']).split(',')[3].strip('%'))
   if delta is not None:value=max(1,min(100,percent+delta))
   if value is not None:run(['brightnessctl','set',str(value)+'%']);percent=value
   return {'available':True,'value':percent,'backend':'backlight'}
  cache=folder/'displays.json'
  displays=json.loads(cache.read_text()) if cache.exists() else {}
  if output not in displays:
   text=run(['ddcutil','detect','--brief']);bus=None
   for line in text.splitlines():
    if 'I2C bus:' in line:bus=int(line.split('i2c-')[-1])
    if 'DRM connector:' in line and bus is not None:
     name=re.sub(r'^card\d+-','',line.split(':',1)[1].strip());displays[name]=bus
   cache.write_text(json.dumps(displays))
  if output not in displays:raise ValueError('Aucun contrôle de luminosité trouvé pour cet écran')
  bus=str(displays[output])
  text=run(['ddcutil','--bus',bus,'getvcp','10','--brief']);m=re.search(r'VCP 10 C (\d+) (\d+)',text)
  if not m:raise ValueError('Luminosité non prise en charge')
  current,maximum=map(int,m.groups())
  if delta is not None:value=max(1,min(100,round(current*100/maximum)+delta))
  if value is not None:
   run(['ddcutil','--bus',bus,'setvcp','10',str(max(1,round(value*maximum/100))),'--noverify'])
   current=round(value*maximum/100)
  return {'available':True,'value':round(current*100/maximum),'backend':'DDC/CI','output':output}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',default='');p.add_argument('--set',type=int);p.add_argument('--delta',type=int);p.add_argument('--osd',action='store_true');a=p.parse_args()
 try:
  if a.set is not None and not 1<=a.set<=100:raise ValueError('Luminosité attendue : 1 à 100 %')
  if not a.output:a.output=next(m['name'] for m in json.loads(run(['hyprctl','-j','monitors'])) if m.get('focused'))
  if a.delta is not None and not -20<=a.delta<=20:raise ValueError('Pas de luminosité invalide')
  print(json.dumps(brightness(a.output,a.set,a.delta),ensure_ascii=False))
  if a.osd:subprocess.run(['qs','ipc','-p',str(Path.home()/'.config/quickshell'),'call','mediaosd','brightness',a.output],check=True,timeout=3)
 except Exception as e:print(json.dumps({'available':False,'error':str(e)},ensure_ascii=False));raise SystemExit(1)
