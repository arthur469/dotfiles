#!/usr/bin/env python3
"""Restore only a live minimized client to this output's current normal workspace."""
import json, re, subprocess, sys

def query(name):
    return json.loads(subprocess.check_output(["hyprctl", "-j", name], timeout=3))

def dispatch(expression):
    result = subprocess.check_output(["hyprctl", "dispatch", expression], text=True, timeout=3)
    if result.strip() != "ok":
        raise RuntimeError(result.strip())

def restore(address, output, at_cursor=False):
    if not re.fullmatch(r"0x[0-9a-fA-F]+", address):
        raise ValueError("Invalid window address")
    client = next((c for c in query("clients") if c["address"] == address and c.get("mapped")
                   and re.fullmatch(r"special:minimized(?:-[a-z0-9-]{1,40})?", c.get("workspace", {}).get("name", ""))), None)
    if client is None:
        raise ValueError("Cette fenêtre n’est plus minimisée.")
    cursor=query('cursorpos') if at_cursor else None
    monitors=query('monitors')
    monitor = next((m for m in monitors if
        (m['x']<=cursor['x']<m['x']+m['width']/m['scale'] and m['y']<=cursor['y']<m['y']+m['height']/m['scale']) if at_cursor),None) if at_cursor else next((m for m in monitors if m['name']==output),None)
    if monitor is None or monitor["activeWorkspace"]["id"] <= 0:
        raise ValueError("Écran ou bureau indisponible.")
    selector = json.dumps("address:" + address)
    workspace = monitor["activeWorkspace"]["id"]
    if at_cursor:
        dispatch(f'hl.dsp.window.fullscreen_state({{window={selector},internal=0,client=0,action="set"}})')
    dispatch(f"hl.dsp.window.move({{window={selector}, workspace={workspace}, follow=false}})")
    if at_cursor:
        dispatch(f'hl.dsp.window.float({{window={selector},action="set"}})')
        width=min(client['size'][0],monitor['width']/monitor['scale']-40)
        if not client.get('floating'):width=min(width,1400,monitor['width']/monitor['scale']*.65)
        height=min(client['size'][1],monitor['height']/monitor['scale']-40)
        if not client.get('floating'):height=min(height,900,monitor['height']/monitor['scale']*.60)
        x=round(max(monitor['x']+10,min(monitor['x']+monitor['width']/monitor['scale']-width-10,cursor['x']-width/2)))
        y=round(max(monitor['y']+10,min(monitor['y']+monitor['height']/monitor['scale']-height-10,cursor['y']-30)))
        dispatch(f'hl.dsp.window.resize({{window={selector},x={round(width)},y={round(height)},relative=false}})')
        dispatch(f'hl.dsp.window.move({{window={selector},x={x},y={y},relative=false}})')
        dispatch(f'hl.dsp.window.tag({{window={selector},tag="+43pr-quick-float"}})')
    dispatch(f"hl.dsp.focus({{window={selector}}})")

if __name__ == "__main__":
    try:
        restore(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else '', '--at-cursor' in sys.argv)
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
