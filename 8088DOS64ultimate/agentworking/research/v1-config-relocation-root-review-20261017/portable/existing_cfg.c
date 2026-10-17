#include "existing_cfg.h"
#include "bulk_context.h"
#include "bulk_uci.h"
#include "startup_close.h"
#include "platform.h"
#include "install_config.h"
#include <string.h>
#define STARTUP 1
#define OPEN 2
#define INFO 3
#define READ 4
#define EOF_READ 5
#define CLOSE 6
struct ri_request_t ri_request;
struct ri_result_t ri_result;
struct ri_receipt_t ri_receipt;
char ri_query_home[128];
br_u16 ri_query_session;
static struct ri_receipt_t committed;
static char home[128],path[128];
static br_u16 timeout,now,began,last,steps,bad_polls,copied,wanted,session;
static br_u8 booted,state,error,phase,leaf,transport,waiting,cancelled,clock_bad,close_attempt;
static br_u32 capacity;
#if DOS64_CONFIG_RELOCATION
br_u32 ri_original_identity;
static br_u32 original_identity;
#endif
static void publish(void){ri_result.state=state;ri_result.error=error;ri_result.phase=phase;ri_result.leaf=leaf;ri_result.transport=transport;ri_result.cleanup=state==RI_BUSY||!sc_ready()||!bc_files_closed();ri_result.session=session;}
static void first(br_u8 e){if(!error)error=e;}
static br_u8 closed(void){return sc_ready()&&bc_files_closed();}
static void fail(void){state=RI_FAILED;}
static void sample(void){if(!ps_clock_poll())clock_bad=1;else{now=ps_ticks;if((br_u16)(now-last)>=0x8000u)clock_bad=1;last=now;}}
static br_u8 eof(void){return phase==EOF_READ&&br_result.state==BR_FAILED&&br_result.error==BR_COUNT&&br_result.known&&!br_result.actual&&!br_result.transport&&br_result.handle==1;}
static void stop(br_u8 e){first(e);if(cancelled)return;cancelled=1;if(phase==STARTUP)sc_cancel();else if(waiting&&phase!=CLOSE){br_now=now;bc_cancel();}}
static br_u8 operation(br_u8 p,br_u8 op){
 memset(&br_request,0,sizeof(br_request));br_request.op=op;br_request.mode=1;
 if(op==BR_OPEN)memcpy(br_request.path,path,128);
 if(op==BR_READ){br_request.length=wanted;memset(uci_data,0xa7,512);}
 bc_slot=0;br_now=now;phase=p;began=now;steps=0;
 if(!bc_start()){if(!error){leaf=br_result.error?br_result.error:br_result.rejected;transport=br_result.transport;}first(RI_FILE);return 0;}
 waiting=1;return 1;
}
static void cleanup(void){
 if(waiting)return;
 if(bc_files_closed()){fail();return;}
 if(!close_attempt){close_attempt=1;if(operation(CLOSE,BR_CLOSE))return;}
 fail();
}
br_u8 ri_boot(void){
#if DOS64_CONFIG_ATTACHED
 return 0;
#else
 if(booted)return 0;booted=1;bc_init();ps_init();return 1;
#endif
}
#if DOS64_CONFIG_ATTACHED
br_u8 ri_attach(void){if(booted||state!=RI_IDLE||!sc_ready()||!bc_files_closed())return 0;booted=2;return 1;}
#endif
br_u8 ri_begin(void){br_u16 n;
 if(!booted||state!=RI_IDLE||ri_request.owner!=0xa5||!ri_request.timeout||ri_request.timeout>=0x8000u||ri_request.capacity<0x400000UL||ri_request.capacity>0x1000000UL||(ri_request.capacity&0xffffUL))return 0;
 memcpy(d64_path_source,ri_request.home,128);memset(d64_path_relative,0,128);strcpy(d64_path_relative,"DOS64.CFG");
 if(!d64_path_join())return 0;
 n=(br_u16)strlen(ri_request.home);for(++n;n<128;++n)if(ri_request.home[n])return 0;
 if(!bc_files_closed())return 0;
#if DOS64_CONFIG_ATTACHED
 if(!sc_ready())return 0;
#endif
 memcpy(home,ri_request.home,128);memcpy(path,d64_path_output,128);capacity=ri_request.capacity;timeout=ri_request.timeout;
 if(!ps_clock_poll())return 0;now=last=ps_ticks;began=now;
#if DOS64_CONFIG_ATTACHED
 ++session;state=RI_BUSY;bc_config[0].owner=0xa5;bc_config[0].target=1;bc_config[0].capacity=capacity;memcpy(bc_config[0].root,home,128);
 if(!operation(OPEN,BR_OPEN))cleanup();publish();return 1;
#else
 sc_now=now;if(!sc_begin(0xa5))return 0;
 ++session;state=RI_BUSY;phase=STARTUP;publish();return 1;
#endif
}
void ri_cancel(void){if(state==RI_BUSY
#if DOS64_CONFIG_RELOCATION
||state==RI_CONFIRM
#endif
){stop(RI_CANCEL);
#if DOS64_CONFIG_RELOCATION
if(state==RI_CONFIRM)fail();
#endif
}publish();}
void ri_poll(void){br_u8 s,expected;
#if DOS64_CONFIG_RELOCATION
 if(state==RI_CONFIRM){sample();if(clock_bad)stop(RI_CLOCK);if(error)fail();publish();return;}
#endif
 if(state!=RI_BUSY){publish();return;}
 sample();
 if(++steps==0){first(RI_LIMIT);fail();publish();return;}
 if(phase==STARTUP){
  sc_now=now;s=sc_poll();if(sc_error&&!error){leaf=sc_error;transport=sc_transport;first(RI_STARTUP);}
 }else if(waiting){
  br_now=now;bc_slot=0;bc_poll();expected=eof();
  if(br_result.error&&!expected){if(!error){leaf=br_result.error;transport=br_result.transport;}first(RI_FILE);}
  if(br_result.state!=BR_BUSY){waiting=0;if(phase==EOF_READ){if(!expected)first(RI_FILE);}else if(br_result.state!=BR_DONE||br_result.error)first(RI_FILE);}
 }
 /* First native leaf observation dominates same-poll RunStop/clock. */
 if(ps_key_poll()&&ps_key==27)stop(RI_CANCEL);
 if(clock_bad)stop(RI_CLOCK);
 if((br_u16)(now-began)>=timeout)stop(RI_TIMEOUT);
 if(clock_bad&&++bad_polls>=256u){first(RI_CLOCK);fail();publish();return;}
 if(phase==STARTUP){
  if(s==SC_BUSY){publish();return;}
  if(s!=SC_DONE||!sc_ready()){first(RI_STARTUP);fail();}
  else if(error)fail();
  else {bc_config[0].owner=0xa5;bc_config[0].target=1;bc_config[0].capacity=capacity;memcpy(bc_config[0].root,home,128);if(!operation(OPEN,BR_OPEN))cleanup();}
 }else if(error){cleanup();}
 else if(!waiting){
  if(phase==OPEN){if(!operation(INFO,BR_INFO))cleanup();}
  else if(phase==INFO){if(!br_result.known||br_result.size!=576UL){first(RI_SIZE);cleanup();}else{wanted=256;if(!operation(READ,BR_READ))cleanup();}}
  else if(phase==READ){
   if(!br_result.known||br_result.actual!=wanted||uci_data_len!=wanted){first(RI_FILE);cleanup();}
   else {memcpy(committed.bytes+copied,uci_data,wanted);copied+=wanted;if(copied<576u){wanted=576u-copied;if(wanted>256u)wanted=256u;if(!operation(READ,BR_READ))cleanup();}else{wanted=1;if(!operation(EOF_READ,BR_READ))cleanup();}}
  }else if(phase==EOF_READ){close_attempt=1;if(!operation(CLOSE,BR_CLOSE))cleanup();}
  else if(phase==CLOSE){
   if(!closed()){first(RI_FILE);fail();}
   else if((
#if D64_CONFIG_INPLACE
   d64_cfg_input=committed.bytes,
#else
   memcpy(d64_cfg_input,committed.bytes,576),
#endif
   !d64_config_validate())){first(RI_CONFIG);fail();}
#if !DOS64_CONFIG_RELOCATION
   else if(memcmp(committed.bytes+8,home,128)){first(RI_HOME);fail();}
#endif
   else {
    /* Validation/copy can span new keyboard/clock input. Settle a fresh
     * terminal fence before publishing any successful receipt authority. */
    sample();if(ps_key_poll()&&ps_key==27)stop(RI_CANCEL);
    if(clock_bad)stop(RI_CLOCK);
    if((br_u16)(now-began)>=timeout)stop(RI_TIMEOUT);
    if(error)fail();
    else {committed.session=session;memcpy(&committed.identity,committed.bytes+572,4);memcpy(committed.home,home,128);state=RI_DONE;
#if DOS64_CONFIG_RELOCATION
     original_identity=committed.identity;
     if(memcmp(committed.bytes+8,home,128)){memcpy(committed.home,committed.bytes+8,128);state=RI_CONFIRM;}
#endif
}
   }
  }
 }
 publish();
}
br_u8 ri_state(void){publish();return state;}
br_u8 ri_error(void){publish();return error;}
br_u8 ri_closed_quiet(void){return state!=RI_BUSY&&closed();}
br_u8 ri_get(void){if(state!=RI_DONE||error||session!=ri_query_session||memcmp(home,ri_query_home,128)||!closed())return 0;ri_receipt=committed;
#if DOS64_CONFIG_RELOCATION
memcpy(ri_receipt.home,home,128);
#endif
return 1;}

#if DOS64_CONFIG_RELOCATION
br_u8 ri_pending(void){if(state!=RI_CONFIRM||error||!closed())return 0;ri_receipt=committed;ri_original_identity=original_identity;return 1;}
br_u8 ri_confirm(void){
 if(!ri_pending())return 0;
 sample();if(ps_key_poll()&&ps_key==27)stop(RI_CANCEL);if(clock_bad)stop(RI_CLOCK);
 if(error){fail();return 0;}
 d64_cfg_input=committed.bytes;memcpy(d64_path_source,home,128);
 if(!d64_config_rebase()){first(RI_CONFIG);fail();return 0;}

 sample();if(ps_key_poll()&&ps_key==27)stop(RI_CANCEL);if(clock_bad)stop(RI_CLOCK);
 if(error){fail();return 0;}
 memcpy(&committed.identity,committed.bytes+572,4);state=RI_DONE;return 1;
}
#endif
