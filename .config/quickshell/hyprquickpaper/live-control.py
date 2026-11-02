#!/usr/bin/python3
"""Control the native 43PR mpvpaper player independently of shell restarts."""
import argparse,fcntl,json,os,shutil,socket,subprocess,time
from pathlib import Path
RUNTIME=Path(os.environ['XDG_RUNTIME_DIR']);MODE=RUNTIME/'43pr-wallpaper-mode.json';SOCKET=RUNTIME/'43pr-wallpaper.sock'
CACHE=Path.home()/'.cache/43pr/last-live';UNIT='43pr-wallpaper-player.service'
VIDEOS={'.mp4','.mkv','.webm','.mov'}
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
def selected_video():
 if not CACHE.exists():return None
 raw=CACHE.read_text().strip()
 if not raw:return None
 source=Path(raw).expanduser().resolve()
 if not source.is_file() or source.suffix.lower() not in VIDEOS:raise ValueError('Selected animated wallpaper is missing or invalid')
 return source
def status():
 result={'mode':mode(),'available':SOCKET.exists(),'selected_video':CACHE.exists(),'single_player_across_workspaces':True}
 if result['available']:
  try:result['paused']=command('get_property','pause')
  except (OSError,RuntimeError):result['available']=False
 return result
def stop(forget=False):
 if shutil.which('systemctl'):subprocess.run(['systemctl','--user','stop',UNIT],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False,timeout=8)
 subprocess.run(['pkill','-u',str(os.getuid()),'-x','mpvpaper'],check=False)
 SOCKET.unlink(missing_ok=True)
 if forget:CACHE.unlink(missing_ok=True)
def start(path):
 source=Path(path).expanduser().resolve()
 if not source.is_file() or source.suffix.lower() not in VIDEOS:raise ValueError('Unsupported wallpaper video')
 stop();CACHE.parent.mkdir(parents=True,exist_ok=True);remember=CACHE.with_suffix('.tmp');remember.write_text(str(source)+'\n');remember.replace(CACHE)
 script=Path(__file__).with_name('wallpaper-mode.lua');options='no-audio loop hwdec=auto panscan=1 input-ipc-server='+str(SOCKET)+' script='+str(script)
 if mode()=='night':options+=' pause=yes'
 args=['mpvpaper','-p','-o',options,'*',str(source)]
 # setsid alone does not escape the Quickshell systemd cgroup. A transient
 # sibling unit preserves the same native player through shell maintenance.
 if shutil.which('systemd-run') and subprocess.run(['systemctl','--user','show-environment'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
  launch=['systemd-run','--user','--collect','--unit='+UNIT,'--service-type=exec','--property=Restart=on-failure','--property=RestartSec=2','--property=StartLimitIntervalSec=30','--property=StartLimitBurst=3','--property=PartOf=graphical-session.target']
  for key in ['WAYLAND_DISPLAY','XDG_RUNTIME_DIR','HYPRLAND_INSTANCE_SIGNATURE','DISPLAY','LIBVA_DRIVER_NAME','GBM_BACKEND','__GLX_VENDOR_LIBRARY_NAME','__NV_PRIME_RENDER_OFFLOAD','DRI_PRIME','VK_ICD_FILENAMES','VK_DRIVER_FILES']:
   if key in os.environ:launch.append('--setenv='+key+'='+os.environ[key])
  result=subprocess.run(launch+args,capture_output=True,text=True,timeout=10)
  if result.returncode:raise RuntimeError('Native wallpaper service could not start: '+result.stderr.strip())
 else:
  log=Path.home()/'.cache/43pr/mpvpaper.log';log.parent.mkdir(parents=True,exist_ok=True)
  with log.open('ab') as output:subprocess.Popen(args,start_new_session=True,stdout=output,stderr=output)
 for _ in range(60):
  if SOCKET.exists():
   result=status()
   if result['available']:
    try:
     if isinstance(command('get_property','time-pos'),(int,float)):return result
    except (OSError,RuntimeError):pass  # IPC can open before mpv has loaded the file.
  time.sleep(.05)
 raise RuntimeError('Native wallpaper IPC did not start')
def playback_expected():
 # Keep native visibility auto-pause on sleeping outputs and fullscreen desks.
 # Unknown compositor state must not become a claimed playback verification.
 try:
  screens=json.loads(subprocess.check_output(['hyprctl','-j','monitors'],text=True,timeout=2))
  workspaces=json.loads(subprocess.check_output(['hyprctl','-j','workspaces'],text=True,timeout=2))
  visible=[s for s in screens if s.get('dpmsStatus',True) and not s.get('disabled',False)]
  for screen in visible:
   workspace=next((w for w in workspaces if w['id']==screen.get('activeWorkspace',{}).get('id')),None)
   if workspace is None:return None
   if not workspace.get('hasfullscreen',False):return True
  return False
 except (OSError,ValueError,subprocess.SubprocessError,KeyError,TypeError):return None

def probe_playback():
 # mpvpaper's visibility deadman runs every two seconds. An immediate pause=false
 # readback misses a delayed re-pause; observe beyond that boundary.
 before=command('get_property','time-pos');time.sleep(2.25)
 after=command('get_property','time-pos');paused=command('get_property','pause')
 return {'advanced':isinstance(before,(int,float)) and isinstance(after,(int,float))
                    and abs(after-before)>.03 and paused is False,
         'before':before,'after':after,'paused':paused}

def change(selected,preview=False):
 before=status();before['target']=selected
 if preview:return dict(before,preview=True,would_restart=selected=='day' and not before['available'] and CACHE.exists(),verified=True)
 temporary=MODE.with_suffix('.tmp');temporary.write_text(json.dumps({'mode':selected}));temporary.chmod(0o600);temporary.replace(MODE)
 restarted=False
 if selected=='day' and not before['available']:
  source=selected_video()
  if source is not None:start(source);restarted=True
 if status()['available']:command('set_property','pause',selected=='night')
 selected_exists=CACHE.exists();playback=None;recovery=None
 expected=playback_expected() if selected=='day' and selected_exists else False
 if expected is True and status()['available']:
  playback=probe_playback()
  # A hotplug or a night pause can leave the existing player's visibility state
  # stuck while its IPC still answers. Recover the same native player and video.
  if not playback['advanced']:expected=playback_expected()
  if not playback['advanced'] and expected is True:
   recovery=playback;source=selected_video()
   if source is None:raise RuntimeError('Selected animated wallpaper disappeared during recovery')
   position=recovery['after'];start(source);restarted=True
   if isinstance(position,(int,float)):command('seek',position,'absolute+exact')
   playback=probe_playback()
  if expected is True and not playback['advanced']:raise RuntimeError('Animated wallpaper remains frozen after recovery: '+json.dumps({'initial':recovery,'final':playback}))
 after=status()
 verified=after['available'] and (selected=='day' or after.get('paused') is True)
 if selected=='night' and not after['available']:verified=True
 if selected=='day' and not selected_exists:verified=True
 if not verified:raise RuntimeError('Animated wallpaper mode could not be verified')
 return dict(after,verified=verified,restarted=restarted,skipped=not selected_exists,
             playback_verification='progress' if playback and playback['advanced'] else 'hidden' if expected is False else 'unavailable',
             playback=playback,initial_stall=recovery)
if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group();g.add_argument('--mode',choices=['day','night']);g.add_argument('--start');g.add_argument('--stop',action='store_true');p.add_argument('--preview',action='store_true');a=p.parse_args()
 try:
  if a.start or a.stop or (a.mode and not a.preview):
   with (RUNTIME/'43pr-wallpaper-control.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if a.stop:stop(True);result=dict(status(),verified=True)
    else:result=start(a.start) if a.start else change(a.mode)
  else:result=change(a.mode,True) if a.mode else status()
  print(json.dumps(result))
 except Exception as error:print(json.dumps({'verified':False,'error':str(error)}));raise SystemExit(1)
