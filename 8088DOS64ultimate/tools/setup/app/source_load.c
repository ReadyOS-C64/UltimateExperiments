#include "template_limits.h"
#include "source_load.h"
#include "bulk_context.h"
#include "setup_overlay.h"
#include "selection_capsule.h"
#include "install_config.h"
#include "native_fat.h"
#include "setup_io.h"
#include "platform.h"
#include "crc32.h"
#include <string.h>
#if DOS64_FILE_DIAGNOSTICS
#include "file_diag.h"
#endif
#ifndef DOS64_SETUP_RELEASE_PREFLIGHT
#define DOS64_SETUP_RELEASE_PREFLIGHT 0
#endif
#if DOS64_SETUP_RELEASE_PREFLIGHT
#include "release_assets.h"
#if DOS64_SETUP_COLD_INVENTORY
#define SL_KIND_COUNT 11u
static const br_u8 kind_asset[11]={0,0,0,3,4,0,1,2,5,6,7};
#else
#define SL_KIND_COUNT 8u
static const br_u8 kind_asset[8]={0,0,0,3,4,0,1,2};
#endif
#else
#define SL_KIND_COUNT 5u
#endif
#define READBACK 0x260000UL
#define OPEN1 1u
#define INFO1 2u
#define POISON 3u
#define LOAD1 4u
#define HASH1 5u
#define EOF1 6u
#define CLOSE1 7u
#define OPEN2 8u
#define INFO2 9u
#define LOAD2 10u
#define COMPARE 11u
#define EOF2 12u
#define CLOSE2 13u
#pragma bss-name(push,"HIGHBSS")
static struct {
 br_u32 capacity,identity,raw,crc[5],at;
 br_u16 generation,ticket,now,began,relative,wanted,steps,bad_steps,timeout;
 br_u8 state,error,phase,leaf,transport,waiting,cancelled,clock_bad,clock_failed,kind,second,valid,installed;
} q;
#if DOS64_SETUP_COLD_INVENTORY
static br_u8 inventory_valid;
#endif
br_u8 sl_kind;
br_u16 sl_timeout,sl_generation;
br_u32 sl_identity;
struct sl_observation_t sl_result;
struct sl_receipt_t sl_receipt;
#pragma bss-name(pop)
#pragma bss-name(push,"UIBSS")
static char path[128];
#pragma bss-name(pop)
extern br_u8 so_scratch[512],uci_data[];
extern br_u8 _HIGH_CODE_LOAD__,_HIGH_CODE_RUN__,_HIGH_CODE_SIZE__;
#ifndef DOS64_SETUP_SMALL_UCI
#define DOS64_SETUP_SMALL_UCI 0
#endif
#if DOS64_SETUP_SMALL_UCI
extern br_u8 _AUX_CODE_LOAD__,_AUX_CODE_RUN__,_AUX_CODE_SIZE__;
extern br_u8 _AUX_RO_SIZE__;
#endif
static br_u32 address(br_u8 k){if(k==0)return 0x100000UL;if(k==1)return 0x180000UL;if(k==2)return 0x380000UL;if(k==3)return 0x2e0000UL;
#if DOS64_SETUP_RELEASE_PREFLIGHT
#if DOS64_SETUP_COLD_INVENTORY
 if(k==8)return 0x080000UL;
#if DOS64_SETUP_MNU_56K
 if(k==9)return 0x08e000UL;if(k==10)return 0x090000UL;
#else
 if(k==9)return 0x08a000UL;if(k==10)return 0x08c000UL;
#endif
#endif
 if(k==5)return 0x2f0000UL;if(k==6)return 0x3fed00UL;if(k==7)return 0x3f8000UL;
#endif
 return 0x3fec00UL;}
static br_u32 size(br_u8 k){
#if DOS64_SETUP_RELEASE_PREFLIGHT
 if(k>=3)return asset_size[kind_asset[k]];
#endif
 return k<3?368640UL:k==3?ST_TEMPLATE_BYTES:64UL;}
#if DOS64_SETUP_RELEASE_PREFLIGHT
static br_u8 bound(void){br_u32 a=address(q.kind),n=size(q.kind);
 return asset_size[0]<=0xb801UL&&asset_size[1]==64UL&&asset_size[2]<=8192UL&&asset_size[3]==ST_TEMPLATE_BYTES&&asset_size[4]==64UL&&a<q.capacity&&n<=q.capacity-a;
}
static br_u8 match(br_u16 n){br_u16 i,off;
 static const br_u8 basic[14]={1,8,11,8,10,0,0x9e,'2','0','6','1',0,0,0};
 if(q.kind==4u||q.kind==6u)return !q.at&&!q.relative&&n==64u&&!memcmp(nf_sector,q.kind==4u?expected_d64s:expected_d64l,64u);
 if(q.kind==3u){
  if(!q.relative&&memcmp(nf_sector,basic,14u))return 0;
  if(q.relative<=RP_CONTROL&&RP_CONTROL-q.relative<n){off=RP_CONTROL-q.relative;if(n-off<131u)return 0;
   for(i=0;i<131u;++i)if(nf_sector[off+i]!=(i==0u||i==3u?255u:i==1u?28u:i==2u?223u:0u))return 0;
  }
 }return 1;
}
#endif
static void publish(void){sl_result.state=q.state;sl_result.error=q.error;sl_result.phase=q.phase;sl_result.leaf=q.leaf;sl_result.transport=q.transport;sl_result.cleanup=q.waiting||!bc_files_closed();}
#if DOS64_FILE_DIAGNOSTICS
static const br_u8 sf_source_ops[]={0,1,2,0,3,6,5,4,1,2,3,6,5,4};
#endif
static void first(br_u8 e){if(!q.error){q.error=e;
#if DOS64_FILE_DIAGNOSTICS
 if(q.kind==7u){memcpy(sf_name,"START.INO",10);sf_op=sf_source_ops[q.phase];sf_code=q.error;sf_leaf=q.leaf;sf_transport=q.transport;}
#endif
}}
static void failed(void){q.state=SL_FAILED;q.valid=0;}
static br_u8 eof(void){return (q.phase==EOF1||q.phase==EOF2)&&br_result.error==BR_COUNT&&br_result.known&&!br_result.actual&&!br_result.transport&&br_result.handle==1;}
static void sample(void){if(!ps_clock_poll())q.clock_bad=q.clock_failed=1;else q.now=ps_ticks;}
static void cancel(br_u8 e){first(e);q.cancelled=1;if(q.waiting&&q.phase!=CLOSE1&&q.phase!=CLOSE2){br_now=q.now;bc_slot=0;bc_cancel();}}
static void service(void){sample();if(q.clock_bad)cancel(SL_CLOCK);if(ps_key_poll()&&ps_key==27)cancel(SL_CANCEL);if(ns_io_owner!=0xa5||ns_capacity!=q.capacity||ns_io_error)cancel(SL_DMA);if(ns_cancel)cancel(SL_CANCEL);if(!q.cancelled&&(br_u16)(q.now-q.began)>=q.timeout)cancel(SL_TIMEOUT);}
static void observe(void){br_now=q.now;bc_slot=0;bc_poll();if(br_result.error&&!eof()){if(!q.error){q.leaf=br_result.error;q.transport=br_result.transport;}first(SL_FILE);}if(br_result.state!=BR_BUSY){q.waiting=0;if(q.phase==EOF1||q.phase==EOF2){if(br_result.state!=BR_FAILED||!eof())first(SL_FILE);}else if(br_result.state!=BR_DONE||br_result.error||br_result.handle==2)first(SL_FILE);}}
static br_u8 op(br_u8 phase,br_u8 command,br_u32 a,br_u16 n){
 memset(&br_request,0,sizeof(br_request));br_request.op=command;br_request.mode=1;br_request.address=a;br_request.length=n;if(command==BR_OPEN)memcpy(br_request.path,path,128);
 br_now=q.now;bc_slot=0;if(!bc_start()){if(!q.error){q.leaf=br_result.error?br_result.error:br_result.rejected;q.transport=br_result.transport;}first(SL_FILE);failed();return 0;}
 q.phase=phase;q.waiting=1;q.began=q.now;q.steps=0;return 1;
}
static br_u8 read(br_u32 a,br_u8*b,br_u16 n){if(nf_store_read(a,b,n)!=n){first(SL_DMA);failed();return 0;}return 1;}
#if DOS64_SETUP_SMALL_UCI
extern br_u8 sl_copy_code(void);
br_u8 sl_install(void){
 if(q.installed||(*(br_u8*)1&7u)!=5u||so_state()!=SO_IDLE||!sl_copy_code())return 0;
 q.installed=0xa5;return 1;
}
#else
br_u8 sl_install(void){br_u16 n=(br_u16)&_HIGH_CODE_SIZE__;br_u8*to=&_HIGH_CODE_RUN__;const br_u8*from=&_HIGH_CODE_LOAD__;
 if(q.installed||(*(br_u8*)1&7u)!=5u||so_state()!=SO_IDLE)return 0;memcpy(to,from,n);if(memcmp(to,from,n))return 0;
#if DOS64_SETUP_SMALL_UCI
 n=(br_u16)&_AUX_CODE_SIZE__+(br_u16)&_AUX_RO_SIZE__;to=&_AUX_CODE_RUN__;from=&_AUX_CODE_LOAD__;
 memcpy(to,from,n);if(memcmp(to,from,n))return 0;
#endif
 q.installed=0xa5;return 1;
}
#endif
br_u8 sl_begin(void){br_u16 offset,n,generation; br_u32 identity; br_u8 kind=sl_kind;
 if(q.installed!=0xa5||kind>=SL_KIND_COUNT||!sl_timeout||sl_timeout>=0x8000u||(q.state!=SL_IDLE&&q.state!=SL_DONE)||!bc_files_closed()||!so_ui_ticket()||ns_io_owner!=0xa5||ns_capacity!=so_capacity()||ns_io_error||ns_cancel)return 0;
 sq_page=0;if(sq_read()!=512u)return 0;memcpy(&generation,sq_bytes+8,2);
#if DOS64_SETUP_COLD_INVENTORY
 if((q.valid||inventory_valid)&&generation!=q.generation)return 0;
#else
 if(q.valid&&generation!=q.generation)return 0;
#endif
 if(kind<3){offset=160u+(br_u16)kind*128u;n=512u-offset;if(n>128u)n=128u;memcpy(path,sq_bytes+offset,n);}
 else {memcpy(d64_path_source,sq_bytes+32,128);memset(d64_path_relative,0,128);memcpy(d64_path_relative,
#if DOS64_SETUP_RELEASE_PREFLIGHT
 asset_name[kind_asset[kind]],
#else
 kind==3?"START.TPL":"START.REL",
#endif
 9);if(!d64_path_join())return 0;memcpy(path,d64_path_output,128);}
 sq_page=1;if(sq_read()!=192u)return 0;memcpy(&identity,sq_bytes+188,4);if(kind==2)memcpy(path+96,sq_bytes,32);
#if DOS64_SETUP_COLD_INVENTORY
 if((q.valid||inventory_valid)&&(identity!=q.identity||(kind<8u?(q.valid&(1u<<kind)):(inventory_valid&(1u<<(kind-8u))))))return 0;
#else
 if(q.valid&&(identity!=q.identity||(q.valid&(1u<<kind))))return 0;
#endif
 memcpy(d64_path_source,path,128);if(!d64_path_parent())return 0;
 bc_config[0].owner=0xa5;bc_config[0].target=1;bc_config[0].capacity=so_capacity();memcpy(bc_config[0].root,d64_path_output,128);
 bc_slot=0;if(!bc_clear_error()||!c32_init())return 0;
 q.ticket=so_ui_ticket();if(!q.ticket)return 0;
 q.capacity=so_capacity();q.timeout=sl_timeout;q.generation=generation;q.identity=identity;q.kind=kind;q.state=SL_BUSY;q.error=q.leaf=q.transport=q.waiting=q.cancelled=q.clock_bad=q.clock_failed=q.second=0;q.steps=q.bad_steps=0;q.at=0;q.raw=0xffffffffUL;
 
#if DOS64_SETUP_RELEASE_PREFLIGHT
 if(!bound()){first(SL_INPUT);failed();publish();return 0;}
#endif
 sample();q.began=q.now;service();if(q.error){failed();publish();return 0;}op(OPEN1,BR_OPEN,0,0);publish();return q.state==SL_BUSY;
}
void sl_poll(void){br_u16 n;
 if(q.state!=SL_BUSY){publish();return;}q.clock_bad=0;sample();if(q.waiting)observe();service();
 if(++q.steps==0){first(SL_TIMEOUT);failed();publish();return;}
 if(q.waiting){if(q.clock_failed&&++q.bad_steps>=256u){first(SL_CLOCK);failed();}publish();return;}
 if(q.error){failed();publish();return;}
 switch(q.phase){
 case OPEN1:op(INFO1,BR_INFO,0,0);break;
 case OPEN2:op(INFO2,BR_INFO,0,0);break;
 case INFO1:case INFO2:
  if(!br_result.known||br_result.size!=size(q.kind)){first(SL_FILE);failed();break;}q.at=0;q.relative=q.wanted=0;q.phase=q.second?LOAD2:POISON;q.began=q.now;break;
 case POISON:
  if(q.at==size(q.kind)){op(q.second?EOF2:EOF1,BR_LOAD,READBACK,1);break;}
  if(!q.wanted){q.wanted=size(q.kind)-q.at>32768UL?32768u:(br_u16)(size(q.kind)-q.at);q.relative=0;}
  if(q.relative==q.wanted){q.relative=0;op(q.second?LOAD2:LOAD1,BR_LOAD,q.second?READBACK:address(q.kind)+q.at,q.wanted);break;}
  n=q.wanted-q.relative>512u?512u:q.wanted-q.relative;memset(nf_sector,q.second?0x5a:0xa5,n);memset(so_scratch,q.second?0xa5:0x5a,n);
  if(nf_store_write((q.second?READBACK:address(q.kind)+q.at)+q.relative,nf_sector,n)!=n||!read((q.second?READBACK:address(q.kind)+q.at)+q.relative,so_scratch,n)||memcmp(nf_sector,so_scratch,n)){first(SL_DMA);failed();break;}
  q.relative+=n;q.began=q.now;q.steps=0;break;
 case LOAD1:if(!br_result.known||br_result.actual!=q.wanted){first(SL_FILE);failed();break;}q.relative=0;q.phase=HASH1;q.began=q.now;break;
 case LOAD2:
  if(q.at==size(q.kind)){op(EOF2,BR_READ,0,1);break;}q.wanted=size(q.kind)-q.at>512UL?512u:(br_u16)(size(q.kind)-q.at);op(COMPARE,BR_READ,0,q.wanted);break;
 case HASH1:
  if(q.relative==q.wanted){q.at+=q.wanted;q.wanted=q.relative=0;q.phase=POISON;q.began=q.now;break;}
  n=q.wanted-q.relative>512u?512u:q.wanted-q.relative;
  if(!read(address(q.kind)+q.at+q.relative,nf_sector,n))break;
  if(q.second){if(!read(READBACK+q.relative,so_scratch,n))break;if(memcmp(nf_sector,so_scratch,n)){first(SL_COMPARE);failed();break;}}
  else {
#if DOS64_SETUP_RELEASE_PREFLIGHT
   if(q.kind>=3u&&!match(n)){first(SL_RELEASE);failed();break;}
#endif
   c32_crc=q.raw;c32_address=(br_u16)nf_sector;c32_length=n;if(!c32_update()){first(SL_COMPARE);failed();break;}q.raw=c32_crc;}
  q.relative+=n;q.began=q.now;q.steps=0;break;
 case COMPARE:
  if(!br_result.known||br_result.actual!=q.wanted){first(SL_FILE);failed();break;}if(!read(address(q.kind)+q.at,nf_sector,q.wanted))break;if(memcmp(nf_sector,uci_data,q.wanted)){first(SL_COMPARE);failed();break;}q.at+=q.wanted;q.phase=LOAD2;q.began=q.now;q.steps=0;break;
 case EOF1:op(CLOSE1,BR_CLOSE,0,0);break;
 case EOF2:op(CLOSE2,BR_CLOSE,0,0);break;
 case CLOSE1:
  if(!bc_files_closed()){first(SL_FILE);failed();break;}bc_slot=0;if(!bc_clear_error()){first(SL_FILE);failed();break;}q.second=1;op(OPEN2,BR_OPEN,0,0);break;
 case CLOSE2:
  if(!bc_files_closed()||so_ui_ticket()!=q.ticket){first(SL_INPUT);failed();break;}service();if(q.error){failed();break;}
#if DOS64_SETUP_RELEASE_PREFLIGHT
  if(q.kind>=3u&&(q.raw^0xffffffffUL)!=asset_crc[kind_asset[q.kind]]){first(SL_RELEASE);
#if DOS64_FILE_DIAGNOSTICS
   sf_op=6u; /* Actual final whole-file CRC comparison, after known CLOSE. */
#endif
   failed();break;}
  if(q.kind<5u)
#endif
  q.crc[q.kind]=q.raw^0xffffffffUL;
#if DOS64_SETUP_COLD_INVENTORY
  if(q.kind>=8u)inventory_valid|=1u<<(q.kind-8u);else
#endif
  q.valid|=1u<<q.kind;q.state=SL_DONE;break;
 default:first(SL_INPUT);failed();break;
 }publish();
}
void sl_cancel(void){if(q.state==SL_BUSY){q.clock_bad=0;sample();if(q.waiting)observe();cancel(SL_CANCEL);if(!q.waiting)failed();}publish();}
#if DOS64_SETUP_COLD_INVENTORY
br_u8 sl_inventory_fact(void){return q.installed==0xa5&&q.state==SL_DONE&&!q.error&&q.valid==255u&&inventory_valid==7u&&sl_generation==q.generation&&sl_identity==q.identity;}
#endif
#pragma code-name(push,"HIGH_CODE")
br_u8 sl_state(void){return q.state;}
br_u8 sl_error(void){return q.error;}
br_u8 sl_fact(void){br_u8 k=sl_kind;if(q.installed!=0xa5||q.state==SL_BUSY||q.state==SL_FAILED||k>=5||!(q.valid&(1u<<k))||sl_generation!=q.generation||sl_identity!=q.identity)return 0;sl_receipt.generation=q.generation;sl_receipt.identity=q.identity;sl_receipt.bytes=k<3?368640UL:k==3?ST_TEMPLATE_BYTES:64UL;sl_receipt.crc=q.crc[k];return 1;}
#pragma code-name(pop)
