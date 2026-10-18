#ifndef DOS64_BULK_UCI_H
#define DOS64_BULK_UCI_H
#include "bulk_reu.h"
/* Directory frontend hook into the SAME existing UCI engine. Acquire the
 * br_ui lease while filehandleclosed; never run a second wire transport, OPEN
 * files behind FILES, reinitialize the engine, or access it from an IRQ.
 * Directory-only caller owns command/response validation, path write authority,
 * bounded block/row count, and atomic elapsed now. Raw start returns0accepted,
 * 1rejected (opposite br_start). Commands1..895; data cap<=896,status<=256;
 * wirestatusmax255. Every BLOCK is fully drained by transport; inspect flags,
 * copy data, then accept; MORE requires bounded continuation. Release only
 * after DONE or a verified quiet FAILED (not INPUT/ID rejection).
 */
#define BR_UCI_BLOCK 5
#define BR_UCI_DONE 9
#define BR_UCI_FAILED 10
extern br_u8 uci_state,uci_error,uci_recovery_failed,uci_flags,uci_last_status;
extern br_u8 uci_command[],uci_data[],uci_status[];
extern br_u16 uci_now,uci_timeout,uci_recovery_timeout;
extern br_u16 uci_command_len,uci_data_len,uci_status_len;
extern br_u16 uci_data_capacity,uci_status_capacity;
br_u8 uci_start(void);
void uci_poll(void),uci_accept(void),uci_abort(void);
#endif
