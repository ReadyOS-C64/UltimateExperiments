#include "setup_ui_run.h"
#include "setup_select.h"
#include "selection_capsule.h"
#include "source_load.h"
#include "setup_overlay.h"
#include "bulk_context.h"
#include "platform.h"
#include "setup_io.h"
#include <string.h>
#ifndef DOS64_SETUP_RELEASE_PREFLIGHT
#define DOS64_SETUP_RELEASE_PREFLIGHT 0
#endif
#if DOS64_SETUP_RELEASE_PREFLIGHT
#define SU_SOURCE_COUNT 8u
#else
#define SU_SOURCE_COUNT 5u
#endif
br_u16 su_timeout;
static br_u16 timeout,ticket;
static br_u8 state,error,phase,kind,drain;
static void first(br_u8 e){if(!error)error=e;}
static void failed(void){phase=5;}
#if DOS64_SETUP_RELEASE_PREFLIGHT
static void caption(void){br_u8 i;const char*p=kind<3u?"Loading DOS ":kind==3u?"Checking START.TPL":kind==4u?"Checking START.REL":kind==5u?"Checking DOS64.PRG":kind==6u?"Checking DOS64.REL":"Checking START.INO";
 ps_row=20;ps_color=1;for(i=0;i<40u;++i){ps_col=i;ps_ascii=*p?*p++:' ';ps_put();}if(kind<3u){ps_col=12;ps_ascii='1'+kind;ps_put();}}
#else
static void caption(void){const char*p=kind<3u?"Loading DOS ":kind==3u?"Loading START":"Loading info ";
 ps_row=24;ps_col=0;ps_color=1;while(*p){ps_ascii=*p++;ps_put();++ps_col;}if(kind<3u){ps_ascii='1'+kind;ps_put();}}
#endif
br_u8 su_begin(void){
 if(state||!su_timeout||su_timeout>=0x8000u)return 0;
 ticket=so_ui_ticket();if(!ticket)return 0;ns_io_owner=0xa5;ns_capacity=so_capacity();timeout=su_timeout;state=SU_BUSY;
 if(!ss_begin(0xa5,timeout)){first(SU_SELECT|ss_error_code());failed();return 1;}return 1;
}
void su_poll(void){br_u8 s;
 if(state!=SU_BUSY)return;
 switch(phase){
 case 0:s=ss_poll();if(ss_error_code())first(SU_SELECT|ss_error_code());if(s==SS_BUSY)return;if(s!=SS_DONE){failed();break;}phase=1;break;
 case 1:if(!sq_publish()){first(SU_CAPSULE|sq_error());failed();break;}phase=2;break;
 case 2:caption();sl_kind=kind;sl_timeout=timeout;if(!sl_begin()){s=sq_error();first(s?(SU_CAPSULE|s):(SU_SOURCE|sl_error()));failed();break;}phase=3;break;
 case 3:sl_poll();s=sl_state();if(sl_error())first(SU_SOURCE|sl_error());if(s==SL_BUSY)return;if(s!=SL_DONE){failed();break;}if(++kind==SU_SOURCE_COUNT)phase=4;else phase=2;break;
 case 4:sq_page=0;if(so_ui_ticket()!=ticket||sq_read()!=512u){first(SU_CAPSULE|sq_error());failed();break;}memcpy(so_request.home,sq_bytes+SQ_HOME,128);state=SU_DONE;break;
 case 5:if(bc_files_closed()){state=SU_FAILED;break;}memset(&br_request,0,sizeof(br_request));br_request.op=BR_CLOSE;bc_slot=0;br_now=ps_ticks;if(!bc_start()){state=SU_FAILED;break;}phase=6;drain=0;break;
 case 6:if(ps_clock_poll())br_now=ps_ticks;bc_slot=0;bc_poll();if(br_result.state!=BR_BUSY||++drain==0)state=SU_FAILED;break;
 }
}
br_u8 su_state(void){return state;}
br_u8 su_error(void){return error;}
br_u8 su_closed_quiet(void){return state!=SU_BUSY&&bc_files_closed();}
