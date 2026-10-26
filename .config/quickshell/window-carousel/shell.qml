import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland

Scope {
    id: root
    property bool opened: false
    property string switchToken: ""
    property var releasedTokens: []
    property var windows: []
    property var history: []
    property int selected: 0
    property var targetScreen: Quickshell.screens[0]
    function remember() {
        const t = ToplevelManager.activeToplevel
        if (t) history = [t].concat(history.filter(w => w !== t && ToplevelManager.toplevels.values.includes(w)))
    }
    Connections {
        target: ToplevelManager
        function onActiveToplevelChanged() { root.remember() }
    }
    function refresh() {
        const all = ToplevelManager.toplevels.values
        const current = windows[selected]
        windows = windows.filter(w => all.includes(w)).concat(all.filter(w => !windows.includes(w)))
        selected = Math.max(0, current ? windows.indexOf(current) : 0)
        if (opened && windows.length === 0) cancel()
    }
    Connections {
        target: ToplevelManager.toplevels
        function onValuesChanged() { root.refresh() }
    }
    function show(reverse) {
        if (opened) { step(reverse ? -1 : 1); return }
        remember()
        const all = ToplevelManager.toplevels.values
        windows = history.filter(w => all.includes(w)).concat(all.filter(w => !history.includes(w)))
        if (!windows.length) return
        const name = Hyprland.focusedMonitor ? Hyprland.focusedMonitor.name : ""
        targetScreen = Quickshell.screens.find(s => s.name === name) || Quickshell.screens[0]
        selected = windows.length > 1 ? (reverse ? windows.length - 1 : 1) : 0
        opened = true
        Qt.callLater(() => { list.forceActiveFocus(); list.center(); centerTimer.restart() })
    }
    function step(delta) { if (windows.length) selected = (selected + delta + windows.length) % windows.length }
    function cancel() { opened = false; switchToken = "" }
    function accept() {
        if (!opened) return
        const t = windows[selected]
        cancel()
        if (t && ToplevelManager.toplevels.values.includes(t)) { t.minimized = false; t.activate() }
    }
    // Le relâchement peut parvenir avant l'ouverture IPC : mémoriser son identifiant.
    function beginSwitch(token, direction) {
        show(direction < 0)
        switchToken = token
        if (releasedTokens.includes(token)) accept()
    }
    function releaseSwitch(token) {
        releasedTokens = releasedTokens.filter(t => t !== token).concat([token]).slice(-32)
        if (opened && switchToken === token) accept()
    }
    Timer { id: centerTimer; interval: 120; onTriggered: { if (root.opened) list.center() } }
    IpcHandler {
        target: "carousel"
        function beginSwitch(token: string, direction: int): void { root.beginSwitch(token, direction) }
        function releaseSwitch(token: string): void { root.releaseSwitch(token) }
        function openCarousel(): void { root.show(false) }
        function reverse(): void { root.show(true) }
        function next(): void { root.step(1) }
        function previous(): void { root.step(-1) }
        function accept(): void { root.accept() }
        function cancel(): void { root.cancel() }
        function status(): string { return JSON.stringify({open:root.opened, selected:root.selected, titles:root.windows.map(w => w.title)}) }
    }
    PanelWindow {
        id: panel
        screen: root.targetScreen
        visible: root.opened
        anchors { top: true; bottom: true; left: true; right: true }
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "window-carousel"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: root.opened ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
        readonly property real ui: Math.min(width / 1280, height / 900, 1.6)
        MouseArea { anchors.fill: parent; onClicked: root.cancel() }
        ListView {
            id: list
            anchors.centerIn: parent
            width: parent.width
            height: Math.min(parent.height * 0.8, 850 * panel.ui)
            orientation: ListView.Horizontal
            model: root.windows
            clip: true
            interactive: false
            keyNavigationEnabled: false
            readonly property real tileWidth: Math.min(height * 0.62, width * 0.6)
            readonly property real sideMargin: (width - tileWidth) / 2
            leftMargin: sideMargin
            rightMargin: sideMargin
            cacheBuffer: width
            function center() { contentX = root.selected * tileWidth - sideMargin }
            Connections { target: root; function onSelectedChanged() { list.center() } }
            onWidthChanged: center()
            Behavior on contentX { enabled: root.opened; SmoothedAnimation { velocity: 5000 * panel.ui; duration: 400 } }
            Keys.onPressed: event => {
                if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
                    root.step((event.modifiers & Qt.ShiftModifier) || event.key === Qt.Key_Backtab ? -1 : 1)
                } else if (event.key === Qt.Key_Escape) root.cancel()
                else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) root.accept()
                else return
                event.accepted = true
            }
            Keys.onReleased: event => {
                if (event.key === Qt.Key_Super_L || event.key === Qt.Key_Super_R || event.key === Qt.Key_Meta) {
                    root.accept(); event.accepted = true
                }
            }
            delegate: Item {
                id: tile
                required property var modelData
                required property int index
                width: list.tileWidth
                height: list.height
                readonly property real baseCenterX: x - list.contentX + width / 2
                readonly property real fraction: Math.min(1, Math.abs(baseCenterX - list.width / 2) / (list.width / 2))
                readonly property real compression: Math.pow(fraction, 4)
                readonly property real scaleFactor: 0.3 + 0.5 * (1 - fraction * fraction * (3 - 2 * fraction))
                readonly property real edgeOffset: (baseCenterX < list.width / 2 ? 1 : -1) * 80 * panel.ui * compression
                z: Math.round((1 - fraction) * 100)
                Rectangle {
                    x: card.x + 6 * panel.ui; y: card.y + 8 * panel.ui
                    width: card.width; height: card.height; radius: 12 * panel.ui; color: "#70000000"
                }
                Rectangle {
                    id: card
                    anchors.verticalCenter: parent.verticalCenter
                    x: (parent.width - width) / 2 + tile.edgeOffset
                    width: parent.width * tile.scaleFactor
                    height: parent.height * tile.scaleFactor
                    color: "#242936"; radius: 10 * panel.ui
                    border.color: tile.index === root.selected ? "#9dccff" : "#506070"
                    border.width: tile.index === root.selected ? 3 : 1
                    Item {
                        id: preview
                        anchors { top: parent.top; left: parent.left; right: parent.right; bottom: caption.top; margins: 4 }
                        clip: true
                        ScreencopyView {
                            id: capture
                            anchors.centerIn: parent
                            captureSource: root.opened && Math.abs(tile.index - root.selected) <= 4 ? tile.modelData : null
                            live: root.opened && tile.index === root.selected
                            paintCursor: false
                            // Cover: same scale on both axes, clipped by the portrait viewport.
                            readonly property real aspect: sourceSize.height > 0 ? sourceSize.width / sourceSize.height : 1
                            width: Math.max(preview.width, preview.height * aspect)
                            height: width / aspect
                            onHasContentChanged: if (hasContent) console.log("CAPTURE", tile.modelData.title, sourceSize)
                        }
                        Text { anchors.centerIn: parent; visible: !capture.hasContent; text: "Aperçu indisponible"; color: "#c4ccda"; font.pixelSize: 12 * panel.ui }
                    }
                    Row {
                        id: caption
                        anchors { bottom: parent.bottom; left: parent.left; right: parent.right; margins: 10 * panel.ui }
                        height: 28 * panel.ui; spacing: 8 * panel.ui
                        Image {
                            width: 22 * panel.ui; height: width; anchors.verticalCenter: parent.verticalCenter
                            readonly property var entry: DesktopEntries.heuristicLookup(tile.modelData.appId)
                            source: Quickshell.iconPath(entry ? entry.icon : "application-x-executable", "application-x-executable")
                        }
                        Text { width: parent.width - 30 * panel.ui; anchors.verticalCenter: parent.verticalCenter; text: tile.modelData.title; color: "white"; elide: Text.ElideRight; font.pixelSize: 13 * panel.ui }
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: { root.selected = tile.index; root.accept() }
                        onWheel: wheel => { root.step(wheel.angleDelta.y < 0 ? 1 : -1); wheel.accepted = true }
                    }
                }
            }
        }
        Text { anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: 35 * panel.ui } text: "Tab : suivant    Maj+Tab : précédent    Super relâché / Entrée : valider    Échap : annuler"; color: "white"; font.pixelSize: 15 * panel.ui }
    }
}
