"""Conservative, reviewable behaviour selection shared by both regression entries."""
from dataclasses import dataclass
import difflib
import re

POSITIONS = ('left', 'top', 'right', 'bottom')
STATIC_MODULES = ('cpu', 'ram', 'gpu', 'temp', 'ws', 'tasks', 'media', 'opacity',
                  'brightness', 'volume', 'battery', 'net', 'notif', 'wall',
                  'settings', 'power', 'clock')
# Memberships overlap deliberately: a consumer can have several responsibilities.
FAMILIES = {
    'slot': ('*',),
    'interactive': ('cpu','ram','gpu','temp','disk:*','tasks','minigroup-*','media',
                    'opacity','brightness','volume','battery','net','notif','wall','settings','power','clock'),
    'mod': ('tasks','minigroup-*','opacity','brightness','volume','battery','net','notif','wall','settings','power','clock'),
    'resource': ('cpu','ram','gpu','temp','disk:*'),
    'workspaces': ('ws',),
    'tasks': ('tasks','minigroup-*'),
    'media': ('media',),
    'scroll-value': ('volume','brightness','opacity'),
    'battery-states': ('battery',),
    'commands': ('net','notif','wall','settings','power'),
    'clock-calendar': ('clock',),
}


def matches(module, patterns):
    import fnmatch
    return any(fnmatch.fnmatchcase(module, pattern) for pattern in patterns)


def csv_selection(value, allowed=None, label='selection'):
    if not value:
        return []
    result = value.split(',')
    if any(not x or x != x.strip() for x in result) or len(result) != len(set(result)):
        raise ValueError(f'{label}: empty, duplicate or whitespace-padded value')
    if allowed is not None and set(result) - set(allowed):
        raise ValueError(f'{label}: unknown values {sorted(set(result)-set(allowed))}')
    return result


def valid_module_selector(module):
    return module in STATIC_MODULES or module in ('disk:*', 'minigroup-*') or bool(
        re.fullmatch(r'(disk:|minigroup-)[^\s,*]+', module))


@dataclass(frozen=True)
class Selection:
    modules: tuple = ()
    positions: tuple = POSITIONS
    coverage: str = 'full'
    strict: bool = True

    def __post_init__(self):
        if not self.positions or set(self.positions)-set(POSITIONS):
            raise ValueError('positions: expected left, top, right, bottom')
        if len(self.positions) != len(set(self.positions)):
            raise ValueError('positions: duplicate')
        if any(not valid_module_selector(x) for x in self.modules):
            raise ValueError('modules: unknown selector')
        if self.coverage not in ('full','families'):
            raise ValueError('coverage: expected full or families')

    def accepts(self, module):
        return not self.modules or matches(module, self.modules)

    def resolve(self, available):
        missing = [x for x in self.modules if not any(matches(m, (x,)) for m in available)]
        if missing and self.strict:
            raise ValueError(f'modules unavailable on this fixture: {missing}')
        return sorted(m for m in available if self.accepts(m))

    def describe(self, available):
        selected = self.resolve(available)
        return {'modules': selected, 'positions': list(self.positions), 'coverage': self.coverage,
                'excluded_modules': sorted(set(available)-set(selected)),
                'excluded_positions': sorted(set(POSITIONS)-set(self.positions)),
                'partial': bool(set(available)-set(selected) or set(POSITIONS)-set(self.positions)),
                'unavailable_static_modules': sorted(set(STATIC_MODULES)-set(available)),
                'unavailable_requested_modules': [x for x in self.modules if not any(matches(m,(x,)) for m in available)],
                'global_invariants': ['uniform zoom including hidden modules', 'settings handle and zoom',
                                      'group opacity', 'opacity shortcuts outside bar', 'capture release and restoration']}

    def representatives(self, available):
        selected = self.resolve(available)
        if self.coverage == 'full':
            return selected
        # Native capture/cancel is common; retain each distinct integration path.
        groups = [('ws',), ('tasks','minigroup-*'), ('media',),
                  ('cpu','ram','gpu','temp','disk:*'), ('volume','brightness','opacity'),
                  ('battery',), ('net','notif','wall','settings','power','clock')]
        representatives=list(dict.fromkeys(next((m for m in selected if matches(m,g)), None)
                                  for g in groups if any(matches(m,g) for m in selected)))
        # A new unclassified integration keeps its complete continuation check.
        return representatives+[m for m in selected if not any(matches(m,g) for g in groups)]


ALL_ISOLATED = ('ipc-reconnect','async-save','layout','ipc-release','sizes',
                'legacy-storage','native-defaults','native-badge','updater-safety','carousel-bindings','style-choice','lifecycle','slider','component-states','surface',
                'shared-gestures','selection','edge-margin','bubble-geometry','wallpaper-control','workspace-clicks','settings-escape','storage-layout','storage-data')
# Symbols are the actual functions/components, not the containing filename.
COMMON = {'moduleScale','moduleFactor','individualFactor','uniformScale','adjustSelection',
          'nativeInput','selectionAt','selectPointerTarget','hitAt','interactionTargets',
          'Interactive','Mod','Slot','Panel','Tip','Lane','cancelModuleDrag',
          'beginModuleDrag','beginGroupDrag','finishModuleDrag','finishGroupDrag',
          'releaseInputAfterDisconnect','rememberDrag','layoutSolution','groupPositions',
          'movingRect','findMerge','measure','solve','edgePadding','moduleIsVertical',
          'openEditor','closeEditor','setEditorValue','editorIds','editorValue','syncEditor',
          'resetEditor','appearanceSnapshot','restoreAppearance','updateModuleDrag','updateGroupDrag',
          'rotateDrag','rebuildBar','persistPositions','migrateDisks','save','saveTimer',
          'reservationRect','layoutState','comps','moduleDefs','defaults','panelThick','bubblePadding','moduleGap'}
SYMBOL_FAMILIES = {'ResourceBadge': ('resource',), 'statsC': ('resource',), 'diskC': ('resource',),
                  'wsC': ('workspaces',), 'activateWorkspace': ('workspaces',), 'tasksC': ('tasks',), 'taskBudget': ('tasks',),
                  'activateTask': ('tasks',), 'beginAppDrag': ('tasks',), 'finishAppDrag': ('tasks',),
                  'mediaC': ('media',), 'mediaAct': ('media',), 'batteryC': ('battery-states',),
                  'volumeC': ('scroll-value',), 'brightnessC': ('scroll-value',),
                  'opacityC': ('scroll-value',), 'clockC': ('clock-calendar',),
                  'clockText': ('clock-calendar',), 'clockVText': ('clock-calendar',),
                  'iconC': ('commands',)}


def impact(symbols=(), files=()):
    """Unknown/common impact widens; it never silently skips a consumer."""
    families, reasons, wide = set(), [], not symbols and not files
    for item in symbols:
        name = item.rsplit(':', 1)[-1]
        if name in COMMON or name not in SYMBOL_FAMILIES:
            wide = True
            reasons.append(f'{item}: shared or uncertain impact; all consumers')
        else:
            families.update(SYMBOL_FAMILIES[name])
            reasons.append(f'{item}: {", ".join(SYMBOL_FAMILIES[name])} consumers')
    isolated = set()
    for file in files:
        name = str(file).replace('\\','/').rsplit('/',1)[-1]
        if name == 'BarSurface.qml':
            isolated.add('surface');wide = True
            reasons.append(f'{file}: all bubble/module alpha consumers')
        elif name == 'Slider.qml':
            isolated.add('slider');wide = True
            reasons.append(f'{file}: settings and precise-editor consumers')
        else:
            wide = True
            reasons.append(f'{file}: no precise symbol proof; conservative full scope')
    if wide:
        return {'modules': [], 'isolated': list(ALL_ISOLATED), 'families': list(FAMILIES),
                'reasons': reasons or ['No change supplied: full regression scope'], 'exclusions': []}
    modules = sorted({m for family in families for m in FAMILIES[family]})
    # All selection always retains transport, write and capture invariants.
    isolated.update(('ipc-reconnect','async-save','ipc-release','sizes','lifecycle','shared-gestures','selection'))
    if 'resource' in families:
        isolated.update(('native-badge','legacy-storage','surface','edge-margin','bubble-geometry','storage-layout','storage-data','layout'))
    if 'workspaces' in families:
        isolated.add('workspace-clicks')
    if 'battery-states' in families:
        isolated.add('component-states')
    return {'modules': modules, 'isolated': [x for x in ALL_ISOLATED if x in isolated],
            'families': sorted(families), 'reasons': reasons,
            'exclusions': [f'{f}: no changed producer/consumer in supplied symbols' for f in FAMILIES
                           if f not in families and f not in ('slot','interactive')]}


def changed_symbols(before, after):
    """Conservative lexical spans; anything outside a named block is unknown.

    Include enclosing components AND functions. Balanced braces ignore strings and
    comments, so a nested handler is attributed to its owning production component.
    """
    def spans(text):
        # Preserve offsets while masking quoted strings and comments.
        masked = re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`',
                        lambda m: ''.join('\n' if x=='\n' else ' ' for x in m[0]), text)
        found = []
        patterns = [(r'\bfunction\s+(\w+)\s*\([^)]*\)[^{]*\{', False),
                    (r'\bcomponent\s+(\w+)\s*:\s*\w+\s*\{', False),
                    (r'\bComponent\s*\{\s*id\s*:\s*(\w+)', True)]
        for pattern, component in patterns:
            for m in re.finditer(pattern, masked):
                start = masked.index('{',m.start());depth=1;end=start+1
                while end<len(masked) and depth:
                    depth += (masked[end]=='{')-(masked[end]=='}');end+=1
                found.append((text.count('\n',0,m.start()), text.count('\n',0,end)+1,m[1]))
        return found
    lines = (before.splitlines(), after.splitlines());known=(spans(before),spans(after));names=set()
    for tag,a,b,c,d in difflib.SequenceMatcher(None,*lines).get_opcodes():
        if tag=='equal':continue
        for side,start,end in ((0,a,b),(1,c,d)):
            if start==end:continue
            for row in range(start,end):
                hit=[name for lo,hi,name in known[side] if lo<=row<hi]
                names.update(hit or ['<unknown>'])
    return sorted(names)
