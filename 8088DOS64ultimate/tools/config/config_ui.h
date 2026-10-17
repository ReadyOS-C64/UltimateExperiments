#ifndef DOS64_CONFIG_UI_H
#define DOS64_CONFIG_UI_H
#include "bulk_reu.h"
#define CG_IDLE 0u
#define CG_STARTUP 1u
#define CG_BROWSER 2u
#define CG_INSPECT 3u
#define CG_OPTIONS 4u
#define CG_REVIEW 5u
#define CG_DONE 6u
#define CG_FAILED 7u
#define CG_RELOCATE 8u
#define CG_INPUT 1u
#define CG_OWNERSHIP 2u
#define CG_DIRECTORY 3u
#define CG_CONFIG 4u
#define CG_CANCEL 5u
#define CG_CLOCK 6u
#define CG_TIMEOUT 7u
#define CG_LIMIT 8u
struct cg_request_t {br_u8 owner;br_u32 capacity;br_u16 timeout;};
struct cg_result_t {br_u8 state,error,leaf,cleanup,stage,row,columns,ready;};
struct cg_receipt_t {
 br_u16 session;br_u32 cfg_identity,capacity;
 char home[128],release_home[128],new_home[128];
 br_u8 columns;br_u16 ini_length;br_u8 ini[32];
};
extern struct cg_request_t cg_request;
extern struct cg_result_t cg_result; /* observation only */
extern struct cg_receipt_t cg_receipt; /* refreshed only by private getter */
/* Standalone CONFIG only. One initialization, one same-engine startup CLOSE1/2,
 * then RI attach before browser leases. No engine reset/SC rearm, file writes,
 * REU mutation or output facts. All browser/RI/RM code stays resident. */
br_u8 cg_boot(void),cg_begin(void);
void cg_poll(void),cg_cancel(void),cg_default_start(void);
br_u8 cg_state(void),cg_error(void),cg_closed_quiet(void);
/* Private DONE + current same RI session/home/body + known closed/quiet.
 * Immediately copy refreshed observation before any callback/phase replacement.
 * Selected release/home are not file identity or output authorization. Capacity
 * is read from validated original CFG. Existing media/readonly bits unchanged.
 * Columns is explicitly a NEW selection (initial default80); this UI does not
 * read old DOS64.INI or claim to preserve its default. Original INI is untouched.
 * Publisher must separately refresh RM and verify the matched source assets. */
br_u8 cg_get(void);
#endif
