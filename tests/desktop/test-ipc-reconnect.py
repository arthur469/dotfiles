#!/usr/bin/env python3
"""Regression native IPC, faux serveur isolé, aucune surface ni entrée réelle."""
import json,os,pathlib,socket,subprocess,threading,time,sys,shutil
binary=sys.argv[1];base=pathlib.Path(os.environ['XDG_RUNTIME_DIR'])/'hypr'/('p0-reconnect-'+str(os.getpid()));base.mkdir(mode=0o700)
stop=threading.Event();requests=[];listeners=[]
def listen(path):
 s=socket.socket(socket.AF_UNIX);s.bind(str(path));s.listen();s.settimeout(.2);listeners.append(s);return s
req=listen(base/'.socket.sock')
def serve():
 while not stop.is_set():
  try:c,_=req.accept()
  except TimeoutError:continue
  except OSError:return
  with c:
   d=c.recv(65536);requests.append(d.decode());c.sendall(b'{"configProvider":"lua"}' if b'status' in d else b'[]')
threading.Thread(target=serve,daemon=True).start()
(base/'shell.qml').write_text('''import QtQuick\nimport Quickshell\nimport Quickshell.Hyprland\nShellRoot { Connections { target: Hyprland; function onRawEvent(e) {console.log("PROBE",e.name,e.data)} function onEventSocketConnectedChanged(){console.log("CONNECTED",Hyprland.eventSocketConnected)} } }''')
env=dict(os.environ,HYPRLAND_INSTANCE_SIGNATURE=base.name)
log=open(base/'log','w+');p=subprocess.Popen([binary,'-p',str(base/'shell.qml'),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT);count=0;passed=[]
def accept(s):
 end=time.monotonic()+5
 while time.monotonic()<end:
  try:return s.accept()[0]
  except TimeoutError:pass
 raise AssertionError('Pas de reconnexion dans 5s')
try:
 # First connect fails; creating the socket later must recover without restart.
 time.sleep(2.2);ev=listen(base/'.socket2.sock');c=accept(ev);count+=1;c.sendall(b'p0_probe>>first\nold-fragment');time.sleep(.2);c.close();passed.append('Socket absent au démarrage : reprise après création')
 c=accept(ev);count+=1;c.sendall(b'p0_probe>>second\n');time.sleep(.2);c.close();ev.close();(base/'.socket2.sock').unlink();passed.append('Fragment interrompu abandonné ; deuxième connexion')
 time.sleep(2.2);ev=listen(base/'.socket2.sock');c=accept(ev);count+=1;c.sendall(b'p0_probe>>thi');time.sleep(.1);c.sendall(b'rd\np0_probe>>fourth\n');time.sleep(.2);c.close();time.sleep(.3);passed.append('Serveur supprimé/recréé : reconnexion, ligne fragmentée, événements groupés')
finally:
 p.terminate()
 try:p.wait(3)
 except subprocess.TimeoutExpired:p.kill();p.wait()
 stop.set()
 for s in listeners:s.close()
 log.flush();log.seek(0);text=log.read();log.close();shutil.rmtree(base)
assert 'PROBE p0_probe second' in text and 'PROBE p0_probe third' in text and 'PROBE p0_probe fourth' in text,text
assert text.count('CONNECTED true')==3 and text.count('CONNECTED false')==3,text
assert requests.count('j/clients')==3,requests
assert text.count('Unable to connect to hyprland event socket')<=7,'Boucle de reconnexion trop rapide'
print(json.dumps({'passed':passed,'connections':count,'model_refreshes':requests.count('j/clients'),'log':text},ensure_ascii=False,indent=2))
