#!/usr/bin/python3
"""Control the existing 43PR mpvpaper player; one decoder across workspaces."""
import argparse,json,os,socket,subprocess,time
from pathlib import Path
RUNTIME=Path(os.environ['XDG_RUNTIME_DIR']);MODE=RUNTIME/'43pr-wallpaper-mode.json';SOCKET=RUNTIME/'43pr-wallpaper.sock'
def command(*args):
 with socket.socket(socket.AF_UNIX) as connection:
  connection.settimeout(2);connection.connect(str(SOCKET));connection.sendall((json.dumps({'command':list(args),'request_id':43})+'\n').encode());data=b''
  while len(data)<65536:
   chunk=connection.recv(4096)
   if not chunk:break
   data+=chunk
   while b'\n' in data:
    line,data=data.split(b'\n',1);result=json.loads(line)
    if result.get('request_id')==43:
     if result.get('error')!='success':raise RuntimeError(result.get('error'))
     return result.get('data')
  raise RuntimeError('No mpv reply')
def mode():
 try:return json.loads(MODE.read_text()).get('mode','day')
 except (OSError,ValueError):return 'day'
def status():
 result={'mode':mode(),'available':SOCKET.exists(),'single_player_across_workspaces':True}
 if result['available']:
  try:result['paused']=command('get_property','pause')
  except (OSError,RuntimeError):result['available']=False
 return result
def change(selected,preview=False):
 result=status();result['target']=selected
 if preview:return dict(result,preview=True,verified=True)
 temporary=MODE.with_suffix('.tmp');temporary.write_text(json.dumps({'mode':selected}));temporary.chmod(0o600);temporary.replace(MODE)
 if result['available']:command('set_property','pause',selected=='night')
 after=status();return dict(after,verified=(not after['available'] or selected=='day' or after.get('paused') is True),skipped=not after['available'])
def start(path):
 source=Path(path).expanduser().resolve()
 if not source.is_file() or source.suffix.lower() not in {'.mp4','.mkv','.webm','.mov'}:raise ValueError('Unsupported wallpaper video')
 # This replaces only the user's native wallpaper player, never media players.
 subprocess.run(['pkill','-u',str(os.getuid()),'-x','mpvpaper'],check=False)
 SOCKET.unlink(missing_ok=True)
 script=Path(__file__).with_name('wallpaper-mode.lua');options='no-audio loop hwdec=auto input-ipc-server='+str(SOCKET)+' script='+str(script)
 if mode()=='night':options+=' pause=yes'
 log=Path.home()/'.cache/43pr/mpvpaper.log';log.parent.mkdir(parents=True,exist_ok=True)
 with log.open('ab') as output:subprocess.Popen(['mpvpaper','-p','-o',options,'*',str(source)],start_new_session=True,stdout=output,stderr=output)
 for _ in range(40):
  if SOCKET.exists():return status()
  time.sleep(.05)
 raise RuntimeError('Native wallpaper IPC did not start')
if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group();g.add_argument('--mode',choices=['day','night']);g.add_argument('--start');p.add_argument('--preview',action='store_true');a=p.parse_args()
 try:print(json.dumps(start(a.start) if a.start else change(a.mode,a.preview) if a.mode else status()))
 except Exception as error:print(json.dumps({'verified':False,'error':str(error)}));raise SystemExit(1)
