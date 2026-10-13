#ifndef READYFS_CONSOLE_H
#define READYFS_CONSOLE_H

/* Continuous physical-row transcript, independent of the editor and overlays.
 * 800 rows with original screen codes and colors in a dedicated REU bank. */
/* Semantic output markers. The console consumes these without drawing a cell.
 * Explicit CR returns summary/error output to white; soft wrapping keeps color. */
#define RF_SUMMARY "\236"
#define RF_ERROR "\034"
#define RF_NORMAL "\005"

#define RF_CONSOLE_ROWS 800u
#define RF_CONSOLE_ROW_BYTES 80u
#define RF_CONSOLE_LOG_BYTES 64000u
#define RF_UI_LIVE_SCREEN_OFF 0x7100u
#define RF_UI_LIVE_COLOR_OFF  0x7500u
#define RF_UI_DRAFT_OFF       0x7900u
#define RF_UI_CACHE_OFF       0x6100u
extern unsigned char readyfs_console_recording;
extern unsigned char readyfs_reu_console_bank_value;
extern unsigned int readyfs_console_head;
extern unsigned int readyfs_console_used;
void readyfs_console_scroll(void);
unsigned char readyfs_reu_console_fetch(unsigned int offset, void *data,
                                        unsigned int length);
#endif
