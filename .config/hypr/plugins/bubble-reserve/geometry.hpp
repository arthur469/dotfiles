#pragma once
#include <algorithm>
#include <cmath>
#include <vector>
namespace BubbleReserve {
struct Rect {double x,y,w,h;};
inline bool overlap(const Rect& a,const Rect& b){return a.x<b.x+b.w && a.x+a.w>b.x && a.y<b.y+b.h && a.y+a.h>b.y;}
inline Rect project(Rect box,const std::vector<Rect>& obstacles,double margin) {
    for(const auto& raw:obstacles) {
        Rect o={raw.x-margin,raw.y-margin,raw.w+2*margin,raw.h+2*margin};
        if(!overlap(box,o))continue;
        std::vector<Rect> candidates;
        auto add=[&](double x,double y,double w,double h){if(w>=32 && h>=24)candidates.push_back({x,y,w,h});};
        add(box.x,box.y,std::min(box.x+box.w,o.x)-box.x,box.h);
        add(std::max(box.x,o.x+o.w),box.y,box.x+box.w-std::max(box.x,o.x+o.w),box.h);
        add(box.x,box.y,box.w,std::min(box.y+box.h,o.y)-box.y);
        add(box.x,std::max(box.y,o.y+o.h),box.w,box.y+box.h-std::max(box.y,o.y+o.h));
        if(candidates.empty())continue;
        box=*std::max_element(candidates.begin(),candidates.end(),[](const Rect& a,const Rect& b){return a.w*a.h<b.w*b.h;});
    }
    return box;
}
}
