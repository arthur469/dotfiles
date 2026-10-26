pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
Singleton {
    id: root
    property real value: 0.55
    property bool available: false
    property string error: ""
    property string output: ""
    property var pendingValues: ({})
    property var pendingActions: ({})
    property var readOutputs: []
    property string workerOutput: ""
    property int workerValue: -1
    property var samples: ({})

    // Session-local: the previous level is independent for every output.
    FileView {
        id: toggleFile
        path: Quickshell.env("XDG_RUNTIME_DIR") + "/43pr-brightness-toggle.json"
        printErrors: false
        blockLoading: true
        adapter: JsonAdapter { id: toggleState; property var previous: ({}) }
    }
    function knownValue(name) {
        if (pendingValues[name] !== undefined) return pendingValues[name];
        if (worker.running && workerOutput === name && workerValue >= 0) return workerValue;
        return samples[name] === undefined ? null : samples[name];
    }
    function selectOutput(name) {
        if (name !== undefined) output = name;
        const known = knownValue(output);
        available = known !== null;
        if (available) value = known / 100;
    }
    function remember(name, percent) {
        if (percent <= 0) return;
        const previous = Object.assign({}, toggleState.previous);
        previous[name] = percent;
        toggleState.previous = previous;
        toggleFile.writeAdapter();
    }
    function requestAction(name, kind, amount) {
        selectOutput(name);
        const known = knownValue(output);
        if (known === null) {
            const actions = Object.assign({}, pendingActions);
            actions[output] = (actions[output] || []).concat([{kind: kind, amount: amount}]);
            pendingActions = actions;
            requestRead(output);
            return;
        }
        if (kind === "toggle") {
            if (known > 0) { remember(output, known); set(0, output); }
            else { const previous = Number(toggleState.previous[output]); set(previous > 0 && previous <= 100 ? previous : 50, output); }
        } else set(known + amount, output);
    }
    function toggle(name) { requestAction(name, "toggle", 0); }
    function adjust(delta, name) { requestAction(name, "adjust", delta); }
    function requestRead(name) {
        if (!(worker.running && workerOutput === name) && !readOutputs.includes(name))
            readOutputs = readOutputs.concat([name]);
        pumpReads();
    }
    function pumpReads() {
        if (worker.running || !readOutputs.length) return;
        const name = readOutputs[0]; readOutputs = readOutputs.slice(1); launch(name, -1);
    }
    function refresh(name) {
        selectOutput(name);
        if (pendingValues[output] === undefined) requestRead(output);
    }
    function set(percent, name) {
        if (name !== undefined) output = name;
        const next = Math.max(0, Math.min(100, Math.round(percent)));
        remember(output, next);
        const values = Object.assign({}, pendingValues); values[output] = next; pendingValues = values;
        value = next / 100; available = true; error = ""; applyTimer.restart();
    }
    function launch(name, percent) {
        workerOutput = name; workerValue = percent;
        let args = ["python3", Qt.resolvedUrl("scripts/brightness.py").toString().replace("file://", "")];
        if (name) args = args.concat(["--output", name]);
        if (percent >= 0) args = args.concat(["--set", String(percent)]);
        worker.command = args; worker.running = true;
    }
    Timer {
        id: applyTimer; interval: 280
        onTriggered: {
            if (worker.running) { restart(); return; }
            const names = Object.keys(root.pendingValues);
            if (!names.length) { root.pumpReads(); return; }
            const name = names.includes(root.output) ? root.output : names[0], next = root.pendingValues[name];
            const values = Object.assign({}, root.pendingValues); delete values[name]; root.pendingValues = values;
            root.launch(name, next);
        }
    }
    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const d = JSON.parse(text), name = root.workerOutput;
                    if (d.available) {
                        const values = Object.assign({}, root.samples); values[name] = d.value; root.samples = values;
                        const actions = root.pendingActions[name] || [];
                        const waiting = Object.assign({}, root.pendingActions); delete waiting[name]; root.pendingActions = waiting;
                        const selected = root.output;
                        for (const action of actions) root.requestAction(name, action.kind, action.amount);
                        root.selectOutput(selected);
                    }
                    if (name === root.output) {
                        root.error = d.error || "";
                        if (!d.available) root.available = false;
                        else root.selectOutput(name);
                    }
                } catch (e) { root.error = LocaleState.tr("Lecture de luminosité impossible", "Cannot read brightness"); }
            }
        }
        onExited: {
            if (Object.keys(root.pendingValues).length && !applyTimer.running) applyTimer.restart();
            root.pumpReads();
        }
    }
}
