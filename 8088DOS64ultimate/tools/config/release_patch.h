#ifndef DOS64_RELEASE_PATCH_H
#define DOS64_RELEASE_PATCH_H
#include "bulk_reu.h"
/* CONFIG-private release-bound adapter, NOT a generic template API.
 * rp_admit consumes the publisher's private five-file verified/known-closed
 * authority once and returns its immutable canonical newhome. NULL refuses.
 * No UI/receipt callback while executing. Only matched release_assets.h.
 * rp_buffer[0..255] source/readback, [256..511] untouched expected output.
 * read/write callbacks service clock/STOP and retain first cause. On write,
 * callback STOREs expected half then initializes first half to its complement,
 * FETCHes destination into first half. Caller owns both buffers and CRCtables.
 * Partial bytes are disposable and NEVER establish readiness on failure. */
/* rp_error reports the latest invocation; rejected reuse may report authority1.
 * No reuse invokes callbacks or revives readiness. Publisher firstcause stays
 * private/sticky independently of this observation. */
extern br_u8 rp_buffer[512],rp_error;
extern br_u32 rp_output_crc;
const char *rp_admit(void);
br_u8 rp_read(br_u16 offset,br_u16 count);
br_u8 rp_write(br_u16 offset,br_u16 count);
br_u8 rp_patch(void);
#endif
