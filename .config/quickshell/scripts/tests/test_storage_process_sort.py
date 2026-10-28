import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

def load(name, filename):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).resolve().parents[1]/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

disk=load('disk_usage','disk-usage.py')
process=load('system_processes','system-processes.py')

class StorageTests(unittest.TestCase):
    def device(self,uuid='one',mounts=None,**extra):
        return dict(name='disk1',path='/dev/test1',fstype='btrfs',uuid=uuid,label='',mountpoints=mounts or [],**extra)
    def stat(self,path):return SimpleNamespace(f_blocks=100,f_bfree=30,f_bavail=25,f_frsize=4096)
    def test_subvolumes_do_not_duplicate_capacity(self):
        rows=disk.volumes([self.device(mounts=['/home','/','/var/log']),self.device(mounts=['/srv'])],self.stat)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['mount'],'/')
        self.assertEqual(rows[0]['used'],70*4096);self.assertEqual(rows[0]['available'],25*4096)
        self.assertEqual(rows[0]['percent'],74)
    def test_unmounted_is_unknown_not_zero(self):
        row=disk.volumes([self.device()],self.stat)[0]
        self.assertFalse(row['mounted']);self.assertIsNone(row['percent']);self.assertIsNone(row['used'])
    def test_mount_disappears_during_probe(self):
        with patch.object(disk.os,'statvfs',side_effect=OSError):
            row=disk.volumes([self.device(mounts=['/mnt/test'])],lambda _: (_ for _ in ()).throw(OSError()))[0]
        self.assertFalse(row['mounted'])
    def test_multiple_disks_and_parent_label(self):
        rows=disk.volumes([dict(name='a',path='/dev/a',model='Portable',children=[self.device(mounts=['/'])]),self.device(uuid='two',mounts=['/mnt/data'])],self.stat)
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['id'],'uuid:two')
        self.assertTrue(any(r['label']=='Portable' for r in rows))
    def test_empty_inventory(self):self.assertEqual(disk.volumes([],self.stat),[])
    def test_zero_size(self):
        row=disk.volumes([self.device(mounts=['/'])],lambda _:SimpleNamespace(f_blocks=0,f_bfree=0,f_bavail=0,f_frsize=4096))[0]
        self.assertEqual(row['percent'],0)

class ProcessTests(unittest.TestCase):
    rows=[dict(pid=1,name='High activity',value=90,memory=100),dict(pid=2,name='Large model',value=None,memory=9000),dict(pid=3,name='Alpha',value=4,memory=150)]
    def test_vram_takes_priority_over_activity(self):
        self.assertEqual([r['pid'] for r in sorted(self.rows,key=lambda r:process.process_sort_key(r,'memory'))],[2,3,1])
    def test_existing_usage_and_name(self):
        self.assertEqual(sorted(self.rows,key=process.process_sort_key)[0]['pid'],1)
        self.assertEqual(sorted(self.rows,key=lambda r:process.process_sort_key(r,'name'))[0]['pid'],3)
    def test_group_totals_and_children_sorted_by_vram(self):
        metadata={r['pid']:dict(r,exe='/app/'+str(r['pid']),start='10',ppid=0,uid=1000) for r in self.rows}
        with patch.object(process,'identity',return_value=dict(identity='10',canStop=False)):
            groups=process.group_processes(self.rows,'gpu','memory',metadata=metadata,windows=[])
        self.assertEqual([g['pid'] for g in groups],[2,3,1]);self.assertEqual(groups[0]['memory'],9000)

if __name__=='__main__':unittest.main()
