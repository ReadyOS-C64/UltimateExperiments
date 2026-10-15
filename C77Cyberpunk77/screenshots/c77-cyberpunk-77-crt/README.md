# C77 dual-bank character ROM — VICE CRT-mode captures

This is a second full-D81 run of the same 21 ReadyOS states with VICE 3.10's
CRT emulation and double-scan enabled.

The exact run settings are recorded in `VICE-CRT-settings.txt`.  VICE's binary
automation framebuffer is captured before its display shader, so the 960x600
PNG previews reproduce the enabled horizontal blur and scanline presentation.
The unprocessed run frames remain in `framebuffer/`, and VICE's own bordered
frame captures are in `vice-native-framebuffer/`.

- `00-complete-crt-gallery-index.png`: all 21 CRT previews
- `00-combined-double-scan-font-proof.png`: six text-heavy screens at full
  preview resolution, preserving every double-scan line
- `00_loader.png` through `20_readme.png`: individual 960x600 CRT previews
- `contact-sheets/`: four-screen CRT pages
- `FONT-VERIFICATION.txt`: exact ROM-bank-1 glyph verification result
