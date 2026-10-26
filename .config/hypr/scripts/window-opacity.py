#!/usr/bin/python3
"""Session window exceptions and workspace inheritance, with transient previews."""
import argparse,json,re,subprocess,sys,os,fcntl,importlib.util
from pathlib import Path

def ctl(*args):return subprocess.check_output(['hyprctl',*args],text=True,timeout=5)
def atomic(path,value):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value));tmp.chmod(0o600);tmp.replace(path)
def read(path,default):return json.loads(path.read_text()) if path.exists() else default

def status():
 windows=json.loads(ctl('-j','clients'));active=json.loads(ctl('-j','activewindow'));ws=json.loads(ctl('-j','activeworkspace'))
 runtime=Path(os.environ['XDG_RUNTIME_DIR'])/'43pr-opacity';saved=read(runtime/'windows.json',{});values=read(Path.home()/'.config/hypr/workspace-opacity.json',{})
 a=active.get('address');entry=saved.get(a,{})
 if entry.get('pid')!=active.get('pid'):entry={}
 workspace=ws.get('id',1);default=values.get(str(workspace),1.0)
 return {'workspace':workspace,'workspaceValue':default,'window':{'address':a,'title':active.get('title',''),'class':active.get('class',''),'locked':bool(entry),'value':entry.get('value',default),'fullscreen':active.get('fullscreen',0)==2 or active.get('fullscreenClient',0)==2},'windows':len(windows)}

def apply(address=None,value=None,sync=False,workspace=None,preview=False,cancel=False,reset_all=False):
 runtime=Path(os.environ['XDG_RUNTIME_DIR'])/'43pr-opacity';runtime.mkdir(mode=0o700,exist_ok=True)
 if value is not None and (round(value*100) not in range(40,101) or abs(round(value*100)/100-value)>1e-6):raise ValueError('Opacity must be between 40 and 100 percent')
 with (runtime/'lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  windows={c['address']:c for c in json.loads(ctl('-j','clients')) if c.get('mapped')}
  p=runtime/'windows.json';saved={a:v for a,v in read(p,{}).items() if a in windows and v.get('pid')==windows[a]['pid']}
  previews=read(runtime/'preview.json',{})
  if reset_all:saved={};previews={}
  elif cancel:previews={}
  elif not sync:
   if workspace is not None:
    if type(workspace) is not int or not 1<=workspace<=9999 or value is None:raise ValueError('Select a normal workspace')
    if preview:previews={'workspace':workspace,'value':value}
    else:
     spec=importlib.util.spec_from_file_location('workspace_opacity',Path(__file__).with_name('workspace-opacity.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
     module.apply(workspace,value,reload=False);previews={}
   else:
    if not address or not re.fullmatch(r'0x[0-9a-fA-F]+',address) or address not in windows:raise ValueError('This window is closed')
    if preview:previews={'window':address,'value':value}
    else:
     if value is None:saved.pop(address,None)
     else:saved[address]={'pid':windows[address]['pid'],'value':value}
     previews={}
  values=read(Path.home()/'.config/hypr/workspace-opacity.json',{})
  commands=[]
  for a,c in windows.items():
   desired=saved[a]['value'] if a in saved else values.get(str(c['workspace']['id']),1.0)
   if previews.get('window')==a:desired=previews['value']
   if previews.get('workspace')==c['workspace']['id'] and a not in saved:desired=previews['value']
   fullscreen=c.get('fullscreen',0)==2 or c.get('fullscreenClient',0)==2
   selector=json.dumps('address:'+a)
   for prop,number in [('opacity',1.0 if fullscreen else desired),('opacity_inactive',1.0 if fullscreen else desired),('opacity_override',1),('opacity_inactive_override',1),('opaque',1 if fullscreen else 0)]:
    commands.append('dispatch hl.dsp.window.set_prop({window='+selector+',prop='+json.dumps(prop)+',value='+json.dumps(str(number))+'})')
  if commands:
   result=ctl('--batch',';'.join(commands))
   if any(line.strip() not in ['ok',''] for line in result.splitlines()):raise RuntimeError(result.strip())
  atomic(p,saved);atomic(runtime/'preview.json',previews)
 return {'success':True,'lockedWindows':len(saved),'preview':preview}

def main():
 p=argparse.ArgumentParser();p.add_argument('--window');p.add_argument('--workspace',type=int);p.add_argument('--set',type=float);p.add_argument('--reset',action='store_true');p.add_argument('--reset-all',action='store_true');p.add_argument('--sync',action='store_true');p.add_argument('--status',action='store_true');p.add_argument('--preview',action='store_true');p.add_argument('--cancel',action='store_true');a=p.parse_args()
 if a.status:print(json.dumps(status()));return
 if a.sync or a.cancel or a.reset_all:print(json.dumps(apply(sync=a.sync,cancel=a.cancel,reset_all=a.reset_all)));return
 if a.set is None and not a.reset:
  subprocess.run(['qs','ipc','-p',str(Path.home()/'.config/quickshell'),'call','opacity','openControl','window'],check=True);return
 address=a.window
 if a.workspace is None and not address:address=json.loads(ctl('-j','activewindow')).get('address')
 print(json.dumps(apply(address,None if a.reset else a.set,workspace=a.workspace,preview=a.preview)))
if __name__=='__main__':
 try:main()
 except Exception as error:print(json.dumps({'success':False,'error':str(error)}));raise SystemExit(1)
