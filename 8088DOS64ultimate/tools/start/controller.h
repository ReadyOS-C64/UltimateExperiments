#ifndef DOS64_START_CONTROLLER_H
#define DOS64_START_CONTROLLER_H
#include "bulk_reu.h"
/* Serialized DATA; patch before first execution. Never store home only in BSS. */
struct lc_control_t {br_u8 owner;br_u16 uci_base;char home[128];};
struct lc_result_t {br_u8 state,error,cleanup,phase,loaded; br_u32 checked,main_crc;
                   br_u8 failed_op,io_error,transport;};
extern struct lc_control_t lc_control;
extern struct lc_result_t lc_result;
extern br_u16 lc_now;
void lc_init(void); /*startup-only, initializes same single-context UCI engine*/
br_u8 lc_validate_start(void); /*canonical persistent settings only, no fileIO*/
br_u8 lc_begin(void); /*1accepted, ownerA5, exact canonical home;0no publication*/
void lc_poll(void),lc_cancel(void);
/* One-shot private authority; prepared4 -> consumed5. Reject clears ready.
 * No other FILES/UCI owner may interleave; consume immediately before DMA. */
br_u8 lc_prepare_handoff(void),lc_consume_handoff(void);
/* DONE=2 means staged/closed/CRC-verified/patched and anchor ready, not executed.
 * Caller owns >=4MiB baseline arenas, RAM/I/O, IRQ/NMI, D=0 and softwarestack.
 * Update lc_now from coherent elapsed clock; polling gaps less thanhalf-wrap.
 * Error is first cause. No retry/in-place file writes. Runtimehandoff separate. */
#endif
