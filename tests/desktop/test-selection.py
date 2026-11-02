#!/usr/bin/env python3
"""Selection and evidence behaviour; no desktop input or service changes."""
from pathlib import Path
import importlib.util
import json
import subprocess as sp
import sys
import tempfile
import unittest
from unittest.mock import patch
from selection import Selection, FAMILIES, STATIC_MODULES, ALL_ISOLATED, impact, changed_symbols
from regression import Desktop, parse_args, EnvironmentChanged, display_signature

spec=importlib.util.spec_from_file_location('isolated_runner',Path(__file__).with_name('run-isolated.py'))
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


class Filters(unittest.TestCase):
    def test_invalid_positions_modules_and_conflicting_phases_before_input(self):
        for argv in [('--positions','up'),('--positions','left,left'),('--positions',''),
                     ('--modules','typo'),('--modules','cpu,cpu'),('--limit','-1'),
                     ('--extras-only','--context-only')]:
            with self.subTest(argv=argv),self.assertRaises(SystemExit),patch('sys.stderr'):
                parse_args(['--plan',*argv])

    def test_unavailable_explicit_module_is_reported(self):
        with self.assertRaisesRegex(ValueError,'unavailable'):
            Selection(('battery',)).describe(['cpu','ram'])

    def test_inferred_unavailable_consumer_is_excluded_explicitly(self):
        scope=Selection(('cpu','disk:*'),strict=False).describe(['cpu','ram'])
        self.assertEqual(scope['modules'],['cpu'])
        self.assertEqual(scope['unavailable_requested_modules'],['disk:*'])
        self.assertTrue(scope['partial'])

    def test_disk_and_window_group_selectors(self):
        scope=Selection(('disk:*','minigroup-*'),('right',)).describe(['cpu','disk:uuid%3Aone','minigroup-project'])
        self.assertEqual(scope['modules'],['disk:uuid%3Aone','minigroup-project'])
        self.assertEqual(scope['excluded_modules'],['cpu']);self.assertTrue(scope['partial'])
        self.assertEqual(scope['excluded_positions'],['bottom','left','top'])

    def fixture(self):
        test=Desktop.__new__(Desktop);test.selection=Selection(('cpu',),('right',));test.results=[];test.base={};test.samples={};test.start=0;test.limit=0;test.transport_retries=[];test.case_sequence=[]
        test.targets=lambda:[{'module':m,'path':'slot'} for m in ['cpu','ram']]
        test.state=lambda:{};test.ipc=lambda *a,**k:'{}';test.write=lambda cfg:self.writes.append(cfg)
        self.writes=[];self.actions=[];test.check_displays=lambda:None
        test.run_point=lambda name,target,fraction,index:self.actions.append(('matrix',target['module'])) or test.results.append({'passed':True})
        test.global_controls=lambda:self.actions.append(('global','zoom'))
        test.size_continuation=lambda m:self.actions.append(('continue',m))
        test.module_context=lambda m:self.actions.append(('context',m))
        test.group_context=lambda:self.actions.append(('global','group'))
        test.outside_context=lambda:self.actions.append(('global','outside'))
        return test

    def test_actual_matrix_extras_and_context_share_filters(self):
        test=self.fixture()
        test.matrix();test.extra_controls();test.context_controls()
        self.assertTrue(self.writes)
        self.assertEqual({cfg['position'] for cfg in self.writes},{'right'})
        self.assertTrue(all(module=='cpu' for phase,module in self.actions if phase!='global'))
        self.assertEqual({x for x in self.actions if x[0]=='global'},{('global','zoom'),('global','group'),('global','outside')})
        self.assertTrue(all(r['id'] for r in test.results))

    def test_shared_positions_use_one_requested_position_and_explain_exclusions(self):
        test=self.fixture();test.selection=Selection(('cpu',),('right','top'),coverage='families')
        test.extra_controls();test.context_controls()
        self.assertEqual({c['position'] for c in self.writes},{'right'})
        self.assertEqual(list(test.samples['common_positions']['excluded']),['top'])
        test.selection=Selection(('cpu',),('right','top'),coverage='full')
        self.assertEqual(test.control_positions(),('right','top'))

    def test_p0_cases_obey_selected_positions(self):
        test=self.fixture();seen=[]
        test.p0_geometry=lambda position:seen.append(('geometry',position))
        test.p0_drag=lambda position,group,*args:seen.append(('drag',position))
        test.p0_controls()
        self.assertEqual(len(seen),3);self.assertEqual({p for _,p in seen},{'right'})
        self.assertEqual({c['position'] for c in self.writes},{'right'})

    def test_every_module_has_overlapping_families_and_a_representative(self):
        import re
        source=(Path(__file__).resolve().parents[2]/'.config/quickshell/Bar.qml').read_text()
        registry=source.split('readonly property var moduleDefs: [',1)[1].split('].concat',1)[0]
        detected=set(re.findall(r'id:\s*"([^"]+)"',registry))
        self.assertEqual(detected,set(STATIC_MODULES)-{'clock'})
        modules=list(STATIC_MODULES)+['disk:one','minigroup-project']
        self.assertTrue(all(any(__import__('selection').matches(m,v) for k,v in FAMILIES.items() if k!='slot') for m in modules))
        selected=Selection(coverage='families').representatives(modules)
        self.assertIn('ws',selected);self.assertIn('media',selected);self.assertIn('battery',selected)
        self.assertLess(len(selected),len(modules))
        self.assertIn('new-integration',Selection(coverage='families').representatives(modules+['new-integration']))
        for m in modules:self.assertEqual(Selection((m,),coverage='families').representatives(modules),[m])


class DisplayGuard(unittest.TestCase):
    def test_output_change_stops_before_sending_input(self):
        old=[dict(name='DP-3',x=0,y=0,width=3440,height=1440,scale=1)]
        new=[dict(name='FALLBACK',x=0,y=0,width=1920,height=1080,scale=1)]
        test=Desktop.__new__(Desktop);test.screen_signature=display_signature(old);test.samples={};test.restoring=False
        with patch('regression.sp.check_output',return_value=json.dumps(new)),patch('regression.sp.run') as send:
            with self.assertRaises(EnvironmentChanged):test.input_at({},'click')
            send.assert_not_called()
        self.assertIn('environment_change',test.samples)

    def test_integer_pointer_corners_stay_inside_fractional_targets(self):
        test=Desktop.__new__(Desktop)
        for origin in [0,.3,.75,319.19421875]:
            for size in [2,8,10,20.9]:
                target={'x':origin,'y':origin,'width':size,'height':size}
                for fraction in [(.05,.05),(.95,.95)]:
                    x,y=test.point(target,fraction)
                    self.assertGreaterEqual(x,origin);self.assertLess(x,origin+size)
                    self.assertGreaterEqual(y,origin);self.assertLess(y,origin+size)

    def test_matrix_stops_at_first_failed_point(self):
        helper=Filters();test=helper.fixture()
        test.run_point=lambda *args:test.results.append({'passed':False})
        with self.assertRaisesRegex(AssertionError,'Input case failed'):test.matrix()
        self.assertEqual(len(test.results),1)
        self.assertEqual(test.results[0]['status'],'failed')


class PersistenceBarrier(unittest.TestCase):
    def test_fixture_waits_for_the_semantic_drop_on_disk(self):
        old=[{'id':'free-source','items':['clock']},{'id':'free-target','items':['cpu']}]
        merged=[{'id':'free-target','items':['cpu','clock']}]
        with tempfile.TemporaryDirectory() as directory:
            test=Desktop.__new__(Desktop);test.bar=Path(directory)/'bar.json';test.samples={}
            test.bar.write_text(json.dumps({'moduleGroups':old}))
            test.state=lambda:{'groups':merged}
            def save_completed(delay):test.bar.write_text(json.dumps({'moduleGroups':merged}))
            with patch('regression.time.sleep',side_effect=save_completed) as waited:
                self.assertEqual(test.wait_layout_persisted()['groups'],merged)
                self.assertTrue(waited.called,'Returned before the pending drop was persisted')

    def test_unpersisted_drop_is_reported_instead_of_replacing_the_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            test=Desktop.__new__(Desktop);test.bar=Path(directory)/'bar.json';test.samples={}
            test.bar.write_text(json.dumps({'moduleGroups':[]}));test.state=lambda:{'groups':[{'id':'free-target','items':['cpu']}]}
            with patch('regression.time.monotonic',side_effect=[0,0,2]),patch('regression.time.sleep'):
                with self.assertRaisesRegex(AssertionError,'did not persist'):test.wait_layout_persisted(timeout=1)
            self.assertIn('p0/persistence_failure',test.samples)

    def test_a_rolled_back_live_state_does_not_count_as_a_persisted_drop(self):
        old=[{'id':'free-source','items':['clock']}]
        merged=[{'id':'free-target','items':['cpu','clock']}]
        with tempfile.TemporaryDirectory() as directory:
            test=Desktop.__new__(Desktop);test.bar=Path(directory)/'bar.json';test.samples={}
            test.bar.write_text(json.dumps({'moduleGroups':old}));test.state=lambda:{'groups':old}
            with patch('regression.time.monotonic',side_effect=[0,0,2]),patch('regression.time.sleep'):
                with self.assertRaisesRegex(AssertionError,'did not persist'):test.wait_layout_persisted(timeout=1,expected=merged)


class Impacts(unittest.TestCase):
    def test_resource_change_retains_consumers_and_invariants(self):
        plan=impact(['Bar.qml:ResourceBadge'])
        self.assertEqual(set(plan['modules']),{'cpu','ram','gpu','temp','disk:*'})
        self.assertIn('ipc-reconnect',plan['isolated']);self.assertIn('async-save',plan['isolated'])
        self.assertTrue(plan['exclusions']);self.assertIn('edge-margin',plan['isolated'])

    def test_workspace_change_retains_click_regression(self):
        for symbol in ('wsC','activateWorkspace'):
            plan=impact(['Bar.qml:'+symbol])
            self.assertEqual(plan['modules'],['ws'])
            self.assertIn('workspace-clicks',plan['isolated'])
            self.assertNotIn('bubble-geometry',plan['isolated'])

    def test_common_unknown_or_unmapped_file_widens(self):
        for symbols,files in [(['Bar.qml:adjustSelection'],[]),(['unknown'],[]),([],['Bar.qml']),([],['runtime.so'])]:
            with self.subTest(symbols=symbols,files=files):
                self.assertEqual(impact(symbols,files)['modules'],[])
                self.assertEqual(set(impact(symbols,files)['isolated']),set(ALL_ISOLATED))

    def test_diff_tracks_nested_handler_consumer_and_unknown_properties(self):
        before='component ResourceBadge: Interactive {\n property string value: "{x}"\n function update() { return 1; }\n}\nproperty int common: 1\n'
        after=before.replace('return 1','return 2')
        names=changed_symbols(before,after)
        self.assertIn('ResourceBadge',names);self.assertIn('update',names)
        self.assertIn('<unknown>',changed_symbols(before,before.replace('common: 1','common: 2')))
        self.assertEqual(changed_symbols(before,before),[])


class Evidence(unittest.TestCase):
    def run_case(self,body,previous=(),timeout=2):
        folder=Path(self.temp.name);script=folder/'case.py';script.write_text(body)
        output=folder/str(len(list(folder.iterdir())));output.mkdir()
        case={'command':[sys.executable,str(script)],'dependencies':[script], 'timeout':timeout}
        return runner.run_one('stable/case',case,output,{'runtime':'fixture'},previous)

    def setUp(self):self.temp=tempfile.TemporaryDirectory()
    def tearDown(self):self.temp.cleanup()

    def test_valid_success_reused_but_code_parameters_runtime_and_log_invalidate(self):
        passed=self.run_case('print("passed")')
        self.assertEqual(passed['status'],'passed')
        self.assertEqual(self.run_case('print("passed")',[passed])['status'],'reused')
        self.assertEqual(self.run_case('print("changed")',[passed])['status'],'passed')
        Path(passed['log']).write_text('tampered')
        self.assertEqual(self.run_case('print("passed")',[passed])['status'],'passed')
        altered=dict(passed,fingerprint='other-runtime-parameters')
        self.assertEqual(self.run_case('print("passed")',[altered])['status'],'passed')

    def test_failure_timeout_and_interruption_never_reusable(self):
        for status in ('failed','timeout','interrupted','passed_after_failure','passed_with_transport_retry'):
            self.assertFalse(runner.reusable({'status':status},'key'))
        failed=self.run_case('raise SystemExit(7)')
        self.assertEqual(failed['returncode'],7);self.assertEqual(failed['status'],'failed')
        timed=self.run_case('import time;time.sleep(2)',timeout=.04)
        self.assertEqual(timed['returncode'],124);self.assertEqual(timed['status'],'timeout')

    def test_source_modified_while_running_is_not_a_success(self):
        result=self.run_case('from pathlib import Path;Path(__file__).write_text("print(123)")')
        self.assertEqual(result['status'],'invalidated_during_run')
        self.assertEqual(result['returncode'],1)

    def test_orphan_running_attempt_does_not_become_unqualified_success(self):
        passed=self.run_case('print("ok")')
        orphan=dict(passed,status='running')
        later=self.run_case('print("ok")',[orphan])
        self.assertEqual(later['status'],'passed_after_failure')
        self.assertEqual(later['prior_failures'][0]['status'],'running')

    def test_success_after_failed_attempt_is_qualified_and_first_error_preserved(self):
        passed=self.run_case('print("ok")')
        earlier=dict(passed,status='interrupted',returncode=130)
        later=self.run_case('print("ok")',[earlier])
        self.assertEqual(later['status'],'passed_after_failure')
        self.assertEqual(later['prior_failures'][0]['status'],'interrupted')
        self.assertTrue(Path(earlier['log']).exists())

if __name__=='__main__':unittest.main()
