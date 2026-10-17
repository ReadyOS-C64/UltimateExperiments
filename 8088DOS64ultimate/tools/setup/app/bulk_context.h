#ifndef DOS64_BULK_CONTEXT_H
#define DOS64_BULK_CONTEXT_H
#include "bulk_reu.h"
/* Two terminal-switched software contexts over ONE UCI engine. Target independence
 * is a model contract pending installed-firmware/hardware qualification.
 * Startup-only bc_init; never call br_* directly thereafter. C IRQ/clock/memory
 * rules from bulk_reu.h apply. Input/output slabs must not alias live source data.
 * Slot0 fixes target1 and readonly OPEN(mode1); slot1 fixes target2. All OPENs
 * still require explicit A5 canonical owned-root authority, including source.
 * Config/request are inputs; bc_status and br_result are observation-only,
 * never authority. Wrapper entries restore the private result ledger before
 * state decisions; FILES handle snapshots govern alias and closed checks.
 * SEEK requires a known file size and offset<=size, avoiding firmware EOF
 * clipping/allocation-growth ambiguity. INFO establishes size; CREATE_NEW starts0.
 * Same source/output pathname (ASCII case-insensitive) is refused while either
 * other handle is open/uncertain. Caller must exclude distinct mount aliases
 * for the same physical file; lexical checks cannot establish disk identity.
 * Context selection/start is refused while either command is busy or UCI unsafe.
 * UI lease requires BOTH handles closed; use same engine directory-only commands.
 */
struct bc_status_t { struct br_result_t result; br_u32 position,file_size; br_u8 position_known,size_known,first_error; };
extern struct br_config_t bc_config[2];
extern struct bc_status_t bc_status[2];
extern br_u8 bc_slot; /* requested slot0/1 input, not active authority */
void bc_init(void);
br_u8 bc_start(void); /* snapshots br_request; 1accepted,0reject */
void bc_poll(void);
void bc_cancel(void);
br_u8 bc_files_closed(void); /*1 only both private handles closed + quiet/unleased*/
br_u8 bc_ui_acquire(void);
br_u8 bc_ui_release(void);
/* Clears first_error only for selected CLOSED context at verified quiet point.
 * Also clears the selected terminal error/transport observation; does not clear uncertainty or reinitialize UCI. */
br_u8 bc_clear_error(void);
/* Readonlysource authority for dedicated cache consumer. Nonzero private32bit
 * token only when slot0 is known-open readonly, knownsize/position, no first
 * error, identical capturedconfig and globallyquiet/unleased. OPEN/CLOSE/INFO
 * advances token, wrap/re-init disables it. Publicobservations never authorize.
 * Caller keeps filesystemcontent immutable; token is not an externalfilelock. */
br_u32 bc_source_identity(void);
br_u32 bc_source_bytes(void);
/* SETUP-only FAT callable; private output1 handle plus globally quiet/unleased.
 * Available only with numeric DOS64_SETUP_WRITER_CLEANUP=1. No context switch,
 * no leaf poll, no error clear; source0 can remain known-open. */
br_u8 bc_output_closed(void);
#endif
