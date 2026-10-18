/* Deliberately compile the unchanged reviewed source in this translation unit:
 * narrow access to its private owner/mode avoids exporting mutable authority.
 * Do not also link bulk_reu.o. Neither underlying source nor wire engine changed. */
#include "bulk_reu.c"
#include "bulk_context.h"
#include <string.h>
extern br_u8 bc_files[25];
struct bc_snapshot { struct br_config_t owner; struct br_result_t result; br_u8 files[25],mode; };
static struct bc_snapshot saved[2];
struct br_config_t bc_config[2];
struct bc_status_t bc_status[2];
static struct bc_status_t ledger[2];
static char open_path[2][128];
br_u8 bc_slot;
static br_u8 active,ui,initialized;
static br_u32 source_epoch;
static br_u8 source_started,source_dead;
static void source_advance(void){if(!source_dead&&++source_epoch==0)source_dead=1;}
/* Linker-checked FILES state offset, not a public result observation. */
#define BC_HANDLE 15
static void restore_result(void) {br_result=ledger[active].result;}
static br_u8 selectable(void) {
 if(!initialized)return 0;
 restore_result();
 return !ui&&br_result.state!=BR_BUSY&&quiet();
}
static void capture(void) {
 br_u8 j;
 br_result.handle=files_handle;
 saved[active].owner=owned;saved[active].result=br_result;saved[active].mode=access_mode;
 for(j=0;j<25;++j)saved[active].files[j]=bc_files[j];
 ledger[active].result=br_result;
 if(br_result.error&&!ledger[active].first_error)ledger[active].first_error=br_result.error;
 bc_status[active]=ledger[active];
}
static br_u8 select_slot(void) {
 br_u8 j;
 if(bc_slot>1||!selectable())return 0;
 if(bc_slot!=active) {
  capture();active=bc_slot;owned=saved[active].owner;br_result=saved[active].result;access_mode=saved[active].mode;
  for(j=0;j<25;++j)bc_files[j]=saved[active].files[j];
 }
 return 1;
}
void bc_init(void) {
 br_u8 j;
 if(source_started)source_dead=1;else{source_started=1;source_epoch=1;}
 br_init();active=ui=bc_slot=0;initialized=1;
 for(j=0;j<2;++j) {
  bc_config[j]=br_config;bc_config[j].owner=0;bc_config[j].target=j+1;
  ledger[j].position=ledger[j].file_size=0;ledger[j].size_known=ledger[j].position_known=0;ledger[j].first_error=0;
  saved[j].owner=owned;saved[j].result=br_result;saved[j].mode=0;
  {br_u8 k;for(k=0;k<25;++k)saved[j].files[k]=bc_files[k];}
  ledger[j].result=br_result;bc_status[j]=ledger[j];
 }
}
static br_u8 fold(br_u8 c){return c>='A'&&c<='Z'?c+32:c;}
static br_u8 same_path(br_u8 other) {
 br_u8 j;
 for(j=0;j<128;++j) {
  if(fold(br_request.path[j])!=fold(open_path[other][j]))return 0;
  if(!br_request.path[j])return 1;
 }
 return 1;
}
br_u8 bc_start(void) {
 br_u8 ok,j,opening;
 if(bc_slot>1||!selectable())return 0;
 /* Reject before switching or touching the active authority. */
 if(bc_config[bc_slot].target!=bc_slot+1)return 0;
 if(!bc_slot&&br_request.op==BR_OPEN&&br_request.mode!=1)return 0;
 capture();
 if(br_request.op==BR_OPEN&&saved[1-bc_slot].files[BC_HANDLE]&&same_path(1-bc_slot))return 0;
 if(br_request.op==BR_SEEK&&(!ledger[bc_slot].size_known||br_request.offset>ledger[bc_slot].file_size))return 0;
 if(!select_slot())return 0;
 opening=br_request.op==BR_OPEN&&!files_handle;
 br_config=bc_config[active];
 if(!active&&(br_request.op==BR_OPEN||br_request.op==BR_CLOSE||br_request.op==BR_INFO))source_advance();
 ok=br_start();
 if(opening&&(ok||files_handle))for(j=0;j<128;++j)open_path[active][j]=q.path[j];
 capture();return ok;
}
void bc_poll(void) {
 br_u8 was;
 if(!initialized||ui)return;
 restore_result();was=br_result.state;
 br_poll();capture();
 if(was!=BR_BUSY||br_result.state==BR_BUSY)return;
 if(br_result.state==BR_DONE) {
  if(q.op==BR_OPEN){ledger[active].position=0;ledger[active].position_known=1;ledger[active].size_known=(q.mode&4)!=0;ledger[active].file_size=0;}
  else if(q.op==BR_INFO){ledger[active].file_size=br_result.size;ledger[active].size_known=1;}
  else if(q.op==BR_CLOSE)ledger[active].position_known=0;
  else if(q.op==BR_SEEK){ledger[active].position=q.offset;ledger[active].position_known=1;}
  else if(q.op==BR_LOAD||q.op==BR_SAVE||q.op==BR_READ) {
   if(ledger[active].position_known) {
    if(br_result.actual>0xffffffffUL-ledger[active].position)ledger[active].position_known=0;
    else {ledger[active].position+=br_result.actual;
     if(q.op==BR_SAVE&&ledger[active].size_known&&ledger[active].position>ledger[active].file_size)ledger[active].file_size=ledger[active].position;
    }
   }
  }
 } else {if(q.op==BR_SAVE||q.op==BR_OPEN||q.op==BR_CLOSE)ledger[active].size_known=0;
 if(q.op==BR_OPEN||q.op==BR_CLOSE||q.op==BR_SEEK||q.op==BR_LOAD||q.op==BR_SAVE||q.op==BR_READ)ledger[active].position_known=0;
 }
 bc_status[active]=ledger[active];
}
void bc_cancel(void) {if(initialized&&!ui){restore_result();br_cancel();capture();}}
br_u8 bc_files_closed(void) {
 if(!selectable())return 0;
 capture();return !saved[0].files[BC_HANDLE]&&!saved[1].files[BC_HANDLE];
}
br_u8 bc_ui_acquire(void) {
 if(!bc_files_closed())return 0;
 if(!br_ui_acquire())return 0;ui=1;return 1;
}
br_u8 bc_ui_release(void) {if(!ui||!br_ui_release())return 0;ui=0;return 1;}
br_u8 bc_clear_error(void) {
 if(!select_slot()||files_handle)return 0;
 ledger[active].first_error=0;br_result.error=br_result.transport=0;capture();return 1;
}
const br_u8 bc_abi_sizes[]={sizeof(struct bc_status_t),sizeof(struct bc_snapshot)};

/* No public result copy is authority here; inspect the retained privateledger
 * and actual active FILES handle. Does not switchcontext or mutate transport. */
br_u32 bc_source_identity(void){
 const struct br_config_t*p; br_u8 h,m;
 if(!initialized||ui||source_dead||!source_epoch||(ledger[active].result.state==BR_BUSY||ledger[active].result.state==BR_FAILED)||(uci_state!=0&&uci_state!=9)||!quiet())return 0;
 h=active?saved[0].files[BC_HANDLE]:files_handle;
 m=active?saved[0].mode:access_mode;p=active?&saved[0].owner:&owned;
 if(h!=1||m!=1||p->owner!=0xa5||p->target!=1||memcmp(&bc_config[0],p,sizeof(*p))||!ledger[0].size_known||!ledger[0].position_known||ledger[0].first_error)return 0;
 return source_epoch;
}
br_u32 bc_source_bytes(void){if(!bc_source_identity())return 0;return ledger[0].file_size;}

#if defined(DOS64_SETUP_WRITER_CLEANUP) && DOS64_SETUP_WRITER_CLEANUP
#pragma code-name(push,"FAT_CODE")
/* Quiet private FILES snapshots; never poll/select a possibly NC-owned source. */
br_u8 bc_output_closed(void){if(!selectable())return 0;return active==1?!files_handle:!saved[1].files[BC_HANDLE];}
#pragma code-name(pop)
#endif
