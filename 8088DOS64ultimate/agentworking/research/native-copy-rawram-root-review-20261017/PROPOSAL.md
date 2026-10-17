# Native observed mapping receipt proposal (not implemented)

The sealed physical attempt36c055fc failed as intended at the old observer. Its initial full4MiB equals ac43, but the directory raw snapshot begins0001. No COPY/reader was started. Profile restoration and whole inventory equality passed; terminal RAM retained; BASIC/quiet not admitted and no reset/replacement followed. Preserve the original failure and reserved ACTIVEb28b.

Pinned official v3.14 source evidence:

- work/sources/route_machine.cc:164–205, GET machine:readmem creates C64_DMA_RAW_READ and returns that raw buffer. Upstream: https://github.com/GideonZ/1541ultimate/blob/v3.14/software/api/route_machine.cc
- work/sources/c64_subsys.cc:407–412 dispatches RAW_READ to dma_load_raw_buffer(...,1); lines524–549 copy from C64_MEMORY_BASE+offset. It is not a 6510 load instruction. Upstream: https://github.com/GideonZ/1541ultimate/blob/v3.14/software/io/c64/c64_subsys.cc
- Both frozen entry.s files call _ps_guard/runtime_init/native_entry and JMP fixture_return forever. There is no return-time port restoration. Both platform.s guards write DDR2F, prepare/mask/ack NMI, then write port35. This supports the intended native mapping contract; it does not make raw RAM0/1 a physical processor-port observation.
- The model bridge currently mirrors CPU-port writes into ram[0:2] (work/*/tests/floppy_export/bridge.cpp:112–127). Its raw copy_model_ram at511 copies ram directly; dos64_peek returns the separate processor-port registers at103–104. The mirror masked the host-observer mismatch in previous tests.

Two actual Peddle controls use unchanged native9901/9ab9 and unchanged accepted model libraries. Directory runs true owner_prelude_entry and14 native commands through exact known-close receipt. Reader runs fixed COPY and first64 native READs to one exact32KiB frame (73 commands total). Both are accepted by their original Source observer before the counter. A model-only direct raw-RAM write then changes only RAM shadow0/1 to0001, leaving native program, result, CPU port2F/F5 and all other bytes unchanged. Both old observers reject. There are zero REU DMA bytes and zero device calls. This is an observer/transport contract counterexample, not new20MiB or hardware acceptance.

First counter fixture assertions incorrectly expected literal35 in effective/readback upper bits. Those failures and both script versions are retained. Corrected assertions compare only the specified low mapping bits and preserve actual full values2F/F5. No native code/model library changed.

Minimal proposed fresh successor:

1. Default-OFF numeric native observation profile; undefined/0 must preserve old9901/9ab9 bytes. No filesystem/DMA/position/ACK/CLOSE changes.
2. A common 8-byte private BSS receipt, exported only for the source-bound observer: NMP1, CPU-read DDR, CPU-read processor port, bytewise complements. Native ASM invalidates the magic first, performs real LDA$00/LDA$01, writes observations/complements/version, and publishes magic byte0 last. It validates (DDR&7)==7 and (port&7)==5, accepting effective upper bits. It must not attempt to repair mapping.
3. Capture/check before each successful ready-header publication and terminal result. A mapping failure latches a distinct first error without overwriting an earlier error, marks truthful failed/unknown state and issues no new I/O or repeated CLOSE. Source verifies the exact new helper bytes/symbol, private ready receipt and its low bits; raw RAM0/1 becomes diagnostic only. This changes evidence location rather than deleting the mapping requirement.
4. Keep every existing native code/SMC/NMI/Cstack/private phase/position/error/knownhandle/quiet/CWD/nonce/headerCRC/content guard. Both DirectorySource and ReaderSource must use this same native observation contract; no permission to admit the old physical bytes as the new successor.
5. Minimal tests: source-built default0 byte identity; actual native directory success and reader first frame with independent raw shadow0001; both native wrong-DDR/wrong-bank observations refuse before publication; missing/torn/stale receipt, complemented-value corruption and immutable-source changes refuse; known quiet/unknown normal CLOSE/error-first chronology remain unchanged. Test fixture must keep CPU port storage independent from raw RAM shadows for this profile. No long unchanged20MiB model replay: final physical full20MiB verification remains mandatory on new binary.

This proposal does not authorize native/source mutation or any hardware dispatch. ROOT must agree the exact successor contract and review a fresh purpose/ACTIVE binding before another device action.
