#ifndef DOS64_SETUP_SELECT_H
#define DOS64_SETUP_SELECT_H
#include "bulk_reu.h"
#define SS_BUSY 1u
#define SS_DONE 2u
#define SS_FAILED 3u
#define SS_INPUT 1u
#define SS_DIRECTORY 2u
#define SS_CANCEL 3u
#define SS_CLOCK 4u
#define SS_HOME_MAX 117u
struct ss_choices_t {
 char home[128],dos[3][128],existing[128];
 br_u8 profile,existing_present;
};
/* Readonly observation in UIBSS: valid only while the UI phase is resident.
 * Copy/validate into a permanent REU capsule BEFORE retiring UI or calling FAT.
 * Source paths are selections, not geometry/CRC/file identity validation. */
extern const struct ss_choices_t * const ss_choices;
extern br_u8 ss_error,ss_stage;
/* Called with SO_UI ticket active, initialized platform and sole same-engine
 * directory lease authority, both firmware file contexts knownclosed.
 * owner=A5, timeout1..7fff; begin once per UI residency. No writes/OPEN here.
 * Poll scans actual CIA input/elapsed clock, including while directory busy.
 * Private return state is authority; public observations cannot grant DONE. */
br_u8 ss_begin(br_u8 owner,br_u16 timeout);
br_u8 ss_poll(void);
/* Private state getter; callable only under a proved current UI ticket. */
br_u8 ss_state(void);
br_u8 ss_error_code(void); /* private first cause, UI-only */
void ss_cancel(void);
#endif
