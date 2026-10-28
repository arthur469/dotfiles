"""Select the running desktop runtime, with an explicit override for isolated tests."""
from pathlib import Path
import os,subprocess,shutil

def quickshell():
    if os.environ.get('QS_TEST_BINARY'):return os.environ['QS_TEST_BINARY']
    result=subprocess.run(['systemctl','--user','show','43pr-quickshell.service','-p','MainPID','--value'],capture_output=True,text=True)
    try:
        pid=int(result.stdout);path=Path(f'/proc/{pid}/exe')
        if pid>0 and path.exists():return str(path.resolve())
    except ValueError:pass
    return shutil.which('qs') or shutil.which('quickshell') or 'qs'
