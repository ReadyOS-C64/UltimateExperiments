# C77 dual-bank character ROM — clean VICE captures

These 21 screens were recaptured from the full ReadyOS Precog D81 with fast
IEC traps.  VICE loaded `c77-photo-reconstruction-readyos-v3-chargen.bin` and
`C77CYBER.VPL` after its default resource reset.

The ROM installs the reconstructed A-Z/0-9 face into both C64 character-set
banks.  This is important because the loader uses bank 0 while ReadyOS and its
apps select bank 1.  Punctuation, symbols, PETSCII graphics, and all unrelated
glyphs are byte-for-byte stock.

- `00-complete-gallery-index.png`: all 21 screens
- `00_loader.png` through `20_readme.png`: 320x200 frame captures
- `3x/`: nearest-neighbour enlarged captures
- `contact-sheets/`: enlarged four-screen pages
- `vice-native/`: VICE's own 384x272 screenshots (launcher and apps)
