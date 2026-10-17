#ifndef MEDIA_PLAN_H
#define MEDIA_PLAN_H
/* Pure native planner, NOT a file/durability or CLEAN receipt. Source CFG must
 * already be independently read/closed and compared against accepted startup.
 * Actual save worker supplies frozen selection and verified output CRC. */
#define MP_OLD 0x3e0000UL
#define MP_NEW 0x3e0300UL
#define MP_JOURNAL 0x3e0600UL
#define MP_JOURNAL_BYTES 1284u
extern unsigned char mp_drive,mp_readonly,mp_cancel,mp_error;
extern unsigned int mp_sequence;
extern unsigned long mp_capacity,mp_image_crc;
extern unsigned char mp_image_path[128],mp_snapshot[42];
unsigned char mp_build(void);
unsigned char mp_journal_check(void);
unsigned char mp_state(void),mp_first_error(void);
/* Pure recovery classification after caller exact current CFG acquisition:
 * 1=old/precommit,2=new/needs image verification,3=missing/needs explicit
 * rollforward and OLD/NEW verification,0=conflict. No value grants boot. */
extern unsigned char mp_current_missing;
unsigned char mp_recovery_classify(void);
#endif
