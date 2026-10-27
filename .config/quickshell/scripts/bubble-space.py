#!/usr/bin/python3
"""Publish bubble geometry without replacing the native Hyprland layout."""
from pathlib import Path
import argparse,json,os,re,subprocess,tempfile,fcntl,math
ROOT=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))/'43pr-bubbles'
def ctl(*args):return subprocess.check_output(['hyprctl',*args],text=True,timeout=3)
def atomic(path,text):
 fd,tmp=tempfile.mkstemp(dir=path.parent)
 try:
  with os.fdopen(fd,'w') as f:f.write(text)
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def update(state):
 ROOT.mkdir(mode=0o700,exist_ok=True)
 with (ROOT/'lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  monitors={m['name']:m for m in json.loads(ctl('-j','monitors'))}
  hits=[]
  for item in state.get('minimized',[]):
   a=item.get('address','');r=item.get('geometry',{});m=monitors.get(r.get('output'))
   if not m or not re.fullmatch(r'0x[0-9a-fA-F]+',a):continue
   vals=[r.get(k) for k in ('x','y','width','height')]
   if any(type(v) not in (int,float) or not math.isfinite(v) for v in vals):continue
   x,y,w,h=vals
   hits.append('{address='+json.dumps(a)+',x='+str(m['x']+x)+',y='+str(m['y']+y)+',w='+str(w)+',h='+str(h)+'}')
  atomic(ROOT/'minimized.lua','return {'+','.join(hits)+'}\n')
  # Migrate the old optional Lua provider once; never replace the native tree.
  marker=ROOT/'previous.json'
  if marker.exists():
   before=json.loads(marker.read_text()).get('layout','dwindle')
   current=json.loads(ctl('-j','getoption','general:layout'))['str']
   if current=='lua:43pr-bubbles':ctl('eval','hl.config({general={layout='+json.dumps(before if before!='lua:43pr-bubbles' else 'dwindle')+'}})')
   marker.unlink();(ROOT/'state.lua').unlink(missing_ok=True)
  signature=os.environ.get('HYPRLAND_INSTANCE_SIGNATURE','')
  if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,180}',signature):raise ValueError('Missing compositor identity')
  session=ROOT/signature;session.mkdir(mode=0o700,exist_ok=True)
  margin=state.get('margin',0)
  if type(margin) not in (int,float) or not math.isfinite(margin) or not 0<=margin<=200:raise ValueError('Invalid edge margin')
  rows=[]
  for r in state.get('rectangles',[])[:128]:
   name=r.get('output');m=monitors.get(name)
   if not m or not re.fullmatch(r'[\w.:-]{1,80}',name):continue
   vals=[r.get(k) for k in ('x','y','width','height')]
   if any(type(v) not in (int,float) or not math.isfinite(v) for v in vals):raise ValueError('Invalid bubble bounds')
   x,y,w,h=vals
   if not 0<w<=20000 or not 0<h<=20000:continue
   rows.append(json.dumps(name)+' '+str(round(m['x']+x,2))+' '+str(round(m['y']+y,2))+' '+str(round(w,2))+' '+str(round(h,2)))
  text=str(int(bool(state.get('active'))))+' '+str(margin)+'\n'+'\n'.join(rows)+'\n'
  target=session/'reservation.txt';changed=not target.exists() or target.read_text()!=text
  if changed:atomic(target,text)
  plugins=json.loads(ctl('-j','plugin','list'))
  ready=any(p.get('name')=='43pr-bubble-reserve' for p in plugins)
  if not ready:
   version=json.loads(ctl('-j','version'))['commit']
   if not re.fullmatch('[0-9a-f]{40}',version):raise ValueError('Invalid compositor version')
   binary=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'43pr/bubble-reserve'/str(version+'.so')
   if binary.exists():
    result=ctl('plugin','load',str(binary));ready='error' not in result.lower()
  if ready and changed:ctl('eval','hl.plugin.bubbles.refresh()')
  plugins=json.loads(ctl('-j','plugin','list')) if ready else []
  loaded=next((p for p in plugins if p.get('name')=='43pr-bubble-reserve'),{})
  version=re.match(r'^(\d+)\.(\d+)\.(\d+)',str(loaded.get('version','')))
  control_bridge=bool(version and tuple(map(int,version.groups()))>=(0,2,0))
  return {'ready':ready,'controlBridge':control_bridge,'active':bool(state.get('active')) and ready,'rectangles':len(rows),'margin':margin}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',required=True);a=p.parse_args()
 try:print(json.dumps(update(json.loads(a.state))))
 except Exception as error:print(json.dumps({'ready':False,'error':str(error)}));raise SystemExit(1)
