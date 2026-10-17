#ifndef DOS64_MEDIA_REINSPECT_H
#define DOS64_MEDIA_REINSPECT_H
#include "bulk_reu.h"
#define RM_IDLE 0u
#define RM_BUSY 1u
#define RM_DONE 2u
#define RM_FAILED 3u
#define RM_INPUT 1u
#define RM_FILE 2u
#define RM_SIZE 3u
#define RM_GEOMETRY 4u
#define RM_DMA 5u
#define RM_COMPARE 6u
#define RM_CANCEL 7u
#define RM_CLOCK 8u
#define RM_TIMEOUT 9u
#define RM_LIMIT 10u
#define RM_OWNER 11u
#define RM_STAGE 0x200000UL
#define RM_STAGE_BYTES 368640UL
/* Standalone CONFIG phase only: RI859968ff and this module remain loaded.
 * Caller owns exclusive REU200000..259FFF, CRCtablesC900..CCFF, RAM35,
 * softwarestackCD00..CFFF, and the ONE existing BC engine after RI success.
 * No bc_init/br_* reset, running emulator or active installer attachment.
 * Filesystem media remain immutable throughout inspection/receipt use.
 * Receipts describe completed readonly reads; they are not filesystem locks.
 */
struct rm_request_t {br_u8 owner;br_u16 timeout,session;char home[128];};
struct rm_result_t {br_u8 state,error,phase,drive,leaf,transport,cleanup;br_u32 checked;};
struct rm_receipt_t {br_u16 session;br_u32 cfg_identity;br_u8 present,readonly,profile,crc_mask;br_u32 crc[2];br_u8 cfg[576];};
extern struct rm_request_t rm_request;
extern struct rm_result_t rm_result; /* observation only */
extern struct rm_receipt_t rm_receipt; /* observation refreshed by private getter */
extern br_u16 rm_query_session;
extern char rm_query_home[128];
/* one-shot; query must match private accepted RI session/home. A/B INFOexact
 * 360KiB, LOADfullstage then independent READ04/FETCH fullcompare+freshCRC;
 * C INFOexact2/20MiB and strict known-profile MBR/BPB, no fullCcopy/CRCclaim.
 * CRCmask distinguishes valid zero CRC from absent/unverified media.
 * Errors latch first native cause before same-poll keys/clock; active cleanup
 * drains at most256 polls, at mostone CLOSE, no hidden retry/reset/navigation.
 */
br_u8 rm_begin(void);
void rm_poll(void),rm_cancel(void);
br_u8 rm_state(void),rm_error(void),rm_closed_quiet(void),rm_get(void);
#endif
