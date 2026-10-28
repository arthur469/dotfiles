#!/usr/bin/python3
"""Read mounted filesystem usage once per UUID; never mount a volume."""
import json, os, subprocess


def volumes(devices, statvfs=os.statvfs):
    found = {}
    def visit(device, model=''):
        model = device.get('model') or model
        fstype = device.get('fstype')
        uuid = device.get('uuid')
        if fstype and fstype not in {'swap','crypto_LUKS','LVM2_member','linux_raid_member'}:
            key = 'uuid:' + uuid if uuid else 'device:' + device['path']
            mounts = [m for m in device.get('mountpoints', []) or [] if m and m.startswith('/')]
            mount = min(mounts, key=lambda p:(len(p),p)) if mounts else ''
            row = {'id':key,'device':device['path'],'label':device.get('label') or model or device['name'],
                   'mount':mount,'fstype':fstype,'mounted':False,'total':None,'used':None,'available':None,'percent':None}
            if mount:
                try:
                    info = statvfs(mount)
                    row.update(mounted=True,total=info.f_blocks*info.f_frsize,
                               used=(info.f_blocks-info.f_bfree)*info.f_frsize,available=info.f_bavail*info.f_frsize)
                    usable = row['used'] + row['available']
                    row['percent'] = round(100*row['used']/usable) if usable else 0
                except OSError:
                    pass
            previous = found.get(key)
            if previous is None or (row['mounted'] and (not previous['mounted'] or len(mount)<len(previous['mount']))):
                found[key] = row
        for child in device.get('children',[]):visit(child,model)
    for device in devices:visit(device)
    return sorted(found.values(),key=lambda row:(not row['mounted'],row['label'].casefold(),row['id']))


if __name__ == '__main__':
    try:
        data = subprocess.check_output(['lsblk','--json','--bytes','--output','NAME,PATH,FSTYPE,UUID,LABEL,MOUNTPOINTS,MODEL'],text=True,timeout=5)
        print(json.dumps({'volumes':volumes(json.loads(data)['blockdevices']),'error':''},ensure_ascii=False))
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print(json.dumps({'volumes':[],'error':type(error).__name__}))
