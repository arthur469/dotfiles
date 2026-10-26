.pragma library
function csv(value) { return String(value || "").split(",").filter(Boolean); }
function expand(items) { return items.reduce((a,x) => a.concat(x === "stats" ? ["cpu","ram","gpu"] : [x]), []); }
function groups(state, moduleIds) {
    const valid = moduleIds.concat(["clock"]), used = new Set(), result = [];
    for (const [id, position] of [["start",0],["center",0.5],["end",1]]) {
        const items = expand(csv(state[id + "Mods"])).filter(x => valid.includes(x) && !used.has(x) && (used.add(x), true));
        result.push({id:id,position:position,items:items});
    }
    for (const raw of (state.moduleGroups || [])) {
        if (!raw || typeof raw.id !== "string" || !raw.id.startsWith("free-") || (!raw.items || typeof raw.items.length !== "number")) continue;
        const items = Array.from(raw.items).filter(x => valid.includes(x) && !used.has(x) && (used.add(x),true));
        if (items.length) result.push({id:raw.id,position:Math.max(0,Math.min(1,Number(raw.position)||0)),x:typeof raw.x === "number" ? raw.x : undefined,y:typeof raw.y === "number" ? raw.y : undefined,items:items});
    }
    if (!used.has("clock")) { result[1].items.unshift("clock"); used.add("clock"); }
    result[2].items = result[2].items.concat(moduleIds.filter(x => !used.has(x)));
    return result;
}
function move(state,moduleIds,item,targetId,position,index) {
    const all = groups(state,moduleIds).map(g => Object.assign({},g,{items:g.items.filter(x => x !== item)}));
    let target = all.find(g => g.id === targetId);
    if (!target) { target={id:targetId,position:position,items:[]}; all.push(target); }
    const i = index === undefined ? target.items.length : Math.max(0,Math.min(target.items.length,index));
    target.items.splice(i,0,item);
    const output={moduleGroups:all.filter(g => g.id.startsWith("free-") && g.items.length)};
    for (const id of ["start","center","end"]) output[id+"Mods"]=all.find(g => g.id===id).items.join(",");
    return output;
}

// Find the nearest non-overlapping logical rectangle, clamped to the output.
function avoid(x,y,w,h,others,width,height) {
    function candidate(cx,cy) {
        cx=Math.max(0,Math.min(Math.max(0,width-w),cx));cy=Math.max(0,Math.min(Math.max(0,height-h),cy));
        if(others.every(r => cx+w+8<=r.x || cx>=r.x+r.width+8 || cy+h+8<=r.y || cy>=r.y+r.height+8)) return {x:cx,y:cy};
        return null;
    }
    let result=candidate(x,y); if(result)return result;
    for(let distance=24;distance<Math.max(width,height);distance+=24) {
        for(let d=-distance;d<=distance;d+=24) {
            result=candidate(x+d,y-distance)||candidate(x+d,y+distance)||candidate(x-distance,y+d)||candidate(x+distance,y+d);
            if(result)return result;
        }
    }
    return {x:Math.max(4,Math.min(width-w-4,x)),y:Math.max(4,Math.min(height-h-4,y)),crowded:true};
}

function cells(state,group,vertical) {
    const saved=(state.groupCells||{})[group.id]||{}, result={};
    group.items.forEach((id,i)=>result[id]=saved[id]||{x:vertical?0:i,y:vertical?i:0});
    return result;
}
function regroup(state,moduleIds,item,targetId,position,index,anchor,direction,vertical) {
    const before=groups(state,moduleIds),target=before.find(g=>g.id===targetId),output=move(state,moduleIds,item,targetId,position,index);
    const all=Object.assign({},state.groupCells||{});
    for(const g of before) {const c=Object.assign({},all[g.id]||{});delete c[item];all[g.id]=c;}
    if(target && anchor) {
        const c=cells(state,target,vertical),a=c[anchor]||{x:0,y:0};delete c[item];
        const horizontal=direction==="left"||direction==="right", axis=horizontal?"x":"y";
        const point=a[axis]+((direction==="right"||direction==="bottom")?1:0);
        for(const id in c)if(c[id][axis]>=point)c[id]=Object.assign({},c[id],{[axis]:c[id][axis]+1});
        c[item]=horizontal?{x:point,y:a.y}:{x:a.x,y:point};all[targetId]=c;
    } else all[targetId]={[item]:{x:0,y:0}};
    output.groupCells=all;return output;
}
function relocate(state,moduleIds,groupId,position,x,y,vertical) {
    const all=groups(state,moduleIds),g=all.find(g=>g.id===groupId);if(!g)return null;
    const id=groupId.startsWith("free-")?groupId:"free-"+Date.now();
    const output={moduleGroups:all.filter(v=>v.id.startsWith("free-")&&v.id!==groupId),groupCells:Object.assign({},state.groupCells||{})};
    for(const key of ["start","center","end"])output[key+"Mods"]=all.find(v=>v.id===key).items.filter(v=>!g.items.includes(v)).join(",");
    output.moduleGroups.push({id:id,position:position,x:x,y:y,items:g.items.slice()});output.groupCells[id]=cells(state,g,vertical);return output;
}
