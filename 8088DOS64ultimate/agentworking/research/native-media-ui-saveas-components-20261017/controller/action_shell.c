#include "action_shell.h"
#include "media_plan.h"
#include <string.h>
/* Actual native worker entrypoints, supplied by exact per-role linker aliases.
 * All worker calls return before their A000 phase bytes are replaced. */
extern unsigned char ac_load(unsigned char phase);
extern unsigned char ac_native_safe(void),ac_context_closed(void),ac_transfer(void),ac_service(void),ac_pending_error(void);
extern void ac_block(void);
extern unsigned int ac_dma_host,ac_dma_count;
extern unsigned long ac_dma_reu;
extern unsigned char ac_ledger[256];
extern unsigned char tw_begin(void),tw_poll(void),tw_state(void),tw_error(void),tw_closed(void),tw_committing(void);
extern char tw_home[128];extern unsigned int tw_sequence,tw_limit;extern unsigned char tw_mode,tw_cancel;
extern unsigned char ms_begin(void),ms_poll(void),ms_state(void),ms_error(void);
extern char ms_path[128];extern unsigned char ms_drive,ms_cancel;
extern void mw_init(void);extern unsigned char mw_build(void);
/* Each phase descriptor additionally carries the matching wrapper; PLAN and
 * BIND both use the verified high96/stackBFFF veneer at7DD0. */
#define WIRE 1u
#define SAVE 2u
#define PLAN 3u
#define BIND 4u
struct ac_request_t ac_request={0xffu,0u,0u,0UL,0u,0u,{0}};
struct ac_result_t ac_result;
static struct ac_request_t job;
static unsigned char home[128],commit_seen,stopped,service_cause;
static unsigned long polls;
static unsigned char failure(unsigned char e,unsigned char worker,unsigned char closed){
 if(!ac_result.error){ac_result.error=e;ac_result.worker_error=worker;}
 ac_result.known_closed=closed;ac_result.state=3u;
 /* Publication may have begun; only a full successful binding permits Resume
  * after commit. Precommit failures require current native context/clock. */
 ac_result.can_resume=!commit_seen&&!service_cause&&closed&&ac_native_safe();
 if(!ac_result.can_resume)ac_block();
 return 0u;
}
/* Each active leaf observes its own published error before later key/clock
 * input. Caller never polls or closes the shared engine behind that leaf. */
static unsigned char sample(void){
 unsigned char v;
 if(service_cause)return 2u;
 v=ac_service();
 if(v==2u)service_cause=9u;
 else if(v==1u&&!commit_seen)stopped=1u;
 return v;
}
static unsigned char admission(void){
 sample();
 if(service_cause)return failure(service_cause,0u,ac_context_closed());
 if(stopped&&!commit_seen)return failure(8u,0u,ac_context_closed());
 return 1u;
}
static void wire_poll(void){
 tw_poll();
 if(tw_committing()){commit_seen=1u;ac_result.committing=1u;}
 if(tw_state()==1u){
  if(!tw_error()&&!ac_pending_error())sample();
  if(service_cause||(stopped&&!commit_seen))tw_cancel=1u;
 }
}
static void save_poll(void){
 ms_poll();
 if(ms_state()==1u){
  if(!ms_error()&&!ac_pending_error())sample();
  if(service_cause||stopped)ms_cancel=1u;
 }
}
static unsigned char fetch_home(void){
 /* The accepted CFG will be independently validated/read by WIRE. Only its
  * canonical home is copied here, before installing any worker BSS. */
 ac_dma_host=(unsigned int)home;ac_dma_reu=0x3ff028UL;ac_dma_count=128u;
 return ac_transfer();
}
static unsigned char wire(unsigned char mode){
 if(!admission())return 0u;
 if(!ac_load(WIRE))return failure(2u,0u,0u);
 if(!admission())return 0u;
 memcpy(tw_home,home,128u);tw_sequence=job.sequence;tw_limit=30000u;tw_mode=mode;
 if(!tw_begin())return failure(3u,tw_error(),tw_closed());
 polls=0;
 while(tw_state()==1u&&polls<40000UL){wire_poll();++polls;}
 if(tw_state()==1u){tw_cancel=1u;polls=0;while(tw_state()==1u&&polls<4096UL){wire_poll();++polls;}}
 if(tw_state()!=2u||!tw_closed())return failure(service_cause?service_cause:3u,tw_error(),tw_closed());
 if(service_cause)return failure(service_cause,0u,tw_closed());
 return 1u;
}
static unsigned char save(void){
 if(!admission())return 0u;
 if(!ac_load(SAVE))return failure(2u,0u,0u);
 if(!admission())return 0u;
 ms_drive=job.drive;memcpy(ms_path,job.path,128u);
 if(!ms_begin())return failure(4u,ms_error(),ac_context_closed());
 polls=0;while(ms_state()==1u&&polls<250000UL){save_poll();++polls;}
 if(ms_state()==1u){ms_cancel=1u;polls=0;while(ms_state()==1u&&polls<4096UL){save_poll();++polls;}}
 if(ms_state()!=2u)return failure(service_cause?service_cause:4u,ms_error(),ac_context_closed());
 if(service_cause)return failure(service_cause,0u,ac_context_closed());
 return 1u;
}
static unsigned char plan(void){
 if(!admission())return 0u;
 if(!ac_load(PLAN))return failure(2u,0u,0u);
 if(!admission())return 0u;
 mw_init();mp_drive=job.drive;mp_readonly=job.readonly;mp_sequence=job.sequence;mp_capacity=job.capacity;
 memcpy(mp_image_path,ac_ledger+4u,128u);memcpy(mp_snapshot,ac_ledger+132u,42u);memcpy(&mp_image_crc,ac_ledger+174u,4u);
 if(!mw_build())return failure(5u,0u,ac_native_safe());
 return 1u;
}
unsigned char ac_body(void){
 unsigned char i,n;
 memcpy(&job,&ac_request,sizeof job);ac_result.state=1u;ac_result.sequence=job.sequence;
 if(job.owner!=0xa5u||job.action!=AC_SAVE_AS||job.drive>1u||job.readonly>1u||!job.sequence||job.capacity<0x400000UL||job.capacity>0x1000000UL)return failure(1u,0u,0u);
 for(n=0;n<128u&&job.path[n];++n){}if(n<2u||n==128u||job.path[0]!='/')return failure(1u,0u,0u);
 for(i=n+1u;i<128u;++i)if(job.path[i])return failure(1u,0u,0u);
 if(!ac_native_safe()||!fetch_home())return failure(1u,0u,0u);
 memset(ac_ledger,0,256u);
 ac_result.phase=WIRE;if(!wire(0u))return 0u;
 ac_result.phase=SAVE;if(!save())return 0u;
 ac_result.phase=PLAN;if(!plan())return 0u;
 ac_result.phase=WIRE;if(!wire(1u))return 0u;
 ac_result.phase=BIND;if(!admission())return 0u;if(!ac_load(BIND))return failure(2u,0u,0u);
 if(!admission())return 0u;
 mw_init();if(!mw_build())return failure(6u,0u,0u);
 if(!ac_native_safe())return failure(7u,0u,0u);
 ac_result.state=2u;ac_result.known_closed=1u;ac_result.can_resume=1u;
 return 1u;
}
