#ifndef DOS64_NATIVE_FINISH_H
#define DOS64_NATIVE_FINISH_H
/* Optional actual native backend component; zero-argument cc65 ABI.
 * Caller binds a private Finish intent/discard policy, keeps the broker lease,
 * installs/zeros this fresh phase once, and retires all prior worker frames.
 * Not a guest INT21/file-buffer flush. Exit applications to DOS first.
 */
typedef unsigned char fn_u8;
typedef unsigned short fn_u16;
extern fn_u8 fn_enable;  /* factory0; callerA5 only with private Finish intent */
extern fn_u8 fn_discard; /* captured explicit A=1/B=2 discard policy */
extern fn_u16 fn_limit;  /* captured elapsed deadline1..32767 */
extern fn_u8 fn_cancel; /* caller reconciles cancel before begin; set after
                         admitted begin to request terminal cancellation */
/* begin1 owns Finish, permanently fences guest Resume, clears per-job cancel.
 * begin0 refuses without FILE transaction/ownership; caller retains its intent.
 * It verifies already-issued write-through HD work is complete. It cannot
 * persist unsaved application data or DOS logical file buffers in guest RAM.
 */
fn_u8 fn_begin(void);
void fn_poll(void); /* state1: bounded busy,2: knownclose candidate,3: failure */
fn_u8 fn_state(void);
fn_u8 fn_error(void); /* first admitted cause; raw FILES/UCI remain available */
fn_u8 fn_known_closed(void); /* actual close proof only; may1 even on latererror */
/* 1 at most once after native known CLOSE, exact current private broker/media
 * context, fresh coherent32 clock/STOP and quiet transport. Zero refuses.
 * No observation field or public enable flag grants authority. Consume before
 * retiring this phase. Neither success nor error ever permits guest Resume.
 */
fn_u8 fn_take_restart(void);
#endif
