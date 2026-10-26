-- Native optional layout: only used for free bar bubbles + reserved space.
-- The regular layout is restored when this option is disabled.
local M={}
local function area(r)return r.w*r.h end
local function overlap(a,b)return a.x<b.x+b.w and a.x+a.w>b.x and a.y<b.y+b.h and a.y+a.h>b.y end
function M.free_rectangles(bounds,obstacles)
    local regions={bounds}
    for _,o in ipairs(obstacles or {}) do
        local next={}
        for _,r in ipairs(regions) do
            if not overlap(r,o) then table.insert(next,r)
            else
                local x1,y1=math.max(r.x,o.x),math.max(r.y,o.y)
                local x2,y2=math.min(r.x+r.w,o.x+o.w),math.min(r.y+r.h,o.y+o.h)
                local function add(x,y,w,h)if w>0 and h>0 then table.insert(next,{x=x,y=y,w=w,h=h})end end
                if o.h>=o.w then
                    add(r.x,r.y,x1-r.x,r.h);add(x2,r.y,r.x+r.w-x2,r.h)
                    add(x1,r.y,x2-x1,y1-r.y);add(x1,y2,x2-x1,r.y+r.h-y2)
                else
                    add(r.x,r.y,r.w,y1-r.y);add(r.x,y2,r.w,r.y+r.h-y2)
                    add(r.x,y1,x1-r.x,y2-y1);add(x2,y1,r.x+r.w-x2,y2-y1)
                end
            end
        end
        regions=next
    end
    table.sort(regions,function(a,b)return area(a)>area(b)end)
    return regions
end
function M.boxes(bounds,obstacles,n)
    local free=M.free_rectangles(bounds,obstacles)
    local usable={}
    for _,r in ipairs(free)do if r.w>=240 and r.h>=160 then table.insert(usable,r)end end
    -- Tiny screens still get a usable rectangle; never intentionally overlap a bubble.
    if #usable==0 and #free>0 then usable={free[1]}end
    if #usable==0 then return {} end
    local counts={};for i=1,#usable do counts[i]=0 end
    for i=1,n do
        local best,score=1,-1
        for j,r in ipairs(usable)do
            local candidate=area(r)/(counts[j]+1)^2
            if candidate>score then best,score=j,candidate end
        end
        counts[best]=counts[best]+1
    end
    local boxes={}
    for i,r in ipairs(usable)do
        local count=counts[i]
        if count>0 then
            local cols=math.max(1,math.min(count,math.floor(math.sqrt(count*r.w/r.h)+.5)))
            local rows=math.ceil(count/cols)
            for j=1,count do
                local row=math.floor((j-1)/cols)
                local inrow=math.min(cols,count-row*cols)
                table.insert(boxes,{x=r.x+((j-1)%cols)*r.w/inrow,y=r.y+row*r.h/rows,w=r.w/inrow,h=r.h/rows})
            end
        end
    end
    return boxes
end
if hl then
    hl.layout.register('43pr-bubbles',{
        recalculate=function(ctx)
            local runtime=os.getenv('XDG_RUNTIME_DIR')
            local ok,state=false,{}
            if runtime then ok,state=pcall(dofile,runtime..'/43pr-bubbles/state.lua')end
            local monitor=ctx.targets[1] and ctx.targets[1].window and ctx.targets[1].window.monitor
            local obstacles=ok and type(state)=='table' and state[monitor and monitor.name or ''] or {}
            local boxes=M.boxes(ctx.area,obstacles,#ctx.targets)
            for i,target in ipairs(ctx.targets)do if boxes[i]then target:place(boxes[i])end end
        end,
        layout_msg=function(ctx,msg)return msg=='refresh' end,
    })
end
return M
