# Risks and unanswered questions

| ID | Risk / unknown | Severity | Next resolution / fallback |
|---|---|---|---|
| K01 | Host instruction/translation cost prevents near-XT speed | High | M1/M3 handler+memory measurements; specialize hot paths; report achievable speed without changing real-DOS scope |
| K02 | REU misses dominate elapsed time | High | Measure DMA by size/direction, page-size sweep and actual DOS locality; smaller pages/prefetch only if data supports them |
| K03 | Resident code + metadata exceed host map | High | Map gate at every slice; static ABI; cold overlays; explicitly trade cache size, never silently overwrite memory |
| K04 | Real DOS boot/drivers need additional BIOS/ports | High | DOSBox/reference and target trace; implement bounded documented subset with tests; do not fake success |
| K05 | Incorrect mock makes unit tests misleading | High | Model conformance vectors + VICE/hardware; distinguish unimplemented register paths from valid defaults |
| K06 | Dirty-cache/UCI failure loses image data | High | Original images immutable; owned copies; exact count/status checks; new output and verification; fault injection and retained recovery state |
| K07 | 80-column colors/font are unreadable | Medium | Early physical font chart and editor test; monochrome/contrast policy; preserve all 80 columns and exact guest state |
| K08 | Turbo causes UCI timeout/protocol failures | High | Asynchronous handshake, elapsed deadlines, 1/16/64 MHz replay; no fixed-delay pacing |
| K09 | VICE traps hide IEC issues | Medium | Smaller true-drive/KERNAL lane and independent extracted-file comparisons |
| K10 | 2 MiB tests accidentally never evict HD cache | Medium | Force 64–256 KiB cache; random reads/writes; compare persisted bytes after reopen |
| K11 | File offsets silently truncate above 16 MiB | High | Explicit 32-bit arithmetic, boundary/final-sector tests in M9 |
| K12 | Original CPU boundary/interrupt quirks missing in vectors | Medium | Intel/Microsoft references, 8088/8086 corpora, independent hand-authored event tests before fast paths |
| K13 | Dirty sibling compiler/harness evolves during work | Medium | Pin/copy needed Peddle sources, hash references, tool manifest; avoid modifying sibling project |
| K14 | Installed C64U firmware differs from current upstream docs | Medium | Capture firmware/config, validate actual command behavior; bounded transfers and fallbacks |
| K15 | 2/20 MiB experimental CHS conflicts with supplied FDISK | Medium | Test exact binaries; use documented conventional geometry if needed and record actual bytes |
| K16 | Scope expands to all DOS utilities/peripheral modes | Medium | Explicit applicability matrix; no printer/network/EGA dependency; record unsupported operation instead of dropping entire useful utility |

No risk is marked resolved by the existence of this plan. Add measurements/evidence and dated state changes as work proceeds.

2026-10-14 checkpoint: K01 remains high. A public warm byte read costs 221 host CPU cycles in ALL_RAM mode, before address generation/decoding; span fetch/hot-path work is required. K05/K06 have stronger functional evidence from all-page/random/partial-failure cache tests and a native VICE eviction probe, but UCI/persistence/physical effects remain unverified. K14 now has a real device inventory (firmware 3.14, FPGA 121, core 1.47, enabled 16 MB REU); actual UCI behavior, active turbo speed and DMA timing remain open. Read-only discovery made no hardware/media changes.
