#!/usr/bin/env python3
"""Use the existing state/desktop helpers; no automated input without coordination."""
from pathlib import Path
import sys,json,subprocess as sp,time,shlex,os,argparse,fcntl,datetime,hashlib,traceback
from state import capture_bar,restore_states
from regression import display_signature
parser=argparse.ArgumentParser(description='Coordinated live edge-margin and resource-width regression; restores the user layout.')
parser.add_argument('--allow-desktop',action='store_true');parser.add_argument('--output',type=Path)
args=parser.parse_args()
if not args.allow_desktop:parser.error('Coordinate with the user, then pass --allow-desktop')
lock_path=Path.home()/'.local/state/43pr-tests/desktop.lock';lock_path.parent.mkdir(parents=True,exist_ok=True);lock=lock_path.open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
out=args.output or Path.home()/'.local/state/43pr-tests'/('edge-margin-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S-%f'))
out.mkdir(parents=True,exist_ok=False,mode=0o700)
bar=Path.home()/'.config/quickshell/state/bar-state.json';saved=capture_bar(bar);cfg=json.loads(saved);results=[];started=time.monotonic()
command=['qs','ipc','-p',str(Path.home()/'.config/quickshell'),'call','bar'];initial=json.loads(sp.check_output(command+['layoutState']));ids=[m['id'] for m in initial['modules'] if m['id'] in ('ws','cpu','ram','gpu') or m['id'].startswith('disk:')];allids=[m['id'] for m in initial['modules']]
assert {'ws','cpu','ram','gpu'}<=set(ids) and any(i.startswith('disk:') for i in ids)
monitors=json.loads(sp.check_output(['hyprctl','-j','monitors']));signature=display_signature(monitors);active=json.loads(sp.check_output(['hyprctl','-j','activewindow'])).get('address');widths={}
reservation=Path(os.environ['XDG_RUNTIME_DIR'])/'43pr-bubbles'/os.environ['HYPRLAND_INSTANCE_SIGNATURE']/'reservation.txt';player=sp.check_output(['systemctl','--user','show','43pr-wallpaper-player.service','-p','MainPID','--value'],text=True)
# hyprctl reports integer client bounds; allow one logical pixel of rounding.
def overlaps(a,b):return a['x']<b['x']+b['width']-1.1 and a['x']+a['width']>b['x']+1.1 and a['y']<b['y']+b['height']-1.1 and a['y']+a['height']>b['y']+1.1
error=None
try:
 for position in ['left','right','top','bottom']:
  vertical=position in ('left','right')
  for interior in [False,True]:
   for mode in ['default','compact']:
    for margin in ([8,24] if not interior else [12]):
     assert display_signature(json.loads(sp.check_output(['hyprctl','-j','monitors'])))==signature
     cells={id:{'x':0 if vertical else i,'y':i if vertical else 0} for i,id in enumerate(ids)}
     group={'id':'free-test-margin','items':ids,'position':.4,'x':.4 if interior else 1 if position=='right' else 0,'y':.4 if interior else 1 if position=='bottom' else 0}
     value=dict(cfg,position=position,statsMode=mode,margin=margin,freeLayout=True,reserveSpace=True,groupRotations={},moduleGroups=[group],groupCells={group['id']:cells},startMods='',centerMods='',endMods='',hidden=','.join(i for i in allids if i not in ids))
     bar.write_text(json.dumps(value));time.sleep(.65);last=None
     for _ in range(40):
      state=json.loads(sp.check_output(command+['layoutState']));p=next(p for p in state['panels'] if p['id']==group['id']);r=p['geometry'];rows=[shlex.split(line) for line in reservation.read_text().splitlines()[1:] if line.strip()];row=next((x for x in rows if x[0]==r['output']),None)
      expected_x=margin*cfg['scale'] if interior or vertical else 0;expected_y=margin*cfg['scale'] if interior or not vertical else 0
      if row is None or abs(float(row[4])-r['height'])>.1 or abs(float(row[3])-r['width'])>.1 or [float(row[5]),float(row[6])]!=[expected_x,expected_y]:time.sleep(.05);continue
      monitor=next(m for m in monitors if m['name']==r['output']);obstacle={'x':r['x']+monitor['x']-expected_x,'y':r['y']+monitor['y']-expected_y,'width':r['width']+2*expected_x,'height':r['height']+2*expected_y}
      clients=[c for c in json.loads(sp.check_output(['hyprctl','-j','clients'])) if not c['floating'] and not c.get('fullscreen',0) and c['workspace']['id']==monitor['activeWorkspace']['id']]
      last=[{'address':c['address'],'x':c['at'][0],'y':c['at'][1],'width':c['size'][0],'height':c['size'][1]} for c in clients]
      if any(overlaps(c,obstacle) for c in last):time.sleep(.05);continue
      break
     else:raise AssertionError({'position':position,'mode':mode,'margin':margin,'interior':interior,'reservation':row,'panel':r,'clients':last})
     resource_widths={m['id']:m['geometry']['width'] for m in state['modules'] if m['id'] in ids and m['id']!='ws'}
     key=(position,interior,margin)
     if key in widths:assert all(abs(v-widths[key][id])<.02 for id,v in resource_widths.items()),(key,resource_widths,widths[key])
     widths[key]=resource_widths;results.append(dict(position=position,mode=mode,margin=margin,interior=interior,panel=r,gapX=expected_x,gapY=expected_y,widths=resource_widths,clients=last,window_overlap=False))
except BaseException as exc:
 error=repr(exc);(out/'failure.log').write_text(traceback.format_exc());raise
finally:
 restore_states({bar:saved})
 if active:sp.run(['hyprctl','dispatch','hl.dsp.focus({window='+json.dumps('address:'+active)+'})'],check=True,stdout=sp.DEVNULL)
 final=json.loads(sp.check_output(command+['layoutState']));assert bar.read_bytes()==saved and not final['manipulating'] and not final['input']['left']
 (out/'results.json').write_text(json.dumps({'checks':results,'error':error,'complete':len(results)==24,'source_fingerprints':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path.home()/'43pr-personnalise/.config/quickshell/Bar.qml',Path.home()/'43pr-personnalise/.config/quickshell/scripts/bar-layout.js']},'baseline_sha256':hashlib.sha256(saved).hexdigest(),'screens':monitors,'duration_seconds':time.monotonic()-started,'restored':True,'player_pid_unchanged':player==sp.check_output(['systemctl','--user','show','43pr-wallpaper-player.service','-p','MainPID','--value'],text=True),'expected_checks':24,'partial':True},indent=2))
assert len(results)==24
print(json.dumps({'checks':len(results),'failed':0,'restored':True,'duration_seconds':time.monotonic()-started,'tokens':'tokens non mesurés','partial':True,'scope':'mixed workspace/CPU/RAM/GPU/disk bubble; four bar positions; edges/interior; default/compact; actual window exclusion'}))
