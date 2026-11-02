"""Exercise production updater reconciliation against disposable local Git repos."""
from pathlib import Path
import os,subprocess as sp,tempfile,unittest,re
ROOT=Path(__file__).resolve().parents[2]
class UpdaterSafety(unittest.TestCase):
 def git(self,folder,*args):return sp.check_output(['git','-C',str(folder),*args],text=True,stderr=sp.DEVNULL).strip()
 def test_updates_never_choose_a_side_of_divergence_or_hide_local_files(self):
  for script,function in [('update.sh','sync_repo_keep_local'),('update2.sh','sync_repo_upstream_wins')]:
   text=(ROOT/script).read_text();start=text.index(function+'() {');end=text.index('\n}\n',start)+2;body=text[start:end]
   for scenario in ['clean-behind','dirty-behind','untracked-behind','diverged','already-current','no-tracking']:
    with self.subTest(script=script,scenario=scenario),tempfile.TemporaryDirectory(prefix='43pr-updater-') as d:
     root=Path(d);remote=root/'remote.git';seed=root/'seed';local=root/'local'
     sp.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
     sp.run(['git','init','-b','main',str(seed)],check=True,capture_output=True)
     for folder in [seed]:
      self.git(folder,'config','user.name','Updater fixture');self.git(folder,'config','user.email','fixture@example.invalid')
     (seed/'base').write_text('original\n');self.git(seed,'add','.');self.git(seed,'commit','-m','base');self.git(seed,'remote','add','origin',str(remote));self.git(seed,'push','-u','origin','main')
     sp.run(['git','clone','--quiet','-b','main',str(remote),str(local)],check=True,capture_output=True)
     self.git(local,'config','user.name','Updater fixture');self.git(local,'config','user.email','fixture@example.invalid')
     if scenario not in ['already-current','no-tracking']:
      (seed/'upstream').write_text('new\n');self.git(seed,'add','.');self.git(seed,'commit','-m','upstream');self.git(seed,'push')
     if scenario=='dirty-behind':(local/'base').write_text('personal edits\n')
     if scenario=='untracked-behind':(local/'untracked').write_text('extension\n')
     if scenario=='diverged':
      (local/'extension').write_text('local commit\n');self.git(local,'add','.');self.git(local,'commit','-m','local extension')
     if scenario=='no-tracking':self.git(local,'branch','--unset-upstream')
     before=self.git(local,'rev-parse','HEAD');files={p.name:p.read_bytes() for p in local.iterdir() if p.is_file()}
     shell='error(){ printf "%s\\n" "$*" >&2; }; warning(){ :; }; info(){ :; };\n'+body+'\n'+function
     result=sp.run(['bash','-c',shell],env=dict(os.environ,REPO_DIR=str(local)),capture_output=True,text=True,timeout=10)
     if scenario in ['clean-behind','already-current']:
      self.assertEqual(result.returncode,0,result.stderr)
      if scenario=='clean-behind':self.assertEqual(self.git(local,'rev-parse','HEAD'),self.git(seed,'rev-parse','HEAD'))
     else:
      self.assertNotEqual(result.returncode,0);self.assertEqual(self.git(local,'rev-parse','HEAD'),before)
      self.assertEqual({p.name:p.read_bytes() for p in local.iterdir() if p.is_file()},files)
     self.assertEqual(self.git(local,'stash','list'),'')
if __name__=='__main__':unittest.main()
