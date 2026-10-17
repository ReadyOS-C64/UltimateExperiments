#include "setup_cooperate.h"
#include "setup_io.h"
#include "setup_overlay.h"
#include "bulk_context.h"
#include "platform.h"
#include <string.h>
#pragma code-name("HIGH_CODE")
#pragma bss-name("HIGHBSS")
static br_u8 enabled,error,active,stopping,drain,closing,leaf,transport,sampled;
static br_u16 now,guard;
static br_u32 capacity;
static void first(br_u8 e){if(!error){error=e;if(e==NC_LEAF){leaf=br_result.error?br_result.error:br_result.rejected;transport=br_result.transport;}}if(error==NC_CANCEL)ns_cancel=1;else if(error&&!ns_io_error)ns_io_error=2;}
static br_u8 external(void){return ns_cancel?NC_CANCEL:ns_io_error?NC_EXTERNAL:(ns_io_owner!=0xa5||ns_capacity!=capacity)?NC_OWNER:0;}
br_u8 nc_begin(void){if(enabled||error||active||ns_io_owner!=0xa5||ns_io_error||ns_cancel||ns_capacity!=so_capacity())return 0;capacity=ns_capacity;sampled=0;enabled=1;return nc_service();}
br_u8 nc_end(void){if(!enabled||error||active||!bc_files_closed()||!nf_inactive())return 0;enabled=0;return 1;}
static br_u8 fresh(void){if(!ps_clock_poll()||(sampled&&(br_u16)(ps_ticks-now)>=0x8000u))return 0;now=ps_ticks;sampled=1;return 1;}
br_u8 nc_service(void){br_u8 e;if(!enabled)return 1;if(error){first(error);return 0;}e=external();if(e)first(e);if(!fresh())first(NC_CLOCK);if(ps_key_poll()&&ps_key==27)first(NC_CANCEL);return !error;}
static br_u8 run(void){br_u8 clock,e;guard=0;drain=0;stopping=0;active=1;
 for(;;){e=external();clock=fresh();br_now=now;bc_slot=0;bc_poll();
  if(br_result.error)first(NC_LEAF);if(e)first(e);if(!clock)first(NC_CLOCK);if(ps_key_poll()&&ps_key==27)first(NC_CANCEL);
  if(br_result.state!=BR_BUSY){active=0;return br_result.state==BR_DONE&&!br_result.error&&br_result.handle!=2;}
  if(++guard==0)first(NC_BOUND);
  if(error&&!closing&&!stopping){bc_cancel();stopping=1;}
  if(error&&++drain==0)return 0;
 }
}
static br_u8 execute(br_u8 close){br_u8 ok;closing=close;
 if(!bc_start()){first(NC_LEAF);return 0;}ok=run();if(ok&&(!error||close))return 1;
 if(!error)first(NC_LEAF);
 if(!active&&!closing&&!bc_files_closed()){memset(&br_request,0,sizeof(br_request));br_request.op=BR_CLOSE;bc_slot=0;br_now=now;closing=1;if(bc_start())run();}
 return 0;
}
br_u8 nc_operation(br_u8 op,br_u32 offset,br_u16 count){
 if((op!=BR_SEEK&&op!=BR_LOAD)||!enabled||error||active||!nc_service())return 0;
 bc_slot=0;br_now=now;memset(&br_request,0,sizeof(br_request));br_request.op=op;br_request.offset=offset;br_request.address=NS_SOURCE_CACHE;br_request.length=count;
 return execute(0);
}
br_u8 nc_prepared(void){br_u8 close=br_request.op==BR_CLOSE;
 if(!enabled||active||(!close&&error)||bc_config[0].owner!=0xa5||bc_config[0].target!=1||bc_config[0].capacity!=capacity)return 0;
 if(br_request.op!=BR_OPEN&&br_request.op!=BR_INFO&&!close)return 0;
 if(br_request.op==BR_OPEN&&br_request.mode!=1)return 0;
 if(!nc_service()&&!close)return 0;bc_slot=0;br_now=now;return execute(close);
}
br_u8 nc_error(void){return error;}
br_u8 nc_pending(void){return active;}
br_u8 nc_closed_quiet(void){return !active&&bc_files_closed();}

br_u8 nc_leaf_error(void){return leaf;}
br_u8 nc_transport_error(void){return transport;}
