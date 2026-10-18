#include "selection_capsule.h"
#include "setup_overlay.h"
#include "setup_select.h"
#include "bulk_context.h"
#include "platform.h"
#include "install_config.h"
#include "crc32.h"
#include <string.h>
extern br_u8 so_scratch[512];
extern const br_u32 so_ui_crc;
extern br_u32 nf_io_address;
extern br_u16 nf_io_buffer,nf_io_length;
extern br_u8 nf_io_direction,nf_io_status;
extern void nf_dma(void);
static struct {br_u32 capacity,ui_crc,whole,chunk[2];br_u16 generation,ticket;br_u8 state,error,cancelled;} q;
br_u8 sq_page;
const br_u8 * const sq_bytes=so_scratch;
static void first(br_u8 e){if(!q.error)q.error=e;}
static br_u8 service(void){
 if(!ps_clock_poll())first(SQ_CLOCK);
 if(ps_key_poll()&&ps_key==27){q.cancelled=1;first(SQ_CANCEL);}
 return !q.error&&!q.cancelled;
}
static br_u8 dma(br_u16 offset,br_u16 host,br_u16 n,br_u8 direction){
 if(!service())return 0;
 nf_io_address=SQ_SLOT+offset;nf_io_buffer=host;nf_io_length=n;nf_io_direction=direction;nf_dma();
 if(nf_io_status){first(SQ_DMA);return 0;}return 1;
}
static br_u8 crc(br_u16 host,br_u16 n,br_u32 want){
 c32_reset();c32_address=host;c32_length=n;
 if(!c32_update()||!c32_finish()||c32_crc!=want){first(SQ_CRC);return 0;}return 1;
}
#pragma bss-name(push,"UIBSS")
static br_u8 record[1024];
#pragma bss-name(pop)
#pragma code-name(push,"UI_CODE")
#pragma rodata-name(push,"UI_RO")
static br_u8 path(const char *s){
 br_u16 i; br_u8 n;
 memcpy(d64_path_source,s,128);if(!s[1]||!d64_path_parent())return 0;n=(br_u8)strlen(s);
 for(i=(br_u16)n+1;i<128;i++)if(s[i])return 0;
 return 1;
}
static br_u8 same(const char*a,const char*b){
 br_u8 x,y;
 do{x=(br_u8)*a++;y=(br_u8)*b++;if(x>='a'&&x<='z')x-=32;if(y>='a'&&y<='z')y-=32;if(x!=y)return 0;}while(x);
 return 1;
}
static br_u8 choices_valid(void){
 br_u8 i,j;
 if(!path(ss_choices->home)||strlen(ss_choices->home)>SS_HOME_MAX||ss_choices->profile>1||ss_choices->existing_present>1)return 0;
 for(i=0;i<3;i++){
  if(!path(ss_choices->dos[i]))return 0;
  for(j=0;j<i;j++)if(same(ss_choices->dos[i],ss_choices->dos[j]))return 0;
 }
 if(ss_choices->existing_present){
  if(!path(ss_choices->existing))return 0;
  for(i=0;i<3;i++)if(same(ss_choices->existing,ss_choices->dos[i]))return 0;
 }else for(i=0;i<128;i++)if(ss_choices->existing[i])return 0;
 return 1;
}
static br_u32 sum(br_u16 host,br_u16 n){
 c32_reset();c32_address=host;c32_length=n;if(!c32_update()||!c32_finish())first(SQ_CRC);return c32_crc;
}
static br_u8 capture(void){
 br_u16 n,i; br_u8 ok=0;
 if(ss_state()!=SS_DONE||!choices_valid()){first(SQ_INPUT);return 0;}
 if(!bc_ui_acquire()){first(SQ_LEASE);return 0;}
 memset(record,0,1024);memcpy(record,"D64Q",4);record[4]=1;record[5]=0xa5;record[6]=0xc0;record[7]=2;
 memcpy(record+8,&q.generation,2);memcpy(record+10,&q.ticket,2);memcpy(record+12,&q.capacity,4);memcpy(record+16,&q.ui_crc,4);
 memcpy(record+32,ss_choices,642);c32_crc=sum((br_u16)record,700);memcpy(record+700,&c32_crc,4);
 q.whole=sum((br_u16)record,704);q.chunk[0]=sum((br_u16)record,512);q.chunk[1]=sum((br_u16)(record+512),192);
 if(q.error)goto done;
 memset(so_scratch,0,512);
 if(!dma(0,(br_u16)so_scratch,512,0)||!dma(512,(br_u16)so_scratch,512,0))goto done;
 record[5]=0;
 if(!dma(0,(br_u16)record,704,0))goto done;
 for(n=0;n<704;n+=512){i=n?192:512;
  if(!dma(n,(br_u16)so_scratch,i,1)||memcmp(so_scratch,record+n,i)){first(SQ_CRC);goto done;}
 }
 if(!dma(704,(br_u16)so_scratch,320,1))goto done;
 for(i=0;i<320;i++)if(so_scratch[i]){first(SQ_CRC);goto done;}
 record[5]=0xa5;
 if(sum((br_u16)record,704)!=q.whole){first(SQ_CRC);goto done;}
 if(!dma(5,(br_u16)(record+5),1,0)||!dma(5,(br_u16)so_scratch,1,1))goto done;
 if(so_scratch[0]!=0xa5){first(SQ_CRC);goto done;}if(!service())goto done;ok=1;
done:
 if(!bc_ui_release()){first(SQ_LEASE);ok=0;}return ok;
}
#pragma rodata-name(pop)
#pragma code-name(pop)
br_u8 sq_publish(void){br_u16 ticket;
 if(q.state==SQ_FAILED||q.state==SQ_BUSY)return 0;
 ticket=so_ui_ticket();if(!ticket||ticket==q.ticket)return 0;
 q.state=SQ_BUSY;q.cancelled=q.error=0;
 if(++q.generation==0){first(SQ_WRAP);q.state=SQ_FAILED;return 0;}
 q.ticket=ticket;q.capacity=so_capacity();q.ui_crc=so_ui_crc;
 if(!capture()){q.state=SQ_FAILED;return 0;}q.state=SQ_READY;return 1;
}
br_u8 sq_state(void){return q.state;}
br_u8 sq_error(void){return q.error;}
void sq_cancel(void){if(q.state==SQ_BUSY||q.state==SQ_READY){q.cancelled=1;first(SQ_CANCEL);q.state=SQ_FAILED;}}
br_u16 sq_read(void){br_u8 i,page; br_u16 n=0;
 if(q.state!=SQ_READY)return 0;
 page=sq_page;
 if(page>1||so_state()!=SO_READY||q.capacity!=so_capacity()||q.ui_crc!=so_ui_crc){first(SQ_IDENTITY);goto bad;}
 if(!bc_ui_acquire()){first(SQ_LEASE);goto bad;}
 c32_reset();c32_address=(br_u16)so_scratch;
 for(i=0;i<2;i++){
  c32_length=i?192:512;
  if(!dma(i?512:0,(br_u16)so_scratch,c32_length,1)||!c32_update()){first(SQ_CRC);goto done;}
 }
 if(!c32_finish()||c32_crc!=q.whole){first(SQ_CRC);goto done;}
 n=page?192:512;
 if(!dma(page?512:0,(br_u16)so_scratch,n,1)||!crc((br_u16)so_scratch,n,q.chunk[page])||!service())n=0;
done:
 if(!bc_ui_release()){first(SQ_LEASE);n=0;}
 if(n)return n;
bad:q.state=SQ_FAILED;return 0;
}
