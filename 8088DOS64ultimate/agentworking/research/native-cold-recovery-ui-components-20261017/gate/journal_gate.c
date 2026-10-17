#pragma code-name("RECOVER_CODE")
#pragma rodata-name("RECOVER_RO")
#pragma bss-name("RECOVER_BSS")
#include "journal_gate.h"
#include "bulk_uci.h"
#include "install_config.h"
#include "startup_close.h"
#include "platform.h"
#include "crc32.h"
#include "prefix.h"
#include <string.h>
extern br_u8 files_handle,files_error,files_target,files_owned_target;
extern br_u16 lc_dma_c64,lc_dma_length;
extern br_u32 lc_dma_reu;
extern br_u8 lc_dma_direction,lc_dma(void),jg_initialized;
char jg_home[128];
br_u8 jg_state_observed,jg_error_observed,jg_cleanup_observed;
static char home[128],image[128],path[128];
static br_u8 buffer[256],compare[256],header[128];
static struct br_result_t leaf;
static br_u32 position,size,crc,image_crc,journal_crc,old_body_crc,new_body_crc;
static br_u16 now,steps,drain;
static br_u8 state,error,cleanup,classification,kind,phase,waiting,opened,close_attempt;
static br_u8 cancel_requested,clock_requested,clock_failed,aborted,absent,equal_old,equal_new,consumed;
static br_u16 count;
#define K_JOURNAL 1u
#define K_CURRENT 2u
#define K_IMAGE 3u
#define P_OPEN 1u
#define P_INFO 2u
#define P_READ 3u
#define P_EOF 4u
#define P_CLOSE 5u
#define P_SAFE 6u
#define P_VALIDATE 7u
#define E_FILE 1u
#define E_FORMAT 2u
#define E_CONFLICT 3u
#define E_CRC 4u
#define E_CANCEL 5u
#define E_CLOCK 6u
#define E_DMA 7u
#define E_STEPS 8u
#define E_OWNER 9u
static void publish(void){jg_state_observed=state;jg_error_observed=error;jg_cleanup_observed=cleanup;}
static void first(br_u8 e){if(!error)error=e;}
static br_u32 wide(const br_u8*p){return (br_u32)p[0]|((br_u32)p[1]<<8)|((br_u32)p[2]<<16)|((br_u32)p[3]<<24);}
static br_u8 status(const char*p,br_u8 n){return !uci_flags&&!(uci_last_status&0x10u)&&uci_status_len==n&&!memcmp(uci_status,p,n);}
static br_u8 missing(void){return phase==P_OPEN&&kind!=K_IMAGE&&leaf.op==BR_OPEN&&leaf.error==BR_STATUS&&!uci_recovery_failed&&(!leaf.transport||(leaf.transport==5u&&files_error==3u&&uci_error==5u))&&status("FILE DOESN'T EXIST",18u);}
static br_u8 eof(void){return phase==P_EOF&&leaf.error==BR_COUNT&&!leaf.transport&&leaf.known&&!leaf.actual&&leaf.handle==1u;}
static br_u8 nofile(void){return (phase==P_SAFE||absent)&&leaf.op==BR_CLOSE&&leaf.error==BR_STATUS&&!leaf.transport&&status("84,NO FILE TO CLOSE",19u);}
static void restore(void){br_result=leaf;br_now=now;}
static void capture(void){leaf=br_result;if(leaf.error&&!missing()&&!eof()&&!nofile())first(E_FILE);}
static br_u8 quiet(void){br_u8 ok;restore();ok=br_ui_acquire();capture();if(!ok)return 0;ok=br_ui_release();capture();return ok&&!files_handle&&!leaf.handle;}
static br_u8 service(void){
 br_u8 ok=ps_clock_poll();if(ok)now=ps_ticks;else{++now;clock_failed=1u;}
 if(!ok||clock_requested){clock_failed=1u;first(E_CLOCK);}
 if(cancel_requested||(ps_key_poll()&&ps_key==27u)){first(E_CANCEL);}
 return !error;
}
static br_u8 dma(br_u8*p,br_u32 at,br_u16 n,br_u8 dir){lc_dma_c64=(br_u16)p;lc_dma_reu=at;lc_dma_length=n;lc_dma_direction=dir;if(!lc_dma()){first(E_DMA);return 0;}return 1;}
static br_u8 fetch(br_u32 at,br_u16 n){memset(buffer,0xa5u,n);memset(compare,0x5au,n);if(!dma(buffer,at,n,1u)||!dma(compare,at,n,1u)||memcmp(buffer,compare,n)){first(E_DMA);return 0;}return service();}
static br_u8 store(br_u32 at,br_u16 n){br_u16 i;if(!dma(buffer,at,n,0u))return 0;for(i=0;i<n;++i)compare[i]=~buffer[i];if(!dma(compare,at,n,1u)||memcmp(buffer,compare,n)){first(E_DMA);return 0;}return service();}
static br_u8 clear_ready(void){buffer[0]=0;return store(0x3ff005UL,1u)&&store(0x3ff505UL,1u);}
static br_u32 crc_bytes(br_u32 c,const br_u8*p,br_u16 n){c32_crc=c;c32_address=(br_u16)p;c32_length=n;if(!c32_update())first(E_CRC);return c32_crc;}
static br_u8 named(const char*name){memcpy(d64_path_source,home,128u);memset(d64_path_relative,0,128u);strcpy((char*)d64_path_relative,name);if(!d64_path_join())return 0;memcpy(path,d64_path_output,128u);return 1;}
static br_u8 configure_path(void){memcpy(d64_path_source,path,128u);if(!d64_path_parent())return 0;memcpy(br_config.root,d64_path_output,128u);br_config.owner=0xa5u;br_config.target=1u;br_config.capacity=0x400000UL;return 1;}
static br_u8 op(br_u8 step,br_u8 command,br_u16 n){restore();memset(&br_request,0,sizeof(br_request));br_request.op=command;br_request.mode=1u;br_request.length=n;if(command==BR_OPEN)memcpy(br_request.path,path,128u);phase=step;if(!br_start()){capture();first(E_FILE);return 0;}capture();waiting=1u;if(command==BR_OPEN)opened=1u;return 1;}
static br_u8 file(br_u8 what){kind=what;position=0;crc=0xffffffffUL;absent=0;close_attempt=0;if(what==K_JOURNAL){size=1284UL;if(!named("DOS64.JRN"))return 0;}else if(what==K_CURRENT){size=576UL;if(!named("DOS64.CFG"))return 0;equal_old=equal_new=1u;}else{size=368640UL;memcpy(path,image,128u);}if(!configure_path()){first(E_FORMAT);return 0;}return op(P_OPEN,BR_OPEN,0);}
static void terminal(void){state=JG_FAILED;publish();}
static void observe(void){if(!waiting)return;restore();br_poll();capture();if(leaf.state!=BR_BUSY)waiting=0;}
static void cleanup_poll(void){
 if(!waiting&&(phase==P_CLOSE||phase==P_SAFE)&&!files_handle&&!leaf.handle&&((leaf.state==BR_DONE&&!leaf.error)||nofile()))opened=0;
 if(++drain>=256u){cleanup=1u;terminal();return;}
 if(waiting){if(phase!=P_CLOSE&&phase!=P_SAFE&&!aborted){aborted=1u;restore();br_cancel();capture();}publish();return;}
 if(opened||files_handle||leaf.handle){
  if(phase==P_CLOSE||phase==P_SAFE||close_attempt){cleanup=1u;terminal();return;}
  close_attempt=1u;if(!op(P_SAFE,BR_CLOSE,0)){cleanup=1u;terminal();}publish();return;
 }
 cleanup=!quiet();terminal();
}
static br_u8 copy_cfg(br_u32 at){br_u16 i,n;for(i=0;i<576u;i+=256u){n=576u-i;if(n>256u)n=256u;if(!fetch(at+i,n))return 0;memcpy(d64_cfg_input+i,buffer,n);}if(!d64_config_validate()||memcmp(d64_cfg_output+8u,home,128u)){first(E_FORMAT);return 0;}return 1;}
static br_u8 allowed_change(br_u16 off,br_u8 a,br_u8 b){br_u16 start=header[8]?264u:136u;if(off>=start&&off<start+128u)return 1;if(off>=572u)return 1;if(off==524u)return !((a^b)&~(header[8]?2u:1u));start=header[8]?532u:528u;return off>=start&&off<start+4u;}
static br_u8 validate(void){
 br_u16 i,n,start;static const br_u8 shape[7]={0xd0,2,0x28,0,2,9,1};
 if(memcmp(header,"D64J\1\4\5",7u)||header[7]||header[8]>1u||header[9]>1u||!(header[10]|header[11])){first(E_FORMAT);return 0;}
 for(i=58u;i<128u;++i)if(header[i]){first(E_FORMAT);return 0;}
 start=12u+(header[8]?10u:0u);if(header[start]||header[start+1u]||(header[start+2u]!=0x10u&&header[start+2u]!=0x18u&&header[start+2u]!=0x38u)||memcmp(header+start+3u,shape,7u)){first(E_FORMAT);return 0;}
 if(!copy_cfg(0x3e0680UL)||!(d64_cfg_output[525]&(header[8]?2u:1u))){first(E_FORMAT);return 0;}old_body_crc=wide(d64_cfg_input+572u);if(!copy_cfg(0x3e08c0UL)){first(E_FORMAT);return 0;}new_body_crc=wide(d64_cfg_input+572u);
 start=header[8]?264u:136u;memcpy(image,d64_cfg_output+start,128u);start=header[8]?532u:528u;image_crc=wide(header+54u);
 if(wide(d64_cfg_output+start)!=image_crc||!!(d64_cfg_output[524]&(header[8]?2u:1u))!=header[9]){first(E_FORMAT);return 0;}
 for(start=0;start<576u;start+=256u){n=576u-start;if(n>256u)n=256u;if(!fetch(0x3e0680UL+start,n))return 0;memcpy(d64_cfg_input,buffer,n);if(!fetch(0x3e08c0UL+start,n))return 0;for(i=0;i<n;++i)if(buffer[i]!=d64_cfg_input[i]&&!allowed_change(start+i,d64_cfg_input[i],buffer[i])){first(E_FORMAT);return 0;}}
 return file(K_CURRENT);
}
static br_u8 current_part(void){br_u16 i;memcpy(d64_cfg_input,buffer,count);if(!fetch(0x3e0680UL+position,count))return 0;for(i=0;i<count;++i)if(buffer[i]!=d64_cfg_input[i])equal_old=0;if(!fetch(0x3e08c0UL+position,count))return 0;for(i=0;i<count;++i)if(buffer[i]!=d64_cfg_input[i])equal_new=0;memcpy(buffer,d64_cfg_input,count);return store(0x3e1000UL+position,count);}
static void closed_file(void){
 opened=0;
 if(!quiet()){first(E_OWNER);cleanup=1u;terminal();return;}
 if(kind==K_JOURNAL){if(absent){classification=JG_NONE;state=JG_DONE;}else phase=P_VALIDATE;}
 else if(kind==K_CURRENT){if(absent)classification=JG_MISSING;else if(equal_old)classification=JG_OLD;else if(equal_new)classification=JG_NEW;else{first(E_CONFLICT);terminal();return;}if(!file(K_IMAGE))terminal();}
 else{if((crc^0xffffffffUL)!=image_crc){first(E_CRC);terminal();return;}state=JG_DONE;}
 publish();
}
br_u8 jg_begin(void){
 br_u16 i;if(!jg_initialized||state||!sc_ready()||files_handle)return 0;leaf=br_result;if(!quiet())return 0;
 memcpy(home,jg_home,128u);for(i=0;i<128u&&home[i];++i){}if(i<2u||i>117u||i==128u)return 0;for(++i;i<128u;++i)if(home[i])return 0;
 if(!named("DOS64.JRN"))return 0;
 c32_crc=0xffffffffUL;c32_address=0x6000u;c32_length=JG_PREFIX_BYTES;if(!c32_update()||(c32_crc^0xffffffffUL)!=JG_PREFIX_CRC)return 0;
 state=JG_BUSY;steps=drain=0;error=cleanup=waiting=opened=cancel_requested=clock_requested=clock_failed=aborted=consumed=0;
 if(!service()||!clear_ready()||!file(K_JOURNAL)){if(!error)first(E_FORMAT);terminal();}
 publish();return 1;
}
void jg_poll(void){
 br_u8 clock_ok;if(state!=JG_BUSY){publish();return;}
 if(++steps==0u){first(E_STEPS);cleanup=1u;terminal();return;}
 clock_ok=ps_clock_poll();if(clock_ok)now=ps_ticks;else{++now;clock_failed=1u;}
 observe();
 if(!clock_ok||clock_requested){clock_failed=1u;first(E_CLOCK);}
 if(cancel_requested||(ps_key_poll()&&ps_key==27u)){first(E_CANCEL);}
 if(error){cleanup_poll();return;}
 if(waiting){publish();return;}
 if(phase==P_VALIDATE){if(!validate()&&!error)first(E_FORMAT);if(error)cleanup_poll();publish();return;}
 if(phase==P_OPEN){if(missing()){absent=1u;if(!op(P_CLOSE,BR_CLOSE,0)){cleanup=1u;terminal();}return;}if(leaf.state!=BR_DONE||leaf.error||leaf.handle!=1u){first(E_FILE);cleanup_poll();return;}if(!op(P_INFO,BR_INFO,0))cleanup_poll();return;}
 if(phase==P_INFO){if(leaf.state!=BR_DONE||leaf.error||!leaf.known||leaf.size!=size){first(E_FORMAT);cleanup_poll();return;}}
 else if(phase==P_READ){
  if(leaf.state!=BR_DONE||leaf.error||!leaf.known||leaf.actual!=count){first(E_FILE);cleanup_poll();return;}
  memcpy(buffer,uci_data,count);
  if(kind==K_JOURNAL){if(!position)memcpy(header,buffer,128u);if(position<1280UL)crc=crc_bytes(crc,buffer,count);else if((crc^0xffffffffUL)!=wide(buffer)){first(E_CRC);cleanup_poll();return;}if(position==1280UL)journal_crc=wide(buffer);if(!store(0x3e0600UL+position,count)){cleanup_poll();return;}}
  else if(kind==K_CURRENT){if(!current_part()){cleanup_poll();return;}}
  else crc=crc_bytes(crc,buffer,count);
  position+=count;
 }else if(phase==P_EOF){if(leaf.state!=BR_FAILED||!eof()){first(E_FILE);cleanup_poll();return;}if(!op(P_CLOSE,BR_CLOSE,0)){first(E_FILE);cleanup=1u;terminal();}return;}
 else if(phase==P_CLOSE){if((leaf.state!=BR_DONE||leaf.error)&&!nofile()){first(E_FILE);cleanup_poll();return;}closed_file();return;}
 else{first(E_FILE);cleanup_poll();return;}
 if(error){cleanup_poll();return;}
 if(position==size){if(!op(P_EOF,BR_READ,1u))cleanup_poll();}
 else{count=(br_u16)(size-position);if(size-position>256UL)count=256u;if(!op(P_READ,BR_READ,count))cleanup_poll();}
 publish();
}
void jg_cancel(void){if(state==JG_BUSY)cancel_requested=1u;}
void jg_clock_fail(void){if(state==JG_BUSY)clock_requested=1u;}
br_u8 jg_state(void){publish();return state;}
br_u8 jg_error(void){publish();return error;}
br_u8 jg_cleanup(void){publish();return cleanup;}
br_u8 jg_class(void){return state==JG_DONE&&!error&&!cleanup?classification:255u;}
br_u8 jg_boot_ready(void){if(consumed||state!=JG_DONE||error||cleanup||classification!=JG_NONE||opened||!quiet()||!sc_ready()||!service())return 0;consumed=1u;return 1;}

/* Additive cold recovery receipt; private authority, one-shot, no boot grant.
 * 0 class;1..128 canonical home;129..132 checked JRN body CRC;133..136 image CRC;
 * 137..138 sequence;139..142 OLD CFG body identity;143..146 NEW body identity.
 * Each CFG identity is copied from its separately validated body checksum,
 * never the fixed residue of a whole self-checksummed CFG codeword. */
br_u8 __fastcall__ jg_recovery_copy(br_u8 *out){
 if(consumed||state!=JG_DONE||error||cleanup||classification==JG_NONE||classification>JG_MISSING||opened||!sc_ready()||!quiet()||!service())return 0;
 consumed=1u;out[0]=classification;memcpy(out+1u,home,128u);memcpy(out+129u,&journal_crc,4u);memcpy(out+133u,&image_crc,4u);memcpy(out+137u,header+10u,2u);memcpy(out+139u,&old_body_crc,4u);memcpy(out+143u,&new_body_crc,4u);return 1;
}
