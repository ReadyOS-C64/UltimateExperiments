#include "coordinator_capture.h"
#include "coordinator_internal.h"
#include "setup_ui_run.h"
#include "setup_overlay.h"
#include "source_load.h"
#include "selection_capsule.h"
#include "bulk_context.h"
#include <string.h>
#include <stddef.h>
#pragma bss-name(push,"HIGHBSS")
struct rc_record_t rc_retained;
#pragma bss-name(pop)
#pragma bss-name(push,"BSS")
br_u16 rc_expected_ticket,rc_generation;
br_u32 rc_identity;
br_u8 rc_flags,rc_source_mask;
#pragma bss-name(pop)
#pragma rodata-name(push,"RODATA")
const char * const rc_home=rc_retained.home;
const br_u16 rc_record_layout[]={sizeof(struct rc_record_t),offsetof(struct rc_record_t,source_crc),offsetof(struct rc_record_t,output),offsetof(struct rc_record_t,valid)};
#pragma rodata-name(pop)
static br_u16 word(const br_u8 *p){return p[0]|((br_u16)p[1]<<8);}
static br_u32 dword(const br_u8 *p){return (br_u32)word(p)|((br_u32)word(p+2)<<16);}
br_u8 rc_capture(void){br_u8 k;
 if(rc_retained.started||su_state()!=SU_DONE||!rc_expected_ticket||so_ui_ticket()!=rc_expected_ticket||!bc_files_closed())return 0;
 rc_retained.started=1;sq_page=0;if(sq_read()!=512u)return 0;
 rc_retained.generation=word(sq_bytes+8);memcpy(rc_retained.home,sq_bytes+SQ_HOME,128);
 sq_page=1;if(sq_read()!=192u)return 0;
 rc_retained.identity=dword(sq_bytes+188);rc_retained.flags=sq_bytes[160]|(sq_bytes[161]<<1);
 for(k=0;k<5u;++k){
  sl_kind=k;sl_generation=rc_retained.generation;sl_identity=rc_retained.identity;
  if(!sl_fact()||sl_receipt.generation!=rc_retained.generation||sl_receipt.identity!=rc_retained.identity||sl_receipt.bytes!=(k<3u?368640UL:k==3u?18432UL:64UL))return 0;
  rc_retained.source_crc[k]=sl_receipt.crc;rc_retained.source_mask|=1u<<k;
 }
 if(so_ui_ticket()!=rc_expected_ticket||sq_state()!=SQ_READY||!bc_files_closed())return 0;
 rc_retained.valid=1;rc_generation=rc_retained.generation;rc_identity=rc_retained.identity;
 rc_flags=rc_retained.flags;rc_source_mask=rc_retained.source_mask;return 1;
}
#pragma code-name(push,"HIGH_CODE")
br_u8 rc_source_ready(void){return rc_retained.valid&&rc_retained.source_mask==31u;}
#pragma code-name(pop)
