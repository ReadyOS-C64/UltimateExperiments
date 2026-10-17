#ifndef DOS64_EXISTING_CFG_H
#define DOS64_EXISTING_CFG_H
#include "bulk_reu.h"
#ifndef DOS64_CONFIG_ATTACHED
#define DOS64_CONFIG_ATTACHED 0
#endif
#define RI_IDLE 0
#define RI_BUSY 1
#define RI_DONE 2
#define RI_FAILED 3
#define RI_STARTUP 1
#define RI_FILE 2
#define RI_SIZE 3
#define RI_CONFIG 4
#define RI_HOME 5
#define RI_CANCEL 6
#define RI_CLOCK 7
#define RI_TIMEOUT 8
#define RI_LIMIT 9
struct ri_request_t { br_u8 owner; br_u32 capacity; br_u16 timeout; char home[128]; };
struct ri_result_t { br_u8 state,error,phase,leaf,transport,cleanup; br_u16 session; };
struct ri_receipt_t { br_u16 session; br_u32 identity; char home[128]; br_u8 bytes[576]; };
extern struct ri_request_t ri_request;
/* cleanup is a refreshed observation:1 whileBUSY or startupSCnotready or
 * BC files not knownclosed/quiet. It never substitutes for ri_closed_quiet()
 * or ri_get private admission. Read after poll/state/error/cancel/begin. */
extern struct ri_result_t ri_result;
extern struct ri_receipt_t ri_receipt;
extern char ri_query_home[128];
extern br_u16 ri_query_session;
/* Own native setup entry, initializes ONE engine/platform once. No prior
 * jobs, lease or other owner. Real CLOSE1+2 occurs after accepted begin.
 * All library code/private receipt lifetime is this phase; no retired calls. */
br_u8 ri_boot(void);
#if DOS64_CONFIG_ATTACHED
/* Composed CONFIG only: never initializes an engine or rearms SC. Both
 * private startup-ready and BC closed/quiet (no UI lease) must be current.
 * This profile disables ri_boot; attach is one-shot and called before browse. */
br_u8 ri_attach(void);
#endif
br_u8 ri_begin(void);
void ri_poll(void),ri_cancel(void);
br_u8 ri_state(void),ri_error(void),ri_closed_quiet(void);
/* Refresh observation from private validated bytes only at private DONE,
 * matching current session and canonical padded query home, known quiet.
 * 0 leaves previous observation unchanged; it never grants a capability. */
br_u8 ri_get(void);
#endif
