#ifndef OWNED_DIRECTORY_PRELUDE_H
#define OWNED_DIRECTORY_PRELUDE_H
#include "bulk_reu.h"
struct dp_control_t {br_u8 owner,nonce[16];char root[128];};
struct dp_result_t {char magic[4];br_u8 state,error,cleanup,closed,phase,mkdir_attempts,created,owner_verified,cwd_changed,raw,handle,reserved; br_u8 nonce[16],readback[52];};
extern struct dp_control_t dp_control;
extern volatile struct dp_result_t dp_result;
extern volatile br_u8 dp_cancel;
void dp_init(void),dp_step(void),dp_entry(void);
#endif
