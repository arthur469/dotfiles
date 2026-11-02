# Desktop controls regression

The standalone entry is `python3 tests/desktop/run-isolated.py` from this repository. It runs isolated checks, keeps complete private logs, and prints a short summary. It never sends desktop input or changes the live layout. Exit codes, initial errors, timeouts and interruptions are preserved. Reports are under `~/.local/state/43pr-tests/`; `--output` chooses a new private directory.

## Select a justified scope

- `--list` shows selected cases, exclusions and reasons without execution.
- `--symbol Bar.qml:ResourceBadge` follows the shared badge through CPU/RAM/GPU/disks, panel geometry, storage data and capture/write invariants.
- `--before-bar /path/to/saved/Bar.qml` compares the actual function/component spans against the active source. Changed lines outside an identified span, an unknown symbol, a common controller, or `--changed Bar.qml` conservatively select all consumers. Other changed files can be added with repeated `--changed`.
- `--cases sizes,legacy-storage` is an explicit diagnostic subset. It is always reported as partial, with exclusions. It is not a full regression pass.
- `--fresh` executes cases even when compatible clean successes exist. Otherwise reuse requires matching source/tests, executable, runtime/package/library information, font files/fontconfig patterns, bundled QML, parameters, embedded data, environment and an intact original log. Live desktop results are never cached: dynamic window/media/input data cannot be proved equivalent.

Each executable case has a stable `isolated/...` ID. A running marker is persisted before execution; an orphan marker cannot become a clean success. A success after a compatible failure is qualified and cannot enter the reusable cache. Source changes during execution invalidate the result. Complete attempts remain in the private history, and reuse references the original evidence.

## Shared behaviours and integration exceptions

Memberships intentionally overlap; the actual registry is checked by `test-selection.py`.

| Consumers | Shared production boundary | Integration evidence and retained exceptions |
|---|---|---|
| Every module | `Slot`, native ownership/capture, size and precise editor | Every detected child centre plus slot centre/corners, four positions and existing variant states; no input target removed |
| CPU, RAM, GPU, every selected disk | `ResourceBadge` → `Interactive` | Compact/default, warning/value/unknown states, labels and independent disk IDs; existing storage/process/VRAM tests retained |
| Workspaces | `wsC`, workspace MouseAreas/WheelHandler → native controller | Each visible dot, focused state, scrolling on/off, module margins and orientation; `workspace-clicks` checks orphan/stale outputs, normal focus, guards and long-press release on the real delegate |
| Open apps and minimized groups | `tasksC`, `Mod`, child `Interactive` and Flickable → native controller | Collapsed/expanded, control and app children, normal/minimized fixture windows, clipped scrolling strip, limited visible count |
| Media | `mediaC` → `Interactive` | Marquee geometry and orientation, play state, primary/secondary/tertiary bindings retained; real playback actions remain guarded in the input matrix |
| Opacity, brightness, volume | `Mod` → `Interactive`, individual value backends | Their own scroll/secondary actions and disabled states remain separate; an active size gesture must not change another value |
| Battery | `Mod` → `Interactive` | 48 native simulated low/charging/disabled/orientation/size states and 240 pointer points; absence of physical battery is explicitly reported |
| Network, notifications, wallpaper, settings, power | `iconC` → `Mod` → `Interactive` | Per-module command, network state and notification badge remain distinct; app actions guarded during sizing |
| Clock/calendar | `Mod` → `Interactive` | Formats/seconds, orientations, calendar bindings and module-specific child inventory retained |
| Bubbles and settings | `Panel`, `BarSurface`, settings window Shortcut | Native geometry/spacing/stacking, independent alpha and fractional seams, focused-control Escape and search clear-before-close |

The common controller is exercised directly with the real `Bar.qml` handlers and `bar-layout.js`: 18 consumers, lower/upper limits, continuation outside the original module, cancellation/rollback, old/new tokens, proportional group sizes and exclusivity. Only compositor geometry, timers and output boundaries are fixtures. Negative controls removing rollback or stale-token rejection must fail.

`--coverage families` (the desktop default) narrows only repeated **continuation/cancellation** desktop checks to one representative for each distinct integration path. Every module and child keeps the complete matrix, and every module keeps its context/rotation check. Common complementary commands run at the first requested position, backed by the common controller and native orientation/geometry checks; the matrix and P0 moves keep all requested positions. These positional exclusions are reported explicitly. Unclassified integrations retain all complementary positions. The common production-controller proof runs first; unknown integrations retain their own continuation check. `--coverage full` retains the full per-module/per-position complementary matrix. No original test was deleted. The replacement map and measured evidence are in the current Migration Linux report.

## Coordinated real desktop checks

Coordinate exclusive keyboard/pointer access and the brief Quickshell restart used for restoration with Arthur **before** running:

```sh
bash "$HOME/Documents/ChatGPT/Migration Linux/pilotage/TESTS-REGRESSION-P0.sh" --desktop --allow-desktop --positions left --modules cpu,ram --coverage families
```

Both the matrix and complementary controls obey `--modules`/`--positions`. Explicit invalid/unavailable selections fail; automatically inferred unavailable consumers are listed. Global zoom (including hidden/new modules), settings zoom/free handle, group alpha, shortcuts outside the bar and final capture/restoration are deliberately retained and named as global invariants.

`--start`/`--limit` restrict only matrix points; `--matrix-only`, `--extras-only`, `--context-only` and `--p0-only` select mutually exclusive diagnostic phases. They do not constitute a full pass. `--plan` previews the desktop selection without input. IDs include phase, position/variant, module, child path and point. A child path is tied to the exact source fingerprint; geometry coordinates are not case identities.

The running service runtime is selected automatically (`QS_TEST_BINARY` explicitly overrides it). Isolated rendering needs QtTest/Pillow; desktop fixtures need Hyprland, Kitty, a C compiler, Wayland/xkbcommon headers. Preferences, opacity files, pointer and focus are restored with Quickshell stopped for atomic restoration. Test profiles and moving preferences are rejected as baselines. Transport retries remain qualified evidence. A suite interruption never means a complete pass. A display-geometry change aborts the run before further input; it never becomes a successful continuation on a different output. Integer pointer coordinates are clamped inside the target, and native region bounds cover fractional painted pixels. The settings handle fixture is temporarily centred before dragging, and expected drop layouts must be persisted before a fixture is replaced. Hardware hot unplug, other physical displays and a phone session are not asserted by an offscreen fixture.

Measure wall duration, executable case groups, their detailed behaviour counts, console bytes and actual IA usage separately. Cache reuse is a repeat-without-change result, not a faster fresh execution. Without an attributable token counter, report **tokens non mesurés**.

`wallpaper-control` checks day/night transitions, actual-progress verification, delayed pause, recovery with initial failure evidence, missing player/video and hidden/unknown output state using deterministic IPC fixtures. Live playback, shell restart survival and output changes require coordinated separate desktop validation.

## Edge margins and resource modes

`edge-margin` runs the production placement and reservation functions, then checks the actual native C++ projection. It protects normal-axis padding on left/right/top/bottom edges, corner attachment, local rotation, scaling and transitions to/from interior placement. Reservation must retain the original anchor after the painted bubble is offset; classifying that offset again can change axes near a corner.

`bubble-geometry` renders the mixed workspace/CPU/RAM/GPU/disk bubble and checks equal Default/Compact resource widths for all four consumers, labels, values, warnings, smoothing, bounds, rotations and sizes. Default labels are stacked above the value; only the height needed for labels differs.

For coordinated live validation, run `python3 tests/desktop/test-margin-live.py --allow-desktop --output /path/to/new-private-directory`. It checks 24 mixed-bubble cases across the four bar positions, both modes, edge/interior placement and actual native window exclusion. It restores preferences through the existing state helper, takes the shared desktop lock, aborts on display changes, records partial/error results and never reuses live results. Coordinate even though this validator changes the layout without synthetic keyboard/pointer events.

The resource renderer also covers a disk badge wider than its CPU/RAM/GPU neighbours, with independent fractional zoom factors. Sixteen pixel renders check both the visible lateral bubble background and the inset badge outline, in Default/Compact on four bar positions and two scales. A one-unit paint inset follows the normal axis only; Slot dimensions, click areas and text sizing remain unchanged. An integer capture wrapper preserves fractional image extents for these pixel checks; the original 66 fractional-geometry and interaction-area cases remain in the 82-case group.

## Private environment for isolated cases

Each isolated case now runs with private runtime/config/cache/data/state XDG directories, an unavailable session bus, no inherited display or Hyprland instance, and Qt offscreen rendering. HOME stays unchanged because the fixtures locate production source files there. Child processes and temporary directories are cleaned up. This is protection against accidental desktop access, not a security boundary for arbitrary test code.

Run the existing default entry while using the computer normally; no `--desktop` flag is needed. Pointer, keyboard, session audio, bar layout and saved preferences remain outside the fixture. Full compositor input, physical displays and hardware are still separate coordinated validations.

En français : la commande par défaut utilise un environnement temporaire hors écran. Elle permet de continuer à utiliser le bureau pendant les essais isolés. Les scénarios matériels et les essais d'entrée dans le vrai compositeur restent à coordonner ; ils ne sont pas certifiés par ces tests.


`wallpaper-control` also runs the real `start()` function with only process and IPC boundaries stubbed, and feeds its layout options into installed libmpv's software render API. A synthetic 16:9 image must cover ultrawide, matching-ratio and portrait surfaces without stretching, for day/night and systemd/fallback launches. Eight edge pixels per render are checked; the original no-fill options must expose black bands on mismatched ratios. These memory renders require libmpv, create no window or audio, and never connect to the user's player or media. They complement the existing 15 mode/visibility/recovery checks; they do not certify a physical monitor, hotplug or a new shell restart. The renderer helper and libmpv binary are included in cache dependencies.


Upstream integration checks: `native-defaults` protects common scalar/bar/keybind defaults; `carousel-bindings` loads production Lua, checks 70 upstream chords and personal conflicts; `native-badge` compares production rendering geometry against the upstream StatBadge in 48 cases; `updater-safety` exercises both production sync functions in 12 temporary Git histories. These checks do not claim a complete visual equivalence of every upstream component. Personal source defaults are declared explicitly in profiles/personal-defaults.json on the personal branch only.
