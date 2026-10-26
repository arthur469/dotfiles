#!/usr/bin/python3
"""Opt-in groups reuse Hyprland special workspaces and the existing Open apps."""
from pathlib import Path
import argparse,json,subprocess,re,uuid,os,tempfile
h=Path.home();path=h/'.config/quickshell/state/bar-state.json'
def query(name):return json.loads(subprocess.check_output(['hyprctl','-j',name],timeout=3))
def config():return json.loads(path.read_text())
def save(data):
 fd,tmp=tempfile.mkstemp(prefix='.bar-groups-',dir=path.parent)
 with os.fdopen(fd,'w') as f:json.dump(data,f,indent=2)
 os.replace(tmp,path)
def dispatch(expression):
 result=subprocess.check_output(['hyprctl','dispatch',expression],text=True,timeout=3)
 if result.strip()!='ok':raise RuntimeError(result.strip())
def move(address,group):
 if not re.fullmatch(r'0x[0-9a-fA-F]+',address):raise ValueError('Fenêtre invalide')
 if group and not re.fullmatch(r'[a-z0-9-]{1,40}',group):raise ValueError('Groupe invalide')
 if not any(c['address']==address and c.get('mapped') for c in query('clients')):raise ValueError('Fenêtre déjà fermée')
 workspace='special:minimized'+('-'+group if group else '')
 dispatch('hl.dsp.window.move({window='+json.dumps('address:'+address)+',workspace='+json.dumps(workspace)+',follow=false})')
def menu(options,prompt):
 r=subprocess.run(['rofi','-dmenu','-p',prompt],input='\n'.join(options)+'\n',text=True,capture_output=True)
 return r.stdout.strip() if r.returncode==0 else None

def main():
 p=argparse.ArgumentParser();p.add_argument('--choose',action='store_true');p.add_argument('--window');p.add_argument('--drop');p.add_argument('--remove');a=p.parse_args();s=config();groups=s.get('windowGroups',[])
 if a.remove:
  if a.remove not in [g['id'] for g in groups]:raise ValueError('Groupe inconnu')
  for c in query('clients'):
   if c['workspace']['name']=='special:minimized-'+a.remove:move(c['address'],'')
  s=config();s['windowGroups']=[g for g in s.get('windowGroups',[]) if g['id']!=a.remove];save(s);return
 if a.drop:
  if not s.get('dropToMinimize'):return
  position=query('cursorpos');monitors=query('monitors');raw=subprocess.check_output(['qs','ipc','-p',str(h/'.config/quickshell'),'call','bar','layoutState'],text=True,timeout=3);layout=json.loads(raw)
  for item in layout['modules']:
   mid=item['id'];rect=item['geometry'];mon=next((m for m in monitors if m['name']==rect['output']),None)
   if not mon or (mid!='tasks' and not mid.startswith('minigroup-')):continue
   x,y=position['x']-mon['x'],position['y']-mon['y']
   if rect['x']<=x<=rect['x']+rect['width'] and rect['y']<=y<=rect['y']+rect['height']:
    group=mid[len('minigroup-'):] if mid.startswith('minigroup-') else ''
    if group and group not in [g['id'] for g in groups]:continue
    move(a.drop if a.drop.startswith('0x') else '0x'+a.drop,group);return
  return
 address=a.window or query('activewindow').get('address')
 if not address:raise ValueError('Sélectionner une fenêtre')
 options=['Réduire — groupe habituel']+[g['name'] for g in groups]+['+ Nouveau groupe…'];selected=menu(options,'Réduire la fenêtre dans…')
 if selected is None:return
 if selected==options[0]:move(address,'');return
 if selected==options[-1]:
  name=menu([],'Nom du nouveau groupe')
  if not name:return
  name=' '.join(name.split())[:40]
  if name in options:raise ValueError('Ce nom est déjà utilisé')
  group={'id':uuid.uuid4().hex[:12],'name':name};s=config();s['windowGroupsEnabled']=True;s['windowGroups']=s.get('windowGroups',[])+[group];save(s)
 else:
  group=next((g for g in groups if g['name']==selected),None)
  if not group:return
 move(address,group['id'])
if __name__=='__main__':
 try:main()
 except Exception as e:print(str(e));raise SystemExit(1)
