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
    } else {const c=target?cells(state,target,vertical):{};delete c[item];const axis=vertical?"y":"x";let end=0;for(const id in c)end=Math.max(end,c[id][axis]+1);c[item]={x:vertical?0:end,y:vertical?end:0};all[targetId]=c;}
    output.groupCells=all;return output;
}
function relocate(state,moduleIds,groupId,position,x,y,vertical) {
    const all=groups(state,moduleIds),g=all.find(g=>g.id===groupId);if(!g)return null;
    const id=groupId.startsWith("free-")?groupId:"free-"+Date.now();
    const output={moduleGroups:all.filter(v=>v.id.startsWith("free-")&&v.id!==groupId),groupCells:Object.assign({},state.groupCells||{})};
    for(const key of ["start","center","end"])output[key+"Mods"]=all.find(v=>v.id===key).items.filter(v=>!g.items.includes(v)).join(",");
    output.moduleGroups.push({id:id,position:position,x:x,y:y,items:g.items.slice()});output.groupCells[id]=cells(state,g,vertical);output.groupRotations=Object.assign({},state.groupRotations||{});output.groupRotations[id]=(state.groupRotations||{})[groupId]||0;return output;
}

// Measure only occupied cells. Invisible/detached slots cannot leave phantom gaps.
function measure(cellMap, entries, gap) {
    const cols={},rows={},positions={};gap=gap||0;
    for(const e of entries){const c=cellMap[e.id]||{x:0,y:0};cols[c.x]=Math.max(cols[c.x]||0,e.width);rows[c.y]=Math.max(rows[c.y]||0,e.height);}
    const xs={},ys={};let width=0,height=0;
    for(const key of Object.keys(cols).map(Number).sort((a,b)=>a-b)){xs[key]=width;width+=cols[key]+gap;}
    for(const key of Object.keys(rows).map(Number).sort((a,b)=>a-b)){ys[key]=height;height+=rows[key]+gap;}
    if(width)width-=gap;if(height)height-=gap;
    for(const e of entries){const c=cellMap[e.id]||{x:0,y:0};positions[e.id]={x:xs[c.x]+((cols[c.x]||0)-e.width)/2,y:ys[c.y]+((rows[c.y]||0)-e.height)/2};}
    return {width:width,height:height,positions:positions};
}
function rotateGroup(state,moduleIds,id,vertical) {
    const group=groups(state,moduleIds).find(g=>g.id===id);if(!group)return null;
    const previous=cells(state,group,vertical),next={};let maxY=0;for(const key in previous)maxY=Math.max(maxY,previous[key].y);
    for(const key in previous)next[key]={x:maxY-previous[key].y,y:previous[key].x};
    const all=Object.assign({},state.groupCells||{});all[id]=next;
    const turns=Object.assign({},state.groupRotations||{});turns[id]=((turns[id]||0)+1)%4;
    return {groupCells:all,groupRotations:turns};
}
function mergeGroups(state,moduleIds,sourceId,targetId,anchor,direction,vertical) {
    const all=groups(state,moduleIds),source=all.find(g=>g.id===sourceId),target=all.find(g=>g.id===targetId);
    if(!source||!target||source===target)return null;
    let output={moduleGroups:all.filter(g=>g.id.startsWith('free-')&&g.id!==sourceId).map(g=>Object.assign({},g,{items:g.id===targetId?g.items.concat(source.items):g.items.slice()}))};
    for(const id of ['start','center','end'])output[id+'Mods']=(id===sourceId?[]:id===targetId?target.items.concat(source.items):all.find(g=>g.id===id).items).join(',');
    const sc=cells(state,source,vertical),tc=cells(state,target,vertical),a=tc[anchor]||{x:0,y:0};
    const horizontal=direction==='left'||direction==='right',axis=horizontal?'x':'y';
    let sx=0,sy=0;for(const id in sc){sx=Math.max(sx,sc[id].x+1);sy=Math.max(sy,sc[id].y+1);}
    const point=a[axis]+((direction==='right'||direction==='bottom')?1:0),amount=horizontal?sx:sy;
    const next={};for(const id in tc)next[id]=Object.assign({},tc[id],{[axis]:tc[id][axis]>=point?tc[id][axis]+amount:tc[id][axis]});
    for(const id in sc)next[id]={x:sc[id].x+(horizontal?point:a.x),y:sc[id].y+(horizontal?a.y:point)};
    output.groupCells=Object.assign({},state.groupCells||{});delete output.groupCells[sourceId];output.groupCells[targetId]=next;
    return output;
}
function intersects(a,b,gap) {return a.x<b.x+b.width+gap&&a.x+a.width+gap>b.x&&a.y<b.y+b.height+gap&&a.y+a.height+gap>b.y;}
function clampRect(r,width,height) {return Object.assign({},r,{x:Math.max(0,Math.min(Math.max(0,width-r.width),r.x)),y:Math.max(0,Math.min(Math.max(0,height-r.height),r.y))});}
// Place the interacted bubble first, then its nearest neighbours. Moving a
// neighbour may therefore push the next one; original anchors are never saved
// merely because a temporary Open apps expansion displaced another bubble.
function solve(rectangles,width,height,priority,axis,gap,ignored,orderAxis) {
    gap=Math.max(0,gap||0);ignored=ignored||[];
    const input=rectangles.map(r=>clampRect(r,width,height));
    // Expansion is a temporary change in size, not an instruction to reorder
    // neighbouring bubbles. Pack each shared band in its saved anchor order.
    if(orderAxis && !ignored.length) {
        const along=orderAxis==='y'?'y':'x',cross=orderAxis==='y'?'x':'y';
        const size=orderAxis==='y'?'height':'width',crossSize=orderAxis==='y'?'width':'height',limit=orderAxis==='y'?height:width;
        const remaining=input.slice(),bands=[];
        while(remaining.length){const band=[remaining.shift()];let changed=true;
            while(changed){changed=false;for(let i=remaining.length-1;i>=0;i--){const r=remaining[i];if(band.some(p=>r[cross]<p[cross]+p[crossSize]+gap&&r[cross]+r[crossSize]+gap>p[cross])){band.push(r);remaining.splice(i,1);changed=true;}}}
            bands.push(band);
        }
        if(bands.every(b=>b.reduce((sum,r)=>sum+r[size],0)+gap*(b.length-1)<=limit)) {
            const result={};
            for(const band of bands){band.sort((a,b)=>(a.order===undefined?a[along]:a.order)-(b.order===undefined?b[along]:b.order));
                const placed=band.map(r=>Object.assign({},r));
                for(let i=1;i<placed.length;i++)placed[i][along]=Math.max(placed[i][along],placed[i-1][along]+placed[i-1][size]+gap);
                for(let i=placed.length-1;i>=0;i--)placed[i][along]=Math.min(placed[i][along],i===placed.length-1?limit-placed[i][size]:placed[i+1][along]-gap-placed[i][size]);
                if(placed[0][along]<0){placed[0][along]=0;for(let i=1;i<placed.length;i++)placed[i][along]=Math.max(placed[i][along],placed[i-1][along]+placed[i-1][size]+gap);}
                for(const r of placed)result[r.id]=r;
            }
            return {positions:result,crowded:false};
        }
    }
    const leader=input.find(r=>r.id===priority),distance=r=>leader?Math.hypot((r.x+r.width/2)-(leader.x+leader.width/2),(r.y+r.height/2)-(leader.y+leader.height/2)):0;
    const order=input.slice().sort((a,b)=>a.id===priority?-1:b.id===priority?1:distance(a)-distance(b));
    const placed=[],result={};let crowded=false;
    for(const r of order) {
        if(ignored.includes(r.id)){result[r.id]=r;continue;}
        let position=r;
        if(placed.some(p=>intersects(r,p,gap))) {
            const candidates=[];
            const add=(x,y)=>{const c=clampRect(Object.assign({},r,{x:x,y:y}),width,height);if(!placed.some(p=>intersects(c,p,gap)))candidates.push(c);};
            for(const p of placed){add(r.x,p.y-r.height-gap);add(r.x,p.y+p.height+gap);add(p.x-r.width-gap,r.y);add(p.x+p.width+gap,r.y);}
            for(const p of placed)for(const q of placed){add(p.x-r.width-gap,q.y-r.height-gap);add(p.x+p.width+gap,q.y+q.height+gap);}
            const score=c=>{const dx=c.x-r.x,dy=c.y-r.y;return dx*dx*(axis==='y'?64:1)+dy*dy*(axis==='x'?64:1);};
            candidates.sort((a,b)=>score(a)-score(b));
            if(candidates.length)position=candidates[0];else crowded=true;
        }
        placed.push(position);result[r.id]=position;
    }
    return {positions:result,crowded:crowded};
}
function snap(rect,others,width,height,threshold) {
    let x=rect.x,y=rect.y,bestX=threshold+1,bestY=threshold+1,guides=[];
    const movingX=[rect.x,rect.x+rect.width/2,rect.x+rect.width],movingY=[rect.y,rect.y+rect.height/2,rect.y+rect.height];
    for(const other of others){
        for(const edge of [other.x,other.x+other.width/2,other.x+other.width])for(const own of movingX){const d=Math.abs(edge-own);if(d<bestX){bestX=d;x=rect.x+edge-own;guides=guides.filter(g=>g.axis!=='x').concat([{axis:'x',value:edge}]);}}
        for(const edge of [other.y,other.y+other.height/2,other.y+other.height])for(const own of movingY){const d=Math.abs(edge-own);if(d<bestY){bestY=d;y=rect.y+edge-own;guides=guides.filter(g=>g.axis!=='y').concat([{axis:'y',value:edge}]);}}
    }
    const clamped=clampRect(Object.assign({},rect,{x:bestX<=threshold?x:rect.x,y:bestY<=threshold?y:rect.y}),width,height);
    return {x:clamped.x,y:clamped.y,guides:guides.filter(g=>(g.axis==='x'?bestX:bestY)<=threshold)};
}
