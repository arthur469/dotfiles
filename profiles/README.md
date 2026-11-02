# Branches and preferences / Branches et réglages

`feature/desktop-extensions` follows upstream 43PR defaults and contains reusable extensions and tests. No personal state is installed from this branch. Super+Tab locks; Delete takes a fullscreen screenshot.

`personal/arthur` derives from that branch and keeps Arthur’s settings separately: French keyboard, current service startup, Wayland Kitty, personal bar layout/sizes/opacity, notifications and keybinds. Super+Tab opens the carousel, Super+L locks and Alt+Tab switches quickly. Switching Git branches does not copy external Quickshell state; the explicit profile application command on the personal branch handles that once, with a backup. Existing external state remains authoritative during ordinary use.

La branche partageable conserve les réglages amont. La branche personnelle contient les choix d’Arthur. Les mises à jour communes sont intégrées dans la première, puis dans la seconde en conservant ses réglages. Ne pas publier la branche personnelle comme proposition amont.

No accounts, device identities, tokens or histories are included. Hardware-dependent volume identities are resolved locally when applying the profile. Display mode selection belongs to the personal profile and must be reviewed on another machine.
