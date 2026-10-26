#!/usr/bin/env bash
# Build explicitly for the installed Hyprland ABI. Never download headers.
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
version=$(hyprctl -j version | python3 -c 'import json,sys; print(json.load(sys.stdin)["commit"])')
[[ "$version" =~ ^[0-9a-f]{40}$ ]] || exit 2
destination="${XDG_DATA_HOME:-$HOME/.local/share}/43pr/bubble-reserve"
mkdir -p -- "$destination"
temporary=$(mktemp "$destination/.build-XXXXXXXX.so")
trap 'rm -f -- "$temporary"' EXIT
read -r -a flags <<< "$(pkg-config --cflags --libs hyprland)"
g++ -std=c++23 -shared -fPIC -O2 -o "$temporary" "$source_dir/main.cpp" "${flags[@]}"
# Install atomically: a previously loaded binary keeps its inode.
chmod 755 "$temporary"
mv -f -- "$temporary" "$destination/$version.so"
printf '%s\n' "$destination/$version.so"
