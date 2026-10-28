"""Private test fixtures: never restore state while its writer is still running."""
from pathlib import Path
import hashlib,json,os,subprocess as sp,tempfile,time
root=Path.home()/'.local/state/43pr-tests/baselines'
root.mkdir(parents=True,exist_ok=True,mode=0o700)
reserved=('free-test','free-check')
def capture_bar(path):
 path=Path(path)
 for _ in range(15):
  ipc=sp.run(['qs','ipc','-p',str(Path.home()/'.config/quickshell'),'call','bar','layoutState'],capture_output=True,text=True)
  try:
   status=json.loads(ipc.stdout)
   if ipc.returncode==0:break
  except ValueError:pass
  time.sleep(.2)
 else:raise RuntimeError('Bar IPC not ready; baseline not captured.')
 if status.get('manipulating'):raise RuntimeError('Manipulation utilisateur active ; différer les essais.')
 # Wait beyond the UI save debounce before taking the user's baseline.
 for _ in range(10):
  data=path.read_bytes();time.sleep(.6)
  if path.read_bytes()==data:break
 else:raise RuntimeError('Préférences encore en mouvement ; ne pas lancer les essais.')
 value=json.loads(data)
 if any(str(g.get('id','')).startswith(reserved) for g in value.get('moduleGroups',[])):
  raise RuntimeError('Profil temporaire déjà présent ; restaurer la disposition vérifiée avant de tester.')
 target=root/('avant-essai-'+str(time.time_ns())+'.json');target.write_bytes(data);target.chmod(0o600)
 return data
def restore_states(files):
 expected={Path(p):data for p,data in files.items()}
 sp.run(['systemctl','--user','stop','43pr-quickshell.service'],check=True)
 try:
  for path,data in expected.items():
   if data is None:path.unlink(missing_ok=True);continue
   fd,tmp=tempfile.mkstemp(dir=path.parent)
   try:
    with os.fdopen(fd,'wb') as output:output.write(data)
    os.chmod(tmp,0o600);os.replace(tmp,path)
   finally:Path(tmp).unlink(missing_ok=True)
 finally:sp.run(['systemctl','--user','start','43pr-quickshell.service'],check=True)
 time.sleep(1.4)
 for path,data in expected.items():
  if data is None:
   if path.exists():raise RuntimeError('Fichier recréé après restauration : '+str(path))
  elif path.read_bytes()!=data:raise RuntimeError('Restauration non conservée : '+str(path))
 bar=Path.home()/'.config/quickshell/state/bar-state.json'
 if bar.exists() and any(str(g.get('id','')).startswith(reserved) for g in json.loads(bar.read_text()).get('moduleGroups',[])):
  raise RuntimeError('Disposition de test toujours active après restauration.')
