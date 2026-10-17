#ifndef DOS64_JOURNAL_GATE_H
#define DOS64_JOURNAL_GATE_H
#include "bulk_reu.h"
/* Verified cold asset only; same existing COREengine and actualSCready.
 * No initialization/rearm of the transport, no active/retired INO frame. */
#define JG_BUSY 1u
#define JG_DONE 2u
#define JG_FAILED 3u
#define JG_NONE 0u
#define JG_OLD 1u
#define JG_NEW 2u
#define JG_MISSING 3u
extern char jg_home[128]; /*captured canonical home; accepted only at begin*/
extern br_u8 jg_state_observed,jg_error_observed,jg_cleanup_observed;
br_u8 __fastcall__ jg_dispatch(br_u8 selector); /*matched entry6546, selectors0init1begin2poll3state4error5cleanup6class7boot8cancel; poll/cancel return private state*/
br_u8 jg_init(void); /*one-shot phasezero after actualclosed/quiet*/
br_u8 jg_begin(void);
void jg_poll(void),jg_cancel(void),jg_clock_fail(void);
br_u8 jg_state(void),jg_error(void),jg_cleanup(void),jg_class(void);
/* Only no-journal path can grant this first read-only slice's boot gate.
 * A valid pending journal still requires explicit completion/archive. */
br_u8 jg_boot_ready(void);
br_u8 __fastcall__ jg_recovery_copy(br_u8 *out); /*147-byte private one-shot recovery receipt*/
#endif
