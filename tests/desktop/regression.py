#!/usr/bin/env python3
"""Authorized desktop regression: every detected input area, stable baseline restored.
Requires --allow-desktop. Logs are private and never written in the source tree.
"""
from pathlib import Path
import argparse,datetime,json,os,subprocess as sp,time,shlex
from state import capture_bar,restore_states
from runtime import quickshell

class Desktop:
    def __init__(self,out):
        self.qs=quickshell();self.transport_retries=[];self.out=out;self.home=Path.home();self.config=self.home/'.config/quickshell';self.bar=self.config/'state/bar-state.json';self.workers=[];self.results=[];self.samples={}
        self.pointer=json.loads(sp.check_output(['hyprctl','-j','cursorpos']));self.active=json.loads(sp.check_output(['hyprctl','-j','activewindow'])).get('address');self.saved=capture_bar(self.bar)
        paths=[self.config/'state/settings-state.json',self.home/'.config/hypr/workspace-opacity.json',self.home/'.config/hypr/workspace-opacity.lua']+[Path(os.environ['XDG_RUNTIME_DIR'])/'43pr-opacity'/name for name in ['windows.json','preview.json']]
        self.files={p:p.read_bytes() if p.exists() else None for p in paths};self.files[self.bar]=self.saved
        screens=json.loads(sp.check_output(['hyprctl','-j','monitors']));assert all(s['x']>=0 and s['y']>=0 for s in screens),'Negative output origins require a mapped pointer fixture'
        self.env=dict(os.environ,**{'43PR_TEST_WIDTH':str(round(max(s['x']+s['width']/s['scale'] for s in screens))),'43PR_TEST_HEIGHT':str(round(max(s['y']+s['height']/s['scale'] for s in screens)))})
        self.source=Path(__file__).resolve().parent;self.input=out/'input';self.keyboard=out/'keyboard';self.build()
    def build(self):
        flags=shlex.split(sp.check_output(['pkg-config','--cflags','--libs','wayland-client'],text=True));sp.run(['cc',str(self.source/'input.c'),str(self.source/'pointer.c'),*flags,'-o',str(self.input)],check=True)
        flags=shlex.split(sp.check_output(['pkg-config','--cflags','--libs','wayland-client','xkbcommon'],text=True));sp.run(['cc',str(self.source/'key-fr.c'),str(self.source/'virtual-keyboard-protocol.c'),*flags,'-o',str(self.keyboard)],check=True)
    def ipc(self,method,*args,target='bar'):
        for attempt in range(2):
            try:return sp.check_output([self.qs,'ipc','-p',str(self.config),'call',target,method,*map(str,args)],text=True,timeout=5).strip()
            except (sp.TimeoutExpired,sp.CalledProcessError):
                self.transport_retries.append({'method':method,'attempt':attempt+1})
                if attempt:raise
                time.sleep(.1)
    def state(self):return json.loads(self.ipc('layoutState'))
    def targets(self):return json.loads(self.ipc('interactionState'))
    def key(self,code,mods=0):sp.run([str(self.keyboard),str(code),str(mods)],check=True);time.sleep(.2)
    def point(self,t,fraction=(.5,.5)):return round(t['x']+t['width']*fraction[0]),round(t['y']+t['height']*fraction[1])
    def input_at(self,t,mode,*args,fraction=(.5,.5)):
        sp.run([str(self.input),*map(str,self.point(t,fraction)),mode,*map(str,args)],env=self.env,check=True,timeout=5)
    def idle(self):
        for _ in range(15):
            s=self.state()
            if not s['manipulating'] and not s['input']['left'] and not s['input']['discardClick']:return s
            time.sleep(.06)
        self.samples['retained_capture']={'state':s,'trace':json.loads(self.ipc('inputTraceState'))}
        raise AssertionError('Input capture retained')
    def write(self,cfg):self.bar.write_text(json.dumps(cfg));time.sleep(.65)
    def fixture_windows(self):
        for i in range(3):
            worker=sp.Popen(['kitty','--config','NONE','--class','43pr-regression-'+str(os.getpid())+'-'+str(i),'sleep','1800'],stdout=sp.DEVNULL,stderr=sp.DEVNULL);self.workers.append(worker)
            for _ in range(40):
                client=next((c for c in json.loads(sp.check_output(['hyprctl','-j','clients'])) if c['class']=='43pr-regression-'+str(os.getpid())+'-'+str(i)),None)
                if client:break
                time.sleep(.1)
            assert client,'Fixture window absent'
            if i:
                workspace='special:minimized'+('-regression' if i==2 else '')
                command='hl.dsp.window.move({window='+json.dumps('address:'+client['address'])+',workspace='+json.dumps(workspace)+',follow=false})'
                sp.run(['hyprctl','dispatch',command],check=True,stdout=sp.DEVNULL)
            else:self.fixture=client['address']
    def initialize(self):
        self.ipc('hide',target='settings');self.ipc('close',target='processes');self.ipc('close',target='opacity');self.fixture_windows();self.ipc('guardInteractions','true')
        self.base=json.loads(self.saved);self.base.update(hidden='',freeLayout=True,reserveSpace=False,allScreens=False,autoGroup=False,scale=1,moduleScaleVersion=2,moduleScale={},moduleZoom=1,groupRotations={},moduleOpacity={},groupOpacity={},bgOpacity=1,startMods='',centerMods='',endMods='',windowGroupsEnabled=True,windowGroups=[{'id':'regression','name':'Regression'}],collapsedGroups={})
        self.write(self.base);self.ids=list(dict.fromkeys(m['id'] for m in self.state()['modules']))
        self.base.update(moduleGroups=[dict(id='free-test-regression',items=self.ids,x=.2,y=.12,position=.5)],groupCells={'free-test-regression':{id:dict(x=i%5,y=i//5) for i,id in enumerate(self.ids)}})
    def run_point(self,case,old,fraction,index):
        time.sleep(.08) # Allow the scene/input region to commit after the previous edit.
        target=next((t for t in self.targets() if t['module']==old['module'] and t['path']==old['path']),None)
        assert target,'Input target disappeared without a state transition'
        before=self.state();sizes={m['id']:m['size'] for m in before['modules']};value=sizes[target['module']];delta=-15 if value<1 else 15;expected=value+(.05 if delta<0 else -.05)
        self.input_at(target,'quickwheel' if index%2==0 else 'holdwheel',delta,fraction=fraction);after=self.idle();actual={m['id']:m['size'] for m in after['modules']}
        ok=abs(actual[target['module']]-expected)<.003 and all(abs(actual.get(id,v)-v)<.003 for id,v in sizes.items() if id!=target['module'])
        result=dict(case=case,module=target['module'],path=target['path'],point=fraction,before=value,expected=expected,actual=actual[target['module']],passed=ok)
        self.results.append(result)
        if not ok:self.samples['failure-'+str(index)]=after
        # The contextual editor must select the same module on every child/gap.
        target=next(t for t in self.targets() if t['module']==old['module'] and t['path']==old['path'])
        self.input_at(target,'move',fraction=fraction);cursor=json.loads(sp.check_output(['hyprctl','-j','cursorpos']));before_key=self.state();self.key(24,65);editor=self.state()['editor'];result['editor_correct']=editor['open'] and editor['scope']=='module' and editor['id']==target['module'];self.key(1)
        result['passed'] &= result['editor_correct']
        if not result['passed']:self.samples['input_failure_'+str(index)]={'target':target,'cursor':cursor,'before_key':before_key,'editor':editor,'trace':json.loads(self.ipc('inputTraceState'))}
        if len(self.results)%20==0:
            self.save(None)
            print(json.dumps({'progress':len(self.results),'failures':sum(not r['passed'] for r in self.results),'case':case}),flush=True)
    def matrix(self):
        cases=[('left','floating','default',False,True,False),('top','joined','compact',True,False,True),('right','strip','default',False,False,True),('bottom','floating','compact',True,True,False)]
        cursor=0
        for position,style,mode,collapsed,scroll,seconds in cases:
            if position not in getattr(self,'positions',['left','top','right','bottom']):continue
            name=position+'-'+mode+('-collapsed' if collapsed else '-expanded');cfg=dict(self.base,position=position,style=style,statsMode=mode,tasksCollapsed=collapsed,collapsedGroups={'minigroup-regression':not collapsed},wsScroll=scroll,clockSeconds=seconds,clock24=not seconds,taskMaxVisible=1 if position=='right' else 3,tooltips=True,tipDelay=40)
            self.write(cfg);inventory=self.targets();self.samples[name]={'targets':inventory,'tasks':json.loads(self.ipc('tasksState')),'layout':self.state()}
            for old in inventory:
                if getattr(self,'modules',[]) and old['module'] not in self.modules:continue
                fractions=[(.5,.5),(.05,.05),(.95,.05),(.05,.95),(.95,.95)] if old['path']=='slot' else [(.5,.5)]
                for fraction in fractions:
                    current=cursor;cursor+=1
                    if current<getattr(self,'start',0):continue
                    if getattr(self,'limit',0) and len(self.results)>=self.limit:return
                    self.run_point(name,old,fraction,current)
        assert self.results and all(r['passed'] for r in self.results),'One or more input targets failed'
    def extra_controls(self):
        # Uniform zoom clears every individual override, including hidden/new modules.
        cfg=dict(self.base,moduleScale={'tasks':.7,'ws':1.7,'clock':.6,'future-hidden':1.8});self.write(cfg);self.ipc('setZoomPercent','125');time.sleep(.5);s=self.state();assert all(abs(m['size']-1.25)<.003 for m in s['modules']);assert json.loads(self.bar.read_text())['moduleScale']=={};self.samples['uniform_zoom']=s
        ui=json.loads(self.bar.read_text());ui['moduleScale']={'tasks':.7,'ws':1.7};self.write(ui)
        for _ in range(12):
            self.ipc('opacity',target='settings');time.sleep(.25);d=json.loads(self.ipc('diagnostic',target='settings'));track=d['zoom']
            if track and d['y']+60<track['y']<d['y']+d['height']-20:break
        else:raise AssertionError('Zoom control is outside the settings viewport')
        handle={'x':d['x']+d['width']/2-80,'y':d['y']+8,'width':2,'height':2};self.input_at(handle,'drag',round(handle['x']+45),round(handle['y']+30));after=json.loads(self.ipc('diagnostic',target='settings'));assert abs(after['x']-d['x'])>20;self.samples['free_settings_handle']=True;track=after['zoom']
        self.input_at(track,'click',fraction=((150-50)/150,.5));time.sleep(.6);s=self.state();self.samples['settings_zoom_debug']={'diagnostic':after,'after':s};assert all(abs(m['size']-1.5)<.02 for m in s['modules']);assert json.loads(self.bar.read_text())['moduleScale']=={};self.samples['settings_zoom']=s;self.ipc('hide',target='settings')
        # Size cancellation and continuation outside the target, one per module.
        for id in sorted({t['module'] for t in self.targets()}):
            self.ipc('resetSizes');time.sleep(.35);target=next(t for t in self.targets() if t['module']==id and t['path']=='slot');x,y=self.point(target)
            gesture=sp.Popen([str(self.input),str(x),str(y),'holdwheelwait','-15'],env=self.env);time.sleep(.95);assert self.state()['manipulating'];self.key(1);gesture.wait(timeout=4);s=self.idle();assert abs(next(m['size'] for m in s['modules'] if m['id']==id)-1)<.003
            target=next(t for t in self.targets() if t['module']==id and t['path']=='slot');self.input_at(target,'outwheel',int(self.env['43PR_TEST_WIDTH'])-20,int(self.env['43PR_TEST_HEIGHT'])-20);s=self.idle();assert abs(next(m['size'] for m in s['modules'] if m['id']==id)-.9)<.003
        self.samples['extra_controls_passed']=True
    def context_controls(self):
        self.write(self.base)
        ids=sorted({t['module'] for t in self.targets()})
        for id in ids:
            self.write(self.base);target=next(t for t in self.targets() if t['module']==id and t['path']=='slot')
            self.input_at(target,'move');self.key(24,64);e=self.state()['editor'];assert e['open'] and e['scope']=='all';self.key(1)
            self.input_at(target,'move');hold=sp.Popen([str(self.keyboard),'-1','4','650']);time.sleep(.15);self.input_at(target,'right');hold.wait(timeout=3);e=self.state()['editor'];assert e['open'] and e['scope']=='module' and e['id']==id;self.key(1)
            target=next(t for t in self.targets() if t['module']==id and t['path']=='slot');old=next(m['vertical'] for m in self.state()['modules'] if m['id']==id)
            self.input_at(target,'rotate');s=self.idle();assert next(m['vertical'] for m in s['modules'] if m['id']==id)!=old
        self.write(dict(self.base,groupOpacity={'free-test-regression':.4}));panel=next(p for p in self.state()['panels'] if p['id']=='free-test-regression');rect=dict(panel['geometry']);rect.update(width=2,height=2);self.input_at(rect,'move');self.key(24,65);e=self.state()['editor'];assert e['open'] and e['scope']=='group'
        self.input_at(e['opacityInput'],'click');self.key(2,1);self.key(11,1);self.key(11,1);self.key(28);s=self.state()
        if s['editor']['open']:self.input_at(s['editor']['buttons'][2],'click')
        s=self.state();assert all(abs(m['opacity']-1)<.003 for m in s['modules']);assert not s['editor']['open'];self.samples['group_opacity_100']=s
        # Outside the bar, the same keys retain workspace/window scope.
        self.ipc('hide',target='settings');sp.run(['hyprctl','dispatch','hl.dsp.focus({window='+json.dumps('address:'+self.fixture)+'})'],check=True,stdout=sp.DEVNULL);time.sleep(.2)
        client=next(c for c in json.loads(sp.check_output(['hyprctl','-j','clients'])) if c['address']==self.fixture);rect={'x':client['at'][0],'y':client['at'][1],'width':client['size'][0],'height':client['size'][1]};self.input_at(rect,'move')
        for mods,mode in [(64,'workspace'),(65,'window')]:
            self.key(24,mods);e=json.loads(self.ipc('diagnostic',target='opacity'));assert e['open'] and e['mode']==mode;self.key(1)
        self.samples['context_controls_passed']=ids
    def restore(self):
        try:self.key(1);self.ipc('guardInteractions','false');self.ipc('hide',target='settings');self.ipc('close',target='processes');self.ipc('close',target='opacity')
        except Exception:pass
        for worker in self.workers:
            worker.terminate()
            try:worker.wait(timeout=3)
            except sp.TimeoutExpired:worker.kill();worker.wait()
        restore_states(self.files)
        sp.run(['python3',str(self.home/'.config/hypr/scripts/window-opacity.py'),'--sync'],check=True,stdout=sp.DEVNULL)
        if self.active:sp.run(['hyprctl','dispatch','hl.dsp.focus({window='+json.dumps('address:'+self.active)+'})'],stdout=sp.DEVNULL)
        sp.run([str(self.input),str(self.pointer['x']),str(self.pointer['y']),'move'],env=self.env,check=True)
        s=self.idle();assert not s['editor']['open'] and not s['processPopupOpen'];assert all((not p.exists()) if data is None else p.read_bytes()==data for p,data in self.files.items());self.restored=True
    def save(self,error):
        (self.out/'results.json').write_text(json.dumps({'error':error,'restored':getattr(self,'restored',False),'results':self.results,'samples':self.samples,'transport_retries':self.transport_retries},indent=2));print(json.dumps({'checks':len(self.results),'failures':sum(not r['passed'] for r in self.results),'restored':getattr(self,'restored',False),'error':error}),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--allow-desktop',action='store_true');parser.add_argument('--output',type=Path);parser.add_argument('--start',type=int,default=0);parser.add_argument('--limit',type=int,default=0);parser.add_argument('--extras-only',action='store_true');parser.add_argument('--modules',default='');parser.add_argument('--context-only',action='store_true');parser.add_argument('--positions',default='left,top,right,bottom');parser.add_argument('--matrix-only',action='store_true');args=parser.parse_args()
    if not args.allow_desktop:parser.error('Explicit --allow-desktop and user coordination are required')
    out=args.output or Path.home()/'.local/state/43pr-tests'/datetime.datetime.now().strftime('%Y%m%dT%H%M%S');out.mkdir(parents=True,exist_ok=True,mode=0o700);test=Desktop(out);test.start=args.start;test.limit=args.limit;test.positions=args.positions.split(",");test.modules=[x for x in args.modules.split(",") if x];error=None
    try:
        test.initialize()
        if args.context_only:test.context_controls()
        elif args.extras_only:test.extra_controls();test.context_controls()
        else:
            test.matrix()
            if not args.matrix_only:test.extra_controls();test.context_controls()
    except BaseException as e:error=repr(e);raise
    finally:
        try:test.restore()
        finally:test.save(error)
if __name__=='__main__':main()
