import QtQuick
import QtQml.Models
import Quickshell

Scope {
    id: root
    property string position: "left"
    property Item target: null
    property var targets: []
    property int revision: 0
    property real gap: 8
    readonly property var window: target ? target.QsWindow.window : null
    readonly property bool vertical: position === "left" || position === "right"
    signal invalidated()
    readonly property var ancestors: {
        const items = []; let item = target;
        while (item) { items.push(item); item = item.parent; }
        return items;
    }
    function registerButton(item) {
        if (targets.indexOf(item) < 0) targets = targets.concat([item]);
        if (!target) target = item;
    }
    function unregisterButton(item) {
        targets = targets.filter(button => button !== item);
        if (target === item) { invalidated(); target = targets.length ? targets[0] : null; }
    }
    function rect(outputWidth, outputHeight) {
        const tick = revision;
        if (!target || !window) return Qt.rect(0, 0, 0, 0);
        const p = window.contentItem.mapFromItem(target, 0, 0,target.width,target.height);
        return Qt.rect(p.x + (position === "right" ? outputWidth - window.width : 0),
            p.y + (position === "bottom" ? outputHeight - window.height : 0), p.width, p.height);
    }
    function base(width, height, outputWidth, outputHeight) {
        if (!target || !window) return Qt.point(outputWidth - width - gap, gap);
        const r = rect(outputWidth, outputHeight);
        return Qt.point(position === "left" ? r.x + r.width + gap : position === "right" ? r.x - width - gap : r.x + (r.width - width) / 2,
            position === "top" ? r.y + r.height + gap : position === "bottom" ? r.y - height - gap : r.y + (r.height - height) / 2);
    }
    function place(width, height, outputWidth, outputHeight, offsetX, offsetY) {
        const p = base(width, height, outputWidth, outputHeight);
        return Qt.point(Math.max(gap, Math.min(Math.max(gap, outputWidth - width - gap), p.x + offsetX)),
            Math.max(gap, Math.min(Math.max(gap, outputHeight - height - gap), p.y + offsetY)));
    }
    Instantiator {
        model: root.ancestors
        delegate: Connections {
            required property var modelData
            target: modelData
            function onScaleChanged() { root.revision++; }
            function onRotationChanged() { root.revision++; }
            function onXChanged() { root.revision++; }
            function onYChanged() { root.revision++; }
            function onWidthChanged() { root.revision++; }
            function onHeightChanged() { root.revision++; }
        }
    }
    Connections {
        target: root.window
        function onVisibleChanged() { if (root.window && !root.window.visible) root.invalidated(); }
    }
}
