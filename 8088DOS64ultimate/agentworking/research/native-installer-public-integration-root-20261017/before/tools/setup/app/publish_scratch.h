#ifndef DOS64_PUBLISH_SCRATCH_H
#define DOS64_PUBLISH_SCRATCH_H
#include "bulk_reu.h"
/* Profile-only explicit union, private owner gates enforce disjoint lifetime.
 * Arrays retain their true sizeof; no pointer-type replacement. */
union pub_scratch_t {br_u8 verify[512];struct {br_u8 input[256],output[256];} pb;};
extern union pub_scratch_t pub_scratch;
#endif
