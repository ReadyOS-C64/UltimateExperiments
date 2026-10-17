#pragma code-name("RF_CODE")
#pragma rodata-name("RF_RO")
#pragma bss-name("RF_BSS")
#include "rollforward.h"
#include "journal_gate.h"
#include "bulk_uci.h"
#include "install_config.h"
#include "startup_close.h"
#include "platform.h"
#include "crc32.h"
#include <string.h>
extern br_u8 files_handle,files_error;
extern br_u16 lc_dma_c64,lc_dma_length;
extern br_u32 lc_dma_reu;
extern br_u8 lc_dma_direction,lc_dma(void);
br_u8 rf_state_observed,rf_error_observed,rf_cleanup_observed;
static br_u8 receipt[147],buffer[256],other[256];
static char path[128],archold[10],archjrn[10];
static struct br_result_t leaf;
static br_u32 size,position,crc;
static br_u16 now,count,steps,drain;
static br_u8 state,error,cleanup,admitted,stage,role,expect,required;
static br_u8 phase,waiting,opened,absent,oldpresent,raw,seen,lease,aborted;
static br_u8 cancel_request,clock_request,clock_bad,have_clock,close_attempt,rename_mask;
#define E_FILE 1u
#define E_FORMAT 2u
#define E_CONFLICT 3u
#define E_CRC 4u
#define E_CANCEL 5u
#define E_CLOCK 6u
#define E_DMA 7u
#define E_BOUND 8u
#define E_OWNER 9u
#define P_OPEN 1u
#define P_INFO 2u
#define P_READ 3u
#define P_EOF 4u
#define P_CLOSE 5u
#define P_SAFE 6u
static void publish(void){rf_state_observed=state;rf_error_observed=error;rf_cleanup_observed=cleanup;}
static void first(br_u8 e){if(!error)error=e;}
static br_u32 wide(const br_u8*p){return (br_u32)p[0]|((br_u32)p[1]<<8)|((br_u32)p[2]<<16)|((br_u32)p[3]<<24);}
static void restore(void){br_result=leaf;br_now=now;}
static br_u8 status(const char*p,br_u8 n){return !uci_flags&&!(uci_last_status&0x10u)&&uci_status_len==n&&!memcmp(uci_status,p,n);}
static br_u8 missing(void){return phase==P_OPEN&&leaf.op==BR_OPEN&&leaf.error==BR_STATUS&&!uci_recovery_failed&&(!leaf.transport||(leaf.transport==5u&&files_error==3u&&uci_error==5u))&&status("FILE DOESN'T EXIST",18u);}
static br_u8 eof(void){return phase==P_EOF&&leaf.error==BR_COUNT&&!leaf.transport&&leaf.known&&!leaf.actual&&leaf.handle==1u;}
static br_u8 nofile(void){return (phase==P_SAFE||absent)&&leaf.op==BR_CLOSE&&leaf.error==BR_STATUS&&!leaf.transport&&status("84,NO FILE TO CLOSE",19u);}
static void capture(void){leaf=br_result;if(leaf.error&&!missing()&&!eof()&&!nofile())first(E_FILE);}
static br_u8 quiet(void){br_u8 ok;restore();ok=br_ui_acquire();capture();if(!ok)return 0;lease=1u;ok=br_ui_release();capture();if(ok)lease=0;return ok&&!files_handle&&!leaf.handle;}
static br_u8 sample(void){br_u16 n;if(!ps_clock_poll()){++now;clock_bad=1;return 0;}n=ps_ticks;if(have_clock&&(br_u16)(n-now)>=0x8000u){now=n;clock_bad=1;return 0;}have_clock=1;now=n;return 1;}
static br_u8 service(void){if(!sample()||clock_request)first(E_CLOCK);if(cancel_request||(ps_key_poll()&&ps_key==27u))first(E_CANCEL);return !error;}
static br_u8 dma(br_u8*p,br_u32 a,br_u16 n,br_u8 direction){lc_dma_c64=(br_u16)p;lc_dma_reu=a;lc_dma_length=n;lc_dma_direction=direction;if(!lc_dma()){first(E_DMA);return 0;}return 1;}
static br_u8 fetch(br_u32 a,br_u16 n){memset(buffer,0xa5u,n);memset(other,0x5au,n);if(!dma(buffer,a,n,1u)||!dma(other,a,n,1u)||memcmp(buffer,other,n)){first(E_DMA);return 0;}return service();}
static br_u8 store(br_u32 a,br_u16 n){br_u16 i;memcpy(buffer,uci_data,n);if(!dma(buffer,a,n,0))return 0;for(i=0;i<n;++i)other[i]=~buffer[i];if(!dma(other,a,n,1)||memcmp(buffer,other,n)){first(E_DMA);return 0;}return service();}
static br_u32 update(br_u32 c,const br_u8*p,br_u16 n){c32_crc=c;c32_address=(br_u16)p;c32_length=n;if(!c32_update())first(E_CRC);return c32_crc;}
static br_u8 named(br_u8 name){const char*p;
 if(name==0)p="DOS64.JRN";else if(name==1)p="DOS64.CFG";else if(name==2)p="DOS64.NEW";else if(name==3)p="DOS64.OLD";else if(name==4)p=archold;else p=archjrn;
 memcpy(d64_path_source,receipt+1u,128u);memset(d64_path_relative,0,128u);strcpy((char*)d64_path_relative,p);if(!d64_path_join()){first(E_FORMAT);return 0;}memcpy(path,d64_path_output,128u);return 1;}
static br_u8 configure(void){memcpy(d64_path_source,path,128u);if(!d64_path_parent()){first(E_FORMAT);return 0;}memcpy(br_config.root,d64_path_output,128u);br_config.owner=0xa5;br_config.target=1;br_config.capacity=0x400000UL;return 1;}
static br_u8 op(br_u8 p,br_u8 command,br_u16 n){restore();memset(&br_request,0,sizeof(br_request));br_request.op=command;br_request.mode=1u;br_request.length=n;if(command==BR_OPEN)memcpy(br_request.path,path,128u);phase=p;if(!br_start()){capture();first(E_FILE);return 0;}capture();waiting=1u;if(command==BR_OPEN)opened=1u;return 1;}
/* ex1 oldCFG,2 newCFG,3 JRN,4 full image. req0 absent,1 exists,2 optional. */
static br_u8 verify(br_u8 name,br_u8 ex,br_u8 req){role=name;expect=ex;required=req;absent=close_attempt=0;position=0;crc=0xffffffffUL;size=ex==3?1284UL:ex==4?368640UL:576UL;
 if(name==6){br_u8 drive;if(!fetch(0x3e0608UL,1u))return 0;drive=buffer[0];if(drive>1u){first(E_FORMAT);return 0;}if(!fetch(0x3e08c0UL+(drive?264u:136u),128u))return 0;memcpy(path,buffer,128u);}else if(!named(name))return 0;
 return configure()&&op(P_OPEN,BR_OPEN,0);}
static void terminal(void){state=3;publish();}
static void cleanup_poll(void){
 if(++drain>=256u){cleanup=1;terminal();return;}
 if(raw){if(uci_state==BR_UCI_DONE||uci_state==BR_UCI_FAILED){raw=0;if(uci_recovery_failed){cleanup=1;terminal();return;}restore();if(!br_ui_release()){capture();cleanup=1;terminal();return;}capture();lease=0;}else{if(!aborted){aborted=1;uci_abort();}return;}}
 if(waiting){if(phase!=P_CLOSE&&phase!=P_SAFE&&!aborted){aborted=1;restore();br_cancel();capture();}return;}
 if((phase==P_CLOSE||phase==P_SAFE)&&!files_handle&&!leaf.handle&&((leaf.state==BR_DONE&&!leaf.error)||nofile()))opened=0;
 if(opened||files_handle||leaf.handle){if(close_attempt||phase==P_CLOSE||phase==P_SAFE){cleanup=1;terminal();return;}close_attempt=1;if(!op(P_SAFE,BR_CLOSE,0)){cleanup=1;terminal();}return;}
 if(lease){restore();if(!br_ui_release()){capture();cleanup=1;terminal();return;}capture();lease=0;}
 cleanup=!quiet();terminal();
}
static br_u8 rename_start(br_u8 from,br_u8 to,br_u8 bit){br_u16 n,k;
 if(rename_mask&bit){first(E_CONFLICT);return 0;}if(!quiet()||!service()){first(E_OWNER);return 0;}restore();if(!br_ui_acquire()){capture();first(E_OWNER);return 0;}capture();lease=1;
 if(!named(from))return 0;n=(br_u16)strlen(path)+1u;memcpy(uci_command+2u,path,n);if(!named(to))return 0;k=(br_u16)strlen(path)+1u;if(n+k+2u>895u){first(E_FORMAT);return 0;}memcpy(uci_command+2u+n,path,k);uci_command[0]=1;uci_command[1]=10;uci_command_len=n+k+2u;uci_data_capacity=0;uci_status_capacity=255u;uci_now=now;seen=0;rename_mask|=bit;
 if(uci_start()){first(E_FILE);return 0;}raw=1;return 1;}
static br_u8 rename_poll(void){uci_now=now;uci_poll();if(uci_error||uci_recovery_failed)first(E_FILE);if(uci_state==BR_UCI_BLOCK){if(seen||uci_data_len||!status("00,OK",5u)){first(E_FILE);return 0;}seen=1;uci_accept();}if(uci_state==BR_UCI_DONE){raw=0;if(!seen){first(E_FILE);return 0;}restore();if(!br_ui_release()){capture();first(E_OWNER);return 0;}capture();lease=0;return 1;}if(uci_state==BR_UCI_FAILED)first(E_FILE);return 0;}
static br_u8 checked_part(void){
 if(expect==1u||expect==2u){if(!fetch((expect==1u?0x3e0680UL:0x3e08c0UL)+position,count))return 0;if(memcmp(buffer,uci_data,count)){first(E_CONFLICT);return 0;}}
 else if(expect==3u){if((position==512UL&&wide(uci_data+188u)!=wide(receipt+139u))||(position==1024UL&&wide(uci_data+252u)!=wide(receipt+143u))){first(E_CRC);return 0;}if(position<1280UL)crc=update(crc,uci_data,count);else if((crc^0xffffffffUL)!=wide(uci_data)||(crc^0xffffffffUL)!=wide(receipt+129u)){first(E_CRC);return 0;}if(stage==0u&&!store(0x3e0600UL+position,count))return 0;}
 else crc=update(crc,uci_data,count);return !error;
}
static void next(void){
 ++stage;
 switch(stage){
 case 1:verify(6,4,1);break;
 case 2:verify(1,receipt[0]==1u?1u:2u,receipt[0]==3u?0u:1u);break;
 case 3:verify(2,2,receipt[0]==2u?0u:1u);break;
 case 4:verify(3,1,receipt[0]==1u?0u:receipt[0]==3u?1u:2u);break;
 case 5:verify(4,1,receipt[0]==2u&&!oldpresent?1u:0u);break;
 case 6:verify(5,3,0);break;
 case 7:if(receipt[0]==1u)rename_start(1,3,1u);else next();break;
 case 8:if(receipt[0]!=2u)rename_start(2,1,2u);else next();break;
 case 9:verify(1,2,1);break;
 case 10:verify(oldpresent||receipt[0]!=2u?3u:4u,1,1);break;
 case 11:if(oldpresent||receipt[0]!=2u)rename_start(3,4,4u);else next();break;
 case 12:verify(4,1,1);break;
 case 13:verify(0,3,1);break;
 case 14:rename_start(0,5,8u);break;
 case 15:verify(5,3,1);break;
 case 16:verify(1,2,1);break;
 case 17:verify(3,1,0);break;
 case 18:verify(2,2,0);break;
 case 19:verify(0,3,0);break;
 default:if(!quiet()||!service())first(E_OWNER);else state=2;publish();break;
 }
}
br_u8 __fastcall__ rf_begin(br_u8 action){br_u8 i,v;
 if(admitted||state||action!=RF_COMPLETE_SAVED_UPDATE)return 0;admitted=1;
 if(!jg_recovery_copy(receipt)){first(E_OWNER);terminal();return 0;}leaf=br_result;state=1;
 if(!quiet()||!service()){first(E_OWNER);terminal();return 1;}
 memcpy(buffer,receipt+137u,2u); /* private checked sequence, never public REU authority */
 strcpy(archold,"S0000.OLD");strcpy(archjrn,"S0000.JRN");for(i=0;i<4u;++i){v=(i<2u?buffer[1]:buffer[0]);v=(i&1u)?v&15u:v>>4;archold[1u+i]=archjrn[1u+i]=(v<10u?'0'+v:'A'+v-10u);}
 if(!verify(0,3,1)&&!error)first(E_FORMAT);if(error)cleanup_poll();publish();return 1;
}
void rf_poll(void){br_u8 ok,done=0;
 if(state!=1u){publish();return;}if(++steps==0){first(E_BOUND);cleanup=1;terminal();return;}
 ok=sample();
 if(raw){done=rename_poll();}else if(waiting){restore();br_poll();capture();if(leaf.state!=BR_BUSY)waiting=0;}
 if(!ok||clock_request)first(E_CLOCK);if(cancel_request||(ps_key_poll()&&ps_key==27u))first(E_CANCEL);
 if(error){cleanup_poll();publish();return;}if(raw||waiting){publish();return;}if(done){next();publish();return;}
 if(phase==P_OPEN){if(missing()){absent=1;if(required==1u)first(E_CONFLICT);if(!op(P_CLOSE,BR_CLOSE,0))cleanup_poll();return;}if(leaf.state!=BR_DONE||leaf.error||leaf.handle!=1u){first(E_FILE);cleanup_poll();return;}if(!required){first(E_CONFLICT);cleanup_poll();return;}if(!op(P_INFO,BR_INFO,0))cleanup_poll();return;}
 if(phase==P_INFO){if(leaf.state!=BR_DONE||leaf.error||!leaf.known||leaf.size!=size){first(E_FORMAT);cleanup_poll();return;}}
 else if(phase==P_READ){if(leaf.state!=BR_DONE||leaf.error||!leaf.known||leaf.actual!=count){first(E_FILE);cleanup_poll();return;}if(!checked_part()){cleanup_poll();return;}position+=count;}
 else if(phase==P_EOF){if(leaf.state!=BR_FAILED||!eof()){first(E_FILE);cleanup_poll();return;}if(!op(P_CLOSE,BR_CLOSE,0)){cleanup=1;terminal();}return;}
 else if(phase==P_CLOSE){if((leaf.state!=BR_DONE||leaf.error)&&!nofile()){first(E_FILE);cleanup_poll();return;}opened=0;if(!quiet()){first(E_OWNER);cleanup=1;terminal();return;}if(absent){leaf.state=BR_DONE;leaf.error=leaf.transport=0;restore();}if(role==3u)oldpresent=!absent;if(expect==4u&&!absent&&(crc^0xffffffffUL)!=wide(receipt+133u)){first(E_CRC);terminal();return;}next();publish();return;}
 else{first(E_FILE);cleanup_poll();return;}
 if(error){cleanup_poll();return;}if(position==size){if(!op(P_EOF,BR_READ,1u))cleanup_poll();}else{count=(br_u16)(size-position);if(size-position>256UL)count=256u;if(!op(P_READ,BR_READ,count))cleanup_poll();}publish();
}
void rf_cancel(void){if(state==1u)cancel_request=1;}
void rf_clock_fail(void){if(state==1u)clock_request=1;}
br_u8 rf_state(void){publish();return state;}
br_u8 rf_error(void){publish();return error;}
br_u8 rf_cleanup(void){publish();return cleanup;}
