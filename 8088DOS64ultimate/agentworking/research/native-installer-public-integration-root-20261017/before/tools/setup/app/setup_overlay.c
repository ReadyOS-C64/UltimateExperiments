#include "setup_overlay.h"
#include "bulk_context.h"
#include "install_config.h"
#include "crc32.h"
#include <string.h>
extern const br_u8 so_asset_header[64];
extern const br_u16 so_ui_bytes,so_fat_bytes,so_asset_bytes;
extern const br_u32 so_ui_crc,so_ui_full_crc,so_fat_crc;
extern const br_u16 so_ui_core_bytes;
extern const br_u32 so_ui_core_crc;
extern const br_u8 so_publish_header[64];
extern const br_u16 so_publish_bytes,so_publish_asset_bytes;
extern const br_u32 so_publish_crc,so_publish_full_crc;
/* Integration supplies the private shared startup-close authority, not a
 * mutable observation bit. Never infer firmware closure from zeroBSS. */
extern br_u8 so_startup_ready(void);
extern br_u32 nf_io_address;
extern br_u16 nf_io_buffer,nf_io_length;
extern br_u8 nf_io_direction,nf_io_status;
extern void nf_dma(void);
struct so_request_t so_request;
struct so_result_t so_result;
const br_u8 so_abi_sizes[]={sizeof(struct so_request_t),sizeof(struct so_result_t)};
br_u16 so_now,so_ticket;
br_u8 so_phase_request;
static struct so_request_t owned;
static struct so_result_t ledger;
br_u8 so_scratch[512];
static br_u8 started,bound,loaded,waiting,stage,destination,leased,handle,cancelled;
static br_u16 began,at,count,next_ticket;
static br_u32 slot,expected,crc;
static br_u16 asset_bytes(void){return destination==SO_FAT?so_asset_bytes:so_publish_asset_bytes;}
static br_u16 phase_bytes(br_u8 p){return p==SO_UI?so_ui_core_bytes:p==SO_FAT?so_fat_bytes:so_publish_bytes;}
static br_u32 phase_crc(br_u8 p){return p==SO_UI?so_ui_core_crc:p==SO_FAT?so_fat_crc:so_publish_crc;}
static void publish(void){so_result=ledger;}
static void first(br_u8 e){if(!ledger.error)ledger.error=e;}
static br_u8 dma(br_u32 reu_address,br_u16 host,br_u16 n,br_u8 direction){
 nf_io_address=reu_address;nf_io_buffer=host;nf_io_length=n;nf_io_direction=direction;nf_dma();return !nf_io_status;
}
static br_u8 ram_crc(br_u16 address,br_u16 bytes,br_u32 want){
 if(!c32_reset())return 0;c32_address=address;c32_length=bytes;
 return c32_update()&&c32_finish()&&c32_crc==want;
}
static void failed(void){
 if(leased){if(!bc_ui_release())ledger.cleanup_failed=1;else leased=0;}
 if(!bc_files_closed())ledger.cleanup_failed=1;ledger.phase=ledger.active=0;ledger.state=SO_FAILED;publish();
}
static br_u8 op(br_u8 command){
 memset(&br_request,0,sizeof(br_request));br_request.op=command;br_request.mode=1;
 br_request.address=destination==SO_FAT?SO_FAT_SLOT:SO_PUBLISH_SLOT;br_request.length=asset_bytes();
 if(command==BR_OPEN){br_u8 n=(br_u8)strlen(owned.home);memcpy(br_request.path,owned.home,n);strcpy(br_request.path+n,destination==SO_FAT?"/SETUP.FAT":"/SETUP.PUB");}
 bc_config[0].owner=0xa5;bc_config[0].target=1;bc_config[0].capacity=owned.capacity;memcpy(bc_config[0].root,owned.home,128);
 bc_slot=0;br_now=so_now;
 if(!bc_start()){handle=br_result.handle;if(!ledger.error){ledger.leaf=br_result.error?br_result.error:br_result.rejected;ledger.transport=br_result.transport;}first(SO_FILE);return 0;}
 waiting=1;began=so_now;return 1;
}
static void observe(void){
 br_now=so_now;bc_poll(); /* restores private context result before all decisions */
 handle=br_result.handle;
 if(br_result.error){if(!ledger.error){ledger.leaf=br_result.error;ledger.transport=br_result.transport;}first(SO_FILE);}
 if(br_result.state!=BR_BUSY){waiting=0;if(br_result.state!=BR_DONE)first(SO_FILE);}
}
br_u8 so_prepare(void){br_u16 n;
 if(started||so_request.owner!=0xa5||so_request.capacity<0x400000UL||so_request.capacity>0x1000000UL||(so_request.capacity&65535UL)||!so_request.timeout||so_request.timeout>=0x8000||!so_startup_ready()||!bc_files_closed()){ledger.rejected=SO_INPUT;publish();return 0;}
 if(!bc_ui_acquire()){first(SO_LEASE);failed();return 0;}leased=1;
 if(!c32_init()||!ram_crc(0x6000,so_ui_bytes,so_ui_crc)){first(SO_CRC);failed();return 0;}
 owned=so_request;memset(owned.home,0,128);started=1;ledger.rejected=0;
 memset(so_scratch,0,512);
 for(n=0;n<0x5000;n+=512)if(!dma(SO_UI_SLOT+n,(br_u16)so_scratch,512,0)){first(SO_DMA);failed();return 0;}
 /* The full initial span above includes serialized HIGH/AUX and remains
  * checked before it is retired. Both RUN copies already passed sl_install.
  * Cache only live immutable UI; the following full-window FETCH zeroes its
  * state, including bytes that previously held relocation source payloads. */
 for(n=0;n<so_ui_core_bytes;n+=count){count=so_ui_core_bytes-n;if(count>512)count=512;if(!dma(SO_UI_SLOT+n,0x6000+n,count,0)){first(SO_DMA);failed();return 0;}}
 if(!dma(SO_UI_SLOT,0x6000,0x5000,1)||!ram_crc(0x6000,0x5000,so_ui_full_crc)){first(SO_CRC);failed();return 0;}
 if(!bc_ui_release()){first(SO_LEASE);failed();return 0;}leased=0;
 ledger.state=SO_READY;ledger.phase=SO_UI;publish();return 1;
}
br_u8 so_bind_home(void){
 if(!started||bound||ledger.state!=SO_READY||ledger.phase!=SO_UI||ledger.active||!so_startup_ready()||!bc_files_closed()){ledger.rejected=SO_INPUT;publish();return 0;}
 if(!ram_crc(0x6000,so_ui_core_bytes,so_ui_core_crc)){first(SO_CRC);failed();return 0;}
 /* UI codec runs only while its current full window is verified. */
 memcpy(d64_path_source,so_request.home,128);memset(d64_path_relative,0,128);strcpy((char*)d64_path_relative,"SETUP.FAT");
 if(so_request.home[1]==0||!d64_path_join()){ledger.rejected=SO_INPUT;publish();return 0;}
 memcpy(owned.home,so_request.home,128);bound=1;ledger.rejected=0;publish();return 1;
}
br_u8 so_state(void){publish();return ledger.state;}
br_u8 so_closed_quiet(void){
 return (ledger.state==SO_READY||ledger.state==SO_FAILED)&&!ledger.active&&!waiting&&!leased&&so_startup_ready()&&bc_files_closed();
}
br_u8 so_begin(void){
 ledger.rejected=0;
 if(!started||ledger.state!=SO_READY||ledger.error||ledger.active||so_phase_request<SO_UI||so_phase_request>SO_PUBLISH||(so_phase_request!=SO_UI&&!bound)||!so_startup_ready()||!bc_files_closed()){ledger.rejected=SO_LEASE;publish();return 0;}
 destination=so_phase_request;ledger.state=SO_BUSY;ledger.phase=0;stage=destination!=SO_UI&&!(loaded&(destination==SO_FAT?1:2))?1:5;waiting=handle=cancelled=0;began=so_now;at=0;
 publish();return 1;
}
void so_poll(void){br_u16 n;
 if(ledger.state!=SO_BUSY){publish();return;}
 if(waiting){observe();if(waiting){if((br_u16)(so_now-began)>=owned.timeout){first(SO_TIMEOUT);if(!cancelled){cancelled=1;br_now=so_now;bc_cancel();}}publish();return;}
  if(stage==8){if(handle||!bc_files_closed())ledger.cleanup_failed=1;failed();return;}
  if(!ledger.error){if(stage==2&&(!br_result.known||br_result.size!=asset_bytes()))first(SO_HEADER);
   if(stage==3&&(!br_result.known||br_result.actual!=asset_bytes()))first(SO_FILE);
   ++stage;}
 }
 if((br_u16)(so_now-began)>=owned.timeout)first(SO_TIMEOUT);
 if(ledger.error){if(handle){stage=8;if(!op(BR_CLOSE)){ledger.cleanup_failed=1;failed();}else publish();}else failed();return;}
 if(stage<=4){if(!op(stage==1?BR_OPEN:stage==2?BR_INFO:stage==3?BR_LOAD:BR_CLOSE)){
   if(handle){stage=8;if(!op(BR_CLOSE)){ledger.cleanup_failed=1;failed();}}else failed();
  }publish();return;}
 if(stage==5){
  if(!bc_ui_acquire()){first(SO_LEASE);failed();return;}leased=1;
  if(destination!=SO_UI){slot=destination==SO_FAT?SO_FAT_SLOT:SO_PUBLISH_SLOT;
   if(!dma(slot,(br_u16)so_scratch,64,1)){first(SO_DMA);failed();return;}
   if(memcmp(so_scratch,destination==SO_FAT?so_asset_header:so_publish_header,64)){first(SO_HEADER);failed();return;}
   slot+=64;count=destination==SO_FAT?so_fat_bytes:0x5000;expected=destination==SO_FAT?so_fat_crc:so_publish_full_crc;
  }else{slot=SO_UI_SLOT;count=0x5000;expected=so_ui_full_crc;}
  at=0;crc=0xffffffffUL;stage=6;
 }
 if(stage==6){n=count-at;if(n>512)n=512;
  if(!dma(slot+at,(br_u16)so_scratch,n,1)){first(SO_DMA);failed();return;}
  c32_crc=crc;c32_address=(br_u16)so_scratch;c32_length=n;if(!c32_update()){first(SO_CRC);failed();return;}crc=c32_crc;at+=n;
  if(at<count){publish();return;}if((crc^0xffffffffUL)!=expected){first(SO_CRC);failed();return;}stage=7;
 }
 if(stage==7){
  if(!dma(slot,0x6000,count,1)){first(SO_DMA);failed();return;}
  if(!ram_crc(0x6000,count,expected)){first(SO_CRC);failed();return;}
  if(!bc_ui_release()){first(SO_LEASE);failed();return;}leased=0;
  if(destination!=SO_UI)loaded|=destination==SO_FAT?1:2;ledger.phase=destination;ledger.state=SO_READY;publish();
 }
}
void so_cancel(void){
 if(ledger.state==SO_BUSY){if(waiting)observe();first(SO_CANCEL);if(waiting&&!cancelled&&stage!=4&&stage!=8){cancelled=1;br_now=so_now;bc_cancel();}if(!waiting)so_poll();}publish();
}
br_u8 so_enter(void){
 ledger.rejected=0;
 if(ledger.state!=SO_READY||ledger.error||ledger.active||so_phase_request!=ledger.phase||!so_startup_ready()||!bc_files_closed()){ledger.rejected=SO_TICKET;publish();return 0;}
 if(!ram_crc(0x6000,phase_bytes(ledger.phase),phase_crc(ledger.phase))){first(SO_CRC);failed();return 0;}
 if(++next_ticket==0){first(SO_TICKET);failed();return 0;}ledger.ticket=next_ticket;ledger.active=1;publish();return 1;
}
br_u8 so_leave(void){
 if(!ledger.active||so_ticket!=ledger.ticket||!bc_files_closed()){ledger.rejected=SO_TICKET;publish();return 0;}
 ledger.active=0;ledger.rejected=0;publish();return 1;
}

static br_u16 phase_ticket(br_u8 p){
 if(ledger.state!=SO_READY||ledger.error||ledger.phase!=p||!ledger.active||!so_startup_ready()||!bc_files_closed())return 0;
 if(!ram_crc(0x6000,phase_bytes(p),phase_crc(p))){first(SO_CRC);failed();return 0;}return ledger.ticket;
}
br_u16 so_ui_ticket(void){return phase_ticket(SO_UI);}
br_u16 so_fat_ticket(void){return phase_ticket(SO_FAT);}
br_u16 so_publish_ticket(void){return phase_ticket(SO_PUBLISH);}
br_u32 so_capacity(void){return started?owned.capacity:0;}
