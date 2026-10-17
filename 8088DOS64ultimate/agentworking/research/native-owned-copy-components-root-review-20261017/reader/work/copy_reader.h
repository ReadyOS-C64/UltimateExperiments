#ifndef OWNED_COPY_READER_H
#define OWNED_COPY_READER_H
#include "bulk_reu.h"
/* PRIVATE purpose component, defaultOFF. Exclusive native RAM/CIA/UCI owner.
 * Source is the fixed historically owned regular DOSHD.IMG. Root is an
 * externally proven fresh owned destination folder, never source == destination.
 * COPY0B uses firmware CREATE_NEW; actual success requires full host readback.
 * No REU command/DMA, no filesystem delete/rename or arbitrary source path.
 * Only cr_ack may change after acceptance. No reentry/deadline renewal.
 */
struct cr_control_t {br_u8 owner; br_u8 nonce[16]; char root[128];};
struct cr_header_t {char magic[4];br_u8 version,state;br_u16 frame;br_u8 nonce[16];br_u32 offset;br_u16 count,reserved;br_u32 crc,read,total,header_crc;};
struct cr_ack_t {br_u16 frame;br_u8 cancel,go;};
struct cr_result_t {char magic[4];br_u8 state,error,cleanup,closed,phase,eof,copy_attempts,copy_uncertain;br_u32 read,ticks,mismatch;br_u8 file_error,transport,raw,handle,cwd_changed;};
extern struct cr_control_t cr_control;
extern volatile struct cr_header_t cr_header;
extern volatile struct cr_ack_t cr_ack;
extern volatile struct cr_result_t cr_result;
void cr_init(void),cr_step(void),cr_entry(void);
/* Header48B,ACK4B,result29B. States0off,1busy,2immutableframe,4done,FFfailed.
 * 640 frames of32768 bytes cover0..20MiB. After durable host bytes, while
 * coherently paused write exact LE16 frame, readback, then GO=A5 once.
 * Cancel byte=1 is terminal. Nonzero cold ACK refuses before any wire command.
 * Each READ04 must return exact512; one EOF0 then one final known CLOSE.
 * Header and4000..BFFF are immutable whilepublished. A failure is reported
 * independently in cr_result and never repaints a pending frame or payload.
 */
#endif
