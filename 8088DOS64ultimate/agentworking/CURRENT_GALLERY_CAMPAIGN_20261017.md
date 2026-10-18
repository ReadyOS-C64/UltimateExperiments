# Physical screenshot campaign — 2026-10-17

Root is the sole hardware owner. No more agents. The user wants screenshots inline in chat; representative DOS40/80, DIR|MORE, GW-BASIC, Turbo editor/save/compile/output and DOS executable captures have been posted. The new RIPPLE source/editor and completed colour picture have also been posted.

## Final hardware state

Terminal1688 completed with exit0/no watchdog; no host controller remains. The Ultimate is RUNNING on the completed40-column RIPPLE picture, waiting in BIOS for a key, with C backing file OPEN. A key restores80-column mode and returns to DOS. Manual64/PAL remains deliberate. Do not reset before actual native Finish or proven closure. Actual Turbo7.01 Disk compile and DOS EXE run passed; all18 editor source lines, all1000 guest cells and all6 frames' native RAM/VIC pixels are exact. All25 frozen inputs match and executed driver copies are archived. See [RIPPLE evidence](evidence/physical-ripple-root-20261017.json). No new close/cold-persistence test of RIPPLE was performed.

Preceding Terminal1685 passed exact cold START/runtime admission, persisted V1EDIT source and EXE in40columns, saved-source reopen in80-column Turbo and AltX return to DOS. Those frozen inputs and archived driver remain historical evidence.

## Verified results

- Core remains runtime1506210a / MNUa2; no emulator performance/code changes in this campaign.
- `c64u-physical-gallery-turbo-input-retained-20261017` captured the actual source, backspace0→1, save, Destination Disk and successful AltF9 compile. Its first output-screen observer failed because the shortcut was sent too early; keep that failure.
- `c64u-physical-gallery-turbo-output-settled-20261017` continued the same instance after a fresh full source/state check. A new state-dependent AltF5 request after confirmed editor return showed `DOS64 V1 EDIT 1`. Editor return, AltX, DOS TYPE of saved source, direct EXE execution with redirection and TYPE of output all passed. Exit0, no watchdog, seven real VIC captures.
- `c64u-gallery-turbo-native-close-persistence-20261017` called actual native FILES CLOSE once through the source-built316B development helper. Actual handle0/state2/UCI9/error0 and immutable helper were checked. Whole20MiB readback passes strict FAT, preserves all302 baseline payloads and contains exactly three new files. PAS66B SHAafbb15d2…, EXE2208B SHA41e615b1…, TXT17B SHA55a10db1… all exactly match the independent Peddle result. Known-closed reset and advancing BASIC passed. This is development cleanup, not native UI Finish acceptance.
- `c64u-gallery-verified-final-20261017/GALLERY.json` independently verifies46 actual DOS/BASIC/Turbo stream PNGs: full8000B bitmap/1000B matrix/source fonts/cursor oracle plus all64000 active VIC pixels. This includes all eight cold-restart frames. Thirteen selected unaltered stream images are exported with hashes in `docs/screenshots/physical-20261017`.

## Explicit runtime fixture scope

Home: `/usb1/DOS64_TEST/v1-gallery-runtime-20261017`. CFG and START are HOST-prepared from the exact canonical descriptor/template; A/B came from the previous actual native installation. Writable C adopts the owned disposable `/usb1/DOS64_TEST/v1-gallery-tp-clean-20261017/TURBOHD.IMG`. Its complete302-payload baseline is retained locally in `c64u-physical-gallery-runtime-turbo-admitted-20261017/C-baseline.IMG`; original360-payload source SHAac1cea54 and the Mac302 derivative remain unchanged. Runtime success does not supersede the failed native20MiB installer. Historical initial capture label “native-created-C” is misleading; manifests/results explicitly identify the host fixture.

## Installer and observer failures retained

1674 imported all360 original payloads but hit the deliberate DOS/DISK1..3 archive-collision policy (NF_NAME4); last-operation OPEN was misleading.1675 verified fresh source/private closure.1676 staged a separate302-payload derivative omitting only58 archives independently identical to the supplied floppies.1677 then failed native C WRITE_NEW with SI phase3/UCI03 after65536 bytes produced.1678 captured actual private closed state. Partial outputs remain in their owned folders. Cause is unestablished; fresh-clock handling after complex producer callbacks is a hypothesis requiring reproduction. Pinned firmware has separate Dos objects for targets1/2; do not assert a shared-handle cause.

1680 host fixture boot/VER/Turbo editor passed, but a30s input observer failed after14 accepted characters `program V1Edit` (last word1474, no semicolon).1681's bad PAUSED-only guard failed read-only because actual native state was RUN4.1682 admitted actual RUN4 or PAUSED5, checked the last accepted word, captured the intact prefix, never retyped it, and completed the source with explicit input300s/poll500 waits. Default harness input30s/poll100 behavior is unchanged.1683 retrieved the completed program's user screen as a new UI action, not a missing-ACK retry. See TEST_LOG for exact failure paths and archive limitations.

## Continuity and remaining V1 scope

Own main commit2120a19 and upstream harness0f8c388/3846727 are local only. Preserve unrelated dirty ReadyFS/root and upstream client/Binary/README work. Current post-reboot lower4MiB baseline is6e7c4fae, persisted on the Ultimate; never restore historicalac43 over it. Manual64 is intentional; no original CPU/RAM/application or finalREU restoration is claimed. Native20MiB installer repair, CONFIG/media/Finish and human keyboard/display acceptance remain open. Defer performance and compiled activation. Every hardware call stays in a detached fresh Terminal worker with devnull, owned logs/PIDs and finite bounds.
