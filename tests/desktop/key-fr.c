#define _GNU_SOURCE
#include <wayland-client.h>
#include <xkbcommon/xkbcommon.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include "virtual-keyboard.h"
static struct zwp_virtual_keyboard_manager_v1 *manager;static struct wl_seat *seat;
static void global(void*d,struct wl_registry*r,uint32_t id,const char*n,uint32_t v){if(!strcmp(n,"zwp_virtual_keyboard_manager_v1"))manager=wl_registry_bind(r,id,&zwp_virtual_keyboard_manager_v1_interface,1);if(!strcmp(n,"wl_seat"))seat=wl_registry_bind(r,id,&wl_seat_interface,1);}
static void gone(void*d,struct wl_registry*r,uint32_t id){}static const struct wl_registry_listener listener={global,gone};
int main(int argc,char**argv){if(argc<3)return 2;int code=atoi(argv[1]),mods=atoi(argv[2]),hold=argc>3?atoi(argv[3]):80;if(code < -1||code>255||mods<0||mods>255||hold<1||hold>5000)return 3;struct wl_display*d=wl_display_connect(0);if(!d)return 4;struct wl_registry*r=wl_display_get_registry(d);wl_registry_add_listener(r,&listener,0);wl_display_roundtrip(d);if(!manager||!seat)return 5;
 struct xkb_context*ctx=xkb_context_new(0);struct xkb_rule_names names={.layout="fr"};struct xkb_keymap*map=xkb_keymap_new_from_names(ctx,&names,0);char*text=xkb_keymap_get_as_string(map,XKB_KEYMAP_FORMAT_TEXT_V1);int fd=memfd_create("43pr-test-clavier-fr",MFD_CLOEXEC);size_t size=strlen(text)+1;if(write(fd,text,size)!=size)return 6;
 struct zwp_virtual_keyboard_v1*k=zwp_virtual_keyboard_manager_v1_create_virtual_keyboard(manager,seat);zwp_virtual_keyboard_v1_keymap(k,WL_KEYBOARD_KEYMAP_FORMAT_XKB_V1,fd,size);wl_display_roundtrip(d);struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);uint32_t ms=t.tv_sec*1000+t.tv_nsec/1000000;
 if(mods&64){zwp_virtual_keyboard_v1_key(k,ms,125,WL_KEYBOARD_KEY_STATE_PRESSED);wl_display_roundtrip(d);}
 zwp_virtual_keyboard_v1_modifiers(k,mods,0,0,0);wl_display_roundtrip(d);usleep(60000);if(code>=0){zwp_virtual_keyboard_v1_key(k,ms,code,WL_KEYBOARD_KEY_STATE_PRESSED);wl_display_roundtrip(d);}usleep(hold*1000);if(code>=0){zwp_virtual_keyboard_v1_key(k,ms+hold,code,WL_KEYBOARD_KEY_STATE_RELEASED);wl_display_roundtrip(d);}if(mods&64){zwp_virtual_keyboard_v1_key(k,ms+hold+1,125,WL_KEYBOARD_KEY_STATE_RELEASED);wl_display_roundtrip(d);}
 zwp_virtual_keyboard_v1_modifiers(k,0,0,0,0);wl_display_roundtrip(d);usleep(60000);zwp_virtual_keyboard_v1_destroy(k);wl_display_flush(d);wl_display_disconnect(d);close(fd);free(text);xkb_keymap_unref(map);xkb_context_unref(ctx);return 0;}
