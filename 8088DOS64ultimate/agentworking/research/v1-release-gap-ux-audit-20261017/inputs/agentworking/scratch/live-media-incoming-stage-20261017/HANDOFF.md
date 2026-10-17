# Incoming floppy image staging component

PASS for the private actual-runtime component. No Insert UI, durable CFG mutation, COMMIT/CANCEL, cold START, or device acceptance is claimed.

The worker is `worker/incoming.s`, with typed ABI in `worker/incoming.h`. `build_incoming.py` regenerates imports from the exact selected runtime and broker labels. The source graph is sealed runtime S+Finish5b54 plus ONLY `work/src/floppy_control.s` and `work/include/disk.inc` from Root e0dc. The newer c866 cold/control composition is not imported; regenerate role imports when composing it. No production files were edited.

## Execution and closure

Fresh source-native/model builds, followed by 2 positive and 22 fault groups, passed. `closed-incoming/NATIVE_RESULT.json` records 1415 source/tool/SDK inputs and 47 products, with original and staged copies exact before/after. UNIT build products were moved to `closed-incoming/excluded-UNIT` before actual execution. The machine loads the runtime PRG and uses host return0300; it does not load a UNIT binary or UNIT sidecar.

The subsequent default-control invocation failed because the expected-default fixture had not been copied (a relative-parent mistake in an earlier staging command). This occurred AFTER all24 native groups passed. It is preserved, including failed exit1; it is not a native failure. `closed-default-followup/RESULT.json` separately closes1420 inputs/copies, verifies all1415 original native inputs and all47 native products still exact, and records fresh old/undefined/explicit0 default builds all equal666089b5. No native tests or SUT were changed for that followup.

Final products:
- runtime PRG: `2de3934f5414db11da683ef8c6209f900b5c972b6f4062c059f91b964c037f58`,47105B.
- worker PRG: `43efb759166bcf3788c6b9a9557055601f40b9832907f26185fc91724583b47d`,2796B including load address;2794B payload.
- CODE A000..AA9F, RODATA AAA0..AAE9;3350B remaining before B800.
- private/public phase BSS7D00..7E5A,347B;37B before7E80 saved-high96.
- dual FETCH buffersB800..B8FF andB900..B9FF. No new zero page, C software stack, CRC table, permanent native RAM, or REU allocation.

## Admission and lifetime

The exclusive caller owns modal stage8/cache0 and an actual outstanding native PREPARE. Caller loads the worker, zeros its347B BSS, supplies a canonical absolute zero-padded128B path, captured nonzero elapsed16 limit<32768, and enableA5. `iw_begin` returns1 only after source-bound private broker/core admission, or0 without authority. The FQ27 must still hold the actual PREPARE result. Worker independently compares its drive, policy, token, free arena and captured/current mount/content generations with native private stage state; it rejects mounted arenas, configured REU<4MiB, invalid capacity, aliases, and invalid paths.

The worker is single-job per phase initialization; do not zero/reload it while active or while its receipt pointer is in use. Every API body preserves caller flags and native scratch20..43 using the hardware stack; it does not use or write high96. The8 explicit P patterns include decimal and IRQ flag combinations. Original C FILES25/HD129/HDB47, its firmware file handle/position/contents, CPU port/CIA DDR/keyboard ports, both mounted images and every REU byte outside the free360KiB arena are checked in positive controls. These are observation comparisons, not a claim of a global CPU write-trap on every RAM address.

Borrowing uses the existing native engine on the other target; it does not initialize/reset FILES/UCI or the clock. One initial safety CLOSE establishes alternate-target ownership, accepting only terminal known00/84. The original C context is not closed and its cache is not changed.

## I/O and receipt

RO OPEN, exact-size INFO, bounded LOAD_REU21 length05A000 to the private PREPARE free base, full dual-poison FETCH/CRC32, EOF/CLOSE, second RO OPEN/INFO, independent READ04 full-byte compare against staged REU, exact EOF, final known CLOSE, then exact C-context restoration. The12 BPB fields are generated from this exact core COMMIT validator and checked before a verified receipt can exist. CRC0 is valid and tested with actual native bytes.

Pinned local firmware v3.14 `firmware-proof/dos.cc`254..290 decodes a requested LE32 length and calls `file->read(..., len, ...)`; LOAD_REU21 is bounded even if the file grows after INFO. `FIRMWARE_PROOF.json` binds the primary source. A growing-source control proves only05A000 bytes are touched, then EOF refuses the extra bytes. Dual differently initialized FETCH buffers detect suppressed/partial DMA; independent READ04 catches repeatable LOAD corruption. This does not assert protection against arbitrary coordinated corruption of every independent backend.

`iw_poll` is cooperative. `iw_state`1 busy/2 done/3 failed; `iw_error` preserves first cause:2 CLOCK,3 CANCEL/STOP,4 FILE/protocol,5 size/content,6 DMA,7 lease/ownership,8 poll exhaustion,9 geometry. `iw_closed` means original C was safely restored; it is not mount/Resume/restart authority. A failed begin need not mint a new error code. Unknown CLOSE or bounded-drain exhaustion retains closed0 and diagE1; no duplicate CLOSE is attempted. Known-closed content/cancel failures can retain diag8, but the outstanding core token still requires the caller's CANCEL before Resume.

The source-bound clock uses existing coherent published raw32 ticks and rejects gaps>=08000000, including the tested elapsed16 full-wrap alias. SAMPLE4 is bounded256; any failed job drains at most256 polls regardless of later clock recovery. Fresh elapsed samples precede UCI advancement so native transport timeout/posted leaf cause wins simultaneous STOP. Physical CIA scanning restores ports/DDR. Once closed/ready, late cancellation irreversibly withdraws the receipt without unnecessarily declaring safely restored C unknown.

`iw_take` returns an AX16 pointer to the private149B receipt once, or0; it revalidates actual broker/native lease, C context, fresh clock and STOP. Receipt: drive0, flags1, base[3]2, token[4]5, mount[4]9, content[4]13, CRC[4]17, path[128]21. Copy it while code/BSS remain loaded and after all worker frames return. Post-admission public FQ/path/limit/enable changes cannot retarget it. Public results do not substitute for this getter.

The original token remains active. Future controller must CANCEL that token, PREPARE again with derived CRC/policy, require SAME free base and unchanged old generations under its retained private receipt and broker lease, then undertake durable publication/COMMIT. This worker deliberately does none of those operations. Root owns that integration and asset packing.

## Replay

In a fresh same-layout source copy with source-only tools and all needed fixture sources:

    python3 -B build_ui_bridge.py --role runtime
    python3 -B build_incoming.py
    python3 -B build_model.py
    python3 -B test_incoming.py
    python3 -B test_incoming_faults.py

The two test processes assert actual executed counts and return nonzero on failure. They use synthetic valid360KiB images and modeled firmware, not redistributed DOS images. `close_incoming.py` is the retained historical runner: for a completely fresh replay also stage `default-expected` before invoking it; it intentionally refuses an existing `closed-incoming` directory. `check_incoming_defaults.py` needs fresh `default-controls` and copied expected fixture. Existing sealed directories must not be overwritten.
