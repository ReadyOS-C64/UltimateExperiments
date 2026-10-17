#ifndef DOS64_SETUP_IO_H
#define DOS64_SETUP_IO_H
#include "native_fat.h"
extern nf_u8 ns_io_owner,ns_io_error,ns_cancel;
extern nf_u32 ns_capacity;
/* Configure owner/capacity before any NF call; defaultOFF. Context source0 must
 * already be readonly open+INFO known; final coordinator owns its lifecycle. */
#define NS_SOURCE_CACHE 0x3f0000UL
/* One-shot bind after source0 readonlyOPEN+INFO and before nativeimport.
 * Never rebind a liveproducer: a secondbind invalidates terminally. All sources
 * remain immutable until outputfinished/sourceCLOSE; no filesystemlock implied.
 * Explicitinvalidate, knownsourcechange, error/cancel/unknown disable hits. */
nf_u8 ns_source_bind(void);
void ns_source_invalidate(void);
/* FAT phase only: discard cache authority after private clean SI_DONE and both
 * contexts closed. No reset of errors/uncertainty; new source must OPEN/INFO/bind. */
nf_u8 ns_source_rearm(void);
struct ns_cache_state_t {nf_u8 bound,valid,error;nf_u16 count;nf_u32 token,source_bytes,window,hits,misses;};
extern struct ns_cache_state_t ns_cache_state; /*observation only*/
#endif
