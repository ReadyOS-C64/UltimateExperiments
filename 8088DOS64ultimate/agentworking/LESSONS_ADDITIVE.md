# Additive lessons log

## 2026-10-14 — planning inspection

1. User clarified target language to 6502 assembly and separately reinforced Zig behavior assertions. This supersedes the planning-stage C/ZeroPage possibilities before any target code was written.
2. Three images are all 360 KiB FAT12. Disk 1 and disk 3 have matching system-file hashes but different config/boot metadata. OEM text does not establish runtime DOS version.
3. Disk 1 refers to a non-existent initial C: installation; plan original-behavior and minimal-config boot lanes separately. Never edit the original to conceal a fixture dependency.
4. Existing Peddle shims provide a useful starting point but not a complete REU/banking/timing model. ReuSQL64 wraps REU addresses by capacity; ZeroPage truncates. Neither behavior can be generalized without device evidence.
5. Ultimate prose docs and inspected upstream code differ on REU transfer length masking. Actual transferred count and installed firmware must govern correctness.
6. A complete bitmap layout must satisfy VIC bank relationships and alignment, not just fit 64 KiB. The proposal places matrix 4000 and bitmap 6000 in bank 4000–7FFF.
7. Parent .gitignore ignores working-record directories recursively. Project-local override is necessary if these planning/continuation records are to be tracked, while scratch/runs stay ignored.
8. DOSBox-X was already installed. Version detection was performed; no guest run or emulator benchmark occurred in planning.
9. D81 SEQ roundtrip was verified using c1541. Its directory output can contain PETSCII bytes and must not be assumed UTF-8; this initially broke the research wrapper, not the container bytes.

## 2026-10-14 — M0 implementation

1. The first runaway fixture hung because Peddle `executeInstruction()` leaves `clock` advancement to the embedding application. Stopped that specific test process, changed the bridge to bounded per-microcycle stepping with explicit increments, and added an exact 8-cycle LDA/RTS assertion. All 10 Zig tests then passed.
2. DOSBox-X works with SDL dummy video/audio for automated reference boot. Copy AUTOEXEC into the disposable image before BOOT, then capture guest-written VER/DIR/DONE from the FAT12 image. The original config remained and the guest reported MS-DOS 3.30.
3. DOSBox-X did not exit promptly on SIGTERM in this run; the wrapper killed only its own process after a bounded wait. The captured files were already closed and verified; this is a functional boot baseline, not clean-shutdown evidence.
