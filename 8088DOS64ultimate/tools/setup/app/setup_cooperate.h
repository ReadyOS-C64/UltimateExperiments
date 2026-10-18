#ifndef DOS64_SETUP_COOPERATE_H
#define DOS64_SETUP_COOPERATE_H
#include "bulk_reu.h"
#define NC_CANCEL 1u
#define NC_CLOCK 2u
#define NC_LEAF 3u
#define NC_OWNER 4u
#define NC_EXTERNAL 5u
#define NC_BOUND 6u
/* HIGH-only; caller installed exact HIGH bootstrap, holds authentic FAT ticket,
 * owns sole keyboard/clock/engine. Explicit bracket; never enable during SU/PUB.
 * Error terminal for session. No engine reset/retry, no public flag authority.
 * Exhausted pending cleanup is truthful uncertainty, never navigation authority.
 * Source0 safetyCLOSE only; output1 remains SI/root ownership.
 * nc_end also requires private NF inactivity; call it under FAT ticket before
 * replacement. Disabled nc_service/getters never call overlaid FAT code. */
br_u8 nc_begin(void),nc_end(void),nc_service(void);
br_u8 nc_error(void),nc_pending(void),nc_closed_quiet(void);
br_u8 nc_leaf_error(void),nc_transport_error(void);
br_u8 nc_operation(br_u8 op,br_u32 offset,br_u16 count);
/* Source0 only: caller fills canonical bc_config[0]/br_request from checked
 * capsule before this synchronous call. Only readonlyOPEN/INFO/CLOSE; gateway
 * privately snapshots config/request before wire. SafetyCLOSE remains allowed
 * after failure; return1 then proves close, NEVER clears nc_error for workflow. */
br_u8 nc_prepared(void);
#endif
