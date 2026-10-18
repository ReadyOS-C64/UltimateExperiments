#ifndef DOS64_INSTALL_WRITER_H
#define DOS64_INSTALL_WRITER_H
#include "bulk_reu.h"
#define SI_IDLE 0
#define SI_BUSY 1
#define SI_DONE 2
#define SI_FAILED 3
/* Planned NF producer required; owner default0. Output MUST be fresh owned
 * basename inside root, target2. CREATE_NEW never replaces an existing file.
 * Caller excludes physical mount aliases and owns immutable NF input REU.
 * Both slabs200000/208000 are disjoint32KiB; source callback may use200000 only
 * while no writer operation is pending. Supply atomic elapsed now each poll. */
struct si_request_t {br_u8 owner; br_u32 capacity; br_u16 timeout;char root[128],path[128];};
struct si_result_t {br_u8 state,error,phase,rejected; br_u32 produced,verified,crc;};
extern struct si_request_t si_request;
/* Observation only; private ledger governs state/errors/progress. Terminal
 * success/failure is private. A clean DONE can explicitly rearm; failure cannot. */
extern struct si_result_t si_result;
extern br_u16 si_now;
br_u8 si_begin(void);
void si_poll(void);
void si_cancel(void);
br_u8 si_error(void); /*private first cause, including while BUSY cleanup*/
br_u8 si_state(void); /*private state; refreshes observations*/
br_u8 si_closed_quiet(void); /*cleanup observation, never grants rearm*/
/* FAT phase only, after previous output facts are retained and source0 closed.
 * Rearm before nf_init/new plan; same engine, no uncertainty/error clearing.
 * Only private clean DONE permits a new CREATE_NEW transaction. */
br_u8 si_rearm(void);
/* DONE means CREATE_NEW stream, CLOSE, readonly reopen INFO/fullCRC/EOF/final
 * CLOSE all completed. It does not publish CFG/START or establish power-loss
 * durability. Failure preserves firsterror and new partial output; it may leave
 * a known/uncertain handle requiring outer bounded cleanup (bc_status). */
/* SETUP-only FAT API (numeric DOS64_SETUP_WRITER_CLEANUP=1). First SI error
 * remains terminal. One cleanup attempt drains SI-owned waiting only, then one
 * guarded output1 CLOSE. Never polls/steals pending source0 (NC owns it).
 * Caller supplies fresh elapsed si_now before every poll; <=256 polls, timeout
 * inherited from captured writer request. States0idle/1busy/2closed/3blocked.
 * CLOSED is cleanup only, never workflow success/rearm. si_closed_quiet must
 * still prove BOTH handles closed before overlay/navigation. No reset/retry. */
br_u8 si_cleanup_begin(void);
void si_cleanup_poll(void);
br_u8 si_cleanup_state(void);
br_u8 si_cleanup_error(void); /*1rejected/2bound/3close failure; SI cause unchanged*/
#endif
