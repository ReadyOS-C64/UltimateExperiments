#include "raw_output.h"
#include "bulk_context.h"
#include "setup_overlay.h"
#include "selection_capsule.h"
#include "install_writer.h"
#include "setup_io.h"
#include "platform.h"
#include "crc32.h"
#include <string.h>
#define READBACK 0x260000UL
#define PRE 1u
#define OPEN_WRITE 2u
#define WRITE 3u
#define SAVE 4u
#define CLOSE_WRITE 5u
#define OPEN_READ 6u
#define INFO 7u
#define POISON 8u
#define LOAD 9u
#define COMPARE 10u
#define EOF_READ 11u
#define CLOSE_READ 12u
struct rw_request_t rw_request;
struct rw_result_t rw_result;
const br_u16 rw_abi_sizes[]={sizeof(struct rw_request_t),sizeof(struct rw_result_t)};
static struct rw_request_t owned;
static struct rw_result_t ledger;
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
#include "publish_scratch.h"
#include "publish_assets.h"
#define verify pub_scratch.verify
#else
static br_u8 verify[512];
#endif
static br_u8 waiting,cancelled,clock_bad,clock_failed;
static br_u16 now,began,relative,wanted,steps,bad_steps,ticket;
static br_u32 at,raw;
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
static br_u32 cfg_identity,body_raw;
static br_u8 cfg_bound;
#define BODY_BAD (cfg_bound&&(body_raw^0xffffffffUL)!=cfg_identity)
#define BODY_RESET body_raw=0xffffffffUL
#else
#define BODY_BAD 0
#define BODY_RESET
#define cfg_chunk(p,n,o) 1
#endif
static void publish(void){rw_result=ledger;}
static void first(br_u8 e){if(!ledger.error)ledger.error=e;}
static void failed(void){
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
 /* Private ledger offsets are locked by rw_result_t ABI20 assertions/tests.
  * The owner remains BUSY until its one legal CLOSE settles; bounded escape
  * and attempted cleanup share the private reserved latch. */
 __asm__("lda _waiting");
 __asm__("bne @cleanup");
 __asm__("jsr _bc_files_closed");
 __asm__("eor #$01");
 __asm__("@cleanup: sta _ledger+6");
 __asm__("tax");
 __asm__("beq @terminal");
 __asm__("lda _ledger+7");
 __asm__("beq @state");
 __asm__("@terminal: ldx #$03");
 __asm__("@state: stx _ledger");
#else
 ledger.state=RW_FAILED;ledger.cleanup_required=waiting||!bc_files_closed();
#endif
}
static br_u8 source_ok(void){
 if(!owned.bytes)return 0;
 return (owned.source>=0x200000UL&&owned.source<0x25a000UL&&owned.bytes<=0x25a000UL-owned.source)||(owned.source>=0x3f8000UL&&owned.source<0x3ff000UL&&owned.bytes<=0x3ff000UL-owned.source);
}
static br_u8 path_ok(void){br_u8 n,i,length;
 for(n=0;n<128u&&owned.root[n];++n){}
 if(n<2u||n>117u||memcmp(owned.root,owned.path,n)||owned.path[n]!='/')return 0;
 for(i=n+1u;i<128u&&owned.path[i];++i){}
 if(i==128u)return 0;length=i-n-1u;
 for(++i;i<128u;++i)if(owned.path[i])return 0;
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
 if(length==9u&&!memcmp(owned.path+n+1u,"DOS64.CFG",9))return cfg_bound&&owned.bytes==576UL;
 if(cfg_bound)return 0;
 return (length==5u&&!memcmp(owned.path+n+1u,"A.IMG",5))||(length==9u&&!memcmp(owned.path+n+1u,"START.PRG",9));
#else
 return (length==5u&&!memcmp(owned.path+n+1u,"A.IMG",5))||(length==9u&&(!memcmp(owned.path+n+1u,"DOS64.CFG",9)||!memcmp(owned.path+n+1u,"START.PRG",9)));
#endif
}
static br_u8 expected_eof(void){return ledger.phase==EOF_READ&&br_result.error==BR_COUNT&&br_result.known&&!br_result.actual&&!br_result.transport&&br_result.handle==1;}
static void observe(void){
 br_now=now;bc_slot=1;bc_poll();
 if(br_result.error&&!expected_eof()){
  if(!ledger.error){ledger.leaf=br_result.error;ledger.transport=br_result.transport;}first(RW_FILE);
 }
 if(br_result.state!=BR_BUSY){waiting=0;
  if(ledger.phase==EOF_READ){if(br_result.state!=BR_FAILED||!expected_eof())first(RW_FILE);}
  else if(br_result.state!=BR_DONE||br_result.error||br_result.handle==2)first(RW_FILE);
 }
}
static void request_cancel(br_u8 e){
 first(e);cancelled=1;
 if(waiting&&ledger.phase!=CLOSE_WRITE&&ledger.phase!=CLOSE_READ){br_now=now;bc_slot=1;bc_cancel();}
}
static void sample_clock(void){
 if(!ps_clock_poll())clock_bad=clock_failed=1;
 else now=ps_ticks;
}
static void service(void){
 sample_clock();if(clock_bad)request_cancel(RW_CLOCK);
 if(ps_key_poll()&&ps_key==27)request_cancel(RW_CANCEL);
 if(ns_io_owner!=0xa5||ns_capacity!=owned.capacity||ns_io_error)request_cancel(RW_DMA);
 if(ns_cancel)request_cancel(RW_CANCEL);
 if(!cancelled&&(br_u16)(now-began)>=owned.timeout)request_cancel(RW_TIMEOUT);
}
static br_u8 op(br_u8 phase,br_u8 command,br_u8 mode,br_u32 address,br_u16 count){
 memset(&br_request,0,sizeof(br_request));br_request.op=command;br_request.mode=mode;br_request.address=address;br_request.length=count;
 if(command==BR_OPEN)memcpy(br_request.path,owned.path,128);
 bc_config[1].owner=0xa5;bc_config[1].target=2;bc_config[1].capacity=owned.capacity;memcpy(bc_config[1].root,owned.root,128);
 br_now=now;bc_slot=1;
 if(!bc_start()){if(!ledger.error){ledger.leaf=br_result.error?br_result.error:br_result.rejected;ledger.transport=br_result.transport;}first(RW_FILE);failed();return 0;}
 ledger.phase=phase;waiting=1;began=now;steps=0;return 1;
}
static br_u8 feed(const br_u8*bytes,br_u16 n){
 c32_crc=raw;c32_address=(br_u16)bytes;c32_length=n;
 if(!c32_update()){first(RW_CRC);failed();return 0;}raw=c32_crc;return 1;
}
static br_u8 read(br_u32 address,br_u8*bytes,br_u16 n){
 if(nf_store_read(address,bytes,n)!=n){first(RW_DMA);failed();return 0;}return 1;
}
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
static br_u8 cfg_chunk(const br_u8*p,br_u16 n,br_u16 offset){br_u16 count=0,i;
 if(!cfg_bound)return 1;
 if(offset<572u){count=572u-offset;if(count>n)count=n;c32_crc=body_raw;c32_address=(br_u16)p;c32_length=count;if(!c32_update()){first(RW_CRC);failed();return 0;}body_raw=c32_crc;}
 for(i=count;i<n;++i)if(offset+i<572u||offset+i>=576u||p[i]!=((const br_u8*)&cfg_identity)[offset+i-572u]){first(RW_CRC);failed();return 0;}
 return 1;
}
br_u8 rw_expect_cfg(br_u32 identity){if(ledger.state!=RW_IDLE||cfg_bound||!so_publish_ticket())return 0;cfg_identity=identity;cfg_bound=1;return 1;}
#endif
br_u8 rw_begin(void){br_u8 reason;
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
 if(pb_state()==1){ledger.rejected=1;publish();return 0;}
#endif
 if(ledger.state!=RW_IDLE||rw_request.owner!=0xa5||!rw_request.timeout||rw_request.timeout>=0x8000u||!so_publish_ticket()||si_state()!=SI_DONE||!si_closed_quiet()){ledger.rejected=1;publish();return 0;}
 owned=rw_request;
 if(owned.capacity!=so_capacity()||ns_io_owner!=0xa5||ns_capacity!=owned.capacity||ns_io_error||ns_cancel||!source_ok()||!path_ok()){ledger.rejected=1;publish();return 0;}
 sq_page=0;
 if(sq_read()!=512u){reason=sq_error();first(reason==SQ_CANCEL?RW_CANCEL:reason==SQ_CLOCK?RW_CLOCK:RW_INPUT);failed();publish();return 0;}
 if(memcmp(owned.root,sq_bytes+SQ_HOME,128)){ledger.rejected=1;publish();return 0;}
 ticket=so_publish_ticket();if(!ticket){ledger.rejected=1;publish();return 0;}
 if(!c32_init()){first(RW_CRC);failed();publish();return 0;}
 bc_slot=1;if(!bc_clear_error()){ledger.rejected=1;publish();return 0;}
 memset(&ledger,0,sizeof(ledger));ledger.state=RW_BUSY;ledger.phase=PRE;waiting=cancelled=clock_bad=clock_failed=0;steps=bad_steps=0;at=0;raw=0xffffffffUL;BODY_RESET;
 if(!ps_clock_poll()){request_cancel(RW_CLOCK);failed();publish();return 0;}now=began=ps_ticks;
 service();if(ledger.error){failed();publish();return 0;}publish();return 1;
}
void rw_poll(void){br_u16 n,i;
 if(ledger.state!=RW_BUSY){publish();return;}
 clock_bad=0;sample_clock(); /* fresh elapsed deadline, without latching yet */
 if(waiting)observe(); /* leaf cause is sampled before user cancel/clock */
 service();
 if(++steps==0){first(RW_BUDGET);
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
 ledger.reserved=1;
#endif
 failed();publish();return;}
 if(waiting){if(clock_failed&&++bad_steps>=256u){first(RW_CLOCK);
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
 ledger.reserved=1;
#endif
 failed();}publish();return;}
 if(ledger.error){
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
 if(!ledger.reserved&&!bc_files_closed()){ledger.reserved=1;op(CLOSE_READ,BR_CLOSE,0,0,0);}else
#endif
 failed();publish();return;}
 switch(ledger.phase){
 case PRE:
  if(at==owned.bytes){
   if((raw^0xffffffffUL)!=owned.crc||BODY_BAD){first(RW_CRC);failed();break;}
   if(so_publish_ticket()!=ticket){first(RW_INPUT);failed();break;}
   service();if(ledger.error){failed();break;}
   at=0;ledger.crc=owned.crc;op(OPEN_WRITE,BR_OPEN,6,0,0);break;
  }
  n=owned.bytes-at>512UL?512u:(br_u16)(owned.bytes-at);
  if(read(owned.source+at,nf_sector,n)&&feed(nf_sector,n)&&cfg_chunk(nf_sector,n,(br_u16)at)){at+=n;began=now;steps=0;}break;
 case OPEN_WRITE:ledger.phase=WRITE;break;
 case WRITE:
  if(at==owned.bytes){op(CLOSE_WRITE,BR_CLOSE,0,0,0);break;}
  wanted=owned.bytes-at>32768UL?32768u:(br_u16)(owned.bytes-at);
  if((owned.source+at&65535UL)+(br_u32)wanted>65536UL)wanted=(br_u16)(65536UL-(owned.source+at&65535UL));
  op(SAVE,BR_SAVE,0,owned.source+at,wanted);break;
 case SAVE:
  if(br_result.actual!=wanted){first(RW_FILE);failed();break;}at+=wanted;ledger.written=at;ledger.phase=WRITE;began=now;break;
 case CLOSE_WRITE:op(OPEN_READ,BR_OPEN,1,0,0);break;
 case OPEN_READ:op(INFO,BR_INFO,0,0,0);break;
 case INFO:
  if(!br_result.known||br_result.size!=owned.bytes){first(RW_FILE);failed();break;}at=0;relative=0;wanted=0;raw=0xffffffffUL;BODY_RESET;ledger.phase=POISON;began=now;break;
 case POISON:
  if(at==owned.bytes){if((raw^0xffffffffUL)!=owned.crc||BODY_BAD){first(RW_CRC);failed();break;}op(EOF_READ,BR_LOAD,0,READBACK,1);break;}
  if(!wanted){wanted=owned.bytes-at>32768UL?32768u:(br_u16)(owned.bytes-at);relative=0;}
  if(relative==wanted){relative=0;op(LOAD,BR_LOAD,0,READBACK,wanted);break;}
  n=wanted-relative>512u?512u:wanted-relative;
  if(!read(owned.source+at+relative,nf_sector,n))break;
  for(i=0;i<n;++i)verify[i]=nf_sector[i]^0xffu;
  if(nf_store_write(READBACK+relative,verify,n)!=n){first(RW_DMA);failed();break;}
  memcpy(verify,nf_sector,n); /* stale/suppressed FETCH must not verify itself */
  if(!read(READBACK+relative,verify,n))break;
  for(i=0;i<n;++i)if(verify[i]!=(br_u8)(nf_sector[i]^0xffu)){first(RW_DMA);failed();break;}
  if(ledger.state==RW_BUSY){relative+=n;began=now;steps=0;}break;
 case LOAD:
  if(!br_result.known||br_result.actual!=wanted){first(RW_FILE);failed();break;}relative=0;ledger.phase=COMPARE;began=now;break;
 case COMPARE:
  if(relative==wanted){at+=wanted;wanted=relative=0;ledger.phase=POISON;began=now;break;}
  n=wanted-relative>512u?512u:wanted-relative;
  if(!read(owned.source+at+relative,nf_sector,n)||!read(READBACK+relative,verify,n))break;
  if(memcmp(nf_sector,verify,n)){first(RW_COMPARE);failed();break;}
  if(feed(verify,n)&&cfg_chunk(verify,n,(br_u16)(at+relative))){relative+=n;ledger.verified=at+relative;began=now;steps=0;}break;
 case EOF_READ:op(CLOSE_READ,BR_CLOSE,0,0,0);break;
 case CLOSE_READ:
  if(!bc_files_closed()){first(RW_FILE);failed();break;}
  if(so_publish_ticket()!=ticket){first(RW_INPUT);failed();break;}
  service();if(ledger.error){failed();break;}ledger.state=RW_DONE;break;
 default:first(RW_INPUT);failed();break;
 }
 publish();
}
void rw_cancel(void){
 if(ledger.state==RW_BUSY){clock_bad=0;sample_clock();if(waiting)observe();request_cancel(RW_CANCEL);if(!waiting)failed();}publish();
}
br_u8 rw_state(void){publish();return ledger.state;}
br_u8 rw_closed_quiet(void){return ledger.state!=RW_BUSY&&!waiting&&bc_files_closed();}
br_u8 rw_rearm(void){
 if(ledger.state!=RW_DONE||waiting||cancelled||!bc_files_closed()||!so_publish_ticket()||ns_io_error||ns_cancel)return 0;
 bc_slot=1;if(!bc_clear_error())return 0;memset(&ledger,0,sizeof(ledger));
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
 cfg_bound=0;
#endif
 publish();return 1;
}
