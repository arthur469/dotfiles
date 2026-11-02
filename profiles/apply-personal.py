#!/usr/bin/env python3
"""One-time profile installation. Preview by default; --apply backs up first."""
from pathlib import Path
import argparse,datetime,json,os,re,shutil,subprocess,tempfile

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args()
 home=Path.home();source=Path(__file__).resolve().parent/'arthur/files'
 if not source.is_dir():p.error('Personal profile is available on personal/arthur only.')
 uuid=subprocess.check_output(['findmnt','-no','UUID','/'],text=True).strip()
 if not re.fullmatch('[0-9a-fA-F-]{36}',uuid):p.error('Root UUID unavailable; review the volume mapping.')
 rows=[]
 for f in sorted(source.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(source);assert rel.parts[:2]==('.config','quickshell') or rel.parts[:2]==('.config','hypr') or rel.parts[:2]==('.config','fish')
  raw=f.read_text().replace('__ROOT_VOLUME_UUID__',uuid).replace('__PROFILE_HOME__',str(home))
  if f.suffix=='.json':json.loads(raw)
  rows.append((rel,raw))
 if not a.apply:
  print('Preview: '+str(len(rows))+' preference files; --apply backs up and installs them. Quickshell must be stopped.');return
 active=subprocess.run(['systemctl','--user','is-active','--quiet','43pr-quickshell.service']).returncode==0
 if active:p.error('Stop 43pr-quickshell.service before applying; restart it afterwards.')
 backup=home/'.local/state/43pr-profiles'/datetime.datetime.now().strftime('%Y%m%dT%H%M%S-%f');backup.mkdir(parents=True,mode=0o700)
 for rel,raw in rows:
  dest=home/rel
  if dest.exists():
   old=backup/rel;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,old)
  dest.parent.mkdir(parents=True,exist_ok=True)
  fd,tmp=tempfile.mkstemp(dir=dest.parent)
  try:
   with os.fdopen(fd,'w') as stream:stream.write(raw)
   os.chmod(tmp,0o600);os.replace(tmp,dest)
  finally:Path(tmp).unlink(missing_ok=True)
 print('Profile installed; previous preferences: '+str(backup))
if __name__=='__main__':main()
