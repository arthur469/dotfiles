-- Chargé depuis keybinds.lua. Indépendant du sélecteur de fonds d'écran.
local base = os.getenv("HOME") .. "/.config/quickshell/window-carousel/"
local ipc = "qs ipc -p " .. base .. " call carousel "
local session = tostring(os.time()) .. "-" .. tostring({}):gsub("%W", "")
local serial = 0
local pending = nil
local function begin(direction)
    if not pending then
        serial = serial + 1
        pending = session .. "-" .. serial
    end
    hl.dispatch(hl.dsp.exec_cmd(ipc .. "beginSwitch " .. pending .. " " .. direction))
end
local function release()
    if not pending then return end
    local token = pending
    pending = nil
    hl.dispatch(hl.dsp.exec_cmd(ipc .. "releaseSwitch " .. token))
end
local chord = kb_carousel or "ALT + Tab"
local reverse = chord:gsub("(%S+)$", "SHIFT + %1")
hl.bind(chord, function() begin(1) end)
hl.bind(reverse, function() begin(-1) end)
-- Le compositeur reçoit aussi les relâchements précédant le focus de la surface QML.
-- Identifiants appariés : un IPC tardif d'un ancien appui ne valide pas le suivant.
local released = chord:upper():find("SUPER",1,true) and {"Super_L","Super_R"}
    or chord:upper():find("ALT",1,true) and {"Alt_L","Alt_R"}
    or {"Control_L","Control_R"}
for _, key in ipairs(released) do
    hl.bind(key, release, { release=true, ignore_mods=true, non_consuming=true, transparent=true })
end

hl.bind(kb_quick_switch or "ALT + Escape", hl.dsp.exec_cmd("python3 " .. base .. "quick-switch.py"))
