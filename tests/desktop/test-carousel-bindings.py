"""Load the real Lua bindings with dispatcher stubs; no compositor input."""
from pathlib import Path
import tempfile,subprocess as sp,os,shutil,unittest,json,re
ROOT=Path(__file__).resolve().parents[2]
class CarouselBindings(unittest.TestCase):
 def test_native_defaults_and_personal_overrides_have_one_action_per_chord(self):
  for personal in [False,True]:
   with self.subTest(personal=personal),tempfile.TemporaryDirectory(prefix='43pr-binds-') as d:
    home=Path(d);folder=home/'.config/quickshell';(folder/'state').mkdir(parents=True);shutil.copytree(ROOT/'.config/quickshell/window-carousel',folder/'window-carousel')
    if personal:(folder/'state/binds.lua').write_text('kb_lock="L"\nkb_focus_right="Right"\nkb_carousel="SUPER + Tab"\nkb_quick_switch="ALT + Tab"\n')
    lua='''mainMod="SUPER";terminal="kitty";browser="brave";fileManager="thunar";menu="rofi"
local function proxy(path)
 return setmetatable({}, {__index=function(_,key)return proxy(path.."."..key)end,
 __call=function(_,args)return {target=path,args=args}end})
end
local binds={};hl={dsp=proxy("dsp"),bind=function(key,action,options)table.insert(binds,{key=key,action=action,options=options or {}})end}
dofile(arg[1])
for _,b in ipairs(binds)do print("CHORD "..b.key)end
if arg[2]=="inventory" then return end
local function find(key)
 local result={};for _,b in ipairs(binds)do if b.key:upper():gsub("%s","")==key:upper():gsub("%s","") then table.insert(result,b)end end;return result
end
local personal=arg[2]=="personal"
local lock=find(personal and "SUPER + L" or "SUPER + Tab");assert(#lock==1,"Lock collision")
assert(lock[1].action.target=="dsp.exec_cmd" and lock[1].action.args=="hyprlock","Wrong lock action")
local carousel=find(personal and "SUPER + Tab" or "ALT + Tab");assert(#carousel==1 and type(carousel[1].action)=="function","Carousel collision")
local quick=find(personal and "ALT + Tab" or "ALT + Escape");assert(#quick==1 and quick[1].action.target=="dsp.exec_cmd","Quick switch collision")
local release=find(personal and "Super_L" or "Alt_L");assert(#release==1 and release[1].options.release,"Missing release binding")
print("PASS native/personal shortcut routing")
'''
    fixture=home/'fixture.lua';fixture.write_text(lua)
    result=sp.run(['lua',str(fixture),str(ROOT/'.config/hypr/keybinds.lua'),'personal' if personal else 'native'],env=dict(os.environ,HOME=str(home)),capture_output=True,text=True,timeout=5)
    self.assertEqual(result.returncode,0,result.stderr)
    if not personal:
     expected=json.loads((ROOT/'tests/fixtures/native-chords-50bab24.json').read_text())
     def canonical(chord):
      value=chord.upper().replace(' ','')
      # Native US/latam number-row bindings and physical XKB codes have the
      # same default effect; the physical form also supports the personal AZERTY.
      return re.sub(r'\+([0-9])$',lambda m:'+CODE:'+str(19 if m[1]=='0' else 9+int(m[1])),value)
     actual={canonical(line[6:]) for line in result.stdout.splitlines() if line.startswith('CHORD ')}
     expected={canonical(chord) for chord in expected}
     self.assertTrue(expected<=actual,sorted(expected-actual))
if __name__=='__main__':unittest.main()
