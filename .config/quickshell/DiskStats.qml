pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "scripts/storage-modules.js" as StorageModules
Singleton {
    id: root
    property var volumes: []
    property string error: ""
    // Registry metadata only changes on topology/label changes, never each usage sample.
    property var inventory: []
    function choices(ids) {
        return inventory.concat(ids.filter(id=>!inventory.some(v=>v.id===id)).map(id=>({id:id,label:LocaleState.tr("Disque absent","Missing disk"),mount:"",device:""})));
    }
    function modules(ids) { return ids.map(id=>({id:StorageModules.moduleId(id),l:LocaleState.tr("Disque","Disk") + " · " + (inventory.find(v=>v.id===id)||{label:LocaleState.tr("Absent","Missing")}).label})); }
    function volume(id) { return selected([id])[0]; }
    function selected(ids) {
        return ids.map(id => volumes.find(v => v.id === id) || {id:id,label:LocaleState.tr("Disque absent","Missing disk"),mounted:false,percent:null});
    }
    function capacity(bytes) { return bytes === null || bytes === undefined ? "—" : (bytes/1073741824).toFixed(1) + " GiB"; }
    function description(volume) {
        return volume.label + (volume.mount ? " · " + volume.mount : "") + "\n" + (volume.mounted
            ? capacity(volume.used) + " / " + capacity(volume.total) + " · " + capacity(volume.available) + LocaleState.tr(" libres"," free")
            : LocaleState.tr("Non monté ou indisponible","Unmounted or unavailable"));
    }
    Process {
        id: probe
        command: ["python3", Qt.resolvedUrl("scripts/disk-usage.py").toString().replace("file://", "")]
        stdout: StdioCollector {
            onStreamFinished: {
                try {const data=JSON.parse(text);root.volumes=data.volumes;root.error=data.error;
                    const inventory=data.volumes.map(v=>({id:v.id,label:v.label,mount:v.mount,device:v.device}));
                    if(JSON.stringify(inventory)!==JSON.stringify(root.inventory))root.inventory=inventory;}
                catch(e) {root.error="unavailable";}
            }
        }
    }
    Timer { interval:10000;running:true;repeat:true;triggeredOnStart:true;onTriggered:if(!probe.running)probe.running=true }
}
