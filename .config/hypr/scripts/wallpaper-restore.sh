#!/usr/bin/env bash
# Draw the wallpaper recorded by theme.py (set by the installer or the picker).
state="${XDG_STATE_HOME:-$HOME/.local/state}/43pr/state.json"

# The existing 43PR picker records live videos here. Restore through its own
# command, rather than starting a second wallpaper manager.
live_state="$HOME/.cache/43pr/last-live"
if [[ -s "$live_state" ]]; then
    IFS= read -r live < "$live_state"
    case "${live,,}" in
        *.mp4|*.mkv|*.webm|*.mov)
            if [[ -f "$live" ]]; then
                for _ in {1..20}; do awww query >/dev/null 2>&1 && break; sleep 0.25; done
                exec bash "$HOME/.config/quickshell/hyprquickpaper/commands.sh" "$live"
            fi
            ;;
    esac
fi


img="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("wallpaper",""))' "$state" 2>/dev/null)"
[[ -f "$img" ]] || exit 0

# Wait for the awww daemon to be ready (up to ~5s)
for _ in {1..20}; do
    awww query >/dev/null 2>&1 && break
    sleep 0.25
done

awww img "$img" -t none
