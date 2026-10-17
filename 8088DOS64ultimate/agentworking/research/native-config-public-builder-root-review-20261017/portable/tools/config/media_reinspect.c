#include "file_error.h"
#include "media_reinspect.h"
#include "existing_cfg.h"
#include "bulk_context.h"
#include "bulk_uci.h"
#include "install_config.h"
#include "platform.h"
#include "crc32.h"
#include <string.h>
#define OPEN 1u
#define INFO 2u
#define LOAD 3u
#define REWIND 4u
#define DATA 5u
#define EOF_READ 6u
#define CLOSE 7u
#define MBR 8u
#define VBR_SEEK 9u
#define VBR 10u
#define END_SEEK 11u
struct rm_request_t rm_request;
struct rm_result_t rm_result;
struct rm_receipt_t rm_receipt;
br_u16 rm_query_session;
char rm_query_home[128];
br_u16 rm_dma_c64,rm_dma_length;
br_u32 rm_dma_reu;
br_u8 rm_dma_direction;
extern br_u8 rm_dma(void);
static struct rm_receipt_t committed;
static char root[128];
static br_u8 compare[256];
static br_u8 state,error,phase,drive,leaf,transport,waiting,cancelled,clock_bad,close_attempt,checked_mask;
static br_u16 timeout,now,last,began,steps,drain_steps,wanted;
static br_u32 capacity,size,position,stream_crc,token;
static br_u16 word(const br_u8*p){return p[0]|((br_u16)p[1]<<8);}
static br_u32 wide(const br_u8*p){return (br_u32)p[0]|((br_u32)p[1]<<8)|((br_u32)p[2]<<16)|((br_u32)p[3]<<24);}
#if DOS64_ALL_FILE_DIAGNOSTICS
#pragma rodata-name(push,"RODATA")
static const br_u8 fd_rm_ops[]={0,1,2,3,10,9,11,4,9,10,9,10};
#pragma rodata-name(pop)
#endif
static void first(br_u8 e){
#if DOS64_ALL_FILE_DIAGNOSTICS
 __asm__("tax");__asm__("lda _error");__asm__("bne @fd_done");__asm__("stx _error");
 __asm__("lda _fd_code");__asm__("bne @fd_done");__asm__("stx _fd_code");
 __asm__("lda _fd_origin");__asm__("sta _fd_op");
 __asm__("lda _leaf");__asm__("sta _fd_leaf");__asm__("lda _transport");__asm__("sta _fd_transport");
 __asm__("@fd_done:");
#else
 if(!error)error=e;
#endif
}
static void publish(void){rm_result.state=state;rm_result.error=error;rm_result.phase=phase;rm_result.drive=drive;rm_result.leaf=leaf;rm_result.transport=transport;rm_result.cleanup=state==RM_BUSY||!ri_closed_quiet()||!bc_files_closed();rm_result.checked=position;}
static void sample(void){if(!ps_clock_poll())clock_bad=1;else{now=ps_ticks;if((br_u16)(now-last)>=0x8000u)clock_bad=1;last=now;}}
static void config(void){bc_slot=0;bc_config[0].owner=0xa5;bc_config[0].target=1;bc_config[0].capacity=capacity;memcpy(bc_config[0].root,root,128);br_now=now;}
static br_u8 eof(void){return phase==EOF_READ&&br_result.op==BR_READ&&br_result.state==BR_FAILED&&br_result.error==BR_COUNT&&br_result.known&&!br_result.actual&&!br_result.transport&&br_result.handle==1&&!uci_data_len&&!uci_flags&&!(uci_last_status&0x10);}
static void observe(void){br_u8 expected;
 if(!waiting)return;config();bc_poll();expected=eof();
 if(br_result.error&&!expected){if(!error){leaf=br_result.error;transport=br_result.transport;}first(RM_FILE);}
 if(br_result.state!=BR_BUSY){waiting=0;if(phase==EOF_READ){if(!expected)first(RM_FILE);}else if(br_result.state!=BR_DONE||br_result.error)first(RM_FILE);}
}
static void abort_once(void){if(cancelled)return;cancelled=1;if(waiting&&phase!=CLOSE){config();bc_cancel();}}
static void stop(br_u8 e){first(e);abort_once();}
static void service(void){sample();if(ps_key_poll()&&ps_key==27)stop(RM_CANCEL);if(clock_bad)stop(RM_CLOCK);if((br_u16)(now-began)>=timeout)stop(RM_TIMEOUT);}
static br_u8 source(void){config();return token&&bc_source_identity()==token&&bc_source_bytes()==size;}
static br_u8 operation(br_u8 p,br_u8 op,br_u32 value){
 config();memset(&br_request,0,sizeof(br_request));br_request.op=op;br_request.mode=1;
 if(op==BR_OPEN)memcpy(br_request.path,committed.cfg+136u+(br_u16)drive*128u,128);
 if(op==BR_LOAD){br_request.address=RM_STAGE;br_request.length=RM_STAGE_BYTES;}
 if(op==BR_READ){br_request.length=value;memset(uci_data,0xa7,512);}
 if(op==BR_SEEK)br_request.offset=value;
 #if DOS64_ALL_FILE_DIAGNOSTICS
fd_origin=fd_rm_ops[phase=p];
#else
phase=p;
#endif
began=now;steps=0;
 if(!bc_start()){if(!error){leaf=br_result.error?br_result.error:br_result.rejected;transport=br_result.transport;}first(RM_FILE);return 0;}
 waiting=1;return 1;
}
static void fail(void){state=RM_FAILED;}
static void cleanup(void){
 if(waiting)return;
 if(bc_files_closed()){fail();return;}
 if(!close_attempt){close_attempt=1;if(operation(CLOSE,BR_CLOSE,0))return;}
 fail();
}
static br_u8 fold(br_u8 c){return c>='A'&&c<='Z'?c+32:c;}
static br_u8 aliases(const br_u8*a,const br_u8*b){br_u8 n;for(n=0;n<128;++n){if(fold(a[n])!=fold(b[n]))return 0;if(!a[n])return 1;}return 1;}
static br_u8 next_file(void){
 br_u8 n;
 while(drive<3&&!(committed.present&(1u<<drive)))++drive;
 if(drive==3){if(checked_mask!=committed.present){first(RM_OWNER);return 0;}service();if(!error&&bc_files_closed())state=RM_DONE;else first(error?error:RM_OWNER);return !error;}
 memcpy(d64_path_source,committed.cfg+136u+(br_u16)drive*128u,128);
#if DOS64_ALL_FILE_DIAGNOSTICS
 fd_set_path((const char*)d64_path_source);
#endif
 if(!d64_path_parent()){first(RM_INPUT);return 0;}
 memcpy(root,d64_path_output,128);config();if(!bc_clear_error()){first(RM_OWNER);return 0;}
 size=drive<2?RM_STAGE_BYTES:(committed.profile?20971520UL:2097152UL);position=0;close_attempt=0;token=0;
 if(drive<2){if(!c32_reset()){first(RM_DMA);return 0;}stream_crc=0xffffffffUL;}
 return operation(OPEN,BR_OPEN,0);
}
static br_u8 mbr_valid(void){
 br_u8 n,p=committed.profile;
 if(word(uci_data+510)!=0xaa55||(uci_data[446]!=0&&uci_data[446]!=0x80)||uci_data[447]!=1||uci_data[448]!=1||uci_data[449]||uci_data[450]!=(p?4:1)||uci_data[451]!=(p?3:1)||uci_data[452]!=(p?0x90:0x10)||uci_data[453]!=127||wide(uci_data+454)!=16UL||wide(uci_data+458)!=(p?40944UL:4080UL))return 0;
 for(n=0;n<48;++n)if(uci_data[462u+n])return 0;return 1;
}
static br_u8 vbr_valid(void){br_u8 p=committed.profile;
 return word(uci_data+11)==512&&uci_data[13]==(p?4:8)&&word(uci_data+14)==1&&uci_data[16]==2&&word(uci_data+17)==512&&word(uci_data+19)==(p?40944u:4080u)&&uci_data[21]==0xf8&&word(uci_data+22)==(p?40:2)&&word(uci_data+24)==16&&word(uci_data+26)==(p?4:2)&&wide(uci_data+28)==16UL&&!wide(uci_data+32)&&word(uci_data+510)==0xaa55;
}
static br_u8 compare_data(void){br_u16 n;
 if(!source()){first(RM_OWNER);return 0;}
 if(!br_result.known||br_result.actual!=wanted||uci_data_len!=wanted){first(RM_FILE);return 0;}
 for(n=0;n<wanted;++n)compare[n]=~uci_data[n];
 rm_dma_c64=(br_u16)compare;rm_dma_reu=RM_STAGE+position;rm_dma_length=wanted;rm_dma_direction=1;
 if(!rm_dma()){first(RM_DMA);return 0;}
 if(memcmp(compare,uci_data,wanted)){first(RM_COMPARE);return 0;}
 c32_crc=stream_crc;c32_address=(br_u16)uci_data;c32_length=wanted;
 if(!c32_update()||c32_error){first(RM_DMA);return 0;}stream_crc=c32_crc;
 service();if(error)return 0;position+=wanted;return 1;
}
br_u8 rm_begin(void){br_u8 a,b;
 if(state!=RM_IDLE||rm_request.owner!=0xa5||!rm_request.timeout||rm_request.timeout>=0x8000u||(*(br_u8*)0&7u)!=7u||(*(br_u8*)1&7u)!=5u||!ri_closed_quiet()||!bc_files_closed())return 0;
 memcpy(ri_query_home,rm_request.home,128);ri_query_session=rm_request.session;
 if(!ri_get())return 0;
 /* No callback/engine operation intervenes between private refresh and copy. */
 memcpy(committed.cfg,ri_receipt.bytes,576);committed.session=ri_receipt.session;committed.cfg_identity=ri_receipt.identity;committed.present=committed.cfg[525];committed.readonly=committed.cfg[524];committed.profile=committed.cfg[522];committed.crc_mask=0;
 for(a=0;a<3;++a)if(committed.present&(1u<<a))for(b=a+1;b<3;++b)if((committed.present&(1u<<b))&&aliases(committed.cfg+136u+(br_u16)a*128u,committed.cfg+136u+(br_u16)b*128u))return 0;
 capacity=wide(committed.cfg+538);if(capacity<0x400000UL||RM_STAGE+RM_STAGE_BYTES>capacity)return 0;
 timeout=rm_request.timeout;if(!ps_clock_poll())return 0;now=last=began=ps_ticks;
 if(!c32_init())return 0;sample();if(clock_bad)return 0;began=now;state=RM_BUSY;drive=0;checked_mask=0;
 if(!next_file()){if(!error)first(RM_INPUT);cleanup();}publish();return 1;
}
void rm_poll(void){
 if(state!=RM_BUSY){publish();return;}
 sample();observe();
 if(++steps>=2048u)stop(RM_LIMIT);
 if(error)abort_once();
 if(ps_key_poll()&&ps_key==27)stop(RM_CANCEL);
 if(clock_bad)stop(RM_CLOCK);
 if((br_u16)(now-began)>=timeout)stop(RM_TIMEOUT);
 if(error){
  if(waiting){if(++drain_steps>=256u)fail();}
  else cleanup();publish();return;
 }
 if(waiting){publish();return;}
 if(phase==OPEN){if(!operation(INFO,BR_INFO,0))cleanup();}
 else if(phase==INFO){
  if(!br_result.known||br_result.size!=size){first(RM_SIZE);cleanup();}
  else {token=bc_source_identity();if(!token){first(RM_OWNER);cleanup();}
   else if(drive<2){if(!operation(LOAD,BR_LOAD,0))cleanup();}
   else {wanted=512;if(!operation(MBR,BR_READ,512))cleanup();}}
 }else if(phase==LOAD){if(!br_result.known||br_result.actual!=size||!source()){first(RM_FILE);cleanup();}else if(!operation(REWIND,BR_SEEK,0))cleanup();}
 else if(phase==REWIND){wanted=256;if(!operation(DATA,BR_READ,wanted))cleanup();}
 else if(phase==DATA){
  if(!compare_data())cleanup();
  else if(position==size){if(!operation(EOF_READ,BR_READ,1))cleanup();}
  else {wanted=256;if(!operation(DATA,BR_READ,wanted))cleanup();}
 }else if(phase==MBR||phase==VBR){
  if(!source()||!br_result.known||br_result.actual!=512UL||uci_data_len!=512){first(RM_FILE);cleanup();}
  else if(!(phase==MBR?mbr_valid():vbr_valid())){
#if DOS64_ALL_FILE_DIAGNOSTICS
fd_origin=0;
#endif
first(RM_GEOMETRY);cleanup();}
  else {service();if(error)cleanup();else if(phase==MBR){if(!operation(VBR_SEEK,BR_SEEK,8192UL))cleanup();}else if(!operation(END_SEEK,BR_SEEK,size))cleanup();}
 }else if(phase==VBR_SEEK){if(!operation(VBR,BR_READ,512))cleanup();}
 else if(phase==END_SEEK){if(!operation(EOF_READ,BR_READ,1))cleanup();}
 else if(phase==EOF_READ){close_attempt=1;if(!operation(CLOSE,BR_CLOSE,0))cleanup();}
 else if(phase==CLOSE){
  if(!ri_closed_quiet()||!bc_files_closed()){first(RM_OWNER);fail();}
  else {if(drive<2){c32_crc=stream_crc;if(!c32_finish()||c32_error)first(RM_DMA);else{committed.crc[drive]=c32_crc;committed.crc_mask|=1u<<drive;}}
   service();if(error)fail();else{checked_mask|=1u<<drive;++drive;if(!next_file())cleanup();}}
 }else {first(RM_INPUT);cleanup();}
 publish();
}
void rm_cancel(void){if(state==RM_BUSY){sample();observe();stop(RM_CANCEL);}publish();}
br_u8 rm_state(void){publish();return state;}
br_u8 rm_error(void){publish();return error;}
br_u8 rm_closed_quiet(void){return state!=RM_BUSY&&ri_closed_quiet()&&bc_files_closed();}
br_u8 rm_get(void){
 if(state!=RM_DONE||error||checked_mask!=committed.present||committed.crc_mask!=(committed.present&3u)||rm_query_session!=committed.session||memcmp(rm_query_home,committed.cfg+8,128)||!rm_closed_quiet())return 0;
 memcpy(ri_query_home,committed.cfg+8,128);ri_query_session=committed.session;if(!ri_get()||ri_receipt.identity!=committed.cfg_identity||memcmp(ri_receipt.bytes,committed.cfg,576))return 0;
 rm_receipt=committed;return 1;
}
const br_u16 rm_abi_sizes[]={sizeof(struct rm_request_t),sizeof(struct rm_result_t),sizeof(struct rm_receipt_t)};
