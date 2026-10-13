#ifndef READYFS_REU_H
#define READYFS_REU_H

#define RF_REU_HISTORY_SLOTS 32u
#define RF_REU_HISTORY_BYTES 256u
#define RF_REU_BATCH_CACHE_OFF 0x0000u
#define RF_REU_BATCH_CACHE_BYTES 0x1000u
#define RF_REU_BATCH_DATA_OFF 0x1000u
#define RF_REU_BATCH_DATA_BYTES 0x4000u
#define RF_REU_BATCH_STATE_OFF 0x5000u
#define RF_REU_TAPE_CACHE_OFF  0x5100u
#define RF_REU_TAPE_CACHE_BYTES 0x1000u
#define RF_REU_MEDIA_OFF 0x9A00u
#define RF_REU_MEDIA_BYTES 0x1700u /* 23 session-only 256-byte paths: units 8..30. */
#define RF_REU_STREAM_CACHE_OFF 0xB100u
#define RF_REU_STREAM_CACHE_BYTES 0x1000u
#define RF_REU_IEC_CACHE_OFF 0xC100u
#define RF_REU_IEC_CACHE_BYTES 0x1000u
#define RF_REU_NATIVE_CACHE_OFF 0xD100u
#define RF_REU_NATIVE_CACHE_BYTES 0x1000u
#define RF_REU_BATCH_BANK_BYTES 0xE100u

extern unsigned char readyfs_reu_batch_bank_value;

/* Bank-local session allocation. Keep this map in one place: DMA regions
 * must never overlap even when a command temporarily uses rollback space. */
#define RF_REU_ALIAS_OFF          0x0000u
#define RF_REU_DRIVE_PROFILE_OFF  0x0888u
#define RF_REU_DRIVE_PROFILE_BYTES 0x005Cu
#define RF_REU_JOURNAL_OFF        0x0900u
#define RF_REU_JOURNAL_BYTES      0x1700u
#define RF_REU_SCROLL_OFF         0x2000u
#define RF_REU_SCROLL_PAGES       24u
#define RF_REU_SCROLL_BYTES       1000u
#define RF_REU_SCROLL_LIVE_OFF    0x7DC0u
#define RF_REU_ACTION_OFF         0x8200u
#define RF_REU_ACTION_BYTES       0x0200u
#define RF_REU_ACTION_REPORT_OFF  0x8300u
#define RF_REU_ACTION_REPORT_BYTES 8u
#define RF_REU_CONFIG_BACKUP_OFF  0x8400u
#define RF_REU_RECURSIVE_OFF      0x8E00u
#define RF_REU_RECURSIVE_BYTES    0x0100u
#define RF_REU_TREE_STATE_OFF     0x8F00u
#define RF_REU_TREE_STATE_BYTES   0x0100u
#define RF_REU_CONFIG_STAGE_OFF   0x9000u
#define RF_REU_RECURSIVE_ROOTS_OFF 0x9988u
#define RF_REU_RECURSIVE_ROOTS_BYTES 0x0200u
/* Overlay cache offsets are in a separate reserved REU bank. */
#define RF_REU_OVERLAY_MATCH_OFF   0x0000u
#define RF_REU_OVERLAY_MATCH_BYTES 0x1000u
#define RF_REU_OVERLAY_PLAN_OFF    0x1000u
#define RF_REU_OVERLAY_PLAN_BYTES  0x1000u
#define RF_REU_OVERLAY_HELP_OFF    0x2000u
#define RF_REU_OVERLAY_HELP_BYTES  0x1000u
#define RF_REU_OVERLAY_BACKEND_OFF   0x3000u
#define RF_REU_OVERLAY_BACKEND_BYTES 0x1000u
#define RF_REU_OVERLAY_CMDPATH_OFF    0x4000u
#define RF_REU_OVERLAY_CMDPATH_BYTES  0x1000u
#define RF_REU_OVERLAY_DRIVE_OFF      0x5000u
#define RF_REU_OVERLAY_DRIVE_BYTES    0x1000u
#define RF_REU_OVERLAY_UTILITY_OFF    0x6000u
#define RF_REU_OVERLAY_UTILITY_BYTES  0x1000u
#define RF_REU_OVERLAY_TREE_OFF       0x7000u
#define RF_REU_OVERLAY_TREE_BYTES     0x1000u
#define RF_REU_OVERLAY_CONTENT_OFF    0x8000u
#define RF_REU_OVERLAY_CONTENT_BYTES  0x1000u
#define RF_REU_TREE_QUEUE_OFF          0x9000u
#define RF_REU_TREE_QUEUE_BYTES        0x5FF0u
#define RF_REU_OVERLAY_RECURSIVE_OFF   0xF000u
#define RF_REU_OVERLAY_RECURSIVE_BYTES 0x1000u
/* Session-bank action plans use the remaining high region. */
#define RF_REU_PLAN_OFF           0xA000u
#define RF_REU_PLAN_BYTES         0x3FF0u

unsigned char readyfs_reu_init(void);
unsigned int readyfs_reu_bank_count(void);
void readyfs_reu_history_add(const char *line);
unsigned char readyfs_reu_history_get(unsigned char age, char *out);
unsigned char readyfs_reu_history_count(void);
unsigned char readyfs_reu_batch_store(unsigned int offset,
                                      const void *data,
                                      unsigned int length);
unsigned char readyfs_reu_batch_fetch(unsigned int offset,
                                      void *data,
                                      unsigned int length);
unsigned char readyfs_reu_session_store(unsigned int offset,
                                        const void *data,
                                        unsigned int length);
unsigned char readyfs_reu_session_fetch(unsigned int offset,
                                        void *data,
                                        unsigned int length);
unsigned char readyfs_reu_overlay_store(unsigned int offset,
                                        const void *data,
                                        unsigned int length);
unsigned char readyfs_reu_overlay_fetch(unsigned int offset,
                                        void *data,
                                        unsigned int length);

#endif
