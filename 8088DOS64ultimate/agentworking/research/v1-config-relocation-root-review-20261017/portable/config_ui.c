#include "config_ui.h"
#include "existing_cfg.h"
#include "directory_browser.h"
#include "bulk_context.h"
#include "startup_close.h"
#include "platform.h"
#include "install_config.h"
#include <string.h>
struct cg_request_t cg_request;
struct cg_result_t cg_result;
struct cg_receipt_t cg_receipt;
static struct cg_receipt_t committed;
static char current[128];
static br_u32 resource_capacity;
static br_u16 timeout,now,last,began,steps,drain,view;
static br_u8 booted,state,error,leaf,stage,row,columns,loading,dirty,cancelled,clock_bad;
const br_u16 cg_abi_sizes[]={sizeof(struct cg_request_t),sizeof(struct cg_result_t),sizeof(struct cg_receipt_t)};
static br_u32 wide(const br_u8*p){return (br_u32)p[0]|((br_u32)p[1]<<8)|((br_u32)p[2]<<16)|((br_u32)p[3]<<24);}
static br_u8 closed(void){return sc_ready()&&bc_files_closed();}
static void publish(void){cg_result.state=state;cg_result.error=error;cg_result.leaf=leaf;cg_result.cleanup=!closed();cg_result.stage=stage;cg_result.row=row;cg_result.columns=columns;cg_result.ready=state==CG_DONE&&!error?0xa5:0;}
static void first(br_u8 e,br_u8 l){if(!error){error=e;leaf=l;}}
static void sample(void){if(!ps_clock_poll())clock_bad=1;else{now=ps_ticks;if((br_u16)(now-last)>=0x8000u)clock_bad=1;last=now;}}
static br_u8 pending(void){return state==CG_STARTUP||state==CG_INSPECT||(state==CG_BROWSER&&loading);}
static void stop(br_u8 e){
 first(e,0);if(cancelled)return;cancelled=1;
 if(state==CG_STARTUP)sc_cancel();else if(state==CG_INSPECT
#if DOS64_CONFIG_RELOCATION
||state==CG_RELOCATE
#endif
)ri_cancel();else if(state==CG_BROWSER&&loading)db_cancel();
}
static void failed(void){state=CG_FAILED;dirty=1;}
static br_u8 checked_ri(void){
 ri_query_session=committed.session;memcpy(ri_query_home,committed.home,128);
 return ri_get()&&ri_receipt.identity==committed.cfg_identity;
}
#if DOS64_CONFIG_RELOCATION
extern br_u8 __fastcall__ cg_same_path(const char*a,const char*b);
#define same cg_same_path
#else
static br_u8 same(const char*a,const char*b){br_u8 i,x,y;for(i=0;i<128;i++){x=a[i];y=b[i];if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return 0;if(!x)return 1;}return 1;}
#endif
static void refresh(br_u16 first_row){
 memset(&db_request,0,sizeof(db_request));db_request.owner=0xa5;db_request.target=1;db_request.folders_only=1;
 db_request.first=first_row;db_request.timeout=timeout;memcpy(db_request.path,current,128);db_now=now;
 if(!db_begin()){first(CG_DIRECTORY,db_result.rejected);failed();return;}
 loading=dirty=1;row=0;view=0;began=now;steps=0;
}
static void browse(br_u8 which){stage=which;state=CG_BROWSER;memset(current,0,128);current[0]='/';refresh(0);}
static br_u8 page_ready(void){return !loading&&db_state()==DB_DONE&&!db_error()&&closed()&&!memcmp(db_page->path,current,128);}
static void text(br_u8 y,br_u8 x,const char*s){ps_row=y;ps_col=x;ps_color=1;while(*s&&ps_col<40){ps_ascii=(br_u8)*s++;ps_put();++ps_col;}}
static br_u8 escaped(br_u8 c){return c<32||c>126||c=='%'||c=='_'||c=='`'||c=='{'||c=='}'||c=='~'||c=='^'||c=='\\'||c=='|';}
static void encoded(br_u8 y,br_u8 x,const char*s,br_u16 skip,br_u8 width){
 static const char hex[]="0123456789ABCDEF";br_u8 c,i,n,out;br_u16 position=0;
 ps_row=y;ps_col=x;ps_color=1;while(*s&&ps_col<x+width){c=(br_u8)*s++;n=escaped(c)?3:1;for(i=0;i<n&&ps_col<x+width;i++){out=n==1?c:(i==0?'%':hex[i==1?c>>4:c&15]);if(position++>=skip){ps_ascii=out;ps_put();++ps_col;}}}
}
static const char* detail(void){
 if(state==CG_REVIEW){if(row==0)return committed.home;if(row==1)return committed.release_home;return committed.new_home;}
 if(state==CG_BROWSER&&page_ready()&&row<db_page->count&&db_select(row))return db_selected_path;
 return current;
}
#if DOS64_CONFIG_RELOCATION
#pragma code-name(push,"RI_CODE")
#pragma rodata-name(push,"RI_RO")
static const char rel_text0[]="Installation folder has moved.";
static const char rel_text1[]="Saved folder:";
static const char rel_text2[]="Selected folder:";
static const char rel_text3[]="Move A/B/C paths inside saved folder?";
static const char rel_text4[]="Shared external paths stay unchanged.";
static const char rel_text5[]="Y: confirm   Run/Stop: cancel";
static void relocation_render(void){
 text(2,0,rel_text0);text(4,0,rel_text1);encoded(5,0,ri_receipt.home,view,40);
 text(8,0,rel_text2);encoded(9,0,committed.home,view,40);
 text(12,0,rel_text3);text(14,0,rel_text4);text(17,0,rel_text5);
}
#pragma rodata-name(pop)
#pragma code-name(pop)
#endif
static void render(void){
 br_u8 i;ps_color=1;ps_clear();text(0,0,"DOS64 CONFIG");
 if(state==CG_FAILED){text(3,0,"Configuration stopped safely");text(5,0,"No files have been written.");text(7,0,closed()?"Files closed. Restart CONFIG to retry.":"File ownership unknown. Restart machine.");return;}
 if(state==CG_DONE){text(3,0,"Choices ready for new launch generation");text(5,0,"No files have been written yet.");text(7,0,"Existing media references are preserved.");return;}
 if(state==CG_STARTUP){text(3,0,"Closing previous firmware file handles");return;}
 if(state==CG_INSPECT){text(3,0,"Checking original DOS64.CFG read-only");return;}
#if DOS64_CONFIG_RELOCATION
 if(state==CG_RELOCATE){relocation_render();}
 else
#endif
 if(state==CG_OPTIONS){text(2,0,"New initial DOS text columns");text(5,0,columns==40?"> 40 columns":"  40 columns");text(7,0,columns==80?"> 80 columns":"  80 columns");text(10,0,"New setting; old INI is unchanged.");text(12,0,"Up/down: select   Return: continue");}
 else if(state==CG_REVIEW){
  text(2,0,"Review new launch generation");text(4,0,row==0?"> Original configuration":"  Original configuration");encoded(5,0,committed.home,view,40);
  text(8,0,row==1?"> Matched release source folder":"  Matched release source folder");encoded(9,0,committed.release_home,view,40);
  text(12,0,row==2?"> New launch folder":"  New launch folder");encoded(13,0,committed.new_home,view,40);
  text(16,0,columns==40?"New initial columns: 40":"New initial columns: 80");text(18,0,"Existing A/B/C paths and flags retained.");
  text(19,0,"Writable media stay shared with old START");text(21,0,"Return: prepare choices for publication");
 }else if(state==CG_BROWSER){
  text(2,0,stage==0?"Choose existing installation folder":(stage==1?"Choose matching release source folder":"Choose a new launch folder"));encoded(3,0,current,0,40);
  if(loading)text(5,0,"Reading folder...");else for(i=0;i<db_page->count;i++){text(5+i,0,i==row?">/":" /");encoded(5+i,2,(const char*)(db_page->rows[i].usable?db_page->rows[i].raw:db_page->rows[i].display),0,38);}
  text(18,0,"Return: open   Delete: parent   F1: use");text(19,0,"F3: previous page   F5: next page");
 }
 text(22,0,"Left/right: path   Run/Stop: cancel");encoded(24,0,detail(),view,40);
}
static void use_folder(void){
 if(!page_ready())return;
 /* Successful private directory job binds current; never accept public result. */
 if(stage==0){
  memcpy(committed.home,current,128);memset(&ri_request,0,sizeof(ri_request));ri_request.owner=0xa5;ri_request.capacity=resource_capacity;ri_request.timeout=timeout;memcpy(ri_request.home,current,128);
  if(!ri_begin()){first(CG_OWNERSHIP,0);failed();return;}state=CG_INSPECT;began=now;steps=0;dirty=1;
 }else if(stage==1){memcpy(committed.release_home,current,128);browse(2);}
 else if(!current[1]||strlen(current)>117u){text(20,0,"New folder must be 2..117 characters.");}
 else if(!same(current,committed.home)&&!same(current,committed.release_home)){
  memcpy(committed.new_home,current,128);state=CG_REVIEW;row=0;view=0;dirty=1;
 }else text(20,0,"Choose a different new launch folder.");
}
br_u8 cg_boot(void){if(booted)return 0;booted=1;bc_init();ps_init();return 1;}
br_u8 cg_begin(void){
 if(!booted||state!=CG_IDLE||cg_request.owner!=0xa5||!cg_request.timeout||cg_request.timeout>=0x8000u||cg_request.capacity<0x400000UL||cg_request.capacity>0x1000000UL||(cg_request.capacity&0xffffUL)||!bc_files_closed())return 0;
 if(!ps_clock_poll())return 0;now=last=ps_ticks;began=now;resource_capacity=cg_request.capacity;timeout=cg_request.timeout;columns=80;
 sc_now=now;if(!sc_begin(0xa5))return 0;state=CG_STARTUP;dirty=1;publish();return 1;
}
void cg_default_start(void){if(!cg_boot())return;cg_request.owner=0xa5;cg_request.capacity=0x400000UL;cg_request.timeout=1000;cg_begin();}
void cg_cancel(void){if(state&&state!=CG_DONE&&state!=CG_FAILED)stop(CG_CANCEL);publish();}
void cg_poll(void){
 br_u8 s=0,key=0,e=0;
 if(state==CG_DONE||state==CG_FAILED||state==CG_IDLE){publish();return;}
 sample();
 if(state==CG_STARTUP){sc_now=now;s=sc_poll();if(sc_error)first(CG_OWNERSHIP,sc_error);}
 else if(state==CG_BROWSER&&loading){db_now=now;db_poll();s=db_state();e=db_error();if(e)first(CG_DIRECTORY,e);}
 else if(state==CG_INSPECT
#if DOS64_CONFIG_RELOCATION
||state==CG_RELOCATE
#endif
){ri_poll();s=ri_state();e=ri_error();if(e)first(e==RI_CANCEL?CG_CANCEL:(e==RI_CLOCK?CG_CLOCK:(e==RI_TIMEOUT?CG_TIMEOUT:CG_CONFIG)),e);}
 /* The native leaf is observed before same-poll keyboard or clock causes. */
 if(ps_key_poll())key=ps_key;if(key==27)stop(CG_CANCEL);if(clock_bad)stop(CG_CLOCK);
 if(pending()){
  if(++steps==0)stop(CG_LIMIT);
  if((br_u16)(now-began)>=timeout)stop(CG_TIMEOUT);
  if(error&&++drain>=256u){failed();goto done;}
 }
 if(state==CG_STARTUP&&s!=SC_BUSY){
  if(error||s!=SC_DONE||!sc_ready()){first(CG_OWNERSHIP,sc_error);failed();}
  else if(!ri_attach()){first(CG_OWNERSHIP,0);failed();}else browse(0);
 }else if(state==CG_BROWSER&&loading&&s!=DB_BUSY){loading=0;if(error||s!=DB_DONE){first(CG_DIRECTORY,e);failed();}dirty=1;}
#if DOS64_CONFIG_RELOCATION
 else if(state==CG_INSPECT&&s==RI_CONFIRM){if(!ri_pending()){first(CG_OWNERSHIP,0);failed();}else{state=CG_RELOCATE;dirty=1;}}
 else if(state==CG_RELOCATE&&s==RI_CONFIRM&&key=='y'){if(ri_confirm()){state=CG_INSPECT;s=RI_DONE;}else{first(CG_CONFIG,ri_error());failed();}}
#endif
#if DOS64_CONFIG_RELOCATION
 if(state==CG_INSPECT&&s!=RI_BUSY&&s!=RI_CONFIRM){
#else
 else if(state==CG_INSPECT&&s!=RI_BUSY){
#endif
  if(error||s!=RI_DONE){first(CG_CONFIG,e);failed();}
  else {ri_query_session=ri_result.session;memcpy(ri_query_home,committed.home,128);if(!ri_get()){first(CG_OWNERSHIP,0);failed();}
   else {committed.session=ri_receipt.session;committed.cfg_identity=ri_receipt.identity;committed.capacity=wide(ri_receipt.bytes+538);state=CG_OPTIONS;dirty=1;}}
 }
 if(error){if(!pending())failed();goto done;}
 if(state==CG_BROWSER&&!loading&&page_ready()){
  if(key==PS_F1)use_folder();
  else if(key==13&&row<db_page->count&&db_select(row)){memcpy(current,db_selected_path,128);refresh(0);}
  else if(key==PS_DELETE&&db_parent()){memcpy(current,db_selected_path,128);refresh(0);}
  else if(key==PS_DOWN&&row+1<db_page->count){++row;view=0;dirty=1;}
  else if(key==PS_UP&&row){--row;view=0;dirty=1;}
  else if(key==PS_F1+2&&db_page->previous)refresh(db_page->first>=12?db_page->first-12:0);
  else if(key==PS_F1+4&&db_page->next)refresh(db_page->first+12);
 }else if(state==CG_OPTIONS){
  if(key==PS_UP){columns=40;dirty=1;}else if(key==PS_DOWN){columns=80;dirty=1;}else if(key==13)browse(1);
 }else if(state==CG_REVIEW){
  if(key==PS_UP&&row){--row;view=0;dirty=1;}else if(key==PS_DOWN&&row<2){++row;view=0;dirty=1;}
  else if(key==13){
   if(!checked_ri()){first(CG_OWNERSHIP,0);failed();}
   else {committed.columns=columns;committed.ini_length=32;memcpy(committed.ini,"[emulator]\r\ninitial_columns=80\r\n",32);if(columns==40)committed.ini[28]='4';
    sample();if(ps_key_poll()&&ps_key==27)stop(CG_CANCEL);if(clock_bad)stop(CG_CLOCK);if(error)failed();else{state=CG_DONE;dirty=1;}}
  }
 }
 if(key==PS_LEFT&&view){--view;dirty=1;}else if(key==PS_RIGHT&&view<380){++view;dirty=1;}
done:
 if(dirty){render();dirty=0;}publish();
}
br_u8 cg_state(void){publish();return state;}
br_u8 cg_error(void){publish();return error;}
br_u8 cg_closed_quiet(void){return !pending()&&closed();}
br_u8 cg_get(void){if(state!=CG_DONE||error||!closed()||!checked_ri())return 0;cg_receipt=committed;return 1;}
