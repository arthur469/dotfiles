#!/usr/bin/env python3
"""Native wallpaper control decisions; deterministic fake IPC, no desktop changes."""
from pathlib import Path
import importlib.util,importlib.machinery,os,sys,tempfile,unittest,json
from unittest.mock import patch
path=Path(os.environ.get('PR43_TEST_WALLPAPER',Path(__file__).resolve().parents[2]/'.config/quickshell/hyprquickpaper/live-control.py'))
spec=importlib.util.spec_from_file_location('wallpaper_control',path,loader=importlib.machinery.SourceFileLoader('wallpaper_control',str(path)));control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
class Wallpaper(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);root=Path(self.temp.name)
  for name,value in [('MODE',root/'mode.json'),('CACHE',root/'last-live')]:
   p=patch.object(control,name,value);p.start();self.addCleanup(p.stop)
  self.video=root/'selected.mp4';self.video.write_bytes(b'fixture');control.CACHE.write_text(str(self.video));control.MODE.write_text('{"mode":"night"}')
  self.available=True;self.paused=True;self.started=[];self.commands=[]
  def status():return dict(mode=control.mode(),available=self.available,selected_video=control.CACHE.exists(),paused=self.paused)
  def command(*args):
   self.commands.append(args)
   if args[:2]==('set_property','pause'):self.paused=args[2]
  def start(source):self.started.append(source);self.available=True;self.paused=False;return status()
  for name,value in [('status',status),('command',command),('start',start),('playback_expected',lambda:True)]:
   p=patch.object(control,name,value,create=True);p.start();self.addCleanup(p.stop)
 def probe(self,*states):
  p=patch.object(control,'probe_playback',side_effect=[dict(advanced=v,after=12.5,paused=not v) for v in states],create=True);m=p.start();self.addCleanup(p.stop);return m
 def test_day_stalled_ipc_alive_restarts_same_video(self):
  self.probe(False,True);r=control.change('day');self.assertTrue(r['restarted']);self.assertEqual(self.started,[self.video]);self.assertFalse(r['initial_stall']['advanced']);self.assertEqual(r['playback_verification'],'progress');self.assertIn(('seek',12.5,'absolute+exact'),self.commands)
 def test_day_progress_keeps_player(self):
  self.probe(True);r=control.change('day');self.assertTrue(r['verified']);self.assertEqual(self.started,[])
 def test_recovery_still_frozen_is_failure(self):
  self.probe(False,False)
  with self.assertRaisesRegex(RuntimeError,'frozen'):control.change('day')
 def test_no_reader_day_restarts(self):
  self.available=False;self.probe(True);r=control.change('day');self.assertTrue(r['restarted']);self.assertEqual(self.started,[self.video])
 def test_no_selected_video_is_skipped(self):
  control.CACHE.unlink();self.available=False;p=self.probe();self.assertTrue(control.change('day')['skipped']);p.assert_not_called()
 def test_night_does_not_probe_or_restart(self):
  p=self.probe();r=control.change('night');self.assertTrue(r['paused']);p.assert_not_called();self.assertEqual(self.started,[])
 def test_night_without_reader_is_valid(self):
  self.available=False;self.assertTrue(control.change('night')['verified'])
 def test_preview_does_not_change_mode_or_call_player(self):
  p=self.probe();before=control.MODE.read_bytes();r=control.change('day',True);self.assertTrue(r['preview']);self.assertEqual(control.MODE.read_bytes(),before);self.assertEqual(self.commands,[]);p.assert_not_called()
 def test_fullscreen_or_sleep_does_not_force_playback(self):
  with patch.object(control,'playback_expected',return_value=False):
   p=self.probe();r=control.change('day');self.assertEqual(r['playback_verification'],'hidden');p.assert_not_called();self.assertEqual(self.started,[])
 def test_output_hidden_during_probe_keeps_native_pause(self):
  self.probe(False)
  with patch.object(control,'playback_expected',side_effect=[True,False]):
   r=control.change('day');self.assertEqual(r['playback_verification'],'hidden');self.assertEqual(self.started,[])
 def test_unknown_visibility_does_not_claim_progress(self):
  with patch.object(control,'playback_expected',return_value=None):self.assertEqual(control.change('day')['playback_verification'],'unavailable')
 def test_missing_video_cannot_be_recovered(self):
  self.video.unlink();self.probe(False)
  with self.assertRaises(ValueError):control.change('day')
 def test_probe_checks_delayed_pause(self):
  # Use the production observation, with only the clock and transport mocked.
  with patch.object(control,'command',side_effect=[10,10.5,True]),patch.object(control.time,'sleep') as sleep:
   self.assertFalse(control.probe_playback()['advanced']);sleep.assert_called_once_with(2.25)
 def test_probe_accepts_video_loop_and_rejects_still_frame(self):
  for before,after,expected in [(29.8,.5,True),(10,10,False),(None,None,False)]:
   with self.subTest(before=before,after=after),patch.object(control,'command',side_effect=[before,after,False]),patch.object(control.time,'sleep'):
    self.assertEqual(control.probe_playback()['advanced'],expected)
 def test_visibility_uses_active_powered_outputs(self):
  # Run the original function; a hidden secondary output must not hide a visible one.
  real=spec.loader;original=importlib.util.module_from_spec(spec);real.exec_module(original)
  for screens,desks,expected in [([],[],False),([{'dpmsStatus':False}],[],False),([{'activeWorkspace':{'id':1}}],[{'id':1,'hasfullscreen':False}],True),([{'activeWorkspace':{'id':1}}],[{'id':1,'hasfullscreen':True}],False),([{'activeWorkspace':{'id':1}}],[],None)]:
   with self.subTest(screens=screens,desks=desks),patch.object(original.subprocess,'check_output',side_effect=[json.dumps(screens),json.dumps(desks)]):self.assertIs(original.playback_expected(),expected)
class WallpaperFill(unittest.TestCase):
 def launch(self, folder, mode, transient):
  # Exercise the real start() function, stubbing process/IPC boundaries only.
  original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
  video=folder/'selected.mp4';video.write_bytes(b'launch fixture')
  original.CACHE=folder/'last-live'
  calls=[]
  def run(args,**kwargs):
   calls.append(args);return original.subprocess.CompletedProcess(args,0,'','')
  with patch.object(original,'stop'),patch.object(original,'mode',return_value=mode),patch.object(original,'status',return_value={'available':True}),patch.object(original,'command',return_value=1.0),patch.object(original.SOCKET.__class__,'exists',return_value=True),patch.object(original.shutil,'which',return_value='/mock/systemd-run' if transient else None),patch.object(original.subprocess,'run',side_effect=run),patch.object(original.subprocess,'Popen',side_effect=lambda args,**kw:calls.append(args)),patch.object(original.Path,'home',return_value=folder):
   original.start(video)
  command=next(args for args in calls if 'mpvpaper' in args)
  self.assertEqual(command[-1],str(video));self.assertEqual(original.CACHE.read_text().strip(),str(video))
  return command[command.index('-o')+1]
 def fixture(self,folder):
  image=folder/'green.ppm';image.write_bytes(b'P6\n160 90\n255\n'+bytes([20,200,40])*(160*90));return image
 def test_fill_from_native_launch_day_night_and_both_process_paths(self):
  from wallpaper_render import render_edges
  with tempfile.TemporaryDirectory(prefix='43pr-fill-') as directory:
   folder=Path(directory);image=self.fixture(folder)
   for mode in ['day','night']:
    for transient in [True,False]:
     with self.subTest(mode=mode,systemd=transient):
      options=self.launch(folder,mode,transient)
      self.assertEqual('pause=yes' in options,mode=='night')
      for frame in render_edges(options,image,[(344,144),(160,90),(144,256)]):
       self.assertTrue(all(g>80 and g>r and g>b for r,g,b in frame['edges']),frame)
 def test_renderer_detects_original_letterboxing(self):
  from wallpaper_render import render_edges
  with tempfile.TemporaryDirectory(prefix='43pr-fill-negative-') as directory:
   folder=Path(directory);image=self.fixture(folder)
   # Reproduce the old startup: no crop/fill setting. Equal ratios still fit;
   # ultrawide and portrait must expose black edges, proving fixture sensitivity.
   frames=render_edges('no-audio loop hwdec=auto',image,[(344,144),(160,90),(144,256)])
   self.assertTrue(any(max(rgb)<10 for rgb in frames[0]['edges']))
   self.assertTrue(all(rgb[1]>80 for rgb in frames[1]['edges']))
   self.assertTrue(any(max(rgb)<10 for rgb in frames[2]['edges']))

if __name__=='__main__':unittest.main()
