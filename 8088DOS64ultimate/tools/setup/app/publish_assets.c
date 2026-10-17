#include "file_error.h"
#include "template_limits.h"
#include "publish_assets.h"
#include "setup_overlay.h"
#include "selection_capsule.h"
#include "bulk_context.h"
#include "setup_io.h"
#include "platform.h"
#include "crc32.h"
#include "start_template.h"
#include "pub_config_prefix.h"
#include <string.h>
#if DOS64_ALL_FILE_DIAGNOSTICS
extern const char fd_name_start[],fd_name_cfg[];
#endif
struct pb_result_t pb_result;
static struct pb_result_t ledger;
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
#include "publish_scratch.h"
#include "raw_output.h"
#define input pub_scratch.pb.input
#define output pub_scratch.pb.output
#else
static br_u8 input[256],output[256];
#endif
static br_u8 cached,cancelled,profile;
static br_u16 ticket,generation,last_tick,filled;
static br_u32 capacity,wire_crc,source_size,window,written,output_raw,fact,cfg_identity;
static void publish(void){pb_result=ledger;}
static br_u8 fail(br_u8 error){if(!ledger.error){ledger.error=error;
#if DOS64_ALL_FILE_DIAGNOSTICS
if(!fd_code){fd_op=7;fd_leaf=ledger.detail;fd_transport=0;fd_code=error;}
#endif
}ledger.state=3;publish();return 0;}
static br_u32 wide(const br_u8*p){return (br_u32)p[0]|((br_u32)p[1]<<8)|((br_u32)p[2]<<16)|((br_u32)p[3]<<24);}
static void put(br_u8*p,br_u32 value){br_u8 i;for(i=0;i<4u;++i){p[i]=(br_u8)value;value>>=8;}}
static br_u8 service(void){br_u16 now;
 if(ledger.error)return 0;
 if(!ps_clock_poll())return fail(PB_CLOCK);now=ps_ticks;
 if((br_u16)(now-last_tick)>=0x8000u)return fail(PB_CLOCK);last_tick=now;
 if(cancelled||ns_cancel||(ps_key_poll()&&ps_key==27u))return fail(PB_CANCEL);
 if(ns_io_owner!=0xa5u||ns_capacity!=capacity||ns_io_error)return fail(PB_DMA);
 return 1;
}
static br_u8 crc_feed(br_u32 *raw,const br_u8*p,br_u16 n){c32_crc=*raw;c32_address=(br_u16)p;c32_length=n;if(!c32_update()||c32_error)return fail(PB_CRC);*raw=c32_crc;return 1;}
static br_u8 read(br_u32 at,br_u8*p,br_u16 n){if(!service())return 0;if(nf_store_read(at,p,n)!=n)return fail(PB_DMA);return service();}
static br_u8 write(br_u32 at,const br_u8*p,br_u16 n){if(!service())return 0;if(nf_store_write(at,p,n)!=n)return fail(PB_DMA);return service();}
static br_u8 flush(void){if(!filled)return 1;if(!crc_feed(&output_raw,output,filled)||!write(PB_START+written,output,filled))return 0;written+=filled;filled=0;return 1;}
st_u8 st_read(st_u32 offset){br_u16 n;
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
 if(ledger.state!=1){st_io_error=1;return 0;}
#endif
 if(offset>=source_size){st_io_error=1;fail(PB_DMA);return 0;}
 if(!cached||offset<window||offset-window>=256UL){window=offset&0xffffff00UL;n=source_size-window>256UL?256u:(br_u16)(source_size-window);if(!read(PB_SOURCE+window,input,n)){st_io_error=1;return 0;}cached=1;}
 return input[(br_u8)(offset-window)];
}
void st_write(st_u32 offset,st_u8 value){
#if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
 if(ledger.state!=1){st_io_error=1;return;}
#endif
 if(offset!=written+filled||offset>=source_size){st_io_error=1;fail(PB_DMA);return;}output[filled++]=value;if(filled==256u&&!flush())st_io_error=1;}
static br_u8 verify(br_u32 at,br_u32 size,br_u32 expected){
 br_u16 n;br_u32 raw=0xffffffffUL;
 while(size){
  n=size>256UL?256u:(br_u16)size;
  /* Streaming output is fully flushed before verification. Reuse its buffer
   * for an independent FETCH; different initial bytes expose stale/partial
   * falsely completed DMA instead of allowing a buffer to verify itself. */
  memset(input,0xa5,n);memset(output,0x5a,n);
  if(!read(at,input,n)||!read(at,output,n))return 0;
  if(memcmp(input,output,n))return fail(PB_DMA);
  if(!crc_feed(&raw,input,n))return 0;
  at+=n;size=size-n;
 }
 if((raw^0xffffffffUL)!=expected)return fail(PB_CRC);return 1;
}
static br_u8 get(br_u8 kind){if(!pb_verified_fact(kind,generation,wire_crc,&fact))return fail(PB_FACT);return service();}
static br_u8 joined(br_u16 offset,const char*name){memcpy(pb_codec_path_source,pb_codec_input+D64_CFG_HOME,128);memset(pb_codec_path_relative,0,128);strcpy((char*)pb_codec_path_relative,name);if(!pb_codec_join()){ledger.detail=pb_codec_error;return fail(PB_CONFIG);}memcpy(pb_codec_input+offset,pb_codec_path_output,128);return 1;}
br_u8 pb_build(void){br_u32 expected;
 if(ledger.state){publish();return 0;}
#if DOS64_ALL_FILE_DIAGNOSTICS
 fd_tail=(br_u16)fd_name_cfg; /* PW retained canonical home; construction target, no authority. */
#endif
 ledger.state=1;cancelled=cached=0;filled=0;written=0;output_raw=0xffffffffUL;
 #if defined(DOS64_SETUP_PUBLICATION) && DOS64_SETUP_PUBLICATION
 if(rw_state()!=RW_IDLE)return fail(PB_PHASE);
#endif
 ticket=so_publish_ticket();if(!ticket||!bc_files_closed())return fail(PB_PHASE);capacity=so_capacity();
 if(!ps_clock_poll())return fail(PB_CLOCK);last_tick=ps_ticks;if(!service())return 0;
 sq_page=0;if(sq_read()!=512u){ledger.detail=sq_error();return fail(PB_INPUT);}memset(pb_codec_input,0,D64_CFG_BYTES);memcpy(pb_codec_input+D64_CFG_HOME,sq_bytes+SQ_HOME,128);generation=sq_bytes[8]|((br_u16)sq_bytes[9]<<8);if(wide(sq_bytes+12)!=capacity)return fail(PB_INPUT);
 #if DOS64_ALL_FILE_DIAGNOSTICS
 fd_set_path((char*)pb_codec_input+D64_CFG_HOME);fd_tail=(br_u16)fd_name_cfg;
#endif
 sq_page=1;if(sq_read()!=192u){ledger.detail=sq_error();return fail(PB_INPUT);}profile=sq_bytes[160];wire_crc=wide(sq_bytes+188);
 if(!get(PB_A_BYTES)||fact!=368640UL)return ledger.error?0:fail(PB_FACT);if(!get(PB_A_CRC))return 0;put(pb_codec_input+D64_CFG_A_CRC,fact);
 if(!get(PB_B_BYTES)||fact!=368640UL)return ledger.error?0:fail(PB_FACT);if(!get(PB_B_CRC))return 0;put(pb_codec_input+D64_CFG_B_CRC,fact);
 if(!get(PB_C_BYTES)||fact!=(profile?20971520UL:2097152UL))return ledger.error?0:fail(PB_FACT);
 if(!get(PB_TEMPLATE_BYTES))return 0;source_size=fact;if(source_size!=ST_TEMPLATE_BYTES)return fail(PB_FACT);
 if(!joined(D64_CFG_A,"A.IMG")||!joined(D64_CFG_B,"B.IMG")||!joined(D64_CFG_C,"C.IMG"))return 0;
 pb_codec_input[D64_CFG_PROFILE+2u]=profile;pb_codec_input[D64_CFG_PRESENT]=7;pb_codec_input[D64_CFG_BOOT_ABI]=1;put(pb_codec_input+D64_CFG_REU_BYTES,capacity);
 if(!pb_codec_make()){ledger.detail=pb_codec_error;return fail(PB_CONFIG);}memcpy(pb_codec_input,pb_codec_output,D64_CFG_BYTES);if(!pb_codec_validate()){ledger.detail=pb_codec_error;return fail(PB_CONFIG);}cfg_identity=wide(pb_codec_output+D64_CFG_CRC);ledger.cfg_crc=pb_codec_fast_crc(pb_codec_output,D64_CFG_BYTES);if(c32_error)return fail(PB_CRC);
#if DOS64_ALL_FILE_DIAGNOSTICS
 fd_tail=(br_u16)fd_name_start;
#endif
 if(!read(PB_DESCRIPTOR,st_descriptor,64))return 0;memcpy(st_home,pb_codec_output+D64_CFG_HOME,128);st_base=0xdf1cu;st_template_bytes=source_size;st_cancel=st_io_error=0;
 if(!st_validate()){ledger.detail=st_error;return ledger.error?0:fail(PB_TEMPLATE);}cached=0;
 if(!st_copy_patch()||!flush()){ledger.detail=st_error;return ledger.error?0:fail(PB_TEMPLATE);}expected=output_raw^0xffffffffUL;
 if(written!=source_size||!verify(PB_START,source_size,expected))return ledger.error?0:fail(PB_DMA);
#if DOS64_ALL_FILE_DIAGNOSTICS
 fd_tail=(br_u16)fd_name_cfg;
#endif
 if(!write(PB_CFG,pb_codec_output,D64_CFG_BYTES)||!verify(PB_CFG,D64_CFG_BYTES,ledger.cfg_crc))return 0;
 if(!service()||so_publish_ticket()!=ticket||!bc_files_closed())return ledger.error?0:fail(PB_PHASE);
 ledger.start_crc=expected;ledger.start_bytes=source_size;ledger.state=2;publish();return 1;
}
br_u8 pb_state(void){publish();return ledger.state;}
br_u8 pb_error(void){publish();return ledger.error;}
br_u8 pb_ready(void){publish();return ledger.state==2&&!ledger.error&&so_publish_ticket()==ticket&&bc_files_closed();}
br_u32 pb_cfg_identity(void){return pb_ready()?cfg_identity:0;}
br_u32 pb_cfg_crc(void){return pb_ready()?ledger.cfg_crc:0;}
br_u32 pb_start_crc(void){return pb_ready()?ledger.start_crc:0;}
br_u32 pb_start_bytes(void){return pb_ready()?ledger.start_bytes:0;}
void pb_cancel(void){if(ledger.state==1){cancelled=1;fail(PB_CANCEL);}publish();}
