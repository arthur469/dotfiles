#!/usr/bin/env python3
"""Authorized desktop regression: every detected input area, stable baseline restored.
Requires --allow-desktop. Logs are private and never written in the source tree.
"""
from pathlib import Path
import argparse,datetime,json,os,subprocess as sp,time,shlex,signal,hashlib,traceback,fcntl,shutil,math
from selection import Selection,POSITIONS,csv_selection,impact,valid_module_selector
from state import capture_bar,restore_states
from runtime import quickshell

class EnvironmentChanged(RuntimeError):pass

def display_signature(screens):
    return tuple(sorted((m['name'],m['x'],m['y'],m['width'],m['height'],m['scale'],m.get('transform',0)) for m in screens))

class Desktop:
    def __init__(self,out):
        self.started=time.monotonic();self.scope={};self.case_sequence=[];self.qs=quickshell();self.transport_retries=[];self.out=out;self.home=Path.home();self.config=self.home/'.config/quickshell';self.bar=self.config/'state/bar-state.json';self.workers=[];self.results=[];self.samples={}
        self.pointer=json.loads(sp.check_output(['hyprctl','-j','cursorpos']));self.active=json.loads(sp.check_output(['hyprctl','-j','activewindow'])).get('address');self.saved=capture_bar(self.bar)
        paths=[self.config/'state/settings-state.json',self.home/'.config/hypr/workspace-opacity.json',self.home/'.config/hypr/workspace-opacity.lua']+[Path(os.environ['XDG_RUNTIME_DIR'])/'43pr-opacity'/name for name in ['windows.json','preview.json']]
        self.files={p:p.read_bytes() if p.exists() else None for p in paths};self.files[self.bar]=self.saved
        screens=json.loads(sp.check_output(['hyprctl','-j','monitors']));self.screen_signature=display_signature(screens);self.restoring=False;assert all(s['x']>=0 and s['y']>=0 for s in screens),'Negative output origins require a mapped pointer fixture'
        self.env=dict(os.environ,**{'43PR_TEST_WIDTH':str(round(max(s['x']+s['width']/s['scale'] for s in screens))),'43PR_TEST_HEIGHT':str(round(max(s['y']+s['height']/s['scale'] for s in screens)))})
        self.source=Path(__file__).resolve().parent;self.input=out/'input';self.keyboard=out/'keyboard';self.build()
    def build(self):
        flags=shlex.split(sp.check_output(['pkg-config','--cflags','--libs','wayland-client'],text=True));sp.run(['cc',str(self.source/'input.c'),str(self.source/'pointer.c'),*flags,'-o',str(self.input)],check=True)
        flags=shlex.split(sp.check_output(['pkg-config','--cflags','--libs','wayland-client','xkbcommon'],text=True));sp.run(['cc',str(self.source/'key-fr.c'),str(self.source/'virtual-keyboard-protocol.c'),*flags,'-o',str(self.keyboard)],check=True)
    def ipc(self,method,*args,target='bar'):
        for attempt in range(2):
            try:return sp.check_output([self.qs,'ipc','-p',str(self.config),'call',target,method,*map(str,args)],text=True,timeout=5).strip()
            except (sp.TimeoutExpired,sp.CalledProcessError) as exc:
                self.transport_retries.append({'method':method,'attempt':attempt+1,'error':repr(exc),'seconds':time.monotonic()-self.started})
                if attempt:raise
                time.sleep(.1)
    def state(self):return json.loads(self.ipc('layoutState'))
    def targets(self):return json.loads(self.ipc('interactionState'))
    def check_displays(self):
        if getattr(self,'restoring',False):return
        screens=json.loads(sp.check_output(['hyprctl','-j','monitors']))
        if display_signature(screens)!=self.screen_signature:
            self.samples['environment_change']={'before':self.screen_signature,'after':display_signature(screens)}
            raise EnvironmentChanged('Display geometry changed; stop and restore instead of sending mis-scaled input')
    def key(self,code,mods=0):
        self.check_displays();sp.run([str(self.keyboard),str(code),str(mods)],check=True);time.sleep(.2)
    def point(self,t,fraction=(.5,.5)):
        # The encoded Wayland pointer uses integer coordinates. Keep even a
        # tiny/fractional target's corner inside its actual logical rectangle.
        def axis(origin,size,ratio):
            low=math.ceil(origin);high=math.ceil(origin+size)-1
            if high<low:raise ValueError('Input area has no addressable logical pixel')
            return max(low,min(high,round(origin+size*ratio)))
        return axis(t['x'],t['width'],fraction[0]),axis(t['y'],t['height'],fraction[1])
    def input_at(self,t,mode,*args,fraction=(.5,.5)):
        self.check_displays()
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
            self.save(None,quiet=True)
            print(json.dumps({'progress':len(self.results),'failures':sum(not r['passed'] for r in self.results),'case':case}),flush=True)
    def selected_ids(self):
        return self.selection.resolve(sorted({t['module'] for t in self.targets()}))
    def execute_case(self,case_id,callback,**identity):
        started=time.monotonic();offset=len(self.results);retries=len(self.transport_retries)
        error=None
        try:
            callback()
            if len(self.results)>offset and not self.results[-1]['passed']:
                self.check_displays()
                raise AssertionError('Input case failed: '+case_id)
        except BaseException as exc:
            error=repr(exc)
            raise
        finally:
            if len(self.results)==offset:self.results.append(dict(identity,passed=error is None))
            record=self.results[-1];record.update(identity);record.update(id=case_id,duration_seconds=time.monotonic()-started)
            if error:record.update(passed=False,error=error)
            record['status']='environment_changed' if error and 'EnvironmentChanged' in error else 'failed' if not record['passed'] else 'passed_with_transport_retry' if len(self.transport_retries)>retries else 'passed'
            self.case_sequence.append(case_id)
    def matrix(self):
        cases=[('left','floating','default',False,True,False),('top','joined','compact',True,False,True),('right','strip','default',False,False,True),('bottom','floating','compact',True,True,False)]
        cursor=0
        for position,style,mode,collapsed,scroll,seconds in cases:
            if position not in self.selection.positions:continue
            name=position+'-'+mode+('-collapsed' if collapsed else '-expanded');cfg=dict(self.base,position=position,style=style,statsMode=mode,tasksCollapsed=collapsed,collapsedGroups={'minigroup-regression':not collapsed},wsScroll=scroll,clockSeconds=seconds,clock24=not seconds,taskMaxVisible=1 if position=='right' else 3,tooltips=True,tipDelay=40)
            self.write(cfg);inventory=self.targets();self.samples[name]={'targets':inventory,'tasks':json.loads(self.ipc('tasksState')),'layout':self.state()}
            for old in inventory:
                if not self.selection.accepts(old['module']):continue
                fractions=[(.5,.5),(.05,.05),(.95,.05),(.05,.95),(.95,.95)] if old['path']=='slot' else [(.5,.5)]
                for fraction in fractions:
                    current=cursor;cursor+=1
                    if current<getattr(self,'start',0):continue
                    if getattr(self,'limit',0) and len(self.results)>=self.limit:
                        assert self.results and all(r['passed'] for r in self.results),'One or more input targets failed'
                        return
                    case_id='/'.join(['matrix',name,style,old['module'],old['path'],str(fraction[0])+','+str(fraction[1])])
                    self.execute_case(case_id,lambda:self.run_point(name,old,fraction,current),module=old['module'],position=position)
        assert self.results and all(r['passed'] for r in self.results),'One or more input targets failed'
    def global_controls(self):
        self.ipc('snapCenter',target='settings') # Dedicated movable fixture, even after output shrink.
        # Deliberate global invariant: hidden/new modules must be normalized too.
        cfg=dict(self.base,position=self.selection.positions[0],moduleScale={'tasks':.7,'ws':1.7,'clock':.6,'future-hidden':1.8});self.write(cfg);self.ipc('setZoomPercent','125');time.sleep(.5);s=self.state();assert all(abs(m['size']-1.25)<.003 for m in s['modules']);assert json.loads(self.bar.read_text())['moduleScale']=={};self.samples['uniform_zoom']=s
        ui=json.loads(self.bar.read_text());ui['moduleScale']={'tasks':.7,'ws':1.7};self.write(ui)
        for _ in range(12):
            self.ipc('opacity',target='settings');time.sleep(.25);d=json.loads(self.ipc('diagnostic',target='settings'));track=d['zoom']
            if track and d['y']+60<track['y']<d['y']+d['height']-20:break
        else:raise AssertionError('Zoom control is outside the settings viewport')
        handle={'x':d['x']+d['width']/2-80,'y':d['y']+8,'width':2,'height':2};self.input_at(handle,'drag',round(handle['x']+45),round(handle['y']+30));after=json.loads(self.ipc('diagnostic',target='settings'));assert abs(after['x']-d['x'])>20;self.samples['free_settings_handle']=True;track=after['zoom']
        self.input_at(track,'click',fraction=((150-50)/150,.5));time.sleep(.6);s=self.state();self.samples['settings_zoom_debug']={'diagnostic':after,'after':s};assert all(abs(m['size']-1.5)<.02 for m in s['modules']);assert json.loads(self.bar.read_text())['moduleScale']=={};self.key(1);assert not json.loads(self.ipc('diagnostic',target='settings'))['open'],'Escape did not close settings after slider focus';self.samples['settings_escape']=True
    def size_continuation(self,id):
        self.ipc('resetSizes');time.sleep(.35);target=next(t for t in self.targets() if t['module']==id and t['path']=='slot');x,y=self.point(target)
        self.check_displays()
        gesture=sp.Popen([str(self.input),str(x),str(y),'holdwheelwait','-15'],env=self.env)
        try:
            time.sleep(.95);assert self.state()['manipulating'];self.key(1)
        finally:gesture.wait(timeout=4)
        s=self.idle();assert abs(next(m['size'] for m in s['modules'] if m['id']==id)-1)<.003
        target=next(t for t in self.targets() if t['module']==id and t['path']=='slot');self.input_at(target,'outwheel',int(self.env['43PR_TEST_WIDTH'])-20,int(self.env['43PR_TEST_HEIGHT'])-20);s=self.idle();assert abs(next(m['size'] for m in s['modules'] if m['id']==id)-.9)<.003
    def control_positions(self):
        # Native ownership/cancellation and editor commands share their rules;
        # the full point matrix and P0 geometry retain every requested position.
        # Keep the Cartesian diagnostic when an integration is unclassified.
        modules=self.selected_ids();unknown=[m for m in modules if not valid_module_selector(m)]
        positions=self.selection.positions[:1] if self.selection.coverage=='families' and not unknown else self.selection.positions
        evidence={'executed':list(positions),'excluded':{p:'shared controller and native geometry proof; every integration remains in matrix/context' for p in self.selection.positions if p not in positions},'unknown_integrations':unknown}
        self.samples['common_positions']=evidence
        if hasattr(self,'scope'):self.scope['complementary_positions']=evidence
        return positions
    def extra_controls(self):
        self.execute_case('global/zoom-settings-handle',self.global_controls)
        for position in self.control_positions():
            self.write(dict(self.base,position=position))
            available={t['module'] for t in self.targets()}
            ids=self.selection.representatives(available)
            self.samples['continuation/'+position]={'selected':ids,'integrations_in_matrix':self.selected_ids(),'excluded_redundant':sorted(set(self.selected_ids())-set(ids))}
            for id in ids:
                self.execute_case('continuation/'+position+'/'+id,lambda:self.size_continuation(id),module=id,position=position)
        self.samples['extra_controls_passed']=True
    def module_context(self,id):
        target=next(t for t in self.targets() if t['module']==id and t['path']=='slot')
        self.input_at(target,'move');self.key(24,64);e=self.state()['editor'];assert e['open'] and e['scope']=='all';self.key(1)
        self.input_at(target,'move');hold=sp.Popen([str(self.keyboard),'-1','4','650'])
        try:time.sleep(.15);self.input_at(target,'right')
        finally:hold.wait(timeout=3)
        e=self.state()['editor'];assert e['open'] and e['scope']=='module' and e['id']==id;self.key(1)
        target=next(t for t in self.targets() if t['module']==id and t['path']=='slot');old=next(m['vertical'] for m in self.state()['modules'] if m['id']==id)
        self.input_at(target,'rotate');s=self.idle();assert next(m['vertical'] for m in s['modules'] if m['id']==id)!=old
    def group_context(self):
        self.write(dict(self.base,position=self.selection.positions[0],groupOpacity={'free-test-regression':.4}));panel=next(p for p in self.state()['panels'] if p['id']=='free-test-regression');rect=dict(panel['geometry']);rect.update(width=2,height=2);self.input_at(rect,'move');self.key(24,65);e=self.state()['editor'];assert e['open'] and e['scope']=='group'
        self.input_at(e['opacityInput'],'click');self.key(2,1);self.key(11,1);self.key(11,1);self.key(28);s=self.state()
        if s['editor']['open']:self.input_at(s['editor']['buttons'][2],'click')
        s=self.state();assert all(abs(m['opacity']-1)<.003 for m in s['modules']);assert not s['editor']['open'];self.samples['group_opacity_100']=s
    def outside_context(self):
        self.ipc('hide',target='settings');sp.run(['hyprctl','dispatch','hl.dsp.focus({window='+json.dumps('address:'+self.fixture)+'})'],check=True,stdout=sp.DEVNULL);time.sleep(.2)
        client=next(c for c in json.loads(sp.check_output(['hyprctl','-j','clients'])) if c['address']==self.fixture);rect={'x':client['at'][0],'y':client['at'][1],'width':client['size'][0],'height':client['size'][1]};self.input_at(rect,'move')
        for mods,mode in [(64,'workspace'),(65,'window')]:
            self.key(24,mods);e=json.loads(self.ipc('diagnostic',target='opacity'));assert e['open'] and e['mode']==mode;self.key(1)
    def context_controls(self):
        selected={}
        for position in self.control_positions():
            self.write(dict(self.base,position=position));ids=self.selected_ids();selected[position]=ids
            for id in ids:
                self.write(dict(self.base,position=position))
                self.execute_case('context/'+position+'/'+id,lambda:self.module_context(id),module=id,position=position)
        self.execute_case('global/group-opacity-100',self.group_context)
        self.execute_case('global/outside-opacity-shortcuts',self.outside_context)
        self.samples['context_controls_passed']=selected
    def p0_fixture(self,position,source_count=2):
        available=self.selected_ids()
        preferred=[m for m in ['ws','cpu','ram'] if m in available]
        target=(preferred+[m for m in available if m not in preferred])[:min(3,max(1,len(available)-1))]
        source=[m for m in available if m not in target][:source_count]
        if not source or not target:raise RuntimeError('P0 mixed-bubble fixture needs at least two selected live modules')
        vertical=position in ('left','right')
        groups=[dict(id='free-test-p0-source',items=source,x=.2,y=.2,position=.2),dict(id='free-test-p0-target',items=target,x=.55,y=.35,position=.35)]
        cells={g['id']:{m:dict(x=0 if vertical else i,y=i if vertical else 0) for i,m in enumerate(g['items'])} for g in groups}
        cfg=dict(self.base,position=position,style='floating',border=False,autoGroup=True,moduleGroups=groups,groupCells=cells,hidden=','.join(m for m in self.ids if m not in source+target))
        self.write(cfg)
        self.samples['p0/fixture/'+position+'/'+str(source_count)]={'source':source,'target':target,'excluded_modules':sorted(set(self.scope.get('modules',available))-set(source+target))}
        return source,target
    def wait_state(self,predicate,timeout=3):
        until=time.monotonic()+timeout;last=None
        while time.monotonic()<until:
            last=self.state()
            if predicate(last):return last
            time.sleep(.025)
        raise AssertionError('Expected desktop state not reached: '+json.dumps(last))
    def capture_region(self,rect,name):
        import math
        x=max(0,math.floor(rect['x']));y=max(0,math.floor(rect['y']));w=max(1,math.ceil(rect['width']));h=max(1,math.ceil(rect['height']))
        output=self.out/(name+'.png');sp.run(['grim','-s','1','-g',f'{x},{y} {w}x{h}',str(output)],check=True,timeout=4)
        return output,x,y
    def wait_layout_persisted(self,timeout=4,expected=None):
        # The semantic drop must be on disk before the fixture replaces it.
        # Capture release alone does not mean FileView's async save completed.
        until=time.monotonic()+timeout
        def groups(values):return sorted((g['id'],tuple(g['items'])) for g in values if g['id'].startswith('free-') and g['items'])
        wanted=groups(expected if expected is not None else self.state()['groups'])
        while time.monotonic()<until:
            disk=json.loads(self.bar.read_text());live=self.state()
            if groups(disk.get('moduleGroups',[]))==wanted and groups(live['groups'])==wanted:return live
            time.sleep(.025)
        self.samples['p0/persistence_failure']={'disk':disk,'live':live}
        raise AssertionError('Drop did not persist before fixture replacement')
    def p0_geometry(self,position):
        source,target=self.p0_fixture(position);s=self.state();vertical=position in ('left','right');cross='width' if vertical else 'height';axis='y' if vertical else 'x';along='height' if vertical else 'width'
        panel=next(p for p in s['panels'] if p['id']=='free-test-p0-target');items=[m for m in s['modules'] if m['id'] in target];rect=panel['geometry']
        assert abs(rect[cross]-max(m['geometry'][cross] for m in items))<.02,'Bubble adds transverse padding'
        ordered=sorted(items,key=lambda m:m['geometry'][axis])
        for a,b in zip(ordered,ordered[1:]):assert abs(b['geometry'][axis]-a['geometry'][axis]-a['geometry'][along]-2)<.02,'Native resource-lane spacing changed'
        if position=='left':
            from PIL import Image
            shot,x,y=self.capture_region(rect,'p0-spacing-left');image=Image.open(shot).convert('RGB')
            for a,b in zip(ordered,ordered[1:]):
                at=round((a['geometry']['y']+a['geometry']['height']+b['geometry']['y'])/2-y)
                center=round(rect['width']/2);side=1
                assert image.getpixel((center,at))==image.getpixel((side,at)),('Visible separator at shared alpha',at)
            self.samples['p0/pixels']=str(shot)
        self.samples['p0/geometry/'+position]={'panel':panel,'modules':items}
    def p0_drag(self,position,group,single=False):
        source,target=self.p0_fixture(position,1 if single else 2);before=self.state();panel=next(p for p in before['panels'] if p['id']=='free-test-p0-source');destination=next(p for p in before['panels'] if p['id']=='free-test-p0-target')['geometry'];vertical=position in ('left','right')
        if group:
            start=dict(panel['geometry']);fraction=(.5,.02) if vertical else (.02,.5)
            # Use the blank 3px along-axis margin, independent of bubble length.
            if vertical:start['height']=2;fraction=(.5,.5)
            else:start['width']=2;fraction=(.5,.5)
        else:start=next(m['geometry'] for m in before['modules'] if m['id']==source[0]);fraction=(.5,.5)
        x,y=self.point(start,fraction);tx,ty=self.point(destination)
        self.check_displays()
        gesture=sp.Popen([str(self.input),str(x),str(y),'dragwait',str(tx),str(ty)],env=self.env)
        try:
            s=self.wait_state(lambda s:s['moved'] and s['mergeTarget']=='free-test-p0-target' and (s['groupDrag']=='free-test-p0-source' if group else s['dragging']==source[0]))
            if group:
                dragged=next(p for p in s['panels'] if p['id']=='free-test-p0-source');assert dragged['z']>max(p['z'] for p in s['panels'] if p['id']!=dragged['id'])
            else:assert s['dragVisual']['visible'] and s['dragVisual']['z']>max(p['z'] for p in s['panels'])
            self.samples['p0/drag/'+position+('/group' if group else '/module-single' if single else '/module')]=s
            if position=='left':
                rect=next(p for p in s['panels'] if p['id']=='free-test-p0-target')['geometry'];self.capture_region(rect,'p0-drag-'+('group' if group else 'module-single' if single else 'module'))
        finally:gesture.wait(timeout=5)
        after=self.idle();moved=source if group else source[:1]
        assert any(all(id in g['items'] for id in target+moved) for g in after['groups']),'Drop did not merge the moving selection'
        self.wait_layout_persisted(expected=after['groups'])
    def p0_controls(self):
        for position in self.selection.positions:
            self.write(dict(self.base,position=position))
            cases=[('geometry',lambda:self.p0_geometry(position)),('group-drag',lambda:self.p0_drag(position,True)),('module-drag',lambda:self.p0_drag(position,False))]
            if len(self.selected_ids())>4:cases.append(('single-module-drag',lambda:self.p0_drag(position,False,True)))
            for name,callback in cases:self.execute_case('p0/'+position+'/'+name,callback,position=position)
    def restore(self):
        self.restoring=True
        screens=json.loads(sp.check_output(['hyprctl','-j','monitors']))
        width=round(max(s['x']+s['width']/s['scale'] for s in screens));height=round(max(s['y']+s['height']/s['scale'] for s in screens))
        self.env.update({'43PR_TEST_WIDTH':str(width),'43PR_TEST_HEIGHT':str(height)})
        pointer={'x':max(0,min(width-1,self.pointer['x'])),'y':max(0,min(height-1,self.pointer['y']))}
        if display_signature(screens)!=self.screen_signature:self.samples['restoration_after_display_change']={'before':self.screen_signature,'after':display_signature(screens),'original_pointer':self.pointer,'restored_pointer':pointer}
        try:self.key(1);self.ipc('guardInteractions','false');self.ipc('hide',target='settings');self.ipc('close',target='processes');self.ipc('close',target='opacity')
        except Exception:pass
        for worker in self.workers:
            worker.terminate()
            try:worker.wait(timeout=3)
            except sp.TimeoutExpired:worker.kill();worker.wait()
        restore_states(self.files)
        sp.run(['python3',str(self.home/'.config/hypr/scripts/window-opacity.py'),'--sync'],check=True,stdout=sp.DEVNULL)
        if self.active:sp.run(['hyprctl','dispatch','hl.dsp.focus({window='+json.dumps('address:'+self.active)+'})'],stdout=sp.DEVNULL)
        sp.run([str(self.input),str(pointer['x']),str(pointer['y']),'move'],env=self.env,check=True)
        s=self.idle();assert not s['editor']['open'] and not s['processPopupOpen'];assert all((not p.exists()) if data is None else p.read_bytes()==data for p,data in self.files.items());self.restored=True
    def save(self,error,quiet=False):
        actual={r['module'] for r in self.results if 'module' in r}
        for name,sample in self.samples.items():
            if name.startswith('p0/fixture/'):actual.update(sample['source']+sample['target'])
        self.scope['executed_modules']=sorted(actual)
        self.scope['excluded_from_module_integration']=sorted(set(self.scope.get('modules',[]))-actual)
        self.scope['executed_positions']=sorted({r.get('position',r.get('case','').split('-')[0]) for r in self.results if r.get('position',r.get('case','').split('-')[0]) in POSITIONS})
        report={'error':error,'restored':getattr(self,'restored',False),'scope':self.scope,'results':self.results,'samples':self.samples,'transport_retries':self.transport_retries,'duration_seconds':time.monotonic()-self.started,'fingerprints':getattr(self,'fingerprints',{}),'tokens':'tokens non mesurés'}
        (self.out/'results.json').write_text(json.dumps(report,indent=2))
        if not quiet:print(json.dumps({'checks':len(self.results),'failures':sum(not r['passed'] for r in self.results),'restored':getattr(self,'restored',False),'error':error,'partial':self.scope.get('partial',True),'duration_seconds':report['duration_seconds'],'transport_retries':len(self.transport_retries),'report':str(self.out/'results.json'),'tokens':'tokens non mesurés'}),flush=True)

def parse_args(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-desktop',action='store_true');parser.add_argument('--output',type=Path)
    parser.add_argument('--start',type=int,default=0);parser.add_argument('--limit',type=int,default=0)
    phases=parser.add_mutually_exclusive_group()
    for name in ('extras-only','context-only','matrix-only','p0-only'):phases.add_argument('--'+name,action='store_true')
    parser.add_argument('--modules',default='');parser.add_argument('--positions',default=','.join(POSITIONS))
    parser.add_argument('--coverage',choices=('full','families'),default='families')
    parser.add_argument('--symbol',action='append',default=[])
    parser.add_argument('--plan',action='store_true',help='print impact and selection without desktop input')
    args=parser.parse_args(argv)
    try:
        modules=csv_selection(args.modules,label='modules')
        if args.symbol and modules:raise ValueError('use symbols or explicit modules, not both')
        args.impact=impact(args.symbol) if args.symbol else None
        if args.impact:modules=args.impact['modules']
        args.selection=Selection(tuple(modules),tuple(csv_selection(args.positions,POSITIONS,'positions')),args.coverage,strict=not bool(args.impact))
        if args.start<0 or args.limit<0:raise ValueError('start and limit must be nonnegative')
    except ValueError as exc:parser.error(str(exc))
    if not args.allow_desktop and not args.plan:parser.error('Explicit --allow-desktop and user coordination are required')
    return args

def main():
    args=parse_args()
    if args.plan:
        print(json.dumps({'modules':list(args.selection.modules) or ['all available'],'positions':args.selection.positions,'coverage':args.coverage,'impact':args.impact,'global_invariants':'retained explicitly; see selection.py'},indent=2));return
    lock_path=Path.home()/'.local/state/43pr-tests/desktop.lock'
    lock_path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=lock_path.open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise RuntimeError('Another desktop regression run is active')
    out=args.output or Path.home()/'.local/state/43pr-tests'/datetime.datetime.now().strftime('%Y%m%dT%H%M%S-%f')
    out.mkdir(parents=True,exist_ok=False,mode=0o700)
    if args.coverage=='families':
        node=shutil.which('node') or str(Path.home()/'.local/opt/odysseus/node/bin/node')
        with (out/'shared-proof.log').open('w') as stream:
            sp.run([node,str(Path(__file__).with_name('test-shared-gestures.cjs'))],stdout=stream,stderr=sp.STDOUT,check=True)
    test=Desktop(out);test.start=args.start;test.limit=args.limit;test.selection=args.selection;error=None
    def interrupted(signum,frame):raise KeyboardInterrupt('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted)
    try:
        test.initialize()
        available={t['module'] for t in test.targets()};test.scope=test.selection.describe(available)
        test.scope.update(phases='p0' if args.p0_only else 'context' if args.context_only else 'extras,context' if args.extras_only else 'matrix' if args.matrix_only else 'matrix,extras,context',start=args.start,limit=args.limit,impact=args.impact)
        test.scope['partial'] |= bool(args.start or args.limit or args.context_only or args.extras_only or args.matrix_only or args.p0_only)
        source=Path(__file__).resolve().parents[2]
        files=[p for folder in (source/'.config/quickshell',Path(__file__).parent) for p in folder.rglob('*') if p.is_file() and p.suffix in ('.qml','.js','.py','.c','.h','.cjs') and '__pycache__' not in p.parts]
        test.fingerprints={'code_tests':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'runtime':{test.qs:hashlib.sha256(Path(test.qs).read_bytes()).hexdigest()},'baseline':hashlib.sha256(test.saved).hexdigest(),'parameters':test.scope,'environment':{'packages':sp.check_output(['pacman','-Q'],text=True),'platform':list(os.uname()),'wayland_xkbcommon':sp.check_output(['pkg-config','--modversion','wayland-client','xkbcommon'],text=True),'displays':json.loads(sp.check_output(['hyprctl','-j','monitors'])),'saved_files':{str(p):hashlib.sha256(data).hexdigest() if data is not None else None for p,data in test.files.items()}},'reuse':'disabled for live desktop: dynamic windows/media/input state cannot be proven equivalent'}
        if args.p0_only:test.p0_controls()
        elif args.context_only:test.context_controls()
        elif args.extras_only:test.extra_controls();test.context_controls()
        else:
            test.matrix()
            if not args.matrix_only:test.extra_controls();test.context_controls();test.p0_controls()
    except BaseException as exc:
        error=repr(exc);(out/'failure.log').write_text(traceback.format_exc());raise
    finally:
        try:test.restore()
        except BaseException as exc:
            error=(error+'; ' if error else '')+'RESTORE: '+repr(exc);raise
        finally:test.save(error)
if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('Interrupted; inspect the private report and restoration status.');raise SystemExit(130)
    except Exception as exc:print('FAILED: '+repr(exc)[:500]);raise SystemExit(1)
