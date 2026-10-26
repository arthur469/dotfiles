#!/usr/bin/env bash
set -euo pipefail

APPDIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
LAUNCHER="$APPDIR/43pr-whatsapp.desktop"

mkdir -p "$APPDIR"

# Priorité à la véritable PWA installée via Brave.
for file in "$APPDIR"/brave-*.desktop; do
    [ -f "$file" ] || continue
    if grep -qiE "^Name=WhatsApp( Web)?$" "$file" &&
       grep -q -- "--app-id=" "$file"; then
        echo "WhatsApp PWA déjà installée : $file"
        exit 0
    fi
done

if ! command -v brave >/dev/null 2>&1; then
    echo "Brave absent : lanceur non créé."
    exit 0
fi

if [ -e "$LAUNCHER" ]; then
    echo "Lanceur existant : $LAUNCHER"
    exit 0
fi

cat > "$LAUNCHER" <<DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=WhatsApp
Comment=WhatsApp Web via Brave
Exec=brave --app=https://web.whatsapp.com/
TryExec=brave
Icon=whatsapp
Terminal=false
Categories=Network;InstantMessaging;
DESKTOP_EOF

echo "Lanceur WhatsApp créé : $LAUNCHER"
