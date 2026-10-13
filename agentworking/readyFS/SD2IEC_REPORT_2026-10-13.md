# ReadyFS SD2IEC implementation and acceptance report

**Status: acceptance is still in progress.** This is the current report, not a completion claim. The remaining physical checks are the corrected recursive round trip and explicit native disk-image operations.

## What is implemented

ReadyFS now detects an SD2IEC through its native IEC DOS identity, resolves its current or explicitly named partition, and prepares file operations for either hierarchical storage or a flat mounted image. No ReadyFS runtime networking, REST service, or Mac relay is involved.

The command surface includes native status/version queries, initialization and reset, expert raw DOS commands, SD2IEC configuration inspection, partition inspection/selection, extension and image-listing settings, wildcard mode, address changes, and explicit EEPROM persistence. See [the native guide](../../ReadyFS/docs/SD2IEC_NATIVE.md) for syntax and worked examples.

The normal ReadyFS operations now use this service: DIR, TREE, VOLUME, file COPY/COMPARE/MOVE, RENAME, DELETE, MKDIR/RMDIR, aliases, and recursive plans. Native exact-name operations reject wildcard and DOS-separator injection; SEQ, PRG, and USR are byte streams, while REL remains unsupported.

## Actual device repair

The external SD2IEC was answering at device 8 despite the intended address 10. The repair temporarily disabled Ultimate A to avoid the collision, sent the binary native address command, persisted it with XW, and verified device 10 after a native processor hard restart. Ultimate A was restored to its original enabled 1581 configuration and `/USB1/readyos.d81` image.

Detected identity: `73,SD2IEC V1.0.0ATENTDEAD0-36,00,00`. Persistence has been demonstrated across that hard restart; an electrical power-cycle test has not been claimed.

## Verified physical results so far

| Area | Evidence | Result |
| --- | --- | --- |
| General/native configuration CLI, partition replies, temporary setting changes and exact restoration | `demo-v3-sd2iec-config-focused-20261013-c` | Passed; read checks at 1, 16, 64 MHz |
| Existing UltimateDOS, mounted IEC-image, SoftwareIEC COPY/MOVE baseline with SD2IEC attached | Repeated retained matrix runs | Passed |
| Unique native SD test root, exact ownership marker, 1,025-byte binary seed | `sd2iec-native-owned-bootstrap-20261013-c` | Passed readback |
| Four-endpoint directed COPY/COMPARE matrix | `demo-v3-sd2iec-native-four-endpoints-20261013-a` | All 12 directed pairs passed |
| Four-endpoint directed MOVE/COMPARE matrix and source removal | Same run | All 12 directed pairs passed |
| Independent byte/type oracle | Same run | Host hashes, SD re-export hashes, persisted IEC-image extraction passed |
| Automatic DIR without a preceding manual PROBE; TREE; SD/U/IEC9 VOLUME | Native directories-b | Passed |
| SD folder creation, same-SD copy, rename, scratch, empty-folder removal | Native directories-b | Passed |
| Recursive host→SD COPY; same-SD recursive MOVE; five nested-file comparisons | Native directories-b | Passed |
| Recursive SD→host export | Native directories-b | Found empty-Ultimate-folder lookup bug; corrected, physical rerun pending |
| Mounted SD disk-image operations and persisted-image oracle | Native image-a | Running |

Endpoint matrix notation in the machine-readable evidence is `u` = UltimateDOS host storage, `i` = separately mounted IEC9 image, `s` = SoftwareIEC, `d` = native SD FAT. This does not imply that every possible drive model or partition type has been exercised.

## Architecture and memory

There are now 20 REU-cached sidecars. Cold stream policy and VOLUME run in slot 16; IEC configuration policy in 17; native configuration/media I/O in 18; native file I/O and preparation in 19; pure native filename/directory policy in 20. Requests and DOS replies have separate bounded resident buffers. Overlay CODE, RODATA, and BSS segments are distinct, preventing compiler-emitted constants from being executed as instructions.

The latest full build passes at resident end `$B29D`, leaving **782 safe bytes** before KERNAL scratch at `$B5AC`. The pre-work end was `$B5A4`, leaving seven safe bytes: **775 bytes recovered** despite the added features. The monolithic build remains within its existing limit, ending `$C5F7`. ReadyOS integration has not started.

A measured hot checksum loop was replaced inside the existing tape/core overlay
with equivalent 6502 code. Actual built-code differential tests pass 46 cases
against an independent CRC implementation. The same 32-byte sample costs 9,505
CPU cycles instead of 52,570 (**5.53× faster for this checksum sample**), with 18
additional resident bytes recovered. This is not an end-to-end transfer-speed
claim: IEC and overlay overhead remain. The frozen old build’s 174,848-byte image
COPY passed in about 28 minutes at 1 MHz, including its verification; the optimized
build still needs physical acceptance.

## Bugs and firmware details resolved

1. Native `OPEN` and `CLOSE` now check KERNAL and DOS completion. A failed open cannot masquerade as an empty successful file, and a failed close cannot become a successful commit.
2. Native status reads TALK the existing DOS channel. Opening and closing channel 15 would discard SD2IEC data buffers, including the other side of a same-device copy.
3. Qualified SD directory requests need `:*`: `$1//folder/:*`. Omitting the colon treats text as a pattern; supplying an empty pattern matches no files. Earlier misleading missing-directory probes are retained and superseded.
4. SD2IEC RMDIR rejects slash paths. ReadyFS changes to the qualified parent and sends a leaf-only RD. CD succeeds with 00, but successful RD returns **01 FILES SCRATCHED**. The implementation now distinguishes them and shows actual DOS failures.
5. Staging names use `rftHH`. A tilde is invalid in SD2IEC's FAT conversion and could force an X00 wrapper even under extension mode0.
6. Ultimate OPEN_DIR returns **01 DIRECTORY EMPTY** for a valid empty folder. This is now authoritative absence for file lookup and successful empty enumeration. READ_DIR is skipped in that case; unrelated failures remain errors.
7. Earlier baseline work corrected SoftwareIEC MOVE cleanup's parent handling and protected reserved REU banks plus exact EOF handling in the spool controller.

## Boundaries and limitations

- Native `10.1:/folder/file` and Ultimate `u:/usb1/image.d81/file` are different path services. An alias does not change endpoint capabilities.
- Explicit native MOUNT/DISMOUNT changes the SD2IEC filesystem view. Automatic `10.1:/image.d64!/FILE` transitions are not implemented.
- A transfer between SD FAT and an image mounted on that same SD device requires an intermediate endpoint and explicit media transitions. Mounting/unmounting can close device-wide buffers; it cannot occur inside the ordinary simultaneous stream pump.
- `G-P` type 1 identifies either FAT or DNP, not which one. It does not recover an unknown prior mounted-image path or current directory. Remembered mount paths are session hints and may become stale after changes elsewhere.
- Native path components are limited to 16 bytes in this implementation. Same-parent native rename is supported; cross-parent movement uses verified copy then cleanup.
- SD extension modes can wrap logical files in X00 containers. A logical COMPARE does not prove raw disk-image mountability. The documented raw-image procedure temporarily selects XE0 and restores the exact previous mode/hiding flag; automatic image creation across every extension mode is not claimed.
- Changing image-listing mode to dirs/both can present an image as a directory. On the exact tested firmware, intermediate image path components are rejected; recursive planning stops before execution when it reaches such a presented directory. It does not silently skip or mount it. Use `images files` explicitly to process containers as files.
- Native directory removal may leave the SD partition's current directory at the removed child's parent. An unknown previous native view cannot be restored by guessing.
- Hardware acceptance covers the attached SD2IEC and C64U endpoints. It does not establish compatibility with physical CMD hardware, Pi1541, tape hardware, every SD firmware, multiple SD partitions, or DNP media.

## Safety and retained evidence

Mutations use newly created owned test roots. Native ownership is reread exactly before subsequent native mutations; host/image mutations use the matching canonical root and marker. Original user files and mounted original images are preserved. Test roots, failed runs, and diagnostic evidence are retained.

External Terminal-owned REST/FTP automation installs and observes the test program; it is not part of ReadyFS runtime. Physical jobs are serialized. Tests restore CPU speed, Ultimate drive settings/images, and SoftwareIEC configuration where touched. Exact restoration outcomes are recorded per run; the active image run must finish before its restoration can be claimed.

The authoritative chronological notes are [the work log](SD2IEC_2026-10-12.md). The compact acceptance snapshot is [JSON evidence](SD2IEC_ACCEPTANCE_2026-10-13.json). Physical logs live below `ReadyFS/logs/readyfs_c64u/`.

## Research used

- Exact firmware source: <https://www.sd2iec.de/nightlies/sd2iec-1.0.0atentdead0-36-g7e7be29.tar.gz>
- C64OS SD2IEC reference: <https://c64os.com/post/sd2iecdocumentation>
- C64OS file-manager concepts: <https://c64os.com/c64os/usersguide/filemanager>
- Local sibling C64OS artifacts and Ultimate firmware source were inspected to distinguish filesystem capabilities, binary protocol behavior, and actual implementation details from assumptions.
