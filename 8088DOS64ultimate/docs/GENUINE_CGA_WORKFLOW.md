# Genuine DOS CGA application gate

`CGAPROBE.COM` is an independently authored 127-byte original-8088 program. Genuine DOS 3.3 reads its FAT12 directory/cluster and loads it through COMMAND.COM. There is no native COM loader or replacement INT21. This is an application probe, separate from the accepted DOS builtins.

The program selects BIOS modes 4, 5, then 6. Each fills all 16 KiB at B800:0000 with a deterministic pattern, writes a mode-specific ready marker in the unused tail, then blocks in BIOS INT16/AH00. Only after a coherent complete snapshot and comparison does the harness send Enter. After mode6 it selects mode3, prints a completion line with ordinary DOS AH09, and terminates with DOS AH4C. The shell must return A> with the complete 80-column text bitmap matching the font oracle.

The fixture builder accepts only the pinned original disk1. It adds CGAPROBE.COM to one free root entry/cluster in a new disposable image, updates both FAT12 mirrors, preserves the boot sector and verifies every existing file through the separate read-only volume inspector. It never patches CONFIG.SYS or AUTOEXEC. Existing output products are rejected. The three supplied reference images remain immutable.

## Running the optional gate

After adding the package files and the integration snippet, run:

```sh
make build
python3 build_support/dos_cga_fixture.py --source 'reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img' --output build/cga-fixture.img
../../zeropage-tooling/bin/zig build native-cga-workflow --summary all
python3 build_support/dos_cga_oracle.py build
python3 -m unittest discover -s tests/tooling -p test_dos_cga_fixture.py -v
```

The fixture, COM and JSON outputs must be absent before fixture creation; preserve an old run before removing its derived build files. The genuine DOS gate is opt-in, with no dependency from default tests. NASM is an optional fixture tool, not the native target compiler. The native emulator remains ca65/ld65 assembly.

The target runs through native ENTRY, cold UCI import, actual REU DMA/cache, BIOS boot, real DOS and native RUN/KEY/SNAPSHOT/READ commands in Peddle. File/FPGA/CIA/input/VIC models are explicitly simulated. Functional CIA time advances from native CPU cost at64:1, excluding DMA/VIC stalls. There are no direct CPU step calls or writes of guest application code after import.

## Independent output oracle

Each ready checkpoint retains complete BDA256, CGA16384, host RAM65536, bitmap8000, matrix1000 and color RAM1000. The oracle first decodes all source pixels, then applies the project policy: 320-wide modes choose the left nonzero foreground index, otherwise the right; 640-wide monochrome ORs each source pair. Every possible two-pixel combination occurs. The mode5 RGBI cyan/red/white policy and mapped VIC colors are explicit; mode4 uses cyan/magenta/white at the default BIOS palette. Mode6 color RAM is unused and unconstrained. Full bitmap/matrix/color bytes are checked, together with BDA geometry and every source VRAM byte. The reusable oracle requires the complete BDA page-size word at4Ch to equal4000h, the complete display-offset word at4Eh to equalzero, active page62h to equalzero, and color-register shadow66h to equal30h in modes4/5 or3Fh in mode6. These are the unchanged original-XT-mode defaults established by the native video mode service and separately asserted by the actual guest workflow; different mutable palette/page settings are rejected by this fixed probe contract. Normal host regressions reject changes to either byte of each word and the palette byte in allthree modes.

Each host capture also compares BASIC/CODE/RODATA/DEVICE and all3584 copied F000–FDFF bytes to the immutable packaged PRG. Only the four documented UCI pointer-operand bytes may differ, after validating their opcode and buffer range. The shadow A5 guard, zero tail and all3072 font bytes must match. This is model identity, not physical bank evidence.

Microsoft's [BIOS contract](https://msarchive.pcjs.org/mspl13/msdos/encyclopedia/appendix-o/) describes mode selection and BIOS services. The [IBM XT BIOS source archive](https://www.pcjs.org/software/pcx86/dev/rom/ibm/5160/) supplies the original mode/default context. IBM’s [Color/Graphics Monitor Adapter manual](https://minuszerodegrees.net/oa/OA%20-%20IBM%20Color%20Graphics%20Monitor%20Adapter%20(CGA).pdf), printed pages10–11, specifies the two visible8000-byte banks and pixel formats. The original XT native-mode defaults are source-bound to `src/video.s` and `include/video.inc`; those emulator sources and the actual Zig assertions are pinned with this cohort. The display reduction is our stated C64 compatibility policy, not original CGA fidelity. No BIOS implementation code is copied.

## Physical handoff boundary

A physical runner must use a fresh owned staged fixture and runtime pair, verify the actual unit proof/source/font identities, snapshot all4MiB before launch, retain full checkpoint RAM/BDA/CGA/bitmap/matrix/color bytes, and restore/compare all4MiB plus prior configuration/media. It must gate each Enter on the corresponding ready marker, full frame and stable BIOS wait. It must not use the text-only MODE observer on graphics frames. The host workflow currently proves Peddle only; a dedicated reviewed physical observer is still needed. Root retains hardware ownership.

RAM proofs do not establish external VIC/HDMI appearance, readable pixels, artifact colors, raster effects, native matrix input, native file persistence or near-XT performance. DOSBox-X comparison was not run for this cohort. Direct CGA ports, palette AH0B and graphics glyph BIOS calls remain outside this probe.
