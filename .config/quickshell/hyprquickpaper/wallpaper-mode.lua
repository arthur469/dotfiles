-- Keep manual night pause when mpvpaper's visibility logic resumes playback.
local utils = require('mp.utils')
local runtime = os.getenv('XDG_RUNTIME_DIR')
local function night()
    if not runtime then return false end
    local file = io.open(runtime .. '/43pr-wallpaper-mode.json', 'r')
    if not file then return false end
    local data = utils.parse_json(file:read('*a')); file:close()
    return type(data) == 'table' and data.mode == 'night'
end
mp.observe_property('pause', 'bool', function(_, paused)
    if paused == false and night() then mp.set_property_bool('pause', true) end
end)
if night() then mp.set_property_bool('pause', true) end
