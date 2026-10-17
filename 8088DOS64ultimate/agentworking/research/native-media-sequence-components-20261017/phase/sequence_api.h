#ifndef DOS64_MEDIA_SEQUENCE_API_H
#define DOS64_MEDIA_SEQUENCE_API_H
/* cc65 zero-argument native ABI; numeric DOS64_MEDIA_SEQUENCE=1 only.
 * A000 phase/FILE engine and its private state must stay loaded throughout.
 * Exclusive native broker stage8/cache0 required; caller owns clock/STOP
 * service and sets tw_cancel before poll. This API never calls engine init.
 * All begin/poll/take calls preserve caller P and 80..83; no C stack changes.
 */
typedef unsigned char tw_u8;
typedef unsigned short tw_u16;
extern char tw_home[128]; /* canonical current CFG home incl zero padding */
extern tw_u16 tw_sequence; /* nonzero start hint, captured on admitted begin */
extern tw_u16 tw_limit; /* elapsed16 bound1..32767, captured on begin */
extern tw_u8 tw_mode,tw_cancel;
#define TW_ALLOCATE 2u
/* begin returns1 iff this job owns alternate FILES, even admitted failure.
 * Poll until state2 DONE or3 FAILED; state1 means borrowed/in progress.
 * Never navigate/resume with closed0; error remains the first native cause.
 */
tw_u8 tw_begin(void);
void tw_poll(void);
tw_u8 tw_state(void);
tw_u8 tw_error(void);
tw_u8 tw_closed(void);
/* AX16 selected sequence at most once. Zero refuses. Fresh coherent SAMPLE4
 * permits a bounded retry; lost broker/context/clock authority is irreversible.
 * Any new begin attempt withdraws a previous unconsumed selection.
 * This is readonly selection, not a filesystem reservation; downstream CREATE
 * and rename must still be no-replace under the same exclusive job lease.
 */
tw_u16 tw_take_sequence(void);
#endif
