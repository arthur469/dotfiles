#!/usr/bin/python3
"""Read-only bounded process snapshots for the existing 43PR statistics badges."""
import argparse,json,os,subprocess,time,signal,select
from pathlib import Path

def processes():
 result={};page=os.sysconf('SC_PAGE_SIZE')
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   text=(p/'stat').read_text();fields=text[text.rfind(')')+2:].split();result[int(p.name)]={'pid':int(p.name),'name':(p/'comm').read_text().strip(),'ticks':int(fields[11])+int(fields[12]),'start':fields[19],'memory':int(fields[21])*page/1048576}
  except (OSError,ValueError,IndexError):continue
 return result

def snapshot(kind,sort="usage"):
 if kind=='gpu':
  try:r=subprocess.run(['nvidia-smi','pmon','-c','1','-s','um'],capture_output=True,text=True,timeout=4,check=True)
  except (OSError,subprocess.SubprocessError):return {'kind':kind,'processes':[],'error':'Détail GPU par processus indisponible sur ce pilote.'}
  rows=[]
  for line in r.stdout.splitlines():
   parts=line.split(None,11)
   if len(parts)<12 or not parts[0].isdigit() or not parts[1].isdigit() or parts[0]!='0':continue
   try:pid=int(parts[1]);memory=float(parts[9]) if parts[9]!='-' else 0;usage=float(parts[3]) if parts[3]!='-' else None
   except ValueError:continue
   name=parts[11]
   try:name=(Path('/proc')/str(pid)/'comm').read_text().strip()
   except OSError:pass
   rows.append({'pid':pid,'name':name,'value':usage,'memory':memory,'display':('—' if usage is None else f'{usage:.0f}')+f' % · {memory:.0f} MiB'})
  rows.sort(key=(lambda p:(p['name'].casefold(),p['pid'])) if sort=='name' else (lambda p:(-1 if p['value'] is None else p['value'],p['memory'])),reverse=sort!='name')
  return {'kind':kind,'processes':rows,'unit':'GPU · mémoire vidéo','error':''}
 first=processes();elapsed=time.monotonic()
 if kind=='cpu':time.sleep(.25)
 second=processes();elapsed=time.monotonic()-elapsed;rows=[]
 for pid,p in second.items():
  if kind=='cpu':
   old=first.get(pid)
   if not old or old['start']!=p['start']:continue
   value=max(0,100*(p['ticks']-old['ticks'])/os.sysconf('SC_CLK_TCK')/elapsed);display=f'{value:.1f} %'
  else:value=p['memory'];display=f'{value:.0f} MiB'
  rows.append({'pid':pid,'name':p['name'],'value':value,'memory':p['memory'],'display':display})
 rows.sort(key=(lambda p:(p['name'].casefold(),p['pid'])) if sort=='name' else (lambda p:(p['value'],p['memory'])),reverse=sort!='name')
 return {'kind':kind,'processes':rows,'unit':'100 % = un cœur' if kind=='cpu' else 'Mémoire résidente','error':''}
def identity(pid):
 p=Path('/proc')/str(pid)
 text=(p/'stat').read_text();fields=text[text.rfind(')')+2:].split()
 name=(p/'comm').read_text().strip()
 uid=p.stat().st_uid
 protected=name in {'Hyprland','systemd','qs','quickshell'} or pid in {1,os.getpid(),os.getppid()}
 return {'identity':fields[19],'canStop':uid==os.getuid() and not protected,'protected':protected}

def stop(pid,token,force=False):
 if pid<=1:raise PermissionError('Ce processus est protégé')
 try:current=identity(pid)
 except FileNotFoundError:return {'success':True,'pid':pid,'status':'exited','message':'Le processus est déjà fermé.'}
 if current['identity']!=token:raise ValueError('Le processus a changé ; actualiser la liste')
 if not current['canStop']:raise PermissionError('Ce processus système ou de session est protégé')
 descriptor=os.pidfd_open(pid)
 try:
  if identity(pid)['identity']!=token:raise ValueError('Le processus a changé ; actualiser la liste')
  signal.pidfd_send_signal(descriptor,signal.SIGKILL if force else signal.SIGTERM)
  exited=bool(select.select([descriptor],[],[],.4)[0])
 finally:os.close(descriptor)
 return {'success':True,'pid':pid,'status':'exited' if exited else 'sent','message':'Arrêt forcé envoyé.' if force else 'Demande de fermeture envoyée.'}

if __name__=='__main__':
 p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True);group.add_argument('--kind',choices=['cpu','ram','gpu']);group.add_argument('--stop-pid',type=int);p.add_argument('--identity');p.add_argument('--force',action='store_true');p.add_argument('--sort',choices=['usage','name'],default='usage');a=p.parse_args()
 try:
  if a.stop_pid is not None:
   if not a.identity or not a.identity.isdigit():raise ValueError('Identité de processus absente')
   data=stop(a.stop_pid,a.identity,a.force)
  else:
   data=snapshot(a.kind,a.sort);data['sort']=a.sort
   for row in data['processes']:
    try:row.update(identity(row['pid']))
    except (OSError,ValueError,IndexError):row.update(identity='',canStop=False,protected=False)
  print(json.dumps(data,ensure_ascii=False))
 except Exception as error:
  print(json.dumps({'success':False,'message':str(error)},ensure_ascii=False));raise SystemExit(1)
