#include "setup_io.h"
#include "bulk_context.h"
#include "platform.h"
#include "install_writer.h"
#include <string.h>
#if defined(DOS64_SETUP_COOPERATIVE) && DOS64_SETUP_COOPERATIVE
#include "setup_cooperate.h"
#endif
nf_u8 ns_io_owner,ns_io_error,ns_cancel;
nf_u32 ns_capacity;
nf_u32 nf_io_address;
nf_u16 nf_io_buffer,nf_io_length;
nf_u8 nf_io_direction,nf_io_status;
extern void nf_dma(void);
static nf_u16 transfer(nf_u32 address,void*buffer,nf_u16 length,nf_u8 direction){
 nf_u16 chunk,left;nf_u8*p;
 if(ns_io_owner!=0xa5||ns_io_error||ns_cancel||!length||ns_capacity<0x400000UL||ns_capacity>0x1000000UL||address>=ns_capacity||length>ns_capacity-address)return 0;
#if defined(DOS64_SETUP_COOPERATIVE) && DOS64_SETUP_COOPERATIVE
 if(!nc_service())return 0;
#endif
 left=length;p=buffer;
 while(left){chunk=left;if((address&65535UL)+chunk>65536UL)chunk=(nf_u16)(65536UL-(address&65535UL));
  nf_io_address=address;nf_io_buffer=(nf_u16)p;nf_io_length=chunk;nf_io_direction=direction;nf_dma();
  if(nf_io_status){ns_io_error=1;
#if defined(DOS64_SETUP_COOPERATIVE) && DOS64_SETUP_COOPERATIVE
   nc_service();
#endif
   return length-left;}
#if defined(DOS64_SETUP_COOPERATIVE) && DOS64_SETUP_COOPERATIVE
  if(!nc_service())return length-left;
#endif
  address+=chunk;p+=chunk;left-=chunk;
 }return length;
}
nf_u16 nf_store_read(nf_u32 a,void*b,nf_u16 n){return transfer(a,b,n,1);}
nf_u16 nf_store_write(nf_u32 a,const void*b,nf_u16 n){return transfer(a,(void*)b,n,0);}
nf_u8 nf_cancelled(void){
#if defined(DOS64_SETUP_COOPERATIVE) && DOS64_SETUP_COOPERATIVE
 if(!nc_service())return 1;
#endif
 return ns_cancel||ns_io_error||ns_io_owner!=0xa5;}
static nf_u8 operation(nf_u8 op,nf_u32 offset,nf_u16 count){
#if defined(DOS64_SETUP_COOPERATIVE) && DOS64_SETUP_COOPERATIVE
 return nc_operation(op,offset,count);
#else
 nf_u16 guard=0;
 if(ns_io_owner!=0xa5||ns_io_error||ns_cancel||!ps_clock_poll())return 0;
 br_now=ps_ticks;bc_slot=0;memset(&br_request,0,sizeof(br_request));br_request.op=op;br_request.offset=offset;br_request.address=NS_SOURCE_CACHE;br_request.length=count;
 if(!bc_start())return 0;
 while(br_result.state==BR_BUSY){
  if(ns_cancel||!ps_clock_poll()||++guard==0){bc_cancel();if(!ns_io_error)ns_io_error=2;return 0;}
  br_now=ps_ticks;bc_poll();
 }return br_result.state==BR_DONE&&!br_result.error&&!br_result.uncertain;
#endif
}
/* Dedicated sourcecache survives writer200000 readback reuse. */
struct ns_cache_state_t ns_cache_state;
static struct ns_cache_state_t cache;
static nf_u8 cache_started;
static nf_u32 cache_capacity;
static void cache_publish(void){ns_cache_state=cache;}
static void cache_fail(nf_u8 e){cache.bound=cache.valid=0;if(!cache.error)cache.error=e;if(!ns_io_error&&!ns_cancel)ns_io_error=4;cache_publish();}
void ns_source_invalidate(void){cache_fail(4);}
nf_u8 ns_source_bind(void){nf_u32 token,size;
#if defined(DOS64_SETUP_COOPERATIVE) && DOS64_SETUP_COOPERATIVE
 if(!nc_service()){cache_fail(ns_cancel?5:2);return 0;}
#endif
 if(cache_started){cache_fail(4);return 0;}
 if(ns_io_owner!=0xa5||ns_io_error||ns_cancel||ns_capacity<0x400000UL||ns_capacity>0x1000000UL||(ns_capacity&65535UL)){cache_fail(ns_cancel?5:1);return 0;}
 token=bc_source_identity();size=bc_source_bytes();
 if(!token||ns_capacity!=bc_config[0].capacity||(size!=0x200000UL&&size!=0x1400000UL)){cache_fail(2);return 0;}
 cache_started=cache.bound=1;cache.valid=cache.error=0;cache.token=token;cache.source_bytes=size;cache_capacity=ns_capacity;cache.hits=cache.misses=0;cache_publish();return 1;
}
/* Token covers private size: only OPEN/INFO can set it (both advanceepoch),
 * readonlysource forbids SAVE; CLOSE/re-init/wrap/unknown/error refuse token. */
static nf_u8 cache_check(void){
#if defined(DOS64_SETUP_COOPERATIVE) && DOS64_SETUP_COOPERATIVE
 if(!nc_service()){cache_fail(ns_cancel?5:2);return 0;}
#endif
 if(!cache.bound||ns_io_owner!=0xa5||ns_capacity!=cache_capacity||ns_io_error||ns_cancel||bc_source_identity()!=cache.token){cache_fail(ns_cancel?5:2);return 0;}return 1;
}
nf_u16 nf_disk_read(nf_u32 offset,void*buffer,nf_u16 length){nf_u16 copied=0,n,relative;nf_u32 start;nf_u8*p=buffer;
 if(!length||length>512u||!cache_check()||offset>=cache.source_bytes||length>cache.source_bytes-offset){cache_fail(1);return 0;}
 while(copied<length){
  if(!cache_check())return copied;
  if(!cache.valid||offset<cache.window||offset-cache.window>=cache.count){
   cache.valid=0;start=offset&0xffff8000UL;n=cache.source_bytes-start>=32768UL?32768u:(nf_u16)(cache.source_bytes-start);
   if(!operation(BR_SEEK,start,0)||!operation(BR_LOAD,0,n)||br_result.actual!=n){cache_fail(3);return copied;}
   if(!cache_check())return copied;
   cache.window=start;cache.count=n;cache.valid=1;++cache.misses;
  }else ++cache.hits;
  relative=(nf_u16)(offset-cache.window);n=cache.count-relative;if(n>length-copied)n=length-copied;
  if(nf_store_read(NS_SOURCE_CACHE+relative,p,n)!=n){cache_fail(3);return copied;}
  copied+=n;p+=n;offset+=n;
 }
 cache_publish();return copied;
}

#pragma code-name(push,"FAT_CODE")
nf_u8 ns_source_rearm(void){
 if(si_state()!=SI_DONE||!bc_files_closed()||ns_io_owner!=0xa5||ns_io_error||ns_cancel||cache.error)return 0;
 memset(&cache,0,sizeof(cache));cache_started=0;cache_capacity=0;cache_publish();return 1;
}
#pragma code-name(pop)
