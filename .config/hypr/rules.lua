-- Docs: https://wiki.hypr.land/Configuring/Basics/Window-Rules/
-- To check class name, open the app and run:
-- hyprctl clients

hl.layer_rule({
    match = { namespace = "rofi" },
    blur = true,
    ignore_alpha = 0.15,
})

-- Per-workspace opacity, edited by Super+O. Fullscreen stays opaque below.
do
    local f = os.getenv("HOME") .. "/.config/hypr/workspace-opacity.lua"
    local fh = io.open(f, "r")
    if fh then fh:close(); local ok, err = pcall(dofile, f); if not ok then print("workspace opacity: " .. tostring(err)) end end
end

hl.window_rule({
    match = { class = ".*", fullscreen = true },
    opacity = "1.0 override", opaque = true,
})



hl.window_rule({
    match = { class = "kitty" },
    suppress_event = "maximize",
})

hl.window_rule({
    name = "file-picker-float",
    match = { class = "^(xdg-desktop-portal-gtk)$" },
    float = true,
    center = true,
    size = "900 600",
})

hl.window_rule({
    name = "float-pavucontrol",
    match = { class = "^(pavucontrol)$" },
    float = true,
})

hl.window_rule({
    name = "float-nm-connection-editor",
    match = { class = "^(nm-connection-editor)$" },
    float = true,
})

hl.window_rule({
    name = "float-blueman-manager",
    match = { class = "^(blueman-manager)$" },
    float = true,
})

hl.window_rule({
    name = "float-open-file",
    match = { title = "^(Open File)$" },
    float = true,
})

hl.window_rule({
    name = "float-save-file",
    match = { title = "^(Save File)$" },
    float = true,
})

-- Client video fullscreen can change without the public fullscreen IPC event.
-- Watch native rule updates too; cache states to avoid recursive property updates.
local opacityFullscreenStates={}
local function syncFullscreenOpacity(w)
    if not w then return end
    local state=tostring(w.fullscreen)..":"..tostring(w.fullscreen_client)
    if opacityFullscreenStates[w.address]==state then return end
    opacityFullscreenStates[w.address]=state
    if w.fullscreen==2 or w.fullscreen_client==2 then
        local selector="address:0x"..w.address:gsub("^0x","")
        for _,prop in ipairs({"opacity","opacity_inactive","opacity_override","opacity_inactive_override","opaque"})do
            hl.dispatch(hl.dsp.window.set_prop({window=selector,prop=prop,value="1"}))
        end
    end
    hl.exec_cmd("python3 "..os.getenv("HOME").."/.config/hypr/scripts/window-opacity.py --sync")
end
hl.on("window.fullscreen",syncFullscreenOpacity)
hl.on("window.update_rules",syncFullscreenOpacity)
hl.on("window.close",function(w)if w then opacityFullscreenStates[w.address]=nil end end)
