#ifndef DOS64_INCOMING_STAGE_H
#define DOS64_INCOMING_STAGE_H
typedef unsigned char iw_u8;
typedef unsigned short iw_u16;
/* Native caller owns modal broker8/cache0 and an actual outstanding PREPARE.
 * Begin captures canonical zero-padded path and the actual native FQ27 facts,
 * validates them against private core lease, then borrows only alternate FILES.
 * This worker never initializes transport, COMMITs or CANCELs the core token.
 */
extern char iw_path[128];
extern iw_u16 iw_limit; /* nonzero elapsed16 bound<32768, captured */
extern iw_u8 iw_enable,iw_cancel; /* enableA5; cancel cooperative afterbegin */
iw_u8 iw_begin(void);
void iw_poll(void);
iw_u8 iw_state(void); /*0idle1busy2done3failed*/
iw_u8 iw_error(void); /* first cause, immutable throughout a job */
iw_u8 iw_closed(void); /* original native C context safely restored */
struct iw_receipt {iw_u8 drive,flags,base[3],token[4],mount[4],content[4],crc[4];char path[128];};
/* Returns native pointer to private149B receipt at most once, or NULL.
 * Copy while worker is loaded, afterallframesreturnbeforeoverlayretirement.
 * A legitimate CRC0 is represented by successful private admission, never by
 * testing CRC!=0. Neither public getters nor a request copy grants authority.
 * Futurecontroller must CANCEL oldtoken and PREPARE samefreebase/unchanged
 * generations withderivedCRC before durablecommit; not performed here.
 */
const struct iw_receipt* iw_take(void);
#endif
