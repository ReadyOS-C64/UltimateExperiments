#pragma code-name("PRELAUNCH")
#pragma rodata-name("PRELAUNCH_RO")
#include "ini_io.h"
#include "ini_parser.h"
#include "bulk_uci.h"
#include "platform.h"
#include <string.h>
extern br_u8 files_handle,files_error;
br_u16 ii_now;
br_u8 ii_error_observed,ii_parser_observed;
br_u16 ii_line_observed;
static struct br_result_t leaf;
static char path[128];
static br_u16 size,position,wanted,drain_steps;
static br_u8 first_op,first_leaf,first_transport;
static br_u8 state,error,phase,waiting,missing,cancelled,clock_failed,cleanup,committed;
#define OPEN 1u
#define INFO 2u
#define READ 3u
#define EOFREAD 4u
#define CLOSE 5u
#define SAFETY 6u
#define E_FILE 1u
#define E_PARSE 2u
#define E_CANCEL 3u
#define E_CLOCK 4u
static void publish(void){ii_error_observed=error;ii_parser_observed=ni_error();ii_line_observed=ni_error_line();}
static void first(br_u8 e){if(!error){error=e;if(e==E_FILE){first_op=leaf.op;first_leaf=leaf.error?leaf.error:leaf.rejected;first_transport=leaf.transport;}}}
static br_u8 status(const char *p,br_u8 n){return !uci_flags&&!(uci_last_status&0x10u)&&uci_status_len==n&&!memcmp(uci_status,p,n);}
/* Strict FILES rejects a non00 OPEN status by its own ABORT, whose native
 * UCI cause is CANCEL5. That bounded recovery is not a transport fault itself;
 * only this exact status + FILES_STATUS3 + induced CANCEL5 can be optional.
 * Any failed recovery or different transport cause remains an error. */
static br_u8 optional_absent(void){return phase==OPEN&&leaf.op==BR_OPEN&&leaf.error==BR_STATUS&&
 !uci_recovery_failed&&(!leaf.transport||(leaf.transport==5u&&files_error==3u&&uci_error==5u))&&status("FILE DOESN'T EXIST",18u);}
static br_u8 eof(void){return phase==EOFREAD&&leaf.error==BR_COUNT&&!leaf.transport&&leaf.known&&!leaf.actual&&leaf.handle==1u;}
static br_u8 nofile(void){return (phase==SAFETY||missing)&&leaf.op==BR_CLOSE&&leaf.error==BR_STATUS&&!leaf.transport&&status("84,NO FILE TO CLOSE",19u);}
static void restore(void){br_result=leaf;br_now=ii_now;}
static void capture(void){
 leaf=br_result;
 if(leaf.error&&!optional_absent()&&!eof()&&!nofile())first(E_FILE);
}
static br_u8 quiet(void){br_u8 ok=br_ui_acquire();capture();if(!ok)return 0;ok=br_ui_release();capture();return ok&&!files_handle&&!leaf.handle;}
static br_u8 op(br_u8 step,br_u8 command,br_u16 n){
 restore();memset(&br_request,0,sizeof(br_request));br_request.op=command;br_request.mode=1u;br_request.length=n;
 if(command==BR_OPEN)memcpy(br_request.path,path,128u);
 phase=step;if(!br_start()){capture();first(E_FILE);return 0;}capture();waiting=1u;return 1;
}
static void terminal(void){state=3u;publish();}
static void observe(void){
 if(!waiting)return;restore();br_poll();capture();
 if(leaf.state!=BR_BUSY)waiting=0;
}
static void abort_job(br_u8 reason){
 if(state!=1u)return;
 observe();first(reason);cancelled=1u;
 if(waiting&&phase!=CLOSE&&phase!=SAFETY){restore();br_cancel();capture();}
 publish();
}
br_u8 ii_begin(const char *p){
 if(state||files_handle||br_result.handle||br_result.state==BR_BUSY||!br_ui_acquire())return 0;
 if(!br_ui_release())return 0;
 memcpy(path,p,128u);leaf=br_result;size=position=drain_steps=0;
 first_op=first_leaf=first_transport=0;error=waiting=missing=cancelled=clock_failed=cleanup=committed=0;state=1u;
 if(!ni_begin()||!op(OPEN,BR_OPEN,0u)){first(E_FILE);terminal();return 0;}
 publish();return 1;
}
void ii_poll(void){
 if(state!=1u){publish();return;}
 observe();
 if(waiting){if(clock_failed&&++drain_steps>=256u){cleanup=1u;first(E_CLOCK);terminal();}publish();return;}
 if(error){
  if(phase==SAFETY||phase==CLOSE){cleanup=leaf.handle||files_handle||!quiet();terminal();return;}
  if(leaf.handle||files_handle){if(!op(SAFETY,BR_CLOSE,0u)){cleanup=1u;terminal();}publish();return;}
  cleanup=!quiet();terminal();return;
 }
 if(phase==OPEN){
  if(optional_absent()){
   missing=1u;if(!ni_finish()){first(E_PARSE);terminal();return;}
   if(!op(CLOSE,BR_CLOSE,0u)){cleanup=1u;first(E_FILE);terminal();}publish();return;
  }
  if(leaf.state!=BR_DONE||leaf.error||leaf.handle!=1u){first(E_FILE);publish();return;}
  if(!op(INFO,BR_INFO,0u)){first(E_FILE);publish();}return;
 }
 if(phase==INFO){
  if(leaf.state!=BR_DONE||leaf.error||!leaf.known||leaf.size>NI_FILE_BYTES){first(E_FILE);publish();return;}
  size=(br_u16)leaf.size;position=0u;
 }else if(phase==READ){
  if(leaf.state!=BR_DONE||leaf.error||!leaf.known||leaf.actual!=wanted){first(E_FILE);publish();return;}
  memcpy(ni_input,uci_data,wanted);ni_count=(br_u8)wanted;
  if(!ni_feed()){first(E_PARSE);publish();return;}position+=wanted;
 }else if(phase==EOFREAD){
  if(leaf.state!=BR_FAILED||!eof()){first(E_FILE);publish();return;}
  if(!ni_finish()){first(E_PARSE);publish();return;}
  if(!op(CLOSE,BR_CLOSE,0u)){first(E_FILE);cleanup=1u;terminal();}publish();return;
 }else if(phase==CLOSE){
  if((leaf.state!=BR_DONE||leaf.error)&&!nofile()){first(E_FILE);cleanup=leaf.handle||files_handle;terminal();return;}
  if(!quiet()){first(E_FILE);cleanup=1u;terminal();return;}
  /* Optional absence's exact84 CLOSE is a qualified known-closed terminal.
   * Clear only its public observation after private proof; raw FILES/UCI
   * failure/status bytes remain available. Genuine errors never reach here. */
  if(missing){leaf.state=BR_DONE;leaf.error=leaf.transport=0u;br_result=leaf;}
  state=2u;publish();return;
 }else {first(E_FILE);publish();return;}
 if(position==size){if(!op(EOFREAD,BR_READ,1u))first(E_FILE);}
 else {wanted=size-position;if(wanted>NI_CHUNK_BYTES)wanted=NI_CHUNK_BYTES;if(!op(READ,BR_READ,wanted))first(E_FILE);}
 publish();
}
void ii_cancel(void){abort_job(E_CANCEL);}
void ii_clock_fail(void){if(state==1u){clock_failed=1u;abort_job(E_CLOCK);}}
br_u8 ii_state(void){return state;}
br_u8 ii_error(void){return error;}
br_u8 ii_cleanup(void){return cleanup;}
br_u8 ii_columns(void){return state==2u&&!error&&!cleanup?ni_columns():0u;}
br_u8 ii_commit(void){
 br_u8 columns;
 if(committed||state!=2u||error||cleanup)return 0;
 restore();if(!quiet()){first(E_FILE);state=3u;publish();return 0;}
 if(!ps_clock_poll()){first(E_CLOCK);state=3u;publish();return 0;}
 ii_now=ps_ticks;
 if(ps_key_poll()&&ps_key==27u){first(E_CANCEL);state=3u;publish();return 0;}
 columns=ii_columns();if(columns!=40u&&columns!=80u){first(E_PARSE);state=3u;publish();return 0;}
 committed=1u;return columns;
}

br_u8 ii_failed_op(void){return first_op;}
br_u8 ii_leaf_error(void){return first_leaf;}
br_u8 ii_transport(void){return first_transport;}
