#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/layout/target/WindowTarget.hpp>
#include <hyprland/src/layout/space/Space.hpp>
#include <set>
#include <linux/input-event-codes.h>
#include <hyprland/src/event/EventBus.hpp>
#include <hyprland/src/managers/EventManager.hpp>
#include <hyprland/src/desktop/state/WindowState.hpp>
#include <hyprland/src/managers/fullscreen/FullscreenController.hpp>
#include <hyprland/src/output/Monitor.hpp>
#include <hyprland/src/render/Renderer.hpp>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <map>
#include <stdexcept>
#include "geometry.hpp"
namespace {
HANDLE handle;
CFunctionHook* hook=nullptr;
CHyprSignalListener buttonListener;
bool leftHeld=false;
using UpdatePosition=void(*)(Layout::CWindowTarget*,uint8_t);
std::filesystem::path statePath;
std::filesystem::file_time_type stateStamp;
std::map<std::string,std::vector<BubbleReserve::Rect>> obstacles;
double margin=0;
bool enabled=false;

void readState() {
    std::error_code error;
    const auto stamp=std::filesystem::last_write_time(statePath,error);
    if(error){enabled=false;obstacles.clear();return;}
    if(stamp==stateStamp)return;
    stateStamp=stamp;obstacles.clear();enabled=false;
    if(std::filesystem::file_size(statePath,error)>65536 || error)return;
    std::ifstream input(statePath);
    int active=0;double gap=0;
    if(!(input>>active>>gap) || !std::isfinite(gap) || gap<0 || gap>200)return;
    margin=gap;enabled=active==1;
    std::string output;BubbleReserve::Rect rect{};size_t count=0;
    while(count++<128 && input>>std::quoted(output)>>rect.x>>rect.y>>rect.w>>rect.h) {
        if(std::isfinite(rect.x)&&std::isfinite(rect.y)&&std::isfinite(rect.w)&&std::isfinite(rect.h)&&rect.w>0&&rect.h>0&&rect.w<=20000&&rect.h<=20000)obstacles[output].push_back(rect);
    }
}
void position(Layout::CWindowTarget* target,uint8_t flags) {
    reinterpret_cast<UpdatePosition>(hook->m_original)(target,flags);
    readState();
    if(!enabled)return;
    const auto window=target->window();
    if(!window || !window->m_isMapped || !window->m_monitor)return;
    const auto fullscreen=Fullscreen::controller()->getFullscreenModes(window);
    if(fullscreen.internal==Fullscreen::FSMODE_FULLSCREEN || fullscreen.client==Fullscreen::FSMODE_FULLSCREEN)return;
    const auto found=obstacles.find(window->m_monitor->m_name);
    if(found==obstacles.end())return;
    const auto original=window->geometricBox(Desktop::View::IGeometric::GEOMETRIC_GOAL);
    const auto next=BubbleReserve::project({original.x,original.y,original.w,original.h},found->second,margin+window->getRealBorderSize());
    if(std::abs(next.x-original.x)<.5&&std::abs(next.y-original.y)<.5&&std::abs(next.w-original.w)<.5&&std::abs(next.h-original.h)<.5)return;
    g_pHyprRenderer->damageWindow(window);
    window->setBox({next.x,next.y,next.w,next.h});
    window->updateWindowDecos();
    if(!(flags&Layout::TARGET_UPDATE_NO_CLIENT_CONFIGURE))window->sendWindowSize();
    g_pHyprRenderer->damageWindow(window);
}
void refresh() {
    readState();
    std::set<Layout::CSpace*> updated;
    for(const auto& window:Desktop::windowState()->windows()) {
        if(!window || !window->m_isMapped || !window->layoutTarget())continue;
        const auto space=window->layoutTarget()->space();
        if(space && updated.insert(space.get()).second)space->recalculate();
    }
    for(const auto& w:Desktop::windowState()->windows())if(w && w->m_isMapped && w->layoutTarget()) {
        // A maximized target must recompute its native box before reservation.
        if(Fullscreen::controller()->getFullscreenModes(w).internal==Fullscreen::FSMODE_MAXIMIZED)
            Fullscreen::controller()->m_windowPosSettingQueued=true;
        w->layoutTarget()->recalc();
    }

}
}
APICALL EXPORT std::string PLUGIN_API_VERSION(){return HYPRLAND_API_VERSION;}
APICALL EXPORT PLUGIN_DESCRIPTION_INFO PLUGIN_INIT(HANDLE pluginHandle) {
    handle=pluginHandle;
    if(HyprlandAPI::getHyprlandVersion(handle).hash!=GIT_COMMIT_HASH)throw std::runtime_error("43PR bubble reservation: rebuild for this Hyprland version");
    const char* runtime=std::getenv("XDG_RUNTIME_DIR");const char* signature=std::getenv("HYPRLAND_INSTANCE_SIGNATURE");
    if(!runtime||!signature)throw std::runtime_error("43PR bubble reservation: missing session identity");
    statePath=std::filesystem::path(runtime)/"43pr-bubbles"/signature/"reservation.txt";
    for(const auto& match:HyprlandAPI::findFunctionsByName(handle,"updatePos")) {
        if(match.demangled.find("Layout::CWindowTarget::updatePos(")!=std::string::npos) {
            hook=HyprlandAPI::createFunctionHook(handle,match.address,reinterpret_cast<void*>(&position));break;
        }
    }
    if(!hook || !hook->hook())throw std::runtime_error("43PR bubble reservation: unsupported target function");
    HyprlandAPI::addLuaFunction(handle,"bubbles","refresh",[](lua_State*){refresh();return 0;});
    // Qt MouseArea does not reliably report a second button during its drag.
    // Publish a read-only native edge; Quickshell ignores it outside bar drags.
    buttonListener=Event::bus()->m_events.input.mouse.button.listen([](IPointer::SButtonEvent event,Event::SCallbackInfo&) {
        if(event.button==BTN_LEFT)leftHeld=event.state==WL_POINTER_BUTTON_STATE_PRESSED;
        if(leftHeld&&event.button==BTN_RIGHT&&event.state==WL_POINTER_BUTTON_STATE_PRESSED)
            g_pEventManager->postEvent({"43pr_bubble_rotate",std::to_string(event.timeMs)});
    });
    return {"43pr-bubble-reserve","Reserve bubble space while keeping the native layout","43PR personal extensions","0.1.0"};
}
APICALL EXPORT void PLUGIN_EXIT(){buttonListener.reset();leftHeld=false;if(hook)hook->unhook();enabled=false;obstacles.clear();refresh();}
