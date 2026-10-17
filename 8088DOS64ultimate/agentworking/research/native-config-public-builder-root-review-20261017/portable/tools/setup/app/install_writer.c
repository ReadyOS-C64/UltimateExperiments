#include "file_error.h"
#include "install_writer.h"
#include "setup_io.h"
#include "crc32.h"
#include "bulk_context.h"
#include <string.h>
struct si_request_t si_request;
struct si_result_t si_result;
static struct si_result_t ledger;
br_u16 si_now;
static struct si_request_t owned;
static br_u16 began,used,wanted;
static br_u32 expected,observed,at;
static br_u8 cancelled,waiting,phase;
#define SLAB 0x208000UL
#define READBACK 0x200000UL
#if DOS64_ALL_FILE_DIAGNOSTICS
#pragma code-name(push,"AUX_CODE")
#pragma rodata-name(push,"AUX_RO")
static const br_u8 fd_si_ops[]={0,1,7,8,4,1,2,9,9,11,4,4};
static void si_first(br_u8 e){if(!ledger.error){ledger.error=e;if(!fd_code){fd_op=phase<12?fd_si_ops[phase]:0;fd_leaf=br_result.error;fd_transport=br_result.transport;fd_code=e;}}}
static void fail(br_u8 e){si_first(e);ledger.state=SI_FAILED;}
#pragma rodata-name(pop)
#pragma code-name(pop)
#else
static void fail(br_u8 e){if(!ledger.error)ledger.error=e;ledger.state=SI_FAILED;}
#endif
/* Raw running CRC API; exactly the same finalXOR as the baseline writer. */
static br_u8 feed(br_u32*v,const br_u8*b,br_u16 n){c32_crc=*v;c32_address=(br_u16)b;c32_length=n;if(!c32_update())return 0;*v=c32_crc;return 1;}
static br_u8 op(br_u8 p,br_u8 command,br_u8 mode,br_u32 length){
 memset(&br_request,0,sizeof(br_request));br_request.op=command;br_request.mode=mode;br_request.address=command==BR_SAVE?SLAB:READBACK;br_request.length=length;
 if(command==BR_OPEN){memcpy(br_request.path,owned.path,128);
#if DOS64_ALL_FILE_DIAGNOSTICS
 fd_set_path(owned.path);
#endif
 }
 #if DOS64_ALL_FILE_DIAGNOSTICS
 phase=p;
 #endif
 br_now=si_now;bc_slot=1;
 if(!bc_start()){fail(3);return 0;}phase=p;ledger.phase=p;waiting=1;began=si_now;return 1;
}
static br_u8 begin(void){
 if(ledger.state!=SI_IDLE||si_request.owner!=0xa5||si_request.capacity<0x400000UL||si_request.capacity>0x1000000UL||(si_request.capacity&65535UL)||!si_request.timeout||si_request.timeout>=0x8000||ns_io_owner!=0xa5||ns_capacity!=si_request.capacity||ns_io_error||ns_cancel||nf_error||nf_finished||nf_pending){ledger.rejected=1;return 0;}
 /* Tables are generated only after explicit admission; no file exists yet. */
 if(!c32_init()){ledger.rejected=1;return 0;}
 /* NFnext establishes actual sealed producer before any file creation. */
 if(nf_next()||!nf_pending){ledger.rejected=1;return 0;}
 memcpy(&owned,&si_request,sizeof(owned));memset(&ledger,0,sizeof(ledger));ledger.state=SI_BUSY;began=si_now;used=0;cancelled=0;waiting=0;expected=0xffffffffUL;observed=0xffffffffUL;at=0;
 bc_config[1].owner=0xa5;bc_config[1].target=2;bc_config[1].capacity=owned.capacity;memcpy(bc_config[1].root,owned.root,128);
 return op(1,BR_OPEN,6,0);
}
static void cancel(void){if(ledger.state!=SI_BUSY)return;cancelled=1;
#if DOS64_ALL_FILE_DIAGNOSTICS
si_first(6);
#else
if(!ledger.error)ledger.error=6;
#endif
if(waiting){bc_slot=1;br_now=si_now;bc_cancel();}else fail(6);}
static br_u8 expected_eof(void){return phase==9&&br_result.error==BR_COUNT&&br_result.known&&!br_result.actual&&!br_result.transport&&br_result.handle==1;}
static void deadline(void){if((br_u16)(si_now-began)>=owned.timeout&&!cancelled){
#if DOS64_ALL_FILE_DIAGNOSTICS
si_first(7);
#else
if(!ledger.error)ledger.error=7;
#endif
cancel();}}
static void poll(void){br_u16 n;
 if(ledger.state!=SI_BUSY)return;
 if(waiting){bc_slot=1;br_now=si_now;bc_poll();
  /* The restored native leaf may already have failed while abort is draining. */
  if(br_result.error&&!expected_eof()&&!ledger.error){
#if DOS64_ALL_FILE_DIAGNOSTICS
si_first(4);
#else
ledger.error=4;
#endif
}
  deadline();if(br_result.state==BR_BUSY)return;waiting=0;
  if(cancelled){fail(ledger.error?ledger.error:6);return;}
  /* Successful SAVE keeps durability uncertainty sticky by design. Expected
   * exact EOF is the sole accepted short LOAD; retain the gateway COUNT record. */
  if(phase==9){if(br_result.state!=BR_FAILED||!expected_eof()){fail(4);return;}}
  else if(br_result.state!=BR_DONE||br_result.error||br_result.handle==2){fail(4);return;}
  switch(phase){
   case 1:phase=2;break;
   case 3:if(br_result.actual!=used){fail(5);return;}used=0;phase=2;break;
   case 4:op(5,BR_OPEN,1,0);return;
   case 5:op(6,BR_INFO,0,0);return;
   case 6:if(br_result.size!=nf_total_bytes){fail(8);return;}phase=7;break;
   case 8:if(br_result.actual!=wanted){fail(5);return;}
    for(n=0;n<wanted;n+=512){if(nf_store_read(READBACK+n,nf_sector,512)!=512){fail(2);return;}if(!feed(&observed,nf_sector,512)){fail(11);return;}}
    at+=wanted;ledger.verified=at;phase=7;break;
   case 9:if(br_result.actual!=0||(observed^0xffffffffUL)!=ledger.crc){fail(9);return;}op(10,BR_CLOSE,0,0);return;
   case 10:ledger.state=SI_DONE;return;
   default:fail(10);return;
  }
 }else {deadline();if(ledger.state!=SI_BUSY)return;}
 if(phase==2){
  if(nf_finished){if(used){op(3,BR_SAVE,0,used);return;}ledger.crc=expected^0xffffffffUL;op(4,BR_CLOSE,0,0);return;}
  if(!nf_pending&&nf_next()){fail(1);return;}
  if(!nf_pending){fail(1);return;}
  if(nf_store_write(SLAB+used,nf_sector,512)!=512){fail(2);return;}
  if(!feed(&expected,nf_sector,512)){fail(11);return;}if(nf_ack(512,0)){fail(1);return;}
  used+=512;ledger.produced+=512;began=si_now;
  if(used==32768u)op(3,BR_SAVE,0,used);
 }else if(phase==7){
  if(at==nf_total_bytes){op(9,BR_LOAD,0,1);return;}
  wanted=nf_total_bytes-at>=32768UL?32768u:(br_u16)(nf_total_bytes-at);op(8,BR_LOAD,0,wanted);
 }
}

br_u8 si_begin(void){br_u8 r=begin();si_result=ledger;return r;}
void si_poll(void){poll();si_result=ledger;}
void si_cancel(void){cancel();si_result=ledger;}

br_u8 si_state(void){si_result=ledger;return ledger.state;}
br_u8 si_error(void){return ledger.error;}
br_u8 si_closed_quiet(void){return ledger.state!=SI_BUSY&&!waiting&&bc_files_closed();}
#pragma code-name(push,"FAT_CODE")
br_u8 si_rearm(void){
 if(ledger.state!=SI_DONE||waiting||cancelled||!bc_files_closed()||!nf_finished||nf_pending||nf_error||ns_cancel||ns_io_error)return 0;
 if(!ns_source_rearm())return 0;
 bc_slot=1;if(!bc_clear_error())return 0;
 memset(&ledger,0,sizeof(ledger));phase=waiting=cancelled=0;used=0;
 si_result=ledger;return 1;
}
#pragma code-name(pop)

#if defined(DOS64_SETUP_WRITER_CLEANUP) && DOS64_SETUP_WRITER_CLEANUP
static br_u8 clean_state,clean_phase,clean_left,clean_error;
#pragma code-name(push,"FAT_CODE")
br_u8 si_cleanup_begin(void){
 if(clean_state||(!ledger.error)||(ledger.state!=SI_FAILED&&ledger.state!=SI_BUSY))return 0;
 clean_state=1;clean_phase=waiting?0:1;clean_left=0;clean_error=0;began=si_now;
 if(waiting)cancel();
 return 1;
}
void si_cleanup_poll(void){
 if(clean_state!=1)return;
 /* Exactly256 caller polls; waiting means this SI owns the current job. */
 if(clean_phase!=1){
  bc_slot=1;br_now=si_now;bc_poll();
  if(br_result.state!=BR_BUSY){waiting=0;ledger.state=SI_FAILED;
   if(clean_phase==2){if(bc_output_closed()){clean_state=2;if(br_result.error)clean_error=3;}else{clean_state=3;clean_error=3;}return;}
   clean_phase=1;
  }
 }
 if((br_u16)(si_now-began)>=owned.timeout||!--clean_left){clean_state=3;clean_error=2;return;}
 if(clean_phase==1){
  if(bc_output_closed()){clean_state=2;return;}
  if(!op(11,BR_CLOSE,0,0)){clean_state=3;clean_error=1;return;}
  clean_phase=2;waiting=1;
 }
 
}
br_u8 si_cleanup_state(void){return clean_state;}
br_u8 si_cleanup_error(void){return clean_error;}
#pragma code-name(pop)
#endif
