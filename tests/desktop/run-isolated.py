#!/usr/bin/env python3
"""Existing isolated checks, private complete logs, compatible result reuse."""
import argparse
import datetime
import hashlib
import functools
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess as sp
import sys
import time
import tempfile
from runtime import quickshell
from selection import ALL_ISOLATED, impact, changed_symbols

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
QML = SOURCE/'.config/quickshell'


@functools.lru_cache(maxsize=512)
def content_digest(path, size, mtime_ns):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(path):
    path=Path(path)
    if not path.is_file():return '<missing>'
    stat=path.stat()
    return content_digest(str(path.resolve()),stat.st_size,stat.st_mtime_ns)


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def catalog(project):
    node=shutil.which('node') or str(Path.home()/'.local/opt/odysseus/node/bin/node')
    runtime=quickshell()
    definitions=[
        ('ipc-reconnect',[sys.executable,str(HERE/'test-ipc-reconnect.py'),runtime],[],25),
        ('async-save',[sys.executable,str(HERE/'test-async-save.py')],['Bar.qml'],15),
        ('layout',[node,str(HERE/'test-layout.cjs')],['scripts/bar-layout.js'],10),
        ('ipc-release',[node,str(HERE/'test-ipc-release.cjs')],['Bar.qml'],10),
        ('sizes',[node,str(HERE/'test-sizes.cjs')],['scripts/bar-layout.js'],10),
        ('legacy-storage',[node,str(HERE/'test-legacy-migration.cjs')],['scripts/bar-layout.js','scripts/storage-modules.js'],10),
        ('native-defaults',[node,str(HERE/'test-native-defaults.cjs')],['Bar.qml', 'BluetoothState.qml', 'Notifications.qml', 'PowerMenu.qml', 'QuickActions.qml', 'RecorderOSD.qml', 'SettingsWindow.qml', 'Theme.qml', 'Todo.qml', 'VolumeOsd.qml', 'SettingsPages/AppearancePage.qml', 'SettingsPages/BarPage.qml', 'SettingsPages/BluetoothPage.qml', 'SettingsPages/DisplayPage.qml', 'SettingsPages/KeybindsPage.qml', 'SettingsPages/SystemPage.qml', 'SettingsPages/ThemesPage.qml', 'SettingsPages/UpdatesPage.qml', 'colorpicker/ColorPicker.qml', 'colorpicker/ColorPickerEditor.qml', 'hyprquickpaper/shell.qml', 'Bar.qml', 'SettingsPages/BarPage.qml', '../hypr/keybinds.lua', 'SettingsPages/KeybindsPage.qml', '../../tests/fixtures/upstream-defaults-50bab24.json','../../profiles/personal-defaults.json'],10),
        ('updater-safety',[sys.executable,str(HERE/'test-updater-safety.py')],['../../update.sh','../../update2.sh'],20),
        ('carousel-bindings',[sys.executable,str(HERE/'test-carousel-bindings.py')],['../hypr/keybinds.lua','window-carousel/bindings.lua','../../tests/fixtures/native-chords-50bab24.json','/usr/bin/lua'],10),
        ('native-migration',[sys.executable,str(HERE/'test-native-migration.py')],['Bar.qml','scripts/storage-modules.js','scripts/bar-layout.js'],10),
        ('native-badge',[sys.executable,str(HERE/'test-native-badge.py')],['Bar.qml','../../tests/fixtures/native-stat-badge-50bab24.qmlpart'],15),
        ('style-choice',[node,str(HERE/'test-style-choice.cjs')],['Bar.qml','SettingsPages/BarPage.qml','scripts/storage-modules.js'],10),
        ('lifecycle',[node,str(HERE/'test-lifecycle.cjs')],['Bar.qml'],10),
        ('slider',[sys.executable,str(HERE/'test-slider.py')],['Slider.qml'],15),
        ('component-states',[sys.executable,str(HERE/'test-components.py')],['Bar.qml'],30),
        ('surface',[sys.executable,str(HERE/'test-surface.py')],['BarSurface.qml'],15),
        ('shared-gestures',[node,str(HERE/'test-shared-gestures.cjs')],['Bar.qml','scripts/bar-layout.js'],10),
        ('selection',[sys.executable,str(HERE/'test-selection.py')],['Bar.qml'],15),
        ('edge-margin',[node,str(HERE/'test-edge-margin.cjs'),shutil.which('c++') or 'c++'],['Bar.qml','scripts/bar-layout.js','../hypr/plugins/bubble-reserve/geometry.hpp','../../tests/desktop/test-edge-margin.cpp',shutil.which('c++') or 'c++'],20),
        ('bubble-geometry',[sys.executable,str(HERE/'test-bubbles.py')],['Bar.qml','BarSurface.qml','scripts/bar-layout.js','scripts/storage-modules.js'],20),
        ('wallpaper-control',[sys.executable,str(HERE/'test-wallpaper.py')],['hyprquickpaper/live-control.py','hyprquickpaper/wallpaper-mode.lua','../../tests/desktop/wallpaper_render.py','/usr/lib/libmpv.so.2'],15),
        ('workspace-clicks',[sys.executable,str(HERE/'test-workspaces.py')],['Bar.qml'],15),
        ('settings-escape',[sys.executable,str(HERE/'test-settings-escape.py')],['SettingsWindow.qml'],12),
        ('storage-layout',[node,str(QML/'scripts/tests/test-storage-modules.cjs')],['scripts/storage-modules.js','scripts/bar-layout.js'],10),
        ('storage-data',[sys.executable,str(QML/'scripts/tests/test_storage_process_sort.py')],['scripts/disk-usage.py','scripts/system-processes.py'],10),
    ]
    # Every runner change invalidates its own result contracts. Runtime, packages
    # and all support files are explicit, immutable evidence in each record.
    return {name:{'command':cmd,'dependencies':[QML/p for p in deps]+[Path(cmd[1]),HERE/'runtime.py',
                   HERE/'selection.py',Path(__file__)]+([HERE/'regression.py',HERE/'state.py'] if name=='selection' else []),'timeout':timeout} for name,cmd,deps,timeout in definitions}


def environment():
    packages=sp.run(['pacman','-Q'],capture_output=True,text=True,check=True).stdout
    runtime=quickshell()
    fixed=Path.home()/'.local/opt/quickshell-p0/bin/qs'
    return {'runtime': {runtime:digest(runtime),str(fixed):digest(fixed)},
            'packages_sha256':hashlib.sha256(packages.encode()).hexdigest(),
            'python':sys.version,'platform':list(os.uname()),
            'variables':{k:os.environ.get(k) for k in ('LANG','LC_ALL','QT_QPA_PLATFORM','QT_QUICK_BACKEND',
                 'QSG_RHI_BACKEND','QT_SCALE_FACTOR','QS_TEST_BINARY','XDG_RUNTIME_DIR','WAYLAND_DISPLAY','DISPLAY','PYTHONPATH','PYTHONHOME',
                 'PYTHONUSERBASE','PYTHONNOUSERSITE','LD_LIBRARY_PATH','QML_IMPORT_PATH','QML2_IMPORT_PATH',
                 'QT_PLUGIN_PATH','NODE_PATH','FONTCONFIG_FILE','FONTCONFIG_PATH')},
            'data':'deterministic embedded fixtures; isolated fake Hyprland transport; no desktop pointer',
            'isolation_policy':'private-xdg-offscreen-v1; HOME kept for source fixtures',
            'workers':1, 'libraries':runtime_libraries(runtime), 'fonts':font_fingerprints(),
            'bundled_qml':runtime_assets(runtime)}


def runtime_assets(binary):
    folder=Path(binary).resolve().parent.parent/'lib/qt6/qml'
    return {str(p):digest(p) for p in sorted(folder.rglob('*')) if p.is_file() and
            (p.suffix in ('.qml','.js') or p.name=='qmldir' or '.so' in p.name)}


def font_fingerprints():
    # Native text geometry depends on the selected face and fontconfig options,
    # including manually installed fonts which package versions cannot describe.
    result={}
    for query in ('JetBrainsMono Nerd Font','JetBrainsMono Nerd Font:weight=bold','monospace','sans-serif'):
        pattern=sp.check_output(['fc-match','-v',query],text=True)
        filename=sp.check_output(['fc-match','-f','%{file}',query],text=True)
        result[query]={'file':filename,'sha256':digest(filename),'pattern_sha256':hashlib.sha256(pattern.encode()).hexdigest()}
    return result


def runtime_libraries(binary):
    result=sp.run(['ldd',binary],capture_output=True,text=True,check=True)
    paths=[]
    for line in result.stdout.splitlines():
        for token in line.split():
            if token.startswith('/') and Path(token).is_file():paths.append(Path(token).resolve())
    return {str(p):{'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in paths}


def fingerprint(case, env):
    return {'environment':env,'command':case['command'],'timeout':case['timeout'],
            'files':{str(p):digest(p) for p in case['dependencies']},
            'executable':digest(shutil.which(case['command'][0]) or case['command'][0])}


def reusable(record, key):
    return bool(record and record.get('fingerprint')==key and record.get('status')=='passed'
                and Path(record.get('log','')).is_file() and digest(record['log'])==record.get('log_sha256'))


def run_one(case_id, case, output, env, previous=(), reuse=True, on_start=None):
    details=fingerprint(case,env);key=canonical(details)
    compatible=[r for r in previous if r.get('id')==case_id and r.get('fingerprint')==key]
    failures=[r for r in compatible if r['status'] not in ('passed','reused')]
    cached=next((r for r in reversed(compatible) if reusable(r,key)),None)
    if reuse and cached and not failures:
        return dict(cached,status='reused',source_status='passed',duration_seconds=0,
                    original_duration_seconds=cached['duration_seconds'])
    attempt=str(time.time_ns())
    log=output/(case_id.replace('/','-')+'.log')
    if on_start:on_start({'id':case_id,'attempt_id':attempt,'status':'running','fingerprint':key,'log':str(log.resolve())})
    started=time.monotonic();code=None;status='interrupted';error=None
    try:
        with log.open('w') as stream, tempfile.TemporaryDirectory(prefix='43pr-isolated-') as private:
            # Keep the source HOME: the existing fixtures locate their production
            # components there. Disconnect display/audio/session sockets and put
            # all XDG writes in a disposable directory instead of the live desktop.
            child_env = dict(os.environ)
            for name in ('WAYLAND_DISPLAY', 'DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE',
                         'DBUS_STARTER_ADDRESS', 'DBUS_STARTER_BUS_TYPE'):
                child_env.pop(name, None)
            for name, folder in (('XDG_RUNTIME_DIR', 'runtime'), ('XDG_CONFIG_HOME', 'config'),
                                 ('XDG_CACHE_HOME', 'cache'), ('XDG_DATA_HOME', 'data'),
                                 ('XDG_STATE_HOME', 'state')):
                location = Path(private) / folder
                location.mkdir(mode=0o700)
                child_env[name] = str(location)
            # The fake IPC fixture expects Hyprland's runtime parent to exist.
            (Path(private) / 'runtime/hypr').mkdir(mode=0o700)
            child_env['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=' + str(Path(private) / 'runtime/bus')
            child_env['QT_QPA_PLATFORM'] = 'offscreen'
            process=sp.Popen(case['command'],stdout=stream,stderr=sp.STDOUT,
                             start_new_session=True,env=child_env)
            try:
                code=process.wait(timeout=case['timeout'])
                status='passed' if code==0 else 'failed'
            except BaseException:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:process.wait(timeout=3)
                except sp.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
                raise
    except sp.TimeoutExpired as e:
        status='timeout';code=124;error=str(e)
    except KeyboardInterrupt:
        status='interrupted';code=130;error='interrupted'
    except BaseException as e:
        status='failed';code=1;error=repr(e)
    if status=='passed' and canonical(fingerprint(case,env))!=key:
        status='invalidated_during_run';code=1;error='code/tests/parameters changed during execution'
    if status=='passed' and failures:status='passed_after_failure'
    return {'id':case_id,'attempt_id':attempt,'status':status,'returncode':code,'duration_seconds':time.monotonic()-started,
            'fingerprint':key,'evidence':details,'log':str(log.resolve()),'log_sha256':digest(log),
            'output_bytes':log.stat().st_size if log.exists() else 0,
            'prior_failures':[{'log':r.get('log'),'status':r['status']} for r in failures], 'error':error}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path.home()/'Documents/ChatGPT/Migration Linux')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--fresh',action='store_true',help='run rather than reuse compatible successes')
    parser.add_argument('--cases',help='comma-separated stable executable case identifiers')
    parser.add_argument('--symbol',action='append',default=[],help='changed production function/component, e.g. Bar.qml:ResourceBadge')
    parser.add_argument('--changed',action='append',default=[],help='changed file; uncertain impact widens selection')
    parser.add_argument('--before-bar',type=Path,help='compare saved Bar.qml to loaded source at function/component level')
    parser.add_argument('--list',action='store_true')
    args=parser.parse_args()
    if os.environ.get('PR43_TEST_QML') or os.environ.get('PR43_BUBBLE_CHECK','all')!='all':parser.error('run the candidate renderer checks directly; this entry tests the active source tree')
    plan=impact(args.symbol,args.changed)
    if args.before_bar:
        symbols=changed_symbols(args.before_bar.read_text(),(QML/'Bar.qml').read_text())
        plan=impact(args.symbol+symbols,args.changed)
    definitions=catalog(args.project.resolve())
    chosen=args.cases.split(',') if args.cases else plan['isolated']
    if not chosen or len(chosen)!=len(set(chosen)) or set(chosen)-set(definitions):parser.error('invalid/duplicate case selection')
    scope={'selected':chosen,'excluded':{k:'not selected by explicit cases or impact map' for k in definitions if k not in chosen},
           'partial':set(chosen)!=set(definitions),'impact':plan}
    if args.list:print(json.dumps(scope,indent=2,ensure_ascii=False));return 0
    lock_path=Path.home()/'.local/state/43pr-tests/isolated.lock'
    lock_path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=lock_path.open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:parser.error('another isolated regression run is active')
    started=time.monotonic();out=(args.output or Path.home()/'.local/state/43pr-tests/isolated'/datetime.datetime.now().strftime('%Y%m%dT%H%M%S-%f')).resolve()
    out.mkdir(parents=True,exist_ok=False,mode=0o700)
    ledger=Path.home()/'.local/state/43pr-tests/isolated-history.jsonl';ledger.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    previous=[]
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            try:previous.append(json.loads(line))
            except ValueError:pass  # truncated final record is never reusable
    # A completed record supersedes its own running marker. An orphan marker
    # is evidence of interruption and prevents unconditional success reuse.
    attempts={}
    for index,record in enumerate(previous):attempts[record.get('attempt_id','legacy-'+str(index))]=record
    previous=list(attempts.values())
    def persist(record):
        with ledger.open('a') as stream:stream.write(json.dumps(record,sort_keys=True)+'\n')
        ledger.chmod(0o600)
    env=environment();records=[];interrupted=False
    def interrupt(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupt)
    for name in chosen:
        record=run_one('isolated/'+name,definitions[name],out,env,previous,not args.fresh,on_start=persist)
        # Slash is part of the stable ID; log filenames use a plain basename.
        records.append(record)
        if record['status']!='reused':
            persist(record)
        if record['status']=='interrupted':interrupted=True;break
    if not interrupted and canonical(environment())!=canonical(env):
        for record in records:
            record.update(status='environment_changed',returncode=1,error='runtime/dependencies/environment changed during run')
            persist(record)
    failures=[r for r in records if r['status'] in ('failed','timeout','interrupted','invalidated_during_run','environment_changed')]
    code=130 if interrupted else next((r['returncode'] or 1 for r in failures),0)
    if code<0:code=128-code
    result={'scope':scope,'results':records,'duration_seconds':time.monotonic()-started,'returncode':code,
            'executed':sum(r['status']!='reused' for r in records),'reused':sum(r['status']=='reused' for r in records),
            'failed':len(failures),'qualified':sum(r['status']=='passed_after_failure' for r in records),
            'not_run':len(chosen)-len(records),'log_bytes':sum(r.get('output_bytes',0) for r in records if r['status']!='reused'),
            'tokens':'tokens non mesurés'}
    (out/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
    summary={k:result[k] for k in ('executed','reused','failed','qualified','not_run','duration_seconds','returncode','tokens')}
    summary.update(partial=scope['partial'],scope=chosen,report=str(out/'results.json'))
    print(json.dumps(summary,ensure_ascii=False))
    for record in failures:
        lines=Path(record['log']).read_text(errors='replace').splitlines() if Path(record['log']).exists() else []
        print(f"{record['id']}: {record['status']}; full log: {record['log']}")
        print('\n'.join(lines[-8:]))
    return code


if __name__=='__main__':sys.exit(main())
