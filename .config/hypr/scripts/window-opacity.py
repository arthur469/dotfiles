#!/usr/bin/python3
"""Native active/inactive opacity; session-only exceptions follow living windows."""
import argparse,json,re,subprocess,sys,os,fcntl
from pathlib import Path

def native(address,value,opaque=False):
 selector=json.dumps('address:'+address);commands=[]
 for prop,number in [('opacity',value),('opacity_inactive',value),('opacity_override',1),('opacity_inactive_override',1),('opaque',1 if opaque else 0)]:
  commands.append('dispatch hl.dsp.window.set_prop({window='+selector+',prop='+json.dumps(prop)+',value='+json.dumps(str(number))+'})')
 r=subprocess.check_output(['hyprctl','--batch',';'.join(commands)],text=True,timeout=4)
 if any(line.strip() not in ['ok',''] for line in r.splitlines()):raise RuntimeError(r.strip())

def apply(address=None,value=None,sync=False):
 runtime=Path(os.environ['XDG_RUNTIME_DIR'])/'43pr-opacity';runtime.mkdir(mode=0o700,exist_ok=True)
 with (runtime/'lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  windows=json.loads(subprocess.check_output(['hyprctl','-j','clients'],timeout=3))
  windows={c['address']:c for c in windows if c.get('mapped')}
  p=runtime/'windows.json';saved=json.loads(p.read_text()) if p.exists() else {}
  saved={a:v for a,v in saved.items() if a in windows and v.get('pid')==windows[a]['pid']}
  if not sync:
   if not address or not re.fullmatch(r'0x[0-9a-fA-F]+',address) or address not in windows:raise ValueError('Cette fenêtre est fermée')
   if value is None:saved.pop(address,None)
   else:
    if round(value*10) not in range(4,11) or abs(round(value*10)/10-value)>1e-6:raise ValueError('Opacité attendue : 40 à 100 %')
    saved[address]={'pid':windows[address]['pid'],'value':value}
  workspace=Path.home()/'.config/hypr/workspace-opacity.json';values=json.loads(workspace.read_text()) if workspace.exists() else {}
  for a,c in windows.items():
   desired=saved[a]['value'] if a in saved else values.get(str(c['workspace']['id']),1.0)
   # Native set_prop opacity does not implement unset in Hyprland 0.56.2.
   # Reapply the workspace fallback on real move/configuration events instead.
   fullscreen=bool(c.get('fullscreen',0) or c.get('fullscreenClient',0))
   browser=c.get('class','').lower() in {'brave-browser','brave-browser-beta','brave-browser-nightly'}
   native(a,1.0 if fullscreen or browser else desired,opaque=fullscreen or browser)
  tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(saved));tmp.chmod(0o600);tmp.replace(p)

def main():
 p=argparse.ArgumentParser();p.add_argument('--window');p.add_argument('--set',type=float);p.add_argument('--reset',action='store_true');p.add_argument('--sync',action='store_true');a=p.parse_args()
 if a.sync:apply(sync=True);return
 address=a.window or json.loads(subprocess.check_output(['hyprctl','-j','activewindow'],timeout=3)).get('address')
 if not address:raise ValueError('Sélectionner une fenêtre avant le raccourci')
 value=a.set
 if value is None and not a.reset:
  choices=['Suivre le bureau']+[str(n)+'%' for n in range(100,39,-10)]
  r=subprocess.run(['rofi','-dmenu','-hover-select','-me-select-entry','','-me-accept-entry','MousePrimary','-p','Opacité — fenêtre sélectionnée'],input='\n'.join(choices)+'\n',text=True,capture_output=True)
  if r.returncode!=0:return
  selected=r.stdout.strip()
  if selected not in choices:return
  if selected!='Suivre le bureau':value=int(selected[:-1])/100
 apply(address,None if a.reset else value)
 print('Fenêtre : suivre le bureau' if value is None or a.reset else f'Fenêtre : {round(value*100)} %')
if __name__=='__main__':
 try:main()
 except Exception as error:print(str(error),file=sys.stderr);raise SystemExit(1)
