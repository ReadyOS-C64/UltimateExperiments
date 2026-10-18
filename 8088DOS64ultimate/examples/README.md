# RIPPLE

`RIPPLE.PAS` is an original-8088 Turbo Pascal picture for DOS64. It selects BIOS
mode 1 (40-column, 16-colour text), draws 960 full-block characters in eight
selected colours, and waits for a key before restoring 80-column text mode.
It uses only the standard System/Dos units, integer arithmetic, BIOS calls and
the PC text buffer. `{$G-}` keeps code generation compatible with the 8088.

Each 40-column character has its own 8×8 C64 bitmap cell and colour pair. This
avoids the shared colour pair required by two adjacent 80-column characters.
The palette is blue, purple, red, light red, yellow, white, cyan and light
blue after DOS64's existing RGBI-to-C64 conversion. It is text art, rather than
a claim of 16-colour CGA graphics support.

Open `RIPPLE.PAS` in Turbo Pascal, select Compile → Destination → Disk, and
compile with Alt-F9. Run `RIPPLE.EXE` from DOS. Drawing is deliberately static;
the completion caption appears only after the last block has been written.

`build_support/ripple_picture_check.py` checks every captured guest character and
attribute. The existing `physical_gallery.py` separately checks the native C64
bitmap/matrix and the actual VIC stream pixels. Physical results and screenshot
paths are recorded in the project-local working records.

The physical Turbo7.01 Disk compile and DOS EXE run passed on2026-10-17.
[Original editor, compiler and finished-picture screenshots](../docs/screenshots/physical-ripple-20261017/README.md)
include exact PNG hashes and verification scope.
