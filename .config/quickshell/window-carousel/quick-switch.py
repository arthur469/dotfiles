#!/usr/bin/env python3
"""Alt+Tab : active la deuxième fenêtre de l'historique Hyprland, sans interface."""
import json
import subprocess
clients = json.loads(subprocess.check_output(['hyprctl', '-j', 'clients']))
clients = sorted((c for c in clients if c.get('mapped') and not c.get('hidden') and c.get('focusHistoryID', -1) >= 0 and c.get('workspace', {}).get('id', 0) >= 0), key=lambda c: c['focusHistoryID'])
if len(clients) > 1:
    selector = json.dumps('address:' + clients[1]['address'])
    result = subprocess.check_output(['hyprctl', 'dispatch', 'hl.dsp.focus({window = ' + selector + '})'], text=True)
    if result.strip() != 'ok':
        raise RuntimeError(result)
