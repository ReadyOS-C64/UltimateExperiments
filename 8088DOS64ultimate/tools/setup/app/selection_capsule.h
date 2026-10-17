#ifndef DOS64_SELECTION_CAPSULE_H
#define DOS64_SELECTION_CAPSULE_H
#include "bulk_reu.h"
#define SQ_SLOT 0x2c0000UL
#define SQ_BYTES 704u
#define SQ_HOME 32u
#define SQ_DOS 160u
#define SQ_EXISTING 544u
#define SQ_PROFILE 672u
#define SQ_EXISTING_PRESENT 673u
#define SQ_WIRE_CRC 700u
#define SQ_IDLE 0u
#define SQ_BUSY 1u
#define SQ_READY 2u
#define SQ_FAILED 3u
#define SQ_INPUT 1u
#define SQ_LEASE 2u
#define SQ_CANCEL 3u
#define SQ_CLOCK 4u
#define SQ_DMA 5u
#define SQ_CRC 6u
#define SQ_IDENTITY 7u
#define SQ_WRAP 8u
/* Caller owns IRQs/D=0/$01=$35, both stacks, immutable resident code and CRC
 * tables, and exclusive cooperative REU/same-engine access. No interrupt job
 * dispatch, external REU mutation or concurrent phase operation is permitted.
 * Resident dispatcher calls only; its entire caller frame must also return
 * before another phase is loaded. Only current private UI ticket + immutable UI CRC may dispatch overlaid
 * capture. Actual private SS_DONE required. Synchronous bounded DMA/CRC work
 * services CIA clock/RunStop between transfers, holds SAME context UI lease,
 * and returns completely before any overlay swap. Fresh session defaultOFF;
 * old REU bytes alone never grant authority. Failed capture is terminal. */
br_u8 sq_publish(void);
br_u8 sq_state(void),sq_error(void);
void sq_cancel(void);
/* Resident-only verified read, including while FAT is resident: no UI calls or
 * pointer access. Page0=512 bytes, page1=192; input is not authority. Returns
 * exact byte count or0, after full704 + selectedpage CRC verification against
 * private captured identity. Requires READY manager and closedquiet contexts.
 * Result buffer is resident shared scratch, readonly until the NEXT manager/
 * capsule operation; caller must copy/consume before then. No arbitrary host
 * destination, and no lifetime promise across another operation. */
extern br_u8 sq_page;
extern const br_u8 * const sq_bytes;
br_u16 sq_read(void);
#endif
