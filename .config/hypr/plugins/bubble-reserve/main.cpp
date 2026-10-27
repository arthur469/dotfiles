#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/layout/target/WindowTarget.hpp>
#include <hyprland/src/layout/space/Space.hpp>
#include <set>
#include <sstream>
#include <hyprland/src/desktop/view/WLSurface.hpp>
#include <hyprland/src/desktop/view/LayerSurface.hpp>
#include <hyprland/src/managers/SeatManager.hpp>
#include <linux/input-event-codes.h>
#include <hyprland/src/event/EventBus.hpp>
#include <hyprland/src/managers/input/InputManager.hpp>
#include <hyprland/src/managers/EventManager.hpp>
#include <hyprland/src/desktop/state/WindowState.hpp>
#include <hyprland/src/desktop/state/ViewState.hpp>
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
CHyprSignalListener axisListener,moveListener,keyListener;
std::set<uint32_t> swallowedKeys,swallowedButtons;
bool candidate=false,rightSwallowed=false,interactive=true,modal=false,cancelledGesture=false;
Vector2D pressPoint;
uint32_t pressToken=0;
std::vector<BubbleReserve::Rect> inputRegions;
bool leftHeld=false;
using UpdatePosition=void(*)(Layout::CWindowTarget*,uint8_t);
std::filesystem::path statePath;
std::filesystem::file_time_type stateStamp;
std::map<std::string,std::vector<BubbleReserve::Rect>> obstacles;
double margin=0;
bool enabled=false;
uint32_t opacityMods=64;
xkb_keysym_t opacitySymbol=XKB_KEY_o;

void readState() {
    std::error_code error;
    const auto stamp=std::filesystem::last_write_time(statePath,error);
    if(error){enabled=false;obstacles.clear();inputRegions.clear();interactive=false;modal=false;candidate=false;return;}
    if(stamp==stateStamp)return;
    stateStamp=stamp;obstacles.clear();inputRegions.clear();enabled=false;interactive=false;
    if(std::filesystem::file_size(statePath,error)>65536 || error)return;
    std::ifstream input(statePath);
    int active=0;double gap=0;
    if(!(input>>active>>gap) || !std::isfinite(gap) || gap<0 || gap>200)return;
    margin=gap;enabled=active==1;int inputEnabled=1;std::string line;std::getline(input,line);std::istringstream header(line);int modalInput=0;header>>inputEnabled>>modalInput;interactive=inputEnabled==1;modal=modalInput==1;inputRegions.clear();
    uint32_t configuredMods=64;std::string configuredKey="o";header>>configuredMods>>std::quoted(configuredKey);
    const auto symbol=xkb_keysym_from_name(configuredKey.c_str(),XKB_KEYSYM_CASE_INSENSITIVE);
    opacityMods=configuredMods<=127?configuredMods:64;opacitySymbol=symbol==XKB_KEY_NoSymbol?XKB_KEY_o:xkb_keysym_to_lower(symbol);
    size_t count=0;
    while(count++<128 && std::getline(input,line)) {
        std::istringstream row(line);std::string output;BubbleReserve::Rect rect{};
        if(!(row>>std::quoted(output)>>rect.x>>rect.y>>rect.w>>rect.h))continue;
        row>>rect.gapX>>rect.gapY;
        if(std::isfinite(rect.x)&&std::isfinite(rect.y)&&std::isfinite(rect.w)&&std::isfinite(rect.h)&&rect.w>0&&rect.h>0&&rect.w<=20000&&rect.h<=20000) {
            if(!std::isfinite(rect.gapX)||rect.gapX<0||rect.gapX>200)rect.gapX=-1;
            if(!std::isfinite(rect.gapY)||rect.gapY<0||rect.gapY>200)rect.gapY=-1;
            obstacles[output].push_back(rect);if(interactive)inputRegions.push_back(rect);
        }
    }
}
bool modalActive(){return std::any_of(Desktop::viewState()->layers().begin(),Desktop::viewState()->layers().end(),[](const auto& layer){return layer&&layer->m_mapped&&layer->m_namespace=="43pr-module-controls";});}
void position(Layout::CWindowTarget* target,uint8_t flags) {
    readState();
    const auto window=target->window();
    const auto found=window && window->m_monitor ? obstacles.find(window->m_monitor->m_name) : obstacles.end();
    bool reserve=enabled && window && window->m_isMapped && found!=obstacles.end();
    if(reserve) {
        const auto fullscreen=Fullscreen::controller()->getFullscreenModes(window);
        reserve=fullscreen.internal!=Fullscreen::FSMODE_FULLSCREEN && fullscreen.client!=Fullscreen::FSMODE_FULLSCREEN;
    }
    // Compute the native geometry without first configuring an intermediate
    // client size. Steam otherwise reacts to two alternating sizes per pass.
    reinterpret_cast<UpdatePosition>(hook->m_original)(target,reserve?flags|Layout::TARGET_UPDATE_NO_CLIENT_CONFIGURE:flags);
    if(!reserve || !window->m_isMapped)return;
    const auto original=window->geometricBox(Desktop::View::IGeometric::GEOMETRIC_GOAL);
    const auto next=BubbleReserve::project({original.x,original.y,original.w,original.h},found->second,margin,window->getRealBorderSize());
    if(std::abs(next.x-original.x)>=.5||std::abs(next.y-original.y)>=.5||std::abs(next.w-original.w)>=.5||std::abs(next.h-original.h)>=.5) {
        g_pHyprRenderer->damageWindow(window);
        window->setBox({next.x,next.y,next.w,next.h});
        window->updateWindowDecos();
        g_pHyprRenderer->damageWindow(window);
    }
    if(!(flags&Layout::TARGET_UPDATE_NO_CLIENT_CONFIGURE))window->sendWindowSize();
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
    HyprlandAPI::addLuaFunction(handle,"bubbles","inspect_input",[](lua_State*){
        std::ostringstream data;data<<"{\"leftHeld\":"<<leftHeld<<",\"candidate\":"<<candidate<<",\"cancelled\":"<<cancelledGesture<<",\"modal\":"<<modalActive()<<",\"opacityMods\":"<<opacityMods<<",\"opacitySymbol\":"<<opacitySymbol<<"}";
        g_pEventManager->postEvent({"43pr_bubble_diagnostic",data.str()});return 0;
    });
    // Pointer-scoped input routing. Ordinary application input is untouched.
    auto emit=[](const std::string& kind,double value=0) {
        std::ostringstream data;data<<kind<<","<<pressToken<<","<<pressPoint.x<<","<<pressPoint.y<<","<<value;
        g_pEventManager->postEvent({"43pr_bubble_input",data.str()});
    };
    auto hit=[](Vector2D point){const auto focused=g_pSeatManager->m_state.pointerFocus.lock();if(!focused)return false;const auto surface=Desktop::View::CWLSurface::fromResource(focused);const auto layer=surface?Desktop::View::CLayerSurface::fromView(surface->view()):nullptr;return layer&&layer->m_namespace=="43pr-bar";};
    auto inEditor=[](){const auto focused=g_pSeatManager->m_state.pointerFocus.lock();if(!focused)return false;const auto surface=Desktop::View::CWLSurface::fromResource(focused);const auto layer=surface?Desktop::View::CLayerSurface::fromView(surface->view()):nullptr;return layer&&layer->m_namespace=="43pr-module-controls";};
    buttonListener=Event::bus()->m_events.input.mouse.button.listen([emit,hit,inEditor](IPointer::SButtonEvent event,Event::SCallbackInfo& info) {
        readState();if(!g_pInputManager)return;
        if(event.button==BTN_LEFT&&event.state==WL_POINTER_BUTTON_STATE_RELEASED){leftHeld=false;if(candidate||cancelledGesture)emit("release");candidate=false;cancelledGesture=false;}
        if(event.state==WL_POINTER_BUTTON_STATE_RELEASED&&swallowedButtons.erase(event.button)){info.cancelled=true;return;}
        if(modalActive()&&!inEditor()&&event.state==WL_POINTER_BUTTON_STATE_PRESSED){swallowedButtons.insert(event.button);info.cancelled=true;return;}
        if(leftHeld&&(candidate||cancelledGesture)&&event.state==WL_POINTER_BUTTON_STATE_PRESSED&&event.button!=BTN_LEFT&&event.button!=BTN_RIGHT){swallowedButtons.insert(event.button);info.cancelled=true;return;}
        const auto point=g_pInputManager->getMouseCoordsInternal();const auto mods=g_pInputManager->getModsFromAllKBs();
        if(event.button==BTN_LEFT) {
            leftHeld=event.state==WL_POINTER_BUTTON_STATE_PRESSED;
            if(leftHeld){cancelledGesture=false;candidate=hit(point)&&!(mods&64);pressPoint=point;pressToken=event.timeMs;if(candidate)emit("press");}
            else {if(candidate||cancelledGesture)emit("release");candidate=false;cancelledGesture=false;}
        }
        if(event.button==BTN_RIGHT) {
            if(event.state==WL_POINTER_BUTTON_STATE_RELEASED&&rightSwallowed){rightSwallowed=false;info.cancelled=true;return;}
            if(event.state!=WL_POINTER_BUTTON_STATE_PRESSED)return;
            if(leftHeld&&(candidate||cancelledGesture)){if(candidate)emit("rotate");rightSwallowed=true;info.cancelled=true;}
            else if((mods&4)&&hit(point)){pressPoint=point;pressToken=event.timeMs;emit("menu");rightSwallowed=true;info.cancelled=true;}
        }
    });
    axisListener=Event::bus()->m_events.input.mouse.axis.listen([emit,inEditor](IPointer::SAxisEvent event,Event::SCallbackInfo& info) {
        readState();if((modalActive()&&!inEditor())||(leftHeld&&cancelledGesture)){info.cancelled=true;return;}
        if(!leftHeld||!candidate)return;
        // v120 discrete units when available; continuous wheel axis uses15 units/notch.
        if(event.axis==WL_POINTER_AXIS_VERTICAL_SCROLL)emit("wheel",event.deltaDiscrete?-event.deltaDiscrete:-event.delta*8.0);
        info.cancelled=true;
    });
    moveListener=Event::bus()->m_events.input.mouse.move.listen([](Vector2D,Event::SCallbackInfo&) {
        if(!leftHeld||!candidate||!g_pInputManager)return;
        const auto point=g_pInputManager->getMouseCoordsInternal();std::ostringstream data;
        data<<"move,"<<pressToken<<","<<point.x<<","<<point.y<<",0";g_pEventManager->postEvent({"43pr_bubble_input",data.str()});
    });
    keyListener=Event::bus()->m_events.input.keyboard.key.listen([emit,hit](IKeyboard::SKeyEvent event,Event::SCallbackInfo& info) {
        if(event.state==WL_KEYBOARD_KEY_STATE_RELEASED){if(swallowedKeys.erase(event.keycode))info.cancelled=true;return;}
        if(!g_pInputManager)return;
        const auto keyboard=g_pSeatManager->m_keyboard.lock();
        const auto symbol=keyboard&&keyboard->m_xkbState?xkb_keysym_to_lower(xkb_state_key_get_one_sym(keyboard->m_xkbStaticState?keyboard->m_xkbStaticState:keyboard->m_xkbState,event.keycode+8)):XKB_KEY_NoSymbol;
        const bool modifier=symbol==XKB_KEY_Control_L||symbol==XKB_KEY_Control_R||symbol==XKB_KEY_Shift_L||symbol==XKB_KEY_Shift_R||symbol==XKB_KEY_Alt_L||symbol==XKB_KEY_Alt_R||symbol==XKB_KEY_Super_L||symbol==XKB_KEY_Super_R;
        if(leftHeld&&candidate&&(symbol==XKB_KEY_Escape||(symbol==XKB_KEY_NoSymbol&&event.keycode==KEY_ESC))){emit("cancel");candidate=false;cancelledGesture=true;swallowedKeys.insert(event.keycode);info.cancelled=true;return;}
        if(leftHeld&&(candidate||cancelledGesture)){
            if(!modifier){swallowedKeys.insert(event.keycode);info.cancelled=true;return;}
        }
        const auto mods=g_pInputManager->getModsFromAllKBs();
        readState();if(modalActive()&&(mods&(64u|8u))&&!modifier){swallowedKeys.insert(event.keycode);info.cancelled=true;return;}
        if((mods&~(2u|16u))!=opacityMods&&(mods&~(2u|16u))!=(opacityMods|1u))return;
        if(symbol!=opacitySymbol)return;
        readState();const auto point=g_pInputManager->getMouseCoordsInternal();if(!hit(point))return;
        if(leftHeld&&candidate){info.cancelled=true;swallowedKeys.insert(event.keycode);return;}
        pressPoint=point;pressToken=event.timeMs;emit((mods&1)?"opacity-target":"opacity-all");
        swallowedKeys.insert(event.keycode);info.cancelled=true;
    });
    return {"43pr-bubble-reserve","Reserve bubble space while keeping the native layout","43PR personal extensions","0.3.0"};
}
APICALL EXPORT void PLUGIN_EXIT(){keyListener.reset();moveListener.reset();axisListener.reset();buttonListener.reset();candidate=false;swallowedKeys.clear();swallowedButtons.clear();leftHeld=false;if(hook)hook->unhook();enabled=false;obstacles.clear();refresh();}
