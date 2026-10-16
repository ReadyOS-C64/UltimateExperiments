#ifndef DOS64_SETUP_PLATFORM_H
#define DOS64_SETUP_PLATFORM_H
/* Standalone SETUP/START platform, not main-emulator policy. cc65 C ABI.
 * Caller supplies valid hardware/software stacks, writable C/ZP RAM and no
 * concurrent device access. init masks IRQ/CIA NMIs and installs our private
 * RTI before exposing RAM at $01=$35; ownership lasts until explicit handoff.
 * No KERNAL calls. CIA1 matrix and CIA2 TA/TB plus VIC are exclusively owned.
 * Future START payload NMI5882 is distinct; no final handoff implemented here.
 */
typedef unsigned char ps_u8;
typedef unsigned int ps_u16;
#define PS_UP 0x80
#define PS_DOWN 0x81
#define PS_LEFT 0x82
#define PS_RIGHT 0x83
#define PS_HOME 0x84
#define PS_DELETE 0x85
#define PS_F1 0x90 /* through F8=97, physical F7 +shift=F8 */
extern ps_u8 ps_row,ps_col,ps_color,ps_ascii;
extern ps_u8 ps_key,ps_modifiers,ps_ghost,ps_clock_valid;
extern ps_u16 ps_ticks;
void ps_init(void); /* startup-only, screen clear, ownership and clock start */
ps_u8 ps_put(void); /*1 writes one bounded40x25 screen/color cell,0 refuses */
void ps_clear(void); /* all1000 cells, currentcolor low4 */
ps_u8 ps_glyph(ps_u8 ascii); /* C64 mixed-case ROM glyph mapping/transliteration */
ps_u8 ps_key_poll(void); /*1 fresh edge in ps_key,0 none; no key repeat/queue */
ps_u8 ps_clock_poll(void); /*1 coherent16bitelapsed sample in ps_ticks,0 stale */
/* One tick=1024 CIA PHI2 clocks, approximately1ms, not PAL/NTSC calibrated.
 * TA continuous1023 reload; TB counts TA underflows. Bounded H/L/H retries.
 * Ticks wrap65536; durations<=32767 and polling before half-wrap required.
 * Clock advances independently of CPU stalls; no CIA phase/ICR samples on reads.
 */
#endif
