#!/usr/bin/python3
"""Coalesce validated bar geometry into Hyprland's optional native Lua layout."""
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
def avoid_floating(output,monitors):
 def intersects(a,b):return a['x']<b['x']+b['w'] and a['x']+a['w']>b['x'] and a['y']<b['y']+b['h'] and a['y']+a['h']>b['y']
 for c in json.loads(ctl('-j','clients')):
  if not c.get('mapped') or not c.get('floating') or c.get('fullscreen') or c.get('fullscreenClient'):continue
  m=next((m for m in monitors.values() if m['id']==c['monitor']),None)
  if not m or c['workspace']['id']!=m['activeWorkspace']['id']:continue
  holes=output.get(m['name'],[]);x,y=c['at'];w,h=c['size'];r=dict(x=x,y=y,w=w,h=h)
  if not any(intersects(r,o) for o in holes):continue
  reserved=m.get('reserved',[0,0,0,0]);left=m['x']+reserved[0];top=m['y']+reserved[1]
  right=m['x']+m['width']/m['scale']-reserved[2];bottom=m['y']+m['height']/m['scale']-reserved[3]
  candidates=[]
  for cx in [x,left,right-w]+[v for o in holes for v in (o['x']-w,o['x']+o['w'])]:
   for cy in [y,top,bottom-h]+[v for o in holes for v in (o['y']-h,o['y']+o['h'])]:
    t=dict(x=cx,y=cy,w=w,h=h)
    if cx>=left and cy>=top and cx+w<=right and cy+h<=bottom and not any(intersects(t,o) for o in holes):candidates.append(t)
  if not candidates:
   # A large floating window may need to shrink to one free rectangle.
   free=[dict(x=left,y=top,w=right-left,h=bottom-top)]
   for o in holes:
    nxt=[]
    for r in free:
     if not intersects(r,o):nxt.append(r);continue
     x1=max(r['x'],o['x']);x2=min(r['x']+r['w'],o['x']+o['w']);y1=max(r['y'],o['y']);y2=min(r['y']+r['h'],o['y']+o['h'])
     for a in [dict(x=r['x'],y=r['y'],w=x1-r['x'],h=r['h']),dict(x=x2,y=r['y'],w=r['x']+r['w']-x2,h=r['h']),dict(x=x1,y=r['y'],w=x2-x1,h=y1-r['y']),dict(x=x1,y=y2,w=x2-x1,h=r['y']+r['h']-y2)]:
      if a['w']>=160 and a['h']>=100:nxt.append(a)
    free=nxt
   if free:
    f=max(free,key=lambda r:min(w,r['w'])*min(h,r['h']))
    candidates=[dict(x=f['x'],y=f['y'],w=min(w,f['w']),h=min(h,f['h']))]
  if not candidates:continue
  t=min(candidates,key=lambda r:(r['x']-x)**2+(r['y']-y)**2)
  selector=json.dumps('address:'+c['address'])
  if t['w']!=w or t['h']!=h:ctl('dispatch',f'hl.dsp.window.resize({{window={selector},x={round(t["w"])},y={round(t["h"])},relative=false}})')
  ctl('dispatch',f'hl.dsp.window.move({{window={selector},x={round(t["x"])},y={round(t["y"])},relative=false}})')
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
  marker=ROOT/'previous.json' 
  if not state.get('active'):
   if marker.exists():
    before=json.loads(marker.read_text())['layout']
    current=json.loads(ctl('-j','getoption','general:layout'))['str']
    if current=='lua:43pr-bubbles':ctl('eval','hl.config({general={layout='+json.dumps(before)+'}})')
    marker.unlink();(ROOT/'state.lua').unlink(missing_ok=True)
   return
  monitors={m['name']:m for m in json.loads(ctl('-j','monitors'))}
  output={}
  for r in state.get('rectangles',[]):
   name=r.get('output');m=monitors.get(name)
   if not m or not re.fullmatch(r'[\w.:-]{1,80}',name):continue
   vals=[r.get(k) for k in ('x','y','width','height')]
   if any(type(v) not in (int,float) or not math.isfinite(v) for v in vals):raise ValueError('Invalid bubble bounds')
   x,y,w,h=vals
   if not 0<w<=10000 or not 0<h<=10000:continue
   # Bar coordinates are logical output-local; compositor coordinates are global.
   output.setdefault(name,[]).append(dict(x=round(m['x']+x-8,2),y=round(m['y']+y-8,2),w=round(w+16,2),h=round(h+16,2)))
  avoid_floating(output,monitors)
  text='return {'+','.join('['+json.dumps(name)+']={'+','.join('{'+','.join(k+'='+str(v) for k,v in r.items())+'}' for r in rows)+'}' for name,rows in output.items())+'}\n'
  if (ROOT/'state.lua').exists() and (ROOT/'state.lua').read_text()==text and marker.exists() and json.loads(ctl('-j','getoption','general:layout'))['str']=='lua:43pr-bubbles':return
  atomic(ROOT/'state.lua',text)
  current=json.loads(ctl('-j','getoption','general:layout'))['str']
  if not marker.exists():atomic(marker,json.dumps({'layout':current if current!='lua:43pr-bubbles' else 'dwindle'}))
  if current!='lua:43pr-bubbles':
   source=str(Path.home()/'.config/hypr/scripts/bubble-layout.lua')
   result=ctl('eval','hl.config({general={layout="lua:43pr-bubbles"}})')
   if 'error' in result.lower():raise RuntimeError(result)
  else:ctl('dispatch','hl.dsp.layout("refresh")')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',required=True);a=p.parse_args();update(json.loads(a.state))
