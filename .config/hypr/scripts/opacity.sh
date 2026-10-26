#!/usr/bin/env bash
# Super+O affects only the current workspace's windows.
exec python3 "$HOME/.config/hypr/scripts/workspace-opacity.py" "$@"
