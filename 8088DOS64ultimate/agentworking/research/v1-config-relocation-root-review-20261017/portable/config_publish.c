#include "config_publish.h"
#include "config_ui.h"
#include "media_reinspect.h"
#include "bulk_context.h"
#include "bulk_uci.h"
#include "install_config.h"
#include "platform.h"
#include "crc32.h"
#include "release_patch.h"
#include <string.h>
#pragma code-name("CONFIG_HIGH")
#pragma rodata-name("CONFIG_HRO")
#include "release_assets.h"
#ifndef RP_TEMPLATE_BYTES
#define RP_TEMPLATE_BYTES 18432u
#endif
#define OPEN 1u
#define INFO 2u
#define LOAD 3u
#define REWIND 4u
#define DATA 5u
#define END_READ 6u
#define CLOSE 7u
#define SAVE 8u
#define READ_OPEN 9u
#define PREPARE 10u
#define OUTPUT_START 0x2b8000UL
#define OUTPUT_CFG 0x2bf000UL
#define OUTPUT_INI 0x2bf400UL
#if DOS64_SETUP_COLD_INVENTORY
#define CP_INI 7u
#define CP_CFG 8u
#define CP_SOURCES 8u
#define CP_OUTPUTS 9u
#define CP_SOURCE_MASK 255u
#else
#define CP_INI 4
#define CP_CFG 5
#define CP_SOURCES 5u
#define CP_OUTPUTS 6u
#define CP_SOURCE_MASK 31u
#endif
#pragma bss-name("CONFIG_PUBSTATE")
static br_u8 cfg[576];
br_u8 rp_buffer[512];
#define io rp_buffer
#pragma bss-name("BSS")
struct cp_request_t cp_request;
struct cp_result_t cp_result;
static char release_root[128],new_root[128];
static br_u8 state,error,phase,file,leaf,transport,mask,output,waiting,close_attempt,cancelled,clock_bad,slot,columns,ini_length,source_mask,patch_consumed;
static br_u16 timeout,now,last,began,steps,drain_steps,wanted,session;
static br_u32 capacity,identity,size,position,raw,checksum,start_crc,ini_crc;
extern br_u8 cp_high_ready;
extern br_u16 rm_dma_c64,rm_dma_length;
extern br_u32 rm_dma_reu;
extern br_u8 rm_dma_direction,rm_dma(void);
#if DOS64_SETUP_COLD_INVENTORY
static br_u8 extra_mask;
#pragma rodata-name("RODATA")
static const char output_name[9][13]={"DOS64.PRG","DOS64.REL","START.INO","START.PRG","DOS64.MNU","START.RCV","START.RFW","DOS64.INI","DOS64.CFG"};
#pragma rodata-name("CONFIG_HRO")
#pragma code-name("CONFIG_HIGH")
static br_u8 output_asset(void){return file<4u?file:file+1u;}
#pragma code-name("CODE")
static br_u8 complete(void){return mask==63u&&extra_mask==7u;}
#define incomplete() (!complete())
static void mark(void){if(file>=4u&&file<=6u)extra_mask|=1u<<(file-4u);else mask|=1u<<(file<4u?file:file-3u);}
#pragma code-name("CONFIG_HIGH")
#else
#define complete() (mask==63)
#define incomplete() (mask!=63)
#define mark() (mask|=1u<<file)
static const char *const output_name[6]={"DOS64.PRG","DOS64.REL","START.INO","START.PRG","DOS64.INI","DOS64.CFG"};
#endif
static br_u32 wide(const br_u8*p){return (br_u32)p[0]|((br_u32)p[1]<<8)|((br_u32)p[2]<<16)|((br_u32)p[3]<<24);}
static void put(br_u8*p,br_u32 v){br_u8 i;for(i=0;i<4;++i){p[i]=(br_u8)v;v>>=8;}}
static void first(br_u8 e){if(!error)error=e;}
static void publish(void){cp_result.state=state;cp_result.error=error;cp_result.stage=phase;cp_result.file=file;cp_result.leaf=leaf;cp_result.transport=transport;cp_result.cleanup=state==CP_BUSY||!bc_files_closed();cp_result.mask=mask;cp_result.identity=identity;}
static void sample(void){if(!ps_clock_poll())clock_bad=1;else{now=ps_ticks;if((br_u16)(now-last)>=0x8000u)clock_bad=1;last=now;}}
static void config(void){bc_slot=slot;bc_config[slot].owner=0xa5;bc_config[slot].target=slot+1;bc_config[slot].capacity=capacity;memcpy(bc_config[slot].root,slot?new_root:release_root,128);br_now=now;}
static br_u8 eof(void){return phase==END_READ&&br_result.op==BR_READ&&br_result.state==BR_FAILED&&br_result.error==BR_COUNT&&br_result.known&&!br_result.actual&&!br_result.transport&&br_result.handle==1&&!uci_data_len&&!uci_flags&&!(uci_last_status&0x10);}
static void observe(void){br_u8 expected;if(!waiting)return;config();bc_poll();expected=eof();if(br_result.error&&!expected){if(!error){leaf=br_result.error;transport=br_result.transport;}first(CP_FILE);}if(br_result.state!=BR_BUSY){waiting=0;if(phase==END_READ){if(!expected)first(CP_FILE);}else if(br_result.state!=BR_DONE||br_result.error)first(CP_FILE);}}
static void abort_once(void){if(cancelled)return;cancelled=1;if(waiting&&phase!=CLOSE){config();bc_cancel();}}
static void stop(br_u8 e){first(e);abort_once();}
static void service(void){sample();if(ps_key_poll()&&ps_key==27)stop(CP_CANCEL);if(clock_bad)stop(CP_CLOCK);if((br_u16)(now-began)>=timeout)stop(CP_TIMEOUT);}
static br_u8 dma(br_u32 address,br_u16 length,br_u8 direction,br_u8*buffer){rm_dma_c64=(br_u16)buffer;rm_dma_reu=address;rm_dma_length=length;rm_dma_direction=direction;if(!length||length>512||address>=capacity||length>capacity-address||!rm_dma()){first(CP_DMA);return 0;}return 1;}
static br_u8 feed(br_u8*p,br_u16 n){c32_crc=raw;c32_address=(br_u16)p;c32_length=n;if(!c32_update()||c32_error){first(CP_DMA);return 0;}raw=c32_crc;return 1;}
static br_u32 address(void){if(!output)return asset_reu[file];
#if DOS64_SETUP_COLD_INVENTORY
return file<3u||(file>=4u&&file<=6u)?asset_reu[output_asset()]:(file==3?OUTPUT_START:(file==CP_INI?OUTPUT_INI:OUTPUT_CFG));
#else
return file<3?asset_reu[file]:(file==3?OUTPUT_START:(file==4?OUTPUT_INI:OUTPUT_CFG));
#endif
}
static br_u32 expected_crc(void){if(!output)return asset_crc[file];
#if DOS64_SETUP_COLD_INVENTORY
return file<3u||(file>=4u&&file<=6u)?asset_crc[output_asset()]:(file==3?start_crc:(file==CP_INI?ini_crc:checksum));
#else
return file<3?asset_crc[file]:(file==3?start_crc:(file==4?ini_crc:checksum));
#endif
}
static void make_ini(void){static const br_u8 text[]="[emulator]\r\ninitial_columns=80\r\n";ini_length=sizeof(text)-1;memcpy(io,text,ini_length);if(columns==40)io[28]='4';}
static br_u8 alias(const char*a,const char*b){br_u8 i,x,y;for(i=0;i<128;++i){x=a[i];y=b[i];if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return 0;if(!x)return 1;}return 1;}
static br_u8 operation(br_u8 p,br_u8 op){config();memset(&br_request,0,sizeof(br_request));br_request.op=op;br_request.mode=slot&&p==OPEN?6u:1u;
 if(op==BR_OPEN){memcpy(d64_path_source,slot?new_root:release_root,128);memset(d64_path_relative,0,128);strcpy((char*)d64_path_relative,output?output_name[file]:asset_name[file]);if(!d64_path_join()){first(CP_INPUT);return 0;}memcpy(br_request.path,d64_path_output,128);}
 if(op==BR_LOAD||op==BR_SAVE){br_request.address=address();br_request.length=size;}
 if(op==BR_READ){br_request.length=p==END_READ?1UL:(br_u32)wanted;memset(uci_data,0xa7,512);}
 phase=p;sample();if(clock_bad){first(CP_CLOCK);return 0;}br_now=began=now;steps=0;
 if(!bc_start()){if(!error){leaf=br_result.error?br_result.error:br_result.rejected;transport=br_result.transport;}first(CP_FILE);return 0;}waiting=1;return 1;
}
static void fail(void){state=CP_FAILED;}
static void cleanup(void){if(waiting)return;if(bc_files_closed()){fail();return;}if(!close_attempt){close_attempt=1;if(operation(CLOSE,BR_CLOSE))return;}fail();}
#if DOS64_SETUP_COLD_INVENTORY
static br_u8 begin_file(void){slot=output;position=0;raw=0xffffffffUL;close_attempt=0;
 if(!output)size=asset_size[file];else if(file==CP_INI)size=ini_length;else if(file==CP_CFG)size=576UL;else size=asset_size[output_asset()];
 config();if(!bc_clear_error()){first(CP_OWNER);return 0;}return operation(OPEN,BR_OPEN);}
#else
static br_u8 begin_file(void){slot=output;position=0;raw=0xffffffffUL;close_attempt=0;size=output?(file<3?asset_size[file]:(file==3?asset_size[3]:(file==4?ini_length:576UL))):asset_size[file];config();if(!bc_clear_error()){first(CP_OWNER);return 0;}return operation(OPEN,BR_OPEN);}
#endif
static br_u8 compare_data(void){br_u16 n;if(!br_result.known||br_result.actual!=wanted||uci_data_len!=wanted){first(CP_FILE);return 0;}for(n=0;n<wanted;++n)io[n]=~uci_data[n];if(!dma(address()+position,wanted,1,io)||memcmp(io,uci_data,wanted)){first(CP_COMPARE);return 0;}
 if((!output&&(file==1||file==4))||(output&&file==1)){const br_u8*p=(!output&&file==4)?expected_d64s:expected_d64l;if(memcmp(uci_data,p+(br_u16)position,wanted)){first(CP_ASSET);return 0;}}
 if(output&&file==CP_CFG&&memcmp(uci_data,cfg+(br_u16)position,wanted)){first(CP_CONFIG);return 0;}
 if(output&&file==CP_INI){make_ini();if(memcmp(uci_data,io+(br_u16)position,wanted)){first(CP_CONFIG);return 0;}}
 if(!feed(uci_data,wanted))return 0;service();if(error)return 0;position+=wanted;return 1;
}
static br_u8 stage(br_u32 at,br_u8*p,br_u16 n){br_u16 i;memcpy(io+256,p,n);if(!dma(at,n,0,io+256))return 0;for(i=0;i<n;++i)io[i]=~io[256+i];return dma(at,n,1,io)&&!memcmp(io,io+256,n);}
/* Patcher is callable only through private completed source authority. */
const char *rp_admit(void){if(state!=CP_BUSY||phase!=PREPARE||source_mask!=CP_SOURCE_MASK||patch_consumed||error||!bc_files_closed())return 0;patch_consumed=1;return new_root;}
br_u8 rp_read(br_u16 at,br_u16 n){if(error||at>RP_TEMPLATE_BYTES||n>RP_TEMPLATE_BYTES-at||n>256)return 0;if(!dma(asset_reu[3]+at,n,1,io))return 0;service();return !error;}
br_u8 rp_write(br_u16 at,br_u16 n){br_u16 i;if(error||at>RP_TEMPLATE_BYTES||n>RP_TEMPLATE_BYTES-at||n>256)return 0;if(!dma(OUTPUT_START+at,n,0,io+256))return 0;for(i=0;i<n;++i)io[i]=~io[256u+i];if(!dma(OUTPUT_START+at,n,1,io))return 0;service();return !error;}
static br_u8 crc_reu(br_u32 at,br_u32 count){br_u16 n;raw=0xffffffffUL;while(count){n=count>512?512u:(br_u16)count;memset(io,0xa7,512);if(!dma(at,n,1,io)||!feed(io,n))return 0;at+=n;count-=n;service();if(error)return 0;}return 1;}
static br_u8 prepare(void){br_u16 n,at;phase=PREPARE;sample();began=now;
 memcpy(cfg+8,new_root,128);raw=0xffffffffUL;if(!feed(cfg,572))return 0;identity=raw^0xffffffffUL;put(cfg+572,identity);
#if D64_CONFIG_INPLACE
 d64_cfg_input=cfg;
#else
 memcpy(d64_cfg_input,cfg,576);
#endif
if(!d64_config_validate()||memcmp(d64_cfg_output,cfg,576)){first(CP_CONFIG);return 0;}
 if(!rp_patch()){first(CP_ASSET);return 0;}start_crc=rp_output_crc;
 if(!crc_reu(OUTPUT_START,asset_size[3])||(raw^0xffffffffUL)!=start_crc){first(CP_COMPARE);return 0;}
 make_ini();raw=0xffffffffUL;if(!feed(io,ini_length))return 0;ini_crc=raw^0xffffffffUL;if(!stage(OUTPUT_INI,io,ini_length)){first(CP_COMPARE);return 0;}
 for(at=0;at<576;at+=n){n=576-at>256?256u:576-at;if(!stage(OUTPUT_CFG+at,cfg+at,n)){first(CP_COMPARE);return 0;}}
 raw=0xffffffffUL;if(!feed(cfg,576))return 0;checksum=raw^0xffffffffUL;service();return !error;
}
br_u8 cp_begin(void){br_u8 a;if(state!=CP_IDLE||!cp_high_ready||cp_request.owner!=0xa5||!cp_request.timeout||cp_request.timeout>=0x8000u||(*(br_u8*)0&7u)!=7u||(*(br_u8*)1&7u)!=5u||!cg_get())return 0;
 session=cg_receipt.session;identity=cg_receipt.cfg_identity;capacity=cg_receipt.capacity;columns=cg_receipt.columns;memcpy(release_root,cg_receipt.release_home,128);memcpy(new_root,cg_receipt.new_home,128);rm_query_session=session;memcpy(rm_query_home,cg_receipt.home,128);
 if(!rm_get()||rm_receipt.session!=session||rm_receipt.cfg_identity!=identity||rm_receipt.crc_mask!=(rm_receipt.present&3u)||wide(rm_receipt.cfg+538)!=capacity||capacity<0x400000UL||capacity<OUTPUT_CFG+576UL||(columns!=40&&columns!=80)||alias(new_root,release_root)||alias(new_root,rm_query_home))return 0;
 memcpy(cfg,rm_receipt.cfg,576);for(a=0;a<2;++a)if(rm_receipt.crc_mask&(1u<<a))put(cfg+528u+(br_u16)a*4u,rm_receipt.crc[a]);timeout=cp_request.timeout;if(!ps_clock_poll())return 0;now=last=began=ps_ticks;if(!c32_init())return 0;sample();if(clock_bad)return 0;state=CP_BUSY;file=output=slot=mask=0;if(!begin_file())cleanup();publish();return 1;
}
void cp_poll(void){if(state!=CP_BUSY){publish();return;}sample();observe();if(++steps>=2048u)stop(CP_LIMIT);if(error)abort_once();if(ps_key_poll()&&ps_key==27)stop(CP_CANCEL);if(clock_bad)stop(CP_CLOCK);if((br_u16)(now-began)>=timeout)stop(CP_TIMEOUT);
 if(error){if(waiting){if(++drain_steps>=256u)fail();}else cleanup();publish();return;}if(waiting){publish();return;}
 if(phase==OPEN){if(!operation(output?SAVE:INFO,output?BR_SAVE:BR_INFO))cleanup();}
 else if(phase==INFO){if(!br_result.known||br_result.size!=size){first(CP_SIZE);cleanup();}else if(!operation(output?DATA:LOAD,output?BR_READ:BR_LOAD))cleanup();}
 else if(phase==LOAD){if(!br_result.known||br_result.actual!=size){first(CP_SIZE);cleanup();}else if(!operation(REWIND,BR_SEEK))cleanup();}
 else if(phase==REWIND){wanted=size>512?512u:(br_u16)size;if(!operation(DATA,BR_READ))cleanup();}
 else if(phase==SAVE){if(!br_result.known||br_result.actual!=size){first(CP_SIZE);cleanup();}else{close_attempt=1;if(!operation(CLOSE,BR_CLOSE))cleanup();}}
 else if(phase==READ_OPEN){wanted=size>512?512u:(br_u16)size;if(!operation(INFO,BR_INFO))cleanup();}
 else if(phase==DATA){if(!compare_data())cleanup();else if(position==size){if((raw^0xffffffffUL)!=expected_crc()){first(CP_COMPARE);cleanup();}else if(!operation(END_READ,BR_READ))cleanup();}else{wanted=size-position>512?512u:(br_u16)(size-position);if(!operation(DATA,BR_READ))cleanup();}}
 else if(phase==END_READ){close_attempt=1;if(!operation(CLOSE,BR_CLOSE))cleanup();}
 else if(phase==CLOSE){if(!bc_files_closed()){first(CP_OWNER);fail();}else if(output&&position==0){close_attempt=0;config();if(!bc_clear_error()||!operation(READ_OPEN,BR_OPEN)){first(CP_OWNER);cleanup();}}
  else{service();if(!error){if(output)mark();else source_mask|=1u<<file;++file;if(file==(output?CP_OUTPUTS:CP_SOURCES)){if(!output){if(prepare()){output=1;file=0;if(!begin_file())cleanup();}else cleanup();}else{service();if(!error&&complete()&&bc_files_closed())state=CP_DONE;else first(CP_OWNER);}}else if(!begin_file())cleanup();}}}
 else{first(CP_INPUT);cleanup();}publish();}
void cp_cancel(void){if(state==CP_BUSY){sample();observe();stop(CP_CANCEL);}publish();}
br_u8 cp_state(void){publish();return state;}br_u8 cp_error(void){publish();return error;}br_u8 cp_closed_quiet(void){return state!=CP_BUSY&&bc_files_closed();}
br_u8 cp_get(void){if(state!=CP_DONE||error||incomplete()||!cp_closed_quiet()||!cg_get()||cg_receipt.session!=session||memcmp(cg_receipt.new_home,new_root,128)||memcmp(cg_receipt.release_home,release_root,128)||cg_receipt.columns!=columns)return 0;rm_query_session=session;memcpy(rm_query_home,cg_receipt.home,128);if(!rm_get())return 0;publish();return 1;}
const br_u16 cp_abi_sizes[]={sizeof(struct cp_request_t),sizeof(struct cp_result_t)};
