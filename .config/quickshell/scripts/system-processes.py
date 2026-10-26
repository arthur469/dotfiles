#!/usr/bin/python3
"""Read-only bounded process snapshots for the existing 43PR statistics badges."""
import argparse,json,os,subprocess,time,signal,select
from pathlib import Path

def processes():
 result={};page=os.sysconf('SC_PAGE_SIZE')
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   text=(p/'stat').read_text();fields=text[text.rfind(')')+2:].split();result[int(p.name)]={'pid':int(p.name),'name':(p/'comm').read_text().strip(),'ticks':int(fields[11])+int(fields[12]),'start':fields[19],'memory':int(fields[21])*page/1048576,'ppid':int(fields[1]),'uid':p.stat().st_uid}
   try:result[int(p.name)]['exe']=os.readlink(p/'exe')
   except OSError:result[int(p.name)]['exe']=result[int(p.name)]['name']
  except (OSError,ValueError,IndexError):continue
 return result

def translated(fr,en):return fr if os.environ.get('LC_MESSAGES',os.environ.get('LANG','en')).lower().startswith('fr') else en

def group_processes(rows,kind,sort='usage',metadata=None,windows=None):
 metadata=metadata if metadata is not None else processes()
 if windows is None:
  try:windows=json.loads(subprocess.check_output(['hyprctl','-j','clients'],text=True,timeout=2))
  except (OSError,ValueError,subprocess.SubprocessError):windows=[]
 anchors={w['pid']:w.get('class') or metadata.get(w['pid'],{}).get('name','Application') for w in windows if w.get('pid') in metadata and w.get('mapped',True)}
 def key(pid):
  seen=set();q=pid;root=pid;exe=metadata.get(pid,{}).get('exe')
  while q in metadata and q not in seen:
   seen.add(q)
   if q in anchors:return 'app:'+anchors[q].casefold(),anchors[q],q
   parent=metadata[q].get('ppid',0)
   if parent in metadata and metadata[parent].get('exe')==exe and metadata[parent].get('uid')==metadata[pid].get('uid'):root=parent
   q=parent
  r=metadata.get(root,metadata.get(pid,{}));return 'pid:'+str(root)+':'+str(r.get('start','')),r.get('name','Process'),root
 buckets={};metrics={r['pid']:r for r in rows}
 relevant={key(pid)[0] for pid in metrics if pid in metadata}
 for pid,p in metadata.items():
  group,name,leader=key(pid)
  if group not in relevant:continue
  if group not in buckets:buckets[group]={'key':group,'name':{'brave-browser':'Brave','brave-browser-beta':'Brave Beta'}.get(name.casefold(),name),'pid':leader,'children':[],'members':[],'group':True}
  try:token=identity(pid)
  except (OSError,ValueError,IndexError):continue
  if token['identity']!=p.get('start'):continue
  row=dict(metrics.get(pid,{'pid':pid,'name':p['name'],'value':None if kind=='gpu' else 0,'memory':0 if kind=='gpu' else p['memory'],'display':'—'}));row.update(token)
  buckets[group]['children'].append(row)
  buckets[group]['members'].append({'pid':pid,'identity':token['identity']})
 result=[]
 for group in buckets.values():
  children=group['children'];known=[r['value'] for r in children if r['value'] is not None]
  group['value']=sum(known) if known else None;group['memory']=sum(r.get('memory',0) for r in children)
  group['canStop']=bool(children) and all(r['canStop'] for r in children)
  group['identity']=next((r['identity'] for r in children if r['pid']==group['pid']),'')
  group['display']=(f"{group['value']:.1f} %" if group['value'] is not None else '—') if kind!='ram' else f"{group['value'] or 0:.0f} MiB"
  if kind=='gpu':group['display']+=f" · {group['memory']:.0f} MiB"
  children.sort(key=lambda r: (r['name'].casefold(),r['pid']) if sort=='name' else (-float(r['value'] or 0),-r.get('memory',0),r['pid']))
  result.append(group)
 result.sort(key=lambda g: (g['name'].casefold(),g['pid']) if sort=='name' else (-float(g['value'] or 0),-g['memory'],g['name']))
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
  else:
   value=p['memory']
   try:
    for line in (Path('/proc')/str(pid)/'smaps_rollup').read_text().splitlines():
     if line.startswith('Pss:'):value=int(line.split()[1])/1024;break
   except (OSError,ValueError):pass
   display=f'{value:.0f} MiB'
  rows.append({'pid':pid,'name':p['name'],'value':value,'memory':p['memory'],'display':display})
 rows.sort(key=(lambda p:(p['name'].casefold(),p['pid'])) if sort=='name' else (lambda p:(p['value'],p['memory'])),reverse=sort!='name')
 return {'kind':kind,'processes':rows,'unit':'100 % = un cœur' if kind=='cpu' else 'Mémoire proportionnelle (PSS), RSS si indisponible','error':''}
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

def stop_group(members,force=False):
 if not isinstance(members,list) or not 1<=len(members)<=1024:raise ValueError('Groupe de processus invalide')
 handles=[];seen=set()
 try:
  for member in members:
   pid=member.get('pid');token=member.get('identity')
   if type(pid) is not int or pid in seen or not isinstance(token,str) or not token.isdigit():raise ValueError('Identité de groupe invalide')
   seen.add(pid)
   try:
    current=identity(pid)
    if current['identity']!=token:raise ValueError('Un processus a changé ; actualiser la liste')
    if not current['canStop']:raise PermissionError('Ce groupe contient un processus protégé')
    fd=os.pidfd_open(pid)
    if identity(pid)['identity']!=token:os.close(fd);raise ValueError('Le processus a changé')
    handles.append(fd)
   except FileNotFoundError:continue
  for fd in handles:
   try:signal.pidfd_send_signal(fd,signal.SIGKILL if force else signal.SIGTERM)
   except ProcessLookupError:pass
  ready=set(select.select(handles,[],[],.4)[0]) if handles else set()
  return {'success':True,'status':'exited' if len(ready)==len(handles) else 'sent','count':len(handles),'message':'Demande de fermeture envoyée.'}
 finally:
  for fd in handles:os.close(fd)

if __name__=='__main__':
 p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True);group.add_argument('--kind',choices=['cpu','ram','gpu']);group.add_argument('--stop-pid',type=int);group.add_argument('--stop-group');p.add_argument('--identity');p.add_argument('--force',action='store_true');p.add_argument('--sort',choices=['usage','name'],default='usage');p.add_argument('--language');a=p.parse_args()
 if a.language:os.environ['LC_MESSAGES']=a.language
 try:
  if a.stop_group is not None:
   if len(a.stop_group)>60000:raise ValueError('Groupe trop volumineux')
   data=stop_group(json.loads(a.stop_group),a.force)
  elif a.stop_pid is not None:
   if not a.identity or not a.identity.isdigit():raise ValueError('Identité de processus absente')
   data=stop(a.stop_pid,a.identity,a.force)
  else:
   data=snapshot(a.kind,a.sort);data['sort']=a.sort
   for row in data['processes']:
    try:row.update(identity(row['pid']))
    except (OSError,ValueError,IndexError):row.update(identity='',canStop=False,protected=False)
   data['groups']=group_processes(data['processes'],a.kind,a.sort)
  print(json.dumps(data,ensure_ascii=False))
 except Exception as error:
  print(json.dumps({'success':False,'message':str(error)},ensure_ascii=False));raise SystemExit(1)
