#ifndef DOS64_SETUP_OVERLAY_H
#define DOS64_SETUP_OVERLAY_H
#include "bulk_reu.h"
#define SO_UI 1
#define SO_FAT 2
#define SO_PUBLISH 3
#define SO_IDLE 0
#define SO_BUSY 1
#define SO_READY 2
#define SO_FAILED 3
#define SO_INPUT 1
#define SO_LEASE 2
#define SO_DMA 3
#define SO_CRC 4
#define SO_FILE 5
#define SO_HEADER 6
#define SO_CANCEL 7
#define SO_TIMEOUT 8
#define SO_TICKET 9
#define SO_UI_SLOT 0x3e0000UL
#define SO_FAT_SLOT 0x3e8000UL
#define SO_PUBLISH_SLOT 0x2d0000UL
struct so_request_t {br_u8 owner;br_u32 capacity;br_u16 timeout;char home[128];};
struct so_result_t {br_u8 state,phase,error,leaf,transport,cleanup_failed,rejected,active;br_u16 ticket;};
extern struct so_request_t so_request;
extern struct so_result_t so_result; /* observation only */
extern br_u16 so_now,so_ticket;
extern br_u8 so_phase_request;
/* Caller owns $01=$35/IRQs, both stacks, immutable resident code/assets and
 * sole REU/UCI access; sourcecaps installed separately from actual detection.
 * UI is included in initial PRG. Prepare is startup-only after truthful firmware
 * target1/2 closure, captures/CRC-checks UI into its separate REU slot, permitting
 * the initial browser before a home is known. Capacity/timeout snapshot then;
 * bind_home explicitly commits canonical nonroot home after UI job returns.
 * Default owner0 disables all operations. All callbacks/returns are resident. */
br_u8 so_prepare(void);
br_u8 so_bind_home(void); /*one-shot, UI ready/inactive/closedquiet*/
/* Private terminal state/cleanup authority; observations never stop draining.
 * closed_quiet does not grant UI/FAT execution or permission to reset a job. */
br_u8 so_state(void);
br_u8 so_closed_quiet(void);
/* Begin asynchronous replacement, phase input UI1/FAT2. FAT loads exact readonly
 * home/SETUP.FAT OPEN/INFO/LOAD/CLOSE before checked lease/DMA/CRC publication.
 * Caller polls monotonic elapsed now, duration1..7fff and gaps<8000ticks. No
 * replacement while a phase ticket or open/uncertain/active context exists. */
br_u8 so_begin(void);
void so_poll(void),so_cancel(void);
/* Gate the ENTIRE phase job with a private monotonically advancing ticket.
 * Enter validates current RAM CRC and requires closedquiet engine. Leave takes
 * so_ticket input, requires exact current ticket and closedquiet. Root dispatcher
 * must never invoke UI/FAT APIs without its active matching ticket, never swap
 * from an overlaid function, and copy paths/facts before retiring UI_RO. */
br_u8 so_enter(void);
br_u8 so_leave(void);
/* Resident gate: only active UI, closedquiet and current immutable UI CRC.
 * Returns private ticket or0; never trust public phase observations. */
br_u16 so_ui_ticket(void);
br_u16 so_fat_ticket(void); /* authentic active FAT+fullRAMCRC+closedquiet */
br_u16 so_publish_ticket(void); /* private active publisher + immutable CRC */
/* Private snapshotted configured capacity,0 before ownership snapshot.
 * This scalar alone grants no execution/READY authority. */
br_u32 so_capacity(void);
#endif
