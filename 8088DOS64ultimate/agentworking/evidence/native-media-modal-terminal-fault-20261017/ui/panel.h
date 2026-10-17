#ifndef DOS64_MEDIA_PANEL_H
#define DOS64_MEDIA_PANEL_H
#include "platform.h"
#define MU_PRESENT 1u
#define MU_READONLY 2u
#define MU_DIRTY 4u
#define MU_UNCERTAIN 8u
#define MU_MENU 1u
#define MU_CONFIRM 2u
#define MU_PATH 3u
#define MU_WAIT 4u
#define MU_ERROR 5u
#define MU_SAFE 6u
#define MU_SAVE 1u
#define MU_SAVE_AS 2u
#define MU_INSERT 3u
#define MU_EJECT 4u
#define MU_PROTECT 5u
#define MU_RESUME 6u
#define MU_FINISH 7u
#define MU_CANCEL 8u
#define MU_DISCARD 1u
/* FINISH flags instead carry explicit discard authorization bits A=1/B=2. */
struct mu_drive_t {ps_u8 flags;char path[128];};
struct mu_view_t {struct mu_drive_t drive[2];ps_u8 can_resume;ps_u8 percent;char operation[40];};
struct mu_event_t {ps_u16 ticket;ps_u8 action,drive,flags;char path[128];};
struct mu_result_t {ps_u8 mode,drive,action,error;ps_u16 ticket;};
extern struct mu_view_t mu_view;
extern struct mu_event_t mu_event;
extern struct mu_result_t mu_result;
extern ps_u16 mu_reply_ticket;
extern ps_u8 mu_reply_error,mu_reply_safe,mu_block_error;
/* Host presentation only. It does not access FILES/REU/guest BDA, reset clocks,
 * grant ownership, clear dirty flags or certify persistence. The native modal
 * controller must first pause/flush/invalidate the borrowed RAM and preserve
 * the guest/C/device context; it validates every intent independently.
 * view/reply/event/result are observations or caller inputs, never authority.
 * init requires quiescent controller/session; poll uses physical CIA1 keys.
 * refresh consumes a bounded view and repaints. take consumes one private
 * intent into event. reply accepts only the active private WAIT ticket.
 * Backend completion must refresh actual disk state before successful reply.
 * No standalone SETUP platform_init/clock_init is called by this module.
 */
/* Terminal safety input: set mu_block_error then call mu_block. Sticky private
 * latch retains first error and pending ticket, refuses take/reply/new intents,
 * and ignores public can_resume. mu_init is ONLY fresh admitted-session init;
 * a terminal controller must never reinitialize a blocked session. */
void mu_init(void),mu_poll(void),mu_refresh(void),mu_block(void);
ps_u8 mu_take(void),mu_reply(void),mu_cancel_requested(void);
#endif
