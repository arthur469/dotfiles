.pragma library
function moduleId(id) { return "disk:" + encodeURIComponent(id); }
function isDisk(id) { return String(id).startsWith("disk:"); }
function volumeId(id) { return isDisk(id) ? decodeURIComponent(id.slice(5)) : ""; }
// Upgrade the old aggregate slot once, preserving its bubble and appearance.
function migrate(state) {
    const ids=(state.diskVolumes||[]).map(moduleId);
    if(!ids.length)return {};
    const all=[].concat(...["start","center","end"].map(k=>String(state[k+"Mods"]||"").split(",")),...(state.moduleGroups||[]).map(g=>g.items||[]));
    const fresh=ids.filter(id=>!all.includes(id)),patch={};
    function replace(items){return items.reduce((out,id)=>out.concat(id==="disk"?fresh:[id]),[]);}
    for(const k of ["startMods","centerMods","endMods"])if(String(state[k]||"").split(",").includes("disk"))patch[k]=replace(state[k].split(",")).join(",");
    if((state.moduleGroups||[]).some(g=>(g.items||[]).includes("disk")))patch.moduleGroups=state.moduleGroups.map(g=>Object.assign({},g,{items:replace(g.items)}));
    for(const k of ["moduleScale","moduleOpacity"]){
        const values=Object.assign({},state[k]||{});
        if(values.disk!==undefined){for(const id of ids)if(values[id]===undefined)values[id]=values.disk;delete values.disk;patch[k]=values;}
    }
    const hidden=String(state.hidden||"").split(",");
    if(hidden.includes("disk"))patch.hidden=Array.from(new Set(hidden.filter(id=>id!=="disk").concat(ids))).join(",");
    const cells=Object.assign({},state.groupCells||{});let changed=false;
    for(const group in cells){
        const before=cells[group];if(!before.disk)continue;
        const next={},at=before.disk,vertical=(state.position==="left"||state.position==="right")!==!!((state.groupRotations||{})[group]%2),axis=vertical?"y":"x";
        for(const id in before)if(id!=="disk")next[id]=Object.assign({},before[id],{[axis]:before[id][axis]>=at[axis]?before[id][axis]+Math.max(0,fresh.length-1):before[id][axis]});
        fresh.forEach((id,i)=>next[id]=Object.assign({},at,{[axis]:at[axis]+i}));cells[group]=next;changed=true;
    }
    if(changed)patch.groupCells=cells;
    return patch;
}

// Keep storage and scale upgrades in the same order in Bar and Settings.
function upgrade(state,scaleMigration) {
    const storage=migrate(state);
    return Object.assign({},storage,scaleMigration({moduleScale:storage.moduleScale||state.moduleScale,moduleZoom:state.moduleZoom,moduleScaleVersion:state.moduleScaleVersion}));
}
