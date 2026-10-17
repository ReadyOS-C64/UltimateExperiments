#ifndef DOS64_PUBLISH_WORKER_H
#define DOS64_PUBLISH_WORKER_H
#include "bulk_reu.h"
/* PUB-only, one-shot under authentic private publish ticket after real FW_DONE.
 * Caller returns entirely before replacement. No public observation grants
 * source or output authority. 1 means all outputs verified and CFG LAST;
 * error8 denotes bounded completion display refusal; failure is terminal and may retain pending output for explicit owner cleanup. */
br_u8 pw_run(void),pw_state(void),pw_error(void),pw_stage(void),pw_closed_quiet(void);
#endif
