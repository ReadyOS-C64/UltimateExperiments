.ifndef DOS64_VIDEO_INC
DOS64_VIDEO_INC = 1
; Original PC/XT CGA logical video BIOS. The ROM gate is owned by bios.s.
; dos64_video_service consumes guest AH and preserves guest FLAGS. It returns
; native C clear if handled; C set with dos64_video_host_error=0 unsupported,
; or =1 terminal coherent-memory/cache failure. Native P except C preserved;
; A/X/Y and address/value/segment scratch clobbered. Synchronous/nonreentrant.
;
; Supported: AH00 modes0..6 (16KiB deterministic clear); AH01/02/03 cursor;
; AH05 page; AH06/07 bounded text scroll; AH08/09/0A text cell operations;
; AH0B CGA background/intensity/palette; AH0C/0D CGA pixel with bit7 XOR; AH0E text tty on mutable BDA active page;
; AH0F raw mutable BDA query. AH09/0A preserve cursor and wrap B800:DI as a
; 16-bit guest offset; stores outside B8000..BBFFF follow the PC bus policy.
; Cursor/page/window/pixel arguments outside supported geometry are rejected.
; Mode7/EGA preserve-clear bit, AH04, graphics glyph services unsupported.
; AH10..FF are original-XT ignored functions: all guest registers/FLAGS and
; memory unchanged; this does not implement EGA/VGA services.
; No font, host renderer, retrace fidelity, sound, or device port emulation.
;
; Contract facts consulted, no BIOS implementation code copied:
; Microsoft MS-DOS Encyclopedia Appendix O (INT10 service register contracts)
; https://msarchive.pcjs.org/mspl13/msdos/encyclopedia/appendix-o/
; IBM 5160 XTBIOS listing (11/08/82): mode defaults, tty active page and
; scroll-fill attribute, 16-bit repeat offsets; archive index:
; https://www.pcjs.org/software/pcx86/dev/rom/ibm/5160/
; RBIL AH0C (XOR bit7; single-page BH ignored):
; https://www.delorie.com/djgpp/doc/rbinter/id/09/1.html
BIOS_VIDEO_PORT = $F3
BIOS_VIDEO_OFFSET = $0150
VIDEO_ROWS = 25
VIDEO_VRAM_SIZE = $4000
.endif
