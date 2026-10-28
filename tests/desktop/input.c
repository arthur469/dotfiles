#include <wayland-client.h>
#include <linux/input-event-codes.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include "pointer.h"
static struct zwlr_virtual_pointer_manager_v1 *manager;
static int testWidth=0,testHeight=0;
static uint32_t nowms(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1000+t.tv_nsec/1000000;}
static void global(void *d,struct wl_registry *r,uint32_t n,const char *s,uint32_t v) {
 if(!strcmp(s,"zwlr_virtual_pointer_manager_v1")) manager=wl_registry_bind(r,n,&zwlr_virtual_pointer_manager_v1_interface,v<2?v:2);
}
static void gone(void*d,struct wl_registry*r,uint32_t n){}
static const struct wl_registry_listener listener={global,gone};
static void motion(struct wl_display*d,struct zwlr_virtual_pointer_v1*p,int x,int y,int ms){
 zwlr_virtual_pointer_v1_motion_absolute(p,nowms(),x,y,testWidth,testHeight);zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);
}
int main(int argc,char **argv){
 const char *tw=getenv("43PR_TEST_WIDTH"),*th=getenv("43PR_TEST_HEIGHT");if(tw)testWidth=atoi(tw);if(th)testHeight=atoi(th);
 if(argc<4||testWidth<=0||testHeight<=0)return 2;int x=atoi(argv[1]),y=atoi(argv[2]);char*mode=argv[3];
 if(x<0||x>=testWidth||y<0||y>=testHeight)return 3;
 struct wl_display*d=wl_display_connect(NULL);if(!d)return 4;
 struct wl_registry*r=wl_display_get_registry(d);wl_registry_add_listener(r,&listener,NULL);wl_display_roundtrip(d);if(!manager)return 5;
 struct zwlr_virtual_pointer_v1*p=zwlr_virtual_pointer_manager_v1_create_virtual_pointer(manager,NULL);
 struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);uint32_t ms=t.tv_sec*1000+t.tv_nsec/1000000;
 motion(d,p,x,y,ms);usleep(100000);
 if(!strcmp(mode,"wheel")){
  int delta=argc>4?atoi(argv[4]):15;
  zwlr_virtual_pointer_v1_axis_source(p,WL_POINTER_AXIS_SOURCE_WHEEL);
  zwlr_virtual_pointer_v1_axis(p,nowms(),WL_POINTER_AXIS_VERTICAL_SCROLL,wl_fixed_from_int(delta));
  zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);
 }else if(strcmp(mode,"move")){
  zwlr_virtual_pointer_v1_button(p,nowms(),(!strcmp(mode,"right")?BTN_RIGHT:BTN_LEFT),WL_POINTER_BUTTON_STATE_PRESSED);zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);
  if(!strcmp(mode,"rotate")){usleep(650000);zwlr_virtual_pointer_v1_button(p,nowms(),BTN_RIGHT,WL_POINTER_BUTTON_STATE_PRESSED);zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);usleep(80000);zwlr_virtual_pointer_v1_button(p,nowms(),BTN_RIGHT,WL_POINTER_BUTTON_STATE_RELEASED);zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);usleep(100000);}
  else if(!strcmp(mode,"outwheel")&&argc==6){int tx=atoi(argv[4]),ty=atoi(argv[5]);usleep(650000);zwlr_virtual_pointer_v1_axis_source(p,WL_POINTER_AXIS_SOURCE_WHEEL);zwlr_virtual_pointer_v1_axis(p,nowms(),WL_POINTER_AXIS_VERTICAL_SCROLL,wl_fixed_from_int(15));zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);usleep(180000);motion(d,p,tx,ty,ms+1000);usleep(200000);zwlr_virtual_pointer_v1_axis(p,nowms(),WL_POINTER_AXIS_VERTICAL_SCROLL,wl_fixed_from_int(15));zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);usleep(200000);}
  else if((!strcmp(mode,"drag")||!strcmp(mode,"dragrotate")||!strcmp(mode,"dragwait"))&&argc==6){int tx=atoi(argv[4]),ty=atoi(argv[5]);if(tx<0||tx>=testWidth||ty<0||ty>=testHeight)return 3;usleep(650000);for(int i=1;i<=20;i++){motion(d,p,x+(tx-x)*i/20,y+(ty-y)*i/20,ms+750+i*20);usleep(20000);if(i==10&&!strcmp(mode,"dragrotate")){zwlr_virtual_pointer_v1_button(p,nowms(),BTN_RIGHT,WL_POINTER_BUTTON_STATE_PRESSED);zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);usleep(50000);zwlr_virtual_pointer_v1_button(p,nowms(),BTN_RIGHT,WL_POINTER_BUTTON_STATE_RELEASED);zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);}}}
  else {usleep((!strcmp(mode,"hold")||!strcmp(mode,"holdwheel")||!strcmp(mode,"holdwheelwait"))?650000:60000);if(!strcmp(mode,"holdwheel")||!strcmp(mode,"holdwheelwait")||!strcmp(mode,"quickwheel")){zwlr_virtual_pointer_v1_axis_source(p,WL_POINTER_AXIS_SOURCE_WHEEL);zwlr_virtual_pointer_v1_axis(p,nowms(),WL_POINTER_AXIS_VERTICAL_SCROLL,wl_fixed_from_int(argc>4?atoi(argv[4]):15));zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);usleep(!strcmp(mode,"holdwheelwait")?1200000:100000);}}
  if(!strcmp(mode,"dragwait"))usleep(450000);
  zwlr_virtual_pointer_v1_button(p,nowms(),(!strcmp(mode,"right")?BTN_RIGHT:BTN_LEFT),WL_POINTER_BUTTON_STATE_RELEASED);zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);
 }
 usleep(100000);zwlr_virtual_pointer_v1_destroy(p);zwlr_virtual_pointer_manager_v1_destroy(manager);wl_registry_destroy(r);wl_display_flush(d);wl_display_disconnect(d);return 0;
}
