# Optional native desktop extensions

These changes extend the existing 43PR bar and wallpaper picker. UI additions select French or English from the session locale; English is the fallback. They were developed with assistance from OpenAI Codex. Personal accounts, hardware profiles, device identities and live state are excluded from the public branch.

- Hold and drag a module to place it beside another module in a row or column. Drag bubble padding to move the entire group; drop inside another bubble to merge groups. Right-click while holding a left-button drag to rotate the arrangement by 90 degrees, keeping glyphs upright. Holding and releasing without movement changes nothing. The selected bubble has an inset accent outline; the visible inner grip is only three logical pixels per edge. Nearby edges and centers show alignment guides.
- Neighbours reflow during insertion and Open apps expansion. Temporary expansion does not save displaced neighbour positions. Open apps prioritizes minimized windows, limits visible length and retains scrolling when space runs out.
- The optional reserved-space plugin projects window geometry around visible bubbles while preserving the native dwindle/master tree. Native window order, swapping and resizing remain available. True fullscreen is exempt. Edge margin controls all four frame edges and bubble-to-window spacing. Turning reservation off restores native geometry.
- The plugin is pinned to the exact Hyprland commit. Build explicitly using `.config/hypr/plugins/bubble-reserve/build.sh` in the repository after a Hyprland upgrade. No binary is downloaded or rebuilt automatically. Without a compatible binary the ordinary bar uses the standard exclusive zone; interior free-bubble reservation is unavailable.
- Brightness wheel changes use the bar volume increment, show the requested number immediately and coalesce hardware writes after 280 ms. Right-click toggles between 0% and the last positive level for that output during the session. Left-click opens the existing display settings. Hardware backlight or DDC/CI is used rather than a gamma filter.
- CPU/RAM/GPU process lists group application processes with aggregate metrics and expandable children. Group or child close actions require confirmation beside the row. SIGTERM is preferred; force stop remains an explicit later action. UID, process start identity and pidfd protections remain active. Hover freezes updates; leaving retains scrolling, while closing resets it. RAM uses PSS when available.
- Super+O opens workspace opacity; Super+Shift+O opens a window override. The native slider supports 40–100%, mouse, wheel and one-percent keyboard increments. Fullscreen is always opaque, with the desired value restored afterwards. Left-clicking the opacity module opens the Opacity section in Display settings. The bar retains the same native, bar-oriented OSD as volume and brightness; scrolling over the icon or track adjusts the workspace by 1%. The keyboard shortcuts retain the dedicated opacity panel and its wheel support. Ctrl+Super+O and right-clicking the opacity module clear all current overrides, including windows on other workspaces; each inherits its own workspace value. Brave is adjustable outside fullscreen.
- Native mpvpaper visibility auto-pause avoids decoding an unseen wallpaper. One player serves the workspaces rather than running a player per hidden workspace. The optional night command pauses that player; day releases the pause. Media players and background tasks are independent. Personal day/night routines are not part of the public dotfiles.
- The Hyprland portal configuration explicitly selects GTK file dialogs. Applications that implement their own Ctrl+O dialog retain that behaviour.

Validation used Quickshell 0.3.2 and Hyprland 0.56.2, dedicated test windows, an isolated nested compositor and one physical 3440×1440 output. Process termination, brightness toggle/restore, native swapping/resizing, fullscreen opacity and minimized-window drag restoration were exercised. Multiple physical monitors and fractional scaling remain untested. Very dense bubble layouts can require smaller modules or scale settings.


## October 27 refinements

With the pointer over a module or bubble, Super+O adjusts opacity for all modules/bubbles; Super+Shift+O adjusts the target only. Contents select a module; background/border selects the group. Outside these objects, the existing workspace/window controls remain in use. Ctrl+O remains available to applications. The range is 40–100%, in 1% steps, without multiplying parent/child alpha twice. Transfers inherit the destination opacity; detached modules retain theirs. Display settings can reset object opacity.

Workspace dots use the local group orientation. Icon ink is centred independently of its monospace advance. End drop zones are more forgiving. Open apps expansion preserves saved anchor order within each band; releasing a drag applies its final position without a settling animation. A wider settings handle leaves room to drag beside its snap buttons.

While a keyboard opacity panel is open, scrolling anywhere on its output adjusts its captured scope and cannot scroll the underlying application. Clicking the slider icon sets 40%. Fullscreen remains opaque.

Steam grouping includes its supervising client rather than only a mapped web helper. Closing an individual supervised helper can still restart it. Native geometry reservation sends the final client size once, avoiding alternating intermediate sizes. The remaining client-side resize cursor has not been visually validated; no global cursor rule is imposed.

`qs ipc call notifications night true` suppresses all popups and sounds while retaining history. Repeating it preserves the original DND choice. `night false` restores that choice. A manual DND toggle leaves the temporary night control. Personal routines are excluded from the clean image.

The Terminal ASCII wallpaper is rendered from Odysseus's existing effect into a lightweight looping video, with no UI or private data. Select it through the existing native wallpaper picker; normal visibility and night pause rules apply.

For Quickshell 0.3.2 startup before BlueZ, `scripts/wait-bluetooth.py` provides a bounded eight-second readiness wait without powering hardware. A user unit can use `ExecStartPre=/usr/bin/python3 %h/.config/quickshell/scripts/wait-bluetooth.py`. A later BlueZ restart can still require restarting Quickshell. Existing upstream report: https://github.com/quickshell-mirror/quickshell/issues/1201.


Hold left-click and **wheel**, without Ctrl, to resize an individual component from 50 to 200%, in 5% steps. A group preserves relative sizes. Display groups Brightness, Module zoom and Workspace opacity in one card, using the same row component and an icon for every control. Common zoom ranges from 50 to 200%, in addition to individual sizes; its icon resets 100%. No zoom module is added to the bar. Existing text scale remains separate. Input geometry, popup anchors and reserved space follow the result, while Open apps retains scrolling when its visible length is reduced. `qs ipc call bar resetSizes` resets both individual sizes and common zoom.

Standalone symbols share a 16-logical-pixel reference square at normal bar scale. Their painted bounds are proportionally fitted and centred in each button, including supplementary Unicode glyphs; individual module scaling is applied afterwards. The notification count stays in a separate corner badge. Rotating a module from its contents preserves its orientation on release and the cursor grip; input rectangles follow free positions.

Configs → Keybinds also lists the carousel directions, quick Alt+Tab switching, window opacity and reset, minimized-window actions and Super+mouse gestures. Fixed bindings remain read-only like native workspace shortcuts; derived opacity chords follow the editable base Opacity key. Quick actions use the same `kb_qa` identifier as Lua. Default fallbacks reserve Super+L for locking, Print for an area screenshot and Shift+Print for a full screenshot.

Contextual input routing requires plugin 0.3 or later, following the existing Opacity key in binds.lua and the actual bar surface instead of adding a second global Super+O command. Rebuild explicitly with its build.sh after plugin source updates, even when Hyprland itself is unchanged. X11 and Hyprcursor sizes now follow the same session value.


## Contextual gestures and precise controls

Ctrl+right-click contents for module controls, or the background/border for bubble controls. The panel retains its target and position when the pointer leaves. Size and opacity support the native slider, wheel, arrow keys and percentage entry. Enter/Apply confirms; Escape/Cancel restores the previous state. Reset restores the current scope; confirm to retain that reset. Configs → Keybinds lists the commands with concise labels; settings pages contain no shortcut paragraphs.

An active manipulation owns input until release: scrolling continues to resize the same target outside its bounds, while other modules/buttons/shortcuts cannot take over. Rotation remains part of movement and does not turn into resizing. Escape cancels; hidden/destroyed sources or disconnected outputs terminate safely. Release clicks do not activate neighbouring controls. Placement and insertion follow the moved rectangle, with target hysteresis, rather than the cursor point alone.


Day mode resumes the selected video and recovers a missing player. The same native mpvpaper engine runs in a separate transient user unit, 43pr-wallpaper-player.service, so restarting Quickshell does not terminate it. Native visibility auto-pause remains permitted; night mode forces pause. Static wallpapers stay static. A missing selected video or failed player startup is reported instead of returning an unverified success.

The three dots above settings are snap buttons; dragging the free handle area moves the window. Maintenance checks cover that handle, contextual keys, fullscreen opacity and the wallpaper night/day cycle. Interactive test layouts must be captured from a stable baseline, restored with Quickshell stopped, and verified afterwards; test profiles must never be consolidated into an image.
