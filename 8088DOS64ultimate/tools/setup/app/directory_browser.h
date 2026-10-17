#ifndef DOS64_DIRECTORY_BROWSER_H
#define DOS64_DIRECTORY_BROWSER_H
#include "bulk_reu.h"
#define DB_ROWS 12
#define DB_NAME_BYTES 128
#define DB_DISPLAY_BYTES 40
#define DB_MAX_ENTRIES 1024
#define DB_IDLE 0
#define DB_BUSY 1
#define DB_DONE 2
#define DB_FAILED 3
#define DB_INPUT 1
#define DB_LEASE 2
#define DB_TRANSPORT 3
#define DB_STATUS 4
#define DB_PROTOCOL 5
#define DB_LIMIT 6
#define DB_CANCEL 7
#define DB_TIMEOUT 8
#define DB_RANGE 9
struct db_request_t {br_u8 owner,target,folders_only; br_u16 first,timeout; char path[128];};
struct db_row_t {br_u8 raw[128],display[40];br_u16 raw_length;br_u8 attr,usable,display_cut;};
struct db_page_t {char path[128];struct db_row_t rows[12];br_u16 first,total,scanned,generation;br_u8 count,previous,next,valid;};
struct db_result_t {br_u8 state,error,transport,rejected,lease,recovery_failed;br_u16 blocks,scanned;};
extern struct db_request_t db_request;
/* Readonly observation: public writes cannot alter state, cause or lease. */
extern struct db_result_t db_result;
extern br_u16 db_now;
extern const struct db_page_t * const db_page;
extern char db_selected_path[128];
/* Integration must acquire/release SAME engine via br_ui_* for the sealed
 * single-handle gateway, or bc_ui_* for two retained contexts. BOTH contexts
 * must be knownclosed before acquire. No public mask substitutes for that.
 * Returns1 success; do not initialize/reinitialize UCI inside these callbacks. */
br_u8 db_lease_acquire(void),db_lease_release(void);
/* Startup after cc65 BSS initialization; does not initialize the transport.
 * Caller owns IRQs/D=0/$01=$35 and atomic elapsed16bit now (<8000 tick gaps).
 * Request snapshots on1accepted;0rejected leaves job/page unchanged except
 * rejected. path is canonical padded absoluteASCII including root'/' and
 * spaces, max127bytes. timeout1..7fff ticks. Defaultowner0 disables start. */
br_u8 db_begin(void);
void db_poll(void),db_cancel(void);
/* Private state/cause authority, including while cleanup remains BUSY.
 * Both refresh the public observation; neither polls/parses new transport. */
br_u8 db_state(void),db_error(void);
/* Committed page is readonly. Replaced only after entire bounded directory,
 * final status and quiet/released lease. Failed/cancelled jobs leave it intact.
 * Rawname retained EXACT only when raw_length<=127; longer names have rawzero
 * and unusable0, never selectable. Display is a separate sanitized40B field.
 * Select revalidates exact raw name/join; failure keeps old selected_path. */
br_u8 db_select(br_u8 row);
/* Writes canonical parent of committed path to selected_path; root->root. */
br_u8 db_parent(void);
#endif
