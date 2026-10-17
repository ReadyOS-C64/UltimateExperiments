#include "publish_worker.h"
#include "coordinator_internal.h"
#include "setup_overlay.h"
#include "selection_capsule.h"
#include "source_load.h"
#include "publish_assets.h"
#include "raw_output.h"
#include "setup_io.h"
#include "platform.h"
#include "crc32.h"
#include "bulk_context.h"
#include <string.h>
/* Internal friend state, never input/observation authority. */
extern br_u8 pw_private_state,pw_private_error,pw_private_stage;
extern br_u16 pw_ticket,pw_last;
extern br_u32 pw_address,pw_bytes,pw_crc;
br_u8 pw_fail(br_u8 e){if(!pw_private_error)pw_private_error=e;pw_private_state=3;return 0;}
br_u8 pw_service(void){br_u16 n;
 if(pw_private_error)return 0;
 if(!ps_clock_poll())return pw_fail(2);n=ps_ticks;if((br_u16)(n-pw_last)>=0x8000u)return pw_fail(2);pw_last=n;
 if(ns_cancel||(ps_key_poll()&&ps_key==27))return pw_fail(3);
 if(ns_io_owner!=0xa5||ns_capacity!=so_capacity()||ns_io_error)return pw_fail(1);
 return 1;
}
br_u8 pb_verified_fact(br_u8 kind,br_u16 gen,br_u32 identity,br_u32*out){br_u8 pair;
 if(pw_private_state!=1||pw_private_stage!=2||!pw_ticket||so_publish_ticket()!=pw_ticket||!rc_retained.valid||rc_retained.source_mask!=31u||rc_retained.output_mask!=(RC_C_MASK|RC_B_MASK|RC_A_MASK)||gen!=rc_retained.generation||identity!=rc_retained.identity)return 0;
 switch(kind){
 case PB_A_BYTES:pair=RC_A_PAIR;break;
 case PB_A_CRC:pair=RC_A_PAIR+1u;break;
 case PB_B_BYTES:pair=RC_B_PAIR;break;
 case PB_B_CRC:pair=RC_B_PAIR+1u;break;
 case PB_C_BYTES:pair=RC_C_PAIR;break;
 case PB_TEMPLATE_BYTES:
  sl_kind=3;sl_generation=gen;sl_identity=identity;
  if(!sl_fact()||sl_receipt.bytes!=18432UL||sl_receipt.crc!=rc_retained.source_crc[3])return 0;
  *out=sl_receipt.bytes;return 1;
 default:return 0;
 }
 *out=rc_retained.output[pair];return 1;
}
