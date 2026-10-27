import QtQuick
import "scripts/bar-layout.js" as BarLayout
import QtQuick.Layouts
import QtQuick.Effects
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import Quickshell.Services.Pipewire
import Quickshell.Services.UPower

Scope {
    id: root
    property var notificationController: null
    property var powerController: null
    property var volumeController: null
    property var opacityController: null
    readonly property string notificationPosition: cfg.position

    // ───────────────────────── Config ─────────────────────────
    // Single source of truth for defaults (used by the adapter AND reset).
    readonly property var defaults: ({
        // layout
        position: "left", style: "joined", thickness: 20, margin: 4,
        reserveSpace: true, allScreens: true, freeLayout: false, groupCells: ({}), groupRotations: ({}), groupOpacity: ({}), moduleOpacity: ({}), moduleScale: ({}), moduleZoom:1, autoGroup: true, quickFloatRetile: false, windowGroupsEnabled: false, windowGroups: [], collapsedGroups: ({}), dropToMinimize: false,
        // appearance
        scale: 1.0, bgOpacity: 0.5, border: false, radius: 16, calRadius: 15,
        // tooltips
        tooltips: true, tooltipHints: true, tipDelay: 450,
        // modules
        modPad: 20, wsDot: 10, wsGap: 8, wsScroll: true,
        statsMode: "compact", statsWarn: 85, statsGpu: true, batLowPct: 15,
        volStep: 2, volMax: 100,
        // clock / calendar
        clock24: true, clockSeconds: false, weekMonday: true,
        tasksCollapsed: false, taskIconSize: 18, taskMaxVisible: 5, moduleGroups: [],
        // module placement
        hidden: "cpu,ram,gpu,wall,settings,tasks",
        startMods: "cpu,ram,gpu,ws",
        centerMods: "clock",
        endMods: "media,volume,battery,net,notif,wall,settings,power"
    })
    readonly property var positions: ["top", "right", "bottom", "left"]
    readonly property var styles: ["floating", "joined", "strip"]
    readonly property var sections: ["start", "center", "end"]
    readonly property var statsModes: ["default", "compact"]

    // Live config object, edited by BarPage (the settings page).
    readonly property var config: cfg

    Component.onCompleted: BluetoothState.init()

    FileView {
        id: cfgFile
        path: Quickshell.env("HOME") + "/.config/quickshell/state/bar-state.json"
        printErrors: false
        watchChanges: true                 // BarPage writes this file; pick its changes up live
        onFileChanged: reload()
        onLoadFailed: error => { if (error === FileViewError.FileNotFound) writeAdapter(); }

        adapter: JsonAdapter {
            id: cfg
            property string position: root.defaults.position
            property string style: root.defaults.style
            property int thickness: root.defaults.thickness
            property int margin: root.defaults.margin
            property bool windowGroupsEnabled: root.defaults.windowGroupsEnabled
            property var windowGroups: root.defaults.windowGroups
            property var collapsedGroups: root.defaults.collapsedGroups
            property bool dropToMinimize: root.defaults.dropToMinimize
            property bool freeLayout: root.defaults.freeLayout
            property var groupCells: root.defaults.groupCells
            property var groupRotations: root.defaults.groupRotations
            property var groupOpacity: root.defaults.groupOpacity
            property var moduleOpacity: root.defaults.moduleOpacity
            property var moduleScale:root.defaults.moduleScale
            property real moduleZoom:root.defaults.moduleZoom
            property bool autoGroup: root.defaults.autoGroup
            property bool quickFloatRetile: root.defaults.quickFloatRetile
            property bool reserveSpace: root.defaults.reserveSpace   // push windows away from the bar
            property bool allScreens: root.defaults.allScreens       // false → first screen only
            property real scale: root.defaults.scale
            property real bgOpacity: root.defaults.bgOpacity
            property bool border: root.defaults.border
            property int radius: root.defaults.radius            // bar corner radius
            property int calRadius: root.defaults.calRadius      // calendar popup corner radius
            property bool tooltips: root.defaults.tooltips
            property bool tooltipHints: root.defaults.tooltipHints // show "Left click: ..." lines in tooltips
            property int tipDelay: root.defaults.tipDelay        // ms before a tooltip appears
            property int modPad: root.defaults.modPad            // horizontal padding of text modules
            property int wsDot: root.defaults.wsDot              // workspace dot size
            property int wsGap: root.defaults.wsGap              // gap between workspace dots
            property bool wsScroll: root.defaults.wsScroll       // scroll on workspaces to switch
            property string statsMode: root.defaults.statsMode   // "default" | "compact"
            property bool statsGpu: root.defaults.statsGpu
            property int statsWarn: root.defaults.statsWarn      // CPU/RAM % that turns red
            property int batLowPct: root.defaults.batLowPct      // battery % that turns red
            property int volStep: root.defaults.volStep          // % per scroll notch
            property int volMax: root.defaults.volMax            // max volume %
            property bool clock24: root.defaults.clock24
            property bool clockSeconds: root.defaults.clockSeconds
            property bool weekMonday: root.defaults.weekMonday
            property var moduleGroups: []
            property bool tasksCollapsed: root.defaults.tasksCollapsed
            property int taskIconSize: root.defaults.taskIconSize
            property int taskMaxVisible: root.defaults.taskMaxVisible   // calendar week starts on Monday
            property string hidden: root.defaults.hidden         // comma list of disabled modules
            property string startMods: root.defaults.startMods
            property string centerMods: root.defaults.centerMods
            property string endMods: root.defaults.endMods
        }
    }

    // Only the bar's own changes (IPC) are saved from here; BarPage saves its own.
    Timer { id: saveTimer; interval: 300; onTriggered: cfgFile.writeAdapter() }
    function save() { saveTimer.restart(); }

    function resetSettings() { for (const k in defaults) cfg[k] = defaults[k]; }
    readonly property bool modified: Object.keys(defaults).some(k => cfg[k] !== defaults[k])

    // ───────────────────────── Derived layout ─────────────────────────
    readonly property bool vertical: cfg.position === "left" || cfg.position === "right"
    readonly property bool joined: cfg.style !== "floating"
    readonly property bool strip: cfg.style === "strip"
    readonly property int bubblePadding: 3
    readonly property int panelThick: Math.max(vertical ? cfg.thickness + 6 : cfg.thickness, isOn("tasks") ? Math.round(cfg.taskIconSize * cfg.scale) + 6 : 0)
    readonly property int effEdge: Math.round(cfg.margin*cfg.scale)
    readonly property int effGap: Math.round(cfg.margin*cfg.scale)
    readonly property real barRadius: strip ? 0 : cfg.radius
    readonly property color bgColor: Qt.alpha(Theme.bg, cfg.bgOpacity)
    readonly property color borderColor: Theme.accent

    function s(n) { return Math.round(n * cfg.scale); }

    readonly property var sz: ({
        stat: s(12), clock: s(12), marquee: s(11),
        icon: s(16), batIcon: s(13), batText: s(12), power: s(15),
        taskIcon: s(18),
        calTime: s(30), calDate: s(12), calMonth: s(13), calArrow: s(16),
        calWeekday: s(11), calDay: s(12)
    })
    readonly property int sizeIconGap: 12
    readonly property int iconYOffset: 1

    // margin for one side of the bar frame
    function edgeMargin(side) { return cfg.freeLayout ? 0 : ((vertical ? side==="left"||side==="right" : side==="top"||side==="bottom") ? effEdge : 0); }

    // ───────────────────────── App icon resolution ─────────────────────────
    // Resolves an icon for ANY window (rofi, Steam, Electron apps, XWayland
    // classes, Flatpaks, reverse-DNS app ids, absolute icon paths, ...).
    // Tries many candidates and returns the first that actually exists.
    function iconFor(appId) {
        const id = appId ?? "";
        const low = id.toLowerCase();
        const cands = [];
        const add = c => { if (c && c !== "" && cands.indexOf(c) < 0) cands.push(c); };

        // 1) desktop entry (matches StartupWMClass, id, name, ...)
        let entry = null;
        try {
            entry = DesktopEntries.heuristicLookup(id)
                 ?? DesktopEntries.heuristicLookup(low)
                 ?? DesktopEntries.byId(id)
                 ?? DesktopEntries.byId(low);
        } catch (e) { entry = null; }
        if (entry) {
            add(entry.icon);
            add(entry.id);
            add((entry.id ?? "").toLowerCase());
        }

        // 2) the app id itself, in several spellings
        add(id);
        add(low);
        add(low.replace(/\s+/g, "-"));
        add(low.replace(/[._\s]+/g, "-"));
        const parts = low.split(".");
        if (parts.length > 1) {
            add(parts[parts.length - 1]);          // org.gnome.Nautilus → nautilus
            add(parts.slice(-2).join("-"));
        }
        const dash = low.split("-");
        if (dash.length > 1) add(dash[0]);         // google-chrome-stable → google

        // 3) first candidate that resolves wins
        for (const c of cands) {
            if (c.startsWith("/")) return "file://" + c;      // absolute path in .desktop
            if (c.startsWith("file://") || c.startsWith("image://")) return c;
            const p = Quickshell.iconPath(c, true);            // true → "" when missing
            if (p !== "") return p;
        }

        // 4) generic fallbacks
        return Quickshell.iconPath("application-x-executable", true)
            || Quickshell.iconPath("application-default-icon", true)
            || Quickshell.iconPath("image-missing");
    }

    // ───────────────────────── Clock formatting ─────────────────────────
    function clockText(d) {
        const h24 = d.getHours();
        const h12 = h24 % 12 || 12;
        const mm = String(d.getMinutes()).padStart(2, "0");
        const ss = String(d.getSeconds()).padStart(2, "0");
        if (cfg.clock24)
            return (cfg.clockSeconds
                ? String(h24).padStart(2, "0") + ":" + mm + ":" + ss
                : String(h24).padStart(2, "0") + ":" + mm);
        const suffix = h24 >= 12 ? "PM" : "AM";
        return cfg.clockSeconds
            ? h12 + ":" + mm + ":" + ss + " " + suffix
            : h12 + ":" + mm + " " + suffix;
    }
    function clockVText(d) {
        const h24 = d.getHours();
        const h = cfg.clock24
            ? String(h24).padStart(2, "0")
            : String(h24 % 12 || 12);
        const mm = String(d.getMinutes()).padStart(2, "0");
        const parts = [h, mm];
        if (cfg.clockSeconds)
            parts.push(String(d.getSeconds()).padStart(2, "0"));
        if (!cfg.clock24)
            parts.push(h24 >= 12 ? "PM" : "AM");
        return parts.join("\n");
    }

    // ───────────────────────── Battery ─────────────────────────
    readonly property var battery: UPower.devices.values.find(d => d.isLaptopBattery)
        ?? (UPower.displayDevice && UPower.displayDevice.isPresent
            && UPower.displayDevice.type === UPowerDeviceType.Battery
            ? UPower.displayDevice : null)
    readonly property int batPct: battery ? Math.round(battery.percentage * 100) : 0
    readonly property bool batCharging: battery !== null
        && (battery.state === UPowerDeviceState.Charging
            || battery.state === UPowerDeviceState.PendingCharge
            || battery.state === UPowerDeviceState.FullyCharged)
    readonly property bool batLow: battery !== null && !batCharging && batPct <= cfg.batLowPct
    readonly property var batIcons: ["\uf244", "\uf243", "\uf242", "\uf241", "\uf240"]
    readonly property string batIcon: batIcons[batPct >= 90 ? 4 : batPct >= 65 ? 3 : batPct >= 40 ? 2 : batPct >= 15 ? 1 : 0]

    function fmtTime(sec) {
        const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60);
        return h > 0 ? h + "h " + m + "m" : m + "m";
    }

    readonly property string batTip: {
        if (battery === null) return "";
        const t = batCharging ? battery.timeToFull : battery.timeToEmpty;
        const st = battery.state === UPowerDeviceState.FullyCharged ? "fully charged"
                 : batCharging ? "charging" : "on battery";
        return "Battery " + batPct + "% · " + st
            + (t > 0 ? " · " + fmtTime(t) + (batCharging ? " to full" : " left") : "");
    }

    // ───────────────────────── Module registry ─────────────────────────
    // Modules with `cmd` are rendered by the generic iconC component:
    //   g = glyph, tip = tooltip title, hint = left-click description.
    // Modules without it have a dedicated Component below (see `comps`).
    readonly property var moduleDefs: [
        { id: "cpu",    l: "CPU" },
        { id: "ram", l: "RAM" },
        { id: "gpu", l: "GPU" },
        { id: "ws",       l: "Workspaces" },
        { id: "tasks",    l: "Open apps" },
        { id: "media",    l: "Media" },
        {id:"opacity",l:LocaleState.tr("Opacité","Opacity"),g:"󰗌",tip:LocaleState.tr("Opacité des fenêtres","Window opacity"),hint:LocaleState.tr("Régler l’opacité","Adjust opacity")},
        { id: "brightness", l: "Luminosité", g: "󰃠", tip: "Luminosité de cet écran", hint: "Régler la luminosité" },
        { id: "volume",   l: "Volume" },
        { id: "battery",  l: "Battery" },
        { id: "net",      l: "Network",       cmd: "qs ipc call settings network",
                                              hint: "Open network settings" },
        { id: "notif",    l: "Notifications", cmd: "qs ipc call notifications toggle", g: "\uDB80\uDC9C",
                                              tip: "Notifications", hint: "Toggle notification panel" },
        { id: "wall",     l: "Wallpapers",    cmd: "qs -n -p ~/.config/quickshell/hyprquickpaper", g: "\uDB80\uDEE9",
                                              tip: "Wallpapers", hint: "Open wallpaper picker" },
        { id: "settings", l: "Settings",      cmd: "qs ipc call settings toggle", g: "\uDB81\uDC93",
                                              tip: "Settings", hint: "Open settings" },
        { id: "power",    l: "Power",         cmd: "qs ipc call powermenu toggle", g: "\uDB81\uDC25",
                                              tip: "Power menu", hint: "Open", fixed: true }
    ].concat(cfg.windowGroupsEnabled ? cfg.windowGroups.map(g=>({id:"minigroup-"+g.id,l:g.name})) : [])
    readonly property var moduleIds: moduleDefs.map(d => d.id)
    readonly property var defMap: moduleDefs.reduce((m, d) => { m[d.id] = d; return m; }, {})
    readonly property var comps: ({
        opacity: opacityC, brightness: brightnessC, cpu: statsC, ram: statsC, gpu: statsC, ws: wsC, tasks: tasksC, media: mediaC, volume: volumeC, battery: batteryC, icon: iconC
    })

    function csv(str) { return str === "" ? [] : str.split(","); }
    function valid(id) { return id === "clock" || moduleIds.indexOf(id) >= 0; }

    // enable / disable
    readonly property var hiddenList: csv(cfg.hidden)
    function isOn(id) { return hiddenList.indexOf(id) < 0; }
    function setOn(id, on) {
        const h = hiddenList.filter(x => x !== id);
        if (!on) h.push(id);
        cfg.hidden = h.join(",");
    }

    function modVisible(id) {
        if (!isOn(id)) return false;
        switch (id) {
        case "cpu": case "ram": case "gpu":   return true;   // icon-sized, fits any bar orientation
        case "media":   return Marquee.player !== null && Marquee.title !== "";
        case "battery": return battery !== null;
        default:        return true;
        }
    }

    // sections
    readonly property var layoutGroups: BarLayout.groups(cfg, moduleIds)
    readonly property var startList: layoutGroups.find(g => g.id === "start").items
    readonly property var centerList: layoutGroups.find(g => g.id === "center").items
    readonly property var endList: layoutGroups.find(g => g.id === "end").items
    function listOf(sec) { const g = layoutGroups.find(g => g.id === sec); return g ? g.items.slice() : []; }
    function setList(sec, a) { cfg[sec + "Mods"] = a.join(","); }
    function sectionOf(id) { const g = layoutGroups.find(g => g.items.includes(id)); return g ? g.id : "end"; }
    function applyLayout(value) { for (const k in value) cfg[k] = value[k]; save(); }
    function moveTo(id, sec) { applyLayout(BarLayout.move(cfg,moduleIds,id,sec,0.5)); }

    function canShift(id, d) {
        const a = listOf(sectionOf(id)), j = a.indexOf(id) + d;
        return j >= 0 && j < a.length;
    }

    function shiftBy(id, d) {
        if (!canShift(id, d)) return;
        const sec = sectionOf(id), a = listOf(sec), i = a.indexOf(id), j = i + d;
        [a[i], a[j]] = [a[j], a[i]];
        applyLayout(BarLayout.move(cfg,moduleIds,id,sec,0.5,j));
    }

    property var moduleSlots: []
    property var bubblePanels: []
    property bool nativeReservation: false
    property bool nativeControlBridge:false
    property bool nativeInputBridge:false
    property bool nativeLeftHeld:false
    property bool discardReleaseClick:false
    Timer{id:releaseClickTimer;interval:250;onTriggered:root.discardReleaseClick=false}
    property string lastNativeKind:""
    property real lastNativeDelta:0
    property double nativeInputToken:0
    property double closedNativeToken:-1
    property point nativePressPoint:Qt.point(0,0)
    readonly property bool manipulating:!!dragItem||dragGroupId!==""||editOpen
    function reservationRect(panel){const r=root.taskRect(panel),pad=BarLayout.edgePadding(r,panel.hostWindow.screen.width,panel.hostWindow.screen.height,root.effEdge,cfg.position);return Object.assign({},r,{gapX:pad.gapX,gapY:pad.gapY});}
    readonly property string reservedBubbleState: JSON.stringify({active:cfg.reserveSpace && barVisible && barLive,margin:root.effEdge,interactive:barVisible&&barLive&&!editOpen,modal:editOpen,
        minimized:taskButtons.filter(t=>t&&t.isMinimized&&t.visible).map(t=>({address:"0x"+t.hyprHandle.address.replace(/^0x/,""),geometry:root.taskRect(t)})),
        rectangles:bubblePanels.filter(p=>p&&p.hostWindow&&p.visible).map(p=>root.reservationRect(p))})
    Connections {
        target:Hyprland
        function onRawEvent(event) {
            if(event.name==="43pr_bubble_input"){root.nativeInput(event.data);return;}
            if(event.name==="43pr_bubble_control"){root.nativeControlHeld=event.data.trim()==="1";return;}
            if(event.name==="43pr_bubble_rotate"){root.rotateDrag();return;}
            if(cfg.reserveSpace&&['openwindow','changefloatingmode','movewindow','movewindowv2','activewindowv2','configreloaded'].includes(event.name))reserveBubbleTimer.restart();
        }
    }
    onReservedBubbleStateChanged: {if(root.manipulating){if(!reserveBubbleTimer.running)reserveBubbleTimer.start();}else reserveBubbleTimer.restart();}
    Timer { id:reserveBubbleTimer;interval:180;onTriggered:{if(reserveBubbleWorker.running){restart();return;}reserveBubbleWorker.command=["python3",Qt.resolvedUrl("scripts/bubble-space.py").toString().replace("file://",""),"--state",root.reservedBubbleState];reserveBubbleWorker.running=true;} }
    Process {id:reserveBubbleWorker;stdout:StdioCollector{onStreamFinished:{try{const state=JSON.parse(text);root.nativeReservation=state.ready;root.nativeControlBridge=state.controlBridge===true;root.nativeInputBridge=state.inputBridge===true;}catch(e){root.nativeReservation=false;root.nativeControlBridge=false;root.nativeInputBridge=false;}}}stderr:StdioCollector{onStreamFinished:if(text.trim())console.warn("Bubble reservation: "+text.trim())}}

    property var calendarControllers: []
    property string layoutPriority: ""
    property string layoutAxis: vertical ? "y" : "x"
    property bool dragMoved: false
    property point dragGrip: Qt.point(0,0)
    property point dragGripRatio:Qt.point(0,0)
    readonly property point moduleGrip:dragItem?Qt.point(dragItem.width*dragGripRatio.x,dragItem.height*dragGripRatio.y):dragGrip
    property var dragTargets: ({})
    property var dragModuleTargets: ({})
    property var dragSavedCells: null
    property var dragSavedRotations: null
    property int dragModuleRotation:0
    property bool opacityGesture: false
    property string gestureMode:""
    property real selectedOpacity: 1
    property Item opacityTarget: null
    property bool nativeControlHeld:false
        function queueSelectionWheel(delta,modifiers){return adjustSelection(delta,modifiers);}
    function flushSelectionWheel(){}
    property bool selectionSizing:false
    property real selectedScale:1
    function individualFactor(id){return typeof cfg.moduleScale[id]==="number"?Math.max(0.5,Math.min(2,cfg.moduleScale[id])):1;}
    function moduleFactor(id){return individualFactor(id)*Math.max(0.5,Math.min(2,cfg.moduleZoom));}
    function adjustSelection(delta,modifiers){
        if(gestureMode!==""&&gestureMode!=="size")return true;gestureMode="size";
        if(!dragItem&&!dragGroupId)return false;
        const ids=dragItem?[dragItem.modelData]:(layoutGroups.find(g=>g.id===dragGroupId)||{items:[]}).items;
        if(!ids.length)return false;
        const resized=BarLayout.resizeModules(cfg.moduleScale,ids,delta/120*0.05),scales=resized.values,next=resized.average;
        cfg.moduleScale=scales;selectedScale=next;selectionSizing=true;opacityGesture=true;dragMoved=false;mergePanel=null;previewCells=({});
        opacityTarget=dragItem||bubblePanels.find(p=>p&&p.groupId===dragGroupId&&p.hostWindow===dragWindow);
        selectionOsdTimer.restart();save();return true;
    }
    function groupAlpha(id) { return typeof cfg.groupOpacity[id]==="number"?Math.max(0.4,Math.min(1,cfg.groupOpacity[id])):1; }
    function moduleAlpha(id) { return typeof cfg.moduleOpacity[id]==="number"?Math.max(0.4,Math.min(1,cfg.moduleOpacity[id])):groupAlpha(sectionOf(id)); }
    Timer {id:selectionOsdTimer;interval:1400}
    BarAnchor {id:selectionPlacement;position:cfg.position;target:root.opacityTarget}
    PanelWindow {
        id:selectionOsd;visible:selectionOsdTimer.running&&!!root.opacityTarget
        screen:root.opacityTarget&&root.opacityTarget.QsWindow.window?root.opacityTarget.QsWindow.window.screen:Quickshell.screens[0]
        anchors {left:true;top:true}
        implicitWidth:270*cfg.scale;implicitHeight:70*cfg.scale;color:"transparent";exclusionMode:ExclusionMode.Ignore
        WlrLayershell.layer:WlrLayer.Overlay;WlrLayershell.namespace:"43pr-selection-opacity"
        readonly property point placement:selectionPlacement.place(width,height,screen.width,screen.height,0,0)
        margins.left:placement.x;margins.top:placement.y
        mask:Region{}
        Rectangle {anchors.fill:parent;radius:Theme.radius;color:Theme.bg;border.width:1;border.color:Theme.accent
            Slider {anchors.fill:parent;anchors.margins:14;enabled:false;icon:"󰗌";label:root.selectionSizing?LocaleState.tr("TAILLE","SIZE"):"";value:root.selectionSizing?(root.selectedScale-0.5)/1.5:(root.selectedOpacity-0.4)/0.6;displayFrom:root.selectionSizing?50:40;displayTo:root.selectionSizing?200:100;step:root.selectionSizing?1/30:1/60;displayText:Math.round((root.selectionSizing?root.selectedScale:root.selectedOpacity)*100)+"%"}
        }
    }
    property bool editOpen:false
    property string editScope:"module"
    property string editId:""
    property string editMode:"both"
    property string editField:"size"
    property Item editTarget:null
    property var editScreen:null
    property point editPoint:Qt.point(12,12)
    property var editBefore:null
    function slotFor(item){let p=item;while(p){if(p.moduleSlotMarker===true)return p;p=p.parent;}return null;}
    function hitAt(x,y){
        function inside(item){const r=root.taskRect(item),screen=item.hostWindow?item.hostWindow.screen:null;return r&&screen&&x>=r.x+screen.x&&x<r.x+screen.x+r.width&&y>=r.y+screen.y&&y<r.y+screen.y+r.height;}
        const slot=moduleSlots.find(s=>s&&s.visible&&s.hostWindow&&inside(s));if(slot)return {item:slot,group:false};
        const group=bubblePanels.find(p=>p&&p.visible&&p.hostWindow&&inside(p));return group?{item:group,group:true}:null;
    }
    function nativeInput(data){
        const parts=data.split(","),kind=parts[0],token=Number(parts[1]),x=Number(parts[2]),y=Number(parts[3]),delta=Number(parts[4]);
        if(!Number.isFinite(token)||!Number.isFinite(x)||!Number.isFinite(y))return;lastNativeKind=kind;if(kind==="wheel")lastNativeDelta=delta;
        if(kind==="press"){nativeLeftHeld=true;closedNativeToken=-1;nativeInputToken=token;nativePressPoint=Qt.point(x,y);return;}
        if(kind==="menu"||kind==="opacity-all"||kind==="opacity-target"){
            if(manipulating)return;const hit=hitAt(x,y);if(hit)openEditor(hit.item,hit.group,kind==="menu"?"both":"opacity",kind==="opacity-all");else if(kind!=="menu"&&opacityController)root.run("qs ipc call opacity openControl "+(kind==="opacity-all"?"workspace":"window"));return;
        }
        if(token!==nativeInputToken)return;
        if(kind==="cancel"){nativeLeftHeld=false;discardReleaseClick=true;cancelModuleDrag();ignoreClickUntil=Date.now()+350;return;}
        if(kind==="release"){nativeLeftHeld=false;releaseClickTimer.restart();if(discardReleaseClick||dragItem||dragGroupId)ignoreClickUntil=Date.now()+300;if(dragItem)finishModuleDrag();else if(dragGroupId){const p=bubblePanels.find(p=>p&&p.groupId===dragGroupId&&p.hostWindow===dragWindow);if(p)finishGroupDrag(p);else cancelModuleDrag();}return;}
        if(token===closedNativeToken)return;
        if(kind==="wheel"||kind==="rotate"){
            if(editOpen)return;
            if(!dragItem&&!dragGroupId){const hit=hitAt(nativePressPoint.x,nativePressPoint.y);if(!hit)return;const r=root.taskRect(hit.item),screen=hit.item.hostWindow.screen,point=Qt.point(nativePressPoint.x-screen.x-r.x,nativePressPoint.y-screen.y-r.y);if(hit.group)beginGroupDrag(hit.item,point);else beginModuleDrag(hit.item,point);}
            if(kind==="wheel")adjustSelection(delta,Qt.NoModifier);else rotateDrag();return;
        }
        if(kind==="move"&&dragWindow&&(dragItem||dragGroupId)&&!opacityGesture){
            dragPoint=Qt.point(x-dragWindow.screen.x-(cfg.position==="right"?dragWindow.screen.width-dragWindow.width:0),y-dragWindow.screen.y-(cfg.position==="bottom"?dragWindow.screen.height-dragWindow.height:0));
            if(Math.hypot(dragPoint.x-dragStart.x,dragPoint.y-dragStart.y)>6){dragMoved=true;gestureMode="move";}
            if(dragMoved)findMerge(dragItem?[dragItem.modelData]:(layoutGroups.find(g=>g.id===dragGroupId)||{items:[]}).items);
        }
    }
    function editorRect(item){if(!item)return {};const r=item.mapToItem(precisePanel.contentItem,0,0,item.width,item.height);return {x:r.x,y:r.y,width:r.width,height:r.height};}
    function editorIds(){return editScope==="all"?moduleIds.concat(["clock"]):editScope==="group"?(layoutGroups.find(g=>g.id===editId)||{items:[]}).items:[editId];}
    function editorValue(field){
        if(field==="size"){const ids=editorIds();return editScope==="all"?cfg.moduleZoom:(ids.length?ids.reduce((sum,id)=>sum+individualFactor(id),0)/ids.length:1);}
        return editScope==="all"?(editorIds().length?editorIds().reduce((sum,id)=>sum+moduleAlpha(id),0)/editorIds().length:1):editScope==="group"?groupAlpha(editId):moduleAlpha(editId);
    }
    function syncEditor(){preciseSize.control.value=(editorValue("size")-0.5)/1.5;preciseOpacity.control.value=(editorValue("opacity")-0.4)/0.6;}
    function openEditor(target,group,mode,all){
        if(manipulating)return;const item=group?target:slotFor(target);if(!item||!item.hostWindow)return;
        const r=root.taskRect(item);editTarget=item;editScreen=item.hostWindow.screen;editScope=all?"all":group?"group":"module";editId=group?item.groupId:item.modelData;editMode=mode;editField=mode==="opacity"?"opacity":"size";editBefore=appearanceSnapshot();
        editPoint=Qt.point(Math.max(8,Math.min(editScreen.width-precisePanel.cardWidth-8,r.x+r.width+8)),Math.max(8,Math.min(editScreen.height-precisePanel.cardHeight-8,r.y)));
        processPopup.close();for(const calendar of calendarControllers)if(calendar)calendar.calOpen=false;
        if(notificationController)notificationController.panelOpen=false;if(powerController)powerController.closeMenu();if(volumeController)volumeController.closeAll();
        syncEditor();editOpen=true;selectionOsdTimer.stop();Qt.callLater(()=>{if(editField==="opacity")preciseOpacity.control.forceActiveFocus();else preciseSize.control.forceActiveFocus();});
    }
    function setEditorValue(field,value){
        if(!editOpen||!Number.isFinite(value))return;editField=field;
        value=Math.max(field==="opacity"?0.4:0.5,Math.min(field==="opacity"?1:2,value));const ids=editorIds();
        if(field==="size"){
            if(editScope==="all")cfg.moduleZoom=Math.round(value*100)/100;
            else cfg.moduleScale=BarLayout.resizeModules(cfg.moduleScale,ids,value-editorValue("size")).values;
        }else{
            const modules=Object.assign({},cfg.moduleOpacity),groups=Object.assign({},cfg.groupOpacity);
            for(const id of ids)modules[id]=Math.round(value*100)/100;
            if(editScope==="group")groups[editId]=value;
            else if(editScope==="all")for(const group of layoutGroups)groups[group.id]=value;
            cfg.moduleOpacity=modules;cfg.groupOpacity=groups;
        }
        save();syncEditor();
    }
    function resetEditor(){
        if(editMode!=="opacity"){
            if(editScope==="all")cfg.moduleZoom=1;
            else{const sizes=Object.assign({},cfg.moduleScale);for(const id of editorIds())delete sizes[id];cfg.moduleScale=sizes;}
        }
        if(editMode!=="size"){
            const modules=Object.assign({},cfg.moduleOpacity),groups=Object.assign({},cfg.groupOpacity);
            if(editScope==="all"){cfg.moduleOpacity=({});cfg.groupOpacity=({});}
            else{for(const id of editorIds())delete modules[id];if(editScope==="group")delete groups[editId];cfg.moduleOpacity=modules;cfg.groupOpacity=groups;}
        }
        save();syncEditor();
    }
    function closeEditor(accept){if(!editOpen)return;editOpen=false;if(!accept)restoreAppearance(editBefore);editBefore=null;editTarget=null;ignoreClickUntil=Date.now()+300;}
    Timer {interval:200;running:root.manipulating;repeat:true;onTriggered:{
        if(root.dragItem&&(!root.dragItem.visible||!root.dragItem.hostWindow))root.cancelModuleDrag();
        if(root.dragGroupId&&!root.bubblePanels.some(p=>p&&p.groupId===root.dragGroupId&&p.hostWindow===root.dragWindow&&p.visible))root.cancelModuleDrag();
        if(root.editOpen&&(!root.editTarget||!root.editTarget.visible||!root.editScreen||!Quickshell.screens.includes(root.editScreen)))root.closeEditor(false);
        if(root.dragWindow&&(!root.dragWindow.screen||!Quickshell.screens.includes(root.dragWindow.screen)))root.cancelModuleDrag();
    }}
    component PreciseRow:Item {
        id:row;required property string field;readonly property alias control:valueSlider
        function inputItem(){return entry;}
        readonly property int minimum:field==="opacity"?40:50
        readonly property int maximum:field==="opacity"?100:200
        readonly property int current:Math.round(root.editorValue(field)*100)
        width:parent.width;height:56;visible:root.editMode==="both"||root.editMode===field
        Text {text:row.field==="opacity"?LocaleState.tr("Opacité","Opacity"):root.editScope==="all"?LocaleState.tr("Zoom global","Global zoom"):LocaleState.tr("Taille","Size");font.family:Theme.fontFamily;font.pixelSize:Theme.textSizeGroup;color:Theme.text}
        Slider {id:valueSlider;y:20;width:parent.width-64;height:34;step:1/(row.maximum-row.minimum);displayFrom:row.minimum;displayTo:row.maximum
            value:(row.current-row.minimum)/(row.maximum-row.minimum)
            onMoved:value=>root.setEditorValue(row.field,(row.minimum+Math.round(value*(row.maximum-row.minimum)))/100)
            onActiveFocusChanged:if(activeFocus)root.editField=row.field
        }
        Rectangle {x:parent.width-58;y:22;width:58;height:30;radius:Theme.radius;color:Theme.bgCard;border.width:1;border.color:entry.activeFocus?Theme.accent:Theme.border
            TextInput {id:entry;anchors.fill:parent;anchors.margins:5;horizontalAlignment:TextInput.AlignHCenter;verticalAlignment:TextInput.AlignVCenter;color:Theme.text;selectionColor:Theme.accent;font.family:Theme.fontFamily;font.pixelSize:Theme.textSizeBody;selectByMouse:true
                text:row.current.toString();validator:IntValidator{bottom:row.minimum;top:row.maximum}
                onActiveFocusChanged:if(activeFocus){root.editField=row.field;selectAll();}
                onEditingFinished:if(root.editOpen&&acceptableInput)root.setEditorValue(row.field,Number(text)/100)
                onAccepted:if(acceptableInput)root.setEditorValue(row.field,Number(text)/100)
            }
        }
    }
    PanelWindow {
        id:precisePanel;visible:root.editOpen;screen:root.editScreen||Quickshell.screens[0]
        anchors{top:true;bottom:true;left:true;right:true}
        color:"transparent";exclusionMode:ExclusionMode.Ignore
        WlrLayershell.layer:WlrLayer.Overlay;WlrLayershell.namespace:"43pr-module-controls"
        WlrLayershell.keyboardFocus:root.editOpen?WlrKeyboardFocus.Exclusive:WlrKeyboardFocus.None
        readonly property real cardWidth:Math.min(screen?screen.width-16:360,360*cfg.scale)
        readonly property real cardHeight:root.editMode==="both"?230:164
        MouseArea {anchors.fill:parent;onClicked:root.closeEditor(true);onWheel:wheel=>{root.setEditorValue(root.editField,root.editorValue(root.editField)+wheel.angleDelta.y/120*0.01);wheel.accepted=true;}}
        Rectangle {x:root.editPoint.x;y:root.editPoint.y;width:precisePanel.cardWidth;height:precisePanel.cardHeight;radius:Theme.radius;color:Theme.bg;border.width:1;border.color:Theme.accent
            Keys.onPressed:event=>{if(event.key===Qt.Key_Escape){root.closeEditor(false);event.accepted=true;}else if(event.key===Qt.Key_Return||event.key===Qt.Key_Enter){root.closeEditor(true);event.accepted=true;}}
            MouseArea {anchors.fill:parent;acceptedButtons:Qt.LeftButton|Qt.RightButton;onWheel:wheel=>{root.setEditorValue(root.editField,root.editorValue(root.editField)+wheel.angleDelta.y/120*0.01);wheel.accepted=true;}}
            Column {anchors.fill:parent;anchors.margins:16;spacing:10
                Text {text:root.editScope==="all"?LocaleState.tr("TOUS LES MODULES","ALL MODULES"):root.editScope==="group"?LocaleState.tr("BULLE","BUBBLE"):LocaleState.tr("MODULE","MODULE");font.family:Theme.fontFamily;font.bold:true;font.pixelSize:Theme.textSizeSection;color:Theme.text}
                PreciseRow{id:preciseSize;field:"size"}
                PreciseRow{id:preciseOpacity;field:"opacity"}
                Row {spacing:8
                    Repeater {id:editorActions;model:[LocaleState.tr("Rétablir","Reset"),LocaleState.tr("Annuler","Cancel"),LocaleState.tr("Valider","Apply")]
                        Rectangle {required property int index;required property string modelData;width:(precisePanel.cardWidth-48)/3;height:30;radius:Theme.radius;color:Qt.alpha(Theme.accent,index===2?0.2:0.08);border.width:1;border.color:Theme.border
                            Text{anchors.centerIn:parent;text:parent.modelData;color:Theme.text;font.family:Theme.fontFamily;font.pixelSize:Theme.textSizeBody}
                            MouseArea{anchors.fill:parent;onClicked:{if(parent.index===0)root.resetEditor();else root.closeEditor(parent.index===2);}}
                        }
                    }
                }
            }
        }
    }

    function moduleIsVertical(item) {
        let ancestor=item;
        while(ancestor) { if(ancestor.moduleSlotMarker===true)return ancestor.moduleVertical; ancestor=ancestor.parent; }
        return root.vertical;
    }
    function recordDragTargets(window) {
        const panels={},modules={};
        for(const panel of bubblePanels)if(panel&&panel.hostWindow===window&&panel.visible){const p=panel.mapToItem(window.contentItem,0,0);panels[panel.groupId]={x:p.x,y:p.y,width:panel.width,height:panel.height};}
        for(const slot of moduleSlots)if(slot&&slot.hostWindow===window){const p=slot.mapToItem(window.contentItem,slot.width/2,slot.height/2);modules[slot.modelData]={x:p.x,y:p.y};}
        dragTargets=panels;dragModuleTargets=modules;
    }
    property var dragSavedAppearance:null
    function appearanceSnapshot(){return {moduleScale:cfg.moduleScale,moduleZoom:cfg.moduleZoom,moduleOpacity:cfg.moduleOpacity,groupOpacity:cfg.groupOpacity};}
    function restoreAppearance(state){if(!state)return;for(const key of Object.keys(state))cfg[key]=state[key];save();}
    function rememberDrag() {gestureMode="";discardReleaseClick=true;releaseClickTimer.stop();dragSavedAppearance=appearanceSnapshot(); dragModuleRotation=0;opacityGesture=false;dragMoved=false;dragSavedCells=cfg.groupCells;dragSavedRotations=cfg.groupRotations; }
    property double lastRotationAt:0
    function rotateDrag() {
        if(!dragWindow || opacityGesture || Date.now()-lastRotationAt<70)return;
        lastRotationAt=Date.now();gestureMode="move";
        if(dragItem){
            dragModuleRotation=(dragModuleRotation+1)%4;dragMoved=true;return;
        }
        const id=dragGroupId;
        const result=BarLayout.rotateGroup(cfg,moduleIds,id,vertical);
        if(result){cfg.groupCells=result.groupCells;cfg.groupRotations=result.groupRotations;dragMoved=true;}
    }
    function movingRect() {
        if(dragItem)return {x:dragPoint.x-moduleGrip.x,y:dragPoint.y-moduleGrip.y,width:dragItem.width,height:dragItem.height};
        const panel=bubblePanels.find(p=>p&&p.groupId===dragGroupId&&p.hostWindow===dragWindow);
        return panel?{x:dragPoint.x-panel.width*dragGripRatio.x,y:dragPoint.y-panel.height*dragGripRatio.y,width:panel.width,height:panel.height}:null;
    }
    function findMerge(sourceIds) {
        const previous=mergePanel?mergePanel.groupId:"";mergePanel=null;mergeAnchor="";previewCells=({});
        if(!cfg.autoGroup||!dragMoved)return;
        const moving=movingRect();if(!moving)return;
        const targets=[];
        for(const panel of bubblePanels){
            if(!panel||panel.hostWindow!==dragWindow||!panel.visible||panel.groupId===dragGroupId)continue;
            const slots=moduleSlots.filter(t=>t&&t.hostWindow===dragWindow&&panel.model.includes(t.modelData)&&!sourceIds.includes(t.modelData)&&t.visible);if(!slots.length)continue;
            const r=dragTargets[panel.groupId];if(r)targets.push(Object.assign({id:panel.groupId,panel:panel,slots:slots},r));
        }
        const target=BarLayout.placementTarget(moving,targets,previous);if(!target)return;
        mergePanel=target.panel;let closest=null,distance=Infinity;
        for(const slot of target.slots){const center=dragModuleTargets[slot.modelData]||slot.mapToItem(dragWindow.contentItem,slot.width/2,slot.height/2),d=Math.hypot(moving.x+moving.width/2-center.x,moving.y+moving.height/2-center.y);if(d<distance){distance=d;closest=slot;}}
        if(!closest)return;mergeAnchor=closest.modelData;
        const center=dragModuleTargets[closest.modelData]||closest.mapToItem(dragWindow.contentItem,closest.width/2,closest.height/2);
        mergeDirection=BarLayout.insertionSide(moving,{x:center.x-closest.width/2,y:center.y-closest.height/2,width:closest.width,height:closest.height});
        const result=dragGroupId?BarLayout.mergeGroups(cfg,moduleIds,dragGroupId,target.id,mergeAnchor,mergeDirection,vertical):BarLayout.regroup(cfg,moduleIds,sourceIds[0],target.id,0.5,undefined,mergeAnchor,mergeDirection,vertical);
        previewCells=(result.groupCells||{})[target.id]||{};
    }
    function persistPositions(layout,window,positions,rename) {
        const state=Object.assign({},cfg,layout),all=BarLayout.groups(state,moduleIds),frame=window.layoutFrame;
        const cells=Object.assign({},state.groupCells||{}),rotations=Object.assign({},state.groupRotations||{}),groups=[];
        for(const g of all){if(!g.items.length)continue;
            const old=Object.keys(rename||{}).find(k=>rename[k]===g.id)||g.id;
            const r=positions[old];let id=g.id;
            if(r && !id.startsWith("free-")){id="free-"+Date.now()+"-"+id;cells[id]=BarLayout.cells(state,g,vertical);rotations[id]=rotations[g.id]||0;}
            const next=Object.assign({},g,{id:id});
            if(r){next.position=vertical?r.y/Math.max(1,frame.height-r.height):r.x/Math.max(1,frame.width-r.width);if(cfg.freeLayout){next.x=r.x/Math.max(1,frame.width-r.width);next.y=r.y/Math.max(1,frame.height-r.height);}}
            if(id.startsWith("free-"))groups.push(next);
        }
        return Object.assign({},layout,{startMods:"",centerMods:"",endMods:"",moduleGroups:groups,groupCells:cells,groupRotations:rotations});
    }
    property Item dragItem: null
    property var dragWindow: null
    property point dragStart: Qt.point(0,0)
    property point dragPoint: Qt.point(0,0)
    property var mergePanel: null
    property string mergeAnchor: ""
    property string mergeDirection: "bottom"
    property var previewCells: ({})
    property string dragGroupId: ""
    property point groupOrigin: Qt.point(0,0)
    property double ignoreClickUntil: 0
    function beginModuleDrag(slot, point) {
        if(!slot.hostWindow||editOpen||dragItem||dragGroupId)return;
        for(const calendar of calendarControllers)if(calendar)calendar.calOpen=false;
        processPopup.close();if(notificationController)notificationController.panelOpen=false;
        if(powerController)powerController.closeMenu();if(volumeController)volumeController.closeAll();
        rememberDrag();dragWindow=slot.hostWindow;dragStart=slot.mapToItem(dragWindow.contentItem,point.x,point.y);
        dragPoint=dragStart;dragGrip=Qt.point(point.x,point.y);dragGripRatio=Qt.point(point.x/Math.max(1,slot.width),point.y/Math.max(1,slot.height));dragItem=slot;mergePanel=null;recordDragTargets(dragWindow);
        layoutPriority=sectionOf(slot.modelData);layoutAxis=vertical?"y":"x";
    }
    function updateModuleDrag(slot,point) {
        if(dragItem!==slot || !dragWindow || opacityGesture)return;
        dragPoint=slot.mapToItem(dragWindow.contentItem,point.x,point.y);
        if(Math.hypot(dragPoint.x-dragStart.x,dragPoint.y-dragStart.y)>6){dragMoved=true;gestureMode="move";}
        if(dragMoved)findMerge([slot.modelData]);
    }
    function cancelModuleDrag(commit) {
        if((dragItem||dragGroupId)&&nativeLeftHeld)closedNativeToken=nativeInputToken;
        if(!nativeLeftHeld)releaseClickTimer.restart();
        if(dragItem || dragGroupId)ignoreClickUntil=Date.now()+250;
        if(!commit)restoreAppearance(dragSavedAppearance);dragSavedAppearance=null;selectionOsdTimer.stop();
        if(!commit && dragSavedCells!==null){cfg.groupCells=dragSavedCells;cfg.groupRotations=dragSavedRotations;}
        dragItem=null;dragGroupId="";dragWindow=null;mergePanel=null;previewCells=({});dragMoved=false;gestureMode="";dragSavedCells=null;dragSavedRotations=null;dragTargets=({});dragModuleTargets=({});
    }
    function finishModuleDrag() {
        flushSelectionWheel();
        if(opacityGesture){cancelModuleDrag(true);return;}
        if(!dragItem || !dragWindow || !dragMoved){cancelModuleDrag();return;}
        const item=dragItem,id=item.modelData,window=dragWindow,target=mergePanel;
        const sourceGroup=layoutGroups.find(g=>g.items.includes(id)),oldId=sourceGroup?sourceGroup.id:"";
        const solved=groupPositions(window,window.layoutFrame),newId=target?target.groupId:sourceGroup&&sourceGroup.items.length===1&&oldId.startsWith("free-")?oldId:"free-"+Date.now();
        const layout=BarLayout.regroup(cfg,moduleIds,id,newId,0.5,undefined,mergeAnchor,mergeDirection,vertical);
        const result=persistPositions(layout,window,solved,target?{}:{"__module-drag":newId});
        const opacities=Object.assign({},cfg.moduleOpacity);
        if(target&&target.groupId!==sectionOf(id))opacities[id]=groupAlpha(target.groupId);
        else if(!target)opacities[id]=moduleAlpha(id);
        result.moduleOpacity=opacities;
        if(!target){result.groupRotations=Object.assign({},cfg.groupRotations);result.groupRotations[newId]=((cfg.groupRotations[oldId]||0)+dragModuleRotation)%4;}
        layoutPriority=newId;cancelModuleDrag(true);applyLayout(result);
    }
    function beginGroupDrag(panel,point) {
        if(dragItem || dragGroupId || editOpen)return;
        rememberDrag();dragWindow=panel.hostWindow;dragGroupId=panel.groupId;
        dragStart=panel.mapToItem(dragWindow.contentItem,point.x,point.y);dragPoint=dragStart;
        recordDragTargets(dragWindow);groupOrigin=panel.mapToItem(dragWindow.contentItem,0,0);dragGrip=Qt.point(point.x,point.y);dragGripRatio=Qt.point(point.x/Math.max(1,panel.width),point.y/Math.max(1,panel.height));
        layoutPriority=panel.groupId;layoutAxis=vertical?"y":"x";processPopup.close();
    }
    function updateGroupDrag(panel,point) {
        if(dragGroupId!==panel.groupId || opacityGesture)return;
        dragPoint=panel.mapToItem(dragWindow.contentItem,point.x,point.y);
        if(Math.hypot(dragPoint.x-dragStart.x,dragPoint.y-dragStart.y)>6){dragMoved=true;gestureMode="move";}
        if(dragMoved)findMerge(panel.model);
    }
    function finishGroupDrag(panel) {
        flushSelectionWheel();
        if(dragGroupId!==panel.groupId)return;
        if(opacityGesture){cancelModuleDrag(true);return;}
        if(!dragMoved){cancelModuleDrag();return;}
        const window=dragWindow,id=dragGroupId,solved=groupPositions(window,window.layoutFrame);let result,rename={};
        if(mergePanel)result=BarLayout.mergeGroups(cfg,moduleIds,id,mergePanel.groupId,mergeAnchor,mergeDirection,vertical);
        else {result=BarLayout.relocate(cfg,moduleIds,id,0.5,undefined,undefined,vertical);const moved=result.moduleGroups[result.moduleGroups.length-1];rename[id]=moved.id;}
        if(mergePanel){const values=Object.assign({},cfg.moduleOpacity);for(const module of (layoutGroups.find(g=>g.id===id)||{items:[]}).items)values[module]=groupAlpha(mergePanel.groupId);result.moduleOpacity=values;}
        else if(rename[id]&&rename[id]!==id){const values=Object.assign({},cfg.groupOpacity);values[rename[id]]=groupAlpha(id);result.groupOpacity=values;}
        result=persistPositions(result,window,solved,rename);cancelModuleDrag(true);if(result)applyLayout(result);
    }
    function layoutSolution(window,frame) {
        const rectangles=[];let guides=[];
        for(const group of layoutGroups){
            const panel=bubblePanels.find(p=>p&&p.hostWindow===window&&p.groupId===group.id);
            if(!panel || !panel.visible)continue;
            if(dragMoved&&dragItem&&dragWindow===window&&panel.model.length===1&&panel.model[0]===dragItem.modelData&&!mergePanel)continue;
            const width=panel.width,height=panel.height;
            let x=group.x!==undefined?group.x*Math.max(0,frame.width-width):vertical?(cfg.position==="right"?frame.width-width:0):group.position*(frame.width-width);
            let y=group.y!==undefined?group.y*Math.max(0,frame.height-height):vertical?group.position*(frame.height-height):(cfg.position==="bottom"?frame.height-height:0);
            if(!cfg.freeLayout){x=vertical?0:group.position*(frame.width-width);y=vertical?group.position*(frame.height-height):0;}
            if(group.id===dragGroupId && dragWindow===window && dragMoved){x=dragPoint.x-width*dragGripRatio.x-frame.x;y=dragPoint.y-height*dragGripRatio.y-frame.y;}
            if(cfg.freeLayout){const pad=BarLayout.edgePadding({x:x,y:y,width:width,height:height},frame.width,frame.height,effEdge,cfg.position);if(pad.edge==="left")x=effEdge;else if(pad.edge==="right")x=frame.width-width-effEdge;else if(pad.edge==="top")y=effEdge;else if(pad.edge==="bottom")y=frame.height-height-effEdge;}
            rectangles.push({id:group.id,x:x,y:y,width:width,height:height,order:vertical?(group.y===undefined?group.position:group.y):(group.x===undefined?group.position:group.x)});
        }
        if(dragItem && dragWindow===window && dragMoved && !mergePanel)rectangles.push({id:"__module-drag",x:dragPoint.x-moduleGrip.x-frame.x-root.bubblePadding,y:dragPoint.y-moduleGrip.y-frame.y-root.bubblePadding,width:dragItem.width+2*root.bubblePadding,height:dragItem.height+2*root.bubblePadding});
        const moving=rectangles.find(r=>r.id===(dragGroupId||"__module-drag"));
        if(moving && cfg.freeLayout && dragMoved && !mergePanel){const snap=BarLayout.snap(moving,rectangles.filter(r=>r!==moving),frame.width,frame.height,10);moving.x=snap.x;moving.y=snap.y;guides=snap.guides;}
        let axis=layoutAxis;
        if(moving && cfg.freeLayout && vertical && moving.x<root.panelThick+10)axis="x";
        const solution=BarLayout.solve(rectangles,frame.width,frame.height,mergePanel?mergePanel.groupId:moving?moving.id:layoutPriority,axis,2,mergePanel&&dragGroupId?[dragGroupId]:[],(!dragItem&&!dragGroupId)?(vertical?"y":"x"):null);
        solution.guides=guides;return solution;
    }
    function groupPositions(window,frame) {return layoutSolution(window,frame).positions;}

    // ───────────────────────── State / IPC ─────────────────────────
    property bool barVisible: true
    property bool barLive: true

    function rebuildBar() {
        if(editOpen)closeEditor(false);cancelModuleDrag();
        processPopup.close();
        if (notificationController) notificationController.panelOpen = false;
        // Retain the popup's parent surface until its close animation finishes.
        // Destroying a layer-shell parent with a fading popup can disconnect Wayland.
        barRetireTimer.restart();
    }
    Timer {
        id: barRetireTimer
        interval: Math.max(300, Theme.animMed + 60)
        onTriggered: { root.barLive = false; rebuildTimer.restart(); }
    }
    Timer { id: rebuildTimer; interval: 80; onTriggered: root.barLive = true }
    Connections {
        target: cfg
        function onPositionChanged() { root.rebuildBar(); }
        function onStyleChanged() { root.rebuildBar(); }
        function onFreeLayoutChanged() { root.rebuildBar(); }
    }

    // Bar settings now live on the BarPage of the settings app.
    // Adjust the IPC call below if your settings app names the page differently.
    function openSettings() { run("qs ipc call settings bar"); }

    IpcHandler {
        target: "bar"
        function setZoomPercent(percent:int):void{cfg.moduleZoom=Math.max(50,Math.min(200,percent))/100;root.save();}
        function resetSizes():void {cfg.moduleScale=({});cfg.moduleZoom=1;root.save();}
        function resetOpacities():void {cfg.groupOpacity=({});cfg.moduleOpacity=({});root.save();}
        function layoutState(): string {
            return JSON.stringify({gestureMode:root.gestureMode,moduleRotation:root.dragModuleRotation,moved:root.dragMoved,groupRotations:cfg.groupRotations,appDragging:root.appDragItem!==null,freeLayout:cfg.freeLayout,reserveSpace:cfg.reserveSpace,nativeReservation:root.nativeReservation,nativeControlBridge:root.nativeControlBridge,nativeInputBridge:root.nativeInputBridge,manipulating:root.manipulating,processPopupOpen:processPopup.opened,input:{discardClick:root.discardReleaseClick,kind:root.lastNativeKind,delta:root.lastNativeDelta,left:root.nativeLeftHeld,token:root.nativeInputToken},editor:{sizeInput:root.editorRect(preciseSize.inputItem()),opacityInput:root.editorRect(preciseOpacity.inputItem()),buttons:[0,1,2].map(i=>root.editorRect(editorActions.itemAt(i))),x:root.editPoint.x,y:root.editPoint.y,width:precisePanel.cardWidth,height:precisePanel.cardHeight,open:root.editOpen,scope:root.editScope,id:root.editId,mode:root.editMode,size:root.editorValue("size"),opacity:root.editorValue("opacity")},zoom:cfg.moduleZoom,groupDrag:root.dragGroupId,mergeTarget:root.mergePanel?root.mergePanel.groupId:"",locale:LocaleState.language,date:LocaleState.locale.toString(new Date(),"dddd, d MMMM yyyy"),groups:root.layoutGroups,panels:root.bubblePanels.filter(p=>p&&p.hostWindow&&p.visible).map(p=>({id:p.groupId,selected:root.dragGroupId===p.groupId,border:p.border.width,opacity:root.groupAlpha(p.groupId),geometry:root.taskRect(p),items:p.model})),calendars:root.calendarControllers.filter(c => c && c.clockTarget).map(c => ({open:c.calOpen,geometry:root.taskRect(c.clockTarget)})),dragging:root.dragItem ? root.dragItem.modelData : "",
                modules:root.moduleSlots.filter(s => s && s.hostWindow).map(s => ({id:s.modelData,holding:s.holding,size:root.moduleFactor(s.modelData),pressed:s.item&&s.item.debugPressed!==undefined?s.item.debugPressed:false,hovered:s.item&&s.item.hovered!==undefined?s.item.hovered:false,itemSize:s.item?{width:s.item.width,height:s.item.height}:null,opacity:root.moduleAlpha(s.modelData),vertical:s.moduleVertical,geometry:root.taskRect(s)}))});
        }
        function nativeAppDrag(address:string,token:string):void {
            if(Number(token)<=root.appDragClosedToken)return;
            const item=root.taskButtons.find(t=>t&&t.isMinimized&&t.hyprHandle&&("0x"+t.hyprHandle.address.replace(/^0x/,""))===address);
            if(item){root.beginAppDrag(item,Qt.point(item.width/2,item.height/2));root.appDragNative=true;}
        }
        function endNativeAppDrag(address:string,token:string):void {
            if(Number(token)<=root.appDragClosedToken)return;
            root.appDragClosedToken=Math.max(root.appDragClosedToken,Number(token));
            root.appDragNative=false;
            if(!root.appDragItem&&!taskRestore.running){
                const item=root.taskButtons.find(t=>t&&t.isMinimized&&t.hyprHandle&&("0x"+t.hyprHandle.address.replace(/^0x/,""))===address);
                if(item)root.appDragItem=item;
            }
            if(root.appDragItem)root.finishAppDrag();
        }
        function resetLayout(): void { cfg.freeLayout=false; cfg.groupCells=({}); cfg.moduleGroups=[]; cfg.startMods=root.defaults.startMods; cfg.centerMods=root.defaults.centerMods; cfg.endMods=root.defaults.endMods; root.save(); }
        function statsState(): string { return JSON.stringify({gpu:GpuStats.sample,buttons:root.statButtons.map(s => ({kind:s.modelData,geometry:root.taskRect(s)}))}); }
        function tasksState(): string {
            const ready = root.nativeToplevels.length;
            return JSON.stringify({collapsed:cfg.tasksCollapsed, iconSize:cfg.taskIconSize,
                maxVisible:cfg.taskMaxVisible, controls:root.taskControls.map(t => root.taskRect(t)),
                strips:root.taskStrips.filter(s => s && s.hostWindow).map(s => ({visible:s.visible,geometry:root.taskRect(s),contentX:s.contentX,contentY:s.contentY,contentWidth:s.contentWidth,contentHeight:s.contentHeight})),
                buttons:root.taskButtons.map(t => ({title:t.modelData.title,
                    address:t.hyprHandle ? "0x" + t.hyprHandle.address.replace(/^0x/, "") : "",
                    minimized:t.isMinimized, geometry:root.taskRect(t)}))});
        }
        function setTasksCollapsed(value: bool): void { cfg.tasksCollapsed = value; root.save(); }
        function setTaskIconSize(value: int): void { cfg.taskIconSize = Math.max(12, Math.min(32, value)); root.save(); }
        function setTaskMaxVisible(value: int): void { cfg.taskMaxVisible = Math.max(1, Math.min(12, value)); root.save(); }
        function toggle(): void { root.barVisible = !root.barVisible; }
        function show(): void { root.barVisible = true; }
        function hide(): void { root.barVisible = false; }
        function setPosition(pos: string): void {
            if (root.positions.indexOf(pos) >= 0) { cfg.position = pos; root.save(); }
        }
        function cyclePosition(): void {
            cfg.position = root.positions[(root.positions.indexOf(cfg.position) + 1) % 4];
            root.save();
        }
        function setStyle(st: string): void {
            if (root.styles.indexOf(st) >= 0) { cfg.style = st; root.save(); }
        }
        function setStatsMode(mode: string): void {
            if (root.statsModes.indexOf(mode) >= 0) { cfg.statsMode = mode; root.save(); }
        }
        function customize(): void { root.openSettings(); }
        function moveModule(id: string, section: string): void {
            if (root.valid(id) && root.sections.indexOf(section) >= 0) { root.moveTo(id, section); root.save(); }
        }
        function shiftModule(id: string, delta: int): void {
            if (root.valid(id)) { root.shiftBy(id, delta); root.save(); }
        }
    }

    // ───────────────────────── System stats ─────────────────────────
    property int cpuUsage: 0
    property int memPercent: 0
    property real memUsedG: 0
    property real memTotalG: 0
    property string netState: "disconnected"
    property real _prevTotal: 0
    property real _prevIdle: 0

    readonly property string netGlyph: netState === "wifi" ? "\uDB81\uDDA9"
                                     : netState === "ethernet" ? "\uDB80\uDE00" : "\uDB81\uDDAA"
    readonly property string netTip: netState === "wifi" ? "Wi-Fi connected"
                                   : netState === "ethernet" ? "Ethernet connected" : "Disconnected"

    FileView {
        id: statFile
        path: "/proc/stat"
        onLoaded: {
            const f = text().split("\n")[0].trim().split(/\s+/).slice(1, 9).map(Number);
            const total = f.reduce((a, b) => a + b, 0);
            const idle = f[3] + f[4];
            const dT = total - root._prevTotal, dI = idle - root._prevIdle;
            if (root._prevTotal > 0 && dT > 0) root.cpuUsage = Math.round(100 * (dT - dI) / dT);
            root._prevTotal = total;
            root._prevIdle = idle;
        }
    }

    FileView {
        id: memFile
        path: "/proc/meminfo"
        onLoaded: {
            const t = text();
            const kb = k => Number(t.match(new RegExp(k + ":\\s+(\\d+)"))[1]);
            const total = kb("MemTotal"), used = total - kb("MemAvailable");
            root.memPercent = Math.round(100 * used / total);
            root.memUsedG = used / 1048576;
            root.memTotalG = total / 1048576;
        }
    }

    // Notification count: the notifications panel persists its history here
    property int notifCount: 0
    readonly property string notifTip: notifCount > 0 ? "Notifications: " + notifCount : "No notifications"

    FileView {
        id: notifFile
        path: Quickshell.env("HOME") + "/.cache/43pr/notifications.json"
        printErrors: false
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try { root.notifCount = JSON.parse(text()).length; }
            catch (e) { root.notifCount = 0; }
        }
        onLoadFailed: root.notifCount = 0
    }

    Process {
        id: netProc
        command: ["nmcli", "-t", "-f", "TYPE,STATE", "device"]
        stdout: StdioCollector {
            onStreamFinished: {
                let st = "disconnected";
                for (const l of text.split("\n")) {
                    if (l === "ethernet:connected") { st = "ethernet"; break; }
                    if (l === "wifi:connected") st = "wifi";
                }
                if (st !== root.netState) root.netState = st;
            }
        }
    }

    Timer {
        interval: 2000; running: root.barVisible; repeat: true; triggeredOnStart: true
        onTriggered: { statFile.reload(); memFile.reload(); }
    }
    Timer {
        interval: 10000; running: root.barVisible; repeat: true; triggeredOnStart: true
        onTriggered: if (!netProc.running) netProc.running = true
    }

    PwObjectTracker { objects: [Pipewire.defaultAudioSink] }

    Process { id: runner }
    function run(cmd) { runner.command = ["sh", "-c", cmd]; runner.running = true; }

    function mediaAct(kind) {
        const p = Marquee.player;
        if (!p) return;
        if (kind === "toggle") p.togglePlaying();
        else if (kind === "next") p.next();
        else p.previous();
    }

    readonly property string wsHints: "Left click: Switch to workspace\nRight click: Quick actions\nScroll: Previous / next workspace"

    // ───────────────────────── Interaction model ─────────────────────────
    // Convention used by every bar module:
    //   Left click   → primary action
    //   Right click  → secondary action (falls back to "Bar settings" if the module has none)
    //   Middle click → tertiary action (optional)
    //   Scroll       → adjust a value (optional)
    // Hints declared on a module are shown automatically in its tooltip.
    // States: hover · pressed · active (accent) · warning (danger) · disabled.

    component Lane: GridLayout {
        id:genericLane
        property int gap: 0
        property bool vertical: root.moduleIsVertical(genericLane)
        flow: vertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
        rowSpacing: gap
        columnSpacing: gap
    }

    // Hover tooltip, anchored next to `target` on the side facing away from the bar edge.
    component Tip: Item {
        id: tp
        property Item target: parent
        property bool hot: false
        property string title: ""
        property string hints: ""
        property bool shown: false
        property bool suppressed: false   // set on click; cleared when the pointer leaves
        readonly property bool usable: cfg.tooltips && !suppressed && (title !== "" || hints !== "")

        width: 0
        height: 0
        onHotChanged: if (!hot) { shown = false; suppressed = false; }

        Timer {
            interval: cfg.tipDelay
            running: tp.hot && tp.usable && !tp.shown
            onTriggered: tp.shown = true
        }

        LazyLoader {
            active: tp.shown && tp.usable

            PopupWindow {
                readonly property var win: tp.target.QsWindow.window
                readonly property point p: win && tp.target ? win.contentItem.mapFromItem(tp.target, 0, 0) : Qt.point(0, 0)

                anchor.window: win
                anchor.adjustment: PopupAdjustment.Slide
                anchor.rect.x: root.vertical
                    ? (cfg.position === "left" ? p.x + tp.target.width + 6 : p.x - implicitWidth - 6)
                    : p.x + (tp.target.width - implicitWidth) / 2
                anchor.rect.y: root.vertical
                    ? p.y + (tp.target.height - implicitHeight) / 2
                    : (cfg.position === "top" ? p.y + tp.target.height + 6 : p.y - implicitHeight - 6)
                implicitWidth: tcol.implicitWidth + 20
                implicitHeight: tcol.implicitHeight + 14
                color: "transparent"
                visible: true

                Rectangle {
                    anchors.fill: parent
                    radius: Math.min(cfg.radius, height / 2)
                    color: root.bgColor
                    border.width: 1
                    border.color: root.borderColor

                    Column {
                        id: tcol
                        anchors.centerIn: parent
                        spacing: 3
                        Text {
                            visible: tp.title !== ""
                            text: tp.title
                            color: Theme.text
                            font.family: Theme.iconFont
                            font.pixelSize: 12
                            font.bold: true
                        }
                        Text {
                            visible: tp.hints !== ""
                            text: tp.hints
                            color: Theme.textDim
                            font.family: Theme.iconFont
                            font.pixelSize: 11
                        }
                    }
                }
            }
        }
    }

    // Behaviour + visual states shared by every interactive bar element.
    component Interactive: Item {
        readonly property var hostWindow: QsWindow.window
        id: it
        property string tip: ""
        property string primaryHint: ""
        property string secondaryHint: ""      // empty → right click opens bar settings
        property string tertiaryHint: ""
        property string scrollHint: ""
        property string disabledReason: ""
        property bool active: false            // accent tint (e.g. calendar open)
        property bool warning: false           // danger tint (e.g. low battery, muted)
        property bool disabled: false          // dimmed, ignores input, tooltip explains why
        property bool interactive: true        // false → informational only (no hover tint / pointer)
        property bool restoreDragEligible: false
        property bool noTip: false             // never show a tooltip for this element
        signal primary()
        signal secondary()
        signal tertiary()
        signal scrolled(real delta)

        readonly property bool debugPressed:ma.pressed
        readonly property bool hovered: ma.containsMouse && !disabled
        readonly property string hintText: {
            if (disabled) return disabledReason;
            if (!cfg.tooltipHints) return "";
            const l = [];
            if (primaryHint !== "") l.push("Left click: " + primaryHint);
            l.push("Right click: " + (secondaryHint !== "" ? secondaryHint : "Quick actions"));
            if (tertiaryHint !== "") l.push("Middle click: " + tertiaryHint);
            if (scrollHint !== "") l.push("Scroll: " + scrollHint);
            return l.join("\n");
        }

        function secondaryAction() {
            if (secondaryHint !== "") secondary();
            else root.openSettings();
        }

        opacity: disabled ? 0.4 : 1
        Behavior on opacity { NumberAnimation { duration: 120 } }

        // state layer: pressed > active > warning, with a hover overlay
        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: Theme.radius
            color: ma.pressed && it.interactive && !it.disabled ? Qt.alpha(Theme.accent, 0.35)
                 : it.active ? Qt.alpha(Theme.accent, 0.22)
                 : it.warning ? Qt.alpha(Theme.danger, 0.16)
                 : Qt.alpha(Theme.text, 0)
            Behavior on color { ColorAnimation { duration: 100 } }

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: it.hovered && it.interactive ? Qt.alpha(Theme.text, 0.1) : Qt.alpha(Theme.text, 0)
                Behavior on color { ColorAnimation { duration: 100 } }
            }
        }

        MouseArea {
            id: ma
            pressAndHoldInterval: 450
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
            cursorShape: it.interactive && !it.disabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onPressed: mouse => { if(root.manipulating)return;if(mouse.button===Qt.RightButton&&(mouse.modifiers&Qt.ControlModifier)){const slot=ma.slotParent();if(slot)root.openEditor(slot,false,"both");return;} tipper.suppressed = true; tipper.shown = false;
                if(mouse.button===Qt.LeftButton && (mouse.modifiers & Qt.MetaModifier) && it.restoreDragEligible){preventStealing=true;root.beginAppDrag(it,Qt.point(mouse.x,mouse.y));}
            }
            function slotParent() { let p=it; while(p) { if (p.moduleSlotMarker === true) return p; p=p.parent; } return null; }
            onPressAndHold: mouse => {
                if (mouse.button !== Qt.LeftButton || it.disabled || root.appDragItem) return;
                const slot=slotParent(); if(slot) { preventStealing=true; root.beginModuleDrag(slot,ma.mapToItem(slot,mouse.x,mouse.y)); mouse.accepted=true; }
            }
            onPositionChanged: mouse => { if(root.appDragItem===it){root.updateAppDrag(it,Qt.point(mouse.x,mouse.y));return;} const slot=slotParent(); if (slot && root.dragItem === slot) root.updateModuleDrag(slot,ma.mapToItem(slot,mouse.x,mouse.y)); }
            onReleased: mouse => { if(mouse.button!==Qt.LeftButton)return; if(root.appDragItem===it&&!root.appDragNative)root.finishAppDrag(); if (root.dragItem === slotParent()) root.finishModuleDrag(); preventStealing=false; }
            onCanceled: { if(root.appDragItem===it&&!root.appDragNative)root.appDragItem=null; if (root.dragItem === slotParent()&&!root.nativeLeftHeld) root.cancelModuleDrag(); preventStealing=false; }
            onClicked: mouse => {
                if (it.disabled || root.discardReleaseClick || root.manipulating || root.appDragItem || Date.now() < root.ignoreClickUntil) return;
                if (mouse.button === Qt.LeftButton) it.primary();
                else if (mouse.button === Qt.MiddleButton) it.tertiary();
                else if(!(mouse.modifiers&Qt.ControlModifier))it.secondaryAction();
            }
            onWheel: wheel => {
                if(root.manipulating){if(!root.nativeInputBridge&&!root.editOpen)root.queueSelectionWheel(wheel.angleDelta.y,wheel.modifiers);wheel.accepted=true;return;}
                if (pressedButtons & Qt.LeftButton) {
                    const slot=slotParent();if(slot&&!root.dragItem&&!root.dragGroupId)root.beginModuleDrag(slot,Qt.point(slot.width/2,slot.height/2));
                    wheel.accepted=root.queueSelectionWheel(wheel.angleDelta.y,wheel.modifiers);return;
                }
                wheel.accepted = it.scrollHint !== "" && !it.disabled;
                if (wheel.accepted) it.scrolled(wheel.angleDelta.y);
            }
        }

        Tip {
            id: tipper
            target: it
            hot: !root.manipulating && !it.noTip && ma.containsMouse
            title: it.tip
            hints: it.hintText
        }
    }

    // Icon / text module built on Interactive
    component Mod: Interactive {
        id: mod
        readonly property bool moduleVertical: root.moduleIsVertical(mod)
        property string mid: ""          // set by Slot; used by generic icon modules
        property string text: ""
        property string vtext: text
        property string glyph: ""
        property string vglyph: glyph
        property real glyphSize: 16
        property real baseSize: 11
        property color color: Theme.text
        property bool bold: false
        property real yOffset: 0
        property real glyphScaleY: 1.0
        property int spacing: root.sizeIconGap
        property int padX: cfg.modPad

        readonly property color fg: warning ? Theme.danger : active ? Theme.accent : color
        readonly property string shown: mod.moduleVertical ? vtext : text
        readonly property bool textIsIcon: (shown.length===1&&(shown.charCodeAt(0)>=0xE000||shown==="⏻"))||(shown.length===2&&shown.charCodeAt(0)>=0xD800&&shown.charCodeAt(0)<=0xDBFF&&shown.charCodeAt(1)>=0xDC00&&shown.charCodeAt(1)<=0xDFFF)
        readonly property string shownGlyph: mod.moduleVertical ? vglyph : glyph

        readonly property bool iconOnly:mod.textIsIcon||(mod.shownGlyph!==""&&mod.shown==="")
        Layout.alignment: Qt.AlignCenter
        implicitWidth: mod.moduleVertical ? root.panelThick : (mod.iconOnly?soloIcon.implicitWidth:content.implicitWidth) + padX
        implicitHeight: mod.moduleVertical ? (mod.iconOnly ? Math.max(root.panelThick, root.sz.icon + 8) : Math.max(20, content.implicitHeight + 8))
                                      : Math.max(root.panelThick - 2, mod.iconOnly ? soloIcon.implicitHeight : content.implicitHeight)


        // Centre the painted glyph, not its font advance or line box. A shared
        // square normalises reference size without stretching the aspect ratio.
        // Fourfold metric sampling limits rounding; distance-field rendering stays smooth under module scaling.
        Item {
            id:soloIcon;visible:mod.iconOnly;anchors.centerIn:parent
            implicitWidth:root.sz.icon;implicitHeight:root.sz.icon
            width:implicitWidth;height:implicitHeight
            TextMetrics {id:iconInk;font:iconText.font;text:iconText.text;renderType:Text.QtRendering}
            Text {
                id:iconText
                text:mod.shownGlyph!==""?mod.shownGlyph:mod.shown
                color:mod.fg;font.family:Theme.iconFont
                font.pixelSize:root.sz.icon*4;renderType:Text.QtRendering
                readonly property real fit:soloIcon.width/Math.max(1,iconInk.tightBoundingRect.width,iconInk.tightBoundingRect.height)
                x:soloIcon.width/2-(iconInk.tightBoundingRect.x+iconInk.tightBoundingRect.width/2)*fit
                y:soloIcon.height/2-(baselineOffset+iconInk.tightBoundingRect.y+iconInk.tightBoundingRect.height/2)*fit
                scale:fit;transformOrigin:Item.TopLeft
            }
        }
        GridLayout {
            id: content
            visible:!mod.iconOnly
            anchors.centerIn: parent
            anchors.verticalCenterOffset: mod.moduleVertical ? 0 : mod.yOffset
            flow: mod.moduleVertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
            rowSpacing: 2
            columnSpacing: mod.spacing

            Text {
                id:glyphText
                visible:mod.shownGlyph!==""||mod.textIsIcon
                Layout.alignment: Qt.AlignCenter
                horizontalAlignment:Text.AlignHCenter
                text:mod.shownGlyph!==""?mod.shownGlyph:mod.textIsIcon?mod.shown:""
                color: mod.fg
                font.family:Theme.iconFont
                font.pixelSize:mod.shownGlyph!==""?mod.glyphSize:mod.baseSize
                renderType:Text.NativeRendering
                transform:Scale {yScale:mod.glyphScaleY;origin.y:height/2}

            }
            Text {
                id:bodyText
                visible:mod.shown!==""&&!mod.textIsIcon
                Layout.alignment: Qt.AlignCenter
                horizontalAlignment:Text.AlignHCenter
                text: mod.shown
                color: mod.fg
                font.family:Theme.iconFont
                font.bold: mod.bold
                font.pixelSize: mod.baseSize
                renderType:Text.NativeRendering

            }
        }
    }

    component Slot: Item {
        id: moduleSlot
        readonly property var hostWindow: QsWindow.window
        Component.onCompleted: root.moduleSlots = root.moduleSlots.filter(s => s && s.objectName !== undefined).concat([moduleSlot])
        Component.onDestruction: { root.moduleSlots = root.moduleSlots.filter(s => s !== moduleSlot); if (root.dragItem === moduleSlot) root.cancelModuleDrag();if(root.editTarget===moduleSlot)root.closeEditor(false); }
        Behavior on x {enabled:root.dragItem!==null;NumberAnimation{duration:100}}
        Behavior on y {enabled:root.dragItem!==null;NumberAnimation{duration:100}}
        z: root.dragItem === moduleSlot ? 1000 : 0
        opacity: root.moduleAlpha(modelData)
        readonly property bool holding: root.dragItem === moduleSlot
        readonly property bool moduleSlotMarker: true
        property var owningPanel: null
        readonly property bool moduleVertical: root.vertical !== (!!(((cfg.groupRotations[(owningPanel?owningPanel.groupId:root.sectionOf(modelData))]||0)+(root.dragItem===moduleSlot?root.dragModuleRotation:0))%2))
        readonly property real sizeFactor:root.moduleFactor(modelData)
        readonly property alias item:moduleLoader.item
        implicitWidth:moduleLoader.implicitWidth*sizeFactor
        implicitHeight:moduleLoader.implicitHeight*sizeFactor
        width: implicitWidth; height: implicitHeight
        Rectangle {
            anchors.fill: parent; anchors.margins: -1; radius: Theme.radius
            color: "transparent"; border.width: 2; border.color: Theme.accent
            visible: root.dragItem === moduleSlot
        }
        required property string modelData
        property Component clockComp: null
        visible: root.modVisible(modelData)
        Layout.alignment: Qt.AlignCenter
        Loader {
            id:moduleLoader;scale:moduleSlot.sizeFactor;transformOrigin:Item.TopLeft
            width:implicitWidth;height:implicitHeight
            sourceComponent: moduleSlot.modelData === "clock" ? moduleSlot.clockComp : (moduleSlot.modelData.startsWith("minigroup-") ? tasksC : (root.comps[moduleSlot.modelData] ?? root.comps.icon))
            onLoaded:if(item.mid!==undefined)item.mid=moduleSlot.modelData
        }
    }

    // One of the three bar sections: a rounded panel holding a Lane of Slots
    component Panel: Rectangle {
        id: panel
        readonly property var hostWindow: QsWindow.window
        property string groupId: ""
        property var model: []
        property Component clockComp: null
        readonly property bool rotatedVertical: root.vertical !== (!!((cfg.groupRotations[groupId]||0)%2))
        property Region inputRegion: Region { x:panel.x+panel.parent.x;y:panel.y+panel.parent.y;width:panel.width;height:panel.height }
        readonly property var cellMap: root.mergePanel===panel?root.previewCells:BarLayout.cells(cfg,{id:groupId,items:model},root.vertical)
        readonly property var baseMetrics: {
            const entries=[];
            for(const slot of root.moduleSlots){if(!slot || slot.hostWindow!==hostWindow || !root.modVisible(slot.modelData) || !model.includes(slot.modelData))continue;
                const task=slot.item&&slot.item.requestedLength!==undefined;
                entries.push({id:slot.modelData,width:task?slot.item.baseWidth*slot.sizeFactor:slot.implicitWidth,height:task?slot.item.baseHeight*slot.sizeFactor:slot.implicitHeight});}
            return BarLayout.measure(BarLayout.cells(cfg,{id:groupId,items:model},root.vertical),entries,0);
        }
        readonly property var metrics: {
            const entries=[];
            for(const slot of root.moduleSlots){if(!slot || slot.hostWindow!==hostWindow || !root.modVisible(slot.modelData))continue;
                const own=model.includes(slot.modelData),ghost=root.mergePanel===panel&&root.previewCells[slot.modelData];
                if((own || ghost) && !(root.dragMoved&&root.dragItem===slot&&root.mergePanel!==panel&&model.length>1))entries.push({id:slot.modelData,width:slot.implicitWidth,height:slot.implicitHeight});}
            return BarLayout.measure(cellMap,entries,0);
        }
        Component.onCompleted: root.bubblePanels=root.bubblePanels.filter(p=>p&&p.objectName!==undefined).concat([panel])
        Component.onDestruction: {root.bubblePanels=root.bubblePanels.filter(p=>p!==panel);if(root.dragGroupId===panel.groupId&&root.dragWindow===panel.hostWindow)root.cancelModuleDrag();if(root.editTarget===panel)root.closeEditor(false);}
        visible: metrics.width>0 && metrics.height>0
        width: Math.max(rotatedVertical?root.panelThick:0,metrics.width+2*root.bubblePadding)
        height: Math.max(!rotatedVertical?root.panelThick:0,metrics.height+2*root.bubblePadding)
        opacity:root.dragMoved&&root.dragItem&&model.length===1&&model[0]===root.dragItem.modelData?0:1
        radius: root.barRadius
        color: root.joined&&!cfg.freeLayout?"transparent":Qt.alpha(root.bgColor,root.bgColor.a*root.groupAlpha(groupId))
        border.width: root.dragGroupId===groupId||root.mergePanel===panel?2:cfg.border&&!root.joined?1:0
        border.color: root.dragGroupId===groupId||root.mergePanel===panel?Theme.accent:root.borderColor
        Behavior on x {enabled:(root.dragItem!==null||root.dragGroupId!=="")&&root.dragGroupId!==groupId;NumberAnimation{duration:100}}
        Behavior on y {enabled:(root.dragItem!==null||root.dragGroupId!=="")&&root.dragGroupId!==groupId;NumberAnimation{duration:100}}
        MouseArea {
            id:bubbleDrag;anchors.fill:parent;acceptedButtons:Qt.LeftButton|Qt.RightButton;pressAndHoldInterval:300

            property point pressedAt:Qt.point(0,0)
            onPressed:mouse=>{if(root.manipulating)return;if(mouse.button===Qt.RightButton){if(mouse.modifiers&Qt.ControlModifier)root.openEditor(panel,true,"both");else root.openSettings();return;}pressedAt=Qt.point(mouse.x,mouse.y);}
            onPressAndHold:mouse=>{if(mouse.button===Qt.LeftButton)root.beginGroupDrag(panel,Qt.point(mouse.x,mouse.y));}
            onPositionChanged:mouse=>{if(!(pressedButtons&Qt.LeftButton))return;if(!root.dragGroupId&&Math.hypot(mouse.x-pressedAt.x,mouse.y-pressedAt.y)>6)root.beginGroupDrag(panel,pressedAt);root.updateGroupDrag(panel,Qt.point(mouse.x,mouse.y));}
            onReleased:mouse=>{if(mouse.button===Qt.LeftButton)root.finishGroupDrag(panel);}
            onCanceled:if(!root.nativeLeftHeld)root.cancelModuleDrag()
            onWheel:wheel=>{if(root.editOpen){wheel.accepted=true;return;}if(root.dragItem||root.dragGroupId){if(!root.nativeInputBridge)root.queueSelectionWheel(wheel.angleDelta.y,wheel.modifiers);wheel.accepted=true;return;}if(pressedButtons&Qt.LeftButton){if(!root.dragGroupId&&!root.dragItem)root.beginGroupDrag(panel,pressedAt);wheel.accepted=root.queueSelectionWheel(wheel.angleDelta.y,wheel.modifiers);}else wheel.accepted=false;}
        }
        Item {
            id:laneItem;anchors.centerIn:parent;width:panel.metrics.width;height:panel.metrics.height
            Repeater {
                model:panel.model
                delegate:Slot {
                    clockComp:panel.clockComp;owningPanel:panel
                    readonly property var position:panel.metrics.positions[modelData]||{x:0,y:0}
                    x:position.x;y:position.y
                }
            }
        }
    }

    // ───────────────────────── Bar helper components ─────────────────────────
    component Rule: Rectangle {
        height: 1
        color: Qt.alpha(Theme.text, 0.12)
    }

    component Arrow: Item {
        id: ar
        property string glyph: ""
        signal clicked()
        width: 28
        height: 26
        Text {
            anchors.centerIn: parent
            text: ar.glyph
            color: arMa.containsMouse ? Theme.accent : Theme.text
            font.family: Theme.iconFont
            font.pixelSize: root.sz.calArrow
        }
        MouseArea {
            id: arMa
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked:if(!root.manipulating&&!root.discardReleaseClick)ar.clicked()
        }
    }

    // Scrolling now-playing text. Rotated 90° by its parent on vertical bars.
    component MarqueeStrip: Item {
        id:marqueeStrip
        readonly property bool moduleVertical:root.moduleIsVertical(marqueeStrip)
        clip: true
        Row {
            x: Marquee.animating ? Marquee.x : 0
            spacing: Marquee.gap
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: marqueeStrip.moduleVertical ? 0 : root.iconYOffset

            Repeater {
                model: Marquee.animating ? 2 : 1
                delegate: Text {
                    required property int index
                    text: Marquee.text
                    color: Theme.text
                    font.family: Theme.iconFont
                    font.pixelSize: root.sz.marquee
                    renderType: marqueeStrip.moduleVertical ? Text.QtRendering : Text.NativeRendering
                    // first copy is width-limited/elided when not scrolling
                    width: index === 0 ? (Marquee.animating ? Marquee.textW
                                                            : Math.min(Marquee.textW, Marquee.maxW))
                                       : implicitWidth
                    elide: index === 0 && !Marquee.animating ? Text.ElideRight : Text.ElideNone
                }
            }
        }
    }

    // ───────────────────────── Module components ─────────────────────────
    // Generic icon button: net / notif / wall / settings / power (driven by moduleDefs)
    Component {
        id: iconC
        Mod {
            id: ic
            property var def: root.defMap[mid] ?? ({})
            readonly property bool isNet: mid === "net"
            readonly property bool isNotif: mid === "notif"
            onIsNotifChanged: {
                if (!root.notificationController) return;
                if (isNotif) root.notificationController.registerBarButton(ic);
                else root.notificationController.unregisterBarButton(ic);
            }
            onMidChanged: {
                if(mid === "power" && root.powerController)root.powerController.registerBarButton(ic);
                if(mid === "brightness" && root.volumeController)root.volumeController.registerBrightnessButton(ic);
            }
            Component.onCompleted: {
                if (isNotif && root.notificationController) root.notificationController.registerBarButton(ic);
                if (mid === "power" && root.powerController) root.powerController.registerBarButton(ic);
                if (mid === "brightness" && root.volumeController) root.volumeController.registerBrightnessButton(ic);
            }
            Component.onDestruction: {
                if (root.notificationController) root.notificationController.unregisterBarButton(ic);
                if (root.powerController) root.powerController.unregisterBarButton(ic);
                if(root.volumeController)root.volumeController.unregisterBrightnessButton(ic);
            }
            baseSize: root.sz.icon
            yOffset: root.iconYOffset
            text: isNet ? root.netGlyph : (def.g ?? "")
            tip: isNet ? root.netTip : mid === "notif" ? root.notifTip : (def.tip ?? "")
            primaryHint: def.hint ?? ""
            warning: isNet && root.netState === "disconnected"
            onPrimary: {
                if (isNotif && root.notificationController) root.notificationController.toggleFromBar(ic);
                else if (mid === "power" && root.powerController) root.powerController.toggleFromBar(ic);
                else if (mid === "brightness" && root.volumeController) root.volumeController.showBrightness(ic);
                else if (def.cmd) root.run(def.cmd);
            }

            // Notification count badge (top-right of the icon)
            Rectangle {
                visible: ic.isNotif && root.notifCount > 0
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                anchors.horizontalCenterOffset: Math.round(root.sz.icon / 2)
                anchors.verticalCenterOffset: -Math.round(root.sz.icon / 2) + 1
                width: Math.max(height, badgeText.implicitWidth + 6)
                height: Math.max(11, badgeText.implicitHeight + 1)
                radius: height / 2
                color: Theme.bg

                Text {
                    id: badgeText
                    anchors.centerIn: parent
                    text: root.notifCount > 9 ? "9+" : root.notifCount
                    color: Theme.text
                    font.family: Theme.iconFont
                    font.pixelSize: Math.max(8, root.s(8))
                    font.bold: true
                    renderType: Text.NativeRendering
                }
            }
        }
    }

    // CPU / RAM — rounded badges, value only (no %)
    //   "compact": round badge, same size as the app icons, number only
    //   "default": capsule with label + number ("CPU 12" / stacked on vertical bars)
    Component {
        id: statsC
        Lane {
            property string mid: "cpu"
            gap: 2
            Repeater {
                model: [parent.mid.toUpperCase()]
                delegate: Interactive {
                    id: stat
                    readonly property bool moduleVertical:root.moduleIsVertical(stat)
                    required property string modelData
                    Component.onCompleted: root.statButtons = root.statButtons.filter(t => t && t.objectName !== undefined).concat([stat])
                    Component.onDestruction: root.statButtons = root.statButtons.filter(s => s !== stat)
                    readonly property bool isCpu: modelData === "CPU"
                    readonly property bool isGpu: modelData === "GPU"
                    readonly property bool compact: cfg.statsMode === "compact"
                    readonly property int val: isCpu ? root.cpuUsage : isGpu ? GpuStats.usage : root.memPercent
                    readonly property color fg: warning ? Theme.danger : Theme.text
                    readonly property int fontPx: Math.round(root.sz.taskIcon * 0.5)

                    Layout.alignment: Qt.AlignCenter
                    implicitWidth: stat.moduleVertical ? root.panelThick : badge.width + 8
                    implicitHeight: stat.moduleVertical ? badge.height + 8
                                                  : Math.max(root.panelThick - 2, badge.height + 6)

                    onPrimary: processPopup.toggle(stat, modelData)
                    primaryHint: "Voir les processus les plus consommateurs"
                    warning: val >= cfg.statsWarn
                    tip: isCpu ? "CPU usage: " + val + "%"
                               : isGpu ? (GpuStats.available ? "GPU : " + GpuStats.usage + "% · " + GpuStats.temperature : "GPU : mesure indisponible")
                               : "Memory: " + root.memUsedG.toFixed(1) + " / " + root.memTotalG.toFixed(1)
                                 + " GiB (" + val + "%)"

                    Rectangle {
                        id: badge
                        anchors.centerIn: parent
                        // compact: circle the size of an app icon
                        // default: capsule sized to its label + number
                        width: stat.compact ? root.sz.taskIcon
                             : stat.moduleVertical ? root.sz.taskIcon + 6
                             : statRow.implicitWidth + 14
                        height: stat.compact ? root.sz.taskIcon
                              : stat.moduleVertical ? statRow.implicitHeight + 10
                              : root.sz.taskIcon
                        radius: Math.min(width, height) / 2
                        color: Qt.alpha(stat.fg, 0.045)
                        border.width: 1
                        border.color: Qt.alpha(stat.fg, 0.18)

                        GridLayout {
                            id: statRow
                            anchors.centerIn: parent
                            flow: stat.moduleVertical ? GridLayout.TopToBottom : GridLayout.LeftToRight
                            rowSpacing: 0
                            columnSpacing: 4

                            Text {
                                visible: !stat.compact
                                Layout.alignment: Qt.AlignCenter
                                text: stat.modelData
                                color: Qt.alpha(stat.fg, 0.75)
                                font.family: Theme.iconFont
                                font.pixelSize: stat.fontPx - 1
                                renderType: Text.NativeRendering
                            }
                            Text {
                                Layout.alignment: Qt.AlignCenter
                                text: stat.val
                                color: stat.fg
                                font.family: Theme.iconFont
                                font.bold: true
                                font.pixelSize: stat.fontPx
                                renderType: Text.NativeRendering
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: wsC
        Item {
            id: workspaceModule
            readonly property bool moduleVertical: root.moduleIsVertical(workspaceModule)
            property var pressedSlot:null
            function slotParent(){let p=parent;while(p){if(p.moduleSlotMarker===true)return p;p=p.parent;}return null;}
            implicitWidth: workspaceModule.moduleVertical ? root.panelThick : wsLane.implicitWidth + 12
            implicitHeight: wsLane.implicitHeight + (workspaceModule.moduleVertical ? 12 : 0)

            Lane {
                id: wsLane
                anchors.centerIn: parent
                gap: cfg.wsGap

                Repeater {
                    model: Hyprland.workspaces
                    delegate: Rectangle {
                        id: dot
                        required property var modelData
                        visible: modelData.id > 0
                        Layout.alignment: Qt.AlignCenter
                        implicitWidth: workspaceModule.moduleVertical ? cfg.wsDot
                                     : (modelData.focused ? Math.round(cfg.wsDot * 3.2) : cfg.wsDot)
                        implicitHeight: workspaceModule.moduleVertical ? (modelData.focused ? Math.round(cfg.wsDot * 2.4) : cfg.wsDot)
                                                      : cfg.wsDot
                        radius: cfg.wsDot / 2
                        color: modelData.urgent ? Theme.danger
                             : modelData.focused ? Qt.alpha(Theme.accent, 0.2)
                             : dotMa.containsMouse ? Theme.accent2
                             : Qt.alpha(Theme.textFaint, 0.5)

                        Behavior on implicitWidth { NumberAnimation { duration: Theme.animMed; easing.type: Easing.OutQuad } }
                        Behavior on implicitHeight { NumberAnimation { duration: Theme.animMed; easing.type: Easing.OutQuad } }

                        MouseArea {
                            id: dotMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            pressAndHoldInterval:450
                            onPressed:mouse=>{dotTip.suppressed=true;dotTip.shown=false;if(mouse.button===Qt.LeftButton)workspaceModule.pressedSlot=workspaceModule.slotParent();}
                            onPressAndHold:mouse=>{const slot=workspaceModule.pressedSlot;if(slot&&mouse.button===Qt.LeftButton){preventStealing=true;root.beginModuleDrag(slot,dotMa.mapToItem(slot,mouse.x,mouse.y));}}
                            onPositionChanged:mouse=>{const slot=workspaceModule.pressedSlot;if(slot&&root.dragItem===slot)root.updateModuleDrag(slot,dotMa.mapToItem(slot,mouse.x,mouse.y));}
                            onReleased:mouse=>{if(mouse.button!==Qt.LeftButton)return;if(root.dragItem===workspaceModule.pressedSlot)root.finishModuleDrag();workspaceModule.pressedSlot=null;preventStealing=false;}
                            onCanceled:{if(root.dragItem===workspaceModule.pressedSlot)root.cancelModuleDrag();workspaceModule.pressedSlot=null;preventStealing=false;}
                            onClicked: mouse => {
                                if(root.discardReleaseClick||root.manipulating||Date.now()<root.ignoreClickUntil)return;
                                if (mouse.button === Qt.RightButton) root.openSettings();
                                else Hyprland.dispatch("hl.dsp.focus({ workspace = " + dot.modelData.id + " })");
                            }
                        }

                        Tip {
                            id: dotTip
                            hot: dotMa.containsMouse
                            title: "Workspace " + dot.modelData.id
                                   + (dot.modelData.urgent ? " · urgent" : dot.modelData.focused ? " · focused" : "")
                            hints: cfg.tooltipHints ? root.wsHints : ""
                        }
                    }
                }
            }

            WheelHandler {
                enabled: cfg.wsScroll
                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                onWheel: e => {if(root.manipulating){e.accepted=true;return;} if(workspaceModule.pressedSlot&&!root.dragItem&&!root.dragGroupId)root.beginModuleDrag(workspaceModule.pressedSlot,Qt.point(0,0)); if(root.dragItem || root.dragGroupId){root.queueSelectionWheel(e.angleDelta.y,e.modifiers);e.accepted=true;return;} root.run("hyprctl dispatch 'hl.dsp.focus({workspace=\"e"
                                       + (e.angleDelta.y > 0 ? "+1" : "-1") + "\"})'"); }
            }
        }
    }

    ProcessListPopup { id: processPopup; position: cfg.position; uiScale: cfg.scale }

    // Extend the existing Open apps module, keeping its ON/START/CENTER/END controls.
    readonly property var nativeToplevels: Hyprland.toplevels.values
    property var taskModules: []
    property var taskControls: []
    function taskBudget(item) {
        const window=item.window;if(!window)return 0;
        const vertical=item.vertical,frame=window.layoutFrame,candidates=bubblePanels.filter(p=>p&&p.hostWindow===window&&p.baseMetrics.width>0&&p.baseMetrics.height>0);
        const owner=candidates.find(p=>p.groupId===sectionOf(item.mid));
        function band(panel) {
            const g=layoutGroups.find(g=>g.id===panel.groupId)||{},extent=(vertical?panel.baseMetrics.width:panel.baseMetrics.height)+2*root.bubblePadding;
            const available=vertical?window.screen.width:window.screen.height;
            const coordinate=cfg.freeLayout?(vertical?g.x:g.y):0;
            return {start:(coordinate||0)*Math.max(0,available-extent),extent:extent};
        }
        const own=owner?band(owner):{start:0,extent:window.screen.width};
        const panels=candidates.filter(p=>{const b=band(p);return b.start<own.start+own.extent&&b.start+b.extent>own.start;});
        let total=vertical?window.screen.height:window.screen.width;
        // Use the group's base dimensions, independent of allocated task length.
        for(const panel of panels)total-=(vertical?panel.baseMetrics.height:panel.baseMetrics.width)+2*root.bubblePadding+2;
        const peers=taskModules.filter(t=>t&&t.window===window&&t.vertical===vertical&&!t.collapsed&&t.count>0&&panels.some(p=>p.groupId===sectionOf(t.mid))).sort((a,b)=>Number(sectionOf(b.mid)===layoutPriority)-Number(sectionOf(a.mid)===layoutPriority));
        total=Math.max(0,total);
        for(let i=0;i<peers.length;i++){
            const peer=peers[i],minimum=peers.slice(i+1).reduce((sum,t)=>sum+(t.slot+2)*root.moduleFactor(t.mid),0),capacity=Math.max((peer.slot+2)*root.moduleFactor(peer.mid),Math.min(peer.requestedLength*root.moduleFactor(peer.mid),total-minimum));
            if(peer===item)return capacity/root.moduleFactor(peer.mid);
            total-=capacity;
        }
        return 0;
    }
    property var taskButtons: []
    property var appDragItem: null
    property double appDragClosedToken: 0
    property bool appDragNative: false
    property point appDragPoint: Qt.point(0,0)
    function beginAppDrag(item,point) {appDragItem=item;updateAppDrag(item,point);}
    function updateAppDrag(item,point) {
        if(appDragItem!==item)return;
        const p=item.mapToItem(item.hostWindow.contentItem,point.x,point.y),r=root.taskRect(item);
        const origin=item.mapToItem(item.hostWindow.contentItem,0,0);
        appDragPoint=Qt.point(p.x+r.x-origin.x,p.y+r.y-origin.y);
    }
    function finishAppDrag() {
        if(!appDragItem)return;
        const item=appDragItem,address="0x"+item.hyprHandle.address.replace(/^0x/,"");
        taskRestore.command=["python3",Quickshell.env("HOME")+"/.config/quickshell/minimized-restore.py",address,"--at-cursor"];
        taskRestore.running=true;appDragItem=null;ignoreClickUntil=Date.now()+250;
    }
    Variants {
        model:root.appDragItem?[root.appDragItem.hostWindow.screen]:[]
        PanelWindow {
            required property var modelData
            screen:modelData;anchors{top:true;bottom:true;left:true;right:true}
            color:"transparent";exclusionMode:ExclusionMode.Ignore
            MouseArea {anchors.fill:parent;hoverEnabled:true;onPositionChanged:mouse=>root.appDragPoint=Qt.point(mouse.x,mouse.y)}
            WlrLayershell.layer:WlrLayer.Overlay
            Rectangle {
                x:root.appDragPoint.x-22;y:root.appDragPoint.y-22;width:44;height:44;radius:Theme.radius
                color:Theme.bg;border.width:1;border.color:Theme.accent;opacity:.9
                Image {anchors.centerIn:parent;width:28;height:28;source:root.appDragItem?root.iconFor(root.appDragItem.modelData.appId):""}
            }
        }
    }
    property var taskStrips: []
    property var statButtons: []
    function addTaskItem(item, control) {
        if (control) taskControls = taskControls.filter(t => t && t.objectName !== undefined).concat([item]);
        else taskButtons = taskButtons.filter(t => t && t.objectName !== undefined).concat([item]);
    }
    function removeTaskItem(item) {
        taskControls = taskControls.filter(t => t !== item);
        taskButtons = taskButtons.filter(t => t !== item);
    }
    function taskRect(item) {
        const w = item ? item.hostWindow : null;
        if (!w || !w.screen) return null;
        // mapFromItem alone does not notify QML when an ancestor moves.
        let dependency=0,ancestor=item;
        while(ancestor){dependency+=ancestor.x+ancestor.y+ancestor.width+ancestor.height+ancestor.scale;ancestor=ancestor.parent;}
        const p = w.contentItem.mapFromItem(item, 0, 0,item.width,item.height);
        return {x:p.x+dependency*0 + (cfg.position === "right" ? w.screen.width - w.width : 0),
            y:p.y + (cfg.position === "bottom" ? w.screen.height - w.height : 0),
            width:p.width, height:p.height, output:w.screen.name};
    }
    function activateTask(toplevel, hyprHandle, output) {
        if (hyprHandle && hyprHandle.workspace && hyprHandle.workspace.name.startsWith("special:minimized")) {
            if (taskRestore.running) return;
            const address = "0x" + hyprHandle.address.replace(/^0x/, "");
            taskRestore.command = ["python3", Quickshell.env("HOME") + "/.config/quickshell/minimized-restore.py", address, output];
            taskRestore.running = true;
        } else toplevel.activate();
    }
    Process {
        id: taskRestore
        stderr: StdioCollector { onStreamFinished: if (text.trim()) console.warn("Open apps restore: " + text.trim()) }
    }
    Component {
        id: tasksC
        Lane {
            id: taskModule
            property string mid: "tasks"
            Component.onCompleted:root.taskModules=root.taskModules.filter(t=>t&&t.objectName!==undefined).concat([taskModule])
            Component.onDestruction:root.taskModules=root.taskModules.filter(t=>t!==taskModule)
            readonly property real baseWidth:vertical?Math.max(slot,taskToggle.implicitWidth):taskToggle.implicitWidth
            readonly property real baseHeight:vertical?taskToggle.implicitHeight:Math.max(slot,taskToggle.implicitHeight)
            readonly property bool group: mid.startsWith("minigroup-")
            readonly property string groupName: group ? ((root.defMap[mid] || {}).l || "Groupe") : "Open apps"
            readonly property bool collapsed: group ? cfg.collapsedGroups[mid] !== false : cfg.tasksCollapsed
            readonly property var windows: {
                const ready=root.nativeToplevels.length;
                return ToplevelManager.toplevels.values.filter(t=>{
                const handle=t.HyprlandToplevel.handle, name=handle && handle.workspace ? handle.workspace.name : "";
                if(group)return name === "special:minimized-"+mid.slice(10);
                return !cfg.windowGroupsEnabled || !cfg.windowGroups.some(g=>name === "special:minimized-"+g.id);
            }).map((t,i)=>({t:t,i:i,min:t.HyprlandToplevel.handle&&t.HyprlandToplevel.handle.workspace&&t.HyprlandToplevel.handle.workspace.name.startsWith("special:minimized")})).sort((a,b)=>Number(b.min)-Number(a.min)||a.i-b.i).map(x=>x.t); }
            gap: 2
            readonly property int count: taskModule.windows.length
            readonly property int iconPixels: Math.round(Math.max(12, Math.min(32, cfg.taskIconSize)) * cfg.scale)
            readonly property int slot: Math.max(root.panelThick, iconPixels + 6)
            readonly property var window: taskModule.QsWindow.window
            readonly property real outputLength: window && window.screen ? (taskModule.vertical ? window.screen.height : window.screen.width) : 800
            readonly property real requestedLength: collapsed?0:Math.min(count*(slot+2),Math.max(1,cfg.taskMaxVisible)*(slot+2),outputLength*0.5)
            readonly property real visibleLength: Math.max(0,Math.min(requestedLength,root.taskBudget(taskModule)))
            Mod {
                id: taskToggle
                Component.onCompleted: root.addTaskItem(taskToggle, true)
                Component.onDestruction: root.removeTaskItem(taskToggle)
                glyph: taskModule.group ? "󰉋" : taskModule.collapsed ? "▸" : "▾"
                text: String(taskModule.count)
                glyphSize: root.sz.icon
                spacing: 3
                padX: 8
                tip: taskModule.groupName + " — " + taskModule.count
                primaryHint: taskModule.collapsed ? "Déplier les applications" : "Replier les applications"
                onPrimary: {
                    if(taskModule.group) { const value=Object.assign({},cfg.collapsedGroups);value[taskModule.mid]=!taskModule.collapsed;cfg.collapsedGroups=value; }
                    else cfg.tasksCollapsed=!cfg.tasksCollapsed;
                    root.layoutPriority=root.sectionOf(taskModule.mid);root.layoutAxis=taskModule.vertical?"y":"x";root.save();
                }
            }
            Flickable {
                id: appStrip
                readonly property var hostWindow: QsWindow.window
                Component.onCompleted: root.taskStrips = root.taskStrips.filter(t => t && t.objectName !== undefined).concat([appStrip])
                Component.onDestruction: root.taskStrips = root.taskStrips.filter(s => s !== appStrip)
                visible: !taskModule.collapsed && taskModule.count > 0 && taskModule.visibleLength > 0
                implicitWidth: taskModule.vertical ? taskModule.slot : taskModule.visibleLength
                implicitHeight: taskModule.vertical ? taskModule.visibleLength : taskModule.slot
                contentWidth: taskModule.vertical ? width : appLane.implicitWidth
                contentHeight: taskModule.vertical ? appLane.implicitHeight : height
                clip: true
                interactive: !root.manipulating && root.appDragItem === null
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: taskModule.vertical ? Flickable.VerticalFlick : Flickable.HorizontalFlick
                WheelHandler {
                    target: null
                    onWheel: event => {
                        if(root.manipulating){event.accepted=true;return;}
                        const delta = (event.angleDelta.y || event.angleDelta.x) / 120 * (taskModule.slot + 2);
                        if (taskModule.vertical) appStrip.contentY = Math.max(0, Math.min(Math.max(0, appStrip.contentHeight - appStrip.height), appStrip.contentY - delta));
                        else appStrip.contentX = Math.max(0, Math.min(Math.max(0, appStrip.contentWidth - appStrip.width), appStrip.contentX - delta));
                        event.accepted = true;
                    }
                }
                Lane {
                    id: appLane
                    vertical:taskModule.vertical
                    gap: 2
                    Repeater {
                        model: taskModule.windows
                        delegate: Interactive {
                            id: task
                            required property var modelData
                            readonly property var hyprHandle: modelData.HyprlandToplevel.handle
                            restoreDragEligible: isMinimized
                            readonly property bool isMinimized: hyprHandle && hyprHandle.workspace && hyprHandle.workspace.name.startsWith("special:minimized")
                            Component.onCompleted: root.addTaskItem(task, false)
                            Component.onDestruction: root.removeTaskItem(task)
                            implicitWidth: taskModule.slot
                            implicitHeight: taskModule.slot
                            active: modelData.activated
                            tip: (isMinimized ? "Réduite — " : "") + (modelData.title || modelData.appId)
                            primaryHint: isMinimized ? "Restaurer sur ce bureau" : "Activer la fenêtre"
                            tertiaryHint: "Fermer la fenêtre"
                            onPrimary: root.activateTask(modelData, hyprHandle, task.QsWindow.window.screen.name)
                            onTertiary: modelData.close()
                            Image {
                                id: appIcon
                                anchors.centerIn: parent
                                width: taskModule.iconPixels; height: taskModule.iconPixels
                                sourceSize: Qt.size(width, height)
                                asynchronous: true; smooth: true; visible: false
                                source: root.iconFor(task.modelData.appId)
                            }
                            MultiEffect {
                                anchors.fill: appIcon
                                source: appIcon
                                saturation: task.isMinimized ? -1 : 0
                                colorization: 0.0
                                opacity: task.isMinimized ? 0.5 : 1.0
                            }
                            Rectangle {
                                visible: task.isMinimized
                                anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 2 }
                                width: Math.max(6, taskModule.iconPixels / 2); height: 2
                                radius: 1; color: Theme.accent
                            }
                        }
                    }
                }
            }
        }
    }
    Component {
        id: mediaC
        Interactive {
            id:mediaButton
            readonly property bool moduleVertical:root.moduleIsVertical(mediaButton)
            readonly property bool playing: Marquee.player !== null && Marquee.player.isPlaying === true
            readonly property real len: Math.min(Marquee.textW, Marquee.maxW)   // visible text length

            implicitWidth: mediaButton.moduleVertical ? root.panelThick : len + 20
            implicitHeight: mediaButton.moduleVertical ? len + 20 : 18

            tip: Marquee.text
            primaryHint: playing ? "Pause" : "Play"
            secondaryHint: "Next track"
            tertiaryHint: "Previous track"
            onPrimary: root.mediaAct("toggle")
            onSecondary: root.mediaAct("next")
            onTertiary: root.mediaAct("prev")

            // On vertical bars the same marquee is rotated: reads bottom→top on the left, top→bottom on the right.
            MarqueeStrip {
                anchors.centerIn: parent
                width: parent.len
                height: 18
                rotation: mediaButton.moduleVertical ? (cfg.position === "left" ? -90 : 90) : 0
            }
        }
    }

    Component {
        id: opacityC
        Mod {
            id:opacityButton;glyph:"󰗌";glyphSize:root.sz.icon
            tip:LocaleState.tr("Opacité des fenêtres","Window opacity")
            primaryHint:LocaleState.tr("Régler l’opacité","Adjust opacity")
            secondaryHint:LocaleState.tr("Déverrouiller toutes les fenêtres","Unlock all windows")
            scrollHint:LocaleState.tr("Régler l’opacité du bureau","Adjust workspace opacity")
            onPrimary:root.run("qs ipc call settings opacity")
            onHoveredChanged:if(hovered&&root.opacityController)root.opacityController.prepareOsd()
            onScrolled:delta=>{if(root.opacityController)root.opacityController.adjustOsd(delta/120);if(root.volumeController)root.volumeController.showOpacity(opacityButton);}
            onSecondary:if(root.opacityController)root.opacityController.resetAll()
        }
    }
    Component {
        id: brightnessC
        Mod {
            id: brightnessButton
            glyphSize: root.sz.icon
            glyph: "󰃠"
            tip: LocaleState.tr("Luminosité : ", "Brightness: ") + Math.round(BrightnessState.value*100) + "%"
            primaryHint: LocaleState.tr("Ouvrir les paramètres de luminosité", "Open brightness settings")
            scrollHint: LocaleState.tr("Régler la luminosité", "Adjust brightness")
            Component.onCompleted: if(root.volumeController)root.volumeController.registerBrightnessButton(brightnessButton)
            Component.onDestruction: if(root.volumeController)root.volumeController.unregisterBrightnessButton(brightnessButton)
            onPrimary: root.run("qs ipc call settings brightness")
            secondaryHint: LocaleState.tr("Éteindre / rétablir la luminosité","Zero / restore brightness")
            onSecondary: { BrightnessState.toggle(brightnessButton.hostWindow.screen.name);if(root.volumeController)root.volumeController.showBrightness(brightnessButton); }
            onScrolled: delta => {
                BrightnessState.adjust((delta/120)*cfg.volStep,brightnessButton.hostWindow.screen.name);
                if(root.volumeController)root.volumeController.showBrightness(brightnessButton);
            }
        }
    }

    Component {
        id: volumeC
        Mod {
            id: volumeButton
            Component.onCompleted: if (root.volumeController) root.volumeController.registerBarButton(volumeButton)
            Component.onDestruction: if (root.volumeController) root.volumeController.unregisterBarButton(volumeButton)
            readonly property var sink: Pipewire.defaultAudioSink
            readonly property bool ready: !!(sink && sink.audio)
            readonly property real vol: ready ? sink.audio.volume : 0
            readonly property bool muted: ready ? sink.audio.muted : false

            glyphSize: root.sz.icon
            glyph: muted || vol <= 0 ? "\uDB81\uDF5F" : "\uDB81\uDD7E"
            warning: muted
            disabled: !ready
            disabledReason: "No audio output available"
            tip: !ready ? "Volume" : muted ? "Volume: muted" : "Volume: " + Math.round(vol * 100) + "%"
            primaryHint: "Open sound settings"
            secondaryHint: "Mute / unmute"
            scrollHint: "Adjust volume"

            onPrimary: root.run("qs ipc call settings sound")
            onSecondary: root.run("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle")
            onScrolled: delta => {
                if (!ready) return;
                if (root.volumeController) root.volumeController.chooseBarButton(volumeButton);
                sink.audio.volume = Math.max(0, Math.min(cfg.volMax / 100,
                    sink.audio.volume + (delta / 120) * (cfg.volStep / 100)));
            }
        }
    }

    Component {
        id: batteryC
        Mod {
            glyphSize: root.sz.icon
            glyphScaleY: 1.12
            yOffset: root.iconYOffset
            glyph: root.batIcon
            warning: root.batLow
            active: root.batCharging
            tip: root.batTip
        }
    }

    // ───────────────────────── The bar ─────────────────────────
    Variants {
        model: root.barLive
            ? (cfg.allScreens ? Quickshell.screens : Quickshell.screens.slice(0, 1))
            : []

        PanelWindow {
            id: bar
            WlrLayershell.namespace:"43pr-bar"
            required property var modelData
            screen: modelData
            readonly property Item layoutFrame: frame

            anchors {
                top: cfg.freeLayout || cfg.position !== "bottom"
                bottom: cfg.freeLayout || cfg.position !== "top"
                left: cfg.freeLayout || cfg.position !== "right"
                right: cfg.freeLayout || cfg.position !== "left"
            }
            implicitWidth: root.vertical ? Math.max(root.panelThick,...root.bubblePanels.filter(p=>p&&p.hostWindow===bar).map(p=>p.width))+2*root.effEdge : 0
            implicitHeight: root.vertical ? 0 : Math.max(root.panelThick,...root.bubblePanels.filter(p=>p&&p.hostWindow===bar).map(p=>p.height))+2*root.effEdge
            exclusionMode: cfg.reserveSpace && !cfg.freeLayout && !root.nativeReservation ? ExclusionMode.Auto : ExclusionMode.Ignore
            color: "transparent"
            property Region completeRegion: Region { item: frame }
            property Region dragRegion: Region { item: root.dragWindow === bar ? frame : null }
            mask: Region { regions: cfg.freeLayout || !root.joined ? root.bubblePanels.filter(p=>p&&p.hostWindow===bar&&p.visible).map(p=>p.inputRegion).concat([bar.dragRegion]) : [bar.completeRegion] }
            visible: root.barVisible

            Item {
                id: frame
                anchors {
                    fill: parent
                    topMargin: root.edgeMargin("top")
                    bottomMargin: root.edgeMargin("bottom")
                    leftMargin: root.edgeMargin("left")
                    rightMargin: root.edgeMargin("right")
                }

                Rectangle {
                    visible: root.joined && !cfg.freeLayout
                    anchors.fill: parent
                    radius: root.barRadius
                    color: root.bgColor
                    border.width: cfg.border ? 1 : 0
                    border.color: root.borderColor
                }

                Item {
                    id: clockPanel
                    width: 0; height: 0
                    property Item clockTarget: null
                    Component.onCompleted: root.calendarControllers = root.calendarControllers.concat([clockPanel])
                    Component.onDestruction: root.calendarControllers = root.calendarControllers.filter(c => c !== clockPanel)
                    property bool calOpen: false
                    property int monthOffset: 0

                    SystemClock {
                        id: clk
                        precision: cfg.clockSeconds ? SystemClock.Seconds : SystemClock.Minutes
                    }

                    Component {
                        id: clockC
                        Mod {
                            id: clockButton
                            Component.onCompleted: clockPanel.clockTarget = clockButton
                            Component.onDestruction: if (clockPanel.clockTarget === clockButton) { clockPanel.calOpen=false; clockPanel.clockTarget=null; }
                            bold: true
                            baseSize: root.sz.clock
                            text: root.clockText(clk.date)
                            vtext: root.clockVText(clk.date)
                            active: clockPanel.calOpen
                            tip: LocaleState.locale.toString(clk.date, "dddd, d MMMM yyyy")
                            primaryHint: clockPanel.calOpen ? "Close calendar" : "Open calendar"
                            secondaryHint: "Quick actions"
                            tertiaryHint: "Settings"
                            onPrimary: {
                                                        clockPanel.monthOffset = 0;
                                clockPanel.calOpen = !clockPanel.calOpen;
                            }
                            onSecondary: root.run("qs ipc call qa toggle")
                            onTertiary: root.run("qs ipc call settings toggle")
                        }
                    }
                    LazyLoader {
                        active: clockPanel.calOpen && clockPanel.clockTarget !== null

                        PopupWindow {
                            readonly property point p: clockPanel.clockTarget ? bar.contentItem.mapFromItem(clockPanel.clockTarget, 0, 0) : Qt.point(0,0)

                            anchor.window: bar
                            anchor.rect.x: root.vertical
                                ? (cfg.position === "left" ? p.x + (clockPanel.clockTarget ? clockPanel.clockTarget.width : 0) + 6
                                                           : p.x - implicitWidth - 6)
                                : p.x + ((clockPanel.clockTarget ? clockPanel.clockTarget.width : 0) - implicitWidth) / 2
                            anchor.rect.y: root.vertical
                                ? p.y + ((clockPanel.clockTarget ? clockPanel.clockTarget.height : 0) - implicitHeight) / 2
                                : (cfg.position === "top" ? p.y + (clockPanel.clockTarget ? clockPanel.clockTarget.height : 0) + 4
                                                          : p.y - implicitHeight - 4)
                            implicitWidth: calBox.gridW + 2 * calBox.pad
                            implicitHeight: calCol.implicitHeight + 2 * calBox.pad
                            color: "transparent"
                            visible: true

                            Rectangle {
                                id: calBox
                                anchors.fill: parent
                                radius: cfg.calRadius
                                color: root.bgColor
                                border.width: cfg.border ? 1 : 0
                                border.color: root.borderColor

                                readonly property int firstDay: cfg.weekMonday ? 1 : 0
                                readonly property int cellW: 36
                                readonly property int cellH: 30
                                readonly property int pad: 16
                                readonly property int gridW: cellW * 7

                                readonly property date now: clk.date
                                readonly property date view: new Date(now.getFullYear(), now.getMonth() + clockPanel.monthOffset, 1)

                                readonly property var cells: {
                                    const first = (view.getDay() - firstDay + 7) % 7;
                                    const y = view.getFullYear(), m = view.getMonth();
                                    const ty = now.getFullYear(), tm = now.getMonth(), td = now.getDate();
                                    return Array.from({ length: 42 }, (_, i) => {
                                        const d = new Date(y, m, i - first + 1);
                                        return {
                                            n: d.getDate(),
                                            inMonth: d.getMonth() === m,
                                            today: d.getFullYear() === ty && d.getMonth() === tm && d.getDate() === td
                                        };
                                    });
                                }

                                WheelHandler {
                                    onWheel: e => clockPanel.monthOffset += (e.angleDelta.y > 0 ? -1 : 1)
                                }

                                Column {
                                    id: calCol
                                    anchors.centerIn: parent
                                    spacing: 12

                                    Column {
                                        spacing: 2
                                        Text {
                                            text: root.clockText(calBox.now)
                                            color: Theme.text
                                            font.family: Theme.iconFont
                                            font.pixelSize: root.sz.calTime
                                            font.bold: true
                                        }
                                        Text {
                                            text: LocaleState.locale.toString(calBox.now, "dddd, d MMMM yyyy")
                                            color: Theme.textDim
                                            font.family: Theme.iconFont
                                            font.pixelSize: root.sz.calDate
                                        }
                                    }

                                    Rule { width: calBox.gridW }

                                    Item {
                                        width: calBox.gridW
                                        height: 26

                                        Arrow {
                                            anchors.left: parent.left
                                            glyph: "\uDB80\uDD41"
                                            onClicked: clockPanel.monthOffset -= 1
                                        }

                                        Item {
                                            anchors.centerIn: parent
                                            width: monthTitle.implicitWidth + 16
                                            height: parent.height
                                            Text {
                                                id: monthTitle
                                                anchors.centerIn: parent
                                                text: LocaleState.locale.toString(calBox.view, "MMMM yyyy")
                                                color: titleMa.containsMouse ? Theme.accent : Theme.text
                                                font.family: Theme.iconFont
                                                font.pixelSize: root.sz.calMonth
                                                font.bold: true
                                            }
                                            MouseArea {
                                                id: titleMa
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: clockPanel.monthOffset = 0
                                            }
                                        }

                                        Arrow {
                                            anchors.right: parent.right
                                            glyph: "\uDB80\uDD42"
                                            onClicked: clockPanel.monthOffset += 1
                                        }
                                    }

                                    Row {
                                        Repeater {
                                            model: 7
                                            delegate: Text {
                                                required property int index
                                                width: calBox.cellW
                                                horizontalAlignment: Text.AlignHCenter
                                                text: LocaleState.locale.dayName((index + calBox.firstDay) % 7, Locale.ShortFormat)
                                                color: Theme.textDim
                                                font.family: Theme.iconFont
                                                font.pixelSize: root.sz.calWeekday
                                            }
                                        }
                                    }

                                    Grid {
                                        columns: 7
                                        Repeater {
                                            model: calBox.cells
                                            delegate: Item {
                                                required property var modelData
                                                width: calBox.cellW
                                                height: calBox.cellH

                                                Rectangle {
                                                    visible: parent.modelData.today
                                                    anchors.fill: parent
                                                    anchors.margins: 2
                                                    radius: Theme.radius
                                                    color: Qt.alpha(Theme.accent, 0.45)
                                                    border.width: 1
                                                    border.color: Theme.accent
                                                }
                                                Text {
                                                    anchors.centerIn: parent
                                                    text: parent.modelData.n
                                                    color: parent.modelData.inMonth ? Theme.text : Theme.textFaint
                                                    font.family: Theme.iconFont
                                                    font.pixelSize: root.sz.calDay
                                                    font.bold: parent.modelData.today
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                PointHandler {
                    target:null;acceptedButtons:Qt.AllButtons
                    property int previousButtons:Qt.NoButton
                    onPointChanged:{const buttons=point.pressedButtons;const rotate=(buttons&Qt.RightButton)&&!(previousButtons&Qt.RightButton);previousButtons=buttons;if(rotate&&root.dragWindow===bar&&(root.dragItem||root.dragGroupId))root.rotateDrag();}
                    onActiveChanged:if(!active)previousButtons=Qt.NoButton
                }
                ShaderEffectSource {
                    visible:root.dragMoved&&root.dragItem!==null&&root.dragWindow===bar
                    sourceItem:root.dragItem;hideSource:true;live:true
                    width:root.dragItem?root.dragItem.width:0;height:root.dragItem?root.dragItem.height:0
                    x:root.dragPoint.x-frame.x-root.moduleGrip.x;y:root.dragPoint.y-frame.y-root.moduleGrip.y;z:10000
                }
                Repeater {
                    model:root.dragMoved&&root.dragWindow===bar?root.layoutSolution(bar,frame).guides:[]
                    delegate:Rectangle {
                        required property var modelData
                        x:modelData.axis==="x"?modelData.value:0;y:modelData.axis==="y"?modelData.value:0
                        width:modelData.axis==="x"?1:frame.width;height:modelData.axis==="y"?1:frame.height
                        color:Theme.accent;opacity:0.5;z:9999
                    }
                }
                Repeater {
                    model: root.layoutGroups
                    delegate: Panel {
                        required property var modelData
                        groupId: modelData.id
                        model: modelData.items
                        clockComp: clockC
                        x: (root.groupPositions(bar,frame)[groupId] || {x:0}).x
                        y: (root.groupPositions(bar,frame)[groupId] || {y:0}).y
                    }
                }
            }
        }
    }
}
// Layout compatibility: Qt ES array reduction.
